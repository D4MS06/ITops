const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

test("l'export de vue transmet les colonnes visibles dans leur ordre et les lignes affichées", async () => {
    let authorizationPath;
    let download;
    const window = {
        NMPSharedDownload: { triggerBrowserDownload: (blob, filename) => { download = { blob, filename }; } },
    };
    const source = fs.readFileSync(path.join(__dirname, "..", "web", "shared_import.js"), "utf8");
    vm.runInNewContext(source, {
        window,
        Blob,
        fetch: async (path) => {
            authorizationPath = path;
            return { ok: true };
        },
    });

    await window.NMPSharedImport.downloadTreeViewExport({
        resourceCode: "copieurs",
        tree: {
            getVisibleColumns: () => [
                { key: "linked", label: "Service lié" },
                { key: "name", label: "Nom" },
                { key: "actions", label: "Actions" },
            ],
            getVisibleRows: () => Array.from({ length: 1201 }, (_, index) => ({
                linked: "Informatique; Accueil", name: `Copieur ${index + 1}`,
            })),
        },
        includeColumn: (column) => column.key !== "actions",
    });

    assert.equal(authorizationPath, "/exports/treeview/authorize?resource_code=copieurs");
    assert.equal(download.filename, "export_copieurs.csv");
    const csv = await download.blob.text();
    assert.equal(csv.split("\r\n").length, 1203);
    assert.ok(csv.replace(/^\ufeff/, "").startsWith("Service lié;Nom\r\n\"Informatique; Accueil\";Copieur 1\r\n"));
    assert.ok(csv.includes("Copieur 1201"));
});

test("l'export standard applique le nom choisi et enregistre dans la destination choisie", async () => {
    let saved = null;
    const destination = { name: "Mon export.csv" };
    const window = {
        NMPSharedDownload: { saveBlob: async (blob, filename, handle) => { saved = { blob, filename, handle }; return handle.name; } },
    };
    const source = fs.readFileSync(path.join(__dirname, "..", "web", "shared_import.js"), "utf8");
    vm.runInNewContext(source, {
        window,
        fetch: async () => ({
            ok: true,
            blob: async () => new Blob(["nom\r\nCopieur"]),
            headers: { get: () => 'attachment; filename="service_records_copieurs.csv"' },
        }),
    });

    const outcome = await window.NMPSharedImport.downloadExport({
        candidatePaths: ["/records/export"],
        filename: "Mon export",
        destination,
    });

    assert.equal(saved.filename, "Mon export.csv");
    assert.equal(saved.handle, destination);
    assert.equal(outcome.filename, "Mon export.csv");
});

test("le choix de destination utilise le nom propose et ecrit dans le fichier choisi", async () => {
    let suggestedName = "";
    let written = "";
    const handle = {
        name: "export_Copieurs.csv",
        createWritable: async () => ({
            write: async (blob) => { written = await blob.text(); },
            close: async () => {},
        }),
    };
    const window = {
        isSecureContext: true,
        showSaveFilePicker: async (options) => { suggestedName = options.suggestedName; return handle; },
    };
    const source = fs.readFileSync(path.join(__dirname, "..", "web", "shared_download.js"), "utf8");
    vm.runInNewContext(source, { window });

    const destination = await window.NMPSharedDownload.chooseSaveDestination("export_Copieurs.csv");
    const filename = await window.NMPSharedDownload.saveBlob(new Blob(["donnees"]), "export_Copieurs.csv", destination);

    assert.equal(suggestedName, "export_Copieurs.csv");
    assert.equal(filename, "export_Copieurs.csv");
    assert.equal(written, "donnees");
});

test("la fenêtre d'export propose le nom du module et transmet le choix", async () => {
    let markup = "";
    let submit;
    let proposedName = "";
    const destination = { name: "Bilan.csv" };
    const body = {
        querySelector: (selector) => {
            if (selector === "[data-treeview-export-options]") return { addEventListener: (_event, handler) => { submit = handler; } };
            if (selector === 'input[name="export_mode"]:checked') return { value: "view" };
            if (selector === '[name="export_filename"]') return { value: "Bilan" };
            return null;
        },
    };
    const window = {
        NMPSharedDownload: { chooseSaveDestination: async (name) => { proposedName = name; return destination; } },
        NMPSharedUi: {
            shell: { createChildModal: (options) => { markup = options.bodyMarkup; return { body, close: () => {} }; } },
            formControls: { createModalActionsMarkup: () => "" },
        },
    };
    const source = fs.readFileSync(path.join(__dirname, "..", "web", "shared_import.js"), "utf8");
    vm.runInNewContext(source, { window });

    const selectionPromise = window.NMPSharedImport.selectExportMode({ moduleName: "Copieurs du siège", visibleCount: 1201 });
    assert.ok(markup.includes('value="export_Copieurs_du_siège.csv"'));
    assert.ok(markup.includes("Export des données du module"));
    assert.ok(markup.includes("Vue actuelle (colonnes et relations affichées, 1201 lignes)"));
    await submit({ preventDefault: () => {} });
    const selection = await selectionPromise;

    assert.equal(proposedName, "Bilan.csv");
    assert.equal(selection.mode, "view");
    assert.equal(selection.filename, "Bilan.csv");
    assert.equal(selection.destination, destination);
});

test("le chargement Tout parcourt toutes les pages sans limiter les relations recherchées", async () => {
    const source = fs.readFileSync(path.join(__dirname, "..", "web", "portal.js"), "utf8");
    const functionSource = source.match(/async function fetchAllNoCodeServiceRecords[\s\S]*?(?=\nasync function reloadNoCodeServiceRecordsPage)/)?.[0];
    assert.ok(functionSource);
    const offsets = [];
    const context = {
        findNoCodeRelationSystemEntity: () => null,
        fetchNoCodeServiceRecordsPage: async (_code, options) => {
            offsets.push(options.offset);
            assert.equal(options.search, "");
            assert.equal(Object.keys(options.filters).length, 0);
            return {
                items: Array.from({ length: Math.min(500, 1201 - options.offset) }, (_, index) => ({ id: options.offset + index })),
                total: 1201,
                offset: options.offset,
            };
        },
    };
    vm.runInNewContext(`${functionSource}\nglobalThis.fetchAll = fetchAllNoCodeServiceRecords;`, context);

    const result = await context.fetchAll("copieurs", { search: "valeur liée", filters: { status: "Actif" } });

    assert.deepEqual(offsets, [0, 500, 1000]);
    assert.equal(result.items.length, 1201);
    assert.equal(result.limit, 0);
});

test("le chargement Tout refuse les doublons entre deux pages", async () => {
    const source = fs.readFileSync(path.join(__dirname, "..", "web", "portal.js"), "utf8");
    const functionSource = source.match(/async function fetchAllNoCodeServiceRecords[\s\S]*?(?=\nasync function reloadNoCodeServiceRecordsPage)/)?.[0];
    assert.ok(functionSource);
    const context = {
        findNoCodeRelationSystemEntity: () => null,
        fetchNoCodeServiceRecordsPage: async (_code, options) => ({
            items: options.offset === 0
                ? Array.from({ length: 500 }, (_, index) => ({ id: index + 1 }))
                : [{ id: 500 }],
            total: 501,
            offset: options.offset,
        }),
    };
    vm.runInNewContext(`${functionSource}\nglobalThis.fetchAll = fetchAllNoCodeServiceRecords;`, context);

    await assert.rejects(context.fetchAll("copieurs"), /inventaire a change/);
});

test("un filtre sur une colonne liée reste actif sans filtre de champ", () => {
    const source = fs.readFileSync(path.join(__dirname, "..", "web", "portal.js"), "utf8");
    const functionSource = source.match(/function noCodeRecordRowsForContext[\s\S]*?(?=\nfunction noCodeRecordRelationsForContext)/)?.[0];
    assert.ok(functionSource);
    const context = {
        noCodeRecordQuickFilterValueMap: () => ({}),
        noCodeRecordQuickFilterColumns: () => [],
        linkedColumnValuesForRow: (row) => row.links,
    };
    vm.runInNewContext(`${functionSource}\nglobalThis.filteredRows = noCodeRecordRowsForContext;`, context);

    const rows = context.filteredRows({
        records: [{ id: 1, links: ["Informatique"] }, { id: 2, links: ["Accueil"] }],
        linkedQuickFilters: { "linked:service": "info" },
    });
    assert.deepEqual(rows.map((row) => row.id), [1]);
});
