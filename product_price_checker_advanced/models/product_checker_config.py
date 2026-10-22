# -*- coding: utf-8 -*-
# Part of product_price_checker_advanced. License LGPL-3.0 (https://www.gnu.org/licenses/lgpl-3.0.html).
"""Price checker kiosk configuration.

Design notes
------------
* Every kiosk is identified by an unguessable token (``secrets.token_urlsafe``).
  The public controller resolves the token, then works in ``sudo`` **but only
  through the ``_ppc_*`` methods below**, which whitelist the data that leaves
  the server (no generic read is ever exposed to the public).
* All kiosk business logic lives in this model ("fat model / thin controller"),
  so it can be unit-tested without HTTP and reused by other modules.
* Methods prefixed with ``_ppc_`` expect to be called on a single record that
  already carries the right company and ``lang`` in its environment
  (see ``_ppc_kiosk_env``).
"""
import hashlib
import logging
import secrets

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import float_compare, float_is_zero
from odoo.tools.misc import formatLang
from odoo.tools.safe_eval import datetime as safe_datetime, safe_eval

_logger = logging.getLogger(__name__)

KIOSK_ROUTE = '/product_checker/token/%s'
MAX_QUERY_LENGTH = 128


def _generate_token():
    """Return a URL-safe, 256-bit random token."""
    return secrets.token_urlsafe(32)


class ProductCheckerConfig(models.Model):
    _name = 'product.checker.config'
    _description = 'Price Checker Kiosk'
    _order = 'sequence, id'

    # ------------------------------------------------------------------
    # General
    # ------------------------------------------------------------------
    name = fields.Char(required=True, translate=False)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        'res.company', required=True, index=True,
        default=lambda self: self.env.company)
    token = fields.Char(
        string='Access Token', required=True, readonly=True, copy=False,
        index=True, default=lambda self: _generate_token(),
        groups='product_price_checker_advanced.group_price_checker_manager')
    kiosk_url = fields.Char(
        string='Kiosk URL', compute='_compute_kiosk_url',
        groups='product_price_checker_advanced.group_price_checker_manager',
        help='Public URL of the kiosk. Anyone with this link can look up prices '
             'and stock, so share it only with your store devices.')

    # ------------------------------------------------------------------
    # Pricing
    # ------------------------------------------------------------------
    pricelist_line_ids = fields.One2many(
        'product.checker.pricelist', 'config_id', string='Pricelists', copy=True,
        help='Prices displayed on the kiosk. The first line is the main (big) price.')
    price_tax_mode = fields.Selection(
        [('included', 'Tax Included'), ('excluded', 'Tax Excluded')],
        string='Displayed Prices', default='included', required=True,
        help='Applied when the Invoicing/Accounting module is installed and '
             'the product has customer taxes.')
    show_discount = fields.Boolean(
        string='Show Original Price', default=True,
        help='Strike through the list price when a pricelist gives a lower price.')
    taxes_available = fields.Boolean(compute='_compute_taxes_available')

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    search_barcode = fields.Boolean(string='Search by Barcode', default=True)
    search_packaging = fields.Boolean(string='Search by Packaging Barcode', default=True)
    search_default_code = fields.Boolean(string='Search by Internal Reference', default=True)
    search_name = fields.Boolean(string='Search by Product Name', default=True)
    search_min_chars = fields.Integer(string='Minimum Characters', default=2)
    search_limit = fields.Integer(string='Max. Results', default=24)
    product_domain = fields.Char(
        string='Products Filter', default="[('sale_ok', '=', True)]",
        help='Only products matching this domain can be looked up on the kiosk.')

    # ------------------------------------------------------------------
    # Inventory
    # ------------------------------------------------------------------
    stock_display = fields.Selection(
        [('hidden', 'Hidden'),
         ('warehouse', 'Per Warehouse'),
         ('location', 'Per Location')],
        string='Stock Breakdown', default='location', required=True)
    stock_qty_mode = fields.Selection(
        [('quantity', 'Exact Quantities'), ('status', 'Availability Status')],
        string='Stock Display', default='quantity', required=True,
        help='Availability status shows "In stock / Low stock / Out of stock" '
             'instead of exact quantities.')
    low_stock_threshold = fields.Float(
        string='Low Stock Threshold', default=5.0, digits='Product Unit of Measure')
    warehouse_ids = fields.Many2many(
        'stock.warehouse', string='Warehouses',
        domain="[('company_id', '=', company_id)]",
        help='Leave empty to include every warehouse of the company.')
    location_ids = fields.Many2many(
        'stock.location', string='Locations',
        domain="[('usage', '=', 'internal'), ('company_id', 'in', [company_id, False])]",
        help='Optional. When set, the breakdown shows exactly these locations '
             '(each one including its children) instead of every location holding stock.')
    show_variant_matrix = fields.Boolean(
        string='Variants x Warehouses Matrix', default=True,
        help='For products with variants, also show the stock of every variant per warehouse.')

    # ------------------------------------------------------------------
    # Product details
    # ------------------------------------------------------------------
    show_default_code = fields.Boolean(string='Show Internal Reference', default=True)
    show_barcode = fields.Boolean(string='Show Barcode', default=True)
    show_description = fields.Boolean(string='Show Sales Description', default=True)
    show_category = fields.Boolean(string='Show Category', default=False)

    # ------------------------------------------------------------------
    # Appearance
    # ------------------------------------------------------------------
    welcome_title = fields.Char(
        translate=True, default=lambda self: _('Check a price'))
    welcome_subtitle = fields.Char(
        translate=True,
        default=lambda self: _('Scan a barcode or search for a product'))
    primary_color = fields.Char(default='#714B67')
    logo = fields.Image(max_width=512, max_height=512, help='Defaults to the company logo.')
    background_image = fields.Image(max_width=1920, max_height=1920)
    promo_ids = fields.One2many('product.checker.promo', 'config_id', string='Promotions', copy=True)
    promo_interval = fields.Integer(string='Slide Duration (s)', default=6)

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------
    clear_delay = fields.Integer(
        string='Auto-clear After (s)', default=20,
        help='Seconds of inactivity after which the result is cleared. 0 disables it.')
    history_enabled = fields.Boolean(string='Session History', default=True)
    history_limit = fields.Integer(default=8)
    keyboard_enabled = fields.Boolean(string='On-screen Keyboard', default=True)
    camera_enabled = fields.Boolean(
        string='Camera Scanning', default=True,
        help='Uses the browser BarcodeDetector API when the device supports it.')

    # ------------------------------------------------------------------
    # Languages
    # ------------------------------------------------------------------
    lang_ids = fields.Many2many(
        'res.lang', string='Kiosk Languages',
        domain="[('active', '=', True)]",
        default=lambda self: self.env['res.lang'].search([]),
        help='Languages offered on the kiosk language switcher.')
    default_lang_id = fields.Many2one(
        'res.lang', string='Default Language',
        domain="[('active', '=', True)]",
        default=lambda self: self.env['res.lang']._lang_get(self.env.lang or 'en_US'))
    reset_lang_on_idle = fields.Boolean(
        string='Back to Default Language When Idle', default=True)

    _sql_constraints = [
        ('token_unique', 'unique(token)', 'The kiosk token must be unique.'),
    ]

    # ==================================================================
    # Compute / constraints / CRUD
    # ==================================================================
    @api.depends('token')
    def _compute_kiosk_url(self):
        base_url = self.get_base_url() if self else ''
        for config in self:
            config.kiosk_url = base_url + KIOSK_ROUTE % config.token if config.token else False

    def _compute_taxes_available(self):
        available = 'taxes_id' in self.env['product.product']._fields
        for config in self:
            config.taxes_available = available

    @api.constrains('clear_delay', 'history_limit', 'search_min_chars', 'search_limit',
                    'low_stock_threshold', 'promo_interval')
    def _check_positive_values(self):
        for config in self:
            if config.clear_delay < 0:
                raise ValidationError(_('The auto-clear delay cannot be negative.'))
            if not 0 <= config.history_limit <= 50:
                raise ValidationError(_('The history limit must be between 0 and 50.'))
            if config.search_min_chars < 1:
                raise ValidationError(_('The minimum number of characters must be at least 1.'))
            if not 1 <= config.search_limit <= 100:
                raise ValidationError(_('The maximum number of results must be between 1 and 100.'))
            if config.low_stock_threshold < 0:
                raise ValidationError(_('The low stock threshold cannot be negative.'))
            if config.promo_interval < 2:
                raise ValidationError(_('A promotion slide must last at least 2 seconds.'))

    @api.constrains('search_barcode', 'search_packaging', 'search_default_code', 'search_name')
    def _check_search_methods(self):
        for config in self:
            if not (config.search_barcode or config.search_packaging
                    or config.search_default_code or config.search_name):
                raise ValidationError(_('Enable at least one search method.'))

    @api.constrains('product_domain')
    def _check_product_domain(self):
        for config in self:
            try:
                domain = config._ppc_eval_domain()
                self.env['product.product'].search_count(domain)
            except Exception as error:
                raise ValidationError(
                    _('The products filter is invalid: %s', error)) from error

    @api.constrains('default_lang_id', 'lang_ids')
    def _check_default_lang(self):
        for config in self:
            if config.default_lang_id and config.lang_ids \
                    and config.default_lang_id not in config.lang_ids:
                raise ValidationError(
                    _('The default language must be one of the kiosk languages.'))

    @api.constrains('primary_color')
    def _check_primary_color(self):
        for config in self:
            color = config.primary_color
            if color and not (len(color) in (4, 7) and color.startswith('#')
                              and all(c in '0123456789abcdefABCDEF' for c in color[1:])):
                raise ValidationError(_('The primary color must be a hex color such as #714B67.'))

    def copy(self, default=None):
        default = dict(default or {}, name=_('%s (copy)', self.name), token=_generate_token())
        return super().copy(default)

    # ==================================================================
    # Actions
    # ==================================================================
    def action_regenerate_token(self):
        """Invalidate the current URL: devices using the old link stop working."""
        for config in self:
            config.token = _generate_token()
        return True

    def action_open_kiosk(self):
        self.ensure_one()
        if not self.active:
            raise UserError(_('Archived kiosks cannot be opened.'))
        return {
            'type': 'ir.actions.act_url',
            'url': KIOSK_ROUTE % self.token,
            'target': 'new',
        }

    # ==================================================================
    # Kiosk helpers (public side). Called on sudo()-ed, token-resolved records.
    # ==================================================================
    @api.model
    def _ppc_get_by_token(self, token):
        """Return the active kiosk matching ``token`` (sudo) or an empty recordset."""
        if not token or not isinstance(token, str) or len(token) > 128:
            return self.browse()
        config = self.sudo().search([('token', '=', token)], limit=1)
        # Constant-time comparison, defence in depth against timing attacks.
        if config and secrets.compare_digest(config.token, token):
            return config
        return self.browse()

    def _ppc_allowed_langs(self):
        self.ensure_one()
        return self.lang_ids.filtered('active') or self.env['res.lang'].search([])

    def _ppc_resolve_lang(self, requested=None):
        """Return the language code to use: requested if allowed, else the default one."""
        self.ensure_one()
        langs = self._ppc_allowed_langs()
        codes = langs.mapped('code')
        if requested and requested in codes:
            return requested
        if self.default_lang_id.active and self.default_lang_id.code in codes:
            return self.default_lang_id.code
        return codes[0] if codes else 'en_US'

    def _ppc_kiosk_env(self, lang=None):
        """Return this kiosk in the environment used for every public request."""
        self.ensure_one()
        lang_code = self._ppc_resolve_lang(lang)
        return self.sudo().with_company(self.company_id).with_context(
            lang=lang_code, active_test=True)

    def _ppc_eval_domain(self):
        self.ensure_one()
        eval_context = {
            'uid': self.env.uid,
            'datetime': safe_datetime,
            'context_today': safe_datetime.datetime.today,
            'company_id': self.company_id.id,
        }
        domain = safe_eval(self.product_domain or '[]', eval_context)
        if not isinstance(domain, (list, tuple)):
            raise ValueError(_('A domain must be a list.'))
        return list(domain)

    def _ppc_product_domain(self):
        """Products the kiosk is allowed to show."""
        self.ensure_one()
        return expression.AND([
            self._ppc_eval_domain(),
            [('company_id', 'in', [False, self.company_id.id])],
        ])

    def _ppc_pricelists(self):
        """Return [(pricelist, label)] in display order, with a sensible fallback."""
        self.ensure_one()
        lines = self.pricelist_line_ids.filtered(
            lambda l: l.pricelist_id.active
            and l.pricelist_id.company_id in (self.company_id, self.env['res.company']))
        result = [(line.pricelist_id, line.label or line.pricelist_id.name)
                  for line in lines.sorted('sequence')]
        if not result:
            fallback = self.env['product.pricelist'].search(
                [('company_id', 'in', [False, self.company_id.id])], limit=1)
            if fallback:
                result = [(fallback, fallback.name)]
        return result

    def _ppc_format_amount(self, amount, currency):
        return formatLang(self.env, amount, currency_obj=currency)

    def _ppc_price_with_taxes(self, product, price, currency):
        """Apply the configured tax display to a unit price (no-op without account)."""
        if 'taxes_id' not in product._fields:
            return price
        taxes = product.taxes_id.filtered(lambda t: t.company_id == self.company_id)
        if not taxes:
            return price
        res = taxes.compute_all(price, currency=currency, quantity=1.0, product=product)
        return res['total_included'] if self.price_tax_mode == 'included' else res['total_excluded']

    def _ppc_prices(self, products):
        """Return {product_id: [price dict per pricelist]} for ``products``.

        Prices of all variants are computed in one batch per pricelist, so the
        frontend can switch variants without any extra round-trip.
        """
        self.ensure_one()
        today = fields.Date.context_today(self)
        result = {product.id: [] for product in products}
        for index, (pricelist, label) in enumerate(self._ppc_pricelists()):
            currency = pricelist.currency_id
            rule_prices = pricelist._compute_price_rule(products, 1.0)
            for product in products:
                price = rule_prices.get(product.id, (product.lst_price, False))[0]
                list_price = product.currency_id._convert(
                    product.lst_price, currency, self.company_id, today)
                price = self._ppc_price_with_taxes(product, price, currency)
                list_price = self._ppc_price_with_taxes(product, list_price, currency)
                discount = 0.0
                if self.show_discount and float_compare(
                        price, list_price, precision_rounding=currency.rounding) < 0 \
                        and not float_is_zero(list_price, precision_rounding=currency.rounding):
                    discount = round((list_price - price) / list_price * 100.0)
                result[product.id].append({
                    'pricelist_id': pricelist.id,
                    'label': label,
                    'is_primary': index == 0,
                    'price': currency.round(price),
                    'price_fmt': self._ppc_format_amount(price, currency),
                    'list_price': currency.round(list_price),
                    'list_price_fmt': self._ppc_format_amount(list_price, currency) if discount else '',
                    'discount': discount,
                })
        return result

    def _ppc_image_url(self, product, size=512):
        """Cache-busted URL of the product image served by the kiosk controller."""
        stamp = '%s-%s' % (product.write_date, product.product_tmpl_id.write_date)
        unique = hashlib.sha1(stamp.encode()).hexdigest()[:10]
        return '%s/image/%s/%s?unique=%s' % (KIOSK_ROUTE % self.token, product.id, size, unique)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def _ppc_search(self, query):
        """Look up products for the kiosk.

        Exact matches (variant barcode, packaging barcode, internal reference)
        win and open the product directly; otherwise a fuzzy search returns a
        list of templates.

        :returns: dict with ``status`` in ``found`` / ``multiple`` / ``none``
                  / ``too_short``.
        """
        self.ensure_one()
        query = (query or '').strip()[:MAX_QUERY_LENGTH]
        if len(query) < self.search_min_chars:
            return {'status': 'too_short'}
        Product = self.env['product.product']
        domain = self._ppc_product_domain()

        # 1) Exact matches open the variant directly.
        exact = Product.browse()
        if self.search_barcode:
            exact = Product.search(expression.AND([domain, [('barcode', '=', query)]]), limit=2)
        if not exact and self.search_packaging:
            packagings = self.env['product.packaging'].search([('barcode', '=', query)], limit=5)
            exact = packagings.product_id.filtered_domain(domain)[:2]
        if not exact and self.search_default_code:
            exact = Product.search(
                expression.AND([domain, [('default_code', '=ilike', query)]]), limit=2)
        if len(exact) == 1:
            return {'status': 'found', 'match': 'exact',
                    'product': self._ppc_product_payload(exact)}

        # 2) Fuzzy search, grouped by template.
        fuzzy = []
        if self.search_name:
            # Names are translatable: match them in every kiosk language, so a
            # customer can type an English name while the UI is in Arabic.
            name_ids = set()
            for lang_code in self._ppc_allowed_langs().mapped('code'):
                name_ids.update(Product.with_context(lang=lang_code).search(
                    expression.AND([domain, [('name', 'ilike', query)]]),
                    limit=self.search_limit * 5).ids)
            fuzzy.append([('id', 'in', list(name_ids))])
        if self.search_default_code:
            fuzzy.append([('default_code', 'ilike', query)])
        if self.search_barcode:
            fuzzy.append([('barcode', 'ilike', query)])
        if not fuzzy:
            return {'status': 'none', 'query': query}
        products = exact or Product.search(
            expression.AND([domain, expression.OR(fuzzy)]), limit=self.search_limit * 5)
        templates = products.product_tmpl_id[:self.search_limit]
        if not templates:
            return {'status': 'none', 'query': query}
        if len(templates) == 1:
            variant = products if len(products) == 1 else None
            return {'status': 'found', 'match': 'fuzzy',
                    'product': self._ppc_product_payload(variant, template=templates)}
        return {
            'status': 'multiple',
            'query': query,
            'results': self._ppc_template_summaries(templates, products),
        }

    def _ppc_template_summaries(self, templates, matched_products):
        """Light-weight cards for a list of templates (search results)."""
        first_variant = {}
        for product in matched_products:
            first_variant.setdefault(product.product_tmpl_id.id, product)
        variants = self.env['product.product'].concat(
            *[first_variant[t.id] for t in templates])
        prices = self._ppc_prices(variants)
        results = []
        for template in templates:
            product = first_variant[template.id]
            primary = (prices.get(product.id) or [{}])[0]
            results.append({
                'template_id': template.id,
                'product_id': product.id if template.product_variant_count == 1 else False,
                'name': template.name,
                'default_code': (product.default_code or '') if self.show_default_code else '',
                'variant_count': template.product_variant_count,
                'image_url': self._ppc_image_url(product, 128),
                'price_fmt': primary.get('price_fmt', ''),
            })
        return results

    def _ppc_product_summaries(self, product_ids):
        """Refresh history entries in the current language (drops forbidden products)."""
        self.ensure_one()
        ids = [int(pid) for pid in (product_ids or []) if str(pid).isdigit()][:50]
        products = self.env['product.product'].search(
            expression.AND([self._ppc_product_domain(), [('id', 'in', ids)]]))
        prices = self._ppc_prices(products)
        by_id = {
            product.id: {
                'product_id': product.id,
                'template_id': product.product_tmpl_id.id,
                'name': self._ppc_product_label(product),
                'image_url': self._ppc_image_url(product, 128),
                'price_fmt': (prices.get(product.id) or [{}])[0].get('price_fmt', ''),
            } for product in products
        }
        return [by_id[pid] for pid in ids if pid in by_id]

    # ------------------------------------------------------------------
    # Product payload (variant matrix)
    # ------------------------------------------------------------------
    @api.model
    def _ppc_matrix_lines(self, template):
        """Attribute lines that generate variants ("never" attributes are sale options)."""
        return template.valid_product_template_attribute_line_ids.filtered(
            lambda l: l.attribute_id.create_variant != 'no_variant')

    @api.model
    def _ppc_sort_variants(self, variants):
        """Order variants like the attribute matrix (attribute, then value sequence)."""
        if len(variants) < 2:
            return variants
        lines = self._ppc_matrix_lines(variants[0].product_tmpl_id)
        position = {
            value.id: (line_index, value_index)
            for line_index, line in enumerate(lines)
            for value_index, value in enumerate(line.product_template_value_ids)
        }
        return variants.sorted(lambda v: sorted(
            position.get(value.id, (99, 0)) for value in v.product_template_attribute_value_ids))

    @api.model
    def _ppc_product_label(self, product):
        """Display name without the [reference] prefix (shown separately)."""
        return product.with_context(display_default_code=False).display_name

    def _ppc_product_payload(self, product=None, template=None):
        """Everything the kiosk needs to render a template and all its variants.

        :param product: product.product to pre-select (optional)
        :param template: product.template, deduced from ``product`` if omitted
        """
        self.ensure_one()
        template = template or product.product_tmpl_id
        template.ensure_one()
        variants = self._ppc_sort_variants(self.env['product.product'].search(expression.AND([
            self._ppc_product_domain(), [('product_tmpl_id', '=', template.id)],
        ])))
        if not variants:
            return False
        if not product or product not in variants:
            product = variants[0]

        # Only attributes that actually generate variants belong to the matrix;
        # "never" (no_variant) attributes are sale-time options.
        used_values = variants.product_template_attribute_value_ids
        attributes = []
        lines = self._ppc_matrix_lines(template)
        for line in lines:
            values = line.product_template_value_ids.filtered(lambda v: v in used_values)
            if not values:
                continue
            attributes.append({
                'id': line.id,
                'name': line.attribute_id.name,
                'display_type': line.attribute_id.display_type,
                'values': [{
                    'id': value.id,
                    'name': value.name,
                    'html_color': value.html_color or False,
                } for value in values],
            })
        line_ids = set(lines.ids)

        prices = self._ppc_prices(variants)
        variant_data = []
        for variant in variants:
            ptavs = variant.product_template_attribute_value_ids.filtered(
                lambda v: v.attribute_line_id.id in line_ids)
            variant_data.append({
                'id': variant.id,
                'value_ids': ptavs.ids,
                'display_name': self._ppc_product_label(variant),
                'variant_label': ptavs._get_combination_name(),
                'default_code': (variant.default_code or '') if self.show_default_code else '',
                'barcode': (variant.barcode or '') if self.show_barcode else '',
                'image_url': self._ppc_image_url(variant, 512),
                'image_zoom_url': self._ppc_image_url(variant, 1024),
                'prices': prices[variant.id],
            })

        return {
            'template': {
                'id': template.id,
                'name': template.name,
                'description': (template.description_sale or '') if self.show_description else '',
                'category': template.categ_id.display_name if self.show_category else '',
                'uom': template.uom_id.name,
            },
            'attributes': attributes,
            'variants': variant_data,
            'selected_variant_id': product.id,
            'stock': self._ppc_stock(product),
        }

    # ------------------------------------------------------------------
    # Stock matrix
    # ------------------------------------------------------------------
    def _ppc_warehouses(self):
        self.ensure_one()
        warehouses = self.warehouse_ids.filtered(lambda w: w.company_id == self.company_id)
        return warehouses or self.env['stock.warehouse'].search(
            [('company_id', '=', self.company_id.id)])

    def _ppc_status(self, available):
        if float_compare(available, 0.0, precision_digits=3) <= 0:
            return 'out'
        if float_compare(available, self.low_stock_threshold, precision_digits=3) <= 0:
            return 'low'
        return 'in'

    def _ppc_qty_cell(self, on_hand, reserved):
        """A matrix cell. Exact quantities are omitted in 'status' mode (not just hidden)."""
        available = on_hand - reserved
        cell = {'status': self._ppc_status(available)}
        if self.stock_qty_mode == 'quantity':
            cell.update(on_hand=round(on_hand, 3), available=round(available, 3))
        return cell

    def _ppc_stock(self, product):
        """Real-time stock of ``product`` (and of its sibling variants).

        One ``read_group`` on ``stock.quant`` (grouped by product and location)
        feeds both the location breakdown of the selected variant and the
        variants x warehouses matrix.
        """
        self.ensure_one()
        if self.stock_display == 'hidden' or product.type != 'product':
            return False
        warehouses = self._ppc_warehouses()
        if not warehouses:
            return False

        siblings = product
        with_matrix = self.show_variant_matrix and product.product_tmpl_id.product_variant_count > 1
        if with_matrix:
            siblings = self._ppc_sort_variants(self.env['product.product'].search(expression.AND([
                self._ppc_product_domain(),
                [('product_tmpl_id', '=', product.product_tmpl_id.id)],
            ])))
            with_matrix = len(siblings) > 1

        scope_locations = self.location_ids.filtered(
            lambda l: l.usage == 'internal' and l.warehouse_id in warehouses)
        scope = scope_locations or warehouses.view_location_id
        groups = self.env['stock.quant'].read_group(
            [('product_id', 'in', siblings.ids),
             ('location_id', 'child_of', scope.ids),
             ('location_id.usage', '=', 'internal')],
            ['quantity:sum', 'reserved_quantity:sum'],
            ['product_id', 'location_id'], lazy=False)

        Location = self.env['stock.location']
        quants = {}  # {product_id: {location: (qty, reserved)}}
        for group in groups:
            location = Location.browse(group['location_id'][0])
            per_location = quants.setdefault(group['product_id'][0], {})
            qty, reserved = per_location.get(location, (0.0, 0.0))
            per_location[location] = (qty + group['quantity'], reserved + group['reserved_quantity'])

        def sum_where(per_location, predicate):
            qty = reserved = 0.0
            for location, (q, r) in per_location.items():
                if predicate(location):
                    qty += q
                    reserved += r
            return qty, reserved

        def in_location(parent):
            return lambda loc: (loc.parent_path or '').startswith(parent.parent_path or '/')

        selected = quants.get(product.id, {})
        warehouse_rows = []
        total_qty = total_reserved = 0.0
        for warehouse in warehouses:
            wh_qty, wh_reserved = sum_where(selected, lambda loc, w=warehouse: loc.warehouse_id == w)
            total_qty += wh_qty
            total_reserved += wh_reserved
            row = {
                'id': warehouse.id,
                'name': warehouse.name,
                'code': warehouse.code,
                'locations': [],
                **self._ppc_qty_cell(wh_qty, wh_reserved),
            }
            if self.stock_display == 'location':
                if scope_locations:
                    rows_locations = scope_locations.filtered(lambda l, w=warehouse: l.warehouse_id == w)
                    for location in rows_locations:
                        qty, reserved = sum_where(selected, in_location(location))
                        row['locations'].append(self._ppc_location_row(location, qty, reserved))
                else:
                    for location, (qty, reserved) in sorted(
                            selected.items(), key=lambda item: item[0].complete_name):
                        if location.warehouse_id == warehouse and not float_is_zero(
                                qty, precision_digits=3):
                            row['locations'].append(self._ppc_location_row(location, qty, reserved))
            warehouse_rows.append(row)

        result = {
            'product_id': product.id,
            'mode': self.stock_display,
            'qty_mode': self.stock_qty_mode,
            'uom': product.uom_id.name,
            'warehouses': warehouse_rows,
            'total': self._ppc_qty_cell(total_qty, total_reserved),
            'matrix': False,
        }
        if with_matrix:
            result['matrix'] = {
                'warehouses': [{'id': w.id, 'code': w.code, 'name': w.name} for w in warehouses],
                'rows': [{
                    'product_id': sibling.id,
                    'label': sibling.product_template_attribute_value_ids._get_combination_name()
                    or self._ppc_product_label(sibling),
                    'cells': [
                        self._ppc_qty_cell(*sum_where(
                            quants.get(sibling.id, {}), lambda loc, w=w: loc.warehouse_id == w))
                        for w in warehouses
                    ],
                    'total': self._ppc_qty_cell(*sum_where(quants.get(sibling.id, {}), lambda loc: True)),
                } for sibling in siblings],
            }
        return result

    def _ppc_location_row(self, location, qty, reserved):
        warehouse_prefix = (location.warehouse_id.view_location_id.name or '') + '/'
        name = location.complete_name or location.name
        if name.startswith(warehouse_prefix):
            name = name[len(warehouse_prefix):]
        return {'id': location.id, 'name': name, **self._ppc_qty_cell(qty, reserved)}

    # ------------------------------------------------------------------
    # Front-end bootstrap
    # ------------------------------------------------------------------
    def _ppc_ui_config(self):
        """Settings serialised into the kiosk page (no secret except the token itself)."""
        self.ensure_one()
        lang_code = self.env.lang
        langs = self._ppc_allowed_langs()
        current = langs.filtered(lambda l: l.code == lang_code)[:1] or \
            self.env['res.lang']._lang_get(lang_code)
        base = KIOSK_ROUTE % self.token
        return {
            'id': self.id,
            'name': self.name,
            'baseUrl': base,
            'company': self.company_id.name,
            'logoUrl': base + '/asset/logo',
            'backgroundUrl': (base + '/asset/background') if self.background_image else False,
            'welcomeTitle': self.welcome_title or '',
            'welcomeSubtitle': self.welcome_subtitle or '',
            'primaryColor': self.primary_color or '#714B67',
            'promos': [{
                'id': promo.id,
                'name': promo.name or '',
                'url': '%s/asset/promo/%s?unique=%s' % (
                    base, promo.id, hashlib.sha1(str(promo.write_date).encode()).hexdigest()[:10]),
            } for promo in self.promo_ids.filtered('image')],
            'promoInterval': self.promo_interval,
            'clearDelay': self.clear_delay,
            'historyEnabled': self.history_enabled and self.history_limit > 0,
            'historyLimit': self.history_limit,
            'keyboardEnabled': self.keyboard_enabled,
            'cameraEnabled': self.camera_enabled,
            'minChars': self.search_min_chars,
            'stockDisplay': self.stock_display,
            'lang': {
                'code': lang_code,
                'name': current.name,
                'direction': current.direction or 'ltr',
            },
            'defaultLang': self._ppc_resolve_lang(),
            'resetLangOnIdle': self.reset_lang_on_idle,
            'languages': [{
                'code': lang.code,
                'name': lang.name.split('/')[-1].strip(),
                'iso': (lang.iso_code or lang.code).split('_')[0].upper(),
                'direction': lang.direction,
            } for lang in langs],
        }
