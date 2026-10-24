"use strict";

function documentListLabel(doc) {
  const assignment = doc.list_assignment || {};
  if (assignment.all_groups) return "Gemeinsame Liste · alle Gruppen";
  const names = (assignment.group_ids || []).map(id => state.groups.find(g => g.id === id)?.name).filter(Boolean);
  return names.length ? "Gemeinsame Liste · " + names.join(", ") : "Nicht in der gemeinsamen Liste";
}

async function assignPlan(id) {
  await refresh(false);
  const doc = state.documents.find(d => d.id === id);
  if (!doc) return;
  const assignment = doc.list_assignment || {all_groups:false, group_ids:[]};
  const scope = assignment.all_groups ? "all" : assignment.group_ids.length ? "groups" : "none";
  dialog("Gemeinsame Dokumentenliste",
    `<p><strong>${e(doc.name)}</strong></p><label>In die Liste aufnehmen für<select name="list_scope">${option("none", "– Keine – / aus der Liste entfernen", scope)}${option("all", "Alle Gruppen (auch zukünftige)", scope)}${option("groups", "Ausgewählte Gruppen", scope)}</select></label>
    <div id="list-groups">${state.groups.map(g => check("list_group", e(g.name), assignment.group_ids.includes(g.id), g.id)).join("")}</div>
    <p class="help">Mehrere Dokumente können gleichzeitig in der Liste stehen. Andere Dokumente werden nicht ersetzt. Die Reihenfolge richtet sich nach dem Dateinamen; alle Seiten eines Dokuments folgen aufeinander.</p>
    <div class="hint">Am Rahmen unter Dokument oder Gemischt die Quelle „Gemeinsame Dokumentenliste“ wählen – auch für die zusätzliche Anzeige. Die Freigabe „Interne Inhalte“ gilt weiterhin. Das Entfernen aus der Liste löscht weder die Datei noch direkte Dokumentauswahlen.</div>`,
    async data => {
      const scope = data.get("list_scope");
      const groups = scope === "groups" ? data.getAll("list_group") : [];
      if (scope === "groups" && !groups.length) throw new Error("Bitte mindestens eine Gruppe auswählen oder „Keine“ wählen.");
      await api(`/admin/documents/${encodeURIComponent(id)}/list`, "PUT", {all_groups:scope === "all", group_ids:groups});
      await saved(scope === "none" ? "Dokument aus der gemeinsamen Liste entfernt." : "Gemeinsame Dokumentenliste gespeichert.");
    }, "Auswahl speichern");
  const select = $("[name=list_scope]", $("#editor"));
  const update = () => { $("#list-groups").hidden = select.value !== "groups"; };
  select.onchange = update;
  update();
}

function documentUsageHTML(references) {
  if (!references.length) return '<p>Dieses Dokument hat keine Zuordnungen und kann gelöscht werden.</p>';
  const direct = references.some((ref) => ref.kind === "device");
  const image = references.some((ref) => ref.kind === "notice");
  return `<p>Das Dokument wird noch hier verwendet:</p><ul class="document-usage">${references.map((ref) => `<li>${e(ref.label)}</li>`).join("")}</ul><p>Beim bestätigten Löschen werden diese Zuordnungen gemeinsam mit dem Dokument entfernt.</p>${direct ? '<p class="help">Direkte Dokumentanzeigen wechseln zu Fotos. Betroffene Dokumenteinträge entfallen aus gemischten Wiedergabelisten; eine sonst leere Liste erhält einen Fotoeintrag. Betroffene manuelle Dokumentumschaltungen kehren zur Automatik zurück. Die Inhaltszeitfenster selbst bleiben erhalten.</p>' : ""}${image ? '<p class="help">Meldungen bleiben mit ihrem Text erhalten und werden künftig ohne dieses Bild angezeigt.</p>' : ""}`;
}

async function deleteDocument(id) {
  const usage = await api(`/admin/documents/${encodeURIComponent(id)}/usage`);
  const used = usage.references.length > 0;
  dialog(
    "Dokument löschen?",
    `<p><strong>${e(usage.document.name)}</strong></p>${documentUsageHTML(usage.references)}${used ? check("unlink", "Alle oben genannten Zuordnungen lösen und dieses Dokument löschen.") : ""}<p class="help">Die Änderung erreicht die Bilderrahmen beim nächsten Abgleich. Dateien auf dem NAS bleiben erhalten.</p>`,
    async (data) => {
      if (used && !data.has("unlink")) throw new Error("Bitte das Lösen der Zuordnungen bestätigen.");
      await api(`/admin/documents/${encodeURIComponent(id)}?unlink=${used}&revision=${encodeURIComponent(usage.revision)}`, "DELETE");
      await saved(used ? "Dokument und Zuordnungen entfernt." : "Dokument entfernt.");
    }, used ? "Zuordnungen lösen und löschen" : "Dokument löschen",
  );
  if (used) {
    const confirm = $("[name=unlink]", $("#editor"));
    const submit = $("button[type=submit]", $("#editor"));
    submit.disabled = true;
    confirm.onchange = () => { submit.disabled = !confirm.checked; };
  }
}
