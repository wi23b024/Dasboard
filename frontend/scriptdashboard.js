

var API_URL = "http://127.0.0.1:8083/metrics";
var DEFAULT_START = "2025-10-01T00:00:00Z";
var DEFAULT_END   = "2025-11-11T00:00:00Z";

/***********************
 * MOCK-DATEN (Fallback)
 ***********************/
var MOCK_DATA = [
  { id: 1,  timestamp: "2025-10-07T12:18:17.992297+00:00", response_time_ms: 252, status_code: 400, region: "US" },
  { id: 2,  timestamp: "2025-10-07T12:19:17.992297+00:00", response_time_ms: 167, status_code: 404, region: "EU" },
  { id: 3,  timestamp: "2025-10-07T12:20:17.992297+00:00", response_time_ms: 176, status_code: 201, region: "EU" },
  { id: 4,  timestamp: "2025-10-07T12:21:17.992297+00:00", response_time_ms: 276, status_code: 200, region: "US" },
  { id: 5,  timestamp: "2025-10-07T12:22:17.992297+00:00", response_time_ms: 154, status_code: 200, region: "US" },
  { id: 6,  timestamp: "2025-10-07T12:23:17.992297+00:00", response_time_ms: 192, status_code: 201, region: "EU" },
  { id: 7,  timestamp: "2025-10-07T12:24:17.992297+00:00", response_time_ms: 416, status_code: 504, region: "APAC" },
  { id: 8,  timestamp: "2025-10-07T12:25:17.992297+00:00", response_time_ms: 148, status_code: 400, region: "EU" },
  { id: 9,  timestamp: "2025-10-07T12:26:17.992297+00:00", response_time_ms: 272, status_code: 504, region: "APAC" },
  { id: 10, timestamp: "2025-10-07T12:27:17.992297+00:00", response_time_ms: 351, status_code: 500, region: "APAC" }
];

/***********************
 * GLOBAL STATE
 ***********************/
var responseChart = null;
var errorChart = null;
var lastRows = [];                // merken, damit wir bei Skalierung nicht neu laden müssen
var yScale = { auto: true, min: null, max: null }; // Zustand der Y-Achse

/***********************
 * HILFSFUNKTIONEN
 ***********************/
function $(s){ return document.querySelector(s); }

function toLocalInput(isoString) {
  var d = new Date(isoString);
  function pad(n){ return String(n).padStart(2, "0"); }
  return d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate())+"T"+pad(d.getHours())+":"+pad(d.getMinutes());
}
function fromLocalInputToISOZ(localVal) {
  if (!localVal) return null;
  var d = new Date(localVal);
  return new Date(d.getTime() - d.getTimezoneOffset()*60000).toISOString();
}
function formatDateTime(iso) {
  var d = new Date(iso);
  return d.toLocaleDateString() + " " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

/***********************
 * REST-FETCH (Frontend → Proxy)
 ***********************/
async function fetchRealData(startISO, endISO) {
  var startInput = $("#startInput");
  var endInput   = $("#endInput");
  var start = startISO || (startInput ? fromLocalInputToISOZ(startInput.value) : null) || DEFAULT_START;
  var end   = endISO   || (endInput   ? fromLocalInputToISOZ(endInput.value)   : null) || DEFAULT_END;

  var url = API_URL + "?start=" + encodeURIComponent(start) + "&end=" + encodeURIComponent(end);

  var res = await fetch(url, { headers: { accept: "application/json" } });
  if (!res.ok) {
    var txt = "";
    try { txt = await res.text(); } catch(e){}
    throw new Error("HTTP "+res.status+" – "+txt.slice(0,150));
  }
  var json = await res.json();

  var result = [];
  var data = json.data || [];
  for (var i=0;i<data.length;i++){
    var r = data[i];
    result.push({
      id: (typeof r.id !== "undefined" ? r.id : (i+1)),
      timestamp: r.timestamp,
      response_time_ms: Number(r.response_time_ms) || 0,
      status_code: Number(r.status_code) || 0,
      region: r.region || "N/A"
    });
  }
  result.sort(function(a,b){ return new Date(a.timestamp) - new Date(b.timestamp); });
  return result;
}

/***********************
 * AGGREGATION: Durchschnitt pro Bucket (~200 Punkte)
 ***********************/
function aggregateMeanAdaptive(rows) {
  if (!rows || rows.length === 0) return { labels: [], mean: [] };

  var startMs = new Date(rows[0].timestamp).getTime();
  var endMs   = new Date(rows[rows.length-1].timestamp).getTime();
  var spanMs  = Math.max(1, endMs - startMs);
  var targetPoints = 200;
  var bucketMs = Math.ceil(spanMs / targetPoints);

  var buckets = {}; // idx -> { ts, vals[] }
  for (var i=0;i<rows.length;i++){
    var t = new Date(rows[i].timestamp).getTime();
    var idx = Math.floor((t - startMs)/bucketMs);
    if (!buckets[idx]) buckets[idx] = { ts: startMs + idx*bucketMs, vals: [] };
    buckets[idx].vals.push(rows[i].response_time_ms);
  }

  var labels=[], mean=[];
  var keys = Object.keys(buckets).map(function(k){ return Number(k); }).sort(function(a,b){ return a-b; });
  for (var j=0;j<keys.length;j++){
    var b = buckets[keys[j]];
    var arr = b.vals;
    var sum = 0; for (var k=0;k<arr.length;k++) sum += arr[k];
    var avg = sum / arr.length;
    labels.push(new Date(b.ts).toISOString());
    mean.push(avg);
  }
  return { labels: labels, mean: mean };
}

/***********************
 * KPIs
 ***********************/
function updateKPIs(rows){
  if(!rows || rows.length===0){
    $("#avgResponseTime").textContent = "–";
    $("#errorRate").textContent = "–";
    $("#totalRequests").textContent = "0";
    return;
  }
  var sum=0, errs=0;
  for (var i=0;i<rows.length;i++){
    sum += rows[i].response_time_ms;
    if (rows[i].status_code >= 400) errs++;
  }
  var avg = sum/rows.length;
  $("#avgResponseTime").textContent = avg.toFixed(1)+" ms";
  $("#errorRate").textContent = ((errs/rows.length)*100).toFixed(1)+" %";
  $("#totalRequests").textContent = String(rows.length);
}

/***********************
 * CHARTS
 ***********************/
function renderLine(rows){
  var ctx = document.getElementById("responseTimeChart").getContext("2d");
  var agg = aggregateMeanAdaptive(rows);

  var xLabels = [];
  for (var i=0;i<agg.labels.length;i++) xLabels.push(formatDateTime(agg.labels[i]));

  if (responseChart) responseChart.destroy();

  // yMin/yMax je nach Zustand
  var yMin = (yScale.auto ? undefined : (yScale.min!==null && yScale.min!=="" ? Number(yScale.min) : undefined));
  var yMax = (yScale.auto ? undefined : (yScale.max!==null && yScale.max!=="" ? Number(yScale.max) : undefined));

  responseChart = new Chart(ctx, {
    type:"line",
    data:{
      labels: xLabels,
      datasets:[{
        label:"Average Response Time",
        data: agg.mean,
        borderColor:"#4cc9f0",
        backgroundColor:"rgba(76,201,240,0)",
        fill:false,
        tension:0.25,
        pointRadius:0
      }]
    },
    options:{
      maintainAspectRatio:false,
      plugins:{
        legend:{ position:"top" },
        tooltip:{
          mode:"nearest", intersect:false,
          callbacks:{
            label: function(ctx){ return ctx.dataset.label+": "+Math.round(ctx.parsed.y)+" ms"; }
          }
        }
      },
      scales:{
        x:{ ticks:{ autoSkip:true, maxTicksLimit:12, maxRotation:0 } },
        y:{
          min: yMin,          // undefined = Auto
          max: yMax,          // undefined = Auto
          title:{ display:true, text:"ms" },
          grid:{ color:"rgba(255,255,255,0.1)" }
        }
      }
    }
  });
}

function renderDonut(rows){
  var ctx = document.getElementById("errorRegionChart").getContext("2d");
  var counts = {};
  for (var i=0;i<rows.length;i++){
    var r = rows[i];
    if (r.status_code >= 400){
      if (!counts[r.region]) counts[r.region]=0;
      counts[r.region]++;
    }
  }
  var labels=[], values=[];
  for (var key in counts){ labels.push(key); values.push(counts[key]); }

  if (errorChart) errorChart.destroy();
  errorChart = new Chart(ctx, {
    type:"doughnut",
    data:{ labels: labels, datasets:[{ data: values, backgroundColor:["#f72585","#4361ee","#4cc9f0","#b5179e"] }] },
    options:{ responsive:true }
  });
}

function renderTable(rows){
  var tbody = document.getElementById("requestTableBody");
  tbody.innerHTML = "";
  var list = rows.slice().reverse().slice(0,20);
  for (var i=0;i<list.length;i++){
    var d = list[i];
    var when = new Date(d.timestamp);
    var display = when.toLocaleDateString()+" "+when.toLocaleTimeString([], { hour:"2-digit", minute:"2-digit" });
    var tr = document.createElement("tr");
    tr.innerHTML =
      "<td>"+d.id+"</td>"+
      "<td>"+display+"</td>"+
      "<td>"+d.region+"</td>"+
      "<td>"+d.status_code+"</td>"+
      "<td>"+d.response_time_ms+"</td>";
    tbody.appendChild(tr);
  }
}

/***********************
 * CONTROLLER
 ***********************/
async function hydrate(opts){
  opts = opts || {};
  try{
    var rows = await fetchRealData(opts.startISO, opts.endISO);
    lastRows = rows;                     // merken für Skalierung
    updateKPIs(rows);
    renderLine(rows);
    renderDonut(rows);
    renderTable(rows);
  }catch(e){
    console.warn("LIVE fehlgeschlagen → Mockdaten:", e.message);
    var rows2 = MOCK_DATA.slice().sort(function(a,b){ return new Date(a.timestamp)-new Date(b.timestamp); });
    lastRows = rows2;
    updateKPIs(rows2);
    renderLine(rows2);
    renderDonut(rows2);
    renderTable(rows2);

    var warn = document.createElement("div");
    warn.textContent = "⚠️ Live-Daten nicht verfügbar: " + e.message;
    warn.style.cssText = "margin:8px 0;padding:8px 10px;border:1px solid #b33;border-radius:8px;background:rgba(255,0,0,.08)";
    var dash = document.querySelector(".dashboard");
    if (dash) dash.prepend(warn);
  }
}

/***********************
 * INIT
 ***********************/
document.addEventListener("DOMContentLoaded", function(){
  var startInput = $("#startInput");
  var endInput   = $("#endInput");
  if (startInput) startInput.value = toLocalInput(DEFAULT_START);
  if (endInput)   endInput.value   = toLocalInput(DEFAULT_END);

  // Erstmal laden
  hydrate({ startISO: DEFAULT_START, endISO: DEFAULT_END });

  // Zeitraum anwenden
  $("#applyFilters").addEventListener("click", function(){
    var s = fromLocalInputToISOZ(startInput ? startInput.value : "") || DEFAULT_START;
    var e = fromLocalInputToISOZ(endInput ? endInput.value : "")     || DEFAULT_END;
    hydrate({ startISO: s, endISO: e });
  });

  // === NEU: Y-Skalierung ===
  var yMinInput = $("#yMinInput");
  var yMaxInput = $("#yMaxInput");
  var yAutoCheck = $("#yAutoCheck");
  $("#applyScale").addEventListener("click", function(){
    yScale.auto = yAutoCheck.checked;
    yScale.min = yMinInput.value;
    yScale.max = yMaxInput.value;
    if (lastRows && lastRows.length){
      renderLine(lastRows);   // nur neu zeichnen, kein Re-Fetch
    }
  });

  // Auto-Checkbox sperrt/entsperrt Inputs
  yAutoCheck.addEventListener("change", function(){
    var dis = yAutoCheck.checked;
    yMinInput.disabled = dis;
    yMaxInput.disabled = dis;
  });
  // initial: Inputs disabled, weil Auto an
  yMinInput.disabled = true;
  yMaxInput.disabled = true;
});



