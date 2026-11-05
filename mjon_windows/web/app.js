/* MJON AI OS · Native Windows local client. No external requests or CDNs. */
"use strict";
const byId = (id) => document.getElementById(id);
const pages = ["inicio","jarvis","modelos","agentes","studio","proyectos","aplicaciones","configuracion","seguridad","rendimiento"];
let overview = null;
let models = [];
let busy = false;
function setText(id, value) {
  const node = byId(id);
  if (node) node.textContent = String(value);
}
function formatBytes(value) {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) return "Sin datos";
  return (value / (1024 ** 3)).toLocaleString("es-AR", {maximumFractionDigits: 1}) + " GB";
}
function notify(message) {
  const el = byId("toast");
  el.textContent = String(message);
  el.classList.add("visible");
  clearTimeout(notify.timer);
  notify.timer = setTimeout(() => el.classList.remove("visible"), 5500);
}
function activatePage(id) {
  if (!pages.includes(id)) return;
  document.querySelectorAll(".page").forEach((node) => node.classList.toggle("active", node.id === "page-" + id));
  document.querySelectorAll(".nav").forEach((node) => {
    const selected = node.dataset.page === id;
    node.classList.toggle("active", selected);
    if (selected) node.setAttribute("aria-current", "page");
    else node.removeAttribute("aria-current");
  });
  if (id === "modelos" || id === "jarvis") refreshModels();
  if (id === "rendimiento" || id === "inicio") refreshOverview();
  if (id === "agentes" || id === "aplicaciones" || id === "studio") refreshOverview();
  window.scrollTo({top: 0, behavior: "instant"});
}
async function api(path, body) {
  const options = { cache: "no-store" };
  if (body !== undefined) {
    options.method = "POST";
    options.headers = {"Content-Type": "application/json"};
    options.body = JSON.stringify(body);
  }
  const response = await fetch(path, options);
  let json;
  try { json = await response.json(); } catch { throw new Error("Respuesta local no válida."); }
  if (!response.ok) throw new Error(json.error || "Solicitud rechazada (" + response.status + ").");
  return json;
}
function moduleCard(m) {
  const card = document.createElement("div");
  card.className = "module-card";
  const title = document.createElement("strong");
  title.textContent = m.name || m.id || "Módulo sin nombre";
  const domain = document.createElement("small");
  domain.textContent = m.domain || "Sin categoría";
  const state = document.createElement("span");
  state.className = "state";
  const labels = {installed_unverified: "Instalado · no verificado", not_installed: "No instalado", remote_opt_in: "Externo · requiere autorización"};
  state.textContent = labels[m.status] || "Estado desconocido";
  card.append(title, domain, state);
  return card;
}
function fillModules() {
  const modules = overview?.modules || [];
  for (const [id, candidates] of [
    ["agent-list", modules.filter(x => ["agents","automation","security","knowledge"].includes(x.domain))],
    ["studio-list", modules.filter(x => ["programming","training","optimization"].includes(x.domain))],
    ["app-list", modules]
  ]) {
    const target = byId(id);
    target.replaceChildren();
    if (!candidates.length) {
      const p = document.createElement("p");
      p.className = "muted";
      p.textContent = "No se detectaron módulos en esta categoría.";
      target.append(p);
    } else candidates.forEach(m => target.append(moduleCard(m)));
  }
}
async function refreshOverview() {
  try {
    const data = await api("/api/overview");
    overview = data;
    const d = data.diagnostics || {};
    setText("home-ram", formatBytes(d.memory_total_bytes));
    setText("home-disk", formatBytes(d.disk_free_bytes));
    setText("home-ollama", d.ollama === "installed_unverified" ? "Detectado · sin probar" : "No instalado");
    setText("health-os", (d.platform || "Windows") + " " + (d.release || ""));
    setText("health-arch", d.architecture || "Sin datos");
    setText("health-ram", formatBytes(d.memory_total_bytes));
    setText("health-disk", formatBytes(d.disk_free_bytes));
    setText("overview-hint", "Datos obtenidos del sistema local");
    setText("connection-state", "Equipo local");
    fillModules();
  } catch (error) {
    setText("connection-state", "Error local");
    setText("overview-hint", error.message);
    notify("No se pudo leer el diagnóstico local: " + error.message);
  }
}
async function refreshModels() {
  const selector = byId("chat-model");
  const previous = selector.value;
  selector.replaceChildren();
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Buscando Ollama local…";
  selector.append(placeholder);
  const list = byId("model-list");
  list.replaceChildren();
  try {
    const result = await api("/api/models");
    models = Array.isArray(result.models) ? result.models.filter(x => typeof x === "string" && x.length < 200) : [];
    setText("models-reason", result.reason || "Modelos descargados (sin prueba de generación).");
    if (!models.length) {
      placeholder.textContent = "No se detectaron modelos locales";
      const info = document.createElement("p");
      info.className = "muted";
      info.textContent = "No se generarán respuestas simuladas. Instalá Ollama y un modelo pequeño de forma explícita para comenzar.";
      list.append(info);
    }
    for (const model of models) {
      const option = document.createElement("option");
      option.value = model;
      option.textContent = model;
      selector.append(option);
      const card = document.createElement("div");
      card.className = "module-card";
      const heading = document.createElement("strong");
      heading.textContent = model;
      const state = document.createElement("small");
      state.textContent = "Descargado · aún no se verificó generación";
      card.append(heading, state);
      list.append(card);
    }
    selector.value = models.includes(previous) ? previous : (models[0] || "");
  } catch (error) {
    placeholder.textContent = "Error consultando Ollama";
    setText("models-reason", error.message);
  }
}
function addMessage(kind, message) {
  const item = document.createElement("div");
  item.className = "message " + kind;
  item.textContent = String(message);
  const log = byId("messages");
  log.append(item);
  log.scrollTop = log.scrollHeight;
}
async function sendChat(event) {
  event.preventDefault();
  if (busy) return;
  const prompt = byId("chat-prompt").value.trim();
  const model = byId("chat-model").value;
  if (!prompt || !model) { notify("Elegí un modelo descargado y escribí una consulta."); return; }
  if (prompt.length > 1024 || model.length > 200) return;
  busy = true;
  byId("send-chat").disabled = true;
  addMessage("user", prompt);
  byId("chat-prompt").value = "";
  try {
    const response = await api("/api/ask", {prompt, model});
    addMessage("assistant", response.answer);
    notify("Generación local real · " + response.model);
  } catch (error) {
    addMessage("error", "No se generó una respuesta: " + error.message);
  } finally {
    busy = false;
    byId("send-chat").disabled = false;
  }
}
async function openSetting(section) {
  try {
    const result = await api("/api/settings", {section});
    notify("Se abrió Configuración de Windows: " + result.opened);
  } catch (error) {
    notify("No se pudo abrir Windows: " + error.message);
  }
}
function updateClock() {
  const dt = new Date();
  const text = dt.toLocaleTimeString("es-AR", {hour: "2-digit", minute: "2-digit"});
  setText("clock", text);
  setText("dock-clock", text);
}
function init() {
  document.querySelectorAll("[data-page]").forEach((node) => node.addEventListener("click", () => activatePage(node.dataset.page)));
  document.querySelectorAll("[data-settings]").forEach((node) => node.addEventListener("click", () => openSetting(node.dataset.settings)));
  byId("refresh-models").addEventListener("click", refreshModels);
  byId("refresh-health").addEventListener("click", refreshOverview);
  byId("chat-form").addEventListener("submit", sendChat);
  const search = byId("quick-search");
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault(); search.focus(); search.select();
    }
    if (event.key === "Escape" && document.activeElement === search) search.blur();
  });
  search.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    const query = search.value.toLowerCase().trim();
    const matching = pages.find(id => id.includes(query) || (id === "configuracion" && query.includes("ajustes")));
    if (matching) { activatePage(matching); search.value = ""; }
    else if (query) notify("No hay acción disponible para esa búsqueda. No se ejecutó ningún comando.");
  });
  updateClock();
  setInterval(updateClock, 30000);
  refreshOverview();
  refreshModels();
}
document.addEventListener("DOMContentLoaded", init);
