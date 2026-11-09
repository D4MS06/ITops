(function () {
    "use strict";

    const RESERVED_FIELDS = new Set(["name", "ip", "description", "notify", "config_saved", "type", "device_subtype", "id_teamviewer", "action_double_click", "action_default_by_os", "web_url", "ssh_user", "device_login", "device_password", "web_direct_no_proxy"]);

    function text(value) { return String(value ?? ""); }
    function escapeHtml(value) { return text(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;"); }
    function field({ key, label, value = "", kind = "text", choices = [], wide = false, placeholder = "" }) {
        const className = `field ${wide ? "wide" : ""}`;
        if (kind === "choice") return `<label class="${className}"><span>${escapeHtml(label)}</span><select name="${escapeHtml(key)}">${choices.map((choice) => `<option value="${escapeHtml(choice.value ?? choice)}" ${text(choice.value ?? choice) === text(value) ? "selected" : ""}>${escapeHtml(choice.label ?? choice)}</option>`).join("")}</select></label>`;
        if (kind === "checkbox") return `<label class="check-field ${wide ? "wide" : ""}"><input name="${escapeHtml(key)}" type="hidden" value="false"><input name="${escapeHtml(key)}" type="checkbox" value="true" ${["1", "true", "yes", "oui", "on"].includes(text(value).trim().toLowerCase()) ? "checked" : ""}><span>${escapeHtml(label)}</span></label>`;
        if (kind === "textarea") return `<label class="${className}"><span>${escapeHtml(label)}</span><textarea name="${escapeHtml(key)}" placeholder="${escapeHtml(placeholder)}">${escapeHtml(value)}</textarea></label>`;
        return `<label class="${className}"><span>${escapeHtml(label)}</span><input name="${escapeHtml(key)}" type="${kind === "url" ? "url" : (kind === "password" ? "password" : "text")}" value="${escapeHtml(value)}" placeholder="${escapeHtml(placeholder)}"></label>`;
    }

    function schemaFieldKeys(schema) {
        return new Set((Array.isArray(schema?.fields) ? schema.fields : []).map((item) => text(item?.field_key).trim().toLowerCase()));
    }

    function actions(schema, device) {
        return window.NMPRemoteActions?.actionsForDevice(schema, device) || [];
    }

    function fieldsMarkup(device, schema, options = {}) {
        const current = device || {};
        const keys = schemaFieldKeys(schema);
        const remoteActions = actions(schema, current);
        const builtinTargets = window.NMPRemoteActions?.builtinTargets(remoteActions) || new Set();
        const defaultAction = text(window.NMPRemoteActions?.configuredDefaultActionForDevice(schema, current)?.action_key);
        const customFields = (Array.isArray(schema?.fields) ? schema.fields : []).filter((item) => !RESERVED_FIELDS.has(text(item?.field_key).trim().toLowerCase()));
        const fields = [];
        if (text(options.mode).trim().toLowerCase() === "create") {
            const types = Array.isArray(options.deviceTypes) ? options.deviceTypes : [];
            fields.push(field({
                key: "device_type",
                label: "Type",
                value: current.device_type,
                kind: "choice",
                choices: types.map((item) => ({ value: item?.code, label: item?.label || item?.code })),
                wide: true,
            }));
        }
        fields.push(
            field({ key: "name", label: "Nom", value: current.name }),
            field({ key: "ip", label: "IP", value: current.ip }),
            field({ key: "description", label: "Description", value: current.description, kind: "textarea", wide: true }),
        );
        if (keys.has("type") || keys.has("device_subtype")) {
            const definition = (schema?.fields || []).find((item) => ["type", "device_subtype"].includes(text(item?.field_key).trim().toLowerCase()));
            const choices = text(definition?.options).split(",").map((value) => value.trim()).filter(Boolean);
            fields.push(field({ key: "device_subtype", label: text(definition?.label) || "Type / système", value: current.device_subtype, kind: choices.length ? "choice" : "text", choices }));
        }
        if (remoteActions.length) fields.push(field({ key: "action_double_click", label: "Action par défaut", value: defaultAction, kind: "choice", choices: remoteActions.map((item) => ({ value: item.action_key, label: item.label || window.NMPRemoteActions?.actionLabel(item.action_key) || item.action_key })) }));
        if (builtinTargets.has("teamviewer")) fields.push(field({ key: "id_Teamviewer", label: "ID TeamViewer", value: current.id_Teamviewer }));
        if (builtinTargets.has("web")) fields.push(field({ key: "web_url", label: "Adresse web", value: current.web_url, kind: "url" }));
        if (builtinTargets.has("web") && text(current.device_type).trim().toLowerCase() === "switch") fields.push(field({ key: "custom:web_direct_no_proxy", label: "Acces web direct (sans proxy)", value: current.custom_data?.web_direct_no_proxy, kind: "checkbox", wide: true }));
        if (builtinTargets.has("ssh")) fields.push(field({ key: "ssh_user", label: "Utilisateur SSH", value: current.ssh_user }));
        if (keys.has("device_login")) fields.push(field({ key: "device_login", label: "Identifiant", value: current.device_login }));
        if (keys.has("device_password")) {
            const hasPassword = Boolean(current.has_device_password || text(current.device_password_masked).trim());
            const passwordInput = `<input name="device_password" type="password" value="" autocomplete="new-password" placeholder="Laisser vide pour conserver le mot de passe">`;
            const revealButton = options.passwordRevealEnabled && text(options.mode).trim().toLowerCase() !== "create" && hasPassword
                ? `<button class="inventory-action-btn" type="button" data-device-password-reveal="true" title="Afficher le mot de passe stocké" aria-label="Afficher le mot de passe stocké"><span class="ui-action-btn-icon ui-action-btn-icon-reveal-password" aria-hidden="true">&#128065;</span></button>`
                : "";
            fields.push(`<div class="field"><span>Mot de passe</span><span class="device-password-edit-control">${passwordInput}${revealButton}</span><span class="device-password-edit-status">${hasPassword ? "Un mot de passe est enregistré." : "Aucun mot de passe enregistré."}</span></div>`);
        }
        customFields.forEach((definition) => {
            const key = text(definition?.field_key).trim();
            if (!key) return;
            const kind = text(definition?.field_kind || "text").trim().toLowerCase();
            const choices = text(definition?.options).split(",").map((value) => value.trim()).filter(Boolean);
            fields.push(field({ key: `custom:${key}`, label: text(definition?.label) || key, value: current.custom_data?.[key] ?? definition?.default_value ?? "", kind: kind === "choice" && choices.length ? "choice" : (kind === "textarea" ? "textarea" : "text"), choices, wide: kind === "textarea" }));
        });
        return `<div class="modal-grid" data-shared-device-fields="true">${fields.join("")}</div>`;
    }

    function remotePluginButtonsMarkup(device, schema) {
        const remote = window.NMPRemoteActions;
        const actions = remote?.pluginActionsForDevice(schema, device) || [];
        return actions.map((action) => {
            const builtin = action.target_value;
            const plugin = remote.pluginDefinitions.find((item) => item.key === builtin);
            const status = remote.webStatus(device, action);
            const available = builtin === "ssh"
                ? Boolean(remote.builtinActionUrl(device, "ssh"))
                : status.ok;
            const label = text(action.label || plugin?.title || remote.actionLabel(builtin)).trim();
            const title = available ? `Se connecter avec ${label}`
                : (builtin === "ssh" ? "Adresse IP manquante pour ouvrir SSH." : status.message);
            return `<button class="type-schema-action-tile device-remote-plugin" type="button"
                data-device-remote-action="${escapeHtml(action.action_key)}"
                title="${escapeHtml(title)}" aria-label="${escapeHtml(title)}" ${available ? "" : "disabled"}>
                <span class="type-schema-action-badge">${escapeHtml(plugin?.badge || builtin.toUpperCase())}</span>
                <span class="type-schema-action-label">${escapeHtml(label)}</span>
            </button>`;
        }).join("");
    }

    function sshLaunchMarkup(device) {
        const url = window.NMPRemoteActions?.builtinActionUrl(device, "ssh") || "";
        if (!url) return "";
        const host = text(device?.ip).trim();
        const user = text(device?.ssh_user).trim();
        const commandUser = /^[a-z0-9_.-]+$/i.test(user) ? user : "";
        const command = `ssh ${commandUser ? `${commandUser}@` : ""}${host}`;
        return `<section class="modal-section">
            <p>Connexion SSH a <strong>${escapeHtml(device?.name || host)}</strong>.</p>
            <p class="muted">Ouvre le client SSH installe sur ce poste, ou utilise cette commande dans un terminal :</p>
            <p><code>${escapeHtml(command)}</code></p>
        </section>
        <div class="modal-actions">
            <a class="primary-btn" href="${escapeHtml(url)}">Ouvrir le client SSH</a>
            <button class="toolbar-btn" type="button" data-action="modal:close">Fermer</button>
        </div>`;
    }

    function markup(device, schema, options = {}) {
        const current = device || {};
        const formId = text(options.formId || "shared-device-editor-form");
        const feedbackId = text(options.feedbackId || "shared-device-editor-feedback");
        const submitLabel = text(options.submitLabel || (text(options.mode).trim().toLowerCase() === "create" ? "Ajouter" : "Enregistrer"));
        const schemaSupportsNotifications = (Array.isArray(schema?.fields) ? schema.fields : [])
            .some((item) => text(item?.field_key).toLowerCase() === "notify");
        const notificationsEnabled = options.notificationsEnabled === undefined
            ? schemaSupportsNotifications
            : Boolean(options.notificationsEnabled);
        const notifyMarkup = notificationsEnabled
            ? `<label class="check-field"><input name="notify" type="checkbox" ${current.notify ? "checked" : ""}><span>Alertes changement actives</span></label>`
            : "";
        const pluginButtons = options.remoteActionsEnabled ? remotePluginButtonsMarkup(current, schema) : "";
        const pluginMarkup = options.remoteActionsEnabled
            ? `<section class="inventory-subsection" data-device-remote-plugins="true" ${pluginButtons ? "" : "hidden"}><h4>Prise en main a distance</h4><div class="type-schema-plugin-catalog" data-device-remote-plugin-list="true">${pluginButtons}</div></section>`
            : "";
        return `<form id="${escapeHtml(formId)}" class="modal-form" data-shared-device-editor="true">${pluginMarkup}${fieldsMarkup(current, schema, options)}${notifyMarkup}<p id="${escapeHtml(feedbackId)}" class="muted inventory-feedback"></p><div class="modal-actions"><button class="toolbar-btn" type="button" data-action="modal:close">Annuler</button><button class="primary-btn" type="submit">${escapeHtml(submitLabel)}</button></div></form>`;
    }

    function refreshFields(form, current, schema, options = {}) {
        const container = form.querySelector('[data-shared-device-fields="true"]');
        if (!container) return;
        const password = form.querySelector('[name="device_password"]')?.value || "";
        container.outerHTML = fieldsMarkup(current, schema, options);
        const passwordField = form.querySelector('[name="device_password"]');
        if (passwordField) passwordField.value = password;
        const pluginList = form.querySelector('[data-device-remote-plugin-list="true"]');
        if (pluginList) {
            pluginList.innerHTML = remotePluginButtonsMarkup(current, schema);
            pluginList.closest('[data-device-remote-plugins="true"]').hidden = !pluginList.innerHTML;
        }
    }

    function payload(form, current) {
        const formData = new FormData(form);
        const customData = { ...(current?.custom_data || {}) };
        for (const [key, value] of formData.entries()) if (text(key).startsWith("custom:")) customData[text(key).slice(7)] = text(value);
        const valueFor = (name, fallback = "") => form.querySelector(`[name="${name}"]`)
            ? text(formData.get(name)).trim()
            : text(current?.[name] ?? fallback).trim();
        const result = {
            name: valueFor("name"), ip: valueFor("ip"), description: valueFor("description"),
            id_Teamviewer: valueFor("id_Teamviewer"), device_subtype: valueFor("device_subtype", current?.type), action_double_click: valueFor("action_double_click"),
            web_url: valueFor("web_url"), ssh_user: valueFor("ssh_user"), device_login: valueFor("device_login"),
            custom_data: customData, notify: form.querySelector('[name="notify"]')?.checked ?? Boolean(current?.notify ?? true), version_token: text(current?.version_token),
        };
        if (form.querySelector('[name="device_password"]')) {
            const password = text(formData.get("device_password"));
            if (password) result.device_password = password;
        }
        return result;
    }

    window.NMPSharedDeviceEditor = Object.freeze({ fieldsMarkup, remotePluginButtonsMarkup, sshLaunchMarkup, markup, refreshFields, payload });
}());
