# -*- coding: utf-8 -*-
# Part of product_price_checker_advanced. License LGPL-3.0 (https://www.gnu.org/licenses/lgpl-3.0.html).
from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

from .common import PriceCheckerCommon


@tagged('post_install', '-at_install', 'product_price_checker_advanced')
class TestPriceChecker(PriceCheckerCommon, TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.setup_price_checker_data()

    # ------------------------------------------------------------------
    # Tokens & access
    # ------------------------------------------------------------------
    def test_token_unique_and_regenerated(self):
        token = self.config.token
        self.assertGreaterEqual(len(token), 40, "Tokens must carry at least 256 bits of entropy")
        other = self.config.copy()
        self.assertNotEqual(other.token, token, "A copied kiosk must get its own token")
        self.config.action_regenerate_token()
        self.assertNotEqual(self.config.token, token)
        self.assertFalse(self.env['product.checker.config']._ppc_get_by_token(token),
                         "The old URL must stop working once the token is regenerated")
        self.assertEqual(
            self.env['product.checker.config']._ppc_get_by_token(self.config.token), self.config)

    def test_token_lookup_rejects_archived_and_garbage(self):
        Config = self.env['product.checker.config']
        self.assertFalse(Config._ppc_get_by_token('nope'))
        self.assertFalse(Config._ppc_get_by_token(''))
        self.assertFalse(Config._ppc_get_by_token('x' * 500))
        token = self.config.token
        self.config.active = False
        self.assertFalse(Config._ppc_get_by_token(token))

    def test_kiosk_url(self):
        self.assertTrue(self.config.kiosk_url.endswith('/product_checker/token/%s' % self.config.token))

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def test_search_exact_barcode_preselects_variant(self):
        result = self.kiosk._ppc_search('PPCREDM0001')
        self.assertEqual(result['status'], 'found')
        self.assertEqual(result['match'], 'exact')
        self.assertEqual(result['product']['selected_variant_id'], self.red_m.id)

    def test_search_internal_reference_case_insensitive(self):
        result = self.kiosk._ppc_search('ppc-blu-s')
        self.assertEqual(result['status'], 'found')
        self.assertEqual(result['product']['selected_variant_id'], self.blue_s.id)

    def test_search_packaging_barcode(self):
        result = self.kiosk._ppc_search('PPCBOX6RED')
        self.assertEqual(result['status'], 'found')
        self.assertEqual(result['product']['selected_variant_id'], self.red_s.id)

    def test_search_by_name_returns_template(self):
        result = self.kiosk._ppc_search('Test Tee')
        self.assertEqual(result['status'], 'found')
        self.assertEqual(result['product']['template']['id'], self.template.id)

    def test_search_multiple_templates(self):
        self.env['product.product'].create({'name': 'PPC Test Mug', 'sale_ok': True})
        result = self.kiosk._ppc_search('PPC Test')
        self.assertEqual(result['status'], 'multiple')
        names = {r['name'] for r in result['results']}
        self.assertIn('PPC Test Tee', names)
        self.assertIn('PPC Test Mug', names)
        tee = next(r for r in result['results'] if r['template_id'] == self.template.id)
        self.assertEqual(tee['variant_count'], 3, "The archived variant must not be counted")
        self.assertFalse(tee['product_id'], "A multi-variant template opens on its matrix")

    def test_search_respects_products_filter(self):
        self.assertEqual(self.kiosk._ppc_search('PPCHIDDEN01')['status'], 'none',
                         "Products outside the kiosk filter (sale_ok) must not be found")
        self.config.product_domain = "[('default_code', '=like', 'PPC-RED-%')]"
        kiosk = self.config._ppc_kiosk_env('en_US')
        self.assertEqual(kiosk._ppc_search('PPC-BLU-S')['status'], 'none')
        self.assertEqual(kiosk._ppc_search('PPC-RED-S')['status'], 'found')

    def test_search_respects_search_methods(self):
        self.config.search_barcode = False
        kiosk = self.config._ppc_kiosk_env('en_US')
        self.assertEqual(kiosk._ppc_search('PPCREDM0001')['status'], 'none')

    def test_search_too_short(self):
        self.assertEqual(self.kiosk._ppc_search('P')['status'], 'too_short')
        self.assertEqual(self.kiosk._ppc_search('   ')['status'], 'too_short')

    def test_search_name_in_any_kiosk_language(self):
        """A product can be found by its name in any kiosk language."""
        lang = self.env['res.lang']._activate_lang('fr_FR')
        self.template.update_field_translations('name', {'fr_FR': 'Tee-shirt de test PPC'})
        self.config.lang_ids = [Command.link(lang.id)]
        kiosk_en = self.config._ppc_kiosk_env('en_US')
        result = kiosk_en._ppc_search('Tee-shirt de test')
        self.assertEqual(result['status'], 'found')
        self.assertEqual(result['product']['template']['name'], 'PPC Test Tee',
                         "Results come back in the kiosk language")
        kiosk_fr = self.config._ppc_kiosk_env('fr_FR')
        self.assertEqual(kiosk_fr._ppc_search('PPC-RED-S')['product']['template']['name'],
                         'Tee-shirt de test PPC')

    # ------------------------------------------------------------------
    # Variant matrix
    # ------------------------------------------------------------------
    def test_payload_variant_attribute_filtering(self):
        payload = self.kiosk._ppc_product_payload(self.red_m)
        attribute_names = [a['name'] for a in payload['attributes']]
        self.assertEqual(attribute_names, ['PPC Colour', 'PPC Size'],
                         "'Never' (no_variant) attributes are not part of the matrix")
        variant_ids = [v['id'] for v in payload['variants']]
        self.assertNotIn(self.blue_m.id, variant_ids, "Archived variants are excluded")
        self.assertEqual(variant_ids, [self.red_s.id, self.red_m.id, self.blue_s.id],
                         "Variants follow the attribute matrix order")
        # Every variant exposes exactly one value per matrix attribute.
        colour_values = {v['id'] for v in payload['attributes'][0]['values']}
        size_values = {v['id'] for v in payload['attributes'][1]['values']}
        for variant in payload['variants']:
            values = set(variant['value_ids'])
            self.assertEqual(len(values & colour_values), 1)
            self.assertEqual(len(values & size_values), 1)
        red_m = next(v for v in payload['variants'] if v['id'] == self.red_m.id)
        self.assertEqual(red_m['default_code'], 'PPC-RED-M')
        self.assertEqual(red_m['variant_label'], 'Red, M')
        self.assertEqual(payload['selected_variant_id'], self.red_m.id)
        self.assertEqual(payload['template']['description'], 'A very comfortable test tee.')

    def test_payload_unavailable_combination(self):
        """Blue/M is archived: no variant combines both values."""
        payload = self.kiosk._ppc_product_payload(template=self.template)
        ptav = {v['name']: v['id'] for a in payload['attributes'] for v in a['values']}
        combos = [set(v['value_ids']) for v in payload['variants']]
        self.assertNotIn({ptav['Blue'], ptav['M']}, combos)
        self.assertIn({ptav['Blue'], ptav['S']}, combos)
        # Both values still exist in the matrix (they combine with something else).
        self.assertIn('Blue', ptav)
        self.assertIn('M', ptav)

    def test_payload_hides_disabled_fields(self):
        self.config.write({'show_default_code': False, 'show_barcode': False, 'show_description': False})
        payload = self.config._ppc_kiosk_env('en_US')._ppc_product_payload(self.red_m)
        variant = payload['variants'][0]
        self.assertEqual((variant['default_code'], variant['barcode']), ('', ''))
        self.assertEqual(payload['template']['description'], '')

    def test_prices_per_pricelist_and_variant(self):
        payload = self.kiosk._ppc_product_payload(self.red_m)
        by_id = {v['id']: v for v in payload['variants']}
        red_s_prices = by_id[self.red_s.id]['prices']
        red_m_prices = by_id[self.red_m.id]['prices']
        self.assertEqual([p['label'] for p in red_m_prices], ['Price', 'Members'])
        self.assertTrue(red_m_prices[0]['is_primary'])
        self.assertAlmostEqual(red_s_prices[0]['price'], 100.0)
        self.assertAlmostEqual(red_m_prices[0]['price'], 110.0, msg="price_extra of size M")
        self.assertAlmostEqual(red_m_prices[1]['price'], 99.0)
        self.assertEqual(red_m_prices[1]['discount'], 10)
        self.assertTrue(red_m_prices[1]['list_price_fmt'])
        self.assertEqual(red_m_prices[0]['discount'], 0)

    def test_prices_without_configured_pricelist_fall_back(self):
        self.config.pricelist_line_ids = [Command.clear()]
        payload = self.config._ppc_kiosk_env('en_US')._ppc_product_payload(self.red_s)
        self.assertEqual(len(payload['variants'][0]['prices']), 1)

    # ------------------------------------------------------------------
    # Multi-location stock
    # ------------------------------------------------------------------
    def _warehouse_row(self, stock, warehouse):
        return next(w for w in stock['warehouses'] if w['id'] == warehouse.id)

    def test_stock_per_location(self):
        stock = self.kiosk._ppc_stock(self.red_m)
        main = self._warehouse_row(stock, self.wh_main)
        second = self._warehouse_row(stock, self.wh_second)
        self.assertEqual((main['on_hand'], main['available']), (11.0, 9.0),
                         "7 + 1 + 3 on hand, 2 reserved")
        self.assertEqual((second['on_hand'], second['available']), (5.0, 5.0))
        self.assertEqual((stock['total']['on_hand'], stock['total']['available']), (16.0, 14.0))
        locations = {loc['id']: loc for loc in main['locations']}
        self.assertEqual(set(locations), {self.shelf_1.id, self.bin_1.id, self.shelf_2.id},
                         "Every internal location holding stock is listed")
        self.assertEqual(locations[self.shelf_1.id]['available'], 5.0)
        self.assertEqual(locations[self.shelf_2.id]['status'], 'low', "3 <= threshold of 4")
        self.assertFalse(locations[self.shelf_1.id]['name'].startswith(self.wh_main.code + '/'),
                         "Location names are shown relative to their warehouse")

    def test_stock_explicit_locations_aggregate_children(self):
        self.config.location_ids = [Command.set((self.shelf_1 | self.wh_second.lot_stock_id).ids)]
        stock = self.config._ppc_kiosk_env('en_US')._ppc_stock(self.red_m)
        main = self._warehouse_row(stock, self.wh_main)
        self.assertEqual([loc['id'] for loc in main['locations']], [self.shelf_1.id])
        self.assertEqual(main['locations'][0]['on_hand'], 8.0, "Shelf 1 includes its bin")
        self.assertEqual(main['on_hand'], 8.0, "Shelf 2 is out of the configured scope")
        second = self._warehouse_row(stock, self.wh_second)
        self.assertEqual(second['locations'][0]['on_hand'], 5.0)

    def test_stock_per_warehouse_mode(self):
        self.config.stock_display = 'warehouse'
        stock = self.config._ppc_kiosk_env('en_US')._ppc_stock(self.red_m)
        self.assertEqual(stock['mode'], 'warehouse')
        self.assertTrue(all(not w['locations'] for w in stock['warehouses']))
        self.assertEqual(self._warehouse_row(stock, self.wh_main)['on_hand'], 11.0)

    def test_stock_warehouse_filter(self):
        self.config.warehouse_ids = [Command.set(self.wh_second.ids)]
        stock = self.config._ppc_kiosk_env('en_US')._ppc_stock(self.red_m)
        self.assertEqual([w['id'] for w in stock['warehouses']], [self.wh_second.id])
        self.assertEqual(stock['total']['on_hand'], 5.0)

    def test_stock_status_mode_hides_quantities(self):
        self.config.stock_qty_mode = 'status'
        stock = self.config._ppc_kiosk_env('en_US')._ppc_stock(self.red_m)
        main = self._warehouse_row(stock, self.wh_main)
        self.assertNotIn('on_hand', main, "Exact quantities never leave the server in status mode")
        self.assertEqual(main['status'], 'in')
        self.assertEqual(self._warehouse_row(stock, self.wh_second)['status'], 'in')

    def test_stock_variant_matrix(self):
        stock = self.kiosk._ppc_stock(self.red_m)
        matrix = stock['matrix']
        self.assertEqual([w['id'] for w in matrix['warehouses']], [self.wh_main.id, self.wh_second.id])
        rows = {row['product_id']: row for row in matrix['rows']}
        self.assertEqual(set(rows), {self.red_s.id, self.red_m.id, self.blue_s.id})
        self.assertEqual([c['available'] for c in rows[self.red_m.id]['cells']], [9.0, 5.0])
        self.assertEqual([c['available'] for c in rows[self.red_s.id]['cells']], [4.0, 0.0])
        self.assertEqual(rows[self.blue_s.id]['total']['status'], 'out')

    def test_stock_hidden_and_non_storable(self):
        self.assertFalse(self.kiosk._ppc_stock(self.service))
        self.config.stock_display = 'hidden'
        self.assertFalse(self.config._ppc_kiosk_env('en_US')._ppc_stock(self.red_m))

    # ------------------------------------------------------------------
    # Languages & configuration
    # ------------------------------------------------------------------
    def test_resolve_lang(self):
        self.assertEqual(self.config._ppc_resolve_lang('en_US'), 'en_US')
        self.assertEqual(self.config._ppc_resolve_lang('xx_XX'), 'en_US',
                         "Unknown languages fall back to the default one")
        lang = self.env['res.lang']._activate_lang('fr_FR')
        self.assertEqual(self.config._ppc_resolve_lang('fr_FR'), 'en_US',
                         "Active but not offered on this kiosk")
        self.config.lang_ids = [Command.link(lang.id)]
        self.assertEqual(self.config._ppc_resolve_lang('fr_FR'), 'fr_FR')
        ui = self.config._ppc_kiosk_env('fr_FR')._ppc_ui_config()
        self.assertEqual(ui['lang']['code'], 'fr_FR')
        self.assertEqual({l['code'] for l in ui['languages']}, {'en_US', 'fr_FR'})

    def test_rtl_language_direction(self):
        lang = self.env['res.lang']._activate_lang('ar_001')
        self.config.lang_ids = [Command.link(lang.id)]
        ui = self.config._ppc_kiosk_env('ar_001')._ppc_ui_config()
        self.assertEqual(ui['lang']['direction'], 'rtl')

    def test_history_summaries(self):
        ids = [self.red_m.id, self.hidden_product.id, 'abc', self.red_s.id]
        summaries = self.kiosk._ppc_product_summaries(ids)
        self.assertEqual([s['product_id'] for s in summaries], [self.red_m.id, self.red_s.id],
                         "Order is kept, forbidden or invalid ids are dropped")
        self.assertNotIn('[', summaries[0]['name'], "No [reference] prefix in names")

    def test_constraints(self):
        with self.assertRaises(ValidationError):
            self.config.clear_delay = -1
        with self.assertRaises(ValidationError):
            self.config.history_limit = 51
        with self.assertRaises(ValidationError):
            self.config.product_domain = "[('not_a_field', '=', 1)]"
        with self.assertRaises(ValidationError):
            self.config.primary_color = 'purple'
        with self.assertRaises(ValidationError):
            self.config.write({'search_barcode': False, 'search_packaging': False,
                               'search_default_code': False, 'search_name': False})
