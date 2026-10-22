/** @odoo-module **/

import { Component } from "@odoo/owl";

/** Several templates match a fuzzy search: let the customer pick one. */
export class ResultsList extends Component {
    static template = "product_price_checker_advanced.ResultsList";
    static props = {
        results: Array,
        query: String,
        onOpen: Function,
    };
}
