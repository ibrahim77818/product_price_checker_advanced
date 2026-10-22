/** @odoo-module **/
/**
 * Session history of the products looked up on a kiosk.
 *
 * Stored in ``sessionStorage`` (scoped per kiosk), so it survives the page
 * reload done when switching language but disappears with the browser
 * session. Storage access is wrapped: private modes may throw.
 */

export class KioskHistory {
    /**
     * @param {number|string} kioskId
     * @param {number} limit
     */
    constructor(kioskId, limit) {
        this.key = `product_price_checker_advanced.history.${kioskId}`;
        this.limit = Math.max(0, limit || 0);
    }

    /** @returns {Array<Object>} */
    load() {
        try {
            const raw = window.sessionStorage.getItem(this.key);
            const entries = raw ? JSON.parse(raw) : [];
            return Array.isArray(entries) ? entries.slice(0, this.limit) : [];
        } catch {
            return [];
        }
    }

    save(entries) {
        try {
            window.sessionStorage.setItem(this.key, JSON.stringify(entries.slice(0, this.limit)));
        } catch {
            // Storage full or unavailable: history is a convenience, ignore.
        }
    }

    /**
     * Put ``entry`` first, de-duplicated by product (or template) id.
     *
     * @param {Array<Object>} entries
     * @param {{productId: number, templateId: number}} entry
     * @returns {Array<Object>} the new list (also persisted)
     */
    push(entries, entry) {
        const next = [
            entry,
            ...entries.filter(
                (e) => e.productId !== entry.productId && e.templateId !== entry.templateId
            ),
        ].slice(0, this.limit);
        this.save(next);
        return next;
    }

    clear() {
        try {
            window.sessionStorage.removeItem(this.key);
        } catch {
            // ignore
        }
        return [];
    }
}
