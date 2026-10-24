const assert = require("node:assert/strict");
const {readFileSync} = require("node:fs");
const {test} = require("node:test");
const vm = require("node:vm");

function context(extra = {}) {
  const ctx = vm.createContext(extra);
  for (const file of ["operating-hours", "device-settings"])
    vm.runInContext(readFileSync(`server/static/${file}.js`, "utf8"), ctx);
  return ctx;
}

test("operating hours and content windows serialize independently in the same editor", () => {
  const operating = {days:[0,1,2,3,4], "operating-start":"07:00", "operating-end":"18:00"};
  const content = {days:[0,1,2,3,4], "hour-start":"11:00", "hour-end":"13:00",
    "hour-name":"Mittag", "hour-mode":"plan", "hour-document":"menu", "hour-area":"secondary"};
  const form = {fields:new Map([["operating_enabled","on"], ["operating_timezone","Europe/Berlin"]]),
    ".operating-row":[operating], ".hour-row":[content]};
  const ctx = context({
    FormData: class {constructor(form) {this.form=form;} has(key) {return this.form.fields.has(key);}
      get(key) {return this.form.fields.get(key);}},
    $$:(selector, form) => form[selector],
    $:(selector, row) => ({value:row[selector.match(/name=(.*)\]/)[1]]}),
    readDays:row => row.days,
  });
  const json = value => JSON.parse(JSON.stringify(value));
  assert.deepEqual(json(ctx.readOperatingHours(form)), {enabled:true, timezone:"Europe/Berlin",
    windows:[{days:[0,1,2,3,4],start:"07:00",end:"18:00"}]});
  assert.deepEqual(json(ctx.readHours(form)), [{days:[0,1,2,3,4],name:"Mittag",start:"11:00",end:"13:00",
    mode:"plan",document_id:"menu",area:"secondary"}]);
  form.fields.delete("operating_enabled");
  assert.equal(ctx.readOperatingHours(form).enabled, false);
  assert.equal(ctx.readHours(form)[0].document_id, "menu");
});

test("summaries distinguish unrestricted operation, complete closure, and overnight windows", () => {
  const ctx = context({days:["Mo","Di","Mi","Do","Fr","Sa","So"]});
  const hours = ctx.operatingDefaults();
  assert.match(ctx.operatingSummary(hours), /Rund um die Uhr/);
  hours.enabled = true;
  assert.match(ctx.operatingSummary(hours), /Durchgehend Ruhezeit/);
  hours.windows = [{days:[0],start:"22:00",end:"02:00"}];
  assert.match(ctx.operatingSummary(hours), /Mo.*22:00–02:00.*Folgetag/);
  hours.windows[0].end = "22:00";
  assert.match(ctx.operatingSummary(hours), /ganztägig/);
});
