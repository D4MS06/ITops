const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const window = {};
for (const filename of ["shared_remote_actions.js", "shared_device_editor.js", "shared_device_editor_controller.js"]) {
    const source = fs.readFileSync(path.join(__dirname, "..", "web", filename), "utf8");
    vm.runInNewContext(source, { window, FormData }, { filename });
}

const schema = {
    fields: ["name", "ip", "device_subtype", "id_Teamviewer", "web_url", "ssh_user", "device_login", "device_password"]
        .map((field_key) => ({ field_key })),
    actions: [
        { action_key: "teamviewer", target_kind: "builtin", target_value: "teamviewer", os_scope: "windows" },
        { action_key: "remote_desktop", target_kind: "builtin", target_value: "remote_desktop", os_scope: "windows" },
        { action_key: "ssh", target_kind: "builtin", target_value: "ssh", os_scope: "linux" },
        { action_key: "web", target_kind: "builtin", target_value: "web", os_scope: "firmware" },
        { action_key: "custom_ssh", target_kind: "command", target_value: "ssh", os_scope: "windows" },
    ],
};

function names(markup) {
    return [...markup.matchAll(/name="([^"]+)"/g)].map((match) => match[1]);
}

test("les champs distants suivent les plugins actifs pour chaque systeme", () => {
    const editor = window.NMPSharedDeviceEditor;
    const windows = names(editor.fieldsMarkup({ device_subtype: "windows" }, schema));
    const linux = names(editor.fieldsMarkup({ device_subtype: "linux" }, schema));
    const firmware = names(editor.fieldsMarkup({ device_subtype: "firmware" }, schema));

    assert.equal(windows.includes("id_Teamviewer"), true);
    assert.equal(windows.includes("ssh_user"), false);
    assert.equal(windows.includes("web_url"), false);
    assert.equal(windows.includes("ip"), true); // Remote Desktop utilise l'IP commune.
    assert.equal(linux.includes("ssh_user"), true);
    assert.equal(linux.includes("id_Teamviewer"), false);
    assert.equal(firmware.includes("web_url"), true);
    assert.equal(firmware.includes("ssh_user"), false);
    assert.equal(windows.includes("device_login"), true); // Option identifiants independante.
    assert.equal(windows.includes("device_password"), true);
});

test("les cartouches ne proposent que les plugins actifs pour l'OS du device", () => {
    const remote = window.NMPRemoteActions;
    const windows = remote.pluginActionsForDevice(schema, { device_subtype: "windows" });
    const linux = remote.pluginActionsForDevice(schema, { device_subtype: "linux" });
    assert.deepEqual(Array.from(windows, (action) => action.target_value), ["remote_desktop", "teamviewer"]);
    assert.deepEqual(Array.from(linux, (action) => action.target_value), ["ssh"]);
    const editor = window.NMPSharedDeviceEditor;
    const windowsMarkup = editor.remotePluginButtonsMarkup({ ip: "192.168.1.20", device_subtype: "windows", id_Teamviewer: "123" }, schema);
    const linuxMarkup = editor.remotePluginButtonsMarkup({ ip: "192.168.1.20", device_subtype: "linux", ssh_user: "admin" }, schema);
    assert.match(windowsMarkup, /data-device-remote-action="teamviewer"/);
    assert.match(windowsMarkup, /data-device-remote-action="remote_desktop"/);
    assert.doesNotMatch(windowsMarkup, /data-device-remote-action="ssh"/);
    assert.match(linuxMarkup, /data-device-remote-action="ssh"/);
    assert.doesNotMatch(linuxMarkup, /data-device-remote-action="teamviewer"/);
});

test("l'action SSH construit une cible locale sans mot de passe", () => {
    const remote = window.NMPRemoteActions;
    assert.equal(remote.builtinActionUrl({ ip: "192.168.1.20", ssh_user: "admin" }, "ssh"), "ssh://admin@192.168.1.20");
    assert.equal(remote.builtinActionUrl({ ip: "192.168.1.20" }, "ssh"), "ssh://192.168.1.20");
    assert.equal(remote.builtinActionUrl({ ip: "192.168.1.20/path" }, "ssh"), "");
    const markup = window.NMPSharedDeviceEditor.sshLaunchMarkup({ ip: "192.168.1.20", ssh_user: "admin" });
    assert.match(markup, /href="ssh:\/\/admin@192\.168\.1\.20"/);
    assert.doesNotMatch(markup, /password|mot de passe/i);
});

test("un ancien champ de schema ou une action non builtin ne reactive pas un plugin", () => {
    const withoutPlugins = { ...schema, actions: schema.actions.filter((action) => action.action_key === "custom_ssh") };
    const fields = names(window.NMPSharedDeviceEditor.fieldsMarkup({ device_subtype: "windows" }, withoutPlugins));
    assert.equal(fields.includes("ssh_user"), false);
    assert.equal(fields.includes("id_Teamviewer"), false);
    assert.equal(fields.includes("web_url"), false);
});

test("une action par defaut devenue indisponible est remplacee par une action active", () => {
    const markup = window.NMPSharedDeviceEditor.fieldsMarkup({ device_subtype: "linux", action_double_click: "teamviewer" }, schema);
    assert.match(markup, /<option value="ssh" selected>/);
    assert.doesNotMatch(markup, /<option value="teamviewer"/);
});

test("l'action distante de la liste suit la configuration du device puis celle de son OS", () => {
    const remote = window.NMPRemoteActions;
    const configuredSchema = {
        ...schema,
        fields: [...schema.fields, { field_key: "action_default_by_os", default_value: JSON.stringify({ windows: "remote_desktop" }) }],
    };
    assert.equal(remote.configuredDefaultActionForDevice(configuredSchema, { device_subtype: "windows" })?.action_key, "remote_desktop");
    assert.equal(remote.configuredDefaultActionForDevice(configuredSchema, { device_subtype: "windows", action_double_click: "teamviewer" })?.action_key, "teamviewer");
    assert.equal(remote.configuredDefaultActionForDevice(configuredSchema, { device_subtype: "linux", action_double_click: "teamviewer" })?.action_key, "ssh");
    assert.equal(remote.configuredDefaultActionForDevice({ actions: [], fields: [] }, { device_subtype: "linux" }), null);
});

test("la fiche propose la revelation seulement pour un mot de passe enregistre", () => {
    const editor = window.NMPSharedDeviceEditor;
    const saved = editor.markup({ id: "1", has_device_password: true }, schema, { passwordRevealEnabled: true });
    assert.match(saved, /data-device-password-reveal="true"/);
    assert.match(saved, /autocomplete="new-password"/);
    assert.doesNotMatch(saved, /value="secret"/);
    assert.doesNotMatch(editor.markup({ id: "2" }, schema, { passwordRevealEnabled: true }), /data-device-password-reveal/);
    assert.doesNotMatch(editor.markup({ has_device_password: true }, schema, { mode: "create", passwordRevealEnabled: true }), /data-device-password-reveal/);
});

test("le bouton de la fiche revele le mot de passe persiste sans transmettre le brouillon", async () => {
    const listeners = new Map();
    const feedback = { textContent: "" };
    const form = {
        addEventListener: (name, handler) => listeners.set(name, [...(listeners.get(name) || []), handler]),
        querySelector: () => feedback,
    };
    let received;
    const editor = {
        markup: (_device, _schema, options) => {
            assert.equal(options.passwordRevealEnabled, true);
            return "<form></form>";
        },
        payload: () => ({ device_password: "brouillon secret" }),
        refreshFields: () => {},
    };
    const controller = window.NMPDeviceEditorController.create({
        repository: { load: async () => null, loadSchema: async () => schema },
        workflow: { updateDevice: async () => null }, editor,
    });
    await controller.openEdit({
        device: { id: "1", device_type: "server", has_device_password: true },
        present: () => ({ body: { querySelector: () => form } }),
        onRevealPassword: async (device, target) => { received = { device, target }; },
    });
    for (const change of listeners.get("change")) {
        change({ target: { getAttribute: () => "device_subtype" } });
    }
    const button = { disabled: false };
    for (const click of listeners.get("click")) {
        await click({ preventDefault: () => {}, target: { closest: () => button } });
    }
    assert.equal(received.device.id, "1");
    assert.equal(received.device.device_password, undefined);
    assert.equal(received.target, feedback);
});

test("changer le systeme dans la fiche d'edition rafraichit les champs sans perdre le brouillon", async () => {
    const listeners = {};
    const form = { addEventListener: (name, handler) => { listeners[name] = handler; } };
    let refreshed;
    const editor = {
        markup: () => "<form></form>",
        payload: (_form, current) => ({ name: "nom modifie", device_subtype: "linux", id_Teamviewer: current.id_Teamviewer }),
        refreshFields: (_form, current, currentSchema) => { refreshed = { current, currentSchema }; },
    };
    const controller = window.NMPDeviceEditorController.create({
        repository: { load: async () => null, loadSchema: async () => schema },
        workflow: { updateDevice: async () => null },
        editor,
    });
    await controller.openEdit({
        device: { id: "1", device_type: "server", device_subtype: "windows", id_Teamviewer: "123" },
        present: () => ({ body: { querySelector: () => form } }),
    });
    listeners.change({ target: { getAttribute: () => "device_subtype" } });
    assert.equal(refreshed.current.device_subtype, "linux");
    assert.equal(refreshed.current.name, "nom modifie");
    assert.equal(refreshed.current.id_Teamviewer, "123");
    assert.equal(refreshed.current.action_double_click, "");
    assert.equal(refreshed.currentSchema, schema);
});

test("le clic sur un cartouche lance l'action du device sans transmettre le mot de passe", async () => {
    const listeners = {};
    const form = {
        addEventListener: (name, handler) => { listeners[name] = handler; },
        querySelector: () => null,
    };
    let received;
    const editor = {
        markup: (_device, _schema, options) => {
            assert.equal(options.remoteActionsEnabled, true);
            return "<form></form>";
        },
        payload: () => ({ name: "serveur", ip: "192.168.1.20", device_subtype: "linux", ssh_user: "admin", device_password: "secret" }),
        refreshFields: () => {},
    };
    const controller = window.NMPDeviceEditorController.create({
        repository: { load: async () => null, loadSchema: async () => schema },
        workflow: { updateDevice: async () => null }, editor,
    });
    await controller.openEdit({
        device: { id: "1", device_type: "server" },
        present: () => ({ body: { querySelector: () => form } }),
        onRemoteAction: async (device, actionKey) => { received = { device, actionKey }; },
    });
    listeners.change({ target: { getAttribute: () => "device_subtype" } });
    await listeners.click({ target: { closest: () => ({ disabled: false, getAttribute: () => "ssh" }) } });
    assert.equal(received.actionKey, "ssh");
    assert.equal(received.device.ssh_user, "admin");
    assert.equal("device_password" in received.device, false);
});

test("les valeurs des plugins masques restent dans la mise a jour", () => {
    class FormDataStub {
        constructor(form) { this.values = form.values; }
        entries() { return Object.entries(this.values); }
        get(name) { return this.values[name] ?? null; }
    }
    const isolatedWindow = {};
    const source = fs.readFileSync(path.join(__dirname, "..", "web", "shared_device_editor.js"), "utf8");
    vm.runInNewContext(source, { window: isolatedWindow, FormData: FormDataStub });
    const form = {
        values: { name: "nouveau nom", ip: "192.168.1.5", device_subtype: "linux", ssh_user: "root" },
        querySelector: (selector) => selector.match(/\[name="([^"]+)"\]/)?.[1] in form.values ? {} : null,
    };
    const payload = isolatedWindow.NMPSharedDeviceEditor.payload(form, {
        id_Teamviewer: "123456",
        web_url: "https://example.test",
        action_double_click: "ssh",
        custom_data: { retained: "oui" },
    });
    assert.equal(payload.ssh_user, "root");
    assert.equal(payload.id_Teamviewer, "123456");
    assert.equal(payload.web_url, "https://example.test");
    assert.equal(payload.custom_data.retained, "oui");
});
