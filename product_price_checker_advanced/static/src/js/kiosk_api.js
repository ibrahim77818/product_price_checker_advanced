/** @odoo-module **/
/**
 * Minimal JSON-RPC client for the kiosk endpoints.
 *
 * The kiosk runs for a public (non logged-in) user and only talks to its own
 * token-scoped routes, so it does not need the full web client RPC stack.
 * Each call carries the current language so product names, attribute values
 * and formatted prices come back translated.
 */

export class KioskRPCError extends Error {
    constructor(message, { status = 0, aborted = false, exceptionName = "" } = {}) {
        super(message);
        this.name = "KioskRPCError";
        this.status = status;
        this.aborted = aborted;
        this.exceptionName = exceptionName;
    }

    /** The kiosk token is unknown (regenerated) or the kiosk was archived. */
    get isInvalidKiosk() {
        return this.status === 404 || this.exceptionName.endsWith("NotFound");
    }
}

let rpcId = 0;

/**
 * @param {string} url
 * @param {Object} params
 * @param {{signal?: AbortSignal, timeout?: number}} [options]
 */
export async function kioskRpc(url, params = {}, { signal, timeout = 15000 } = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    const onAbort = () => controller.abort();
    if (signal) {
        if (signal.aborted) {
            controller.abort();
        }
        signal.addEventListener("abort", onAbort);
    }
    try {
        const response = await fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ jsonrpc: "2.0", method: "call", id: ++rpcId, params }),
            signal: controller.signal,
        });
        if (!response.ok) {
            throw new KioskRPCError(response.statusText || "HTTP error", { status: response.status });
        }
        const payload = await response.json();
        if (payload.error) {
            const data = payload.error.data || {};
            throw new KioskRPCError(data.message || payload.error.message, {
                status: 200,
                exceptionName: data.name || "",
            });
        }
        return payload.result;
    } catch (error) {
        if (error.name === "AbortError") {
            throw new KioskRPCError("aborted", { aborted: true });
        }
        throw error instanceof KioskRPCError ? error : new KioskRPCError(error.message);
    } finally {
        clearTimeout(timer);
        if (signal) {
            signal.removeEventListener("abort", onAbort);
        }
    }
}

/**
 * Typed facade over the kiosk routes of one kiosk/language.
 */
export class KioskAPI {
    /**
     * @param {string} baseUrl  e.g. "/product_checker/token/<token>"
     * @param {string} lang     e.g. "ar_001"
     */
    constructor(baseUrl, lang) {
        this.baseUrl = baseUrl;
        this.lang = lang;
    }

    _call(route, params, options) {
        return kioskRpc(`${this.baseUrl}/${route}`, { ...params, lang: this.lang }, options);
    }

    search(query, options) {
        return this._call("search", { query }, options);
    }

    product({ templateId = false, productId = false }, options) {
        return this._call("product", { template_id: templateId, product_id: productId }, options);
    }

    stock(productId, options) {
        return this._call("stock", { product_id: productId }, options);
    }

    history(productIds, options) {
        return this._call("history", { product_ids: productIds }, options);
    }

    languageUrl(langCode) {
        return `${this.baseUrl}?lang=${encodeURIComponent(langCode)}`;
    }
}
