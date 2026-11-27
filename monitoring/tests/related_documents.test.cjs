const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");

const source = fs.readFileSync(path.join(__dirname, "../web/portal.js"), "utf8");

function load(name, context) {
    const match = source.match(new RegExp("function " + name + "\\([\\s\\S]*?\\r?\\n}\\r?\\n"));
    assert.ok(match, name);
    vm.runInNewContext(match[0], context);
}

test("le dossier affiché utilise des noms lisibles et conserve les valeurs manquantes", () => {
    const context = {
        state: { noCodeServiceRecordContext: { service: { code: "orders" } } },
        noCodeServiceDocumentFolderFieldKey: entry => entry.folder_field_key,
        noCodeServiceDocumentFolderSourceKind: entry => entry.folder_source_kind,
        noCodeRecordDocumentRelationFolder: () => "Fournisseur Exemple",
        noCodeRecordPrimaryLabel: (_service, record) => record.values.nom || record.id,
    };
    load("noCodeRecordDocumentFolder", context);
    const record = { recordId: "opaque-id", values: { supplier: "Fournisseur Exemple" } };
    const entry = { folder_source_kind: "field", folder_field_key: "supplier" };
    assert.equal(context.noCodeRecordDocumentFolder(entry, record), "Fournisseur Exemple");
    record.values.supplier = "";
    assert.equal(context.noCodeRecordDocumentFolder(entry, record), "");
    assert.equal(context.noCodeRecordDocumentFolder({ folder_source_kind: "record" }, record), "");
    record.values.nom = "Commande du service technique";
    assert.equal(context.noCodeRecordDocumentFolder({ folder_source_kind: "record" }, record), "Commande du service technique");
    assert.equal(context.noCodeRecordDocumentFolder(entry, record), "Commande du service technique");
    entry.folder_fallback_kind = "error";
    assert.equal(context.noCodeRecordDocumentFolder(entry, record), "");
});

test("les documents liés conservent leur racine de stockage et leur provenance", () => {
    const context = {};
    load("noCodeDocumentLinkItems", context);
    const [item] = context.noCodeDocumentLinkItems([{
        id: "pdf", filename: "quote.pdf",
        metadata: { root_id: "source-root", path: "request/quote.pdf" },
        document_source: { module_code: "requests", record_id: "q", readonly: true },
    }]);
    assert.equal(item.root_id, "source-root");
    assert.equal(item.file_id, "pdf");
    assert.equal(item.document_source.readonly, true);
});

test("les consultations de documents conservent la zone partagée des messages d'erreur", () => {
    const sections = [];
    const context = {
        buildTreeSectionMarkup: options => { sections.push(options); return "tree"; },
        createModalActionsMarkup: () => "actions",
    };
    for (const name of ["buildNoCodeRecordDocumentLinksModalMarkup", "buildLinkedNoCodeRecordDocumentsMarkup"]) {
        load(name, context);
        context[name]();
    }
    assert.equal(sections.length, 2);
    for (const section of sections) assert.equal(section.feedbackId, "modal-service-record-feedback");
});

test("le TreeView ouvre le fichier source et réserve sa gestion à sa fiche", async () => {
    let options, downloaded, opened;
    class Element {}
    const context = {
        HTMLElement: Element,
        document: { getElementById: () => new Element() },
        window: { NMPSharedUi: { treeView: { SharedTreeView: class {
            constructor(value) { options = value; }
            render() {}
        } } } },
        downloadNoCodeRecordDocument: (...args) => { downloaded = args; },
        openLinkedNoCodeRecordFromSummary: (...args) => { opened = args; },
    };
    load("renderNoCodeDocumentTree", context);
    const item = {
        file_id: "pdf", path: "request/quote.pdf", root_id: "source-root",
        document_source: { module_code: "requests", record_id: "q", module_label: "Demandes", readonly: true },
    };
    context.renderNoCodeDocumentTree({ headId: "h", bodyId: "b", items: [item], documentIndex: 2, canDelete: true });
    const remove = options.rowActions.find(action => action.id === "delete");
    assert.equal(remove.visible([item]), false);
    assert.equal(remove.visible([{ file_id: "local" }]), true);
    await options.onTreeAction({ actionId: "download", rows: [item] });
    assert.deepEqual(downloaded, [2, "request/quote.pdf", "source-root"]);
    await options.onTreeAction({ actionId: "source", rows: [item] });
    assert.deepEqual(opened, ["requests", "q"]);
});

test("le chargement des documents parcourt les inventaires de plus de 500 fiches", async () => {
    const requested = [];
    const context = {
        noCodeRecordDocumentEntries: () => [{ field_key: "quote" }],
        noCodeServiceDocumentFieldKey: entry => entry.field_key,
        noCodeRecordDocumentStateKey: String,
        noCodeDocumentLinkItems: value => value,
        URLSearchParams,
        requestJson: async url => {
            const ids = new URL(url, "http://itops").searchParams.get("record_ids").split(",");
            requested.push(ids.length);
            assert.ok(ids.length <= 500);
            return Object.fromEntries(ids.map(id => [id, [{ id: "file-" + id }]]));
        },
    };
    const match = source.match(/async function hydrateNoCodeRecordDocumentLinkSummaries[\s\S]*?(?=\r?\nfunction buildNoCodeRecordDocumentFieldMarkup)/);
    assert.ok(match);
    vm.runInNewContext(match[0], context);
    const inventory = {
        service: { code: "orders" },
        records: Array.from({ length: 1201 }, (_, id) => ({ id: String(id) })),
    };
    await context.hydrateNoCodeRecordDocumentLinkSummaries(inventory);
    assert.deepEqual(requested, [500, 500, 201]);
    assert.equal(inventory.documentLinkSummaries["0"]["1200"][0].id, "file-1200");
});
