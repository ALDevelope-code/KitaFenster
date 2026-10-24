"use strict";

function documentCategory(doc) {
  return doc.category || (doc.kind === "plan" ? "Dienstplan" : "Meldungsbild");
}
function documentOptions(selected) {
  const docs = state.documents.filter((doc) => doc.kind === "plan");
  return option("", "Gemeinsame Dokumentenliste", selected || "") +
    (selected && !docs.some((doc) => doc.id === selected)
      ? option(selected, "Dokument nicht mehr verfügbar", selected) : "") +
    docs.map((doc) => option(doc.id,
      `${documentCategory(doc)} · ${doc.name}${doc.public ? " · für Eltern freigegeben" : " · Freigabe prüfen"}`,
      selected)).join("");
}
function documentField(name, selected, mode) {
  return `<label class="document-choice" ${mode !== "plan" ? "hidden" : ""}>Dokument<select name="${name}">${documentOptions(selected)}</select></label>`;
}
function orderButtons(prefix, label) {
  return `<div class="order-actions"><button type="button" class="text-button ${prefix}-up" aria-label="${label} nach oben" title="Nach oben">↑</button><button type="button" class="text-button ${prefix}-down" aria-label="${label} nach unten" title="Nach unten">↓</button><button type="button" class="text-button ${prefix}-remove" aria-label="${label} entfernen" title="Entfernen">✕</button></div>`;
}
function hourHTML(hour = { days: [0, 1, 2, 3, 4], start: "07:00", end: "18:00" }) {
  return `<div class="hour-row"><div class="hour-heading"><strong class="hour-position"></strong>${orderButtons("hour", "Zeitfenster")}</div><label>Bezeichnung (optional)<input name="hour-name" maxlength="80" value="${e(hour.name || "")}" placeholder="Zum Beispiel: Mittagessen"></label>${areaField("hour-area", hour.area || "main")}${dayPicker(hour.days, "hour-days")}<div class="form-grid"><label>Von<input type="time" name="hour-start" value="${e(hour.start)}" required></label><label>Bis<input type="time" name="hour-end" value="${e(hour.end)}" required></label><label>Was soll angezeigt werden?<select name="hour-mode">${option("", "Standardinhalt dieses Bereichs", hour.mode || "")}${modeOptions(hour.mode)}</select></label>${documentField("hour-document", hour.document_id, hour.mode)}</div></div>`;
}
function playlistHTML(entry = { mode: "photos", seconds: 12 }) {
  return `<div class="playlist-row"><div class="form-grid"><label>Inhalt<select name="playlist-mode">${["photos", "plan", "messages"].map((x) => option(x, modes[x], entry.mode)).join("")}</select></label><label>Sekunden pro Bild / Seite<input type="number" name="playlist-seconds" min="3" max="3600" value="${entry.seconds}" required></label>${documentField("playlist-document", entry.document_id, entry.mode)}</div>${orderButtons("playlist", "Eintrag")}</div>`;
}
function refreshOrder(container, prefix) {
  const rows = $$(`.${prefix}-row`, container);
  rows.forEach((row, index) => {
    $(`.${prefix}-up`, row).disabled = index === 0;
    $(`.${prefix}-down`, row).disabled = index === rows.length - 1;
    if (prefix === "hour") $(".hour-position", row).textContent = `Priorität ${index + 1}`;
  });
  $(`#add-${prefix}`).disabled = rows.length >= (prefix === "hour" ? 14 : 12);
}
function reorderRow(event, container, prefix) {
  const row = event.target.closest(`.${prefix}-row`);
  if (!row) return;
  if (event.target.closest(`.${prefix}-remove`)) row.remove();
  else if (event.target.closest(`.${prefix}-up`) && row.previousElementSibling)
    row.previousElementSibling.before(row);
  else if (event.target.closest(`.${prefix}-down`) && row.nextElementSibling)
    row.nextElementSibling.after(row);
  refreshOrder(container, prefix);
}
function readHours(form) {
  return $$(".hour-row", form).map((row) => {
    const mode = $("[name=hour-mode]", row).value || null;
    return {
      name: $("[name=hour-name]", row).value.trim(),
      days: readDays(row, "hour-days"),
      start: $("[name=hour-start]", row).value,
      end: $("[name=hour-end]", row).value,
      mode,
      area: $("[name=hour-area]", row)?.value || "main",
      document_id: mode === "plan" ? $("[name=hour-document]", row).value || null : null,
    };
  });
}
function deviceEditor(id) {
  const device = state.devices.find((d) => d.id === id);
  const value = device || {
    name: "", group_id: state.groups[0]?.id, allow_internal: false,
    settings: structuredClone(defaults),
  };
  const s = { ...structuredClone(defaults), ...value.settings };
  s.motion = { ...defaults.motion, ...value.settings.motion };
  s.split = { ...splitDefaults(), ...s.split };
  s.split.secondary = { ...splitDefaults().secondary, ...s.split.secondary };
  dialog(
    device ? "Bilderrahmen verwalten" : "Neuen Bilderrahmen hinzufügen",
    `<section class="device-section"><h3>1. Standort &amp; Freigaben</h3><div class="form-grid"><label>Name<input name="name" value="${e(value.name)}" placeholder="Zum Beispiel: Vorraum Gruppe 1" maxlength="60" required></label><label>Gruppe<select name="group_id">${state.groups.map((g) => option(g.id, g.name, value.group_id)).join("")}</select></label></div>${check("allow_internal", "Interne Inhalte zulassen · nur für einen Standort im Personalbereich", value.allow_internal)}<p class="help">Für Elternbereiche ausgeschaltet lassen. Dokumente für Eltern unter „Inhalte → Bearbeiten“ freigeben; dies gilt für direkte Dokumente und die gemeinsame Dokumentenliste.</p></section>
    <section class="device-section"><h3>2. Hauptanzeige · Standardinhalt</h3><p class="help">Diese Inhalte laufen innerhalb der Betriebszeiten, solange kein Inhaltszeitfenster oder manueller Modus etwas anderes vorgibt.</p><div class="form-grid" id="default-content"><label>Inhalt<select name="default_mode">${modeOptions(s.default_mode)}</select></label>${documentField("document_id", s.document_id, s.default_mode)}<label>Bildwechsel alle … Sekunden<input type="number" min="3" max="3600" name="interval" value="${s.interval}" required></label></div>
    <details id="mixed-settings" class="nested-settings"><summary>Gemischte Anzeige zusammenstellen</summary><p class="help">Gilt für die Hauptanzeige, wenn „Gemischt“ gewählt ist. Alle Bilder oder Seiten eines Eintrags laufen nacheinander; die Dauer gilt pro Bild, Seite oder Meldung.</p><div id="playlist">${s.playlist.map(playlistHTML).join("")}</div><button type="button" id="add-playlist" class="small">＋ Eintrag</button></details></section>
    ${splitFields(s.split)}
    ${deviceOperatingFields(s)}
    <section class="device-section"><h3>5. Inhaltszeitfenster</h3>${check("content_windows_enabled", "Inhalte zeitabhängig wechseln", s.content_windows_enabled)}<p class="help" id="hours-status" role="status"></p><div id="hours">${s.content_windows.map(hourHTML).join("")}</div><button type="button" id="add-hour" class="small">＋ Inhaltszeitfenster</button><p class="help">Je Anzeigebereich gilt das oberste passende Zeitfenster. Mit ↑ und ↓ verschieben. Außerhalb dieser Fenster läuft der Standardinhalt des jeweiligen Bereichs. Inhaltszeitfenster schalten den Rahmen nicht ein oder aus und gelten nur innerhalb seiner Betriebszeiten.</p><label>Zeitzone der Inhaltszeitfenster<input name="timezone" value="${e(s.timezone)}" required></label></section>
    <details class="device-section"><summary>6. Bild &amp; Darstellung</summary><div class="form-grid"><label>Ausrichtung<select name="rotation">${[[0,"Querformat · 0°"],[90,"Hochformat · 90°"],[180,"Querformat · 180°"],[270,"Hochformat · 270°"]].map(([v,l]) => option(v,l,s.rotation)).join("")}</select></label><label>Bildausschnitt<select name="fit">${option("contain", "Ganzes Bild · ohne Abschneiden", s.fit)}${option("cover", "Bildschirm füllen · mit Beschnitt", s.fit)}</select></label><label>Fotoreihenfolge<select name="order">${option("name", "Nach Dateinamen", s.order)}${option("shuffle", "Zufällig", s.order)}</select></label><label>Übergang<select name="transition">${option("none", "Direkter Wechsel", s.transition)}${option("fade", "Sanft überblenden", s.transition)}${option("slide", "Seitlich einschieben", s.transition)}</select></label><label>Übergangsdauer in Sekunden<input type="number" min="0" max="3" step="0.1" name="transition_seconds" value="${s.transition_seconds}" required></label></div></details>
    <details class="device-section" ${s.motion.enabled ? "open" : ""}><summary>7. Bewegungssensor &amp; Energiesparen</summary>${motionHTML(s.motion)}${device ? motionDiagnosticsHTML() : ""}</details>
    ${device ? `<details class="device-section"><summary>8. Gerät &amp; Wartung</summary><p class="help">Status: ${e(device.reported?.reason || "Noch keine Rückmeldung")}</p><div class="head-actions"><button type="button" data-action="preview" data-id="${id}">Vorschau</button><button type="button" data-action="sync" data-id="${id}">Abgleichen</button><button type="button" data-action="restart" data-id="${id}">Player neu starten</button></div><p class="help">Der Neustart betrifft nur die Anzeige-Anwendung. Einstellungen vor dem Öffnen einer anderen Ansicht speichern.</p><button type="button" class="small" data-action="pair" data-id="${id}">Neuen Kopplungscode erstellen</button> <button type="button" class="small danger" data-action="delete-device" data-id="${id}">Gerät entfernen</button></details>` : ""}`,
    async (data, form) => {
      const hours = readHours(form);
      const playlist = $$(".playlist-row", form).map((row) => {
        const mode = $("[name=playlist-mode]", row).value;
        return { mode, seconds: Number($("[name=playlist-seconds]", row).value),
          document_id: mode === "plan" ? $("[name=playlist-document]", row).value || null : null };
      });
      if (!playlist.length) throw new Error("Mindestens ein Eintrag für den gemischten Modus ist erforderlich.");
      const body = {
        name: data.get("name"), group_id: data.get("group_id"), allow_internal: data.has("allow_internal"),
        settings: {
          default_mode: data.get("default_mode"),
          document_id: data.get("default_mode") === "plan" ? data.get("document_id") || null : null,
          interval: Number(data.get("interval")), rotation: Number(data.get("rotation")),
          fit: data.get("fit"), order: data.get("order"), transition: data.get("transition"),
          transition_seconds: Number(data.get("transition_seconds")), timezone: data.get("timezone"),
          operating_hours_override: data.has("operating_override") ? readOperatingHours(form) : null,
          content_windows_enabled: data.has("content_windows_enabled"), content_windows: hours, playlist, split: readSplit(form),
          motion: { enabled: data.has("motion_enabled"), idle_minutes: Number(data.get("motion_idle_minutes")), power_mode: data.get("motion_power_mode") },
        },
      };
      if (device) {
        await api("/admin/devices/" + id, "PUT", body);
        if ($("#motion-diagnostics")?.dataset.running === "true") {
          await refresh();
          toast("Gespeichert. In der Live-Diagnose siehst du, wann die Einstellungen am Pi ankommen.");
        } else await saved();
      } else {
        const result = await api("/admin/devices", "POST", body);
        await refresh();
        showPair(result.code);
      }
    }, device ? "Einstellungen speichern" : "Rahmen registrieren",
  );
  const form = $("#editor");
  function updateChoices() {
    for (const [root, field] of [["#default-content", "default_mode"], [".hour-row", "hour-mode"], [".playlist-row", "playlist-mode"], ["#secondary-content", "secondary_mode"], [".secondary-playlist-row", "secondary-playlist-mode"]]) {
      $$(root, form).forEach((row) => {
        $(".document-choice", row).hidden = $(`[name=${field}]`, row).value !== "plan";
      });
    }
    updateSplitPreview(form);
    const enabled = $("[name=content_windows_enabled]", form).checked;
    $("#hours-status").textContent = enabled
      ? "Inhaltszeitfenster aktiv: Sie wechseln nur Inhalte; die Betriebszeiten bleiben unabhängig davon gültig."
      : "Inhaltszeitfenster pausiert: Innerhalb der Betriebszeiten gilt der Standardinhalt beider Bereiche.";
    const operatingFields = $("#operating-override-fields", form);
    operatingFields.hidden = operatingFields.disabled = !$("[name=operating_override]", form).checked;
  }
  for (const [prefix, containerId, html] of [["hour", "hours", hourHTML], ["playlist", "playlist", playlistHTML], ["secondary-playlist", "secondary-playlist", secondaryPlaylistHTML]]) {
    const container = $("#" + containerId);
    $("#add-" + prefix).onclick = () => {
      container.insertAdjacentHTML("beforeend", html());
      refreshOrder(container, prefix);
      updateChoices();
    };
    container.onclick = (event) => reorderRow(event, container, prefix);
    refreshOrder(container, prefix);
  }
  initOperatingFields(form);
  form.addEventListener("change", updateChoices);
  $("#mixed-settings").open = s.default_mode === "mixed" || s.content_windows.some((h) => h.mode === "mixed");
  $("#secondary-mixed").open = s.split.secondary.default_mode === "mixed";
  updateChoices();
  if (device) dialogCleanup = initMotionDiagnostics(id);
}
