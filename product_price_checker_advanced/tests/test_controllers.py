# -*- coding: utf-8 -*-
# Part of product_price_checker_advanced. License LGPL-3.0 (https://www.gnu.org/licenses/lgpl-3.0.html).
import json

from odoo.tests import HttpCase, tagged

from .common import PriceCheckerCommon


@tagged('post_install', '-at_install', 'product_price_checker_advanced')
class TestPriceCheckerControllers(PriceCheckerCommon, HttpCase):
    """The public endpoints, called without any session (public user)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.setup_price_checker_data()
        cls.base = '/product_checker/token/%s' % cls.config.token

    def _rpc(self, route, **params):
        response = self.url_open(
            self.base + route,
            data=json.dumps({'jsonrpc': '2.0', 'method': 'call', 'id': 1, 'params': params}),
            headers={'Content-Type': 'application/json'},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_kiosk_page(self):
        response = self.url_open(self.base)
        self.assertEqual(response.status_code, 200)
        self.assertIn('o_ppc_root', response.text)
        self.assertIn('no-store', response.headers.get('Cache-Control', ''))
        self.assertIn('noindex', response.headers.get('X-Robots-Tag', ''))

    def test_kiosk_page_rtl(self):
        lang = self.env['res.lang']._activate_lang('ar_001')
        self.config.lang_ids = [(4, lang.id)]
        response = self.url_open(self.base + '?lang=ar_001')
        self.assertEqual(response.status_code, 200)
        self.assertIn('dir="rtl"', response.text)
        self.assertIn('lang="ar-001"', response.text)

    def test_frontend_translations_include_kiosk_terms(self):
        modules = self.env['ir.http']._get_translation_frontend_modules_name()
        self.assertIn('product_price_checker_advanced', modules,
                      "Public pages only receive the translations of whitelisted modules")

    def test_unknown_token(self):
        self.assertEqual(self.url_open('/product_checker/token/not-a-token').status_code, 404)
        result = self._rpc_raw('/product_checker/token/not-a-token/search', query='PPC-RED-M')
        self.assertIn('error', result)

    def _rpc_raw(self, url, **params):
        return self.url_open(
            url, data=json.dumps({'jsonrpc': '2.0', 'method': 'call', 'params': params}),
            headers={'Content-Type': 'application/json'}).json()

    def test_archived_kiosk(self):
        self.config.active = False
        self.assertEqual(self.url_open(self.base).status_code, 404)

    def test_search_and_product_endpoints(self):
        result = self._rpc('/search', query='PPC-RED-M')['result']
        self.assertEqual(result['status'], 'found')
        self.assertEqual(result['product']['selected_variant_id'], self.red_m.id)
        product = self._rpc('/product', template_id=self.template.id)['result']
        self.assertEqual(product['template']['id'], self.template.id)
        self.assertFalse(self._rpc('/product', product_id=self.hidden_product.id)['result'],
                         "Products outside the kiosk filter cannot be fetched by id")

    def test_stock_endpoint(self):
        stock = self._rpc('/stock', product_id=self.red_m.id)['result']
        self.assertEqual(stock['total']['on_hand'], 16.0)
        self.assertFalse(self._rpc('/stock', product_id=self.hidden_product.id)['result'])

    def test_history_endpoint(self):
        result = self._rpc('/history', product_ids=[self.red_m.id, self.hidden_product.id])['result']
        self.assertEqual([r['product_id'] for r in result], [self.red_m.id])

    def test_images(self):
        ok = self.url_open('%s/image/%s/128' % (self.base, self.red_m.id))
        self.assertEqual(ok.status_code, 200)
        self.assertTrue(ok.headers['Content-Type'].startswith('image/'))
        hidden = self.url_open('%s/image/%s/128' % (self.base, self.hidden_product.id))
        self.assertEqual(hidden.status_code, 404, "Images of non-kiosk products are not served")
        self.assertEqual(self.url_open('%s/image/%s/77' % (self.base, self.red_m.id)).status_code, 404)
        self.assertEqual(self.url_open(self.base + '/asset/logo').status_code, 200)
        self.assertEqual(self.url_open(self.base + '/asset/background').status_code, 404)
