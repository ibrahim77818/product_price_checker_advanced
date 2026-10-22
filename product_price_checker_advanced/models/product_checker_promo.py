# -*- coding: utf-8 -*-
# Part of product_price_checker_advanced. License LGPL-3.0 (https://www.gnu.org/licenses/lgpl-3.0.html).
from odoo import fields, models


class ProductCheckerPromo(models.Model):
    """Promotional slide displayed on the idle screen of a kiosk."""
    _name = 'product.checker.promo'
    _description = 'Price Checker Promotion'
    _order = 'sequence, id'

    config_id = fields.Many2one(
        'product.checker.config', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Caption', translate=True)
    image = fields.Image(required=True, max_width=1920, max_height=1920)
