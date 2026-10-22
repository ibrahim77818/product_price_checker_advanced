# -*- coding: utf-8 -*-
# Part of product_price_checker_advanced. License LGPL-3.0 (https://www.gnu.org/licenses/lgpl-3.0.html).
"""Public kiosk endpoints.

Every route is scoped by the kiosk token. The controller only:

1. resolves the token to an active ``product.checker.config`` (404 otherwise),
2. builds the kiosk environment (sudo, kiosk company, requested language),
3. delegates to the whitelisted ``_ppc_*`` model methods.

No generic ORM access is ever exposed to the public user.
"""
import json
import logging

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

BASE = '/product_checker/token/<string:token>'
IMAGE_SIZES = (128, 512, 1024)


class ProductPriceCheckerController(http.Controller):

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _ppc_config(self, token, lang=None):
        """Return the kiosk record in its public environment, or raise 404."""
        config = request.env['product.checker.config']._ppc_get_by_token(token)
        if not config:
            raise NotFound()
        return config._ppc_kiosk_env(lang)

    @staticmethod
    def _ppc_int(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            raise NotFound()

    # ------------------------------------------------------------------
    # Kiosk page
    # ------------------------------------------------------------------
    @http.route(BASE, type='http', auth='public', methods=['GET'], sitemap=False)
    def kiosk(self, token, lang=None, **kwargs):
        config = self._ppc_config(token, lang)
        lang_code = config.env.lang
        # The rendering context language drives QWeb translations and the
        # RTL/LTR variant of the CSS bundles served in the page <head>.
        request.update_context(lang=lang_code)
        ui_config = config._ppc_ui_config()
        values = {
            'config': config,
            'title': config.name,
            'ui_config_json': json.dumps(ui_config),
            'no_header': True,
            'no_footer': True,
            'body_classname': 'o_ppc_body',
            'lang_direction': ui_config['lang']['direction'],
            'html_data': {
                'lang': lang_code.replace('_', '-'),
                'dir': ui_config['lang']['direction'],
                'data-ppc-kiosk': '1',
            },
        }
        response = request.render('product_price_checker_advanced.kiosk_page', values)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Robots-Tag'] = 'noindex, nofollow'
        response.headers['Referrer-Policy'] = 'no-referrer'  # never leak the token
        return response

    # ------------------------------------------------------------------
    # JSON API
    # ------------------------------------------------------------------
    @http.route(BASE + '/search', type='json', auth='public', methods=['POST'])
    def search(self, token, query='', lang=None, **kwargs):
        return self._ppc_config(token, lang)._ppc_search(query)

    @http.route(BASE + '/product', type='json', auth='public', methods=['POST'])
    def product(self, token, template_id=None, product_id=None, lang=None, **kwargs):
        config = self._ppc_config(token, lang)
        domain = config._ppc_product_domain()
        if product_id:
            product = config.env['product.product'].search(
                domain + [('id', '=', self._ppc_int(product_id))], limit=1)
            if not product:
                return False
            return config._ppc_product_payload(product)
        template = config.env['product.template'].browse(self._ppc_int(template_id)).exists()
        if not template:
            return False
        return config._ppc_product_payload(template=template)

    @http.route(BASE + '/stock', type='json', auth='public', methods=['POST'])
    def stock(self, token, product_id=None, lang=None, **kwargs):
        config = self._ppc_config(token, lang)
        product = config.env['product.product'].search(
            config._ppc_product_domain() + [('id', '=', self._ppc_int(product_id))], limit=1)
        return config._ppc_stock(product) if product else False

    @http.route(BASE + '/history', type='json', auth='public', methods=['POST'])
    def history(self, token, product_ids=None, lang=None, **kwargs):
        return self._ppc_config(token, lang)._ppc_product_summaries(product_ids or [])

    # ------------------------------------------------------------------
    # Binary content
    # ------------------------------------------------------------------
    @http.route(BASE + '/image/<int:product_id>/<int:size>', type='http',
                auth='public', methods=['GET'], sitemap=False)
    def image(self, token, product_id, size=512, unique=None, **kwargs):
        if size not in IMAGE_SIZES:
            raise NotFound()
        config = self._ppc_config(token)
        product = config.env['product.product'].search(
            config._ppc_product_domain() + [('id', '=', product_id)], limit=1)
        if not product:
            raise NotFound()
        stream = request.env['ir.binary']._get_image_stream_from(
            product, 'image_%s' % size)
        return stream.get_response(immutable=bool(unique))

    @http.route([BASE + '/asset/<string:kind>',
                 BASE + '/asset/<string:kind>/<int:record_id>'],
                type='http', auth='public', methods=['GET'], sitemap=False)
    def asset(self, token, kind, record_id=None, unique=None, **kwargs):
        config = self._ppc_config(token)
        if kind == 'logo':
            record, field = (config, 'logo') if config.logo else (config.company_id, 'logo')
        elif kind == 'background' and config.background_image:
            record, field = config, 'background_image'
        elif kind == 'promo' and record_id:
            record = config.promo_ids.filtered(lambda p: p.id == record_id)
            field = 'image'
            if not record:
                raise NotFound()
        else:
            raise NotFound()
        stream = request.env['ir.binary']._get_image_stream_from(record, field)
        return stream.get_response(immutable=bool(unique))
