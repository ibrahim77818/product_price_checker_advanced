/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { formatQty } from "../kiosk_utils";

/**
 * Multi-location inventory of the selected variant.
 *
 * Tab 1: warehouses (and their locations in "per location" mode) for the
 *        selected variant.
 * Tab 2: variants x warehouses matrix; tapping a row selects that variant.
 */
export class StockMatrix extends Component {
    static template = "product_price_checker_advanced.StockMatrix";
    static props = {
        stock: { type: [Object, Boolean], optional: true },
        loading: { type: Boolean, optional: true },
        selectedVariantId: Number,
        onSelectVariant: Function,
    };

    setup() {
        this.state = useState({ tab: "locations" });
        this.formatQty = formatQty;
    }

    get showQuantities() {
        return this.props.stock && this.props.stock.qty_mode === "quantity";
    }

    statusLabel(status) {
        return {
            in: _t("In stock"),
            low: _t("Low stock"),
            out: _t("Out of stock"),
        }[status];
    }

    cellText(cell) {
        return this.showQuantities ? formatQty(cell.available) : this.statusLabel(cell.status);
    }

    selectTab(tab) {
        this.state.tab = tab;
    }
}
