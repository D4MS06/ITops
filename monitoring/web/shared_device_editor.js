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
        const defaultAction = text(current.action_double_click) || text(window.NMPRemoteActions?.defaultActionForDevice(schema, current));
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
        if (keys.has("id_teamviewer") || remoteActions.some((item) => item.target_value === "teamviewer")) fields.push(field({ key: "id_Teamviewer", label: "ID TeamViewer", value: current.id_Teamviewer }));
        if (keys.has("web_url")) fields.push(field({ key: "web_url", label: "Adresse web", value: current.web_url, kind: "url" }));
        if (text(current.device_type).trim().toLowerCase() === "switch") fields.push(field({ key: "custom:web_direct_no_proxy", label: "Acces web direct (sans proxy)", value: current.custom_data?.web_direct_no_proxy, kind: "checkbox", wide: true }));
        if (keys.has("ssh_user")) fields.push(field({ key: "ssh_user", label: "Utilisateur SSH", value: current.ssh_user }));
        if (keys.has("device_login")) fields.push(field({ key: "device_login", label: "Identifiant", value: current.device_login }));
        if (keys.has("device_password")) fields.push(field({ key: "device_password", label: "Mot de passe", value: "", kind: "password", placeholder: "Laisser vide pour conserver le mot de passe" }));
        customFields.forEach((definition) => {
            const key = text(definition?.field_key).trim();
            if (!key) return;
            const kind = text(definition?.field_kind || "text").trim().toLowerCase();
            const choices = text(definition?.options).split(",").map((value) => value.trim()).filter(Boolean);
            fields.push(field({ key: `custom:${key}`, label: text(definition?.label) || key, value: current.custom_data?.[key] ?? definition?.default_value ?? "", kind: kind === "choice" && choices.length ? "choice" : (kind === "textarea" ? "textarea" : "text"), choices, wide: kind === "textarea" }));
        });
        return `<div class="modal-grid" data-shared-device-fields="true">${fields.join("")}</div>`;
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
        return `<form id="${escapeHtml(formId)}" class="modal-form" data-shared-device-editor="true">${fieldsMarkup(current, schema, options)}${notifyMarkup}<p id="${escapeHtml(feedbackId)}" class="muted inventory-feedback"></p><div class="modal-actions"><button class="toolbar-btn" type="button" data-action="modal:close">Annuler</button><button class="primary-btn" type="submit">${escapeHtml(submitLabel)}</button></div></form>`;
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

    window.NMPSharedDeviceEditor = Object.freeze({ fieldsMarkup, markup, payload });
}());
