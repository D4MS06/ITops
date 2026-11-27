const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../web/portal.js"), "utf8");
function load(context, name) {
    const match = source.match(new RegExp("(?:async )?function " + name + "\\([\\s\\S]*?\\r?\\n}\\r?\\n"));
    assert.ok(match, name);
    vm.runInNewContext(match[0], context);
}

function creationContext() {
    const relation = { id: 30, source_service_code: "marches", target_service_code: "fournisseurs" };
    const requested = [];
    const context = {
        state: {
            noCodeServiceRecordContext: { service: { code: "marches", tile_config: {} } },
            noCodeRecordEditor: { mode: "create", values: { intitule: "Marché de fournitures" } },
        },
        noCodeRecordEditableRelationsForContext: () => [relation],
        noCodeRelationLinkedServiceCodeForContext: (_context, item) => item.target_service_code,
        refreshOpenNoCodeRecordEditorMarkup: () => {},
        noCodeRecordFieldIsVisible: () => true,
        normalizeErrorMessage: value => value,
        fetchNoCodeServiceRecordsPage: async code => {
            requested.push(code);
            return { items: [{ id: "supplier", values: { nom: "Fournisseur Exemple" } }] };
        },
    };
    for (const name of ["noCodeRecordRelationState", "isNoCodeDynamicFieldRelation", "loadVisibleNoCodeDynamicRelationCandidates",
        "loadNoCodeRecordRelationCandidates", "loadNoCodeRecordRelationExperience"]) load(context, name);
    return { context, requested, relation };
}

test("créer un marché charge les fournisseurs titulaires sans attendre un panneau d'édition", async () => {
    const { context, requested } = creationContext();
    await context.loadNoCodeRecordRelationExperience();
    assert.deepEqual(requested, ["fournisseurs"]);
    const state = context.state.noCodeRecordEditor.relationStates["30"];
    assert.equal(state.candidatesLoaded, true);
    assert.equal(state.candidates[0].id, "supplier");
    assert.equal(state.links.length, 0);
});

test("les sélecteurs et champs dynamiques partagent le chargement et respectent les présélections", async () => {
    const { context, requested } = creationContext();
    context.state.noCodeServiceRecordContext.service.tile_config.dynamic_fields = [{ field_key: "supplier", relation_id: "30" }];
    context.state.noCodeRecordCreationContext = { relationSelections: { "30": ["supplier"] } };
    await context.loadNoCodeRecordRelationExperience();
    assert.deepEqual(requested, ["fournisseurs"]);
    assert.equal(context.state.noCodeRecordEditor.relationStates["30"].links[0].linked_record.id, "supplier");
});

for (const mode of ["selector", "dynamic"]) {
    test(`la création charge aussi une relation affichée en mode ${mode}, une seule fois`, async () => {
        const { context, requested } = creationContext();
        const tile = context.state.noCodeServiceRecordContext.service.tile_config;
        tile[mode === "dynamic" ? "dynamic_fields" : "relation_selectors"] = [{ field_key: "supplier", relation_id: "30" }];
        await context.loadNoCodeRecordRelationExperience();
        assert.deepEqual(requested, ["fournisseurs"]);
        assert.equal(context.state.noCodeRecordEditor.relationStates["30"].candidatesLoaded, true);
    });
}

test("la création ne charge pas les relations entrantes réservées à la fiche enregistrée", async () => {
    const { context, requested, relation } = creationContext();
    context.noCodeRecordEditableRelationsForContext = () => [relation, {
        id: 31, source_service_code: "commandes_informatiques", target_service_code: "marches",
    }];
    await context.loadNoCodeRecordRelationExperience();
    assert.deepEqual(requested, ["fournisseurs"]);
    assert.equal(context.state.noCodeRecordEditor.relationStates["31"], undefined);
});

test("un refus de lecture reste visible et le chargement peut reprendre après correction", async () => {
    const { context } = creationContext();
    context.state.noCodeRecordEditor.relationStates = {};
    const fetch = context.fetchNoCodeServiceRecordsPage;
    context.fetchNoCodeServiceRecordsPage = async () => { throw new Error("Droit de lecture Fournisseurs requis."); };
    await context.loadNoCodeRecordRelationCandidates("30");
    let state = context.state.noCodeRecordEditor.relationStates["30"];
    assert.equal(state.candidatesError, "Droit de lecture Fournisseurs requis.");
    assert.equal(state.candidatesLoaded, false);
    context.fetchNoCodeServiceRecordsPage = fetch;
    await context.loadNoCodeRecordRelationCandidates("30");
    state = context.state.noCodeRecordEditor.relationStates["30"];
    assert.equal(state.candidatesLoaded, true);
    assert.equal(state.candidatesError, "");
});
