/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

const FORMATS = ["ean_13", "ean_8", "upc_a", "upc_e", "code_128", "code_39", "itf", "qr_code"];

/** True when the browser exposes the native BarcodeDetector API and a camera. */
export function isCameraScanSupported() {
    return (
        typeof window !== "undefined" &&
        "BarcodeDetector" in window &&
        !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)
    );
}

/**
 * Full-screen camera scanner based on the native BarcodeDetector API
 * (Chrome/Edge on Android, ChromeOS, macOS). No third-party library.
 */
export class CameraScanner extends Component {
    static template = "product_price_checker_advanced.CameraScanner";
    static props = {
        onDetected: Function,
        onClose: Function,
    };

    setup() {
        this.videoRef = useRef("video");
        this.state = useState({ error: "" });
        this.stream = null;
        this.stopped = false;

        onMounted(() => this.start());
        onWillUnmount(() => this.stop());
    }

    async start() {
        try {
            const supported = await window.BarcodeDetector.getSupportedFormats();
            const formats = FORMATS.filter((f) => supported.includes(f));
            this.detector = new window.BarcodeDetector({ formats });
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: "environment" },
                audio: false,
            });
            if (this.stopped) {
                this.stop();
                return;
            }
            const video = this.videoRef.el;
            video.srcObject = this.stream;
            await video.play();
            this.loop();
        } catch {
            this.state.error = _t("The camera is not available on this device.");
        }
    }

    async loop() {
        if (this.stopped) {
            return;
        }
        try {
            const codes = await this.detector.detect(this.videoRef.el);
            if (codes.length && codes[0].rawValue) {
                this.stop();
                this.props.onDetected(codes[0].rawValue);
                return;
            }
        } catch {
            // Frame not ready yet: try again on the next frame.
        }
        this.frame = requestAnimationFrame(() => this.loop());
    }

    stop() {
        this.stopped = true;
        cancelAnimationFrame(this.frame);
        if (this.stream) {
            for (const track of this.stream.getTracks()) {
                track.stop();
            }
            this.stream = null;
        }
    }
}
