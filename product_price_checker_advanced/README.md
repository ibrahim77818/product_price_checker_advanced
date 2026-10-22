# Product Price Checker Kiosk (Odoo 16)

A standalone, token-secured price checker for retail stores and warehouses.
Open the kiosk URL on a tablet, a wall screen or a scanner terminal: customers
scan a barcode (or search) and see prices, variants and stock — no login needed.

## Features

| Area | What it does |
|---|---|
| Security | One unguessable 256-bit token per kiosk (`/product_checker/token/<token>`), regenerable; constant-time lookup; every public call is token-scoped and returns whitelisted data only (`_ppc_*` methods); `noindex`, `no-store`, `no-referrer` headers. |
| Search | Variant barcode, packaging barcode, internal reference (exact match opens the variant), then fuzzy name/reference search across **all kiosk languages**; configurable product filter (domain). |
| Input | Hardware scanners (keyboard wedge, with or without focus), camera scanning (native `BarcodeDetector`, no library), on-screen keyboard with per-language layouts (QWERTY / AZERTY / QWERTZ / Arabic + Latin + numeric). |
| Variant matrix | Attribute selector (colour swatches / pills). All variants are pre-loaded, so switching updates image, prices, reference, barcode and label instantly. Unavailable combinations are flagged and jump to the closest existing variant. "Never" attributes are excluded. |
| Prices | Several ordered pricelists per kiosk (custom translatable labels), discount badge and struck list price, tax included/excluded when Accounting is installed. Server-side formatting in the kiosk language. |
| Stock | Real time from `stock.quant` (on hand, reserved, available): per warehouse, per location, or per configured locations (children aggregated) + a variants × warehouses matrix. "Status only" mode never sends quantities to the browser. |
| Session | History in `sessionStorage` (refreshed in the current language), idle countdown with auto-clear, optional return to the default language, promotional slideshow. |
| Languages | Language switcher, translations through standard `.po` files (Arabic and French included), translated product data, RTL layout built on CSS logical properties. |

## Architecture

```
product_price_checker_advanced/
├── __manifest__.py
├── controllers/main.py            # thin public controller: token -> kiosk env -> _ppc_* methods
├── models/
│   ├── product_checker_config.py  # kiosk settings + all kiosk business logic (search, payload, stock)
│   ├── product_checker_pricelist.py
│   ├── product_checker_promo.py
│   ├── ir_http.py                 # whitelists the module for frontend translations
│   └── product_checker_demo.py    # demo-only helper (variants, quants, translations)
├── security/                      # User / Administrator groups, multi-company rule, ACLs
├── views/                         # backend views & menus, QWeb kiosk page (web.frontend_layout)
├── demo/product_checker_demo.xml
├── i18n/                          # .pot, ar.po, fr.po
├── static/src/
│   ├── js/kiosk_main.js           # mounts the OWL app once the public root (translations) is ready
│   ├── js/kiosk_api.js            # JSON-RPC client with abort/timeout
│   ├── js/kiosk_hooks.js          # barcode wedge + idle countdown hooks
│   ├── js/kiosk_history.js, keyboard_layouts.js, kiosk_utils.js
│   ├── js/components/*.js         # KioskApp, SearchBar, VariantSelector, PricePanel, StockMatrix, ...
│   ├── xml/*.xml                  # OWL templates
│   └── scss/kiosk.scss
├── static/tests/tours/price_checker_tour.js
└── tests/                         # TransactionCase, HttpCase (endpoints) and browser tour
```

### Language switching
`?lang=<code>` on the kiosk URL is validated against the kiosk languages. The
page is rendered in that language (`<html lang dir>`), the standard
localization service loads the module translations, and every JSON call sends
the same language so product data comes back translated. The kiosk root also
carries `dir`, so the layout is correct even where `rtlcss` is not installed.

## Configuration

*Price Checker ▸ Kiosks ▸ New*: choose pricelists, search methods, stock
breakdown, languages and appearance, then **Open Kiosk** or copy the Kiosk URL.
**Regenerate Token** immediately invalidates the previous URL.

Demo kiosks (demo data): `/product_checker/token/demo-price-checker-main-store-token-change-me`
and `/product_checker/token/demo-price-checker-warehouse-token-change-me` —
regenerate their tokens on any database reachable from outside.

## Tests

```bash
odoo-bin -d <db> -i product_price_checker_advanced --test-enable --test-tags /product_price_checker_advanced --stop-after-init
```

38 tests: search & token logic, variant attribute filtering, prices, multi-location
stock calculations (reservations, child locations, warehouse filter, status mode),
public endpoints and a browser tour (scan, variant matrix incl. unavailable
combination, stock matrix, history).

## Notes

* Depends on `stock` and `http_routing` only. Taxes are applied when `account` is installed.
* The kiosk is public by design: anyone holding the URL can read prices and stock of
  the products matching the kiosk filter. Use a reverse-proxy rate limit if the URL
  may be exposed to the internet.
