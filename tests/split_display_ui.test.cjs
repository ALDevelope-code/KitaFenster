const assert = require("node:assert/strict");
const {readFileSync} = require("node:fs");
const {test} = require("node:test");
const vm = require("node:vm");

function context(extra = {}) {
  const ctx = vm.createContext({ ...extra });
  vm.runInContext(readFileSync("server/static/split-display.js", "utf8"), ctx);
  return ctx;
}

test("automatic preview orientation follows rotation and keeps the selected secondary size on either side", () => {
  const ctx = context();
  for (const rotation of [0, 90, 180, 270]) {
    for (const percent of [33, 40, 50]) {
      for (const position of ["first", "second"]) {
        const value = ctx.splitLayoutClass({direction:"auto", secondary_percent:percent, main_position:position}, rotation);
        assert.match(value, rotation % 180 ? /vertical/ : /horizontal/);
        assert.ok(value.includes("secondary-" + percent));
        assert.equal(value.includes("main-second"), position === "second");
      }
    }
  }
  assert.match(ctx.splitLayoutClass({direction:"horizontal", secondary_percent:33}, 90), /horizontal/);
  assert.match(ctx.splitLayoutClass({direction:"vertical", secondary_percent:33}, 0), /vertical/);
});

test("preview uses independent timers and cancels them when closed", () => {
  const elements = new Map(), timers = new Map();
  let token = 0;
  const ctx = context({
    e: String, noticeHTML: (n) => n.title,
    dialog: () => {}, dialogCleanup: () => {},
    $: (id) => { if (!elements.has(id)) elements.set(id, {}); return elements.get(id); },
    setTimeout: (fn, ms) => { const id = ++token; timers.set(id, {fn, ms}); return id; },
    clearTimeout: (id) => timers.delete(id),
  });
  const image = (asset, seconds) => ({kind:"image", asset, seconds});
  ctx.showSplitPreview("Test", {manifest:{settings:{rotation:0, split:{enabled:true,direction:"auto",secondary_percent:33}}},
    decision:{reason:"Standard",secondary:{reason:"Standard"}},
    slides:[image("a", 3), image("b", 3)], secondary_slides:[image("c", 20), image("d",20)]});
  assert.deepEqual([...timers.values()].map(t => t.ms), [3000, 20000]);
  const secondaryHTML = elements.get("#preview-secondary").innerHTML;
  [...timers.values()][0].fn();
  assert.match(elements.get("#preview-main").innerHTML, /assets\/b/);
  assert.equal(elements.get("#preview-secondary").innerHTML, secondaryHTML);
  ctx.dialogCleanup();
  assert.equal(timers.size, 0);
});

test("empty secondary content and urgent notices use a single preview region", () => {
  for (const mode of ["photos", "messages", "black"]) {
    let html;
    const nodes = {};
    const ctx = context({e:String, dialog:(_title, body) => {html=body;},
      $:(id) => nodes[id] ||= {}, dialogCleanup:()=>{}, clearTimeout:()=>{}});
    ctx.showSplitPreview("Test", {manifest:{settings:{rotation:0,split:{enabled:true}}},
      decision:{mode, reason:mode === "messages" ? "Sofortmeldung" : "Standard"},
      slides:[], secondary_slides:[]});
    assert.doesNotMatch(html, /id="preview-secondary"/);
    assert.equal(Boolean(nodes["#preview-main"].innerHTML), mode !== "black");
  }
});
