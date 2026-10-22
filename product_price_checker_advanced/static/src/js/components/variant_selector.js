/** @odoo-module **/

import { Component } from "@odoo/owl";
import { findBestVariant } from "../kiosk_utils";

/**
 * Interactive attribute matrix (e.g. Colour x Size).
 *
 * All variants are known client-side, so the selector is purely
 * computational: every value is rendered as
 *   - "selected"     part of the current variant,
 *   - "available"    combinable with the other current selections,
 *   - "unavailable"  exists, but not with the other current selections
 *                    (still clickable: we jump to the closest existing variant).
 */
export class VariantSelector extends Component {
    static template = "product_price_checker_advanced.VariantSelector";
    static props = {
        attributes: Array,
        variants: Array,
        selectedVariantId: Number,
        onSelect: Function,
    };

    get currentVariant() {
        return this.props.variants.find((v) => v.id === this.props.selectedVariantId)
            || this.props.variants[0];
    }

    /** Selected value id of ``attribute`` in the current variant. */
    selectedValueId(attribute) {
        const ids = new Set(attribute.values.map((v) => v.id));
        return this.currentVariant.value_ids.find((id) => ids.has(id));
    }

    /** The current combination where ``attribute`` takes ``valueId``. */
    _combinationWith(attribute, valueId) {
        const attributeValueIds = new Set(attribute.values.map((v) => v.id));
        return [
            ...this.currentVariant.value_ids.filter((id) => !attributeValueIds.has(id)),
            valueId,
        ];
    }

    valueState(attribute, value) {
        if (value.id === this.selectedValueId(attribute)) {
            return "selected";
        }
        const wanted = this._combinationWith(attribute, value.id);
        const exists = this.props.variants.some((variant) =>
            wanted.every((id) => variant.value_ids.includes(id))
        );
        return exists ? "available" : "unavailable";
    }

    selectedValueName(attribute) {
        const id = this.selectedValueId(attribute);
        const value = attribute.values.find((v) => v.id === id);
        return value ? value.name : "";
    }

    onClickValue(attribute, value) {
        if (value.id === this.selectedValueId(attribute)) {
            return;
        }
        const variant = findBestVariant(
            this.props.variants,
            this._combinationWith(attribute, value.id),
            value.id
        );
        if (variant) {
            this.props.onSelect(variant.id);
        }
    }

    /** Light text on dark swatches, dark text on light ones. */
    swatchStyle(value) {
        return value.html_color ? `background-color: ${value.html_color};` : "";
    }
}
