(function () {
    "use strict";

    function text(value) {
        return String(value ?? "").trim();
    }

    function create({ repository, workflow, editor = window.NMPSharedDeviceEditor, normalizeErrorMessage = (message) => text(message) || "Erreur inconnue." } = {}) {
        if (!repository || typeof repository.load !== "function" || typeof repository.loadSchema !== "function") {
            throw new Error("Le repository d'équipements ne respecte pas le contrat de lecture.");
        }
        if (!workflow || typeof workflow.updateDevice !== "function") {
            throw new Error("Le workflow d'équipements ne respecte pas le contrat de mise à jour.");
        }
        if (!editor || typeof editor.markup !== "function" || typeof editor.payload !== "function") {
            throw new Error("L'éditeur d'équipements ne respecte pas le contrat partagé.");
        }

        async function openEdit({
            device,
            deviceType = device?.device_type,
            deviceId = device?.id,
            loadDevice = false,
            requestOptions = {},
            present,
            title,
            formId = "shared-device-editor-form",
            feedbackId = "shared-device-editor-feedback",
            width = "min(980px, calc(100vw - 40px))",
            notificationsEnabled,
            onRemoteAction,
            onRevealPassword,
            onSaved,
        } = {}) {
            const typeCode = text(deviceType);
            const id = text(deviceId);
            if (!typeCode || !id) {
                throw new Error("Équipement introuvable.");
            }
            if (typeof present !== "function") {
                throw new Error("Le présentateur de formulaire est requis.");
            }

            const [loadedDevice, schema] = await Promise.all([
                loadDevice ? repository.load(typeCode, id, requestOptions) : Promise.resolve(device),
                repository.loadSchema(typeCode, { requestOptions }),
            ]);
            let current = loadedDevice || repository.get?.(typeCode, id);
            if (!current) {
                throw new Error("Équipement introuvable.");
            }
            const modal = present({
                title: title || `Modifier ${text(current.name || current.ip || "l’équipement")}`,
                bodyMarkup: editor.markup(current, schema, { formId, feedbackId, notificationsEnabled, remoteActionsEnabled: typeof onRemoteAction === "function", passwordRevealEnabled: typeof onRevealPassword === "function" }),
                width,
            });
            const root = modal?.body;
            const form = root?.querySelector?.(`#${formId}`);
            if (!form || typeof form.addEventListener !== "function") {
                throw new Error("Le formulaire d'équipement est indisponible.");
            }

            let credentialState = null;
            const credentialsSection = form.querySelector("[data-device-access-credentials]");
            let accessTree = null;
            let accessRows = [];
            function renderCredentials() {
                if (!credentialsSection || !credentialState) return;
                const targets = window.NMPRemoteActions?.builtinTargets(window.NMPRemoteActions?.actionsForDevice(schema, current) || []) || new Set();
                const selected = window.NMPRemoteActions?.configuredDefaultActionForDevice(schema, current);
                const defaultAccess = String(selected?.target_value || "").toLowerCase();
                const byAccess = new Map((credentialState.items || []).map((item) => [item.access, item]));
                accessRows = [...targets].filter((access) => ["web", "ssh", "remote_desktop", "teamviewer"].includes(access)).map((access) => ({ ...(byAccess.get(access) || { access, login: "", has_password: false }), active: true, isDefault: access === defaultAccess }));
                for (const item of credentialState.items || []) if (!targets.has(item.access) && (item.login || item.has_password)) accessRows.push({ ...item, active: false });
                accessRows.sort((a, b) => Number(b.access === defaultAccess) - Number(a.access === defaultAccess));
                if (accessTree) { accessTree.render(); return; }
                credentialsSection.replaceChildren();
                const heading = document.createElement("h4");
                heading.className = "inset-panel";
                heading.textContent = "Identifiants par accès";
                credentialsSection.append(heading);
                const table = document.createElement("table");
                table.className = "device-table inventory-table";
                const head = document.createElement("thead");
                const body = document.createElement("tbody");
                table.append(head, body);
                credentialsSection.append(table);
                class AccessTreeView extends window.NMPSharedUi.treeView.SharedTreeView {
                    constructor() {
                        super({ headElement: head, bodyElement: body, columnVisibility: false,
                            getRows: () => accessRows, getRowKey: (row) => row.access,
                            getColumns: () => [
                                { key: "access", label: "Accès", value: (row) => `${window.NMPRemoteActions?.actionLabel(row.access) || row.access}${row.isDefault ? " (par défaut)" : ""}${row.active ? "" : " (indisponible)"}` },
                                { key: "login", label: "Identifiant", value: (row) => row.access === "teamviewer" ? current.id_Teamviewer || "—" : row.login || "—" },
                                { key: "password", label: "Mot de passe", renderCell: (row) => row.has_password ? "•••••••• " : "—", actionIds: ["reveal"] },
                                { key: "actions", label: "Actions", actions: true, sortable: false },
                            ],
                            rowActions: [
                                { id: "reveal", icon: "reveal-password", title: "Afficher le mot de passe", columnOnly: true, visible: ([row]) => row.has_password },
                                { id: "edit", icon: "edit", title: "Modifier les identifiants", visible: ([row]) => credentialState.can_manage && row.active && row.access !== "teamviewer" },
                                { id: "copy", icon: "copy", title: "Reprendre les identifiants existants", visible: ([row]) => credentialState.can_manage && row.active && row.access !== "teamviewer" && !row.login && !row.has_password && credentialState.has_legacy_credentials },
                            ],
                            onTreeAction: ({ actionId, rows }) => handleAccessAction(actionId, rows[0]),
                        });
                    }
                }
                accessTree = new AccessTreeView();
                accessTree.render();
            }
            async function refreshCredentials() {
                credentialState = await repository.accessCredentials(typeCode, id);
                renderCredentials();
                await onSaved?.(await repository.load(typeCode, id, requestOptions), current);
            }

            async function handleAccessAction(actionId, item) {
                if (!item) return;
                const dialogs = window.NMPSharedUi.credentialDialogs;
                const feedback = form.querySelector(`#${feedbackId}`);
                try {
                    if (actionId === "reveal") {
                        const result = await dialogs.requestWithSessionPassword({
                            request: (password) => repository.revealAccessCredentials(typeCode, id, item.access, password),
                        });
                        if (result) await dialogs.showPassword(result.device_password);
                        return;
                    }
                    if (actionId === "copy") {
                        const result = await dialogs.requestWithSessionPassword({
                            request: (password) => repository.copyLegacyCredentials(typeCode, id, item.access, password),
                        });
                        if (result) await refreshCredentials();
                        return;
                    }
                    if (actionId !== "edit") return;
                    const label = window.NMPRemoteActions?.actionLabel(item.access) || item.access;
                    const ui = window.NMPSharedUi;
                    const modal = window.NMPSharedUi.shell.createChildModal({
                        title: `Identifiants ${label}`,
                        width: "min(560px, calc(100vw - 40px))",
                        bodyMarkup: `<form class="modal-form">
                            ${ui.createFieldMarkup({ key: "login", label: "Identifiant", value: item.login || "" })}
                            ${ui.createFieldMarkup({ key: "password", label: "Mot de passe", value: "", inputType: "password" })}
                            <p class="muted">Laisser le mot de passe vide pour le conserver.</p>
                            <p class="muted inventory-feedback" data-feedback></p>
                            ${ui.formControls.createModalActionsMarkup({ buttons: [{ preset: "cancel" }, { preset: "save" }] })}
                        </form>`,
                    });
                    const childForm = modal.body.querySelector("form");
                    childForm.elements.login.autocomplete = "off";
                    childForm.elements.password.autocomplete = "new-password";
                    let saving = false;
                    childForm.addEventListener("submit", async (event) => {
                        event.preventDefault();
                        if (saving) return;
                        saving = true;
                        const submit = childForm.querySelector('[type="submit"]');
                        submit.disabled = true;
                        const data = { login: childForm.elements.login.value };
                        if (childForm.elements.password.value) data.password = childForm.elements.password.value;
                        try {
                            await repository.saveAccessCredentials(typeCode, id, item.access, data);
                            modal.close("saved");
                            await refreshCredentials();
                        } catch (error) {
                            const target = childForm.isConnected ? childForm.querySelector("[data-feedback]") : feedback;
                            if (target) target.textContent = normalizeErrorMessage(error?.message);
                        } finally {
                            saving = false;
                            submit.disabled = false;
                        }
                    });
                } catch (error) {
                    if (feedback) feedback.textContent = normalizeErrorMessage(error?.message);
                }
            }
            if (credentialsSection && typeof repository.accessCredentials === "function") {
                try { credentialState = await repository.accessCredentials(typeCode, id); await renderCredentials(); }
                catch (error) { credentialsSection.textContent = normalizeErrorMessage(error?.message || "Chargement des identifiants impossible."); }
            }

            form.addEventListener("change", (event) => {
                const name = text(event?.target?.getAttribute?.("name"));
                if (name === "action_double_click") {
                    current = { ...current, ...editor.payload(form, current) };
                    renderCredentials();
                    return;
                }
                if (name !== "device_subtype") return;
                current = { ...current, ...editor.payload(form, current), action_double_click: "" };
                editor.refreshFields(form, current, schema, { passwordRevealEnabled: typeof onRevealPassword === "function" });
                renderCredentials();
            });
            if (typeof onRemoteAction === "function") {
                form.addEventListener("click", async (event) => {
                    const button = event?.target?.closest?.("[data-device-remote-action]");
                    if (!button || button.disabled) return;
                    const draft = editor.payload(form, current);
                    const safeCurrent = { ...current };
                    delete safeCurrent.device_password;
                    const remoteDevice = {
                        ...safeCurrent,
                        name: draft.name,
                        ip: draft.ip,
                        device_subtype: draft.device_subtype,
                        id_Teamviewer: draft.id_Teamviewer,
                        web_url: draft.web_url,
                        ssh_user: draft.ssh_user,
                        custom_data: draft.custom_data,
                    };
                    try {
                        await onRemoteAction(remoteDevice, button.getAttribute("data-device-remote-action"), schema);
                    } catch (error) {
                        const feedback = form.querySelector(`#${feedbackId}`);
                        if (feedback) feedback.textContent = normalizeErrorMessage(error?.message || String(error || ""));
                    }
                });
            }
            form.addEventListener("submit", async (event) => {
                event.preventDefault();
                const feedback = form.querySelector(`#${feedbackId}`);
                if (feedback) feedback.textContent = "Enregistrement...";
                try {
                    const saved = await workflow.updateDevice(typeCode, id, editor.payload(form, current));
                    await onSaved?.(saved, current);
                    modal?.close?.("saved");
                } catch (error) {
                    if (feedback) feedback.textContent = normalizeErrorMessage(error?.message || String(error || ""));
                }
            });
            return modal;
        }

        async function openCreate({
            device = {},
            deviceType = device?.device_type,
            deviceTypes = [],
            requestOptions = {},
            present,
            title = "Ajouter un équipement",
            formId = "shared-device-create-form",
            feedbackId = "shared-device-create-feedback",
            width = "min(980px, calc(100vw - 40px))",
            onSaved,
        } = {}) {
            if (typeof workflow.createDevice !== "function") {
                throw new Error("Le workflow d'équipements ne permet pas la création.");
            }
            if (typeof present !== "function") {
                throw new Error("Le présentateur de formulaire est requis.");
            }
            let current = { ...device, device_type: text(deviceType) };
            if (!current.device_type) {
                throw new Error("Type d'équipement manquant.");
            }

            async function render() {
                const schema = await repository.loadSchema(current.device_type, { requestOptions });
                const typeDefinition = (Array.isArray(deviceTypes) ? deviceTypes : [])
                    .find((item) => text(item?.code) === current.device_type);
                const notificationsEnabled = typeDefinition
                    ? Boolean(typeDefinition.monitoring_enabled)
                    : undefined;
                const modal = present({
                    title,
                    bodyMarkup: editor.markup(current, schema, { formId, feedbackId, mode: "create", deviceTypes, notificationsEnabled }),
                    width,
                });
                const form = modal?.body?.querySelector?.(`#${formId}`);
                if (!form || typeof form.addEventListener !== "function") {
                    throw new Error("Le formulaire d'équipement est indisponible.");
                }
                form.addEventListener("change", async (event) => {
                    const field = text(event?.target?.getAttribute?.("name"));
                    if (!["device_type", "device_subtype"].includes(field)) return;
                    const nextType = field === "device_type"
                        ? text(event.target.value)
                        : text(form.querySelector('[name="device_type"]')?.value || current.device_type);
                    if (!nextType) return;
                    const draft = editor.payload(form, current);
                    current = {
                        ...current,
                        ...draft,
                        device_type: nextType,
                        action_double_click: field === "device_subtype" ? "" : draft.action_double_click,
                        custom_data: field === "device_type" ? {} : draft.custom_data,
                    };
                    await render();
                });
                form.addEventListener("submit", async (event) => {
                    event.preventDefault();
                    const feedback = form.querySelector(`#${feedbackId}`);
                    if (feedback) feedback.textContent = "Enregistrement...";
                    try {
                        const saved = await workflow.createDevice({
                            ...editor.payload(form, current),
                            device_type: current.device_type,
                        });
                        await onSaved?.(saved, current);
                        modal?.close?.("saved");
                    } catch (error) {
                        if (feedback) feedback.textContent = normalizeErrorMessage(error?.message || String(error || ""));
                    }
                });
                return modal;
            }

            return render();
        }

        return Object.freeze({ openEdit, openCreate });
    }

    window.NMPDeviceEditorController = Object.freeze({ create });
}());
