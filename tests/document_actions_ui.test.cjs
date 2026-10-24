const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { test } = require("node:test");
const vm = require("node:vm");

function context(extra = {}) {
  const ctx = vm.createContext({
    e: (v) => String(v).replaceAll("&", "&amp;").replaceAll("<", "&lt;"),
    ...extra,
  });
  vm.runInContext(readFileSync("server/static/document-actions.js", "utf8"), ctx);
  return ctx;
}

test("shared list offers all, selected groups and removal without changing document permissions", async () => {
  const nodes = new Map(), calls = [];
  let html, submit;
  const ctx = context({state:{groups:[{id:"a", name:"Piraten <img>"}], documents:[{id:"doc", name:"Plan", list_assignment:{all_groups:false, group_ids:["a"]}}]},
    refresh:async()=>{}, saved:async()=>{},
    option:(v,label,selected)=>`<option value="${v}" ${v === selected ? "selected" : ""}>${label}</option>`,
    check:(name,label,checked,value)=>`${name}:${label}:${checked}:${value}`,
    dialog:(_title,body,callback)=>{html=body;submit=callback;},
    $:selector=>{if(!nodes.has(selector)) nodes.set(selector,{value:"groups"});return nodes.get(selector);},
    api:async(path,method,body)=>calls.push({path,method,body}),
  });
  await ctx.assignPlan("doc");
  assert.match(html, /value="none"/);
  assert.match(html, /value="all"/);
  assert.match(html, /value="groups" selected/);
  assert.match(html, /Piraten &lt;img/);
  assert.equal(nodes.get("#list-groups").hidden,false);
  const data = scope => {const d = new FormData(); d.set("list_scope",scope); return d;};
  await assert.rejects(submit(data("groups")), /mindestens eine Gruppe/);
  const selected=data("groups"); selected.append("list_group","a");
  await submit(selected);
  await submit(data("all"));
  await submit(data("none"));
  assert.deepEqual(JSON.parse(JSON.stringify(calls.map(c=>c.body))), [
    {all_groups:false,group_ids:["a"]},{all_groups:true,group_ids:[]},{all_groups:false,group_ids:[]}]);
  assert.ok(calls.every(c=>c.path === "/admin/documents/doc/list" && c.method === "PUT"));
  nodes.get("[name=list_scope]").value="all";
  nodes.get("[name=list_scope]").onchange();
  assert.equal(nodes.get("#list-groups").hidden,true);
});

test("usage list escapes names and explains the actual affected content", () => {
  const ctx = context();
  const html = ctx.documentUsageHTML([
    {kind:"group", label:"Group <img src=x>"},
    {kind:"device", label:"Frame: Lunch"},
    {kind:"notice", label:"Message"},
  ]);
  assert.match(html, /Group &lt;img/);
  assert.doesNotMatch(html, /<img/);
  assert.match(html, /Dokumentanzeigen wechseln zu Fotos/);
  assert.match(html, /Meldungen bleiben mit ihrem Text erhalten/);
  assert.match(ctx.documentUsageHTML([]), /keine Zuordnungen/);
});

test("used document deletion requires confirmation and sends the reviewed revision", async () => {
  const confirm = {checked:false}, button = {};
  let submit, requests = [];
  const ctx = context({
    $: (selector) => selector === "[name=unlink]" ? confirm : button,
    check: () => "checkbox",
    dialog: (_title, _html, callback) => { submit = callback; },
    api: async (url, method) => {
      if (!method) return {document:{name:"Lunch.pdf"}, references:[{kind:"group",label:"Group"}], revision:"reviewed"};
      requests.push([url,method]);
    },
    saved: async () => {},
  });
  await ctx.deleteDocument("doc");
  assert.equal(button.disabled, true);
  await assert.rejects(submit(new Map()), /bestätigen/);
  assert.equal(requests.length, 0);
  confirm.checked = true;
  confirm.onchange();
  assert.equal(button.disabled, false);
  await submit(new Map([["unlink", "on"]]));
  assert.deepEqual(requests, [["/admin/documents/doc?unlink=true&revision=reviewed", "DELETE"]]);
});

function editorContext(documents = []) {
  const calls = [], checks = [];
  let submit;
  const ctx = vm.createContext({
    state: {documents}, FormData,
    e: (value) => String(value ?? ""),
    documentCategory: (doc) => doc.category || "Dokument",
    check: (name, label, checked) => { checks.push({name, label, checked}); return "checkbox"; },
    dialog: (_title, _html, callback) => { submit = callback; },
    api: async (url, method, body) => { calls.push({url, method, body}); return {id: "doc"}; },
    saved: async () => {}, refresh: async () => {}, documentPreview: () => {}, toast: () => {},
  });
  const source = readFileSync("server/static/app.js", "utf8");
  vm.runInContext(source.slice(source.indexOf("function documentFields("), source.indexOf("function documentPreview(")), ctx);
  return {ctx, calls, checks, submit: (data) => submit(data)};
}

test("document upload defaults to public and sends the inverse internal checkbox state", async () => {
  for (const internal of [true, false]) {
    const editor = editorContext();
    editor.ctx.uploadEditor("plan");
    assert.equal(editor.checks[0].name, "internal");
    assert.equal(editor.checks[0].checked, false);
    assert.match(editor.checks[0].label, /nur für interne Zwecke/);
    const data = new Map([["file", "test.pdf"], ["category", "Speiseplan"]]);
    if (internal) data.set("internal", "on");
    await editor.submit(data);
    assert.equal(editor.calls[0].body.get("public"), String(!internal));
  }
  const image = editorContext();
  image.ctx.uploadEditor("image");
  assert.equal(image.checks.length, 0);
  await image.submit(new Map([["file", "test.jpg"], ["category", "Meldungsbild"]]));
  assert.equal(image.calls[0].body.get("public"), "false");
});

test("document editing preserves existing permissions and applies both checkbox states", async () => {
  for (const publicValue of [true, false, undefined]) {
    for (const internal of [true, false]) {
      const editor = editorContext([{id: "doc", kind: "plan", name: "Plan.pdf", public: publicValue}]);
      editor.ctx.documentEditor("doc");
      assert.equal(editor.checks[0].checked, !publicValue);
      const data = new Map([["name", "Plan.pdf"], ["category", "Speiseplan"]]);
      if (internal) data.set("internal", "on");
      await editor.submit(data);
      assert.equal(editor.calls[0].body.public, !internal);
      assert.equal(editor.calls[0].body.revoke_group_release, (!internal) !== publicValue);
    }
  }
  const image = editorContext([{id: "doc", kind: "image", name: "Photo.jpg"}]);
  image.ctx.documentEditor("doc");
  assert.equal(image.checks.length, 0);
  await image.submit(new Map([["name", "Photo.jpg"], ["category", "Meldungsbild"]]));
  assert.equal(image.calls[0].body.public, false);
  assert.equal(image.calls[0].body.revoke_group_release, true);
});
