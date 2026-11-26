const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const sandbox = {
    window: {},
    document: { addEventListener() {}, getElementById() { return null; } },
    HTMLInputElement: class {},
};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../web/shared_ui.js"), "utf8"), sandbox);
const source = fs.readFileSync(path.join(__dirname, "../web/portal.js"), "utf8");
for (const name of ["noCodeRecordQuickFilterValueMap", "noCodeRecordRowsForContext", "showAllNoCodeServiceRecords"]) {
    const definition = source.match(new RegExp("function " + name + "\\([\\s\\S]*?\\r?\\n}\\r?\\n"));
    assert.ok(definition, name);
    vm.runInNewContext(definition[0], sandbox);
}
sandbox.noCodeRecordQuickFilterColumns = () => [{ field_key: "statut", kind: "text" }, { field_key: "date", kind: "date" }];
sandbox.noCodeRecordColumnValue = (row, column) => row.values[column.field_key];
sandbox.isNoCodeDateYearQuickFilter = (column) => column.field_key === "date";
const order = { id: "order", values: { statut: "Devis reçu", date: "" } };
const context = {
    service: { code: "commandes_informatiques" },
    records: [order],
    quickFilters: { date: "2026" },
    linkedQuickFilters: {},
};
assert.equal(sandbox.noCodeRecordRowsForContext(context).length, 0);
context.quickFilters = {};
assert.equal(sandbox.noCodeRecordRowsForContext(context).length, 1);
context.quickFilters = { statut: "Devis" };
assert.equal(sandbox.noCodeRecordRowsForContext(context).length, 0);
context.recordsPage = { source: "query" };
assert.equal(sandbox.noCodeRecordRowsForContext(context).length, 1);
context.linkedQuickFilters = { supplier: "hidden" };
context.searchQuery = "hidden";
sandbox.showAllNoCodeServiceRecords(context);
assert.equal(Object.keys(context.quickFilters).length, 0);
assert.equal(Object.keys(context.linkedQuickFilters).length, 0);
assert.equal(context.searchQuery, "");
const Tree = sandbox.window.NMPSharedUi.treeView.SharedTreeView;
assert.equal(Tree.prototype._resolveQuery.call({ getSearchQuery: () => "", searchInput: { value: "stale" } }), "");
assert.equal(Tree.prototype._resolveQuery.call({ searchInput: { value: "Test" } }), "test");
