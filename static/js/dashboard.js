"use strict";

// ---- Auth guard ----
if (!sessionStorage.getItem("auth")) {
  location.href = "/login";
}

// ---- State ----
let state = { tipo: "Pneus", semana: "Todas", view: "dashboard", charts: {}, dtComparativo: null };

Chart.defaults.color = "#8b949e";
Chart.defaults.borderColor = "#21262d";
Chart.defaults.font.family = "'Segoe UI', system-ui, sans-serif";
Chart.defaults.font.size = 12;

$(function () {
  atualizarDados();
  setInterval(updateTimestamp, 1000);
  carregarListaArquivos();
});

// ---- Auth ----
function sair() {
  sessionStorage.removeItem("auth");
  location.href = "/login";
}

// ---- Upload panel ----
function toggleUpload() {
  const p = document.getElementById("uploadPanel");
  const visible = p.style.display !== "none";
  p.style.display = visible ? "none" : "";
  if (!visible) carregarListaArquivos();
}

function handleDrop(event, tipo) {
  event.preventDefault();
  document.getElementById("dropzoneDados").classList.remove("drag-over");
  uploadDados(event.dataTransfer.files);
}

function uploadDados(files) {
  if (!files || !files.length) return;
  const fd = new FormData();
  for (const f of files) fd.append("files", f);

  const st = document.getElementById("uploadDadosStatus");
  st.innerHTML = `<p class="upload-result"><i class="fa-solid fa-spinner fa-spin"></i> Enviando ${files.length} arquivo(s)...</p>`;

  fetch("/api/upload/dados", { method: "POST", body: fd })
    .then(r => r.json())
    .then(data => {
      let msg = "";
      if (data.salvos.length) msg += `✅ Salvos: ${data.salvos.join(", ")}. `;
      if (data.erros.length) msg += `❌ Erros: ${data.erros.join(", ")}`;
      st.innerHTML = `<p class="upload-result">${msg}</p>`;
      atualizarSemanas(data.semanas);
      updateFooter(data.arquivos_total, data.registros);
      setStatus(`${data.arquivos_total.length} arquivo(s) carregado(s)`, true);
      carregarListaArquivos();
      loadDashboard();
      showToast(`✅ ${data.salvos.length} arquivo(s) enviado(s)`, "success");
    })
    .catch(e => {
      st.innerHTML = `<p class="upload-result erro">❌ Erro: ${e.message}</p>`;
    });
}

function uploadAuxiliares() {
  const fd = new FormData();
  const v = document.getElementById("auxVendedores").files[0];
  const p = document.getElementById("auxEmpPneus").files[0];
  const s = document.getElementById("auxEmpPecas").files[0];
  if (v) fd.append("vendedores", v);
  if (p) fd.append("empresas_pneus", p);
  if (s) fd.append("empresas_pecas", s);
  if (!v && !p && !s) { showToast("Selecione ao menos um arquivo", "error"); return; }

  fetch("/api/upload/auxiliares", { method: "POST", body: fd })
    .then(r => r.json())
    .then(data => {
      const st = document.getElementById("uploadAuxStatus");
      let msg = "";
      if (data.salvos.length) msg += `✅ Atualizados: ${data.salvos.join(", ")}. `;
      if (data.erros.length) msg += `❌ ${data.erros.join(", ")}`;
      st.innerHTML = `<p class="upload-result">${msg}</p>`;
      loadDashboard();
      showToast("✅ Auxiliares atualizados", "success");
    });
}

function carregarListaArquivos() {
  fetch("/api/arquivos")
    .then(r => r.json())
    .then(data => {
      const el = document.getElementById("listaArquivos");
      if (!data.dados.length) {
        el.innerHTML = `<p class="text-muted">Nenhum arquivo de dados encontrado.</p>`;
        return;
      }
      const items = data.dados.map(f => `
        <div class="upload-file-item">
          <span class="fname"><i class="fa-solid fa-file-excel"></i> ${f}</span>
          <button class="btn-del" onclick="deletarArquivo('${f.replace(/'/g,"\\'")}')">
            <i class="fa-solid fa-trash"></i>
          </button>
        </div>`).join("");
      el.innerHTML = `<div class="upload-file-list">${items}</div>`;
    });
}

function deletarArquivo(nome) {
  if (!confirm(`Remover "${nome}" do servidor?`)) return;
  fetch("/api/arquivos/deletar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nome })
  })
  .then(r => r.json())
  .then(d => {
    if (d.ok) { carregarListaArquivos(); loadDashboard(); showToast("🗑️ Arquivo removido", "info"); }
    else showToast("❌ " + d.erro, "error");
  });
}

// ---- Data reload ----
function atualizarDados() {
  showLoading(true);
  fetch("/api/atualizar", { method: "POST" })
    .then(r => r.json())
    .then(data => {
      atualizarSemanas(data.semanas);
      updateFooter(data.arquivos, data.total_registros);
      setStatus(`${data.arquivos.length} arquivo(s) carregado(s)`, true);
      showToast(`✅ ${data.arquivos.length} arquivo(s) processado(s)`, "success");
      loadDashboard();
    })
    .catch(err => { showToast("❌ Erro: " + err.message, "error"); showLoading(false); });
}

function loadDashboard() {
  showLoading(true);
  const url = `/api/dashboard?tipo=${encodeURIComponent(state.tipo)}&semana=${encodeURIComponent(state.semana)}`;
  fetch(url)
    .then(r => r.json())
    .then(data => {
      renderKPIs(data.kpis);
      if (state.view === "dashboard") renderAllCharts(data);
      else renderComparativo(data.comparativo);
      atualizarSemanas(data.semanas_disponiveis);
      updateFooter(data.arquivos_carregados, null);
    })
    .catch(err => showToast("❌ " + err.message, "error"))
    .finally(() => showLoading(false));
}

// ---- KPIs ----
function renderKPIs(kpis) {
  document.getElementById("kpiFaturamento").textContent = formatMoney(kpis.faturamento_total);
  document.getElementById("kpiTicket").textContent = formatMoney(kpis.ticket_medio);
  document.getElementById("kpiVendas").textContent = formatNum(kpis.qtd_vendas);
  document.getElementById("kpiClientes").textContent = formatNum(kpis.clientes_unicos);
  document.getElementById("kpiVendedores").textContent = formatNum(kpis.vendedores_unicos);
  document.getElementById("kpiEmpresas").textContent = formatNum(kpis.empresas_unicas);
}

// ---- Charts ----
function renderAllCharts(data) {
  renderHBar("chartVendQtd", data.top_vendedores_qtd, "Vendas", "#1f6feb");
  renderHBar("chartVendVal", data.top_vendedores_valor, "R$", "#3fb950", true);
  renderHBar("chartCompQtd", data.top_compradores_qtd, "Compras", "#8957e5");
  renderHBar("chartCompVal", data.top_compradores_valor, "R$", "#f0c040", true);
  renderHBar("chartEmpQtd", data.empresas_qtd, "Vendas", "#1abc9c");
  renderHBar("chartEmpVal", data.empresas_valor, "R$", "#ff6b6b", true);
  renderLineArea("chartFatDia",
    data.faturamento_dia.map(d => d.data),
    data.faturamento_dia.map(d => d.valor),
    "Faturamento (R$)", "#58a6ff");
}

function renderHBar(canvasId, items, label, color, isMoney = false) {
  destroyChart(canvasId);
  if (!items || !items.length) return;
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  state.charts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: items.map(i => truncate(i.nome, 22)),
      datasets: [{ label, data: items.map(i => i.valor), backgroundColor: color + "cc", borderColor: color, borderWidth: 1, borderRadius: 4 }],
    },
    options: {
      indexAxis: "y", responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => isMoney ? "  " + formatMoney(c.raw) : "  " + formatNum(c.raw) } } },
      scales: { x: { grid: { color: "#21262d" }, ticks: { callback: v => isMoney ? abrevMoney(v) : formatNum(v) } }, y: { grid: { display: false } } },
    },
  });
}

function renderLineArea(canvasId, labels, values, label, color) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  state.charts[canvasId] = new Chart(ctx, {
    type: "line",
    data: { labels, datasets: [{ label, data: values, fill: true, backgroundColor: color + "22", borderColor: color, borderWidth: 2, pointBackgroundColor: color, pointRadius: 4, tension: 0.4 }] },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => "  " + formatMoney(c.raw) } } },
      scales: { x: { grid: { color: "#21262d" } }, y: { grid: { color: "#21262d" }, ticks: { callback: v => abrevMoney(v) } } },
    },
  });
}

function renderBarSingle(canvasId, labels, values, label, color) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  state.charts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: { labels, datasets: [{ label, data: values, backgroundColor: color + "cc", borderColor: color, borderWidth: 1, borderRadius: 4 }] },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { grid: { color: "#21262d" } }, y: { grid: { color: "#21262d" }, ticks: { callback: v => abrevMoney(v) } } },
    },
  });
}

// ---- Comparativo ----
function renderComparativo(comp) {
  if (!comp || !comp.length) return;
  const semanas = comp.map(r => r.semana);

  destroyChart("chartEvoFat");
  const ctxFat = document.getElementById("chartEvoFat");
  state.charts["chartEvoFat"] = new Chart(ctxFat, {
    type: "line",
    data: { labels: semanas, datasets: [{ label: "Faturamento (R$)", data: comp.map(r => r.faturamento), fill: true, backgroundColor: "#1f6feb22", borderColor: "#1f6feb", borderWidth: 2.5, pointBackgroundColor: "#1f6feb", pointRadius: 6, tension: 0.35 }] },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => "  " + formatMoney(c.raw) } } },
      scales: { x: { grid: { color: "#21262d" } }, y: { grid: { color: "#21262d" }, ticks: { callback: v => abrevMoney(v) } } },
    },
  });

  renderBarSingle("chartEvoQtd", semanas, comp.map(r => r.qtd_vendas), "Qtd. Vendas", "#3fb950");
  renderBarSingle("chartEvoTicket", semanas, comp.map(r => r.ticket_medio), "Ticket Médio", "#f0c040");
  renderBarSingle("chartEvoClientes", semanas, comp.map(r => r.clientes_unicos), "Clientes", "#8957e5");
  renderBarSingle("chartEvoVendedores", semanas, comp.map(r => r.vendedores_unicos), "Vendedores", "#1abc9c");

  const tbody = document.getElementById("tabelaComparativoBody");
  tbody.innerHTML = comp.map(r => `<tr>
    <td><strong>${r.semana}</strong></td>
    <td>${formatMoney(r.faturamento)}</td>
    <td>${formatNum(r.qtd_vendas)}</td>
    <td>${formatMoney(r.ticket_medio)}</td>
    <td>${formatNum(r.clientes_unicos)}</td>
    <td>${formatNum(r.vendedores_unicos)}</td>
  </tr>`).join("");

  if (state.dtComparativo) { state.dtComparativo.destroy(); }
  state.dtComparativo = $("#tabelaComparativo").DataTable({ paging: false, searching: false, info: false, order: [] });
}

// ---- Filters ----
function setTipo(btn) {
  document.querySelectorAll("#tipoCampanha .tab-btn").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  state.tipo = btn.dataset.value;
  loadDashboard();
}

function onSemanaChange() {
  state.semana = document.getElementById("semanaSelect").value;
  loadDashboard();
}

function atualizarSemanas(semanas) {
  const sel = document.getElementById("semanaSelect");
  const current = sel.value;
  sel.innerHTML = `<option value="Todas">📅 Todas as Semanas</option>`;
  (semanas || []).forEach(s => {
    const opt = document.createElement("option");
    opt.value = s; opt.textContent = s;
    if (s === current) opt.selected = true;
    sel.appendChild(opt);
  });
  state.semana = sel.value;
}

function showView(view) {
  state.view = view;
  document.getElementById("viewDashboard").style.display = view === "dashboard" ? "" : "none";
  document.getElementById("viewComparativo").style.display = view === "comparativo" ? "" : "none";
  document.getElementById("btnDashboard").classList.toggle("active", view === "dashboard");
  document.getElementById("btnComparativo").classList.toggle("active", view === "comparativo");
  loadDashboard();
}

// ---- Exports ----
function exportarExcel() {
  window.location.href = `/api/exportar_excel?tipo=${encodeURIComponent(state.tipo)}&semana=${encodeURIComponent(state.semana)}`;
  showToast("📊 Exportando Excel...", "info");
}

function exportarPDF() {
  showToast("📄 Gerando PDF...", "info");
  const { jsPDF } = window.jspdf;
  html2canvas(document.getElementById("mainContent"), { backgroundColor: "#0d1117", scale: 1.5, useCORS: true, logging: false })
    .then(canvas => {
      const imgData = canvas.toDataURL("image/png");
      const pdf = new jsPDF("l", "mm", "a3");
      const pw = pdf.internal.pageSize.getWidth(), ph = pdf.internal.pageSize.getHeight();
      const ratio = Math.min(pw / canvas.width, ph / canvas.height);
      pdf.setFillColor(13, 17, 23); pdf.rect(0, 0, pw, ph, "F");
      pdf.setTextColor(212, 160, 23); pdf.setFontSize(16); pdf.setFont("helvetica", "bold");
      pdf.text("CAMPANHA COPA — Dashboard Executivo", 14, 14);
      pdf.setTextColor(139, 148, 158); pdf.setFontSize(9); pdf.setFont("helvetica", "normal");
      pdf.text(`${state.tipo} | ${state.semana} | Gerado em ${new Date().toLocaleString("pt-BR")}`, 14, 20);
      pdf.addImage(imgData, "PNG", (pw - canvas.width*ratio) / 2, 26, canvas.width*ratio, canvas.height*ratio - 26);
      pdf.save(`Dashboard_${state.tipo.replace(/\s/g,"_")}_${state.semana.replace(/\s/g,"_")}.pdf`);
      showToast("✅ PDF gerado!", "success");
    });
}

function baixarPNG() {
  showToast("🖼️ Capturando tela...", "info");
  html2canvas(document.getElementById("mainContent"), { backgroundColor: "#0d1117", scale: 2, useCORS: true })
    .then(canvas => {
      const link = document.createElement("a");
      link.download = `Dashboard_${state.tipo.replace(/\s/g,"_")}_${state.semana.replace(/\s/g,"_")}.png`;
      link.href = canvas.toDataURL(); link.click();
      showToast("✅ PNG salvo!", "success");
    });
}

// ---- Helpers ----
function destroyChart(id) { if (state.charts[id]) { state.charts[id].destroy(); delete state.charts[id]; } }
function formatMoney(v) { if (v == null || isNaN(v)) return "—"; return "R$ " + Number(v).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
function formatNum(v) { if (v == null || isNaN(v)) return "—"; return Number(v).toLocaleString("pt-BR"); }
function abrevMoney(v) { if (Math.abs(v) >= 1e6) return "R$ " + (v/1e6).toFixed(1) + "M"; if (Math.abs(v) >= 1e3) return "R$ " + (v/1e3).toFixed(0) + "k"; return "R$ " + v; }
function truncate(str, max) { if (!str) return ""; return str.length > max ? str.substring(0, max) + "…" : str; }
function showLoading(show) { document.getElementById("loadingOverlay").classList.toggle("show", show); }
function setStatus(text, ok = true) {
  const bar = document.getElementById("statusBar"), span = document.getElementById("statusText");
  span.textContent = text;
  bar.style.color = ok ? "var(--accent-green-light)" : "var(--accent-red)";
  bar.style.borderColor = ok ? "rgba(63,185,80,0.3)" : "rgba(182,35,36,0.3)";
  bar.style.background = ok ? "rgba(35,134,54,0.1)" : "rgba(182,35,36,0.1)";
}
function updateFooter(arquivos, total) {
  const el = document.getElementById("footerArquivos");
  if (arquivos && arquivos.length) el.textContent = `Arquivos: ${arquivos.join(" | ")}`;
}
function updateTimestamp() { const el = document.getElementById("footerTimestamp"); if (el) el.textContent = new Date().toLocaleString("pt-BR"); }
function showToast(msg, type = "info") {
  const el = document.createElement("div");
  el.className = `toast toast-${type}`; el.innerHTML = msg;
  document.body.appendChild(el);
  setTimeout(() => { el.style.animation = "slideOut 0.3s ease forwards"; setTimeout(() => el.remove(), 300); }, 3500);
}
