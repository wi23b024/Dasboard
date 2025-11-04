const data = [
  {id:1, timestamp:"2025-10-07T12:18:17.992297+00:00", response_time_ms:252, status_code:400, region:"US"},
  {id:2, timestamp:"2025-10-07T12:19:17.992297+00:00", response_time_ms:167, status_code:404, region:"EU"},
  {id:3, timestamp:"2025-10-07T12:20:17.992297+00:00", response_time_ms:176, status_code:201, region:"EU"},
  {id:4, timestamp:"2025-10-07T12:21:17.992297+00:00", response_time_ms:276, status_code:200, region:"US"},
  {id:5, timestamp:"2025-10-07T12:22:17.992297+00:00", response_time_ms:154, status_code:200, region:"US"},
  {id:6, timestamp:"2025-10-07T12:23:17.992297+00:00", response_time_ms:192, status_code:201, region:"EU"},
  {id:7, timestamp:"2025-10-07T12:24:17.992297+00:00", response_time_ms:416, status_code:504, region:"APAC"},
  {id:8, timestamp:"2025-10-07T12:25:17.992297+00:00", response_time_ms:148, status_code:400, region:"EU"},
  {id:9, timestamp:"2025-10-07T12:26:17.992297+00:00", response_time_ms:272, status_code:504, region:"APAC"},
  {id:10, timestamp:"2025-10-07T12:27:17.992297+00:00", response_time_ms:351, status_code:500, region:"APAC"},
  {id:11, timestamp:"2025-10-07T12:28:17.992297+00:00", response_time_ms:245, status_code:404, region:"APAC"},
  {id:12, timestamp:"2025-10-07T12:29:17.992297+00:00", response_time_ms:290, status_code:400, region:"APAC"},
  {id:13, timestamp:"2025-10-07T12:30:17.992297+00:00", response_time_ms:388, status_code:200, region:"APAC"},
  {id:14, timestamp:"2025-10-07T12:31:17.992297+00:00", response_time_ms:190, status_code:504, region:"EU"},
  {id:15, timestamp:"2025-10-07T12:32:17.992297+00:00", response_time_ms:284, status_code:400, region:"US"},
  {id:16, timestamp:"2025-10-07T12:33:17.992297+00:00", response_time_ms:319, status_code:504, region:"EU"},
];

// --- KPI Berechnungen ---
const avgResponse = data.reduce((acc, d) => acc + d.response_time_ms, 0) / data.length;
const errorCount = data.filter(d => d.status_code >= 400).length;
const total = data.length;

document.getElementById("avgResponseTime").innerText = `${avgResponse.toFixed(1)} ms`;
document.getElementById("errorRate").innerText = `${((errorCount / total) * 100).toFixed(1)} %`;
document.getElementById("totalRequests").innerText = total;

// --- Chart 1: Response Time über Zeit ---
const ctx1 = document.getElementById('responseTimeChart').getContext('2d');
new Chart(ctx1, {
  type: 'line',
  data: {
    labels: data.map(d => new Date(d.timestamp).toLocaleTimeString()),
    datasets: [{
      label: 'Response Time (ms)',
      data: data.map(d => d.response_time_ms),
      borderColor: '#4cc9f0',
      backgroundColor: 'rgba(76, 201, 240, 0.2)',
      fill: true,
      tension: 0.3
    }]
  },
  options: { scales: { y: { beginAtZero: true } } }
});

// --- Chart 2: Fehler nach Region ---
const regions = [...new Set(data.map(d => d.region))];
const errorByRegion = regions.map(r => data.filter(d => d.region === r && d.status_code >= 400).length);
const ctx2 = document.getElementById('errorRegionChart').getContext('2d');
new Chart(ctx2, {
  type: 'doughnut',
  data: {
    labels: regions,
    datasets: [{
      label: 'Errors by Region',
      data: errorByRegion,
      backgroundColor: ['#f72585','#4361ee','#4cc9f0','#b5179e'],
    }]
  }
});

// --- Tabelle füllen ---
const tbody = document.getElementById('requestTableBody');
data.slice(-10).forEach(d => {
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td>${d.id}</td>
    <td>${new Date(d.timestamp).toLocaleTimeString()}</td>
    <td>${d.region}</td>
    <td>${d.status_code}</td>
    <td>${d.response_time_ms}</td>
  `;
  tbody.appendChild(tr);
});
