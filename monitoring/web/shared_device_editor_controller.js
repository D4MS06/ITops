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
            const current = loadedDevice || repository.get?.(typeCode, id);
            if (!current) {
                throw new Error("Équipement introuvable.");
            }
            const modal = present({
                title: title || `Modifier ${text(current.name || current.ip || "l’équipement")}`,
                bodyMarkup: editor.markup(current, schema, { formId, feedbackId }),
                width,
            });
            const root = modal?.body;
            const form = root?.querySelector?.(`#${formId}`);
            if (!form || typeof form.addEventListener !== "function") {
                throw new Error("Le formulaire d'équipement est indisponible.");
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
                const modal = present({
                    title,
                    bodyMarkup: editor.markup(current, schema, { formId, feedbackId, mode: "create", deviceTypes }),
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
