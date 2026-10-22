/** @odoo-module **/
/**
 * Kiosk tour (see tests/test_ui.py for the data):
 * scan a variant barcode, navigate the attribute matrix (including an
 * unavailable combination), check the multi-location stock and the
 * variants x warehouses matrix, then the session history.
 */
import tour from "web_tour.tour";

tour.register("product_price_checker_advanced_tour", { test: true }, [
    {
        content: "The kiosk is mounted",
        trigger: ".o_ppc_root.o_ppc_ready .o_ppc_idle",
        run() {},
    },
    {
        content: "Scan the Red / M barcode",
        trigger: ".o_ppc_search_input",
        run: "text PPCREDM0001",
    },
    {
        content: "Submit",
        trigger: ".o_ppc_search_btn",
    },
    {
        content: "The scanned variant is pre-selected",
        trigger: ".o_ppc_product_name:contains('PPC Test Tee')",
        extra_trigger: ".o_ppc_default_code:contains('PPC-RED-M')",
        run() {},
    },
    {
        content: "Size M has its price extra",
        trigger: ".o_ppc_price:contains('110')",
        run() {},
    },
    {
        content: "Shelf 1: 7 on hand - 2 reserved = 5 available",
        trigger: ".o_ppc_stock_loc[data-location-name$='PPC Shelf 1'] .o_ppc_available:contains('5')",
        run() {},
    },
    {
        content: "Second warehouse is listed",
        trigger: ".o_ppc_stock_wh[data-warehouse-code='PPC2'] .o_ppc_available:contains('5')",
        run() {},
    },
    {
        content: "Total available across warehouses",
        trigger: ".o_ppc_stock_total .o_ppc_available:contains('14')",
        run() {},
    },
    {
        content: "Switch colour to Blue (Blue / M does not exist)",
        trigger: ".o_ppc_value[data-value-name='Blue']",
    },
    {
        content: "Closest existing variant Blue / S is selected, reference and price follow",
        trigger: ".o_ppc_default_code:contains('PPC-BLU-S')",
        extra_trigger: ".o_ppc_price:contains('100')",
        run() {},
    },
    {
        content: "M is flagged unavailable with Blue",
        trigger: ".o_ppc_value.o_ppc_unavailable[data-value-name='M']",
        run() {},
    },
    {
        content: "Blue / S has no stock",
        trigger: ".o_ppc_stock_total .o_ppc_status_out",
        run() {},
    },
    {
        content: "Pick the unavailable M: jump back to Red / M",
        trigger: ".o_ppc_value.o_ppc_unavailable[data-value-name='M']",
    },
    {
        content: "Red / M again",
        trigger: ".o_ppc_default_code:contains('PPC-RED-M')",
        run() {},
    },
    {
        content: "Open the variants x warehouses matrix",
        trigger: ".o_ppc_tab_variants",
    },
    {
        content: "The current variant is highlighted",
        trigger: ".o_ppc_matrix_row.o_ppc_selected:contains('Red, M')",
        run() {},
    },
    {
        content: "Select Red / S from the matrix",
        trigger: ".o_ppc_matrix_row:contains('Red, S')",
    },
    {
        content: "Red / S is displayed",
        trigger: ".o_ppc_default_code:contains('PPC-RED-S')",
        extra_trigger: ".o_ppc_matrix_row.o_ppc_selected:contains('Red, S')",
        run() {},
    },
    {
        content: "Back to the home screen",
        trigger: ".o_ppc_brand",
    },
    {
        content: "The product is in the session history",
        trigger: ".o_ppc_history_item:contains('PPC Test Tee')",
    },
    {
        content: "History opens the product again",
        trigger: ".o_ppc_default_code:contains('PPC-RED-S')",
        run() {},
    },
]);
