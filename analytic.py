#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta

__all__ = ['Account', 'Line']
__metaclass__ = PoolMeta


class Account:
    __name__ = 'analytic_account.account'

    @classmethod
    def delete(cls, accounts):
        Location = Pool().get('stock.location')
        super(Account, cls).delete(accounts)
        # Restart the cache on the fields_view_get method of stock.location
        Location._fields_view_get_cache.clear()

    @classmethod
    def create(cls, vlist):
        Location = Pool().get('stock.location')
        accounts = super(Account, cls).create(vlist)
        # Restart the cache on the fields_view_get method of stock.location
        Location._fields_view_get_cache.clear()
        return accounts

    @classmethod
    def write(cls, *args):
        Location = Pool().get('stock.location')
        super(Account, cls).write(*args)
        # Restart the cache on the fields_view_get method of stock.location
        Location._fields_view_get_cache.clear()


class Line:
    __name__ = 'analytic_account.line'
    income_stock_move = fields.Many2One('stock.move', 'Income Stock Move',
            ondelete='CASCADE', readonly=True)
    expense_stock_move = fields.Many2One('stock.move', 'Expense Stock Move',
            ondelete='CASCADE', readonly=True)
