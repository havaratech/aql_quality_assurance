function get_multi_select_options(fieldname, txt) {
    return frappe.call({
        method: "aql_quality_assurance.aql_quality_assurance_by_havaratech.report.aql_process_capability_result.aql_process_capability_result.get_filter_options",
        args: { fieldname, txt }
    }).then((r) => {
        return (r.message || []).map((d) => ({
            value: d.value,
            description: d.value
        }));
    });
}


frappe.query_reports["AQL Process Capability Result"] = {
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
    report.page.wrapper.off("click.aql-spc-chart-result");
    report.page.wrapper.on("click.aql-spc-chart-result", ".aql-show-spc-chart", function() {
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
    if (window.aqlSpcResultChart) {
        window.aqlSpcResultChart.destroy();
        window.aqlSpcResultChart = null;
    }

    report.page.wrapper.find("#spcResultSection").remove();
}


function ensure_chart_area(report) {
    clear_chart_area(report);

    report.page.wrapper.find(".layout-main-section").append(`
        <div id="spcResultSection" style="margin-top: 16px; border: 1px solid #d1d8dd; border-radius: 8px; background: #fff; padding: 16px;">
            <div id="spcResultMeta" style="margin-bottom: 16px;"></div>
            <div id="spcResultLegend" style="display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; font-size: 12px;"></div>
            <div id="spcResultChartWrap" style="position: relative; min-height: 320px;"></div>
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

    const legend_html = `
        <span><strong style="color: #5e64ff;">Frequency</strong> histogram</span>
        <span><strong style="color: #2490ef;">Normal Curve</strong> overlay</span>
        <span><strong style="color: #d63c3c;">LSL</strong> spec limit</span>
        <span><strong style="color: #1f7a1f;">USL</strong> spec limit</span>
    `;

    report.page.wrapper.find("#spcResultMeta").html(meta_html);
    report.page.wrapper.find("#spcResultLegend").html(legend_html);
}


function render_histogram(report, row_key) {
    const filters = report.get_values ? report.get_values() : frappe.query_report.get_filter_values();
    filters.row_key = row_key;

    frappe.call({
        method: "aql_quality_assurance.aql_quality_assurance_by_havaratech.report.aql_process_capability_result.aql_process_capability_result.get_histogram_data",
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
        draw_chart(report, chart_data);
    });
}


function build_histogram_data(values, chart_data) {
    const lsl = Number.isFinite(Number(chart_data.lsl)) ? Number(chart_data.lsl) : null;
    const usl = Number.isFinite(Number(chart_data.usl)) ? Number(chart_data.usl) : null;
    const numeric_limits = [lsl, usl].filter((v) => v !== null);
    const raw_min = Math.min(...values, ...(numeric_limits.length ? numeric_limits : [Math.min(...values)]));
    const raw_max = Math.max(...values, ...(numeric_limits.length ? numeric_limits : [Math.max(...values)]));
    const span = raw_max - raw_min;

    if (span <= 0) {
        return null;
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
        const start = raw_min + i * step;
        const end = start + step;
        labels.push(`${start.toFixed(2)}-${end.toFixed(2)}`);
    }

    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    const std = Math.sqrt(
        values.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / (values.length - 1)
    );

    let curve = [];
    if (std > 0) {
        for (let i = 0; i < bins; i++) {
            const x = raw_min + (i + 0.5) * step;
            const pdf = (1 / (std * Math.sqrt(2 * Math.PI))) *
                Math.exp(-0.5 * Math.pow((x - mean) / std, 2));
            curve.push(Number((pdf * values.length * step).toFixed(3)));
        }
    } else {
        curve = new Array(bins).fill(0);
    }

    return {
        bins,
        curve,
        freq,
        labels,
        lsl,
        raw_min,
        raw_max,
        span,
        step,
        usl
    };
}


function draw_chart(report, chart_data) {
    const values = chart_data.values || [];
    if (!values.length) {
        return;
    }

    const histogram = build_histogram_data(values, chart_data);
    if (!histogram) {
        frappe.msgprint("The selected row does not have enough variation to draw a histogram.");
        clear_chart_area(report);
        return;
    }

    const container = document.getElementById("spcResultChartWrap");
    if (!container) {
        return;
    }

    container.innerHTML = "";

    window.aqlSpcResultChart = new frappe.Chart(container, {
        title: `${chart_data.parameter || "Parameter"} SPC Histogram`,
        type: "axis-mixed",
        height: 320,
        colors: ["#5e64ff", "#2490ef"],
        axisOptions: {
            xIsSeries: 1,
            shortenYAxisNumbers: 0
        },
        barOptions: {
            spaceRatio: 0.2
        },
        lineOptions: {
            regionFill: 0,
            hideDots: 0,
            spline: 1
        },
        data: {
            labels: histogram.labels,
            datasets: [
                {
                    name: "Frequency",
                    chartType: "bar",
                    values: histogram.freq
                },
                {
                    name: "Normal Curve",
                    chartType: "line",
                    values: histogram.curve
                }
            ]
        }
    });

    requestAnimationFrame(() => render_spec_limit_markers(container, window.aqlSpcResultChart, histogram));
}


function render_spec_limit_markers(container, chart, histogram) {
    container.querySelectorAll(".spc-limit-line, .spc-limit-text").forEach((el) => el.remove());

    const svg = container.querySelector("svg");
    if (!svg || !chart || !chart.measures) {
        return;
    }

    const measures = chart.measures;
    const plot_left = (measures.margins.left || 0) + (measures.paddings.left || 0);
    const plot_top = (measures.titleHeight || 0) + (measures.margins.top || 0) + (measures.paddings.top || 0);
    const plot_right = plot_left + chart.width;
    const plot_bottom = plot_top + chart.height;
    const plot_width = plot_right - plot_left;

    function create_line(value, color, label, x_offset = 0) {
        if (value === null || value === undefined || !Number.isFinite(value) || histogram.span <= 0) {
            return;
        }

        let pos = plot_left + ((value - histogram.raw_min) / histogram.span) * plot_width;
        pos = Math.max(plot_left, Math.min(plot_right - 2, pos)) + x_offset;

        const line = document.createElement("div");
        line.className = "spc-limit-line";
        line.style.position = "absolute";
        line.style.left = `${pos}px`;
        line.style.top = `${plot_top}px`;
        line.style.height = `${plot_bottom - plot_top}px`;
        line.style.width = "2px";
        line.style.background = color;
        line.style.zIndex = "5";

        const text = document.createElement("div");
        text.className = "spc-limit-text";
        text.innerText = `${label} (${value})`;
        text.style.position = "absolute";
        text.style.left = `${Math.min(pos, plot_right - 90)}px`;
        text.style.top = `${plot_top}px`;
        text.style.color = color;
        text.style.fontSize = "12px";
        text.style.background = "#fff";
        text.style.padding = "0 2px";
        text.style.zIndex = "6";

        container.appendChild(line);
        container.appendChild(text);
    }

    const overlap = histogram.lsl !== null && histogram.usl !== null && histogram.lsl === histogram.usl;
    create_line(histogram.lsl, "#d63c3c", "LSL", overlap ? -3 : 0);
    create_line(histogram.usl, "#1f7a1f", "USL", overlap ? 3 : 0);
}
