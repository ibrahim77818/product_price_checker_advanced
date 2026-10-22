/** @odoo-module **/

import { Component, onMounted, useExternalListener, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { KioskAPI } from "../kiosk_api";
import { KioskHistory } from "../kiosk_history";
import { useBarcodeWedge, useIdleCountdown } from "../kiosk_hooks";
import { preloadImages } from "../kiosk_utils";
import { CameraScanner, isCameraScanSupported } from "./camera_scanner";
import { IdleScreen } from "./idle_screen";
import { LanguageSwitcher } from "./language_switcher";
import { OnScreenKeyboard } from "./on_screen_keyboard";
import { ProductView } from "./product_view";
import { ResultsList } from "./results_list";
import { SearchBar } from "./search_bar";

/** Stock older than this is refetched when a variant is displayed again. */
const STOCK_TTL_MS = 30000;

/**
 * Root of the kiosk. Owns the screen state machine:
 *
 *   idle -> loading -> product | results | none | error -> (auto-clear) idle
 */
export class KioskApp extends Component {
    static template = "product_price_checker_advanced.KioskApp";
    static components = {
        CameraScanner,
        IdleScreen,
        LanguageSwitcher,
        OnScreenKeyboard,
        ProductView,
        ResultsList,
        SearchBar,
    };
    static props = { config: Object };

    setup() {
        const config = this.props.config;
        this.config = config;
        this.api = new KioskAPI(config.baseUrl, config.lang.code);
        this.historyStore = new KioskHistory(config.id, config.historyLimit);
        this.cameraAvailable = config.cameraEnabled && isCameraScanSupported();
        this.stockFetchedAt = {};
        this.pending = null; // AbortController of the running search/product call

        this.state = useState({
            view: "idle",
            query: "",
            lastQuery: "",
            results: [],
            product: null,
            selectedVariantId: 0,
            stock: {},
            stockLoading: false,
            history: config.historyEnabled ? this.historyStore.load() : [],
            keyboardOpen: false,
            cameraOpen: false,
            error: "",
            focusToken: 0,
            progress: 0,
        });

        this.idle = useIdleCountdown(this.state, config.clearDelay, () => this.onIdle());
        useBarcodeWedge((code) => this.search(code));
        useExternalListener(window, "keydown", (ev) => {
            if (ev.key === "Escape") {
                this.clear();
            }
        });
        onMounted(() => this.refreshHistory());
    }

    // ------------------------------------------------------------------
    // Getters
    // ------------------------------------------------------------------
    get showStock() {
        return this.config.stockDisplay !== "hidden";
    }

    get currentStock() {
        return this.state.stock[this.state.selectedVariantId] || false;
    }

    get rootClass() {
        return {
            o_ppc_rtl: this.config.lang.direction === "rtl",
            o_ppc_keyboard_open: this.state.keyboardOpen,
            [`o_ppc_view_${this.state.view}`]: true,
        };
    }

    get rootStyle() {
        const bg = this.config.backgroundUrl;
        return bg ? `--ppc-background: url('${bg}');` : "";
    }

    // ------------------------------------------------------------------
    // Search & navigation
    // ------------------------------------------------------------------
    _newRequest() {
        if (this.pending) {
            this.pending.abort();
        }
        this.pending = new AbortController();
        return this.pending.signal;
    }

    async search(rawQuery) {
        const query = (rawQuery || "").trim();
        if (!query) {
            return;
        }
        if (query.length < this.config.minChars) {
            this._showMessage("none", _t("Please type at least %s characters.").replace("%s", this.config.minChars));
            return;
        }
        const signal = this._newRequest();
        this.state.view = "loading";
        this.state.lastQuery = query;
        this.state.cameraOpen = false;
        try {
            const result = await this.api.search(query, { signal });
            this.state.query = "";
            if (result.status === "found") {
                this.state.results = [];
                this._showProduct(result.product);
            } else if (result.status === "multiple") {
                this.state.results = result.results;
                this.state.view = "results";
                this.idle.start();
            } else if (result.status === "too_short") {
                this._showMessage("none", _t("Please type a longer search."));
            } else {
                this._showMessage("none", "");
            }
        } catch (error) {
            this._handleError(error);
        }
        this.state.focusToken++;
    }

    async openResult(result) {
        const signal = this._newRequest();
        this.state.view = "loading";
        try {
            const payload = await this.api.product(
                { templateId: result.template_id, productId: result.product_id },
                { signal }
            );
            if (payload) {
                this._showProduct(payload);
            } else {
                this._showMessage("none", "");
            }
        } catch (error) {
            this._handleError(error);
        }
    }

    openHistory(entry) {
        return this.openResult({ template_id: entry.templateId, product_id: entry.productId });
    }

    backToResults() {
        this.state.view = "results";
        this.state.product = null;
        this.idle.start();
    }

    _showProduct(payload) {
        this.state.product = payload;
        this.state.selectedVariantId = payload.selected_variant_id;
        if (payload.stock) {
            this.state.stock[payload.selected_variant_id] = payload.stock;
            this.stockFetchedAt[payload.selected_variant_id] = Date.now();
        }
        this.state.view = "product";
        preloadImages(payload.variants.map((v) => v.image_url));
        this._pushHistory();
        this.idle.start();
    }

    _showMessage(view, message) {
        this.state.view = view;
        this.state.error = message;
        this.idle.start();
    }

    _handleError(error) {
        if (error && error.aborted) {
            return; // superseded by a newer request
        }
        if (error && error.isInvalidKiosk) {
            this._showMessage("error", _t("This kiosk link is no longer valid. Please contact the store staff."));
        } else {
            this._showMessage("error", _t("The connection to the server failed. Please try again."));
        }
    }

    // ------------------------------------------------------------------
    // Variants & stock
    // ------------------------------------------------------------------
    selectVariant(variantId) {
        if (!this.state.product || variantId === this.state.selectedVariantId) {
            return;
        }
        this.state.selectedVariantId = variantId;
        this._pushHistory();
        const fetchedAt = this.stockFetchedAt[variantId] || 0;
        if (this.showStock && Date.now() - fetchedAt > STOCK_TTL_MS) {
            this.loadStock(variantId);
        }
    }

    async loadStock(productId) {
        if (this.stockRequest) {
            this.stockRequest.abort();
        }
        this.stockRequest = new AbortController();
        this.state.stockLoading = true;
        try {
            const stock = await this.api.stock(productId, { signal: this.stockRequest.signal });
            this.state.stock[productId] = stock;
            this.stockFetchedAt[productId] = Date.now();
            this.state.stockLoading = false;
        } catch (error) {
            if (!error.aborted) {
                this.state.stockLoading = false;
            }
        }
    }

    // ------------------------------------------------------------------
    // History
    // ------------------------------------------------------------------
    _pushHistory() {
        if (!this.config.historyEnabled || !this.state.product) {
            return;
        }
        const { template, variants } = this.state.product;
        const variant = variants.find((v) => v.id === this.state.selectedVariantId) || variants[0];
        const primary = variant.prices[0] || {};
        this.state.history = this.historyStore.push(this.state.history, {
            productId: variant.id,
            templateId: template.id,
            name: variant.display_name,
            imageUrl: variant.image_url,
            priceFmt: primary.price_fmt || "",
        });
    }

    /** Re-fetch names/prices in the current language (history survives lang switches). */
    async refreshHistory() {
        const ids = this.state.history.map((entry) => entry.productId);
        if (!ids.length) {
            return;
        }
        try {
            const summaries = await this.api.history(ids);
            const entries = summaries.map((s) => ({
                productId: s.product_id,
                templateId: s.template_id,
                name: s.name,
                imageUrl: s.image_url,
                priceFmt: s.price_fmt,
            }));
            this.historyStore.save(entries);
            this.state.history = entries;
        } catch {
            // Keep the cached entries.
        }
    }

    clearHistory() {
        this.state.history = this.historyStore.clear();
    }

    // ------------------------------------------------------------------
    // Idle / reset
    // ------------------------------------------------------------------
    clear() {
        if (this.pending) {
            this.pending.abort();
        }
        this.idle.stop();
        Object.assign(this.state, {
            view: "idle",
            query: "",
            results: [],
            product: null,
            selectedVariantId: 0,
            error: "",
            cameraOpen: false,
        });
        this.state.focusToken++;
    }

    onIdle() {
        this.state.keyboardOpen = false;
        this.clear();
        const { lang, defaultLang, resetLangOnIdle } = this.config;
        if (resetLangOnIdle && defaultLang && lang.code !== defaultLang) {
            window.location.assign(this.api.languageUrl(defaultLang));
        }
    }

    switchLanguage(code) {
        window.location.assign(this.api.languageUrl(code));
    }

    // ------------------------------------------------------------------
    // Input helpers (search bar, on-screen keyboard, camera)
    // ------------------------------------------------------------------
    onQueryInput(value) {
        this.state.query = value;
    }

    toggleKeyboard() {
        this.state.keyboardOpen = !this.state.keyboardOpen;
        this.state.focusToken++;
    }

    onKeyboardKey(char) {
        this.state.query += char;
    }

    onKeyboardBackspace() {
        this.state.query = this.state.query.slice(0, -1);
    }

    onKeyboardClear() {
        this.state.query = "";
    }

    onKeyboardEnter() {
        this.search(this.state.query);
    }

    openCamera() {
        this.state.cameraOpen = true;
    }

    closeCamera() {
        this.state.cameraOpen = false;
        this.state.focusToken++;
    }

    onCameraDetected(code) {
        this.state.cameraOpen = false;
        this.search(code);
    }
}
