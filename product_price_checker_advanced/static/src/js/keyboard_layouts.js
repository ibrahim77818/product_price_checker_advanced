/** @odoo-module **/
/**
 * On-screen keyboard layouts, chosen from the kiosk language.
 *
 * Product references and barcodes are usually Latin/ASCII, so non-Latin
 * layouts expose a quick switch to the Latin one (see ``hasLatinSwitch``).
 * To support another language, add an entry keyed by its ISO 639-1 prefix.
 */

const QWERTY = [
    ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
    ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"],
    ["a", "s", "d", "f", "g", "h", "j", "k", "l", "-"],
    ["z", "x", "c", "v", "b", "n", "m", ".", "/"],
];

const AZERTY = [
    ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
    ["a", "z", "e", "r", "t", "y", "u", "i", "o", "p"],
    ["q", "s", "d", "f", "g", "h", "j", "k", "l", "m"],
    ["w", "x", "c", "v", "b", "n", "é", "è", "-", "."],
];

const QWERTZ = [
    ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
    ["q", "w", "e", "r", "t", "z", "u", "i", "o", "p", "ü"],
    ["a", "s", "d", "f", "g", "h", "j", "k", "l", "ö", "ä"],
    ["y", "x", "c", "v", "b", "n", "m", "ß", "-", "."],
];

const ARABIC = [
    ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
    ["ض", "ص", "ث", "ق", "ف", "غ", "ع", "ه", "خ", "ح", "ج"],
    ["ش", "س", "ي", "ب", "ل", "ا", "ت", "ن", "م", "ك", "ط"],
    ["ئ", "ء", "ؤ", "ر", "ى", "ة", "و", "ز", "ظ", "د", "ذ"],
];

const NUMERIC = [
    ["7", "8", "9"],
    ["4", "5", "6"],
    ["1", "2", "3"],
    ["-", "0", "."],
];

const LAYOUTS = {
    en: { rows: QWERTY, latin: true },
    fr: { rows: AZERTY, latin: true },
    de: { rows: QWERTZ, latin: true },
    ar: { rows: ARABIC, latin: false },
};

/**
 * @param {string} langCode e.g. "ar_001", "fr_FR"
 * @returns {{rows: string[][], latin: boolean}}
 */
export function layoutForLang(langCode) {
    const prefix = (langCode || "en").split(/[_-]/)[0].toLowerCase();
    return LAYOUTS[prefix] || LAYOUTS.en;
}

export const LATIN_LAYOUT = LAYOUTS.en;
export const NUMERIC_LAYOUT = { rows: NUMERIC, latin: true };
