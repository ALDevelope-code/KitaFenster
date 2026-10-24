"use strict";

function areaField(name = "area", selected = "main") {
  return `<label>Anzeigebereich<select name="${name}">${option("main", "Hauptanzeige (Default)", selected)}${option("secondary", "Zusätzliche Anzeige", selected)}</select></label>`;
}
function splitDefaults() {
  return {enabled: false, direction: "auto", secondary_percent: 33, main_position: "first",
    secondary: {default_mode: "messages", document_id: null, interval: 15,
      playlist: [{mode: "messages", seconds: 15}, {mode: "photos", seconds: 12}]}};
}
function secondaryPlaylistHTML(entry) {
  return playlistHTML(entry).replaceAll("playlist-", "secondary-playlist-");
}
function splitFields(split) {
  const secondary = split.secondary;
  return `<section class="device-section"><h3>3. Bildschirm teilen</h3>${check("split_enabled", "Zwei Inhalte gleichzeitig anzeigen", split.enabled)}
    <div id="split-settings" ${split.enabled ? "" : "hidden"}><div class="form-grid">
    <label>Aufteilung<select name="split_direction">${option("auto", "Automatisch nach Ausrichtung", split.direction)}${option("horizontal", "Nebeneinander · links / rechts", split.direction)}${option("vertical", "Untereinander · oben / unten", split.direction)}</select></label>
    <label>Größe der zusätzlichen Anzeige<select name="split_secondary_percent">${[33, 40, 50].map(percent => option(percent, `${percent} %`, split.secondary_percent)).join("")}</select></label>
    <label>Hauptanzeige (Default)<select name="split_main_position">${option("first", "Links bzw. oben", split.main_position)}${option("second", "Rechts bzw. unten", split.main_position)}</select></label></div>
    <h3>Vorschau der Aufteilung</h3><div id="split-layout-preview" class="split-layout-preview" role="img" aria-label="Aufteilung des Bildschirms"></div>
    <p class="help">Die zusätzliche Anzeige behält die gewählte Größe beim Seitenwechsel; die Hauptanzeige nutzt den übrigen Platz. Automatisch: im Querformat nebeneinander, im Hochformat untereinander. Ohne Inhalte im Zusatzbereich nutzt die Hauptanzeige den ganzen Bildschirm. Sofortmeldungen erscheinen immer im Vollbild.</p>
    <h3>Zusätzliche Anzeige · Standardinhalt</h3><div class="form-grid" id="secondary-content"><label>Inhalt<select name="secondary_mode">${modeOptions(secondary.default_mode)}</select></label>${documentField("secondary_document", secondary.document_id, secondary.default_mode)}<label>Eigener Bildwechsel alle … Sekunden<input type="number" name="secondary_interval" min="3" max="3600" value="${secondary.interval}" required></label></div>
    <details class="nested-settings" id="secondary-mixed"><summary>Gemischte zusätzliche Anzeige</summary><div id="secondary-playlist">${secondary.playlist.map(secondaryPlaylistHTML).join("")}</div><button type="button" id="add-secondary-playlist" class="small">＋ Eintrag</button></details>
    <p class="help">Dieser Standard gilt ohne passendes Zusatz-Zeitfenster. Interne Inhalte benötigen auch hier die Freigabe des Rahmens. Betriebszeiten und Bewegungssensor gelten gemeinsam für den ganzen Bildschirm.</p></div></section>`;
}
function readSplit(form) {
  const data = new FormData(form);
  const playlist = $$(".secondary-playlist-row", form).map((row) => {
    const mode = $("[name=secondary-playlist-mode]", row).value;
    return {mode, seconds: Number($("[name=secondary-playlist-seconds]", row).value),
      document_id: mode === "plan" ? $("[name=secondary-playlist-document]", row).value || null : null};
  });
  if (!playlist.length) throw new Error("Mindestens ein Eintrag für die gemischte zusätzliche Anzeige ist erforderlich.");
  return {enabled: data.has("split_enabled"), direction: data.get("split_direction"),
    secondary_percent: Number(data.get("split_secondary_percent")), main_position: data.get("split_main_position"),
    secondary: {default_mode: data.get("secondary_mode"),
      document_id: data.get("secondary_mode") === "plan" ? data.get("secondary_document") || null : null,
      interval: Number(data.get("secondary_interval")), playlist}};
}
function splitLayoutClass(split, rotation) {
  const vertical = split.direction === "vertical" || (split.direction === "auto" && Number(rotation) % 180 !== 0);
  return `split-screen ${vertical ? "vertical" : "horizontal"} secondary-${split.secondary_percent} ${split.main_position === "second" ? "main-second" : ""}`;
}
function updateSplitPreview(form) {
  const data = new FormData(form);
  $("#split-settings").hidden = !data.has("split_enabled");
  const split = {direction: data.get("split_direction"), secondary_percent: Number(data.get("split_secondary_percent")), main_position: data.get("split_main_position")};
  const preview = $("#split-layout-preview");
  preview.className = `split-layout-preview ${splitLayoutClass(split, data.get("rotation"))} ${Number(data.get("rotation")) % 180 ? "portrait" : ""}`;
  preview.innerHTML = `<div class="split-main"><strong>Hauptanzeige (Default)</strong><span>${e(modes[data.get("default_mode")])}</span></div><div class="split-secondary"><strong>Zusätzliche Anzeige</strong><span>${e(modes[data.get("secondary_mode")])}</span></div>`;
}
function previewItem(item) {
  if (!item) return '<div class="neutral"><h2>Schön, dass ihr da seid.</h2></div>';
  return item.kind === "image"
    ? `<img class="${item.fit === "cover" ? "cover" : ""}" src="/api/admin/assets/${e(item.asset)}" alt="Vorschau">`
    : noticeHTML({...item.notice, image: item.notice.image ? "/api/admin/assets/" + item.notice.image : null});
}
function showSplitPreview(title, result) {
  const settings = result.manifest.settings, split = settings.split;
  const lists = {main: result.slides, secondary: result.secondary_slides};
  const splitActive = result.decision.mode !== "black" && Boolean(lists.secondary.length);
  const areas = splitActive ? ["main", "secondary"] : ["main"];
  const positions = {main: 0, secondary: 0}, timers = {};
  dialog(title, `<p class="help">${e(result.decision.reason)}${result.decision.secondary ? " · Zusatz: " + e(result.decision.secondary.reason) : ""}. Inhaltliche Vorschau, kein Live-Bildschirm. Beide Bereiche wechseln unabhängig.</p>
    <div class="preview-stage ${settings.rotation % 180 ? "portrait" : ""} ${splitActive ? splitLayoutClass(split, settings.rotation) : ""}">${areas.map((area) => `<div class="split-${area} preview-region" id="preview-${area}"></div>`).join("")}</div>
    ${areas.map((area) => `<div class="preview-controls"><span>${area === "main" ? "Hauptanzeige" : "Zusätzliche Anzeige"}</span><button type="button" id="previous-${area}" aria-label="${area === "main" ? "Hauptanzeige" : "Zusätzliche Anzeige"}: vorherige Seite">←</button><span id="count-${area}"></span><button type="button" id="next-${area}" aria-label="${area === "main" ? "Hauptanzeige" : "Zusätzliche Anzeige"}: nächste Seite">→</button></div>`).join("")}
    ${!splitActive && result.decision.mode !== "black" && result.decision.reason !== "Sofortmeldung" ? '<p class="help">Keine zusätzlichen Inhalte: Die Hauptanzeige nutzt den ganzen Bildschirm.</p>' : ""}`);
  function draw(area) {
    clearTimeout(timers[area]);
    const list = lists[area], item = list[positions[area]];
    $("#preview-" + area).innerHTML = result.decision.mode === "black" ? "" : previewItem(item);
    $("#count-" + area).textContent = list.length ? `${positions[area] + 1} / ${list.length}` : "Keine Inhalte";
    if (list.length > 1) timers[area] = setTimeout(() => { positions[area] = (positions[area] + 1) % list.length; draw(area); }, (item.seconds || 12) * 1000);
  }
  for (const area of areas) {
    for (const [prefix, delta] of [["previous", -1], ["next", 1]]) $("#" + prefix + "-" + area).onclick = () => {
      if (lists[area].length) positions[area] = (positions[area] + delta + lists[area].length) % lists[area].length;
      draw(area);
    };
    draw(area);
  }
  dialogCleanup = () => Object.values(timers).forEach(clearTimeout);
}
