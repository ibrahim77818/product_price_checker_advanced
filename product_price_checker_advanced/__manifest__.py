# -*- coding: utf-8 -*-
# Part of product_price_checker_advanced. License LGPL-3.0 (https://www.gnu.org/licenses/lgpl-3.0.html).
{
    'name': 'Product Price Checker Kiosk',
    'version': '16.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Token-secured, touch-friendly price checker kiosk with variant matrix, '
               'multi-pricelist prices, multi-location stock and multi-language UI',
    'description': """
Product Price Checker Kiosk
===========================
A standalone web kiosk (no login) for retail stores and warehouses:

* Unique secret token per kiosk (``/product_checker/token/<token>``), regenerable at any time.
* Barcode scanner (keyboard wedge), camera scanning, manual search and on-screen keyboard.
* Interactive variant matrix: switching attributes updates image, prices, reference and description instantly.
* Several pricelists per kiosk, with discount detection and tax-included / excluded display.
* Real-time stock per warehouse or per location, plus a variants x warehouses matrix.
* Session history, idle auto-clear and promotional slideshow.
* Multi-language kiosk with RTL support and per-language on-screen keyboard layouts.
    """,
    'author': 'Ibrahim Yahia',
    'website': 'https://www.linkedin.com/in/ibrahim-yahia',
    'license': 'LGPL-3',
    # http_routing: frontend translations hook (see models/ir_http.py).
    'depends': ['stock', 'http_routing'],
    'data': [
        'security/product_checker_security.xml',
        'security/ir.model.access.csv',
        'views/product_checker_config_views.xml',
        'views/product_checker_menus.xml',
        'views/kiosk_templates.xml',
    ],
    'demo': [
        'demo/product_checker_demo.xml',
    ],
    'assets': {
        # Dedicated bundle, loaded only by the kiosk page (on top of web.assets_frontend).
        'product_price_checker_advanced.assets_kiosk': [
            'product_price_checker_advanced/static/src/scss/kiosk.scss',
            'product_price_checker_advanced/static/src/js/**/*.js',
            'product_price_checker_advanced/static/src/xml/**/*.xml',
        ],
        'web.assets_tests': [
            'product_price_checker_advanced/static/tests/tours/**/*.js',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
}
