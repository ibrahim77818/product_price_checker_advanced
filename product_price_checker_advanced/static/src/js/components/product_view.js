/** @odoo-module **/

import { Component } from "@odoo/owl";
import { PricePanel } from "./price_panel";
import { StockMatrix } from "./stock_matrix";
import { VariantSelector } from "./variant_selector";

/**
 * Product sheet: image, identification, prices, variant matrix and stock.
 * Everything derives from the selected variant, so toggling an attribute
 * re-renders image, prices, reference and description at once.
 */
export class ProductView extends Component {
    static template = "product_price_checker_advanced.ProductView";
    static components = { PricePanel, StockMatrix, VariantSelector };
    static props = {
        product: Object,
        selectedVariantId: Number,
        stock: { type: [Object, Boolean], optional: true },
        stockLoading: { type: Boolean, optional: true },
        showStock: Boolean,
        onSelectVariant: Function,
    };

    get variant() {
        const { variants } = this.props.product;
        return variants.find((v) => v.id === this.props.selectedVariantId) || variants[0];
    }

    get hasMatrix() {
        return this.props.product.attributes.some((attribute) => attribute.values.length > 1);
    }
}
