/** @odoo-module **/

import { Component, onWillUnmount, useState } from "@odoo/owl";

/**
 * Welcome screen with the promotional slideshow and the session history.
 */
export class IdleScreen extends Component {
    static template = "product_price_checker_advanced.IdleScreen";
    static props = {
        config: Object,
        history: Array,
        onOpenHistory: Function,
        onClearHistory: Function,
    };

    setup() {
        this.state = useState({ slide: 0 });
        const { promos, promoInterval } = this.props.config;
        if (promos.length > 1) {
            const timer = setInterval(() => {
                this.state.slide = (this.state.slide + 1) % promos.length;
            }, Math.max(2, promoInterval) * 1000);
            onWillUnmount(() => clearInterval(timer));
        }
    }
}
