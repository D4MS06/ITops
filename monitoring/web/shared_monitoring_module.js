(function () {
    "use strict";

    function escapeHtml(value) {
        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function statusLabel(value) {
        return ({ online: "En ligne", offline: "Hors ligne", idle: "Inactif" })[String(value || "").toLowerCase()] || "Inactif";
    }

    function statusClass(value) {
        const normalized = String(value || "idle").toLowerCase();
        if (normalized === "online") return "status-online";
        if (normalized === "offline") return "status-offline";
        return "status-idle";
    }

    function monitoringStatus(snapshot) {
        const types = (Array.isArray(snapshot?.types) ? snapshot.types : [])
            .filter((item) => Boolean(item?.monitoring_enabled))
            .map((item) => ({
                typeCode: String(item?.type_code || "").trim(),
                label: String(item?.label || item?.type_code || "Type").trim(),
                running: Boolean(item?.running),
                total: Number(item?.total || 0),
                online: Number(item?.online || 0),
                offline: Number(item?.offline || 0),
            }));
        const summary = snapshot?.summary || {};
        return {
            runningAny: Boolean(summary.running_any),
            runningAll: Boolean(summary.running_all),
            total: types.reduce((count, item) => count + item.total, 0),
            online: types.reduce((count, item) => count + item.online, 0),
            offline: types.reduce((count, item) => count + item.offline, 0),
            types,
        };
    }

    function traceMarkup(state) {
        const normalized = ["running", "partial", "stopped"].includes(state) ? state : "stopped";
        const path = normalized === "stopped"
            ? "M4 32 L156 32"
            : "M4 34 L28 34 L38 9 L52 55 L66 34 L94 34 L106 17 L120 34 L156 34";
        return `<span class="monitor-trace monitor-trace-small is-${normalized}" aria-hidden="true"><svg class="monitor-trace-svg" viewBox="0 0 160 64" preserveAspectRatio="none"><path class="monitor-trace-base" d="${path}" pathLength="100"></path><path class="monitor-trace-draw" d="${path}" pathLength="100"></path></svg></span>`;
    }

    function create(options = {}) {
        const root = options.root instanceof HTMLElement ? options.root : null;
        const statusTarget = options.statusTarget instanceof HTMLElement ? options.statusTarget : null;
        const requestJson = typeof options.requestJson === "function" ? options.requestJson : null;
        const onLoadingChange = typeof options.onLoadingChange === "function" ? options.onLoadingChange : () => {};
        const onAction = typeof options.onAction === "function" ? options.onAction : () => {};
        const createTypeControlMarkup = window.NMPSharedUi?.monitoringControls?.createTypeControlMarkup;
        const initialContext = options.initialContext && typeof options.initialContext === "object" ? options.initialContext : {};
        const state = {
            snapshot: null,
            filter: String(initialContext.filter || "global"),
            status: String(initialContext.status || ""),
            query: String(initialContext.query || ""),
            logs: null,
            refreshTimer: null,
            destroyed: false,
        };

        function filteredRows() {
            const rows = Object.entries(state.snapshot?.devices || {}).flatMap(([typeCode, devices]) => (
                (Array.isArray(devices) ? devices : []).map((item) => ({ ...item, device_type: item?.device_type || typeCode }))
            ));
            const typeCode = state.filter;
            const requestedStatus = state.status;
            const query = state.query.toLowerCase();
            return rows.filter((item) => {
                const itemType = String(item?.device_type || "").trim().toLowerCase();
                const itemStatus = String(item?.status || "idle").trim().toLowerCase();
                const searchable = [itemType, item?.name, item?.ip, item?.device_login, item?.description, itemStatus].join(" ").toLowerCase();
                return (typeCode === "global" || itemType === typeCode)
                    && (!requestedStatus || itemStatus === requestedStatus)
                    && (!query || searchable.includes(query));
            });
        }

        function renderStatus() {
            if (!statusTarget || !state.snapshot) return;
            const status = monitoringStatus(state.snapshot);
            const visualState = status.runningAll ? "running" : (status.runningAny ? "partial" : "stopped");
            const label = status.runningAll ? "Actif" : (status.runningAny ? "Partiel" : "Arrêté");
            let strip = statusTarget.querySelector("#portal-monitoring-status-strip");
            if (!(strip instanceof HTMLElement)) {
                strip = document.createElement("section");
                strip.id = "portal-monitoring-status-strip";
                strip.className = "monitoring-status-strip portal-monitoring-status-strip";
                statusTarget.querySelector("h2")?.insertAdjacentElement("afterend", strip);
            }
            strip.innerHTML = `
                <button class="monitoring-summary-toggle is-${visualState}" type="button" data-monitoring-action="toggle-global">
                    <span class="monitoring-status-visual">${traceMarkup(visualState)}</span>
                    <span class="monitoring-summary-copy"><strong>Monitoring ${label}</strong><small>${status.online} en ligne / ${status.offline} hors ligne / ${status.total} appareils</small></span>
                </button>
                <div class="monitoring-type-controls" role="group" aria-label="Monitoring par type d'équipement">
                    ${typeof createTypeControlMarkup === "function" ? status.types.map((item) => createTypeControlMarkup(item)).join("") : ""}
                </div>`;
            strip.querySelector('[data-monitoring-action="toggle-global"]')?.addEventListener("click", () => {
                command(status.runningAny ? "/monitoring/stop-all" : "/monitoring/start-all");
            });
            strip.querySelectorAll("[data-monitoring-type-action]").forEach((button) => {
                button.addEventListener("click", () => {
                    const typeCode = String(button.dataset.monitoringTypeCode || "").trim().toLowerCase();
                    if (!typeCode) return;
                    if (button.dataset.monitoringTypeAction === "filter") {
                        state.filter = typeCode;
                        state.status = "";
                        render();
                        return;
                    }
                    const type = status.types.find((item) => item.typeCode === typeCode);
                    command(`/monitoring/${type?.running ? "stop" : "start"}/${encodeURIComponent(typeCode)}`);
                });
            });
        }

        function render() {
            if (!root || !state.snapshot) return;
            if (Array.isArray(state.logs)) {
                root.innerHTML = `<section class="monitoring-native-module"><div class="detail-head monitoring-native-head"><div><p class="panel-kicker">Historique</p><h3>Journaux du monitoring</h3></div><button class="toolbar-btn compact" type="button" data-monitoring-action="back">Retour au monitoring</button></div><div class="modal-log-list">${state.logs.length ? state.logs.map((row) => `<article class="log-item ${escapeHtml(String(row?.new_status || "").toLowerCase())}"><div class="log-item-head"><strong>${escapeHtml(String(row?.event_kind || "Événement"))}</strong><span class="log-item-meta">${escapeHtml(String(row?.created_at || ""))}</span></div><div class="log-item-body"><strong>${escapeHtml(String(row?.device_name || ""))}</strong> (${escapeHtml(String(row?.dtype || ""))})<br>${escapeHtml(String(row?.old_status || "-"))} → ${escapeHtml(String(row?.new_status || "-"))}${row?.details ? `<br>${escapeHtml(String(row.details))}` : ""}</div></article>`).join("") : '<p class="muted">Aucun événement.</p>'}</div></section>`;
                root.querySelector('[data-monitoring-action="back"]')?.addEventListener("click", () => { state.logs = null; render(); });
                return;
            }
            const status = monitoringStatus(state.snapshot);
            const availableTypes = status.types;
            if (state.filter !== "global" && !availableTypes.some((item) => item.typeCode.toLowerCase() === state.filter)) {
                state.filter = "global";
            }
            const rows = filteredRows();
            const selectedType = availableTypes.find((item) => item.typeCode.toLowerCase() === state.filter);
            const title = selectedType ? `Inventaire ${selectedType.label}` : "Inventaire du monitoring";
            root.innerHTML = `
                <section class="monitoring-native-module" aria-label="Monitoring réseau">
                    <div class="detail-head monitoring-native-head"><div><p class="panel-kicker">Vue détaillée</p><h3>${escapeHtml(title)}</h3></div><button class="toolbar-btn compact" type="button" data-monitoring-action="refresh">Rafraîchir</button></div>
                    <article class="panel inset-panel monitoring-native-inventory">
                        <section class="content-filter-section monitoring-tree-filter-section"><div class="content-filter-grid monitoring-tree-controls">
                            <label class="field inline-field compact-field"><span>Type</span><select data-monitoring-filter="type"><option value="global">Tous les types monitorés</option>${availableTypes.map((item) => `<option value="${escapeHtml(item.typeCode.toLowerCase())}" ${state.filter === item.typeCode.toLowerCase() ? "selected" : ""}>${escapeHtml(item.label)}</option>`).join("")}</select></label>
                            <label class="field inline-field compact-field"><span>État</span><select data-monitoring-filter="status"><option value="">Afficher tout</option><option value="online" ${state.status === "online" ? "selected" : ""}>En ligne</option><option value="offline" ${state.status === "offline" ? "selected" : ""}>Hors ligne</option></select></label>
                            <label class="field inline-field"><span>Filtre</span><input data-monitoring-filter="query" type="search" value="${escapeHtml(state.query)}" placeholder="Nom, IP, type, statut"></label>
                            <div class="monitoring-native-actions" aria-label="Outils du monitoring">
                                <button class="toolbar-btn compact" type="button" data-monitoring-native-action="engine">Moteur</button>
                                <button class="toolbar-btn compact" type="button" data-monitoring-native-action="logs">Journaux</button>
                                <button class="toolbar-btn compact" type="button" data-monitoring-native-action="notifications">Notifications</button>
                                <button class="toolbar-btn compact" type="button" data-monitoring-native-action="storage">Fichiers de configuration</button>
                                <button class="toolbar-btn compact" type="button" data-monitoring-native-action="types">Types</button>
                            </div>
                        </div></section>
                        <div class="table-wrap"><table class="device-table"><thead><tr><th>Type</th><th>Nom</th><th>IP</th><th>Statut</th><th>Description</th></tr></thead><tbody>${rows.map((item) => `<tr><td>${escapeHtml(item.device_type || "")}</td><td>${escapeHtml(item.name || "")}</td><td>${escapeHtml(item.ip || "")}</td><td><span class="status-badge ${statusClass(item.status)}">${escapeHtml(statusLabel(item.status))}</span></td><td>${escapeHtml(item.description || "")}</td></tr>`).join("") || '<tr><td colspan="5" class="muted">Aucun équipement ne correspond aux filtres.</td></tr>'}</tbody></table></div>
                    </article>
                </section>`;
            root.querySelector('[data-monitoring-action="refresh"]')?.addEventListener("click", () => refresh({ loading: true }));
            root.querySelector('[data-monitoring-filter="type"]')?.addEventListener("change", (event) => { state.filter = String(event.target.value || "global"); render(); });
            root.querySelector('[data-monitoring-filter="status"]')?.addEventListener("change", (event) => { state.status = String(event.target.value || ""); render(); });
            root.querySelector('[data-monitoring-filter="query"]')?.addEventListener("input", (event) => { state.query = String(event.target.value || ""); render(); });
            root.querySelectorAll("[data-monitoring-native-action]").forEach((button) => {
                button.addEventListener("click", async () => {
                    const result = await onAction(String(button.dataset.monitoringNativeAction || ""));
                    if (result?.view === "logs") {
                        state.logs = Array.isArray(result.rows) ? result.rows : [];
                        render();
                    }
                });
            });
            renderStatus();
        }

        async function refresh({ loading = false } = {}) {
            if (state.destroyed || !requestJson) return;
            if (loading) onLoadingChange(true);
            try {
                state.snapshot = await requestJson("/monitoring/snapshot", { showGlobalLoading: false });
                render();
            } finally {
                if (loading) onLoadingChange(false);
            }
        }

        async function command(path) {
            if (!requestJson || state.destroyed) return;
            onLoadingChange(true);
            try {
                await requestJson(path, { method: "POST", showGlobalLoading: false });
                await refresh();
            } finally {
                onLoadingChange(false);
            }
        }

        return {
            async mount() {
                await refresh({ loading: true });
                state.refreshTimer = window.setInterval(() => refresh(), 15000);
            },
            refresh: () => refresh({ loading: true }),
            getContext() {
                return {
                    filter: state.filter,
                    status: state.status,
                    query: state.query,
                };
            },
            destroy() {
                state.destroyed = true;
                if (state.refreshTimer) window.clearInterval(state.refreshTimer);
                statusTarget?.querySelector("#portal-monitoring-status-strip")?.remove();
            },
        };
    }

    window.NMPMonitoringModule = Object.freeze({ create, monitoringStatus });
}());
