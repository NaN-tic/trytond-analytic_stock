# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal

from trytond.model import Workflow, ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

__all__ = ['Location', 'Move']
__metaclass__ = PoolMeta


class Location:
    __name__ = 'stock.location'
    analytic_accounts = fields.Many2One('analytic_account.account.selection',
        'Analytic Accounts',
        help='It is used to manage analytical costs of Stock Moves. If you '
        'fill up it, the stock movements from or to this location that '
        'aren\'t to or from a location with the same Analytic Accounts will '
        'generate an analytic line.')
    journal = fields.Many2One('account.journal', 'Journal')

    @classmethod
    def __setup__(cls):
        super(Location, cls).__setup__()
        cls._error_messages['journal_required'] = ('The journal is required '
            'for location "%s" because it has analytic accounts defined.')

    @classmethod
    def validate(cls, locations):
        for location in locations:
            if (location.analytic_accounts and
                    location.analytic_accounts.accounts and
                    not location.journal):
                cls.raise_user_error('journal_required', location.rec_name)

        super(Location, cls).validate(locations)

    @classmethod
    def _view_look_dom_arch(cls, tree, type, field_children=None):
        AnalyticAccount = Pool().get('analytic_account.account')
        AnalyticAccount.convert_view(tree)
        return super(Location, cls)._view_look_dom_arch(tree, type,
            field_children=field_children)

    @classmethod
    def fields_get(cls, fields_names=None):
        AnalyticAccount = Pool().get('analytic_account.account')

        fields = super(Location, cls).fields_get(fields_names)

        analytic_accounts_field = super(Location, cls).fields_get(
                ['analytic_accounts'])['analytic_accounts']

        fields.update(AnalyticAccount.analytic_accounts_fields_get(
                analytic_accounts_field, fields_names))
        return fields

    @classmethod
    def default_get(cls, fields, with_rec_name=True):
        fields = [x for x in fields if not x.startswith('analytic_account_')]
        return super(Location, cls).default_get(fields,
            with_rec_name=with_rec_name)

    @classmethod
    def read(cls, ids, fields_names=None):
        if fields_names:
            fields_names2 = [x for x in fields_names
                    if not x.startswith('analytic_account_')]
        else:
            fields_names2 = fields_names

        res = super(Location, cls).read(ids, fields_names=fields_names2)

        if not fields_names:
            fields_names = cls._fields.keys()

        root_ids = []
        for field in fields_names:
            if field.startswith('analytic_account_') and '.' not in field:
                root_ids.append(int(field[len('analytic_account_'):]))
        if root_ids:
            id2record = {}
            for record in res:
                id2record[record['id']] = record
            locations = cls.browse(ids)
            for location in locations:
                for root_id in root_ids:
                    id2record[location.id]['analytic_account_'
                        + str(root_id)] = None
                if not location.analytic_accounts:
                    continue
                for account in location.analytic_accounts.accounts:
                    if account.root.id in root_ids:
                        id2record[location.id]['analytic_account_'
                            + str(account.root.id)] = account.id
                        for field in fields_names:
                            if field.startswith('analytic_account_'
                                    + str(account.root.id) + '.'):
                                _, field2 = field.split('.', 1)
                                id2record[location.id][field] = account[field2]
        return res

    @classmethod
    def create(cls, vlist):
        Selection = Pool().get('analytic_account.account.selection')
        vlist = [x.copy() for x in vlist]
        to_write = []
        for vals in vlist:
            selection_vals = {}
            for field in vals.keys():
                if field.startswith('analytic_account_'):
                    if vals[field]:
                        selection_vals.setdefault('accounts', [])
                        selection_vals['accounts'].append(('add',
                                [vals[field]]))
                    del vals[field]
            if vals.get('analytic_accounts'):
                to_write.extend(([Selection(vals['analytic_accounts'])],
                    selection_vals))
            else:
                selection, = Selection.create([selection_vals])
                vals['analytic_accounts'] = selection.id

        if to_write:
            Selection.write(*to_write)

        return super(Location, cls).create(vlist)

    @classmethod
    def write(cls, *args):
        Selection = Pool().get('analytic_account.account.selection')
        actions = iter(args)
        args = []
        to_write = []
        for locations, vals in zip(actions, actions):
            vals = vals.copy()
            selection_vals = {}
            for field in vals.keys():
                if field.startswith('analytic_account_'):
                    root_id = int(field[len('analytic_account_'):])
                    selection_vals[root_id] = vals[field]
                    del vals[field]
            if selection_vals:
                for location in locations:
                    accounts = []
                    if not location.analytic_accounts:
                        # Create missing selection
                        with Transaction().set_user(0):
                            selection, = Selection.create([{}])
                        cls.write([location], {
                                'analytic_accounts': selection.id,
                                })
                    for account in location.analytic_accounts.accounts:
                        if account.root.id in selection_vals:
                            value = selection_vals[account.root.id]
                            if value:
                                accounts.append(value)
                        else:
                            accounts.append(account.id)
                    for account_id in selection_vals.values():
                        if account_id \
                                and account_id not in accounts:
                            accounts.append(account_id)
                    to_remove = list(
                        set((a.id for a in
                                location.analytic_accounts.accounts))
                        - set(accounts))
                    to_write.extend(([location.analytic_accounts], {
                            'accounts': [
                                ('remove', to_remove),
                                ('add', accounts),
                                ],
                            }))
            args.extend((locations, vals))
        if to_write:
            Selection.write(*to_write)
        return super(Location, cls).write(*args)

    @classmethod
    def delete(cls, locations):
        Selection = Pool().get('analytic_account.account.selection')

        selections = []
        for location in locations:
            if location.analytic_accounts:
                selections.append(location.analytic_accounts)

        super(Location, cls).delete(locations)
        Selection.delete(selections)

    @classmethod
    def copy(cls, locations, default=None):
        Selection = Pool().get('analytic_account.account.selection')

        new_locations = super(Location, cls).copy(locations, default=default)

        for location in new_locations:
            if location.analytic_accounts:
                selection, = Selection.copy([location.analytic_accounts])
                cls.write([location], {
                    'analytic_accounts': selection.id,
                    })
        return new_locations


class Move:
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
        default.update({
                'income_analytic_lines': None,
                'expense_analytic_lines': None,
                })
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
        if type_ == 'income':
            return (self.from_location.analytic_accounts and
                self.from_location.analytic_accounts.accounts or [])
        elif type_ == 'expense':
            return (self.to_location.analytic_accounts and
                self.to_location.analytic_accounts.accounts or [])
        return []

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

    def _get_journal_for_analytic(self, type_):
        if type_ == 'income':
            return self.from_location.journal
        elif type_ == 'expense':
            return self.to_location.journal

    def _get_analytic_lines_vals(self, type_, analytic_accounts, amount):
        journal = self._get_journal_for_analytic(type_)

        base_vals = {
            'name': self.rec_name,
            'internal_company': self.company.id,
            'journal': journal and journal.id,
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
