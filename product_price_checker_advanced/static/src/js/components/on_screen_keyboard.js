/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { LATIN_LAYOUT, NUMERIC_LAYOUT, layoutForLang } from "../keyboard_layouts";

/**
 * Touch keyboard. Its alphabetic layout follows the kiosk language; Latin and
 * numeric layouts are one tap away (references and barcodes are Latin).
 */
export class OnScreenKeyboard extends Component {
    static template = "product_price_checker_advanced.OnScreenKeyboard";
    static props = {
        lang: String,
        onKey: Function,
        onBackspace: Function,
        onClear: Function,
        onEnter: Function,
        onClose: Function,
    };

    setup() {
        this.langLayout = layoutForLang(this.props.lang);
        this.state = useState({ mode: "lang", shift: false });
    }

    get layout() {
        if (this.state.mode === "numeric") {
            return NUMERIC_LAYOUT;
        }
        return this.state.mode === "latin" ? LATIN_LAYOUT : this.langLayout;
    }

    get showLatinSwitch() {
        return !this.langLayout.latin;
    }

    /** Keep the focus (and caret) in the search field while typing. */
    onPointerDown(ev) {
        ev.preventDefault();
    }

    keyLabel(key) {
        return this.state.shift ? key.toLocaleUpperCase() : key;
    }

    press(key) {
        this.props.onKey(this.keyLabel(key));
        if (this.state.shift) {
            this.state.shift = false;
        }
    }

    setMode(mode) {
        this.state.mode = this.state.mode === mode ? "lang" : mode;
    }

    toggleShift() {
        this.state.shift = !this.state.shift;
    }
}
