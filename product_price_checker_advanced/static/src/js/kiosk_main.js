/** @odoo-module **/
/**
 * Kiosk entry point.
 *
 * The page is rendered with ``web.frontend_layout``: the public root starts
 * the standard services, including the localization service which loads the
 * translations of the language given by ``<html lang>``. We wait for it, then
 * mount our own OWL application with ``translateFn: _t`` so every text of the
 * kiosk templates is translated at compile time.
 */

import { App, whenReady } from "@odoo/owl";
import { templates } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import publicRootReady from "@web/legacy/js/public/public_root_instance";
import { KioskApp } from "./components/kiosk_app";

export async function startKiosk() {
    await whenReady();
    const root = document.getElementById("o_ppc_root");
    if (!root) {
        return null;
    }
    await publicRootReady;
    const config = JSON.parse(root.dataset.config);
    const app = new App(KioskApp, {
        templates,
        props: { config },
        dev: Boolean(odoo.debug),
        translateFn: _t,
        translatableAttributes: ["data-tooltip"],
    });
    root.replaceChildren();
    await app.mount(root);
    root.classList.add("o_ppc_ready");
    return app;
}

startKiosk();
