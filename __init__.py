# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool

import stock


def register():
    Pool.register(
        stock.AnalyticLine,
        stock.Location,
        stock.Move,
        module='analytic_stock', type_='model')
