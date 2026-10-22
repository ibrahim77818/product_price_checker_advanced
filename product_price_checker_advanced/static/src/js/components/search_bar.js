/** @odoo-module **/

import { Component, useEffect, useRef } from "@odoo/owl";

/**
 * Search field. The physical scanner types into it (wedge) and ends with
 * Enter, which submits the form. When the on-screen keyboard is open the
 * native virtual keyboard is suppressed with ``inputmode="none"``.
 */
export class SearchBar extends Component {
    static template = "product_price_checker_advanced.SearchBar";
    static props = {
        query: String,
        loading: Boolean,
        keyboardEnabled: Boolean,
        keyboardOpen: Boolean,
        cameraAvailable: Boolean,
        onInput: Function,
        onSubmit: Function,
        onClear: Function,
        onToggleKeyboard: Function,
        onOpenCamera: Function,
        focusToken: Number,
    };

    setup() {
        this.inputRef = useRef("input");
        // Re-focus the field whenever the parent bumps ``focusToken``
        // (after a search, after clearing...), so the next scan lands here.
        useEffect(
            () => {
                const input = this.inputRef.el;
                if (input && document.activeElement !== input) {
                    input.focus({ preventScroll: true });
                }
            },
            () => [this.props.focusToken]
        );
    }

    onSubmit(ev) {
        ev.preventDefault();
        this.props.onSubmit(this.inputRef.el.value);
    }

    onInput(ev) {
        this.props.onInput(ev.target.value);
    }
}
