# -*- coding: utf-8 -*-
# Part of product_price_checker_advanced. License LGPL-3.0 (https://www.gnu.org/licenses/lgpl-3.0.html).
"""Demo data that cannot be expressed in XML (ORM-generated variants, quants)."""
import base64
import logging

from odoo import api, models
from odoo.tools import file_open

_logger = logging.getLogger(__name__)

DEMO_LANGS = ('ar_001', 'fr_FR')

# {xml id: {lang: translation}}
DEMO_TRANSLATIONS = {
    'demo_tmpl_tshirt': {
        'name': {'ar_001': 'تيشيرت قطني كلاسيكي', 'fr_FR': 'T-shirt classique en coton'},
        'description_sale': {
            'ar_001': 'قطن ممشط 100٪، قصة عادية، 180 جم/م². قابل للغسل في الغسالة على 30 درجة.',
            'fr_FR': '100 % coton peigné, coupe droite, 180 g/m². Lavable en machine à 30 °C.'},
    },
    'demo_tmpl_sneaker': {
        'name': {'ar_001': 'حذاء رياضي أوربان رنر', 'fr_FR': 'Baskets Urban Runner'},
        'description_sale': {
            'ar_001': 'جزء علوي محبوك خفيف ونعل EVA مريح. مثالي للمشي اليومي في المدينة.',
            'fr_FR': 'Tige en maille légère, semelle EVA amortissante. Idéales pour la ville.'},
    },
    'demo_product_bottle': {
        'name': {'ar_001': 'قارورة ماء ستانلس 750 مل', 'fr_FR': 'Gourde inox 750 ml'},
        'description_sale': {
            'ar_001': 'عزل مزدوج: بارد 24 ساعة، ساخن 12 ساعة. خالية من BPA.',
            'fr_FR': 'Double paroi isolante : 24 h froid, 12 h chaud. Sans BPA.'},
    },
    'demo_product_earbuds': {
        'name': {'ar_001': 'سماعات لاسلكية برو', 'fr_FR': 'Écouteurs sans fil Pro'},
        'description_sale': {
            'ar_001': 'إلغاء نشط للضوضاء، بطارية 30 ساعة مع علبة الشحن.',
            'fr_FR': 'Réduction de bruit active, 30 h d’autonomie avec le boîtier.'},
    },
    'demo_product_coffee': {
        'name': {'ar_001': 'حبوب قهوة عضوية 1 كجم', 'fr_FR': 'Café en grains bio 1 kg'},
        'description_sale': {
            'ar_001': 'أرابيكا أحادية المصدر، تحميص متوسط.',
            'fr_FR': 'Arabica d’origine unique, torréfaction moyenne.'},
    },
    'demo_attr_color': {'name': {'ar_001': 'اللون', 'fr_FR': 'Couleur'}},
    'demo_attr_color_red': {'name': {'ar_001': 'أحمر', 'fr_FR': 'Rouge'}},
    'demo_attr_color_blue': {'name': {'ar_001': 'أزرق', 'fr_FR': 'Bleu'}},
    'demo_attr_color_black': {'name': {'ar_001': 'أسود', 'fr_FR': 'Noir'}},
    'demo_attr_color_white': {'name': {'ar_001': 'أبيض', 'fr_FR': 'Blanc'}},
    'demo_attr_size': {'name': {'ar_001': 'المقاس', 'fr_FR': 'Taille'}},
    'demo_attr_shoe': {'name': {'ar_001': 'مقاس الحذاء', 'fr_FR': 'Pointure'}},
    'demo_categ_apparel': {'name': {'ar_001': 'ملابس', 'fr_FR': 'Vêtements'}},
    'demo_pricelist_vip': {'name': {'ar_001': 'أعضاء VIP', 'fr_FR': 'Membres VIP'}},
    'demo_kiosk_main': {
        'welcome_title': {'ar_001': 'تحقق من السعر', 'fr_FR': 'Vérifiez un prix'},
        'welcome_subtitle': {'ar_001': 'امسح الباركود أو ابحث عن منتج',
                             'fr_FR': 'Scannez un code-barres ou recherchez un produit'},
    },
    'demo_kiosk_main_pl_public': {'label': {'ar_001': 'السعر', 'fr_FR': 'Prix'}},
    'demo_kiosk_main_pl_vip': {'label': {'ar_001': 'أعضاء VIP', 'fr_FR': 'Membres VIP'}},
    'demo_kiosk_main_promo_season': {
        'name': {'ar_001': 'تشكيلة الموسم الجديد وصلت', 'fr_FR': 'La nouvelle collection est arrivée'}},
    'demo_kiosk_main_promo_members': {
        'name': {'ar_001': 'أعضاء VIP يوفرون 10٪ على كل شيء', 'fr_FR': 'Les membres VIP économisent 10 %'}},
}


def _ean13(base12):
    """Return ``base12`` followed by its EAN-13 check digit."""
    total = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(base12))
    return base12 + str((10 - total % 10) % 10)


class ProductCheckerConfigDemo(models.Model):
    _inherit = 'product.checker.config'

    @api.model
    def _ppc_demo_setup(self):
        """Complete the XML demo data. Only called from the demo XML file."""
        ref = lambda xmlid: self.env.ref('product_price_checker_advanced.%s' % xmlid)

        # -- Variants: references, barcodes, images, price extras --------------
        sequence = iter(range(100, 200))
        variant_images = {}
        for color in ('red', 'blue', 'black'):
            variant_images[('tshirt', color)] = 'tshirt_%s.png' % color
        for color in ('black', 'white', 'red'):
            variant_images[('sneaker', color)] = 'sneaker_%s.png' % color

        for key, prefix in (('tshirt', 'TSH'), ('sneaker', 'RUN')):
            template = ref('demo_tmpl_%s' % key)
            for variant in template.product_variant_ids:
                values = variant.product_template_attribute_value_ids
                color = values.filtered(lambda v: v.attribute_id == ref('demo_attr_color'))
                other = values - color
                color_code = color.product_attribute_value_id.name.lower()
                variant.write({
                    'default_code': '%s-%s-%s' % (prefix, color_code[:3].upper(), other.name),
                    'barcode': _ean13('6281000%05d' % next(sequence)),
                    'image_variant_1920': self._ppc_demo_image(variant_images[(key, color_code)]),
                })
        # +5 for size L, +20 for shoe size 43.
        ref('demo_tmpl_tshirt').attribute_line_ids.product_template_value_ids.filtered(
            lambda v: v.product_attribute_value_id == ref('demo_attr_size_l')).price_extra = 5.0
        ref('demo_tmpl_sneaker').attribute_line_ids.product_template_value_ids.filtered(
            lambda v: v.product_attribute_value_id == ref('demo_attr_shoe_43')).price_extra = 20.0
        # Red sneakers do not exist in 43: demonstrates unavailable combinations.
        ref('demo_tmpl_sneaker').product_variant_ids.filtered(
            lambda p: p.product_template_attribute_value_ids.product_attribute_value_id
            >= (ref('demo_attr_color_red') | ref('demo_attr_shoe_43'))).active = False

        # -- Locations ----------------------------------------------------------
        Location = self.env['stock.location']
        main_wh = self.env.ref('stock.warehouse0')
        downtown, mall = ref('demo_wh_downtown'), ref('demo_wh_mall')
        shelves = {}
        for warehouse, names in ((main_wh, ('Aisle A', 'Aisle B', 'Backroom')),
                                 (downtown, ('Showroom', 'Storage'))):
            for name in names:
                shelves[(warehouse.code, name)] = Location.create({
                    'name': name, 'location_id': warehouse.lot_stock_id.id, 'usage': 'internal'})

        # -- Stock (deterministic spread across locations) ---------------------
        targets = list(shelves.values()) + [mall.lot_stock_id]
        products = (ref('demo_tmpl_tshirt').product_variant_ids
                    | ref('demo_tmpl_sneaker').product_variant_ids
                    | ref('demo_product_bottle') | ref('demo_product_earbuds')
                    | ref('demo_product_coffee'))
        Quant = self.env['stock.quant']
        for p_index, product in enumerate(products):
            for l_index, location in enumerate(targets):
                qty = (p_index * 7 + l_index * 5) % 23
                if qty > 2:
                    Quant._update_available_quantity(product, location, float(qty))

        # -- Languages & translations -------------------------------------------
        Lang = self.env['res.lang']
        for code in DEMO_LANGS:
            try:
                Lang._activate_lang(code)
            except Exception:  # pragma: no cover - missing locale on the host
                _logger.warning('Price checker demo: could not activate %s', code)
        active_codes = Lang.search([]).mapped('code')
        for xmlid, fields_translations in DEMO_TRANSLATIONS.items():
            record = ref(xmlid)
            for field_name, translations in fields_translations.items():
                translations = {k: v for k, v in translations.items() if k in active_codes}
                if translations:
                    record.update_field_translations(field_name, translations)

        kiosks = ref('demo_kiosk_main') | ref('demo_kiosk_warehouse')
        kiosks.write({
            'lang_ids': [(6, 0, Lang.search([('code', 'in', ('en_US',) + DEMO_LANGS)]).ids)],
            'default_lang_id': Lang._lang_get('en_US').id,
        })
        return True

    @api.model
    def _ppc_demo_image(self, filename):
        with file_open('product_price_checker_advanced/static/img/demo/%s' % filename, 'rb') as image:
            return base64.b64encode(image.read())
