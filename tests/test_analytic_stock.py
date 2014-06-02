#!/usr/bin/env python
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.

import sys
import os
DIR = os.path.abspath(os.path.normpath(os.path.join(__file__,
    '..', '..', '..', '..', '..', 'trytond')))
if os.path.isdir(DIR):
    sys.path.insert(0, os.path.dirname(DIR))

import unittest
import datetime
from decimal import Decimal
import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, DB_NAME, USER, CONTEXT, test_view,\
    test_depends
from trytond.transaction import Transaction


class AnalyticStockTestCase(unittest.TestCase):
    '''
    Test AnalyticStock module.
    '''

    def setUp(self):
        trytond.tests.test_tryton.install_module('analytic_stock')
        self.template = POOL.get('product.template')
        self.product = POOL.get('product.product')
        self.category = POOL.get('product.category')
        self.uom = POOL.get('product.uom')
        self.location = POOL.get('stock.location')
        self.company = POOL.get('company.company')
        self.user = POOL.get('res.user')
        self.journal = POOL.get('account.journal')
        self.analytic_account = POOL.get('analytic_account.account')
        self.move = POOL.get('stock.move')
        self.party = POOL.get('party.party')
        self.payment_term = POOL.get('account.invoice.payment_term')
        self.purchase = POOL.get('purchase.purchase')
        self.sale = POOL.get('sale.sale')

    def test0005views(self):
        '''
        Test views.
        '''
        test_view('analytic_stock')

    def test0006depends(self):
        '''
        Test depends.
        '''
        test_depends()

    def test0010move_analytic_accounts(self):
        '''
        Test Move.income/expense_analytic_lines.
        '''
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            category, = self.category.create([{
                        'name': 'Test Move.income/expense_analytic_lines',
                        }])
            unit, = self.uom.search([('name', '=', 'Unit')])
            template, = self.template.create([{
                        'name': 'Test Move.income/expense_analytic_lines',
                        'type': 'goods',
                        'list_price': Decimal(4),
                        'cost_price': Decimal(2),
                        'category': category.id,
                        'cost_price_method': 'fixed',
                        'default_uom': unit.id,
                        }])
            product, = self.product.create([{
                        'template': template.id,
                        }])
            supplier, = self.location.search([('code', '=', 'SUP')])
            customer, = self.location.search([('code', '=', 'CUS')])
            storage, = self.location.search([('code', '=', 'STO')])
            storage2, = self.location.create([{
                        'name': 'Storage 2',
                        'code': 'STO2',
                        'type': 'storage',
                        'parent': storage.id,
                        }])

            company, = self.company.search([
                    ('rec_name', '=', 'Dunder Mifflin'),
                    ])
            currency = company.currency
            self.user.write([self.user(USER)], {
                'main_company': company.id,
                'company': company.id,
                })
            journal_expense, = self.journal.search([
                    ('code', '=', 'EXP'),
                    ])

            # Analytic accounts
            analytic_acc_r1, analytic_acc_r2 = self.analytic_account.create([{
                        'name': 'Root 1',
                        'code': 'R1',
                        'currency': currency.id,
                        'company': None,
                        'type': 'root',
                        'state': 'opened',
                        }, {
                        'name': 'Root 2',
                        'code': 'R2',
                        'currency': currency.id,
                        'company': None,
                        'type': 'root',
                        'state': 'opened',
                        }])
            (analytic_acc_a11, analytic_acc_a12, analytic_acc_a21,
                analytic_acc_a22) = self.analytic_account.create([{
                        'name': 'Account R1-1',
                        'code': 'A11',
                        'currency': currency.id,
                        'company': None,
                        'type': 'normal',
                        'root': analytic_acc_r1.id,
                        'parent': analytic_acc_r1.id,
                        'state': 'opened',
                        }, {
                        'name': 'Account R1-2',
                        'code': 'A12',
                        'currency': currency.id,
                        'company': None,
                        'type': 'normal',
                        'root': analytic_acc_r1.id,
                        'parent': analytic_acc_r1.id,
                        'state': 'opened',
                        }, {
                        'name': 'Account R2-1',
                        'code': 'A21',
                        'currency': currency.id,
                        'company': None,
                        'type': 'normal',
                        'root': analytic_acc_r2.id,
                        'parent': analytic_acc_r2.id,
                        'state': 'opened',
                        }, {
                        'name': 'Account R2-2',
                        'code': 'A22',
                        'currency': currency.id,
                        'company': None,
                        'type': 'normal',
                        'root': analytic_acc_r2.id,
                        'parent': analytic_acc_r2.id,
                        'state': 'opened',
                        }])
            # set analytic accounts to locations
            root1_field = 'analytic_account_%d' % analytic_acc_r1.id
            root2_field = 'analytic_account_%d' % analytic_acc_r2.id
            self.location.write([supplier, customer], {
                    root1_field: analytic_acc_a11.id,
                    root2_field: analytic_acc_a22.id,
                    'journal': journal_expense.id,
                    })
            self.location.write([storage], {
                    root1_field: analytic_acc_a12.id,
                    root2_field: analytic_acc_a21.id,
                    'journal': journal_expense.id,
                    })

            today = datetime.date.today()

            #Create origin fields for moves
            party, = self.party.create([{
                        'name': 'Customer/Supplier',
                        }])
            term, = self.payment_term.create([{
                        'name': 'Payment Term',
                        'lines': [
                            ('create', [{
                                        'sequence': 0,
                                        'type': 'remainder',
                                        'months': 0,
                                        'days': 0,
                                        }])]
                        }])
            sale, = self.sale.create([{
                        'party': party.id,
                        'payment_term': term.id,
                        'lines': [('create', [{
                                        'quantity': 1.0,
                                        'unit_price': Decimal(1),
                                        'description': 'desc',
                                        }])],

                        }])
            sale_line, = sale.lines
            purchase, = self.purchase.create([{
                        'party': party.id,
                        'payment_term': term.id,
                        'lines': [('create', [{
                                        'quantity': 1.0,
                                        'unit_price': Decimal(1),
                                        'description': 'desc',
                                        }])],

                        }])
            purchase_line, = purchase.lines

            moves = self.move.create([{
                        'product': product.id,
                        'uom': unit.id,
                        'quantity': 5,
                        'from_location': supplier.id,
                        'to_location': customer.id,
                        'planned_date': today,
                        'effective_date': today,
                        'company': company.id,
                        'unit_price': Decimal('1'),
                        'currency': currency.id,
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
                        'currency': currency.id,
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
                        'currency': currency.id,
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
                        'currency': currency.id,
                        'origin': str(sale_line),
                        }])
            self.move.do(moves)

            # supplier -> customer
            self.assertTrue(not moves[0].income_analytic_lines)
            self.assertTrue(not moves[0].expense_analytic_lines)
            # supplier -> storage
            self.assertTrue(not moves[1].income_analytic_lines)
            self.assertEqual(
                set([al.account.id for al in moves[1].expense_analytic_lines]),
                set([a.id for a in storage.analytic_accounts.accounts])
                )
            # storage -> storage2
            self.assertEqual(
                set([al.account.id for al in moves[2].income_analytic_lines]),
                set([a.id for a in storage.analytic_accounts.accounts])
                )
            self.assertTrue(not moves[2].expense_analytic_lines)
            # storage2 -> customer
            self.assertTrue(not moves[3].income_analytic_lines)
            self.assertEqual(
                set([al.account.id for al in moves[3].expense_analytic_lines]),
                set([a.id for a in customer.analytic_accounts.accounts])
                )


def suite():
    suite = trytond.tests.test_tryton.suite()
    from trytond.modules.account.tests import test_account
    for test in test_account.suite():
        #Skip doctest
        class_name = test.__class__.__name__
        if test not in suite and class_name != 'DocFileCase':
            suite.addTest(test)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        AnalyticStockTestCase))
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
