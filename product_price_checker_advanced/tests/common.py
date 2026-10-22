# -*- coding: utf-8 -*-
# Part of product_price_checker_advanced. License LGPL-3.0 (https://www.gnu.org/licenses/lgpl-3.0.html).
"""Shared fixture: a 2x2 variant product, two warehouses with shelves, stock and pricelists.

Tests never rely on the module demo data, so they also pass on databases
installed without demo.
"""
from odoo import Command


class PriceCheckerCommon:

    @classmethod
    def setup_price_checker_data(cls):
        env = cls.env
        cls.company = env.company
        # Make test data independent from whatever the database already contains.
        Attribute = env['product.attribute']
        cls.attr_color = Attribute.create({
            'name': 'PPC Colour', 'display_type': 'color', 'create_variant': 'always',
            'value_ids': [
                Command.create({'name': 'Red', 'html_color': '#ff0000', 'sequence': 1}),
                Command.create({'name': 'Blue', 'html_color': '#0000ff', 'sequence': 2}),
            ],
        })
        cls.attr_size = Attribute.create({
            'name': 'PPC Size', 'display_type': 'pills', 'create_variant': 'always',
            'value_ids': [
                Command.create({'name': 'S', 'sequence': 1}),
                Command.create({'name': 'M', 'sequence': 2}),
            ],
        })
        cls.attr_option = Attribute.create({
            'name': 'PPC Engraving', 'create_variant': 'no_variant',
            'value_ids': [Command.create({'name': 'Yes'}), Command.create({'name': 'No'})],
        })
        cls.red, cls.blue = cls.attr_color.value_ids
        cls.small, cls.medium = cls.attr_size.value_ids

        cls.template = env['product.template'].create({
            'name': 'PPC Test Tee',
            'detailed_type': 'product',
            'list_price': 100.0,
            'sale_ok': True,
            'description_sale': 'A very comfortable test tee.',
            'attribute_line_ids': [
                Command.create({'attribute_id': cls.attr_color.id,
                                'value_ids': [Command.set(cls.attr_color.value_ids.ids)]}),
                Command.create({'attribute_id': cls.attr_size.id,
                                'value_ids': [Command.set(cls.attr_size.value_ids.ids)]}),
                Command.create({'attribute_id': cls.attr_option.id,
                                'value_ids': [Command.set(cls.attr_option.value_ids.ids)]}),
            ],
        })
        cls.variants = {}
        for variant in cls.template.product_variant_ids:
            values = variant.product_template_attribute_value_ids.product_attribute_value_id
            color = (values & cls.attr_color.value_ids).name
            size = (values & cls.attr_size.value_ids).name
            variant.write({
                'default_code': 'PPC-%s-%s' % (color[:3].upper(), size),
                'barcode': 'PPC%s%s0001' % (color[:3].upper(), size),
            })
            cls.variants[(color, size)] = variant
        cls.red_s = cls.variants[('Red', 'S')]
        cls.red_m = cls.variants[('Red', 'M')]
        cls.blue_s = cls.variants[('Blue', 'S')]
        cls.blue_m = cls.variants[('Blue', 'M')]
        # Size M costs +10.
        cls.template.attribute_line_ids.product_template_value_ids.filtered(
            lambda v: v.product_attribute_value_id == cls.medium).price_extra = 10.0
        # Blue / M is not sold: an "unavailable" combination for the matrix.
        cls.blue_m.active = False

        cls.hidden_product = env['product.product'].create({
            'name': 'PPC Internal Spare Part', 'detailed_type': 'product',
            'sale_ok': False, 'default_code': 'PPC-HIDDEN', 'barcode': 'PPCHIDDEN01',
        })
        cls.service = env['product.product'].create({
            'name': 'PPC Gift Card Service', 'detailed_type': 'service',
            'default_code': 'PPC-SRV', 'list_price': 25.0,
        })
        env['product.packaging'].create({
            'name': 'PPC box of 6', 'product_id': cls.red_s.id, 'qty': 6, 'barcode': 'PPCBOX6RED',
        })

        # Warehouses & locations.
        Location = env['stock.location']
        cls.wh_main = env['stock.warehouse'].search([('company_id', '=', cls.company.id)], limit=1)
        cls.wh_second = env['stock.warehouse'].create({
            'name': 'PPC Second Store', 'code': 'PPC2', 'company_id': cls.company.id})
        cls.shelf_1 = Location.create({'name': 'PPC Shelf 1', 'location_id': cls.wh_main.lot_stock_id.id})
        cls.shelf_2 = Location.create({'name': 'PPC Shelf 2', 'location_id': cls.wh_main.lot_stock_id.id})
        cls.bin_1 = Location.create({'name': 'PPC Bin 1', 'location_id': cls.shelf_1.id})

        # Stock: Red/M = 7 + 3 (+1 in a bin under shelf 1) in main, 5 in second store.
        Quant = env['stock.quant']
        Quant._update_available_quantity(cls.red_m, cls.shelf_1, 7.0)
        Quant._update_available_quantity(cls.red_m, cls.bin_1, 1.0)
        Quant._update_available_quantity(cls.red_m, cls.shelf_2, 3.0)
        Quant._update_available_quantity(cls.red_m, cls.wh_second.lot_stock_id, 5.0)
        Quant._update_reserved_quantity(cls.red_m, cls.shelf_1, 2.0)
        Quant._update_available_quantity(cls.red_s, cls.shelf_2, 4.0)

        # Pricelists: the public one and a 10% members discount.
        Pricelist = env['product.pricelist']
        currency = cls.company.currency_id
        cls.pricelist_public = Pricelist.create({'name': 'PPC Public', 'currency_id': currency.id})
        cls.pricelist_members = Pricelist.create({
            'name': 'PPC Members', 'currency_id': currency.id,
            'item_ids': [Command.create({
                'applied_on': '3_global', 'compute_price': 'percentage', 'percent_price': 10,
            })],
        })

        cls.config = env['product.checker.config'].create({
            'name': 'PPC Test Kiosk',
            'company_id': cls.company.id,
            'warehouse_ids': [Command.set((cls.wh_main | cls.wh_second).ids)],
            'stock_display': 'location',
            'stock_qty_mode': 'quantity',
            'low_stock_threshold': 4.0,
            'price_tax_mode': 'excluded',
            'pricelist_line_ids': [
                Command.create({'pricelist_id': cls.pricelist_public.id, 'label': 'Price', 'sequence': 1}),
                Command.create({'pricelist_id': cls.pricelist_members.id, 'label': 'Members', 'sequence': 2}),
            ],
            'lang_ids': [Command.set(env['res.lang']._lang_get('en_US').ids)],
            'default_lang_id': env['res.lang']._lang_get('en_US').id,
        })
        cls.kiosk = cls.config._ppc_kiosk_env('en_US')
