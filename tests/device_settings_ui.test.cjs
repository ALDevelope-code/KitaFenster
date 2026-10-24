const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { test } = require("node:test");
const vm = require("node:vm");

function context(extra = {}) {
  const escape = (v) => String(v ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll('"', "&quot;");
  const ctx = vm.createContext({
    e: escape,
    option: (v, text, selected) => `<option value="${escape(v)}" ${v === selected ? "selected" : ""}>${escape(text)}</option>`,
    state: { documents: [] },
    ...extra,
  });
  vm.runInContext(readFileSync("server/static/device-settings.js", "utf8"), ctx);
  return ctx;
}

test("document choices preserve missing selections, separate message images, and escape labels", () => {
  const ctx = context({ state: { documents: [
    { id: "menu", kind: "plan", category: 'Speiseplan <img src=x>', name: "Mittag.pdf", public: true },
    { id: "photo", kind: "image", name: "Meldung.jpg" },
  ] } });
  const html = ctx.documentOptions("deleted");
  assert.match(html, /value="deleted" selected/);
  assert.match(html, /nicht mehr verfügbar/);
  assert.match(html, /Speiseplan &lt;img/);
  assert.doesNotMatch(html, /<img|Meldung.jpg/);
  assert.equal(ctx.documentCategory({ kind: "plan" }), "Dienstplan");
  assert.equal(ctx.documentCategory({ kind: "plan", category: "Eigene Art" }), "Eigene Art");
});

test("saving follows the visible row order and sends a document only for document mode", () => {
  function row(name, mode, document) {
    return { name, mode, document, start: "11:00", end: "13:00" };
  }
  const rows = [row("Mittag", "plan", "menu"), row("Eltern", "photos", "stale")];
  const ctx = context({
    $$: () => rows,
    $: (selector, row) => ({ value: row[{
      "[name=hour-name]": "name", "[name=hour-mode]": "mode", "[name=hour-document]": "document",
      "[name=hour-start]": "start", "[name=hour-end]": "end",
    }[selector]] }),
    readDays: () => [0, 1, 2, 3, 4],
  });
  assert.deepEqual(JSON.parse(JSON.stringify(ctx.readHours({}))).map((h) => [h.name, h.document_id]),
    [["Mittag", "menu"], ["Eltern", null]]);
  rows.reverse();
  assert.equal(ctx.readHours({})[0].name, "Eltern");
  rows[0].mode = "";
  assert.equal(ctx.readHours({})[0].mode, null);
});
