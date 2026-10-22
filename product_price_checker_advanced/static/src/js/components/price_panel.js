/** @odoo-module **/

import { Component } from "@odoo/owl";

/**
 * Prices of the current variant: the first pricelist is the "big" price, the
 * other ones are listed below (members price, wholesale...).
 */
export class PricePanel extends Component {
    static template = "product_price_checker_advanced.PricePanel";
    static props = {
        prices: Array,
    };

    get primary() {
        return this.props.prices[0];
    }

    get secondary() {
        return this.props.prices.slice(1);
    }
}
