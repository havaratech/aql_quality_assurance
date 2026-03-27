function get_multi_select_options(fieldname, txt) {
    return frappe.call({
        method: "aql_quality_assurance.aql_quality_assurance_by_havaratech.report.aql_process_capability_report.aql_process_capability_report.get_filter_options",
        args: { fieldname, txt }
    }).then((r) => {
        return (r.message || []).map((d) => ({
            value: d.value,
            description: d.value
        }));
    });
}


frappe.query_reports["AQL Process Capability Report"] = {
    filters: [
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date",
            reqd: 1
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            reqd: 1
        },
        {
            fieldname: "parameter",
            label: "Parameter",
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                return get_multi_select_options("parameter", txt);
            }
        },
        {
            fieldname: "inspection_template",
            label: "Inspection Template",
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                return get_multi_select_options("inspection_template", txt);
            }
        },
        {
            fieldname: "item_code",
            label: "Item",
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                return get_multi_select_options("item_code", txt);
            }
        },
        {
            fieldname: "supplier",
            label: "Supplier",
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                return get_multi_select_options("supplier", txt);
            }
        }
    ],

    formatter: function(value, row, column, data, default_formatter) {
        if (column.fieldname === "chart_action" && data && data.row_key) {
            return `
                <button class="btn btn-xs btn-primary aql-show-spc-chart" data-row-key="${frappe.utils.escape_html(data.row_key)}">
                    Show Chart
                </button>
            `;
        }

        return default_formatter(value, row, column, data);
    },

    onload: function(report) {
        report.aql_selected_row_key = null;
        attach_chart_click_handler(report);
    },

    after_datatable_render: function(report) {
        attach_chart_click_handler(report);
    },

    refresh: function(report) {
        clear_chart_area(report);
    }
};


function attach_chart_click_handler(report) {
    report.page.wrapper.off("click.aql-spc-chart");
    report.page.wrapper.on("click.aql-spc-chart", ".aql-show-spc-chart", function() {
        const row_key = this.dataset.rowKey;
        if (!row_key) {
            frappe.msgprint("Unable to identify the selected row for chart generation.");
            return;
        }

        report.aql_selected_row_key = row_key;
        render_histogram(report, row_key);
    });
}


function clear_chart_area(report) {
    if (window.aqlSpcSingleChart) {
        window.aqlSpcSingleChart.destroy();
        window.aqlSpcSingleChart = null;
    }

    report.page.wrapper.find("#spcChartSection").remove();
}


function ensure_chart_area(report) {
    clear_chart_area(report);

    report.page.wrapper.find(".layout-main-section").append(`
        <div id="spcChartSection" style="margin-top: 16px; border: 1px solid #d1d8dd; border-radius: 8px; background: #fff; padding: 16px;">
            <div id="spcChartMeta" style="margin-bottom: 16px;"></div>
            <div id="spcChartWrap" style="position: relative;">
                <canvas id="spcChartCanvas" height="120"></canvas>
            </div>
        </div>
    `);
}


function format_metric(value, digits = 3) {
    if (value === null || value === undefined || value === "") {
        return "-";
    }

    const num = Number(value);
    if (Number.isFinite(num)) {
        return num.toFixed(digits);
    }

    return String(value);
}


function render_summary(report, chart_data) {
    const meta_html = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px;">
            <div><strong>Parameter:</strong><br>${frappe.utils.escape_html(chart_data.parameter || "-")}</div>
            <div><strong>Inspection Template:</strong><br>${frappe.utils.escape_html(chart_data.inspection_template || "-")}</div>
            <div><strong>Item:</strong><br>${frappe.utils.escape_html(chart_data.item_code || "-")}</div>
            <div><strong>Supplier:</strong><br>${frappe.utils.escape_html(chart_data.supplier || "-")}</div>
            <div><strong>Sample Size:</strong><br>${format_metric(chart_data.sample_size, 0)}</div>
            <div><strong>Mean:</strong><br>${format_metric(chart_data.mean)}</div>
            <div><strong>Std Dev:</strong><br>${format_metric(chart_data.std_dev)}</div>
            <div><strong>LSL:</strong><br>${format_metric(chart_data.lsl)}</div>
            <div><strong>USL:</strong><br>${format_metric(chart_data.usl)}</div>
            <div><strong>Cp:</strong><br>${format_metric(chart_data.cp)}</div>
            <div><strong>Cpk:</strong><br>${format_metric(chart_data.cpk)}</div>
            <div><strong>Status:</strong><br>${frappe.utils.escape_html(chart_data.status || "-")}</div>
        </div>
    `;

    report.page.wrapper.find("#spcChartMeta").html(meta_html);
}


function render_histogram(report, row_key) {
    const filters = report.get_values ? report.get_values() : frappe.query_report.get_filter_values();
    filters.row_key = row_key;

    frappe.call({
        method: "aql_quality_assurance.aql_quality_assurance_by_havaratech.report.aql_process_capability_report.aql_process_capability_report.get_histogram_data",
        args: { filters }
    }).then((r) => {
        const chart_data = r.message || {};

        if (!chart_data.values || chart_data.values.length < 2) {
            frappe.msgprint("No chart data available for the selected row.");
            clear_chart_area(report);
            return;
        }

        ensure_chart_area(report);
        render_summary(report, chart_data);

        if (typeof Chart === "undefined") {
            frappe.require("https://cdn.jsdelivr.net/npm/chart.js", function() {
                draw_chart(report, chart_data);
            });
            return;
        }

        draw_chart(report, chart_data);
    });
}


function draw_chart(report, chart_data) {
    const values = chart_data.values || [];
    const lsl = Number.isFinite(Number(chart_data.lsl)) ? Number(chart_data.lsl) : null;
    const usl = Number.isFinite(Number(chart_data.usl)) ? Number(chart_data.usl) : null;
    const numeric_limits = [lsl, usl].filter((v) => v !== null);

    if (!values.length) {
        return;
    }

    const raw_min = Math.min(...values, ...(numeric_limits.length ? numeric_limits : [Math.min(...values)]));
    const raw_max = Math.max(...values, ...(numeric_limits.length ? numeric_limits : [Math.max(...values)]));
    const span = raw_max - raw_min;

    if (span <= 0) {
        frappe.msgprint("The selected row does not have enough variation to draw a histogram.");
        clear_chart_area(report);
        return;
    }

    const bins = 10;
    const step = span / bins;
    const freq = new Array(bins).fill(0);
    const labels = [];

    values.forEach((v) => {
        let idx = Math.min(Math.floor((v - raw_min) / step), bins - 1);
        idx = Math.max(0, idx);
        freq[idx] += 1;
    });

    for (let i = 0; i < bins; i++) {
        labels.push((raw_min + i * step).toFixed(2));
    }

    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    const std = Math.sqrt(
        values.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / (values.length - 1)
    );

    let curve = [];
    if (std > 0) {
        for (let i = 0; i < bins; i++) {
            const x = raw_min + i * step;
            const pdf = (1 / (std * Math.sqrt(2 * Math.PI))) *
                Math.exp(-0.5 * Math.pow((x - mean) / std, 2));
            curve.push(pdf * values.length * step);
        }
    } else {
        curve = new Array(bins).fill(null);
    }

    const ctx = document.getElementById("spcChartCanvas");
    if (!ctx) {
        return;
    }

    if (window.aqlSpcSingleChart) {
        window.aqlSpcSingleChart.destroy();
    }

    window.aqlSpcSingleChart = new Chart(ctx, {
        data: {
            labels: labels,
            datasets: [
                {
                    type: "bar",
                    label: "Frequency",
                    data: freq,
                },
                {
                    type: "line",
                    label: "Normal Curve",
                    data: curve,
                    borderWidth: 2,
                    fill: false,
                }
            ]
        },
        options: {
            plugins: {
                title: {
                    display: true,
                    text: `${chart_data.parameter || "Parameter"} SPC Histogram`
                }
            },
            scales: {
                x: {
                    title: { display: true, text: "Measurement" }
                },
                y: {
                    title: { display: true, text: "Frequency" }
                }
            }
        }
    });

    const chart = window.aqlSpcSingleChart;
    const container = document.getElementById("spcChartWrap");
    container.querySelectorAll(".spc-limit-line, .spc-limit-text").forEach((el) => el.remove());

    const left = chart.chartArea.left;
    const right = chart.chartArea.right;
    const top = chart.chartArea.top;
    const bottom = chart.chartArea.bottom;
    const plot_width = right - left;

    function create_line(value, color, label, x_offset = 0) {
        if (value === null || value === undefined || !Number.isFinite(value)) {
            return;
        }

        let pos = left + ((value - raw_min) / span) * plot_width;
        pos = Math.max(left, Math.min(right - 2, pos)) + x_offset;

        const line = document.createElement("div");
        line.className = "spc-limit-line";
        line.style.position = "absolute";
        line.style.left = `${pos}px`;
        line.style.top = `${top}px`;
        line.style.height = `${bottom - top}px`;
        line.style.width = "2px";
        line.style.background = color;
        line.style.zIndex = "5";

        const text = document.createElement("div");
        text.className = "spc-limit-text";
        text.innerText = `${label} (${value})`;
        text.style.position = "absolute";
        text.style.left = `${Math.min(pos, right - 70)}px`;
        text.style.top = `${top + 2}px`;
        text.style.color = color;
        text.style.fontSize = "12px";
        text.style.background = "#fff";
        text.style.zIndex = "6";

        container.appendChild(line);
        container.appendChild(text);
    }

    const overlap = lsl !== null && usl !== null && lsl === usl;
    create_line(lsl, "red", "LSL", overlap ? -3 : 0);
    create_line(usl, "blue", "USL", overlap ? 3 : 0);
}
