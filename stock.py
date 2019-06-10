# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
from trytond.model import Workflow, ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

__all__ = ['AnalyticLine', 'Location', 'Move']


class AnalyticLine(metaclass=PoolMeta):
    __name__ = 'analytic_account.line'
    income_stock_move = fields.Many2One('stock.move', 'Income Stock Move',
            ondelete='CASCADE', readonly=True)
    expense_stock_move = fields.Many2One('stock.move', 'Expense Stock Move',
            ondelete='CASCADE', readonly=True)


class Location(metaclass=PoolMeta):
    __name__ = 'stock.location'

    @classmethod
    def enabled_location_types(cls):
        location_types = super(Location, cls).enabled_location_types()
        if 'storage' not in location_types:
            location_types.append('storage')
        return location_types


class Move(metaclass=PoolMeta):
    __name__ = 'stock.move'
    income_analytic_lines = fields.One2Many('analytic_account.line',
        'income_stock_move', 'Income Analytic Lines', readonly=True,
        help='Analytic lines to manage analytical costs of stock moves when '
        'these aren\'t originated on sales nor purchases.\n'
        'These are the analytic lines that computes the value of this move as '
        'income for destination location.')
    expense_analytic_lines = fields.One2Many('analytic_account.line',
        'expense_stock_move', 'Expense Analytic Lines', readonly=True,
        help='Analytic lines to manage analytical costs of stock moves when '
        'these aren\'t originated on sales nor purchases.\n'
        'These are the analytic lines that computes the value of this move as '
        'expense for source location.')

    @classmethod
    def copy(cls, moves, default=None):
        if default is None:
            default = {}
        default = default.copy()
        default.setdefault('income_analytic_lines', None)
        default.setdefault('expense_analytic_lines', None)
        return super(Move, cls).copy(moves, default=default)

    @classmethod
    @ModelView.button
    @Workflow.transition('done')
    def do(cls, moves):
        super(Move, cls).do(moves)
        for move in moves:
            vals = move._analytic_vals()
            if vals:
                cls.write([move], vals)

    def _analytic_vals(self):
        '''
        If analytic accounts defined in from_location and to_location are
        diferent, it prepares the values of analytic lines for
        'income_analytic_lines' and 'expense_analytic_lines' fields.
        It uses the 'unit_price' and 'quantity' to compute the amount.
        If 'unit_price' is empty it uses the cost_price.
        '''
        pool = Pool()
        PurchaseLine = pool.get('purchase.line')
        SaleLine = pool.get('sale.line')

        income_analytic_accs = self._get_analytic_accounts('income')
        expense_analytic_accs = self._get_analytic_accounts('expense')
        if (set([a.id for a in income_analytic_accs]) ==
                set([a.id for a in expense_analytic_accs])):
            # same analytic accounts => no analytic cost/moves
            return

        amount = self._get_analytic_amount()

        vals = {}
        if income_analytic_accs and not isinstance(self.origin, SaleLine):
            income_lines_vals = self._get_analytic_lines_vals('income',
                income_analytic_accs, amount)
            if income_lines_vals:
                vals['income_analytic_lines'] = [('create', income_lines_vals)]

        if expense_analytic_accs and not isinstance(self.origin, PurchaseLine):
            expense_lines_vals = self._get_analytic_lines_vals('expense',
                expense_analytic_accs, amount)
            if expense_lines_vals:
                vals['expense_analytic_lines'] = [
                    ('create', expense_lines_vals),
                    ]

        return vals

    def _get_analytic_accounts(self, type_):
        pool = Pool()
        AnalyticEntry = pool.get('analytic.account.entry')

        entries = AnalyticEntry.search([
                ('origin.company', '=', self.company,
                    'stock.location.company'),
                ('origin.location', '=',
                    self.from_location if type_ == 'income'
                    else self.to_location,
                    'stock.location.company'),
                ('account', '!=', None),
                ])
        return [e.account for e in entries]

    def _get_analytic_amount(self):
        pool = Pool()
        Currency = pool.get('currency.currency')
        Uom = pool.get('product.uom')

        # unit_price is in move's UoM and currency. cost_price is in product's
        # default_uom and company's currency
        if self.unit_price:
            amount = self.unit_price * Decimal(str(self.quantity))
            if self.currency != self.company.currency:
                with Transaction().set_context(date=self.effective_date):
                    amount = Currency.compute(self.currency, amount,
                        self.company.currency)
        else:
            qty = Uom.compute_qty(self.uom, self.quantity,
                self.product.default_uom)
            amount = self.cost_price * Decimal(str(qty))

        digits = self.company.currency.digits
        return amount.quantize(Decimal(str(10.0 ** -digits)))

    def _get_analytic_lines_vals(self, type_, analytic_accounts, amount):
        base_vals = {
            'internal_company': self.company.id,
            'date': self.effective_date,
            'debit': Decimal(0),
            'credit': Decimal(0),
            }
        if type_ == 'income':
            base_vals['debit'] = amount
        elif type_ == 'expense':
            base_vals['credit'] = amount

        if self.shipment:
            base_vals['reference'] = self.shipment.reference
            if hasattr(self.shipment, 'customer'):
                base_vals['party'] = self.shipment.customer.id
            elif hasattr(self.shipment, 'supplier'):
                base_vals['party'] = self.shipment.supplier.id

        lines_vals = []
        for account in analytic_accounts:
            vals = base_vals.copy()
            vals['account'] = account.id
            lines_vals.append(vals)
        return lines_vals
