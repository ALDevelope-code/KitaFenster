"use strict";

function operatingDefaults() {
  return {enabled: false, timezone: "Europe/Berlin", windows: []};
}
function operatingWindowHTML(window = {days:[0,1,2,3,4], start:"07:00", end:"18:00"}) {
  return `<div class="operating-row">${dayPicker(window.days, "operating-days")}<div class="form-grid"><label>Von<input type="time" name="operating-start" value="${e(window.start)}" required></label><label>Bis<input type="time" name="operating-end" value="${e(window.end)}" required></label></div><button type="button" class="small operating-remove">Betriebszeit entfernen</button></div>`;
}
function operatingFields(value) {
  return `${check("operating_enabled", "Betriebszeiten begrenzen", value.enabled)}<p class="help">Ohne Begrenzung ist die Anzeige rund um die Uhr erlaubt. Mit Begrenzung sind nur die eingetragenen Zeiten freigegeben; eine leere Liste bedeutet durchgehend Ruhezeit.</p><div id="operating-windows">${value.windows.map(operatingWindowHTML).join("")}</div><button type="button" id="add-operating" class="small">＋ Betriebszeit</button><label>Zeitzone der Betriebszeiten<input name="operating_timezone" value="${e(value.timezone)}" required></label><p class="help">Alle Zeitfenster gelten gemeinsam. Ein Ende vor dem Start reicht bis zum nächsten Tag; gleiche Uhrzeiten bedeuten ganztägig. Außerhalb dieser Zeiten ruht der gesamte Bildschirm. Sofortmeldungen haben Vorrang.</p>`;
}
function initOperatingFields(form) {
  const container = $("#operating-windows", form), add = $("#add-operating", form);
  const update = () => { add.disabled = $$(".operating-row", container).length >= 14; };
  add.onclick = () => { container.insertAdjacentHTML("beforeend", operatingWindowHTML()); update(); };
  container.onclick = event => {
    if (event.target.closest(".operating-remove")) { event.target.closest(".operating-row").remove(); update(); }
  };
  update();
}
function readOperatingHours(form) {
  const data = new FormData(form);
  return {enabled:data.has("operating_enabled"), timezone:data.get("operating_timezone"),
    windows:$$(".operating-row", form).map(row => ({days:readDays(row,"operating-days"),
      start:$("[name=operating-start]",row).value, end:$("[name=operating-end]",row).value}))};
}
function operatingSummary(value) {
  if (!value.enabled) return "Rund um die Uhr freigegeben";
  if (!value.windows.length) return "Durchgehend Ruhezeit · keine Betriebszeiten eingetragen";
  return value.windows.map(w => `${w.days.map(d => days[d]).join(", ")} · ${w.start}–${w.end}${w.start === w.end ? " (ganztägig)" : w.start > w.end ? " (bis zum Folgetag)" : ""}`).join(" / ");
}
function renderOperatingHours() {
  const value = state.operating_hours;
  const overrides = state.devices.filter(d => d.settings.operating_hours_override !== null);
  return head("Betriebszeiten", "Wann dürfen eure Bilderrahmen anzeigen? Inhalte werden am jeweiligen Rahmen eingestellt.", button("operating-edit", "Betriebszeiten bearbeiten", "", true)) +
    `<section class="panel"><h2>Zentraler Standard für alle Rahmen</h2><p>${e(operatingSummary(value))}</p><p class="help">Zeitzone: ${e(value.timezone)}. Gilt für alle Rahmen ohne eigene Betriebszeiten und für neu angelegte Rahmen. Der Pi beachtet diese Zeiten auch offline; Änderungen übernimmt er beim nächsten Abgleich.</p></section>
    <section class="panel form-section"><h2>Abweichende Betriebszeiten</h2>${overrides.length ? overrides.map(d => `<div class="row-item"><div><strong>${e(d.name)}</strong><p>${e(operatingSummary(d.settings.operating_hours_override))}</p></div>${button("device", "Rahmen verwalten", d.id)}</div>`).join("") : '<p>Alle Rahmen verwenden den zentralen Standard.</p>'}</section>
    <div class="hint">Bewegungssensoren können die Anzeige innerhalb der Betriebszeiten zusätzlich pausieren. Sofortmeldungen erscheinen auch außerhalb der Betriebszeiten. Inhaltszeitfenster und manuelle Umschaltungen verlängern keine Betriebszeiten.</div>`;
}
function operatingHoursEditor() {
  dialog("Zentrale Betriebszeiten", operatingFields(state.operating_hours), async (_data, form) => {
    await api("/admin/operating-hours", "PUT", readOperatingHours(form));
    await saved("Betriebszeiten gespeichert. Verbundene Rahmen übernehmen sie beim nächsten Abgleich.");
  });
  initOperatingFields($("#editor"));
}
function deviceOperatingFields(settings) {
  const override = settings.operating_hours_override;
  return `<section class="device-section"><h3>4. Betriebszeiten</h3><p class="help">Zentraler Standard: ${e(operatingSummary(state.operating_hours))}</p>${check("operating_override", "Eigene Betriebszeiten für diesen Rahmen verwenden", override !== null)}<fieldset id="operating-override-fields" ${override === null ? "hidden disabled" : ""}>${operatingFields(override || state.operating_hours)}</fieldset><p class="help">Ohne eigene Betriebszeiten folgt dieser Rahmen allen Änderungen des zentralen Standards. Haupt- und Zusatzanzeige schalten gemeinsam. Die Art der Abschaltung wird unter „Bewegungssensor & Energiesparen“ gewählt.</p></section>`;
}
