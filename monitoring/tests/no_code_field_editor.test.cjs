const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

test("modifier une règle conserve ses paramètres et les validations désactivées", () => {
    const source = fs.readFileSync(path.join(__dirname, "..", "web", "portal.js"), "utf8").replaceAll("\r\n", "\n");
    const start = source.indexOf("    const automationCards = Array.from(form.querySelectorAll");
    const end = source.indexOf("\n}\n\nfunction refreshNoCodeFieldDefaultChoices", start);
    assert.ok(start > 0 && end > start);
    const controls = {
        "[data-automation-trigger]": "threshold", "[data-automation-field]": "quantity",
        "[data-automation-value]": "12", "[data-action-type]": "set_field_from_event",
        "[data-action-field]": "received",
    };
    const control = (selector) => ({ value: controls[selector] || "" });
    const action = { querySelector: control };
    const card = {
        dataset: { automationRule: "r", edited: "true" },
        querySelector: control,
        querySelectorAll: (selector) => selector === "[data-automation-action]" ? [action] : [],
    };
    const validation = {
        dataset: { validationRule: "v" },
        querySelector: (selector) => ({ value: {
            "[data-validation-condition-field]": "status",
            "[data-validation-condition-operator]": "equals",
            "[data-validation-required-field]": "vendor",
            "[data-validation-message]": "Message ajusté",
        }[selector] || "" }),
    };
    const form = {
        querySelectorAll: (selector) => selector === "[data-automation-rule]" ? [card] : [validation],
    };
    const editor = {
        automation_rules: [{
            id: "r", trigger: { type: "threshold", field_key: "quantity", operator: "greater_or_equal" },
            actions: [{ type: "set_field_from_event", event_value_key: "sent_at", only_if_empty: false }],
        }],
        validation_rules: [{
            id: "v", enabled: false, condition: { field_key: "status", operator: "equals", value: "Sent" },
            required_field_keys: ["vendor", "date"], message: "Original",
        }],
    };
    const context = { readLinkedRecordAction: () => ({}) };
    vm.runInNewContext("function syncRules(form, editor) {\n" + source.slice(start, end) + "\n}", context);
    context.syncRules(form, editor);
    assert.equal(editor.automation_rules[0].trigger.operator, "greater_or_equal");
    assert.equal(editor.automation_rules[0].trigger.value, "12");
    assert.equal(editor.automation_rules[0].actions[0].event_value_key, "sent_at");
    assert.equal(editor.automation_rules[0].actions[0].only_if_empty, false);
    assert.equal(editor.validation_rules[0].enabled, false);
    assert.equal(editor.validation_rules[0].message, "Original");
    validation.dataset.edited = "true";
    context.syncRules(form, editor);
    assert.equal(editor.validation_rules[0].enabled, false);
    assert.equal(editor.validation_rules[0].message, "Message ajusté");
    assert.deepEqual(Array.from(editor.validation_rules[0].required_field_keys), ["vendor", "date"]);
});

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
