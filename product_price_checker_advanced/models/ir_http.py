# -*- coding: utf-8 -*-
# Part of product_price_checker_advanced. License LGPL-3.0 (https://www.gnu.org/licenses/lgpl-3.0.html).
from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        """Public pages only load the terms of whitelisted modules: add the kiosk's."""
        modules = super()._get_translation_frontend_modules_name()
        return modules + ['product_price_checker_advanced']
