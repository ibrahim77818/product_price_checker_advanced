/** @odoo-module **/

import { Component, useState, useExternalListener, useRef } from "@odoo/owl";

/**
 * Language picker. Switching reloads the kiosk with ``?lang=``: the server
 * then renders the page with the right translations, number formats and the
 * RTL/LTR variant of the stylesheets.
 */
export class LanguageSwitcher extends Component {
    static template = "product_price_checker_advanced.LanguageSwitcher";
    static props = {
        languages: Array,
        current: Object,
        onSelect: Function,
    };

    setup() {
        this.state = useState({ open: false });
        this.rootRef = useRef("root");
        useExternalListener(window, "pointerdown", (ev) => {
            if (this.state.open && this.rootRef.el && !this.rootRef.el.contains(ev.target)) {
                this.state.open = false;
            }
        });
    }

    get currentIso() {
        const lang = this.props.languages.find((l) => l.code === this.props.current.code);
        return lang ? lang.iso : this.props.current.code.split("_")[0].toUpperCase();
    }

    toggle() {
        this.state.open = !this.state.open;
    }

    select(lang) {
        this.state.open = false;
        if (lang.code !== this.props.current.code) {
            this.props.onSelect(lang.code);
        }
    }
}
