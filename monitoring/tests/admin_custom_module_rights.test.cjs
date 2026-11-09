const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const window = {};
const source = fs.readFileSync(path.join(__dirname, "..", "web", "shared_admin_ui.js"), "utf8");
vm.runInNewContext(source, { window }, { filename: "shared_admin_ui.js" });

test("les droits du constructeur désignent les modules personnalisés", () => {
    const markup = window.NMPSharedAdminUi.buildRoleFormMarkup({
        modules: [{ code: "module_builder", label: "Gestion des modules personnalisés", is_active: true }],
    });

    assert.match(markup, /Créer des modules personnalisés/);
    assert.match(markup, /Modifier ses modules personnalisés/);
    assert.match(markup, /Supprimer ses modules personnalisés/);
    assert.doesNotMatch(markup, /modules personnels/);
});
