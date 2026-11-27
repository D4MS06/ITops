const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

class Select {}
class Details {}
class Form {
    constructor() {
        this.template = { value: "" };
        this.feedback = { textContent: "" };
        this.profile = Object.assign(new Select(), { name: "role_module_profile_quotes", value: "custom" });
        this.checks = ["read", "update", "credentials_view", "credentials_manage", "notifications_followup"]
            .map(value => ({ value, checked: false, closest: () => this.card }));
        this.card = {
            querySelectorAll: () => this.checks,
            querySelector: selector => selector === "details" ? new Details() : this.profile,
        };
        this.profile.closest = () => this.card;
        this.dataset = {};
    }
    querySelector(selector) { return selector === "#modal-role-feedback" ? this.feedback : this.template; }
    querySelectorAll(selector) {
        if (selector.startsWith("select")) return [this.profile];
        return selector.endsWith(":checked") ? this.checks.filter(node => node.checked) : this.checks;
    }
}
const window = { FormData: class { constructor(form) { this.form = form; } get(key) { return key === "role_template" ? this.form.template.value : ""; } } };
vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../web/shared_admin_ui.js"), "utf8"), {
    window, HTMLFormElement: Form, HTMLSelectElement: Select, HTMLDetailsElement: Details,
    CSS: { escape: value => value },
});
const ui = window.NMPSharedAdminUi;

test("Complet inclut le suivi, et une exception reste décochée après application du modèle global", () => {
    const form = new Form();
    form.template.value = "administrator";
    ui.syncRoleTemplate(form, form.template);
    assert.equal(form.checks.find(node => node.value === "notifications_followup").checked, true);
    const subscription = form.checks.find(node => node.value === "notifications_followup");
    subscription.checked = false;
    ui.syncRolePermissionCheckbox(form, subscription);
    const permissions = ui.parseRoleForm(form).payload.module_permissions.quotes;
    assert.ok(permissions.includes("read"));
    assert.ok(permissions.includes("update"));
    assert.ok(!permissions.includes("notifications_followup"));
    assert.equal(form.template.value, "");
});

test("cocher le suivi active la lecture sans écriture et retirer la lecture retire les droits dépendants", () => {
    const form = new Form();
    const subscription = form.checks.find(node => node.value === "notifications_followup");
    subscription.checked = true;
    ui.syncRolePermissionCheckbox(form, subscription);
    let permissions = ui.parseRoleForm(form).payload.module_permissions.quotes;
    assert.deepEqual(Array.from(permissions), ["read", "notifications_followup"]);
    const read = form.checks.find(node => node.value === "read");
    read.checked = false;
    ui.syncRolePermissionCheckbox(form, read);
    assert.ok(form.checks.every(node => !node.checked));
    assert.equal(ui.parseRoleForm(form).payload.module_codes.length, 0);
    assert.match(form.feedback.textContent, /notifications/);
});

test("ouvrir un ancien rôle administrateur ne présélectionne pas un modèle qui abonne au suivi", () => {
    const markup = ui.buildRoleFormMarkup({
        role: { code: "admin", module_codes: ["quotes"], module_permissions: { quotes: ["read", "update"] } },
        modules: [{ code: "quotes", label: "Devis", is_active: true }],
    });
    assert.match(markup, /Recevoir les notifications de suivi/);
    assert.doesNotMatch(markup, /value="notifications_followup" checked/);
    assert.doesNotMatch(markup, /value="administrator" selected/);
});

test("la fabrique partagée transmet les attributs de données sans permettre une injection", () => {
    const source = fs.readFileSync(path.join(__dirname, "../web/shared_ui.js"), "utf8");
    const start = source.indexOf("    function createFieldMarkup(");
    const end = source.indexOf("\n    const ACTION_BUTTON_PRESETS", start);
    const context = { defaultEscape: value => String(value ?? "").replaceAll('"', "&quot;").replaceAll("<", "&lt;") };
    vm.runInNewContext(source.slice(start, end), context);
    for (const options of [{ inputType: "select", options: [] }, { multiline: true }, {}]) {
        const markup = context.createFieldMarkup({
            key: "target", label: "Destinataire", value: "", ...options,
            data: { action_recipient_kind: '"<', 'bad" onclick': "injected" },
        });
        assert.match(markup, /data-action-recipient-kind="&quot;&lt;"/);
        assert.doesNotMatch(markup, /onclick|injected/);
    }
});

test("les actions partagées distinguent les tâches bloquées et celles à traiter", async () => {
    const source = fs.readFileSync(path.join(__dirname, "../web/portal.js"), "utf8");
    const start = source.indexOf("class NotificationTasksTreeView extends");
    const end = source.indexOf("\nfunction ensureNotificationTasksTreeView", start);
    let options;
    const updates = [];
    const context = {
        window: { NMPSharedUi: { treeView: { SharedTreeView: class { constructor(value) { options = value; } } } } },
        document: { getElementById: () => ({}) }, state: {},
        isPendingNotificationTask: row => row.status === "pending",
        notificationTaskFilteredRows: () => [],
        updateNotificationTaskStatus: async (id, status) => updates.push([id, status]),
    };
    vm.runInNewContext(source.slice(start, end) + "\nnew NotificationTasksTreeView();", context);
    const rows = [{ id: "p", status: "pending" }, { id: "b", status: "blocked" }, { id: "s", status: "sent" }];
    await options.onTreeAction({ actionId: "done", rows });
    assert.deepEqual(updates.splice(0), [["p", "done"]]);
    await options.onTreeAction({ actionId: "resume", rows });
    assert.deepEqual(updates.splice(0), [["b", "pending"]]);
    await options.onTreeAction({ actionId: "cancel", rows });
    assert.deepEqual(updates.splice(0), [["p", "cancelled"], ["b", "cancelled"]]);
});
