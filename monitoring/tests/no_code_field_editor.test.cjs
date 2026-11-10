const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

function openFieldEditor(form) {
    const source = fs.readFileSync(path.join(__dirname, "..", "web", "portal.js"), "utf8");
    const functionSource = source.match(/function startNoCodeFieldEditor[\s\S]*?(?=\nfunction removeNoCodeField)/)?.[0];
    assert.ok(functionSource);
    class Input {
        constructor(value, checked = true) { this.value = value; this.checked = checked; }
    }
    const editor = {
        fields: [{ field_key: "numero", label: "Numéro", field_kind: "text" }],
        tile_config: { form_layout: { single_column: false } },
        fieldEditor: null,
    };
    let renderCount = 0;
    const context = {
        state: { noCodeServiceEditor: editor },
        document: { getElementById: (id) => id === "modal-service-form" ? form?.(Input) || null : null },
        HTMLInputElement: Input,
        noCodeFieldEditorSeed: (field) => ({ mode: field ? "edit" : "create", originalKey: field?.field_key || "" }),
        noCodeDynamicFieldConfiguration: () => ({}),
        noCodeFieldVisibilityConfiguration: () => ({}),
        renderNoCodeServiceEditor: () => { renderCount++; },
        renderNoCodeServiceDocumentsTreeView: () => {},
    };
    vm.runInNewContext(`${functionSource}\nglobalThis.openField = startNoCodeFieldEditor;`, context);
    context.openField("numero");
    return { editor, renderCount };
}

test("l'engrenage ouvre un champ existant quand les options du formulaire sont absentes", () => {
    const result = openFieldEditor(null);

    assert.equal(result.editor.fieldEditor.mode, "edit");
    assert.equal(result.editor.fieldEditor.originalKey, "numero");
    assert.equal(result.renderCount, 1);
});

test("l'engrenage conserve les choix de présentation du formulaire", () => {
    const result = openFieldEditor((Input) => ({
        querySelector: () => new Input("", true),
        querySelectorAll: (selector) => selector.includes("multiline")
            ? [new Input("numero")]
            : [new Input("commentaire")],
    }));

    assert.equal(result.editor.fieldEditor.mode, "edit");
    assert.equal(result.editor.tile_config.form_layout.single_column, true);
    assert.deepEqual(Array.from(result.editor.tile_config.form_layout.multiline_field_keys), ["numero"]);
    assert.deepEqual(Array.from(result.editor.tile_config.form_layout.create_hidden_field_keys), ["commentaire"]);
});
