(function initSharedConfigStorage(global) {
    "use strict";

    const FREQUENCIES = Object.freeze([
        { seconds: 24 * 60 * 60, label: "1 jour" },
        { seconds: 7 * 24 * 60 * 60, label: "1 semaine" },
        { seconds: 30 * 24 * 60 * 60, label: "1 mois" },
        { seconds: 365 * 24 * 60 * 60, label: "1 an" },
    ]);

    function frequencyAt(index) {
        const normalized = Math.max(0, Math.min(FREQUENCIES.length - 1, Math.trunc(Number(index) || 0)));
        return FREQUENCIES[normalized];
    }

    function frequencyIndex(intervalSeconds) {
        const requested = Number(intervalSeconds);
        if (!Number.isFinite(requested) || requested <= 0) return 1;
        return FREQUENCIES.reduce((closest, frequency, index) => (
            Math.abs(frequency.seconds - requested) < Math.abs(FREQUENCIES[closest].seconds - requested)
                ? index
                : closest
        ), 0);
    }

    function create(options = {}) {
        const requestJson = options.requestJson;
        const applySettingsPatch = options.applySettingsPatch;
        const openModal = options.openModal;
        const closeModal = options.closeModal;
        const escapeHtml = options.escapeHtml || ((value) => String(value ?? ""));
        const createActions = options.createActions;
        const onExplore = options.onExplore;
        const onStorageSaved = options.onStorageSaved;
        if (typeof requestJson !== "function" || typeof applySettingsPatch !== "function" || typeof openModal !== "function" || typeof closeModal !== "function" || typeof createActions !== "function") {
            throw new Error("Contrat de gestion du stockage de configuration incomplet.");
        }

        function actions(buttons) {
            return createActions({ buttons });
        }

        function storageModeLabel(mode) {
            return String(mode || "").trim().toLowerCase() === "smb3" ? "Redondance SMB3" : "Local serveur uniquement";
        }

        function renderState(storageState) {
            const mode = String(storageState?.mode || "local").trim().toLowerCase();
            const ok = Boolean(storageState?.can_open_backup_folder);
            const stateClass = mode === "smb3" ? (ok ? "tool-output-ok" : "tool-output-ko") : "tool-output-warning";
            const status = mode === "smb3" ? (ok ? "Accessible" : "Non accessible") : "Local actif";
            const message = String(storageState?.message || "Non teste").trim() || "Non teste";
            const localPath = String(storageState?.local_storage_path || "").trim();
            const backupPath = String(storageState?.backup_path || "").trim();
            return `
                <div data-config-storage-state class="modal-tool-output config-storage-state ${stateClass}">
                    <strong>${escapeHtml(status)}</strong>
                    <span>Mode teste: ${escapeHtml(storageModeLabel(mode))}</span>
                    <span>${escapeHtml(message)}</span>
                    ${localPath ? `<span>Stockage local serveur: ${escapeHtml(localPath)}</span>` : ""}
                    ${backupPath ? `<span>Destination sauvegarde: ${escapeHtml(backupPath)}</span>` : ""}
                    <span>Mot de passe SMB configure: ${storageState?.has_smb_password ? "Oui" : "Non"}</span>
                </div>
            `;
        }

        function field(name, label, value, type = "text", wide = false) {
            return `<label class="field${wide ? " wide" : ""}"><span>${escapeHtml(label)}</span><input name="${escapeHtml(name)}" type="${type}" value="${escapeHtml(value)}"></label>`;
        }

        function storageMarkup(settings, storageState) {
            const mode = String(settings.config_storage_mode || "local").trim().toLowerCase() === "smb3" ? "smb3" : "local";
            return `
                <form data-config-storage-form class="modal-form">
                    <div class="modal-settings-grid">
                        <label class="field"><span>Mode</span><select name="config_storage_mode"><option value="local" ${mode === "local" ? "selected" : ""}>Local serveur uniquement</option><option value="smb3" ${mode === "smb3" ? "selected" : ""}>Redondance SMB3</option></select></label>
                    </div>
                    <section data-config-storage-remote class="config-storage-remote-fields" ${mode === "smb3" ? "" : "hidden"}>
                        <div class="modal-settings-grid">
                            ${field("config_smb_unc_path", "Destination distante", settings.config_smb_unc_path || "", "text", true)}
                            ${field("config_smb_username", "Utilisateur SMB", settings.config_smb_username || "")}
                            ${field("config_smb_password", "Mot de passe SMB", "", "password")}
                        </div>
                        <p class="muted config-storage-help">Sous Linux, indiquez un chemin deja monte sur le serveur, par exemple /mnt/sauvegardes. Un chemin UNC Windows ne peut pas etre monte automatiquement par l'application.</p>
                    </section>
                    ${renderState(storageState)}
                    <p data-config-storage-feedback class="muted inventory-feedback"></p>
                    ${actions([
                        { preset: "cancel" },
                        ...(typeof onExplore === "function" ? [{ label: "Gestion fichiers de configuration", type: "button", action: "config-storage:explore" }] : []),
                        { label: "Tester", type: "button", action: "config-storage:test" },
                        { preset: "save" },
                    ])}
                </form>
            `;
        }

        function autoSyncMarkup(settings) {
            const enabled = Boolean(settings.config_auto_sync_enabled);
            const index = frequencyIndex(settings.config_auto_sync_interval_seconds);
            return `
                <form data-config-auto-sync-form class="modal-form">
                    <section class="config-auto-sync-settings">
                        <p class="muted">Planifiez la sauvegarde de tous les fichiers de configuration vers l'espace de stockage distant configure.</p>
                        <label class="check-field"><input name="config_auto_sync_enabled" type="checkbox" ${enabled ? "checked" : ""}><span>Activer la synchronisation automatique</span></label>
                        <section class="config-auto-sync-frequency${enabled ? "" : " is-disabled"}" data-config-auto-sync-frequency>
                            <div class="config-auto-sync-frequency-header"><span>Frequence de sauvegarde</span><output data-config-auto-sync-frequency-label>${escapeHtml(frequencyAt(index).label)}</output></div>
                            <input name="config_auto_sync_frequency_index" type="range" min="0" max="${FREQUENCIES.length - 1}" step="1" value="${index}" aria-label="Frequence de sauvegarde automatique" ${enabled ? "" : "disabled"}>
                            <div class="config-auto-sync-frequency-ticks" aria-hidden="true">${FREQUENCIES.map((item) => `<span>${escapeHtml(item.label)}</span>`).join("")}</div>
                        </section>
                    </section>
                    <p data-config-auto-sync-feedback class="muted inventory-feedback"></p>
                    ${actions([{ preset: "cancel" }, { preset: "save", label: "Enregistrer" }])}
                </form>
            `;
        }

        function setFeedback(form, selector, message) {
            const feedback = form.querySelector(selector);
            if (feedback) feedback.textContent = message;
        }

        function syncStorageMode(form) {
            const remote = form.querySelector("[data-config-storage-remote]");
            if (remote) remote.hidden = form.elements.config_storage_mode?.value !== "smb3";
        }

        function syncFrequency(form) {
            const enabled = Boolean(form.elements.config_auto_sync_enabled?.checked);
            const range = form.elements.config_auto_sync_frequency_index;
            if (range) range.disabled = !enabled;
            form.querySelector("[data-config-auto-sync-frequency]")?.classList.toggle("is-disabled", !enabled);
            const label = form.querySelector("[data-config-auto-sync-frequency-label]");
            if (label) label.textContent = frequencyAt(range?.value).label;
        }

        async function saveStorage(form, closeAfterSave) {
            const mode = String(form.elements.config_storage_mode?.value || "local").trim().toLowerCase();
            await applySettingsPatch({
                config_storage_mode: mode === "smb3" ? "smb3" : "local",
                switch_configs_dir: "",
                config_smb_unc_path: mode === "smb3" ? String(form.elements.config_smb_unc_path?.value || "").trim() : "",
                config_smb_username: mode === "smb3" ? String(form.elements.config_smb_username?.value || "").trim() : "",
                config_smb_password: mode === "smb3" ? String(form.elements.config_smb_password?.value || "") : "",
            }, "");
            await onStorageSaved?.();
            if (closeAfterSave) window.setTimeout(closeModal, 400);
        }

        function bindStorage(form) {
            form.addEventListener("change", (event) => {
                if (event.target?.name === "config_storage_mode") syncStorageMode(form);
            });
            form.addEventListener("click", async (event) => {
                const testButton = event.target?.closest?.('[data-action="config-storage:test"]');
                if (!testButton) return;
                event.preventDefault();
                event.stopPropagation();
                try {
                    setFeedback(form, "[data-config-storage-feedback]", "Enregistrement et test...");
                    await saveStorage(form, false);
                    const storageState = await requestJson("/config-storage/test-connection", { method: "POST" });
                    const current = form.querySelector("[data-config-storage-state]");
                    const wrapper = document.createElement("div");
                    wrapper.innerHTML = renderState(storageState).trim();
                    current?.replaceWith(wrapper.firstElementChild);
                    setFeedback(form, "[data-config-storage-feedback]", storageState?.can_open_backup_folder ? `Test OK (${storageModeLabel(storageState?.mode)}). ${storageState?.message || ""}` : `Test KO (${storageModeLabel(storageState?.mode)}). ${storageState?.message || ""}`);
                } catch (error) {
                    setFeedback(form, "[data-config-storage-feedback]", `Test impossible: ${error?.message || String(error)}`);
                }
            });
            form.addEventListener("submit", async (event) => {
                event.preventDefault();
                event.stopPropagation();
                try {
                    await saveStorage(form, true);
                } catch (error) {
                    setFeedback(form, "[data-config-storage-feedback]", error?.message || String(error));
                }
            });
        }

        function bindAutoSync(form) {
            form.addEventListener("input", (event) => {
                if (event.target?.name === "config_auto_sync_frequency_index") syncFrequency(form);
            });
            form.addEventListener("change", (event) => {
                if (event.target?.name === "config_auto_sync_enabled") syncFrequency(form);
            });
            form.addEventListener("submit", async (event) => {
                event.preventDefault();
                event.stopPropagation();
                try {
                    await applySettingsPatch({
                        config_auto_sync_enabled: Boolean(form.elements.config_auto_sync_enabled?.checked),
                        config_auto_sync_interval_seconds: frequencyAt(form.elements.config_auto_sync_frequency_index?.value).seconds,
                    }, "");
                    window.setTimeout(closeModal, 400);
                } catch (error) {
                    setFeedback(form, "[data-config-auto-sync-feedback]", error?.message || String(error));
                }
            });
        }

        return {
            async openStorage() {
                const [settings, storageState] = await Promise.all([requestJson("/settings"), requestJson("/config-storage/state")]);
                const modal = openModal("Configurer sauvegarde", storageMarkup(settings, storageState), { width: "min(920px, calc(100vw - 40px))" });
                const root = modal?.body instanceof HTMLElement ? modal.body : document;
                const form = root.querySelector("[data-config-storage-form]");
                if (form instanceof HTMLFormElement) bindStorage(form);
            },
            async openAutoSync() {
                const settings = await requestJson("/settings");
                const modal = openModal("Synchronisation automatique", autoSyncMarkup(settings), { width: "min(640px, calc(100vw - 40px))" });
                const root = modal?.body instanceof HTMLElement ? modal.body : document;
                const form = root.querySelector("[data-config-auto-sync-form]");
                if (form instanceof HTMLFormElement) bindAutoSync(form);
            },
        };
    }

    global.NMPConfigStorage = Object.freeze({ create, FREQUENCIES });
}(window));
