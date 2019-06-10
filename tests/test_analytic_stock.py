# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import datetime
import unittest
from decimal import Decimal

import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase, with_transaction
from trytond.pool import Pool

from trytond.modules.company.tests import create_company, set_company
from trytond.modules.account.tests import create_chart


class AnalyticStockTestCase(ModuleTestCase):
    'Test AnalyticStock module'
    module = 'analytic_stock'

    @with_transaction()
    def test0010move_analytic_accounts(self):
        '''
        Test Move.income/expense_analytic_lines.
        '''
        pool = Pool()
        Template = pool.get('product.template')
        Uom = pool.get('product.uom')
        Location = pool.get('stock.location')
        AnalyticAccount = pool.get('analytic_account.account')
        Move = pool.get('stock.move')
        Party = pool.get('party.party')
        PaymentTerm = pool.get('account.invoice.payment_term')
        Purchase = pool.get('purchase.purchase')
        Sale = pool.get('sale.sale')

        company = create_company()
        with set_company(company):
            create_chart(company)
            unit, = Uom.search([('name', '=', 'Unit')])
            template, = Template.create([{
                        'name': 'Test Move.income/expense_analytic_lines',
                        'type': 'goods',
                        'list_price': Decimal(4),
                        'cost_price_method': 'fixed',
                        'default_uom': unit.id,
                        'products': [
                            ('create', [{}]),
                            ],
                        }])
            product, = template.products

            supplier, = Location.search([('code', '=', 'SUP')])
            customer, = Location.search([('code', '=', 'CUS')])
            storage, = Location.search([('code', '=', 'STO')])
            storage2, = Location.create([{
                        'name': 'Storage 2',
                        'code': 'STO2',
                        'type': 'storage',
                        'parent': storage.id,
                        }])

            # Analytic accounts
            analytic_acc_r1, analytic_acc_r2 = AnalyticAccount.create([{
                        'name': 'Root 1',
                        'code': 'R1',
                        'type': 'root',
                        }, {
                        'name': 'Root 2',
                        'code': 'R2',
                        'type': 'root',
                        }])
            (analytic_acc_a11, analytic_acc_a12, analytic_acc_a21,
                analytic_acc_a22) = AnalyticAccount.create([{
                        'name': 'Account R1-1',
                        'code': 'A11',
                        'type': 'normal',
                        'root': analytic_acc_r1.id,
                        'parent': analytic_acc_r1.id,
                        }, {
                        'name': 'Account R1-2',
                        'code': 'A12',
                        'type': 'normal',
                        'root': analytic_acc_r1.id,
                        'parent': analytic_acc_r1.id,
                        }, {
                        'name': 'Account R2-1',
                        'code': 'A21',
                        'type': 'normal',
                        'root': analytic_acc_r2.id,
                        'parent': analytic_acc_r2.id,
                        }, {
                        'name': 'Account R2-2',
                        'code': 'A22',
                        'type': 'normal',
                        'root': analytic_acc_r2.id,
                        'parent': analytic_acc_r2.id,
                        }])
            # set analytic accounts to locations
            Location.write([supplier, customer], {
                    'companies': [
                        ('create', [{
                                'analytic_accounts': [
                                    ('create', [{
                                            'root': analytic_acc_r1.id,
                                            'account': analytic_acc_a11.id,
                                            }, {
                                            'root': analytic_acc_r2.id,
                                            'account': analytic_acc_a22.id,
                                            }])
                                    ],
                                }])
                        ],
                    })
            Location.write([storage], {
                    'companies': [
                        ('create', [{
                                'analytic_accounts': [
                                    ('create', [{
                                            'root': analytic_acc_r1.id,
                                            'account': analytic_acc_a12.id,
                                            }, {
                                            'root': analytic_acc_r2.id,
                                            'account': analytic_acc_a21.id,
                                            }])
                                    ],
                                }])
                        ],
                    })

            today = datetime.date.today()

            # Create origin fields for moves
            party, = Party.create([{
                        'name': 'Customer/Supplier',
                        }])
            term, = PaymentTerm.create([{
                        'name': 'Payment Term',
                        'lines': [
                            ('create', [{
                                        'sequence': 0,
                                        'type': 'remainder',
                                        }])]
                        }])
            sale, = Sale.create([{
                        'party': party.id,
                        'payment_term': term.id,
                        'lines': [('create', [{
                                        'quantity': 1.0,
                                        'unit_price': Decimal(1),
                                        'description': 'desc',
                                        }])],

                        }])
            sale_line, = sale.lines
            purchase, = Purchase.create([{
                        'party': party.id,
                        'payment_term': term.id,
                        'lines': [('create', [{
                                        'quantity': 1.0,
                                        'unit_price': Decimal(1),
                                        'description': 'desc',
                                        }])],

                        }])
            purchase_line, = purchase.lines

            moves = Move.create([{
                        'product': product.id,
                        'uom': unit.id,
                        'quantity': 5,
                        'from_location': supplier.id,
                        'to_location': customer.id,
                        'planned_date': today,
                        'effective_date': today,
                        'company': company.id,
                        'unit_price': Decimal('1'),
                        'currency': company.currency.id,
                        'origin': str(sale_line),
                        }, {
                        'product': product.id,
                        'uom': unit.id,
                        'quantity': 10,
                        'from_location': supplier.id,
                        'to_location': storage.id,
                        'planned_date': today,
                        'effective_date': today,
                        'company': company.id,
                        'unit_price': Decimal('1'),
                        'currency': company.currency.id,
                        'origin': str(sale_line),
                        }, {
                        'product': product.id,
                        'uom': unit.id,
                        'quantity': 5,
                        'from_location': storage.id,
                        'to_location': storage2.id,
                        'planned_date': today,
                        'effective_date': today,
                        'company': company.id,
                        'unit_price': Decimal('1'),
                        'currency': company.currency.id,
                        }, {
                        'product': product.id,
                        'uom': unit.id,
                        'quantity': 5,
                        'from_location': storage2.id,
                        'to_location': customer.id,
                        'planned_date': today,
                        'effective_date': today,
                        'company': company.id,
                        'unit_price': Decimal('1'),
                        'currency': company.currency.id,
                        'origin': str(sale_line),
                        }])
            Move.do(moves)

            # supplier -> customer
            self.assertTrue(not moves[0].income_analytic_lines)
            self.assertTrue(not moves[0].expense_analytic_lines)
            # supplier -> storage
            self.assertTrue(not moves[1].income_analytic_lines)
            self.assertEqual(
                set([al.account.id for al in moves[1].expense_analytic_lines]),
                set([e.account.id for lc in storage.companies
                        for e in lc.analytic_accounts])
                )
            # storage -> storage2
            self.assertEqual(
                set([al.account.id for al in moves[2].income_analytic_lines]),
                set([e.account.id for lc in storage.companies
                        for e in lc.analytic_accounts])
                )
            self.assertTrue(not moves[2].expense_analytic_lines)
            # storage2 -> customer
            self.assertTrue(not moves[3].income_analytic_lines)
            self.assertEqual(
                set([al.account.id for al in moves[3].expense_analytic_lines]),
                set([e.account.id for lc in customer.companies
                        for e in lc.analytic_accounts])
                )


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        AnalyticStockTestCase))
    return suite
