# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
try:
    from trytond.modules.analytic_stock.tests.test_analytic_stock import suite
except ImportError:
    from .test_analytic_stock import suite

__all__ = ['suite']
