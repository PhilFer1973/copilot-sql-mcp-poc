"""Cursor MCP App renderer assets.

This module is mechanically extracted from the legacy working server.
"""

CHART_VIEW_URI = "ui://sqlserver-mcp/chart-view.html"

CHART_VIEW_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="color-scheme" content="light dark">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SQL Server interactive result</title>

  <style>
    :root {
      font-family: Inter, ui-sans-serif, system-ui, -apple-system,
                   BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    html, body {
      margin: 0;
      padding: 0;
      background: transparent;
    }

    body {
      padding: 14px;
    }

    .card {
      border: 1px solid rgba(127, 127, 127, 0.24);
      border-radius: 12px;
      padding: 14px;
      background: rgba(127, 127, 127, 0.06);
    }

    h2 {
      margin: 0 0 5px;
      font-size: 17px;
    }

    .subtitle,
    .reason {
      margin: 0 0 9px;
      font-size: 12px;
      opacity: 0.72;
    }

    .toolbar {
      display: flex;
      gap: 7px;
      margin: 10px 0;
    }

    button {
      border: 1px solid rgba(127, 127, 127, 0.26);
      border-radius: 7px;
      padding: 6px 10px;
      color: inherit;
      background: transparent;
      cursor: pointer;
    }

    button.active {
      background: rgba(127, 127, 127, 0.17);
    }

    .chart-wrap {
      position: relative;
      min-height: 355px;
    }

    canvas {
      width: 100% !important;
      height: 355px !important;
    }

    .kpi {
      margin: 32px 0 24px;
      font-size: 42px;
      font-weight: 750;
      letter-spacing: -0.035em;
    }

    .table-wrap {
      max-height: 440px;
      overflow: auto;
      border: 1px solid rgba(127, 127, 127, 0.22);
      border-radius: 8px;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }

    th,
    td {
      padding: 8px 10px;
      border-bottom: 1px solid rgba(127, 127, 127, 0.16);
      text-align: left;
      white-space: nowrap;
    }

    th {
      position: sticky;
      top: 0;
      z-index: 1;
      background: Canvas;
    }

    .error {
      color: #b42318;
      white-space: pre-wrap;
    }

    .hidden {
      display: none;
    }
  </style>
</head>

<body>
  <div class="card">
    <h2 id="title">SQL Server result</h2>
    <p id="subtitle" class="subtitle"></p>
    <p id="reason" class="reason"></p>

    <div id="toolbar" class="toolbar hidden">
      <button id="visual-tab" class="active">Visual</button>
      <button id="data-tab">Data</button>
    </div>

    <section id="visual-panel">
      <div id="kpi" class="kpi hidden"></div>
      <div id="chart-wrap" class="chart-wrap hidden">
        <canvas id="chart"></canvas>
      </div>
    </section>

    <section id="data-panel" class="hidden">
      <div class="table-wrap">
        <table id="data-table"></table>
      </div>
    </section>

    <div id="error" class="error hidden"></div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>

  <script type="module">
    import { App } from
      "https://unpkg.com/@modelcontextprotocol/ext-apps@0.4.0/app-with-deps";

    const app = new App({
      name: "SQL Server interactive result",
      version: "1.0.0"
    });

    let chartInstance = null;
    const byId = id => document.getElementById(id);

    function setVisible(id, visible) {
      byId(id).classList.toggle("hidden", !visible);
    }

    function switchPanel(panel) {
      const visual = panel === "visual";
      setVisible("visual-panel", visual);
      setVisible("data-panel", !visual);
      byId("visual-tab").classList.toggle("active", visual);
      byId("data-tab").classList.toggle("active", !visual);
    }

    function formatValue(value, payload) {
      if (value === null || value === undefined) return "";
      const number = Number(value);

      if (payload.value_format === "currency" && !Number.isNaN(number)) {
        return new Intl.NumberFormat(undefined, {
          style: "currency",
          currency: payload.currency_code || "USD",
          maximumFractionDigits: 2
        }).format(number);
      }

      if (payload.value_format === "percent" && !Number.isNaN(number)) {
        return `${number.toLocaleString()}%`;
      }

      if (!Number.isNaN(number) && value !== "") {
        return number.toLocaleString();
      }

      return String(value);
    }

    function renderTable(payload) {
      const table = byId("data-table");
      table.innerHTML = "";

      const thead = document.createElement("thead");
      const headerRow = document.createElement("tr");

      for (const column of payload.columns) {
        const th = document.createElement("th");
        th.textContent = column;
        headerRow.appendChild(th);
      }

      thead.appendChild(headerRow);
      table.appendChild(thead);

      const tbody = document.createElement("tbody");

      for (const row of payload.rows) {
        const tr = document.createElement("tr");

        for (const column of payload.columns) {
          const td = document.createElement("td");
          td.textContent = row[column] === null || row[column] === undefined
            ? ""
            : String(row[column]);
          tr.appendChild(td);
        }

        tbody.appendChild(tr);
      }

      table.appendChild(tbody);
    }

    function renderKpi(payload) {
      setVisible("kpi", true);
      setVisible("chart-wrap", false);

      const field = payload.y_fields[0] || payload.columns[0];
      const value = payload.rows[0]?.[field];
      byId("kpi").textContent = formatValue(value, payload);
    }

    function renderChart(payload) {
      setVisible("kpi", false);
      setVisible("chart-wrap", true);

      if (chartInstance) {
        chartInstance.destroy();
        chartInstance = null;
      }

      const typeMap = {
        bar: "bar",
        horizontal_bar: "bar",
        line: "line",
        scatter: "scatter",
        pie: "pie",
        doughnut: "doughnut"
      };

      const chartType = typeMap[payload.visual_type] || "bar";
      let chartData;

      if (payload.visual_type === "scatter") {
        const xField = payload.x_field;
        const yField = payload.y_fields[0];

        chartData = {
          datasets: [{
            label: yField,
            data: payload.rows.map(row => ({
              x: Number(row[xField]),
              y: Number(row[yField])
            }))
          }]
        };
      } else if (
        payload.visual_type === "pie"
        || payload.visual_type === "doughnut"
      ) {
        const xField = payload.x_field;
        const yField = payload.y_fields[0];

        chartData = {
          labels: payload.rows.map(row => String(row[xField])),
          datasets: [{
            label: yField,
            data: payload.rows.map(row => Number(row[yField]))
          }]
        };
      } else {
        const xField = payload.x_field;

        chartData = {
          labels: payload.rows.map(row => String(row[xField])),
          datasets: payload.y_fields.map(field => ({
            label: field,
            data: payload.rows.map(row => Number(row[field])),
            borderWidth: payload.visual_type === "line" ? 2 : 1,
            tension: payload.visual_type === "line" ? 0.2 : 0,
            fill: false
          }))
        };
      }

      const options = {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: "nearest",
          intersect: false
        },
        plugins: {
          legend: {
            display:
              payload.y_fields.length > 1
              || payload.visual_type === "pie"
              || payload.visual_type === "doughnut"
          },
          tooltip: {
            enabled: true
          }
        }
      };

      if (payload.visual_type === "horizontal_bar") {
        options.indexAxis = "y";
      }

      chartInstance = new Chart(byId("chart"), {
        type: chartType,
        data: chartData,
        options
      });
    }

    byId("visual-tab").addEventListener(
      "click",
      () => switchPanel("visual")
    );

    byId("data-tab").addEventListener(
      "click",
      () => switchPanel("data")
    );

    app.ontoolresult = result => {
      try {
        const payload = result.structuredContent;

        if (!payload) {
          throw new Error("No structured visual payload was returned.");
        }

        if (payload.error) {
          throw new Error(payload.error);
        }

        byId("title").textContent = payload.title || "SQL Server result";
        byId("subtitle").textContent =
          `${payload.row_count} row(s) · `
          + payload.visual_type.replaceAll("_", " ");
        byId("reason").textContent = payload.reason || "";

        renderTable(payload);
        setVisible("toolbar", payload.visual_type !== "table");

        if (payload.visual_type === "table") {
          switchPanel("data");
        } else if (payload.visual_type === "kpi") {
          renderKpi(payload);
          switchPanel("visual");
        } else {
          renderChart(payload);
          switchPanel("visual");
        }
      } catch (error) {
        setVisible("error", true);
        byId("error").textContent = String(error);
      }
    };

    await app.connect();
  </script>
</body>
</html>"""
