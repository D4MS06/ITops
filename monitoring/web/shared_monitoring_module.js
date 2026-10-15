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
        const loadTypeSchema = typeof options.loadTypeSchema === "function" ? options.loadTypeSchema : null;
        const SharedTreeView = window.NMPSharedUi?.treeView?.SharedTreeView;
        const onLoadingChange = typeof options.onLoadingChange === "function" ? options.onLoadingChange : () => {};
        const onAction = typeof options.onAction === "function" ? options.onAction : () => {};
        const onSnapshot = typeof options.onSnapshot === "function" ? options.onSnapshot : () => {};
        const onDeviceContext = typeof options.onDeviceContext === "function" ? options.onDeviceContext : () => {};
        const onDeviceDoubleClick = typeof options.onDeviceDoubleClick === "function" ? options.onDeviceDoubleClick : () => {};
        const websocketToken = String(options.websocketToken || "").trim();
        const createTypeControlMarkup = window.NMPSharedUi?.monitoringControls?.createTypeControlMarkup;
        const initialContext = options.initialContext && typeof options.initialContext === "object" ? options.initialContext : {};
        const state = {
            snapshot: null,
            filter: String(initialContext.filter || "global"),
            status: String(initialContext.status || ""),
            query: String(initialContext.query || ""),
            logs: null,
            toolsOpen: false,
            configMenuOpen: false,
            configStorageConfigured: Boolean(options.configStorageConfigured),
            refreshTimer: null,
            websocket: null,
            destroyed: false,
            typeSchemas: new Map(),
            loadedColumnContexts: new Set(),
            tree: null,
            snapshotFingerprint: "",
        };

        function monitoringSnapshotFingerprint(snapshot) {
            const types = (Array.isArray(snapshot?.types) ? snapshot.types : []).map((item) => [
                item?.type_code, item?.monitoring_enabled, item?.config_backups_enabled, item?.running, item?.total, item?.online, item?.offline,
            ]);
            const devices = Object.entries(snapshot?.devices || {}).flatMap(([typeCode, items]) => (
                (Array.isArray(items) ? items : []).map((item) => [
                    typeCode, item?.id, item?.name, item?.ip, item?.status, item?.description,
                    item?.device_login, item?.custom_data || {},
                ])
            ));
            return JSON.stringify({ types, devices });
        }

        const columnContext = () => state.filter === "global" ? "global" : `type:${state.filter}`;
        const schemaFields = () => {
            const schema = state.typeSchemas.get(state.filter);
            return Array.isArray(schema?.fields) ? schema.fields.filter((field) => {
                const key = String(field?.field_key || "").trim();
                return key && Boolean(field?.show_in_table) && !["name", "ip", "description", "notify", "config_saved", "device_login", "device_password"].includes(key);
            }) : [];
        };
        const treeColumns = () => {
            const columns = [];
            if (state.filter === "global") columns.push({ key: "type", label: "Type", renderCell: (row) => escapeHtml(String(row.device_type || "")) });
            columns.push(
                { key: "name", label: "Nom" },
                { key: "ip", label: "IP" },
                { key: "status", label: "Statut", renderCell: (row) => `<span class="status-badge ${statusClass(row.status)}">${escapeHtml(statusLabel(row.status))}</span>` },
                { key: "description", label: "Description" },
            );
            if (state.filter !== "global") {
                schemaFields().forEach((field) => {
                    const key = String(field.field_key || "").trim();
                    columns.push({
                        key: `custom:${key}`,
                        label: String(field.label || key),
                        renderCell: (row) => escapeHtml(String(row.custom_data?.[key] || "")),
                    });
                });
            }
            return columns;
        };
        async function ensureSelectedTypeSchema() {
            const typeCode = state.filter;
            if (!loadTypeSchema || typeCode === "global" || state.typeSchemas.has(typeCode)) return;
            try {
                state.typeSchemas.set(typeCode, await loadTypeSchema(typeCode));
                if (!state.destroyed) render();
            } catch (_) {
                state.typeSchemas.set(typeCode, {});
            }
        }

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

        function configBackupsEnabledForType(typeCode) {
            const normalized = String(typeCode || "").trim().toLowerCase();
            const type = (Array.isArray(state.snapshot?.types) ? state.snapshot.types : [])
                .find((item) => String(item?.type_code || "").trim().toLowerCase() === normalized);
            return Boolean(type?.config_backups_enabled);
        }

        function applyTreeFilters({ typeCode = state.filter, status = state.status, query = state.query } = {}) {
            state.filter = String(typeCode || "global").trim().toLowerCase() || "global";
            state.status = ["online", "offline"].includes(String(status || "").trim().toLowerCase())
                ? String(status).trim().toLowerCase()
                : "";
            state.query = String(query || "");
            render();
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
                        applyTreeFilters({ typeCode, status: "" });
                        return;
                    }
                    if (button.dataset.monitoringTypeAction === "status-filter") {
                        applyTreeFilters({ typeCode, status: button.dataset.monitoringStatus, query: "" });
                        return;
                    }
                    const type = status.types.find((item) => String(item.typeCode || "").toLowerCase() === typeCode);
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
                                <div class="monitoring-native-tools-menu"><button class="toolbar-btn compact" type="button" data-monitoring-action="tools">Outils</button><div class="monitoring-native-tools-popover" data-monitoring-popover="tools" ${state.toolsOpen ? "" : "hidden"}><button type="button" data-monitoring-native-action="network-tool:scan">Scan réseau</button><button type="button" data-monitoring-native-action="network-tool:ping">Ping</button><button type="button" data-monitoring-native-action="network-tool:port">Port check</button><button type="button" data-monitoring-native-action="network-tool:traceroute">Traceroute</button><button type="button" data-monitoring-native-action="network-tool:dns">DNS lookup</button><button type="button" data-monitoring-native-action="network-tool:http">HTTP(S) check</button><button type="button" data-monitoring-native-action="network-tool:snmp">SNMP</button></div></div>
                                <button class="toolbar-btn compact" type="button" data-monitoring-native-action="logs">Journaux</button>
                                <button class="toolbar-btn compact" type="button" data-monitoring-native-action="notifications">Notifications</button>
                                <div class="monitoring-native-tools-menu"><button class="toolbar-btn compact" type="button" data-monitoring-action="config-menu">Gestion des configurations</button><div class="monitoring-native-tools-popover" data-monitoring-popover="config" ${state.configMenuOpen ? "" : "hidden"}><button type="button" data-monitoring-native-action="config:manage">Espace de stockage distant</button><button type="button" data-monitoring-native-action="storage:sync" ${state.configStorageConfigured ? "" : "disabled"}>Sauvegarder maintenant</button><button type="button" data-monitoring-native-action="config:schedule" ${state.configStorageConfigured ? "" : "disabled"}>Synchronisation automatique</button></div></div>
                                <button class="toolbar-btn compact" type="button" data-monitoring-native-action="types">Types</button>
                                <button class="toolbar-btn compact" type="button" data-monitoring-native-action="engine">Paramètres</button>
                            </div>
                        </div></section>
                        <div class="table-wrap"><table class="device-table" id="monitoring-native-tree-${escapeHtml(columnContext())}"><thead id="monitoring-native-tree-head"></thead><tbody id="monitoring-native-tree-body"></tbody></table></div>
                    </article>
                </section>`;
            root.querySelector('[data-monitoring-action="refresh"]')?.addEventListener("click", () => refresh({ loading: true }));
            root.querySelector('[data-monitoring-action="tools"]')?.addEventListener("click", () => { state.toolsOpen = !state.toolsOpen; state.configMenuOpen = false; root.querySelector('[data-monitoring-popover="tools"]')?.toggleAttribute("hidden", !state.toolsOpen); root.querySelector('[data-monitoring-popover="config"]')?.setAttribute("hidden", ""); });
            root.querySelector('[data-monitoring-action="config-menu"]')?.addEventListener("click", () => { state.configMenuOpen = !state.configMenuOpen; state.toolsOpen = false; root.querySelector('[data-monitoring-popover="config"]')?.toggleAttribute("hidden", !state.configMenuOpen); root.querySelector('[data-monitoring-popover="tools"]')?.setAttribute("hidden", ""); });
            root.querySelector('[data-monitoring-filter="type"]')?.addEventListener("change", (event) => applyTreeFilters({ typeCode: event.target.value }));
            root.querySelector('[data-monitoring-filter="status"]')?.addEventListener("change", (event) => applyTreeFilters({ status: event.target.value }));
            root.querySelector('[data-monitoring-filter="query"]')?.addEventListener("input", (event) => { state.query = String(event.target.value || ""); render(); });
            root.querySelectorAll("[data-monitoring-native-action]").forEach((button) => {
                button.addEventListener("click", async () => {
                    const result = await onAction(String(button.dataset.monitoringNativeAction || ""));
                    state.toolsOpen = false;
                    state.configMenuOpen = false;
                    root.querySelector('[data-monitoring-popover="tools"]')?.setAttribute("hidden", "");
                    root.querySelector('[data-monitoring-popover="config"]')?.setAttribute("hidden", "");
                    if (result?.view === "logs") {
                        state.logs = Array.isArray(result.rows) ? result.rows : [];
                        render();
                    }
                });
            });
            const treeHead = root.querySelector("#monitoring-native-tree-head");
            const treeBody = root.querySelector("#monitoring-native-tree-body");
            const treeTable = root.querySelector(".device-table");
            if (SharedTreeView && treeHead instanceof HTMLElement && treeBody instanceof HTMLElement && treeTable instanceof HTMLTableElement) {
                const preferenceContext = columnContext();
                state.tree = new SharedTreeView({
                    headElement: treeHead,
                    bodyElement: treeBody,
                    tableElement: treeTable,
                    renderHead: true,
                    columnVisibilityStorageKey: `monitoring:devices:${preferenceContext}`,
                    loadRemoteColumnPreferences: !state.loadedColumnContexts.has(preferenceContext),
                    getColumns: treeColumns,
                    getRows: () => rows,
                    getRowKey: (row) => `${row.device_type || ""}:${row.id || ""}`,
                    getRowAttributes: (_row, index) => ({ "data-monitoring-device-index": String(index) }),
                    emptyMessage: "Aucun équipement ne correspond aux filtres.",
                    onRowDoubleClick: (device) => onDeviceDoubleClick(device),
                    onRowsRendered: () => treeBody.querySelectorAll("tr[data-monitoring-device-index]").forEach((row) => {
                        row.addEventListener("contextmenu", (event) => {
                            event.preventDefault();
                            const device = rows[Number(row.dataset.monitoringDeviceIndex || -1)];
                            if (device) onDeviceContext({
                                event,
                                device,
                                configBackupsEnabled: configBackupsEnabledForType(device.device_type),
                            });
                        });
                    }),
                });
                state.loadedColumnContexts.add(preferenceContext);
                state.tree.render();
            }
            ensureSelectedTypeSchema();
            renderStatus();
        }

        async function refresh({ loading = false } = {}) {
            if (state.destroyed || !requestJson) return;
            if (loading) onLoadingChange(true);
            try {
                const nextSnapshot = await requestJson("/monitoring/snapshot", { showGlobalLoading: false });
                onSnapshot(nextSnapshot);
                const nextFingerprint = monitoringSnapshotFingerprint(nextSnapshot);
                if (nextFingerprint !== state.snapshotFingerprint) {
                    state.snapshot = nextSnapshot;
                    state.snapshotFingerprint = nextFingerprint;
                    render();
                }
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

        function startPolling() {
            if (state.refreshTimer || state.destroyed) return;
            state.refreshTimer = window.setInterval(() => refresh(), 15000);
        }

        function connectRealtime() {
            if (!websocketToken || !window.WebSocket || state.destroyed) {
                startPolling();
                return;
            }
            const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
            const socket = new window.WebSocket(`${protocol}//${window.location.host}/monitoring/ws?token=${encodeURIComponent(websocketToken)}&interval_ms=1000`);
            state.websocket = socket;
            socket.addEventListener("message", (event) => {
                try {
                    const payload = JSON.parse(event.data);
                    if (payload?.event !== "monitoring.snapshot" || state.destroyed) return;
                    const nextSnapshot = payload.data;
                    onSnapshot(nextSnapshot);
                    const nextFingerprint = monitoringSnapshotFingerprint(nextSnapshot);
                    if (nextFingerprint === state.snapshotFingerprint) return;
                    state.snapshot = nextSnapshot;
                    state.snapshotFingerprint = nextFingerprint;
                    render();
                } catch (_) {
                }
            });
            socket.addEventListener("close", () => {
                if (state.websocket === socket) state.websocket = null;
                startPolling();
            });
            socket.addEventListener("error", () => socket.close());
        }

        return {
            async mount() {
                await refresh({ loading: true });
                connectRealtime();
            },
            refresh: () => refresh({ loading: true }),
            closeActiveView() {
                if (!Array.isArray(state.logs)) return false;
                state.logs = null;
                render();
                return true;
            },
            setConfigStorageConfigured(configured) {
                const next = Boolean(configured);
                if (state.configStorageConfigured === next) return;
                state.configStorageConfigured = next;
                render();
            },
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
                state.websocket?.close();
                state.websocket = null;
                statusTarget?.querySelector("#portal-monitoring-status-strip")?.remove();
            },
        };
    }

    window.NMPMonitoringModule = Object.freeze({ create, monitoringStatus });
}());
