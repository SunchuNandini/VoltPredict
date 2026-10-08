let historyChartInstance = null;
let predictionChartInstance = null;
let applianceChartInstance = null;
let distributionChartInstance = null;

const money = (value) => value == null ? "—" : "₹ " + Number(value).toLocaleString("en-IN", {maximumFractionDigits: 0});
const number = (value, digits = 2) => value == null ? "—" : Number(value).toLocaleString("en-IN", {maximumFractionDigits: digits});

async function getJSON(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
}

function setModelStatus() {
  getJSON("/api/health").then(data => {
    const el = document.getElementById("modelStatus");
    const name = document.getElementById("modelName");
    if (!el) return;
    el.textContent = data.model_loaded ? "● Online" : "● Error";
    el.className = data.model_loaded ? "status-online" : "status-error";
    if (name) name.textContent = data.model;
  }).catch(() => {});
}

function setupRefresh() {
  const btn = document.getElementById("refreshBtn");
  if (btn) btn.addEventListener("click", () => window.location.reload());
}

async function loadSummary() {
  const s = await getJSON("/api/summary");
  const ids = {
    avgBill: money(s.avg_bill),
    avgUnits: `${number(s.avg_units)} kWh`,
    maxBill: money(s.max_bill),
    minBill: money(s.min_bill),
    medianBill: money(s.median_bill),
    records: number(s.records, 0),
    latestBill: money(s.recent.latest_bill),
    predictionCount: number(s.recent.count, 0),
    analyticsPredictionCount: number(s.recent.count, 0),
    tipsRunCount: number(s.recent.count, 0),
    r2: s.r2 == null ? "—" : Number(s.r2).toFixed(3),
    mae: s.mae == null ? "—" : money(s.mae),
    rmse: s.rmse == null ? "—" : money(s.rmse),
    latestUnits: s.recent.latest_units == null ? "—" : `${number(s.recent.latest_units)} kWh`,
    recentAverage: s.recent.average_recent_bill == null ? "—" : money(s.recent.average_recent_bill),
  };
  Object.entries(ids).forEach(([id, value]) => { const el = document.getElementById(id); if (el) el.textContent = value; });

  const latestNote = document.getElementById("latestBillNote");
  if (latestNote) latestNote.textContent = s.recent.count ? "Latest saved model result" : "No prediction yet";

  if (s.recent.count) {
    const latest = await getJSON("/api/recent");
    const last = latest.predictions[0];
    const change = document.getElementById("latestChange");
    const trend = document.getElementById("predictionTrend");
    if (change) change.textContent = last.change_percent == null ? "—" : `${last.change_percent >= 0 ? "+" : ""}${Number(last.change_percent).toFixed(1)}%`;
    if (trend) trend.textContent = s.recent.trend_percent == null ? "—" : `${s.recent.trend_percent >= 0 ? "+" : ""}${Number(s.recent.trend_percent).toFixed(1)}%`;
  }
}

async function loadHistoryChart() {
  const canvas = document.getElementById("historyChart");
  if (!canvas) return;
  const data = await getJSON("/api/history");
  if (historyChartInstance) historyChartInstance.destroy();
  historyChartInstance = new Chart(canvas, {
    type: "line",
    data: { labels: data.map(x => x.month), datasets: [
      {label:"Average Bill (₹)", data:data.map(x=>x.bill), borderWidth:2, tension:.35, yAxisID:"bill"},
      {label:"Average Units (kWh)", data:data.map(x=>x.units), borderWidth:2, tension:.35, yAxisID:"units"}
    ]},
    options: chartOptions({bill:{position:"left"}, units:{position:"right", grid:{drawOnChartArea:false}}})
  });
}

function chartOptions(scales) {
  return {
    responsive:true,
    maintainAspectRatio:false,
    interaction:{mode:"index", intersect:false},
    scales:{...scales, x:{ticks:{color:"#91a5ba"}, grid:{color:"rgba(255,255,255,.04)"}}, y:{ticks:{color:"#91a5ba"}, grid:{color:"rgba(255,255,255,.05)"}}},
    plugins:{legend:{labels:{color:"#a9b9c9"}}}
  };
}

async function loadRecentMini() {
  const box = document.getElementById("recentMini");
  if (!box) return;
  const data = await getJSON("/api/recent");
  if (!data.predictions.length) {
    box.innerHTML = '<div class="empty-state">No predictions yet. Open Bill Predictor to start.</div>';
    return;
  }
  box.innerHTML = data.predictions.slice(0, 5).map(p => `
    <div class="recent-row">
      <div><b>${money(p.predicted_bill)}</b><small>${new Date(p.timestamp).toLocaleString()}</small></div>
      <span>${number(p.units,0)} kWh</span>
    </div>`).join("");
}

function setupPredictor() {
  const form = document.getElementById("predictionForm");
  if (!form) return;
  const units = form.elements.units_consumed;
  const days = form.elements.days_in_bill;
  const avg = document.getElementById("avgDailyInput");
  const updateDaily = () => { avg.value = (Number(units.value || 0) / Math.max(1, Number(days.value || 1))).toFixed(2); };
  units.addEventListener("input", updateDaily); days.addEventListener("input", updateDaily); updateDaily();

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const result = document.getElementById("result");
    const error = document.getElementById("formError");
    error.hidden = true;
    result.textContent = "Calculating…";
    const data = Object.fromEntries(new FormData(form).entries());
    Object.keys(data).forEach(k => data[k] = Number(data[k]));
    try {
      const out = await getJSON("/api/predict", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(data)});
      result.textContent = money(out.predicted_bill);
      document.getElementById("rUnits").textContent = `${number(out.units)} kWh`;
      document.getElementById("rDailyUnits").textContent = `${number(out.avg_daily_units)} kWh`;
      document.getElementById("rUnitChange").textContent = `${out.change_units >= 0 ? "+" : ""}${number(out.change_units)} kWh`;
      document.getElementById("rChange").textContent = out.change_percent == null ? "—" : `${out.change_percent >= 0 ? "+" : ""}${Number(out.change_percent).toFixed(1)}%`;
      document.getElementById("dailyCost").textContent = `≈ ${money(out.estimated_daily_cost)} / day`;
      document.getElementById("predictionTime").textContent = `Saved at ${new Date(out.timestamp).toLocaleString()}`;
      document.getElementById("meter").style.width = Math.min(100, Math.max(8, out.predicted_bill / 50)) + "%";
      await loadRecentTable();
      const badge = document.getElementById("recentCountBadge");
      const recent = await getJSON("/api/recent");
      badge.textContent = `${recent.summary.count} RUN${recent.summary.count === 1 ? "" : "S"}`;
    } catch (err) {
      result.textContent = "Prediction error";
      error.textContent = err.message;
      error.hidden = false;
    }
  });
}

async function loadRecentTable() {
  const tbody = document.getElementById("recentTable");
  if (!tbody) return;
  const data = await getJSON("/api/recent");
  if (!data.predictions.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="empty-state">No saved predictions yet.</td></tr>';
    return;
  }
  tbody.innerHTML = data.predictions.map(p => `<tr>
    <td>${new Date(p.timestamp).toLocaleString()}</td>
    <td>${number(p.units)} kWh</td>
    <td><b>${money(p.predicted_bill)}</b></td>
    <td class="${p.change_percent >= 0 ? 'positive' : 'negative'}">${p.change_percent == null ? '—' : `${p.change_percent >= 0 ? '+' : ''}${Number(p.change_percent).toFixed(1)}%`}</td>
  </tr>`).join("");
}

async function loadAnalytics() {
  const data = await getJSON("/api/analytics");
  const labels = data.recent_predictions.map(x => new Date(x.label).toLocaleDateString([], {month:"short", day:"numeric", hour:"2-digit", minute:"2-digit"}));
  const predictionCanvas = document.getElementById("predictionChart");
  if (predictionCanvas) {
    document.getElementById("predictionEmpty").hidden = data.recent_predictions.length > 0;
    if (predictionChartInstance) predictionChartInstance.destroy();
    predictionChartInstance = new Chart(predictionCanvas, {type:"line", data:{labels, datasets:[{label:"Predicted bill (₹)", data:data.recent_predictions.map(x=>x.bill), borderWidth:2, tension:.35}]}, options:chartOptions({y:{title:{display:true,text:"₹"}}})});
  }
  const applianceCanvas = document.getElementById("applianceChart");
  if (applianceCanvas) {
    if (applianceChartInstance) applianceChartInstance.destroy();
    applianceChartInstance = new Chart(applianceCanvas, {type:"bar", data:{labels:data.appliances.map(x=>x.name), datasets:[{label:"Average usage", data:data.appliances.map(x=>x.value), borderWidth:1}]}, options:chartOptions({y:{beginAtZero:true}})});
  }
  const distributionCanvas = document.getElementById("distributionChart");
  if (distributionCanvas) {
    if (distributionChartInstance) distributionChartInstance.destroy();
    distributionChartInstance = new Chart(distributionCanvas, {type:"doughnut", data:{labels:data.distribution.map(x=>x.range), datasets:[{data:data.distribution.map(x=>x.records), borderWidth:1}]}, options:{responsive:true, maintainAspectRatio:false, plugins:{legend:{position:"bottom", labels:{color:"#a9b9c9"}}}}});
  }
  const latest = data.latest;
  const insight = document.getElementById("latestInsight");
  if (insight) {
    insight.innerHTML = latest ? `<b>Latest estimate: ${money(latest.predicted_bill)}</b><span>${number(latest.units)} kWh was entered against ${number(latest.previous_units)} kWh previously, a ${latest.change_percent == null ? "—" : (latest.change_percent >= 0 ? "+" : "") + Number(latest.change_percent).toFixed(1) + "%"} change. The personal trend chart will update every time you submit another prediction.</span>` : "Make a prediction to see a personalized insight here.";
  }
}

async function loadTips() {
  const grid = document.getElementById("tipsGrid");
  if (!grid) return;
  const data = await getJSON("/api/tips");
  const latest = data.latest;
  document.getElementById("tipsRunCount").textContent = data.prediction_count;
  if (latest) {
    document.getElementById("tipsHeadline").textContent = `Suggestions for your ₹${Number(latest.predicted_bill).toLocaleString("en-IN", {maximumFractionDigits:0})} estimate`;
    document.getElementById("tipsSubtext").textContent = `These recommendations are based on your most recent ${number(latest.units)} kWh usage profile.`;
  }
  grid.innerHTML = data.tips.map(t => `<div class="tip-card"><div class="tip-icon">${t.icon}</div><div><h3>${t.title}</h3><p>${t.text}</p></div></div>`).join("");
  const profile = document.getElementById("latestProfile");
  if (profile) {
    profile.innerHTML = latest ? [
      ["Units consumed", `${number(latest.units)} kWh`], ["Previous units", `${number(latest.previous_units)} kWh`], ["AC usage", `${number(latest.ac_usage_hours)} hrs/day`], ["Fan usage", `${number(latest.fan_usage_hours)} hrs/day`], ["Water heater", `${number(latest.water_heater_hours)} hrs/day`], ["Temperature", `${number(latest.temperature_avg,1)} °C`], ["Humidity", `${number(latest.humidity_avg,1)} %`], ["Occupants", number(latest.occupants,0)]
    ].map(([a,b]) => `<div><span>${a}</span><b>${b}</b></div>`).join("") : '<div class="empty-state">No prediction available yet.</div>';
  }
}

async function boot() {
  setupRefresh();
  setModelStatus();
  const page = document.body.dataset.page;
  try {
    if (page === "dashboard") { await loadSummary(); await loadRecentMini(); await loadHistoryChart(); }
    if (page === "predictor") { await loadSummary(); await loadRecentTable(); setupPredictor(); }
    if (page === "analytics") { await loadSummary(); await loadHistoryChart(); await loadAnalytics(); }
    if (page === "tips") { await loadSummary(); await loadTips(); }
  } catch (err) { console.error(err); }
}

document.addEventListener("DOMContentLoaded", boot);
