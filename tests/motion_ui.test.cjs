const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { test } = require("node:test");
const vm = require("node:vm");

function context(extra = {}) {
  const ctx = vm.createContext({
    e: (value) => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll('"', "&quot;"),
    date: (value) => value || "Noch nicht verbunden",
    defaults: { motion: { enabled: false, idle_minutes: 5, power_mode: "hdmi" } },
    ...extra,
  });
  vm.runInContext(readFileSync("server/static/motion.js", "utf8"), ctx);
  return ctx;
}
function result(changes = {}) {
  return {
    age_seconds: 1,
    settings: { enabled: true, idle_minutes: 1, power_mode: "hdmi" },
    sample: {
      enabled: true, idle_minutes: 1, power_mode: "hdmi", signal: true,
      signal_seconds: 42, phase: "high", remaining_seconds: 60,
      display: "on", reason: "Bewegung erkannt", events: [], ...changes,
    },
  };
}
test("HIGH explains the held timeout; LOW shows the actual countdown", () => {
  const ctx = context();
  assert.match(ctx.motionDiagnosticView(result()), /Erst nach LOW/);
  assert.match(ctx.motionDiagnosticView(result()), /Wird noch nicht heruntergezählt/);
  assert.match(ctx.motionDiagnosticView(result({ phase: "hold", signal: false, remaining_seconds: 12 })), /12 s/);
});
test("stale samples and unapplied settings are explicit, and GPIO errors are escaped", () => {
  const ctx = context();
  const data = result({ phase: "error", signal: null, sensor_error: "<script>oops</script>", enabled: false });
  data.age_seconds = 8;
  const html = ctx.motionDiagnosticView(data);
  assert.match(html, /Messwerte.*veraltet/);
  assert.match(html, /am Pi noch nicht angekommen/);
  assert.match(html, /Unbekannt/);
  assert.match(html, /&lt;script>/);
  assert.doesNotMatch(html, /<script>/);
  assert.match(ctx.motionDiagnosticView({ sample: null }), /NAS und Pi-Player/);
});
test("closing the diagnostic stops polling and ignores an in-flight response", async () => {
  const root = { dataset: {}, isConnected: true }, button = {}, status = {}, data = {};
  const nodes = { "#motion-diagnostics": root, "#motion-live-toggle": button, "#motion-live-status": status, "#motion-live-data": data };
  let complete, timers = 0;
  const ctx = context({
    $: (selector) => nodes[selector],
    api: () => new Promise((resolve) => { complete = resolve; }),
    setTimeout: () => { timers++; }, clearTimeout: () => {},
    setInterval: () => {}, clearInterval: () => {},
  });
  const cleanup = ctx.initMotionDiagnostics("one");
  button.onclick();
  assert.equal(root.dataset.running, "true");
  cleanup();
  complete(result());
  await new Promise(setImmediate);
  assert.equal(root.dataset.running, "false");
  assert.equal(data.innerHTML, "");
  assert.equal(timers, 0);
});

test("a hanging network request cannot keep old measurements labelled live", async () => {
  const root = { dataset: {}, isConnected: true }, button = {}, status = {}, data = {};
  const nodes = { "#motion-diagnostics": root, "#motion-live-toggle": button, "#motion-live-status": status, "#motion-live-data": data };
  let ageCheck, now = 0;
  const ctx = context({
    $: (selector) => nodes[selector], api: async () => result(), Date: { now: () => now },
    setTimeout: () => {}, clearTimeout: () => {},
    setInterval: (callback) => { ageCheck = callback; }, clearInterval: () => {},
  });
  const cleanup = ctx.initMotionDiagnostics("one");
  button.onclick();
  await new Promise(setImmediate);
  assert.equal(status.textContent, "Live-Diagnose läuft");
  now = 7000;
  ageCheck();
  assert.match(status.textContent, /veraltet/);
  assert.match(data.innerHTML, /Messwerte.*veraltet/);
  cleanup();
});
