# -*- coding: utf-8 -*-
# Part of product_price_checker_advanced. License LGPL-3.0 (https://www.gnu.org/licenses/lgpl-3.0.html).
from odoo import api, fields, models


class ProductCheckerPricelist(models.Model):
    """Ordered pricelists displayed by a kiosk; the first one is the main price."""
    _name = 'product.checker.pricelist'
    _description = 'Price Checker Pricelist'
    _order = 'sequence, id'

    config_id = fields.Many2one(
        'product.checker.config', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='config_id.company_id')
    sequence = fields.Integer(default=10)
    pricelist_id = fields.Many2one(
        'product.pricelist', required=True, ondelete='cascade',
        domain="[('company_id', 'in', [company_id, False])]")
    label = fields.Char(
        translate=True,
        help='Caption shown on the kiosk, e.g. "Members price". Defaults to the pricelist name.')
    currency_id = fields.Many2one(related='pricelist_id.currency_id')

    _sql_constraints = [
        ('pricelist_unique', 'unique(config_id, pricelist_id)',
         'A pricelist can only be added once per kiosk.'),
    ]

    @api.onchange('pricelist_id')
    def _onchange_pricelist_id(self):
        if self.pricelist_id and not self.label:
            self.label = self.pricelist_id.name
