/** @odoo-module **/

import { onWillUnmount, useExternalListener } from "@odoo/owl";

/**
 * Detect hardware barcode scanners working as "keyboard wedges".
 *
 * Scanners type very fast (a few ms per character) and end with Enter. When
 * the search input has the focus the browser handles it natively (the form is
 * submitted), so this hook only collects keystrokes typed *outside* inputs,
 * e.g. while the result screen is displayed.
 *
 * @param {(code: string) => void} onScan
 * @param {{maxInterval?: number, minLength?: number}} [options]
 */
export function useBarcodeWedge(onScan, { maxInterval = 60, minLength = 3 } = {}) {
    let buffer = "";
    let lastTime = 0;

    useExternalListener(window, "keydown", (ev) => {
        const target = ev.target;
        if (
            target &&
            (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable)
        ) {
            return;
        }
        const now = performance.now();
        if (now - lastTime > maxInterval) {
            buffer = "";
        }
        lastTime = now;
        if (ev.key === "Enter" || ev.key === "Tab") {
            if (buffer.length >= minLength) {
                ev.preventDefault();
                onScan(buffer);
            }
            buffer = "";
        } else if (ev.key.length === 1 && !ev.ctrlKey && !ev.metaKey && !ev.altKey) {
            buffer += ev.key;
        }
    });
}

/**
 * Inactivity countdown driving the auto-clear of the result screen.
 *
 * The countdown is (re)started with ``start()`` and reset by any user
 * activity. ``state.progress`` (1 -> 0) can be bound to a progress bar.
 *
 * @param {Object} state      reactive object receiving ``progress``
 * @param {number} delaySec   0 disables the timer
 * @param {() => void} onExpire
 */
export function useIdleCountdown(state, delaySec, onExpire) {
    const delay = (delaySec || 0) * 1000;
    let deadline = 0;
    let interval = null;

    const stop = () => {
        if (interval) {
            clearInterval(interval);
            interval = null;
        }
        state.progress = 0;
    };
    const tick = () => {
        const remaining = deadline - Date.now();
        if (remaining <= 0) {
            stop();
            onExpire();
        } else {
            state.progress = remaining / delay;
        }
    };
    const start = () => {
        if (!delay) {
            return;
        }
        deadline = Date.now() + delay;
        state.progress = 1;
        if (!interval) {
            interval = setInterval(tick, 200);
        }
    };
    const touch = () => {
        if (interval) {
            start();
        }
    };
    for (const name of ["pointerdown", "keydown", "wheel", "touchmove"]) {
        useExternalListener(window, name, touch, { capture: true, passive: true });
    }
    onWillUnmount(stop);
    return { start, stop, touch };
}
