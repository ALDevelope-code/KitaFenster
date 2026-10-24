"use strict";
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const escapeHTML = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
const e = escapeHTML;
const modes = {
  photos: "Fotos",
  plan: "Dokument",
  messages: "Meldungen",
  mixed: "Gemischt",
  black: "Ruhezeit",
  sleep: "Ruhemodus",
};
const pages = {
  overview: "Übersicht",
  devices: "Bilderrahmen",
  groups: "Gruppen & NAS",
  content: "Inhalte",
  operating: "Betriebszeiten",
  branding: "Einrichtung",
};
const days = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];
let state = {
  groups: [],
  devices: [],
  notices: [],
  operating_hours: operatingDefaults(),
  documents: [],
  snapshots: [],
};
let csrf = "",
  page = "overview",
  toastTimer;
const defaults = {
  default_mode: "photos",
  interval: 12,
  order: "name",
  fit: "contain",
  transition: "fade",
  transition_seconds: 0.6,
  rotation: 0,
  timezone: "Europe/Berlin",
  operating_hours_override: null,
  content_windows_enabled: true,
  document_id: null,
  content_windows: [],
  motion: { enabled: false, idle_minutes: 5, power_mode: "hdmi" },
  playlist: [
    { mode: "photos", seconds: 12 },
    { mode: "plan", seconds: 20 },
    { mode: "messages", seconds: 15 },
  ],
};

function toast(message) {
  $("#toast").textContent = message;
  $("#toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    $("#toast").hidden = true;
  }, 5000);
}
function showLogin() {
  $("#dialog").close();
  $("#app").hidden = true;
  $("#login").hidden = false;
}
async function api(path, method = "GET", body) {
  const options = { method, credentials: "same-origin", headers: {} };
  if (method !== "GET") options.headers["X-CSRF-Token"] = csrf;
  if (body instanceof FormData) options.body = body;
  else if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const response = await fetch("/api" + path, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && path !== "/login") {
      $("#dialog").close();
      showLogin();
    }
    const detail = Array.isArray(data.detail)
      ? data.detail
          .map((x) => `${x.loc?.slice(1).join(".")}: ${x.msg}`)
          .join(" · ")
      : data.detail;
    throw new Error(detail || "Die Anfrage konnte nicht ausgeführt werden.");
  }
  return data;
}
async function refresh(render = true) {
  state = await api("/admin/state");
  applyBranding(state.branding);
  $("[data-server-version]").textContent = `Serverversion ${state.server_version}`;
  if (render) renderPage();
}
function applyBranding(branding) {
  if (!branding) return;
  document.title = `KitaFenster · ${branding.name}`;
  $$("[data-kita-name]").forEach((node) => {
    node.textContent = branding.name;
  });
  $$("[data-kita-logo]").forEach((node) => {
    if (node.getAttribute("src") !== branding.logo_url)
      node.src = branding.logo_url;
    node.alt = `Logo · ${branding.name}`;
  });
  $("link[rel=icon]").href = branding.logo_url;
}

function renderBranding() {
  const b = state.branding;
  return (
    head(
      "Euer Name. Eure Momente.",
      "Richtet KitaFenster für eure Einrichtung ein.",
    ) +
    `<div class="branding-grid"><section class="panel branding-card"><p class="eyebrow">EURE EINRICHTUNG</p>
    <h2>${e(b.name)}</h2><p class="muted">Dieser Name erscheint bei der Anmeldung und in der Verwaltung.</p>
    ${button("branding-name", "Namen ändern")}
    <div class="form-section"><h3>Gruppen &amp; Bilderrahmen</h3><p class="muted">Die Beispielgruppen lassen sich passend zu eurer Kita umbenennen und um weitere Gruppen ergänzen.</p>
    ${button("nav", "Gruppen einrichten →", "groups")}</div></section>
    <section class="panel branding-card"><p class="eyebrow">EUER LOGO</p>
    <div class="branding-preview"><img src="${e(b.logo_url)}" alt="Aktuelles Logo der Einrichtung"></div>
    <p class="help">${b.custom_logo ? "Euer eigenes Logo ist aktiv." : "Das neutrale Beispiel-Logo ist aktiv."} PNG, JPEG oder WebP · bis 2 MB.</p>
    <div class="row-actions">${button("branding-logo", "Logo hochladen", "", true)}${b.custom_logo ? button("branding-reset", "Beispiel-Logo verwenden") : ""}</div>
    <p class="help">Name und Logo sind auch vor der Anmeldung sichtbar. Verwendet dafür Inhalte, die öffentlich sichtbar sein dürfen.</p></section></div>
    <div class="hint">KitaFenster bleibt der Name der Anwendung. Euer Logo und eure Einstellungen gehören nur zu eurer Installation und werden bei einer Datensicherung mitgesichert.</div>
    <section class="panel form-section"><h2>Softwareversion</h2><p><strong>KitaFenster · Serverversion ${e(state.server_version)}</strong></p><p class="help">Diese Version läuft aktuell auf eurem NAS-Server. Die Pi-Player werden separat aktualisiert.</p></section>
    <p class="help license-links">Freie Software unter AGPLv3 · <a href="/api/license" target="_blank" rel="noopener">Lizenz lesen</a> · <a href="/api/source">Quellcode herunterladen</a></p>`
  );
}
function brandingNameEditor() {
  dialog(
    "Name der Einrichtung",
    `<label>Kita-Name<input name="name" value="${e(state.branding.name)}" maxlength="80" required></label>`,
    async (data) => {
      await api("/admin/branding", "PUT", { name: data.get("name").trim() });
      await saved("Der Name eurer Einrichtung wurde gespeichert.");
    },
  );
}
function brandingLogoEditor() {
  dialog(
    "Euer Logo hochladen",
    `<label>Logo-Datei<input name="file" type="file" accept="image/png,image/jpeg,image/webp" required></label>
    <p class="help">PNG, JPEG oder WebP, maximal 2 MB und 4 Millionen Bildpunkte. Transparenz bleibt erhalten; das Bild wird auf höchstens 512 × 512 Pixel verkleinert.</p>
    <div class="branding-preview" id="logo-selection" hidden><img alt="Vorschau des ausgewählten Logos"></div>`,
    async (data) => {
      const file = data.get("file");
      if (file.size > 2 * 1024 * 1024)
        throw new Error("Das Logo darf höchstens 2 MB groß sein.");
      const upload = new FormData();
      upload.append("file", file);
      await api("/admin/branding/logo", "POST", upload);
      await saved("Euer Logo wurde gespeichert.");
    },
    "Logo speichern",
  );
  let previewUrl;
  const revoke = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  };
  $("#dialog").addEventListener("close", revoke, { once: true });
  $('input[name="file"]', $("#editor")).onchange = (event) => {
    revoke();
    const file = event.target.files[0],
      preview = $("#logo-selection");
    preview.hidden = true;
    if (
      file &&
      file.size <= 2 * 1024 * 1024 &&
      ["image/png", "image/jpeg", "image/webp"].includes(file.type)
    ) {
      previewUrl = URL.createObjectURL(file);
      $("img", preview).src = previewUrl;
      preview.hidden = false;
    }
  };
}
function date(value) {
  return value
    ? new Intl.DateTimeFormat("de-DE", {
        dateStyle: "short",
        timeStyle: "short",
      }).format(new Date(value))
    : "Noch nicht verbunden";
}
function relative(value) {
  if (!value) return "Noch nicht synchronisiert";
  const minutes = Math.max(
    0,
    Math.floor((Date.now() - new Date(value).getTime()) / 60000),
  );
  return minutes < 1
    ? "Gerade eben"
    : minutes < 60
      ? `Vor ${minutes} Min.`
      : date(value);
}
function localInput(value) {
  if (!value) return "";
  const d = new Date(value);
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}
const iso = (value) => (value ? new Date(value).toISOString() : null);
const option = (value, label, selected) =>
  `<option value="${e(value)}" ${String(value) === String(selected) ? "selected" : ""}>${e(label)}</option>`;
const modeOptions = (selected, automatic = false) =>
  (automatic ? option("", "Automatisch · Inhaltszeitfenster / Standard", selected) : "") +
  Object.entries(modes)
    .filter(([key]) => !["black", "sleep"].includes(key))
    .map(([key, label]) => option(key, label, selected))
    .join("");
const groupOf = (device) => state.groups.find((g) => g.id === device.group_id);
const snapshotOf = (id) => state.snapshots.find((s) => s.id === id) || {};
function targetName(target) {
  return target.kind === "all"
    ? "Alle Bilderrahmen"
    : state[target.kind === "group" ? "groups" : "devices"].find(
        (x) => x.id === target.id,
      )?.name || "Entferntes Ziel";
}
function targetOptions(selected = { kind: "all", id: "" }) {
  const key = selected.kind + ":" + (selected.id || "");
  return (
    option("all:", "Alle Bilderrahmen", key) +
    '<optgroup label="Gruppen">' +
    state.groups.map((g) => option("group:" + g.id, g.name, key)).join("") +
    '</optgroup><optgroup label="Einzelne Geräte">' +
    state.devices.map((d) => option("device:" + d.id, d.name, key)).join("") +
    "</optgroup>"
  );
}
function readTarget(value) {
  const [kind, id] = value.split(":");
  return { kind, id };
}
function badge(label, type = "", dot = false) {
  return `<span class="badge ${e(type)}">${dot ? '<span class="dot"></span>' : ""}${e(label)}</span>`;
}
function head(title, subtitle, actions = "") {
  return `<div class="page-head"><div><p class="eyebrow">KITAFENSTER</p><h1>${title}</h1><p class="muted">${subtitle}</p></div><div class="head-actions">${actions}</div></div>`;
}
function empty(title, text, action = "") {
  return `<div class="empty"><span class="empty-symbol">▧</span><h2>${title}</h2><p>${text}</p>${action}</div>`;
}
function button(action, text, id = "", primary = false) {
  return `<button ${primary ? 'class="primary"' : ""} data-action="${action}" data-id="${e(id)}">${text}</button>`;
}
function deviceCard(device) {
  const group = groupOf(device),
    snapshot = snapshotOf(device.group_id);
  const photo = snapshot.photos?.[0];
  return `<article class="device-card"><div class="device-image"><span class="device-badge">${device.settings.rotation % 180 ? "↕ Hochformat" : "↔ Querformat"}</span><div class="screen-mini">${photo ? `<img src="/api/admin/assets/${e(photo)}" alt="Beispielfoto der Gruppe ${e(group?.name)}" loading="lazy">` : `<strong>${e(group?.name)}</strong><span>Unsere gemeinsamen Momente</span>`}</div></div><div class="device-body"><div class="device-title"><h3>${e(group?.name)}</h3>${badge(device.online ? "Verbunden" : "Offline", device.online ? "" : "offline", true)}</div><p class="device-subtitle">${e(device.name)} · ${device.allow_internal ? "Interne Anzeige" : "Für Eltern"}</p><div class="device-state"><span>Soll-Anzeige</span><strong>${e(modes[device.effective.mode] || device.effective.mode)}</strong></div><div class="device-foot"><span>${e(device.effective.reason)}</span><button data-action="device" data-id="${e(device.id)}">Verwalten →</button></div></div></article>`;
}
function renderOverview() {
  const online = state.devices.filter((d) => d.online).length;
  const photos = state.snapshots.reduce(
    (sum, s) => sum + (s.photos?.length || 0),
    0,
  );
  const active = state.notices.filter(
    (n) =>
      (!n.starts_at || Date.now() >= new Date(n.starts_at)) &&
      (!n.ends_at || Date.now() < new Date(n.ends_at)),
  );
  return (
    head(
      "Alles im Blick.",
      "Ein guter Tag beginnt mit gemeinsamen Momenten.",
    ) +
    `<section class="hero"><div class="hero-copy"><p class="eyebrow">AUS DEM GRUPPENALLTAG</p><h2>Ein kleines Fenster. Ganz viel Kita.</h2><p>Teilt die schönsten Momente und alles, was Eltern wissen sollten — direkt in den Vorräumen eurer Gruppen.</p></div><div class="hero-art" aria-hidden="true"><div class="mini-frame"></div><div class="art-leaf"></div></div></section><div class="stats"><div class="stat"><span class="stat-symbol">▣</span><div><div class="stat-value">${online}<span class="muted"> / ${state.devices.length}</span></div><div class="stat-label">Bilderrahmen verbunden</div></div></div><div class="stat"><span class="stat-symbol">▧</span><div><div class="stat-value">${photos}</div><div class="stat-label">Fotos auf dem NAS</div></div></div><div class="stat"><span class="stat-symbol">▤</span><div><div class="stat-value">${active.length}</div><div class="stat-label">Aktuelle Meldungen</div></div></div></div><div class="section-head"><div><h2>Eure Bilderrahmen</h2><p class="muted">Die Vorschaukarten zeigen ein Gruppenfoto, nicht den Live-Bildschirm.</p></div><button class="text-button" data-action="nav" data-id="devices">Alle verwalten →</button></div>` +
    (state.devices.length
      ? `<div class="device-grid">${state.devices.map(deviceCard).join("")}</div>`
      : empty(
          "Der erste Bilderrahmen wartet.",
          "Registriert einen Rahmen, ordnet ihm eine Gruppe zu und koppelt den Raspberry Pi mit dem angezeigten Code.",
          button("device", "＋ Ersten Bilderrahmen hinzufügen", "new", true),
        )) +
    `<div class="lower-grid"><section class="panel"><div class="section-head"><h2>Aktuelle Meldungen</h2><button class="text-button" data-action="nav" data-id="content">Alle Inhalte →</button></div>${
      active.length
        ? active
            .slice(0, 3)
            .map(
              (n) =>
                `<div class="row-item"><span class="row-icon">${n.urgent ? "!" : "▤"}</span><div><strong>${e(n.title)}</strong><p>${e(targetName(n.target))} · ${n.ends_at ? "Bis " + e(date(n.ends_at)) : "Ohne Ablaufdatum"}</p></div>${badge(n.urgent ? "Sofortmeldung" : n.internal ? "Intern" : "Für Eltern", n.urgent ? "attention" : n.internal ? "internal" : "public")}</div>`,
            )
            .join("")
        : '<p class="muted tiny">Noch keine aktuellen Meldungen. Eine Begrüßung ist ein schöner Anfang.</p>'
    }</section><section class="panel"><h2>Betriebszeiten und Inhalte</h2><p class="muted tiny">Betriebszeiten geben den Rahmen frei. Inhaltszeitfenster am Rahmen wählen die passenden Inhalte.</p><div class="row-item"><span class="row-icon">◷</span><div><strong>${e(operatingSummary(state.operating_hours))}</strong><p>Zentraler Standard · eigene Betriebszeiten sind je Rahmen möglich</p></div><button class="text-button" data-action="nav" data-id="operating">Einrichten →</button></div><div class="priority-list"><span>1 Sofortmeldung</span><span>2 Betriebszeiten / Bewegungspause</span><span>3 Manuell</span><span>4 Inhaltszeitfenster</span><span>5 Standardinhalt</span></div></section></div>`
  );
}
function storageLabel(storage) {
  if (!storage || !storage.total_bytes || !Number.isFinite(storage.free_bytes))
    return "Speicher: noch keine Meldung vom Pi";
  const gib = (bytes) => (bytes / (1024 ** 3)).toLocaleString("de-DE", { maximumFractionDigits: 1 });
  const percent = Math.round(100 * storage.free_bytes / storage.total_bytes);
  const prefix = storage.free_bytes <= storage.reserved_bytes ? "Speicher knapp: " : "Speicher frei: ";
  return `${prefix}${gib(storage.free_bytes)} von ${gib(storage.total_bytes)} GiB (${percent} %)`;
}
function renderDevices() {
  return (
    head(
      "Eure Bilderrahmen",
      "Jede Gruppe hat ihr eigenes Fenster. Hier laufen die Fäden zusammen.",
      button("control", "⇄ Anzeige wechseln") +
        button("device", "＋ Rahmen hinzufügen", "new", true),
    ) +
    (state.devices.length
      ? `<div class="table-wrap"><table><thead><tr><th>Bilderrahmen</th><th>Verbindung</th><th>Anzeige</th><th>Letzter Abgleich</th><th>Aktionen</th></tr></thead><tbody>${state.devices.map((d) => `<tr><td><strong>${e(d.name)}</strong><small>${e(groupOf(d)?.name)} · ${d.allow_internal ? "Intern freigegeben" : "Elternbereich"}</small></td><td>${badge(d.online ? "Verbunden" : "Offline", d.online ? "" : "offline", true)}<small>${e(date(d.last_seen))}</small><small>${d.reported?.local_ip ? "Geräte-IP: " + e(d.reported.local_ip) : "Geräte-IP: noch keine Meldung vom Player"}</small></td><td>${e(modes[d.effective.mode])}<small>${e(d.effective.reason)}</small>${d.effective.secondary ? `<small>Zusatz: ${e(modes[d.effective.secondary.mode])} · ${e(d.effective.secondary.reason)}</small>` : ""}<small>Gemeldet: ${e(modes[d.reported?.mode] || "Noch keine Rückmeldung")}</small><small>${e(d.reported?.reason || "")}</small></td><td>${e(relative(d.reported?.last_sync))}<small>${e(storageLabel(d.reported?.storage))}</small><small>${e(d.reported?.error || "")}</small></td><td><div class="row-actions"><button class="small" data-action="preview" data-id="${d.id}">Vorschau</button><button class="small" data-action="device" data-id="${d.id}">Verwalten</button></div></td></tr>`).join("")}</tbody></table></div><p class="help">Änderungen erreichen verbundene Geräte normalerweise innerhalb von 15 Sekunden. Offline-Geräte übernehmen sie nach der nächsten Verbindung. Die Geräte-IP meldet der aktualisierte Player selbst. Angezeigt wird die Adresse seiner Verbindung zur Zentrale; ob sie über VPN erreichbar ist, hängt vom Netz ab.</p>`
      : empty(
          "Noch kein Rahmen verbunden.",
          "Füge einen Raspberry Pi hinzu und wähle die passende Gruppe.",
          button("device", "＋ Rahmen hinzufügen", "new", true),
        ))
  );
}
function groupIconHTML(group, index = 0) {
  return group.icon_url
    ? `<img src="${e(group.icon_url)}" alt="" loading="lazy">`
    : ["⚑", "≋", "✳"][Math.max(0, index) % 3];
}
function renderGroups() {
  return (
    head(
      "Eure Gruppen. Viele Geschichten.",
      "Gruppen, Gruppenbilder und Fotoordner auf eurem Synology-NAS verwalten.",
      button("scan", "↻ NAS abgleichen") +
        button("group", "＋ Gruppe hinzufügen", "new", true),
    ) +
    `<div class="group-grid">${state.groups
      .map((g, i) => {
        const s = snapshotOf(g.id);
        return `<section class="panel group-panel"><div class="group-icon">${groupIconHTML(g, i)}</div><h2>${e(g.name)}</h2><p class="muted">NAS-Ordner: ${e(g.folder)}</p><div class="group-count">${s.photos?.length || 0}<small>Fotos</small></div>${badge(s.error ? "Abgleich prüfen" : s.last_sync ? "NAS abgeglichen" : "Noch kein Abgleich", s.error ? "attention" : "", true)}<p class="muted">${e(s.error || relative(s.last_sync))}</p><button class="full" data-action="group" data-id="${g.id}">Gruppe bearbeiten</button></section>`;
      })
      .join(
        "",
      )}</div><div class="hint">Die Ordner werden auf dem NAS nur gelesen. Ein fehlender oder nicht lesbarer Ordner behält seinen letzten erfolgreichen Stand. Ein vorhandener, leerer Ordner leert die Fotoanzeige beim nächsten erfolgreichen Abgleich.</div>`
  );
}
function noticeHTML(n) {
  return `<div class="notice-preview ${e(n.theme || "ocean")}"><span class="tag">${n.urgent ? "Wichtige Information" : "Aus unserer Kita"}</span>${n.image ? `<img src="${e(n.image)}" alt="Meldungsbild">` : ""}<h3>${e(n.title || "Eure Überschrift")}</h3><p>${e(n.text || "")}</p></div>`;
}
function renderContent() {
  return (
    head(
      "Was möchtet ihr teilen?",
      "Meldungen, Elterninfos und Dokumente für eure Gruppen.",
      button("notice", "＋ Meldung erstellen", "new", true),
    ) +
    (state.notices.length
      ? `<div class="content-grid">${state.notices
          .map((n) => {
            const image = state.documents.find((d) => d.id === n.image_id)
              ?.assets[0];
            return `<article class="notice-card">${noticeHTML({ ...n, image: image ? "/api/admin/assets/" + image : null })}<div class="notice-card-foot">${badge(n.internal ? "Intern" : "Für Eltern", n.internal ? "internal" : "public")}${n.urgent ? badge("Sofortmeldung", "attention") : ""}<button class="small" data-action="notice" data-id="${n.id}">Bearbeiten</button></div><div class="notice-card-meta">${e(targetName(n.target))} · ${n.starts_at ? e(date(n.starts_at)) : "Ab sofort"}${n.ends_at ? " – " + e(date(n.ends_at)) : " · Ohne Ablauf"}</div></article>`;
          })
          .join("")}</div>`
      : empty(
          "Was gibt es Neues?",
          "Begrüßt Eltern, kündigt ein Fest an oder informiert über den nächsten Ausflug.",
          button("notice", "Erste Meldung erstellen", "new", true),
        )) +
    `<div class="toolbar document-toolbar"><div><h2>Dokumente &amp; Bilder</h2><p class="muted tiny">Speisepläne, Elterninformationen und weitere Dokumente. Art und Freigabe lassen sich jederzeit bearbeiten.</p></div><div class="document-upload-actions">${button("upload", "↑ Dokument (PDF) hochladen", "plan")}${button("upload", "↑ Meldungsbild hochladen", "image")}</div></div>` +
    (state.documents.length
      ? `<div class="table-wrap"><table><thead><tr><th>Datei</th><th>Art</th><th>Seiten</th><th>Hochgeladen</th><th></th></tr></thead><tbody>${state.documents.map((d) => `<tr><td><strong>${e(d.name)}</strong>${d.kind === "plan" ? `<small>${e(documentListLabel(d))}</small>` : ""}</td><td>${e(documentCategory(d))}<small>${d.kind === "plan" ? d.public ? "Für Eltern freigegeben" : d.parent_groups?.length ? "Bisherige Elternfreigabe für einzelne Gruppen" : "Nur intern" : "Für Meldungen"}</small></td><td>${d.assets.length}</td><td>${e(date(d.created_at))}</td><td><div class="row-actions"><button class="small" data-action="document-edit" data-id="${d.id}">Bearbeiten</button><button class="small" data-action="document-preview" data-id="${d.id}">Vorschau</button>${d.kind === "plan" ? `<button class="small" data-action="assign-plan" data-id="${d.id}">Dokumentenliste</button>` : ""}<button class="small danger" data-action="delete-document" data-id="${d.id}">Entfernen</button></div></td></tr>`).join("")}</tbody></table></div>`
      : '<p class="muted">Noch keine Dateien hochgeladen.</p>') +
    `<div class="hint">Unter „Dokumentenliste“ wählst du, welche Dokumente für alle oder ausgewählte Gruppen gemeinsam laufen. Am Rahmen die Quelle „Gemeinsame Dokumentenliste“ einstellen. Unter „Bearbeiten“ legst du fest, ob ein Dokument nur intern angezeigt werden darf. Ohne Listenaufnahme bleibt es direkt auswählbar.</div>`
  );
}
function renderPage() {
  $("#main").innerHTML = {
    overview: renderOverview,
    devices: renderDevices,
    groups: renderGroups,
    content: renderContent,
    operating: renderOperatingHours,
    branding: renderBranding,
  }[page]();
  $("#breadcrumb").textContent = pages[page];
  $$("[data-nav]").forEach((b) =>
    b.classList.toggle("active", b.dataset.nav === page),
  );
  $("#today").textContent = new Intl.DateTimeFormat("de-DE", {
    weekday: "long",
    day: "numeric",
    month: "long",
  }).format(new Date());
}
function navigate(to) {
  page = pages[to] ? to : "overview";
  history.replaceState(null, "", "#" + page);
  renderPage();
}
let dialogCleanup = () => {};
$("#dialog").addEventListener("close", () => dialogCleanup());
function dialog(title, html, submit, submitLabel = "Speichern") {
  dialogCleanup();
  dialogCleanup = () => {};
  $("#dialog-content").innerHTML =
    `<div class="dialog-head"><h2>${e(title)}</h2><button class="text-button" data-close aria-label="Schließen">✕</button></div><div class="dialog-body">${submit ? '<form id="editor">' : ""}${html}${submit ? `<p class="form-error" id="editor-error" role="alert"></p><div class="dialog-actions"><button type="button" data-close>Abbrechen</button><button type="submit" class="primary">${e(submitLabel)}</button></div></form>` : ""}</div>`;
  $$("[data-close]", $("#dialog")).forEach(
    (b) => (b.onclick = () => $("#dialog").close()),
  );
  if (submit)
    $("#editor").onsubmit = async (event) => {
      event.preventDefault();
      const form = event.currentTarget,
        saves = $$("button[type=submit]", form);
      saves.forEach((save) => (save.disabled = true));
      $("#editor-error").textContent = "";
      try {
        await submit(new FormData(form), form);
      } catch (error) {
        $("#editor-error").textContent = error.message;
      } finally {
        saves.forEach((save) => {
          if (save.isConnected) save.disabled = false;
        });
      }
    };
  if (!$("#dialog").open) $("#dialog").showModal();
}
async function saved(
  message = "Gespeichert. Die Geräte übernehmen die Änderung beim nächsten Abgleich.",
) {
  $("#dialog").close();
  await refresh();
  toast(message);
}
function check(name, label, checked = false, value = "on") {
  return `<label class="check"><input type="checkbox" name="${name}" value="${e(value)}" ${checked ? "checked" : ""}>${label}</label>`;
}
function dayPicker(selected = [0, 1, 2, 3, 4], name = "days") {
  return `<div class="day-picker">${days.map((day, i) => `<label><input type="checkbox" name="${name}" value="${i}" ${selected.includes(i) ? "checked" : ""}>${day}</label>`).join("")}</div>`;
}
function readDays(form, name = "days") {
  const result = $$(`input[name="${name}"]:checked`, form).map((x) =>
    Number(x.value),
  );
  if (!result.length)
    throw new Error("Bitte mindestens einen Wochentag auswählen.");
  return result;
}
function periodFields(value) {
  return `<div class="form-grid"><label>Start (leer = ab sofort)<input type="datetime-local" name="starts_at" value="${e(localInput(value.starts_at))}"></label><label>Ende (leer = ohne Ablauf)<input type="datetime-local" name="ends_at" value="${e(localInput(value.ends_at))}"></label></div><p class="help">Diese Datumsfelder verwenden die Zeitzone deines Browsers. Wöchentliche Zeiten laufen in der am Gerät eingestellten Zeitzone.</p>`;
}
function motionHTML(motion) {
  return `<div class="form-section"><h3>Bewegung im Raum</h3><p class="help">Optionaler HC-SR501 am Pi dieses Bilderrahmens. Ohne Aktivierung bestimmen allein die Betriebszeiten die Ruhezeiten.</p></div>${check("motion_enabled", "Bewegungssensor verwenden", motion.enabled)}<div class="form-grid"><label>Nachlaufzeit ohne Bewegung (Minuten)<input type="number" name="motion_idle_minutes" min="1" max="240" value="${motion.idle_minutes}" required></label><label>Abschaltung bei Ruhezeit oder Bewegungspause<select name="motion_power_mode">${option("hdmi", "HDMI abschalten · Monitor-Standby", motion.power_mode)}${option("black", "Schwarzes Bild · Beleuchtung bleibt an", motion.power_mode)}</select></label></div><p class="help">Bewegung aktiviert die Anzeige innerhalb der Betriebszeiten. Sofortmeldungen haben immer Vorrang. Nach dem Aktivieren läuft der Sensor 60 Sekunden ein. HDMI-Abschaltung und Aufwachen einmal am angeschlossenen Monitor testen.</p>`;
}

function showPair(code) {
  dialog(
    "Raspberry Pi koppeln",
    `<p>Der Rahmen ist registriert. Starte auf dem Raspberry Pi die Kopplung und gib diesen einmaligen Code ein.</p><div class="pair-code">${e(code)}</div><p class="help">Der Code gilt 15 Minuten. Nach erfolgreicher Kopplung verwendet der Pi einen eigenen Geräteschlüssel. Ein vorhandener Geräteschlüssel wird erst durch die neue Kopplung ersetzt.</p><button class="primary full" data-close>Verstanden</button>`,
  );
}
function groupEditor(id) {
  const g = state.groups.find((x) => x.id === id) || {
    name: "",
    folder: "",
  };
  const index = state.groups.findIndex((x) => x.id === id);
  let iconEditor;
  dialog(
    id === "new" ? "Gruppe hinzufügen" : "Gruppe bearbeiten",
    `<label>Gruppenname<input name="name" value="${e(g.name)}" maxlength="60" required></label>
    <section class="group-icon-editor"><h3>Gruppenbild (Icon)</h3><div class="group-icon-selection"><div id="group-icon-preview" class="group-icon" role="img" aria-label="Vorschau des Gruppenbilds">${groupIconHTML(g, index)}</div><div><label>Eigenes Bild auswählen<input name="icon_file" type="file" accept="image/png,image/jpeg,image/webp"></label><p class="help">PNG, JPEG oder WebP · bis 2 MB und 4 Millionen Bildpunkte. Das Bild erscheint auf der Gruppenkarte.</p><div class="document-upload-actions"><button type="button" class="small" id="group-icon-remove" ${g.icon_url ? "" : "hidden"}>Bild entfernen</button><button type="button" class="small" id="group-icon-reset" hidden>Änderung verwerfen</button></div><p class="help" id="group-icon-status" role="status">${g.icon_url ? "Eigenes Gruppenbild gespeichert." : "Das Standardsymbol wird verwendet."}</p></div></div></section>
    <label>Fotoordner auf dem NAS<input name="folder" value="${e(g.folder)}" placeholder="Gruppe 1" required></label><p class="help">Relativ zum eingebundenen NAS-Stammordner. Unterordner werden mitgelesen.</p>`,
    async (data) => {
      const upload = new FormData();
      upload.append("data", JSON.stringify({
          name: data.get("name"),
          folder: data.get("folder"),
      }));
      iconEditor.appendTo(upload);
      await api(`/admin/groups/${encodeURIComponent(id)}/edit`, "POST", upload);
      await saved(
        "Gruppe gespeichert. Der nächste NAS-Abgleich liest die Inhalte ein.",
      );
    },
  );
  iconEditor = setupGroupIconEditor(g, index);

}
function setupGroupIconEditor(group, index) {
  const form = $("#editor"), input = $('[name="icon_file"]', form);
  const preview = $("#group-icon-preview"), status = $("#group-icon-status");
  const remove = $("#group-icon-remove"), reset = $("#group-icon-reset");
  let action = "keep", selected = null, previewUrl;
  const revoke = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null;
  };
  const restore = () => {
    revoke();
    action = "keep";
    selected = null;
    input.value = "";
    input.setCustomValidity("");
    preview.innerHTML = groupIconHTML(group, index);
    remove.hidden = !group.icon_url;
    reset.hidden = true;
    status.textContent = group.icon_url ? "Eigenes Gruppenbild gespeichert." : "Das Standardsymbol wird verwendet.";
  };
  dialogCleanup = revoke;
  input.onchange = () => {
    const file = input.files[0];
    if (!file) { restore(); return; }
    const error = file.size > 2 * 1024 * 1024
      ? "Das Gruppenbild darf höchstens 2 MB groß sein."
      : !["image/png", "image/jpeg", "image/webp"].includes(file.type)
        ? "Bitte PNG, JPEG oder WebP auswählen." : "";
    input.setCustomValidity(error);
    if (error) { status.textContent = error; reset.hidden = false; return; }
    revoke();
    action = "replace";
    selected = file;
    previewUrl = URL.createObjectURL(file);
    preview.innerHTML = `<img src="${e(previewUrl)}" alt="">`;
    remove.hidden = false;
    reset.hidden = false;
    status.textContent = "Die Auswahl wird beim Speichern der Gruppe übernommen.";
  };
  remove.onclick = () => {
    restore();
    action = "remove";
    preview.innerHTML = groupIconHTML({}, index);
    remove.hidden = true;
    reset.hidden = false;
    status.textContent = "Nach dem Speichern wird das Standardsymbol verwendet.";
  };
  reset.onclick = restore;
  return { appendTo(data) {
    if (!input.checkValidity()) throw new Error(input.validationMessage);
    data.append("icon_action", action);
    if (action === "replace") data.append("file", selected);
  } };
}
function controlEditor(target) {
  dialog(
    "Anzeige wechseln",
    `<label>Auf welchen Bilderrahmen?<select name="target">${targetOptions(target)}</select></label>${areaField()}<label>Gewünschte Anzeige<select name="mode">${modeOptions("photos", true)}</select></label><label>Manuellen Modus automatisch beenden (optional)<input type="datetime-local" name="until"></label><div class="hint">„Automatisch“ gibt die Anzeige wieder an Inhaltszeitfenster und Standardmodus zurück. Sofortmeldungen und Ruhezeiten haben weiterhin Vorrang. Die Auswahl „Alle“ gilt für die aktuell registrierten Geräte. Zusatz-Umschaltungen gelten nur für Rahmen mit aktivierter Bildschirmteilung.</div>`,
    async (data) => {
      const result = await api("/admin/control", "POST", {
        target: readTarget(data.get("target")),
        mode: data.get("mode") || null,
        until: iso(data.get("until")),
        area: data.get("area") || "main",
      });
      await saved(`${result.changed.length} Bilderrahmen umgestellt.`);
    },
    "Anzeige übernehmen",
  );
}
function noticeEditor(id) {
  const n = state.notices.find((x) => x.id === id) || {
    title: "",
    text: "",
    target: { kind: "all", id: "" },
    theme: "ocean",
    urgent: false,
    internal: false,
  };
  dialog(
    id === "new" ? "Neue Meldung" : "Meldung bearbeiten",
    `<label>Vorlage<select id="template"><option value="">Eigene Meldung</option value="welcome">Willkommen</option><option value="trip">Ausflug</option><option value="event">Elternabend</option></select></label><label>Überschrift<input name="title" value="${e(n.title)}" maxlength="100" required></label><label>Text<textarea name="text" rows="4" maxlength="1400">${e(n.text)}</textarea></label><div class="form-grid"><label>Zielgruppe<select name="target">${targetOptions(n.target)}</select></label><label>Farbstil<select name="theme">${option("ocean", "Meergrün", n.theme)}${option("sun", "Sonnengelb", n.theme)}${option("berry", "Beere", n.theme)}</select></label></div><label>Optionales Meldungsbild<select name="image_id">${option("", "Ohne Bild", n.image_id)}${state.documents
      .filter((d) => d.kind === "image")
      .map((d) => option(d.id, d.name, n.image_id))
      .join(
        "",
      )}</select></label>${periodFields(n)}${check("internal", "Interne Meldung · nur für ausdrücklich freigegebene Geräte", n.internal)}${check("urgent", "Sofortmeldung · übersteuert alle Modi und auch Ruhezeiten", n.urgent)}<div class="form-section"><h3>Vorschau vor der Veröffentlichung</h3><p class="help">Inhaltliche Vorschau. Die genaue Schriftgröße passt der Pi an seinen Bildschirm an.</p></div><div id="notice-live-preview"></div>${id !== "new" ? `<div class="form-section"><button type="button" class="small danger" data-action="delete-notice" data-id="${id}">Meldung beenden und entfernen</button></div>` : ""}`,
    async (data) => {
      await api("/admin/notices/" + id, "PUT", {
        title: data.get("title"),
        text: data.get("text"),
        target: readTarget(data.get("target")),
        theme: data.get("theme"),
        image_id: data.get("image_id") || null,
        starts_at: iso(data.get("starts_at")),
        ends_at: iso(data.get("ends_at")),
        internal: data.has("internal"),
        urgent: data.has("urgent"),
      });
      await saved("Meldung veröffentlicht.");
    },
    "Veröffentlichen",
  );
  function updatePreview() {
    const form = $("#editor"),
      data = new FormData(form),
      image = state.documents.find((d) => d.id === data.get("image_id"))
        ?.assets[0];
    $("#notice-live-preview").innerHTML = noticeHTML({
      title: data.get("title"),
      text: data.get("text"),
      theme: data.get("theme"),
      urgent: data.has("urgent"),
      image: image ? "/api/admin/assets/" + image : null,
    });
  }
  $("#editor").addEventListener("input", updatePreview);
  updatePreview();
  $("#template").onchange = (event) => {
    const templates = {
      welcome: [
        "Schön, dass ihr da seid.",
        "Willkommen in unserer Gruppe! Hier teilen wir kleine Einblicke in unseren Kita-Alltag.",
      ],
      trip: [
        "Wir gehen auf Entdeckungstour.",
        "Bitte denkt an wetterfeste Kleidung, einen kleinen Rucksack und eine Trinkflasche.",
      ],
      event: [
        "Zeit für einen Elternabend.",
        "Wir freuen uns auf einen gemeinsamen Austausch.\nTermin und Treffpunkt ergänzen.",
      ],
    };
    const t = templates[event.target.value];
    if (t) {
      $("[name=title]", $("#editor")).value = t[0];
      $("[name=text]", $("#editor")).value = t[1];
      updatePreview();
    }
  };
}
function documentFields(doc) {
  return `<label>Art<input name="category" list="document-categories" value="${e(documentCategory(doc))}" maxlength="60" required></label><datalist id="document-categories">${["Dokument", "Dienstplan", "Speiseplan", "Elterninformation", "Wochenplan", "Meldungsbild", "Sonstiges"].map((name) => `<option value="${name}"></option>`).join("")}</datalist><p class="help">Vorschlag wählen oder eine eigene Art eingeben. Die Art dient der Übersicht; in den Inhaltszeitfenstern wählst du das konkrete Dokument aus.</p>${doc.kind === "plan" ? check("internal", "Dieses Dokument ist nur für interne Zwecke – z. B. Personalraum", !doc.public) + '<p class="help">Mit Haken für Rahmen mit „Interne Inhalte“. Ohne Haken auch für ausgewählte Elternanzeigen aller Gruppen freigegeben. Beim Ändern dieser Freigabe werden bisherige gruppenspezifische Elternfreigaben ersetzt; Änderungen an Name oder Art behalten sie.</p>' : ""}`;
}
function documentEditor(id) {
  const doc = state.documents.find((item) => item.id === id);
  if (!doc) return;
  dialog("Dokument bearbeiten",
    `<label>Name<input name="name" value="${e(doc.name)}" maxlength="120" required></label>${documentFields(doc)}`,
    async (data) => {
      const public_ = doc.kind === "plan" && !data.has("internal");
      await api("/admin/documents/" + id, "PUT", {
        name: data.get("name"), category: data.get("category"), public: public_,
        revoke_group_release: public_ !== doc.public,
      });
      await saved("Dokument gespeichert.");
    });
}
function uploadEditor(kind) {
  dialog(
    kind === "plan" ? "Dokument (PDF) hochladen" : "Meldungsbild hochladen",
    `<label>Datei<input name="file" type="file" accept="${kind === "plan" ? ".pdf," : ""}.jpg,.jpeg,.png,.webp,.bmp" required></label><p class="help">${kind === "plan" ? "PDF oder Bild, maximal 40 MB. PDF: höchstens 30 Seiten." : "Bilddatei, maximal 40 MB."} Anschließend kannst du die vorbereiteten Seiten prüfen.</p>${documentFields({ kind, category: kind === "plan" ? "Dokument" : "Meldungsbild", public: kind === "plan" })}`,
    async (data) => {
      const upload = new FormData();
      upload.append("file", data.get("file"));
      upload.append("category", data.get("category"));
      upload.append("public", kind === "plan" && !data.has("internal"));
      const result = await api("/admin/upload/" + kind, "POST", upload);
      await refresh();
      documentPreview(result.id);
      toast("Datei vorbereitet. Die Vorschau ist bereit.");
    }, "Hochladen & Vorschau öffnen",
  );
}
function documentPreview(id) {
  const document = state.documents.find((d) => d.id === id);
  if (!document) return;
  showSlides(
    document.name,
    document.assets.map((asset) => ({
      kind: "image",
      asset,
      fit: "contain",
      seconds: 20,
    })),
    {},
    0,
    `<button data-action="document-edit" data-id="${id}">Art &amp; Freigabe bearbeiten</button>` +
    (document.kind === "plan" ? `<button data-action="assign-plan" data-id="${id}" class="primary">Gemeinsame Dokumentenliste verwalten</button>` : ""),
  );
}
function showSlides(title, items, decision, rotation = 0, extra = "") {
  let index = 0;
  dialog(
    title,
    `<p class="help">${e(decision.reason || "Vorbereitete Inhalte")} · Inhaltliche Vorschau, kein Live-Bildschirm.</p><div class="preview-stage ${rotation % 180 ? "portrait" : ""}" id="preview-stage"></div><div class="preview-controls"><button id="prev-slide" aria-label="Vorherige Seite">←</button><span id="slide-count" class="tiny"></span><button id="next-slide" aria-label="Nächste Seite">→</button></div>${extra ? `<div class="dialog-actions">${extra}</div>` : ""}`,
  );
  function draw() {
    const item = items[index];
    $("#slide-count").textContent = items.length
      ? `${index + 1} / ${items.length}`
      : "Keine Inhalte";
    $("#preview-stage").innerHTML =
      decision.mode === "black"
        ? ""
        : !item
          ? '<div class="neutral"><h2>Schön, dass ihr da seid.</h2><p>Hier ist Platz für unsere gemeinsamen Momente.</p></div>'
          : item.kind === "image"
            ? `<img class="${item.fit === "cover" ? "cover" : ""}" src="/api/admin/assets/${e(item.asset)}" alt="Vorschau Seite ${index + 1}">`
            : noticeHTML({
                ...item.notice,
                image: item.notice.image
                  ? "/api/admin/assets/" + item.notice.image
                  : null,
              });
  }
  $("#prev-slide").onclick = () => {
    if (items.length) index = (index - 1 + items.length) % items.length;
    draw();
  };
  $("#next-slide").onclick = () => {
    if (items.length) index = (index + 1) % items.length;
    draw();
  };
  draw();
}
async function devicePreview(id) {
  const result = await api("/admin/preview/" + id);
  if (result.manifest.settings.split?.enabled) {
    showSplitPreview("Vorschau · " + state.devices.find((d) => d.id === id)?.name, result);
    return;
  }
  showSlides(
    "Vorschau · " + state.devices.find((d) => d.id === id)?.name,
    result.slides,
    result.decision,
    result.manifest.settings.rotation,
  );
}
function confirmDelete(title, message, run) {
  dialog(
    title,
    `<p>${e(message)}</p>`,
    async () => {
      await run();
      await saved("Entfernt.");
    },
    "Entfernen",
  );
}

document.addEventListener("click", async (event) => {
  const nav = event.target.closest("[data-nav]");
  if (nav) {
    navigate(nav.dataset.nav);
    return;
  }
  const b = event.target.closest("[data-action]");
  if (!b) return;
  const { action, id } = b.dataset;
  try {
    if (action === "nav") navigate(id);
    else if (action === "device") deviceEditor(id);
    else if (action === "group") groupEditor(id);
    else if (action === "control") controlEditor();
    else if (action === "notice") noticeEditor(id);
    else if (action === "operating-edit") operatingHoursEditor();
    else if (action === "branding-name") brandingNameEditor();
    else if (action === "branding-logo") brandingLogoEditor();
    else if (action === "branding-reset") {
      await api("/admin/branding/logo", "DELETE");
      await refresh();
      toast("Das neutrale Beispiel-Logo ist wieder aktiv.");
    } else if (action === "upload") uploadEditor(id);
    else if (action === "assign-plan") await assignPlan(id);
    else if (action === "document-preview") documentPreview(id);
    else if (action === "document-edit") documentEditor(id);
    else if (action === "preview") await devicePreview(id);
    else if (action === "scan") {
      b.disabled = true;
      await api("/admin/scan", "POST");
      await refresh();
      toast(
        "NAS-Abgleich abgeschlossen. Den Status findest du bei jeder Gruppe.",
      );
    } else if (action === "sync" || action === "restart") {
      b.disabled = true;
      await api(`/admin/devices/${id}/commands/${action}`, "POST");
      toast(
        action === "restart"
          ? "Neustart angefordert. Das Gerät bestätigt ihn beim nächsten Abgleich."
          : "Abgleich angefordert.",
      );
    } else if (action === "pair") {
      const result = await api(`/admin/devices/${id}/pair`, "POST");
      showPair(result.code);
    } else if (action === "delete-device")
      confirmDelete(
        "Bilderrahmen entfernen?",
        "Der Gerätezugriff wird widerrufen. Ein erreichbarer Pi leert seinen Cache beim nächsten Abgleich. Ein offline befindliches Gerät muss vor Ort geleert werden.",
        () => api("/admin/devices/" + id, "DELETE"),
      );
    else if (action === "delete-notice")
      confirmDelete(
        "Meldung beenden?",
        "Die Meldung wird nach dem nächsten Abgleich nicht mehr angezeigt.",
        () => api("/admin/notices/" + id, "DELETE"),
      );
    else if (action === "delete-document") await deleteDocument(id);
  } catch (error) {
    toast(error.message);
  } finally {
    if (b.isConnected) b.disabled = false;
  }
});
$("#login-form").onsubmit = async (event) => {
  event.preventDefault();
  const form = event.currentTarget,
    b = $("button", form);
  b.disabled = true;
  $("#login-error").textContent = "";
  try {
    const data = new FormData(form),
      result = await api("/login", "POST", {
        username: data.get("username"),
        password: data.get("password"),
      });
    csrf = result.csrf;
    form.reset();
    await start();
  } catch (error) {
    $("#login-error").textContent = error.message;
  } finally {
    b.disabled = false;
  }
};
$("#logout").onclick = async () => {
  try {
    await api("/logout", "POST");
    showLogin();
  } catch (error) {
    toast(error.message);
  }
};
async function start() {
  await refresh(false);
  $("#login").hidden = true;
  $("#app").hidden = false;
  page = pages[location.hash.slice(1)] ? location.hash.slice(1) : "overview";
  renderPage();
}
(async () => {
  try {
    applyBranding(await api("/branding"));
  } catch {
    /* Neutral logo remains available. */
  }
  try {
    csrf = (await api("/session")).csrf;
    await start();
  } catch {
    showLogin();
  }
})();
setInterval(async () => {
  if (!$("#app").hidden) {
    try {
      await refresh(!$("#dialog").open);
    } catch (error) {
      toast(error.message);
    }
  }
}, 30000);
