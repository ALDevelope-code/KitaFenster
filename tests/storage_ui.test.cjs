const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { test } = require("node:test");
const vm = require("node:vm");

test("device list shows measured free space and handles older players", () => {
  const source = readFileSync("server/static/app.js", "utf8");
  const ctx = vm.createContext({
    state: { devices: [
      { id: "a", name: "Rahmen A", last_ip: "172.21.0.1", reported: { mode: "photos", local_ip: "192.168.10.42", storage: {
        total_bytes: 20 * 1024 ** 3, free_bytes: 5 * 1024 ** 3,
        reserved_bytes: 2 * 1024 ** 3,
      } }, effective: { mode: "photos", reason: "Fotos" } },
      { id: "b", name: "Rahmen B", reported: {}, effective: { mode: "photos", reason: "Fotos" } },
    ] },
    e: (value) => String(value ?? ""),
    head: () => "", button: () => "", badge: () => "", groupOf: () => ({ name: "Gruppe" }),
    date: () => "", relative: () => "", modes: { photos: "Fotos" },
  });
  vm.runInContext(source.slice(source.indexOf("function storageLabel("), source.indexOf("function groupIconHTML(")), ctx);
  const html = ctx.renderDevices();
  assert.match(html, /Rahmen A[\s\S]*Geräte-IP: 192\.168\.10\.42/);
  assert.doesNotMatch(html, /172\.21\.0\.1/);
  assert.match(html, /Rahmen A[\s\S]*Speicher frei: 5 von 20 GiB \(25 %\)/);
  assert.match(html, /Rahmen B[\s\S]*Geräte-IP: noch keine Meldung vom Player/);
  assert.match(html, /Rahmen B[\s\S]*Speicher: noch keine Meldung vom Pi/);
});
