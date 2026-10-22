/** @odoo-module **/

import { localization } from "@web/core/l10n/localization";

/**
 * Format a stock quantity with the separators of the kiosk language
 * (the localization service is loaded before the kiosk is mounted).
 *
 * @param {number} value
 * @returns {string}
 */
export function formatQty(value) {
    const number = Number(value) || 0;
    const rounded = Math.round(number * 100) / 100;
    const [intPart, decPart] = Math.abs(rounded).toString().split(".");
    let decimalPoint = ".";
    let thousandsSep = ",";
    try {
        decimalPoint = localization.decimalPoint;
        thousandsSep = localization.thousandsSep;
    } catch {
        // localization not ready (should not happen once mounted): keep defaults
    }
    if (typeof decimalPoint !== "string") {
        decimalPoint = ".";
    }
    if (typeof thousandsSep !== "string") {
        thousandsSep = ",";
    }
    const grouped = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, thousandsSep);
    const sign = rounded < 0 ? "-" : "";
    return sign + grouped + (decPart ? decimalPoint + decPart : "");
}

/**
 * Pick the variant best matching ``wantedValueIds``.
 *
 * Exact match first; otherwise the variant containing ``mustHave`` that shares
 * the most values with the wanted combination (so toggling one attribute keeps
 * as many of the other selections as possible).
 *
 * @param {Array<{id: number, value_ids: number[]}>} variants
 * @param {number[]} wantedValueIds
 * @param {number} mustHave
 * @returns {Object|undefined}
 */
export function findBestVariant(variants, wantedValueIds, mustHave) {
    let best;
    let bestScore = -1;
    for (const variant of variants) {
        const values = new Set(variant.value_ids);
        if (mustHave && !values.has(mustHave)) {
            continue;
        }
        const score = wantedValueIds.filter((id) => values.has(id)).length;
        if (score === wantedValueIds.length && values.size === wantedValueIds.length) {
            return variant;
        }
        if (score > bestScore) {
            best = variant;
            bestScore = score;
        }
    }
    return best;
}

/** Preload images so that switching variants is instantaneous. */
export function preloadImages(urls) {
    for (const url of new Set(urls)) {
        const img = new Image();
        img.decoding = "async";
        img.src = url;
    }
}
