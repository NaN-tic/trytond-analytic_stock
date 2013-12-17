#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.

from trytond.pool import Pool
from .analytic import *
from .stock import *


def register():
    Pool.register(
        Location,
        Account,
        Line,
        Move,
        module='analytic_stock', type_='model')
