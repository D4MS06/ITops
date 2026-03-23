const STANDARD_FIELDS = new Set([
    "name",
    "ip",
    "description",
    "id_Teamviewer",
    "device_subtype",
    "action_double_click",
    "web_url",
    "ssh_user",
    "notify",
]);

const FIELD_LABELS = {
    name: "Nom",
    ip: "IP",
    description: "Description",
    id_Teamviewer: "TeamViewer",
    device_subtype: "Sous-type",
    action_double_click: "Action double-clic",
    web_url: "URL web",
    ssh_user: "Utilisateur SSH",
    notify: "Notifications",
};

const state = {
    token: window.localStorage.getItem("nmp_token") || "",
    snapshot: null,
    websocket: null,
    reconnectTimer: null,
    pollingTimer: null,
    fallbackToPolling: false,
    capabilities: null,
    uiConfig: null,
    currentView: "dashboard",
    currentSection: "supervision",
    inventory: [],
    deviceTypes: [],
    deviceSchemas: {},
    selectedDeviceKey: "",
    inventoryFormMode: "edit",
    contextMenuDeviceKey: "",
    openTopMenu: "",
    configStorageState: null,
    supervisionSort: { column: "type", direction: "asc" },
    inventorySort: { column: "type", direction: "asc" },
    typeSyncTimer: null,
    lastSnapshotTypeSignature: "",
    configManagerDeviceKey: "",
};

const authScreen = document.getElementById("auth-screen");
const dashboardPanel = document.getElementById("dashboard-panel");
const authTitle = document.getElementById("auth-title");
const authHelp = document.getElementById("auth-help");
const authForm = document.getElementById("auth-form");
const authSubmit = document.getElementById("auth-submit");
const passwordInput = document.getElementById("password-input");
const authError = document.getElementById("auth-error");
const refreshButton = document.getElementById("refresh-button");
const logoutButton = document.getElementById("logout-button");
const deviceFilter = document.getElementById("device-filter");
const navToolbar = document.getElementById("nav-toolbar");
const cardsGrid = document.getElementById("cards-grid");
const monitoringToolbar = document.getElementById("monitoring-toolbar");
const placeholderPanel = document.getElementById("dashboard-placeholder");
const detailPanel = document.getElementById("detail-panel");
const detailTitle = document.getElementById("detail-title");
const inventoryTitle = document.getElementById("inventory-title");
const devicesSection = document.getElementById("devices-section");
const typesPanel = document.getElementById("types-panel");
const supervisionSection = document.getElementById("supervision-section");
const inventorySection = document.getElementById("inventory-section");
const runtimeStrip = document.querySelector(".runtime-strip");
const menuSupervision = document.getElementById("menu-supervision");
const menuEquipments = document.getElementById("menu-equipments");
const menuDisplay = document.getElementById("menu-display");
const menuHelp = document.getElementById("menu-help");
const inventoryTypeFilter = document.getElementById("inventory-type-filter");
const inventorySearch = document.getElementById("inventory-search");
const inventoryBody = document.getElementById("inventory-body");
const inventoryFeedback = document.getElementById("inventory-feedback");
const inventoryEmpty = document.getElementById("inventory-empty");
const inventoryDetail = document.getElementById("inventory-detail");
const inventoryDetailTitle = document.getElementById("inventory-detail-title");
const inventoryDetailFields = document.getElementById("inventory-detail-fields");
const inventoryLogsState = document.getElementById("inventory-logs-state");
const inventoryLogs = document.getElementById("inventory-logs");
const inventoryConfigsState = document.getElementById("inventory-configs-state");
const inventoryConfigs = document.getElementById("inventory-configs");
const inventoryEditButton = document.getElementById("inventory-edit-button");
const inventoryCancelButton = document.getElementById("inventory-cancel-button");
const inventoryEditForm = document.getElementById("inventory-edit-form");
const inventoryEditFields = document.getElementById("inventory-edit-fields");
const inventoryNotify = document.getElementById("inventory-notify");
const inventorySaveButton = document.getElementById("inventory-save-button");
const inventoryFormFeedback = document.getElementById("inventory-form-feedback");
const inventoryAddButton = document.getElementById("inventory-add-button");
const appModal = document.getElementById("app-modal");
const appModalBackdrop = document.getElementById("app-modal-backdrop");
const appModalPanel = document.getElementById("app-modal-panel");
const appModalTitle = document.getElementById("app-modal-title");
const appModalBody = document.getElementById("app-modal-body");
const appModalClose = document.getElementById("app-modal-close");
const topMenuPanel = document.getElementById("top-menu-panel");
const contextMenu = document.getElementById("context-menu");
const inventoryTableWrap = document.querySelector(".inventory-table-wrap");
const devicesHead = document.getElementById("devices-head");
const inventoryHead = document.getElementById("inventory-head");

function setError(message = "") {
    authError.hidden = !message;
    authError.textContent = message;
}

function setLiveStatus(label) {
    document.getElementById("runtime-live").textContent = label;
}

function clearRealtimeTimers() {
    window.clearTimeout(state.reconnectTimer);
    window.clearTimeout(state.pollingTimer);
    state.reconnectTimer = null;
    state.pollingTimer = null;
}

function teardownRealtime() {
    clearRealtimeTimers();
    if (state.websocket) {
        try {
            state.websocket.close();
        } catch (_error) {
        }
        state.websocket = null;
    }
}

function headers() {
    return state.token ? { Authorization: `Bearer ${state.token}` } : {};
}

function normalizeErrorMessage(message) {
    const normalized = String(message || "").trim();
    const lowered = normalized.toLowerCase();
    if (!normalized) {
        return "Connexion impossible.";
    }
    if (lowered === "invalid credentials." || lowered === "invalid credentials") {
        return "Identifiants invalides.";
    }
    if (lowered === "invalid or expired session." || lowered === "invalid or expired session") {
        return "Session invalide ou expiree.";
    }
    if (lowered === "missing bearer token." || lowered === "missing bearer token") {
        return "Jeton Bearer manquant.";
    }
    if (lowered === "empty bearer token." || lowered === "empty bearer token") {
        return "Jeton Bearer vide.";
    }
    return normalized;
}

async function requestJson(path, options = {}) {
    const response = await fetch(path, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...headers(),
            ...(options.headers || {}),
        },
    });
    if (!response.ok) {
        let detail = `${response.status} ${response.statusText}`;
        try {
            const body = await response.json();
            detail = body.detail || body.message || detail;
        } catch (_error) {
        }
        throw new Error(normalizeErrorMessage(detail));
    }
    if (response.status === 204) {
        return null;
    }
    return response.json();
}

function persistToken(token) {
    state.token = token || "";
    if (state.token) {
        window.localStorage.setItem("nmp_token", state.token);
    } else {
        window.localStorage.removeItem("nmp_token");
    }
}

function escapeHtml(value) {
    return String(value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function statusClass(status) {
    const normalized = String(status || "idle").toLowerCase();
    if (normalized === "online") {
        return "status-online";
    }
    if (normalized === "offline") {
        return "status-offline";
    }
    return "status-idle";
}

function localizeStatus(status) {
    const normalized = String(status || "idle").toLowerCase();
    if (normalized === "online") {
        return "En ligne";
    }
    if (normalized === "offline") {
        return "Hors ligne";
    }
    if (normalized === "idle") {
        return "Inactif";
    }
    return status || "";
}

function localizeEventKind(kind) {
    const normalized = String(kind || "").toLowerCase();
    if (normalized === "status_change") {
        return "Changement d'etat";
    }
    if (normalized === "diagnostic") {
        return "Diagnostic";
    }
    return kind || "Evenement";
}

function displayLabelForView(view) {
    if (view === "dashboard") {
        return "Tableau de bord";
    }
    if (view === "global") {
        return "Globale";
    }
    const typeState = (state.snapshot?.types || []).find((item) => item.type_code === view);
    return typeState ? typeState.label : view;
}

function typeLabel(typeCode) {
    const item = (state.deviceTypes || []).find((entry) => entry.code === typeCode);
    return item ? item.label : typeCode;
}

function typeMeta(typeCode) {
    return (state.deviceTypes || []).find((entry) => entry.code === typeCode) || null;
}

function compareByColumn(column, direction, left, right) {
    const dir = direction === "desc" ? -1 : 1;
    const byText = (a, b) => String(a || "").localeCompare(String(b || ""), undefined, { sensitivity: "base" }) * dir;
    const byIp = (a, b) => {
        const parse = (value) => String(value || "").split(".").map((x) => Number.parseInt(x, 10));
        const av = parse(a);
        const bv = parse(b);
        const len = Math.max(av.length, bv.length);
        for (let i = 0; i < len; i += 1) {
            const ai = Number.isFinite(av[i]) ? av[i] : -1;
            const bi = Number.isFinite(bv[i]) ? bv[i] : -1;
            if (ai !== bi) {
                return (ai - bi) * dir;
            }
        }
        return 0;
    };
    if (column === "ip") {
        return byIp(left.ip, right.ip);
    }
    if (column === "notify") {
        return ((left.notify === right.notify ? 0 : left.notify ? 1 : -1) * dir);
    }
    if (column === "type") {
        return byText(typeLabel(left.device_type || left.type), typeLabel(right.device_type || right.type));
    }
    if (column === "status") {
        return byText(localizeStatus(left.status), localizeStatus(right.status));
    }
    if (column === "description") {
        return byText(left.description, right.description);
    }
    return byText(left.name, right.name);
}

function formatDetailValue(value) {
    const normalized = String(value ?? "").trim();
    return normalized || "-";
}

function deviceKey(device) {
    return `${device.device_type}:${device.id}`;
}

function contextMenuDevice() {
    return state.inventory.find((item) => deviceKey(item) === state.contextMenuDeviceKey) || getSelectedDevice();
}

function configManagerDevice() {
    return state.inventory.find((item) => deviceKey(item) === state.configManagerDeviceKey) || null;
}

function closeContextMenu() {
    contextMenu.hidden = true;
    contextMenu.innerHTML = "";
    state.contextMenuDeviceKey = "";
}

function closeTopMenu() {
    topMenuPanel.hidden = true;
    topMenuPanel.innerHTML = "";
    state.openTopMenu = "";
    [menuSupervision, menuEquipments, menuDisplay, menuHelp].forEach((button) => {
        button.classList.remove("active");
    });
}

function openModal(title, bodyMarkup, options = {}) {
    appModalTitle.textContent = title;
    appModalBody.innerHTML = bodyMarkup;
    appModalPanel.style.width = options.width || "min(980px, calc(100vw - 40px))";
    appModal.hidden = false;
}

function closeModal() {
    appModal.hidden = true;
    appModalBody.innerHTML = "";
    state.configManagerDeviceKey = "";
}

function canRunBuiltinAction(device, builtin) {
    const ip = String(device?.ip || "").trim();
    const tvId = String(device?.id_Teamviewer || "").trim();
    const webUrl = String(device?.web_url || "").trim();
    if (builtin === "teamviewer") {
        return Boolean(tvId);
    }
    if (builtin === "web") {
        return Boolean(webUrl || ip);
    }
    return false;
}

function builtinActionUrl(device, builtin) {
    const ip = String(device?.ip || "").trim();
    const subtype = String(device?.device_subtype || device?.type || "").trim().toLowerCase();
    const tvId = String(device?.id_Teamviewer || "").trim();
    const webUrl = String(device?.web_url || "").trim();
    if (builtin === "teamviewer" && tvId) {
        return `https://start.teamviewer.com/${encodeURIComponent(tvId)}`;
    }
    if (builtin === "web") {
        if (webUrl) {
            return webUrl;
        }
        if (subtype === "dsm") {
            return `http://${ip}:5000`;
        }
        if (ip) {
            return `http://${ip}`;
        }
    }
    return "";
}

function escapeAttribute(value) {
    return escapeHtml(String(value || "")).replaceAll("`", "&#96;");
}

async function runBuiltinAction(device, builtin) {
    const url = builtinActionUrl(device, builtin);
    if (!url) {
        inventoryFeedback.textContent = `Action ${builtin} indisponible sur cette interface web.`;
        return;
    }
    window.open(url, "_blank", "noopener,noreferrer");
}

async function runDeviceDoubleClickAction(device) {
    await ensureDeviceTypeSchema(device.device_type);
    const schema = state.deviceSchemas[device.device_type] || { actions: [] };
    const available = (schema.actions || [])
        .map((item) => String(item.target_value || item.action_key || "").trim().toLowerCase())
        .filter((item) => ["web", "teamviewer"].includes(item));
    let action = String(device.action_double_click || "").trim().toLowerCase();
    if (!available.includes(action)) {
        action = available[0] || "web";
    }
    await runBuiltinAction(device, action);
}

function statusMap() {
    const map = new Map();
    const groups = state.snapshot?.devices || {};
    Object.entries(groups).forEach(([typeCode, devices]) => {
        devices.forEach((item) => {
            map.set(`${typeCode}:${item.id}`, item);
        });
    });
    return map;
}

function inventoryRows() {
    const query = String(inventorySearch.value || "").trim().toLowerCase();
    const filterType = String(inventoryTypeFilter.value || "").trim();
    const statuses = statusMap();
    return state.inventory
        .map((item) => {
            const runtime = statuses.get(deviceKey(item)) || {};
            return {
                ...item,
                status: runtime.status || "idle",
                last_seen: runtime.last_seen || "",
            };
        })
        .filter((item) => !filterType || item.device_type === filterType)
        .filter((item) => {
            if (!query) {
                return true;
            }
            return [
                item.device_type,
                typeLabel(item.device_type),
                item.name,
                item.ip,
                item.description,
                item.web_url,
                item.ssh_user,
            ]
                .join(" ")
                .toLowerCase()
                .includes(query);
        })
        .sort((left, right) => compareByColumn(state.inventorySort.column, state.inventorySort.direction, left, right));
}

function getSelectedDevice() {
    return inventoryRows().find((item) => deviceKey(item) === state.selectedDeviceKey) || null;
}

function ensureSelectedDevice() {
    const rows = inventoryRows();
    if (!rows.length) {
        state.selectedDeviceKey = "";
        return null;
    }
    if (!rows.some((item) => deviceKey(item) === state.selectedDeviceKey)) {
        state.selectedDeviceKey = deviceKey(rows[0]);
    }
    return getSelectedDevice();
}

function customFieldDefinitions(deviceType) {
    const schema = state.deviceSchemas[deviceType];
    const fields = Array.isArray(schema?.fields) ? schema.fields : [];
    return fields.filter((field) => !STANDARD_FIELDS.has(String(field.field_key || "")));
}

function fieldLabel(fieldKey, explicitLabel = "") {
    return explicitLabel || FIELD_LABELS[fieldKey] || fieldKey;
}

async function ensureDeviceTypeSchema(typeCode) {
    if (state.deviceSchemas[typeCode]) {
        return state.deviceSchemas[typeCode];
    }
    const schema = await requestJson(`/device-types/${encodeURIComponent(typeCode)}/schema`);
    state.deviceSchemas[typeCode] = schema;
    return schema;
}

async function loadInventoryConfigs(device) {
    inventoryConfigsState.textContent = "Chargement...";
    inventoryConfigs.innerHTML = "";
    const meta = typeMeta(device.device_type);
    if (!meta?.config_backups_enabled) {
        inventoryConfigsState.textContent = "Non disponible";
        inventoryConfigs.innerHTML = `<div class="muted">Aucune gestion de configuration pour ce type.</div>`;
        return;
    }
    try {
        const params = new URLSearchParams({
            device_type_label: typeLabel(device.device_type),
            device_name: device.name,
        });
        const rows = await requestJson(`/config-files?${params.toString()}`);
        if (deviceKey(device) !== state.selectedDeviceKey) {
            return;
        }
        if (!rows.length) {
            inventoryConfigsState.textContent = "Aucun fichier";
            inventoryConfigs.innerHTML = `<div class="muted">Aucune version locale disponible.</div>`;
            return;
        }
        inventoryConfigsState.textContent = `${rows.length} fichier(s)`;
        inventoryConfigs.innerHTML = rows
            .map((row) => `
                <article class="log-item">
                    <div class="config-item-title">${escapeHtml(row.name)}</div>
                    <div class="config-item-meta">${escapeHtml(row.modified_at)}</div>
                    ${row.detail ? `<div class="log-item-body">${escapeHtml(row.detail)}</div>` : ""}
                </article>
            `)
            .join("");
    } catch (error) {
        if (deviceKey(device) !== state.selectedDeviceKey) {
            return;
        }
        inventoryConfigsState.textContent = "Erreur";
        inventoryConfigs.innerHTML = `<div class="error-text">${escapeHtml(normalizeErrorMessage(error.message))}</div>`;
    }
}

async function ensureInventorySideData(device) {
    await Promise.all([
        loadInventoryLogs(device),
        loadInventoryConfigs(device),
    ]);
}

function applyUiConfig(config) {
    state.uiConfig = config || null;
    const root = document.documentElement;
    const colors = (config && config.theme_colors) || {};
    const mapped = {
        "--bg": colors.app_bg,
        "--surface": colors.surface_bg,
        "--panel": colors.panel_bg,
        "--panel-hover": colors.panel_hover_bg,
        "--text": colors.text_primary,
        "--text-secondary": colors.text_secondary,
        "--muted": colors.text_muted,
        "--line": colors.placeholder_border,
        "--accent": colors.button_global_bg || colors.nav_active_bg,
        "--success": colors.button_active_bg,
        "--danger": "#dc2626",
        "--warning": "#d97706",
        "--control-bg": colors.control_bg || colors.button_inactive_bg,
        "--control-fg": colors.control_fg || colors.button_inactive_fg,
        "--control-border": colors.control_border || colors.placeholder_border,
        "--control-hover-bg": colors.control_hover_bg || colors.nav_active_bg,
        "--control-hover-fg": colors.control_hover_fg || colors.text_primary,
        "--tree-bg": colors.tree_bg,
        "--tree-fg": colors.tree_fg,
        "--tree-heading-bg": colors.tree_heading_bg,
        "--tree-heading-fg": colors.tree_heading_fg,
    };
    Object.entries(mapped).forEach(([name, value]) => {
        if (value) {
            root.style.setProperty(name, value);
        }
    });
    const requiresToken = Boolean(config && config.watermark_url === "/ui/watermark-image");
    const isAuthWatermark = Boolean(config && config.watermark_url === "/ui/auth-watermark-image");
    const canUseWatermark = Boolean(config && config.watermark_enabled && config.watermark_url);
    const watermarkEnabled = canUseWatermark && (!requiresToken || Boolean(state.token));
    const watermarkUrl = watermarkEnabled
        ? `${config.watermark_url}${requiresToken ? `?token=${encodeURIComponent(state.token)}` : ""}${requiresToken ? "&" : "?"}v=${encodeURIComponent(config.app_version || "1")}`
        : "";
    const watermarkOpacity = watermarkEnabled
        ? Math.min(0.4, Math.max(0.18, Number(config.watermark_opacity || 0.16) * 1.8))
        : 0;
    const dashboardWatermark = watermarkEnabled && !isAuthWatermark ? `url("${watermarkUrl}")` : "none";
    const authWatermark = watermarkEnabled ? `url("${watermarkUrl}")` : "none";
    root.style.setProperty("--dashboard-watermark-image", dashboardWatermark);
    root.style.setProperty("--dashboard-watermark-opacity", String(watermarkEnabled && !isAuthWatermark ? watermarkOpacity : 0));
    root.style.setProperty("--auth-watermark-image", authWatermark);
    root.style.setProperty("--auth-watermark-opacity", String(watermarkEnabled ? Math.min(0.9, watermarkOpacity * 2.1) : 0));
    document.getElementById("app-version").textContent = config?.app_version || "-";
    document.getElementById("ui-theme-label").textContent = config?.ui_theme || "-";
    document.getElementById("watermark-state").textContent = watermarkEnabled
        ? `Actif (${Math.round(watermarkOpacity * 100)}%)`
        : "Desactive";
}

async function loadAuthMode() {
    const status = await requestJson("/auth/status", { headers: {} });
    const bootstrapMode = !status.has_admin_password;
    authTitle.textContent = bootstrapMode ? "Initialiser l'acces" : "Connexion";
    authHelp.textContent = bootstrapMode
        ? "Aucun mot de passe admin n'est defini. Cree le mot de passe initial pour activer l'acces web."
        : "Connecte-toi avec le mot de passe administrateur pour ouvrir le dashboard web.";
    authSubmit.textContent = bootstrapMode ? "Initialiser" : "Se connecter";
    passwordInput.autocomplete = bootstrapMode ? "new-password" : "current-password";
    authForm.dataset.mode = bootstrapMode ? "bootstrap" : "login";
    await loadPublicUiConfig();
}

function showDashboard() {
    authScreen.hidden = true;
    dashboardPanel.hidden = false;
    authScreen.style.display = "none";
    dashboardPanel.style.display = "";
    document.body.dataset.screen = "dashboard";
    document.documentElement.classList.remove("auth-mode");
    document.documentElement.classList.add("dashboard-mode");
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
}

function showAuth() {
    dashboardPanel.hidden = true;
    authScreen.hidden = false;
    dashboardPanel.style.display = "none";
    authScreen.style.display = "";
    document.body.dataset.screen = "auth";
    document.documentElement.classList.add("auth-mode");
    document.documentElement.classList.remove("dashboard-mode");
    setLiveStatus("Deconnecte");
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
}

function renderNavigation(types) {
    const runningTypes = state.snapshot?.summary?.running_types || [];
    if (state.currentView !== "dashboard" && state.currentView !== "global" && !types.some((item) => item.type_code === state.currentView)) {
        state.currentView = "dashboard";
    }
    navToolbar.innerHTML = "";
    const entries = [
        { key: "dashboard", label: "Tableau de bord" },
        ...types.map((item) => ({ key: item.type_code, label: item.label })),
        { key: "global", label: "Globale" },
    ];
    entries.forEach((entry) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = `nav-btn${state.currentView === entry.key ? " active" : ""}`;
        button.textContent = entry.label;
        button.addEventListener("click", () => {
            state.currentView = entry.key;
            renderSection();
        });
        navToolbar.appendChild(button);
    });
    if (state.currentView === "dashboard" && runningTypes.length > 1) {
        state.currentView = "dashboard";
    }
}

function renderCards(snapshot) {
    const summary = snapshot.summary || {};
    const runningAny = Boolean(summary.running_any);
    const runningAll = Boolean(summary.running_all);
    const cards = [
        {
            title: "Equipements",
            value: summary.total || 0,
            sub: "Inventaire global",
            stats: runningAny ? { online: summary.online || 0, offline: summary.offline || 0 } : null,
            clickView: "global",
        },
        {
            title: "Monitoring",
            value: runningAll ? "Globale" : (runningAny ? "Partiel" : "Arrete"),
            sub: "Etat des sondes",
            stats: null,
            clickView: null,
        },
        ...snapshot.types.map((item) => ({
            title: `Etat ${item.label}`,
            value: item.total,
            sub: `Inventaire ${item.label.toLowerCase()}`,
            stats: item.running ? { online: item.online, offline: item.offline } : null,
            clickView: item.type_code,
        })),
    ];
    cardsGrid.innerHTML = "";
    cards.forEach((card) => {
        const article = document.createElement("article");
        article.className = `dash-card panel${card.clickView ? " clickable" : ""}`;
        article.innerHTML = `
            <div class="dash-card-title">${escapeHtml(card.title)}</div>
            <div class="dash-card-value">${escapeHtml(card.value)}</div>
            <div class="dash-card-sub">${escapeHtml(card.sub)}</div>
            <div class="dash-card-stats">
                ${card.stats ? `<span>En ligne: <span class="stat-online">${escapeHtml(card.stats.online)}</span></span>` : "<span></span>"}
                ${card.stats ? `<span>Hors ligne: <span class="stat-offline">${escapeHtml(card.stats.offline)}</span></span>` : "<span></span>"}
            </div>
        `;
        if (card.clickView) {
            article.addEventListener("click", () => {
                state.currentSection = "supervision";
                state.currentView = card.clickView;
                renderSection();
            });
        }
        cardsGrid.appendChild(article);
    });
}

function renderMonitoringToolbar(types, summary) {
    const runningAll = Boolean(summary?.running_all);
    monitoringToolbar.innerHTML = "";

    const globalButton = document.createElement("button");
    globalButton.type = "button";
    globalButton.className = `monitor-btn${runningAll ? " global-active" : ""}`;
    globalButton.textContent = "Monitoring globale";
    globalButton.addEventListener("click", async () => {
        await postMonitoringCommand(runningAll ? "/monitoring/stop-all" : "/monitoring/start-all");
    });
    monitoringToolbar.appendChild(globalButton);

    types.forEach((item) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = `monitor-btn${item.running ? " type-active" : ""}`;
        button.textContent = `Monitoring ${item.label}`;
        button.addEventListener("click", async () => {
            await postMonitoringCommand(`/monitoring/${item.running ? "stop" : "start"}/${encodeURIComponent(item.type_code)}`);
        });
        monitoringToolbar.appendChild(button);
    });
}

function renderTypes(types) {
    const container = document.getElementById("types-list");
    container.innerHTML = "";
    types.forEach((item) => {
        const article = document.createElement("article");
        article.className = "type-row";
        article.innerHTML = `
            <div class="type-row-head">
                <div>
                    <strong>${escapeHtml(item.label)}</strong>
                    <div class="muted">${escapeHtml(item.type_code)}</div>
                </div>
                <span class="state-badge ${item.running ? "state-live" : "state-idle"}">${item.running ? "Actif" : "Arrete"}</span>
            </div>
            <div class="type-row-stats">
                <span>${item.total} total</span>
                <span class="stat-online">${item.online} en ligne</span>
                <span class="stat-offline">${item.offline} hors ligne</span>
                <span>${item.idle} inactif</span>
            </div>
        `;
        article.addEventListener("click", () => {
            state.currentSection = "supervision";
            state.currentView = item.type_code;
            renderSection();
        });
        container.appendChild(article);
    });
}

function visibleRowsForCurrentView(snapshot) {
    const rows = Object.entries(snapshot.devices || {}).flatMap(([typeCode, items]) =>
        items.map((item) => ({ ...item, device_type: item.device_type || typeCode })),
    );
    if (state.currentView === "global" || state.currentView === "dashboard") {
        return rows;
    }
    return rows.filter((item) => item.device_type === state.currentView);
}

function resolveDeviceRecord(item) {
    const key = `${item.device_type}:${item.id}`;
    const stored = state.inventory.find((entry) => deviceKey(entry) === key);
    return stored ? { ...stored, status: item.status || "idle" } : { ...item };
}

function renderDevices(snapshot) {
    const query = (deviceFilter.value || "").trim().toLowerCase();
    const tbody = document.getElementById("devices-body");
    tbody.innerHTML = "";

    visibleRowsForCurrentView(snapshot)
        .filter((item) => {
            if (!query) {
                return true;
            }
            return [item.device_type, item.name, item.ip, item.status, item.description].join(" ").toLowerCase().includes(query);
        })
        .sort((left, right) => compareByColumn(state.supervisionSort.column, state.supervisionSort.direction, left, right))
        .forEach((item) => {
            const device = resolveDeviceRecord(item);
            const tr = document.createElement("tr");
            if (deviceKey(device) === state.selectedDeviceKey) {
                tr.classList.add("is-selected");
            }
            tr.innerHTML = `
                <td>${escapeHtml(item.device_type || "")}</td>
                <td>${escapeHtml(item.name || "")}</td>
                <td>${escapeHtml(item.ip || "")}</td>
                <td><span class="status-badge ${statusClass(item.status)}">${escapeHtml(localizeStatus(item.status || "idle"))}</span></td>
                <td>${escapeHtml(item.description || "")}</td>
            `;
            tr.addEventListener("click", () => {
                state.selectedDeviceKey = deviceKey(device);
                closeContextMenu();
                closeTopMenu();
                if (state.snapshot) {
                    renderDevices(state.snapshot);
                }
            });
            tr.addEventListener("dblclick", async () => {
                state.selectedDeviceKey = deviceKey(device);
                closeTopMenu();
                await runDeviceDoubleClickAction(device);
            });
            tr.addEventListener("contextmenu", async (event) => {
                event.preventDefault();
                state.selectedDeviceKey = deviceKey(device);
                if (state.snapshot) {
                    renderDevices(state.snapshot);
                }
                await openContextMenu(event.clientX, event.clientY, device);
            });
            tbody.appendChild(tr);
        });
}

function applyCurrentView() {
    if (!state.snapshot) {
        return;
    }
    const summary = state.snapshot.summary || {};
    const runningTypes = summary.running_types || [];
    const runningAny = Boolean(summary.running_any);
    const focusView = state.currentView !== "dashboard";

    renderNavigation(state.snapshot.types || []);
    detailPanel.classList.toggle("detail-focus-mode", focusView && state.currentSection === "supervision");

    if (state.currentView === "dashboard") {
        if (!runningAny) {
            detailPanel.hidden = true;
            placeholderPanel.hidden = false;
            return;
        }
        placeholderPanel.hidden = true;
        detailPanel.hidden = false;
        detailTitle.textContent = "Globale";
        inventoryTitle.textContent = "Inventaire global";
        typesPanel.hidden = false;
        devicesSection.hidden = false;
        if (runningTypes.length === 1) {
            state.currentView = runningTypes[0];
            applyCurrentView();
            return;
        }
        renderDevices(state.snapshot);
        return;
    }

    placeholderPanel.hidden = true;
    detailPanel.hidden = false;
    typesPanel.hidden = true;
    devicesSection.hidden = false;
    detailTitle.textContent = displayLabelForView(state.currentView);
    inventoryTitle.textContent = state.currentView === "global"
        ? "Inventaire global"
        : `Inventaire ${displayLabelForView(state.currentView)}`;
    renderDevices(state.snapshot);
}

function renderInventoryFilters() {
    const options = [
        { value: "", label: "Tous les types" },
        ...state.deviceTypes
            .slice()
            .sort((left, right) => `${left.sort_order}:${left.label}`.localeCompare(`${right.sort_order}:${right.label}`))
            .map((item) => ({ value: item.code, label: item.label })),
    ];
    inventoryTypeFilter.innerHTML = options
        .map((item) => `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</option>`)
        .join("");
}

function renderInventoryList() {
    const rows = inventoryRows();
    inventoryBody.innerHTML = "";
    inventoryFeedback.textContent = `${rows.length} equipement(s) affiches`;
    rows.forEach((item) => {
        const selected = deviceKey(item) === state.selectedDeviceKey;
        const tr = document.createElement("tr");
        if (selected) {
            tr.classList.add("is-selected");
        }
        tr.innerHTML = `
            <td>${escapeHtml(typeLabel(item.device_type))}</td>
            <td>${escapeHtml(item.name)}</td>
            <td>${escapeHtml(item.ip)}</td>
            <td><span class="status-badge ${statusClass(item.status)}">${escapeHtml(localizeStatus(item.status))}</span></td>
            <td>${item.notify ? "Oui" : "Non"}</td>
        `;
        tr.addEventListener("click", async () => {
            state.selectedDeviceKey = deviceKey(item);
            closeInventoryEditMode();
            closeContextMenu();
            closeTopMenu();
            renderInventoryDetail();
            await ensureInventorySideData(item);
        });
        tr.addEventListener("dblclick", async () => {
            state.selectedDeviceKey = deviceKey(item);
            closeTopMenu();
            renderInventoryDetail();
            await runDeviceDoubleClickAction(item);
        });
        tr.addEventListener("contextmenu", async (event) => {
            event.preventDefault();
            event.stopPropagation();
            state.selectedDeviceKey = deviceKey(item);
            renderInventoryDetail();
            await openContextMenu(event.clientX, event.clientY, item);
        });
        inventoryBody.appendChild(tr);
    });
}

function renderInventoryDetail() {
    const device = ensureSelectedDevice();
    renderInventoryList();
    if (!device) {
        inventoryDetailTitle.textContent = "Aucun equipement selectionne";
        inventoryEmpty.hidden = false;
        inventoryDetail.hidden = true;
        inventoryEditButton.disabled = true;
        inventoryLogs.innerHTML = "";
        inventoryLogsState.textContent = "Aucun equipement";
        inventoryConfigs.innerHTML = "";
        inventoryConfigsState.textContent = "Aucun equipement";
        return;
    }

    inventoryDetailTitle.textContent = `${device.name} (${typeLabel(device.device_type)})`;
    inventoryEmpty.hidden = true;
    inventoryDetail.hidden = false;
    inventoryEditButton.disabled = false;

    const details = [
        ["Type", typeLabel(device.device_type)],
        ["Nom", device.name],
        ["IP", device.ip],
        ["Statut", localizeStatus(device.status)],
        ["Description", device.description],
        ["Notifications", device.notify ? "Oui" : "Non"],
        ["TeamViewer", device.id_Teamviewer],
        ["Sous-type", device.device_subtype],
        ["Double-clic", device.action_double_click],
        ["URL web", device.web_url],
        ["Utilisateur SSH", device.ssh_user],
    ];

    customFieldDefinitions(device.device_type).forEach((field) => {
        details.push([fieldLabel(field.field_key, field.label), device.custom_data?.[field.field_key] || ""]);
    });

    inventoryDetailFields.innerHTML = details
        .map(([label, value]) => `<dt>${escapeHtml(label)}</dt><dd>${escapeHtml(formatDetailValue(value))}</dd>`)
        .join("");
}

async function loadInventoryLogs(device) {
    inventoryLogsState.textContent = "Chargement...";
    inventoryLogs.innerHTML = "";
    try {
        const params = new URLSearchParams({
            limit: "12",
            device_type: device.device_type,
            device_id: device.id,
        });
        const rows = await requestJson(`/logs?${params.toString()}`);
        if (deviceKey(device) !== state.selectedDeviceKey) {
            return;
        }
        if (!rows.length) {
            inventoryLogsState.textContent = "Aucun evenement recent";
            inventoryLogs.innerHTML = `<div class="muted">Aucun log pour cet equipement.</div>`;
            return;
        }
        inventoryLogsState.textContent = `${rows.length} evenement(s)`;
        inventoryLogs.innerHTML = rows
            .map((row) => `
                <article class="log-item">
                    <div class="log-item-head">
                        <strong>${escapeHtml(localizeEventKind(row.event_kind))}</strong>
                        <span class="log-item-meta">${escapeHtml(row.created_at)}</span>
                    </div>
                    <div class="log-item-body">
                        ${escapeHtml(localizeStatus(row.old_status))} -> ${escapeHtml(localizeStatus(row.new_status))}
                        ${row.details ? `<br>${escapeHtml(row.details)}` : ""}
                    </div>
                </article>
            `)
            .join("");
    } catch (error) {
        if (deviceKey(device) !== state.selectedDeviceKey) {
            return;
        }
        inventoryLogsState.textContent = "Erreur";
        inventoryLogs.innerHTML = `<div class="error-text">${escapeHtml(normalizeErrorMessage(error.message))}</div>`;
    }
}

function createFieldMarkup({ key, label, value, multiline = false, wide = false }) {
    if (multiline) {
        return `
            <label class="field ${wide ? "wide" : ""}">
                <span>${escapeHtml(label)}</span>
                <textarea name="${escapeHtml(key)}">${escapeHtml(value)}</textarea>
            </label>
        `;
    }
    return `
        <label class="field ${wide ? "wide" : ""}">
            <span>${escapeHtml(label)}</span>
            <input name="${escapeHtml(key)}" value="${escapeHtml(value)}">
        </label>
    `;
}

function createSelectMarkup({ key, label, options, value }) {
    return `
        <label class="field">
            <span>${escapeHtml(label)}</span>
            <select name="${escapeHtml(key)}">
                ${options.map((item) => `<option value="${escapeHtml(item.value)}"${item.value === value ? " selected" : ""}>${escapeHtml(item.label)}</option>`).join("")}
            </select>
        </label>
    `;
}

function buildDeviceFormMarkup(current, mode, targetType) {
    const customFields = customFieldDefinitions(targetType);
    return `
        <form id="modal-device-form" class="modal-form">
            <div class="modal-grid">
                ${mode === "create" ? createSelectMarkup({
                    key: "device_type",
                    label: "Type",
                    value: targetType,
                    options: state.deviceTypes.map((item) => ({ value: item.code, label: item.label })),
                }) : ""}
                ${createFieldMarkup({ key: "name", label: fieldLabel("name"), value: current.name })}
                ${createFieldMarkup({ key: "ip", label: fieldLabel("ip"), value: current.ip })}
                ${createFieldMarkup({ key: "description", label: fieldLabel("description"), value: current.description, multiline: true, wide: true })}
                ${createFieldMarkup({ key: "id_Teamviewer", label: fieldLabel("id_Teamviewer"), value: current.id_Teamviewer })}
                ${createFieldMarkup({ key: "device_subtype", label: fieldLabel("device_subtype"), value: current.device_subtype })}
                ${createFieldMarkup({ key: "action_double_click", label: fieldLabel("action_double_click"), value: current.action_double_click })}
                ${createFieldMarkup({ key: "web_url", label: fieldLabel("web_url"), value: current.web_url })}
                ${createFieldMarkup({ key: "ssh_user", label: fieldLabel("ssh_user"), value: current.ssh_user })}
                ${customFields.map((field) => createFieldMarkup({
                    key: `custom:${field.field_key}`,
                    label: fieldLabel(field.field_key, field.label),
                    value: current.custom_data?.[field.field_key] || "",
                    multiline: String(field.field_kind || "").toLowerCase() === "textarea",
                    wide: String(field.field_kind || "").toLowerCase() === "textarea",
                })).join("")}
            </div>
            <label class="check-field">
                <input id="modal-device-notify" name="notify" type="checkbox" ${current.notify ? "checked" : ""}>
                <span>Notifications actives</span>
            </label>
            <p id="modal-device-feedback" class="muted inventory-feedback"></p>
            <div class="modal-actions">
                <button class="toolbar-btn" type="button" data-action="modal:close">Annuler</button>
                <button class="primary-btn" type="submit">${mode === "create" ? "Ajouter" : "Enregistrer"}</button>
            </div>
        </form>
    `;
}

function buildLogsModalMarkup(rows, options = {}) {
    const heading = options.heading || "Journal";
    return `
        <section class="modal-form">
            <div class="section-head slim-head">
                <h3>${escapeHtml(heading)}</h3>
            </div>
            <div class="modal-log-list">
                ${rows.length ? rows.map((row) => `
                    <article class="log-item">
                        <div class="log-item-head">
                            <strong>${escapeHtml(localizeEventKind(row.event_kind))}</strong>
                            <span class="log-item-meta">${escapeHtml(row.created_at)}</span>
                        </div>
                        <div class="log-item-body">
                            <strong>${escapeHtml(row.device_name)}</strong> (${escapeHtml(typeLabel(row.dtype))})<br>
                            ${escapeHtml(localizeStatus(row.old_status))} -> ${escapeHtml(localizeStatus(row.new_status))}
                            ${row.details ? `<br>${escapeHtml(row.details)}` : ""}
                        </div>
                    </article>
                `).join("") : `<div class="muted">Aucun evenement.</div>`}
            </div>
        </section>
    `;
}

function buildMonitoringSettingsMarkup(settings) {
    return `
        <form id="modal-settings-form" class="modal-form">
            <div class="modal-settings-grid">
                ${createFieldMarkup({ key: "offline_delay_seconds", label: "Delai offline (s)", value: settings.offline_delay_seconds })}
                ${createFieldMarkup({ key: "online_recovery_delay_seconds", label: "Delai online (s)", value: settings.online_recovery_delay_seconds })}
                ${createFieldMarkup({ key: "notification_cooldown_seconds", label: "Cooldown notif (s)", value: settings.notification_cooldown_seconds })}
                ${createFieldMarkup({ key: "failures_for_offline", label: "Echecs pour offline", value: settings.failures_for_offline })}
                ${createFieldMarkup({ key: "successes_for_online", label: "Succes pour online", value: settings.successes_for_online })}
                ${createFieldMarkup({ key: "ping_timeout_ms", label: "Timeout ping (ms)", value: settings.ping_timeout_ms })}
                ${createFieldMarkup({ key: "probe_interval_ms", label: "Intervalle sonde (ms)", value: settings.probe_interval_ms })}
                ${createSelectMarkup({
                    key: "ui_theme",
                    label: "Theme",
                    value: settings.ui_theme,
                    options: [
                        { value: "light", label: "Clair" },
                        { value: "dark", label: "Sombre" },
                    ],
                })}
            </div>
            <label class="check-field">
                <input name="log_diagnostic_events" type="checkbox" ${settings.log_diagnostic_events ? "checked" : ""}>
                <span>Journaliser les evenements diagnostiques</span>
            </label>
            <label class="check-field">
                <input name="show_status_popup" type="checkbox" ${settings.show_status_popup ? "checked" : ""}>
                <span>Activer les popups de statut</span>
            </label>
            <p id="modal-settings-feedback" class="muted inventory-feedback"></p>
            <div class="modal-actions">
                <button class="toolbar-btn" type="button" data-action="modal:close">Annuler</button>
                <button class="primary-btn" type="submit">Enregistrer</button>
            </div>
        </form>
    `;
}

function buildNotificationSettingsMarkup(settings) {
    return `
        <form id="modal-notification-form" class="modal-form">
            <div class="modal-settings-grid">
                ${createFieldMarkup({ key: "smtp_host", label: "SMTP host", value: settings.smtp_host || "" })}
                ${createFieldMarkup({ key: "smtp_port", label: "SMTP port", value: settings.smtp_port || 0 })}
                ${createFieldMarkup({ key: "user", label: "Utilisateur SMTP", value: settings.user || "" })}
                ${createFieldMarkup({ key: "recipients", label: "Destinataires", value: settings.recipients || "", wide: true })}
            </div>
            <label class="check-field">
                <input name="use_tls" type="checkbox" ${settings.use_tls ? "checked" : ""}>
                <span>Activer TLS</span>
            </label>
            <label class="check-field">
                <input name="show_status_popup" type="checkbox" ${settings.show_status_popup ? "checked" : ""}>
                <span>Activer les popups de statut</span>
            </label>
            <p id="modal-notification-feedback" class="muted inventory-feedback"></p>
            <div class="modal-actions">
                <button class="toolbar-btn" type="button" data-action="modal:close">Annuler</button>
                <button class="primary-btn" type="submit">Enregistrer</button>
            </div>
        </form>
    `;
}

function buildWebServerSettingsMarkup(settings) {
    return `
        <form id="modal-webserver-form" class="modal-form">
            <div class="modal-settings-grid">
                ${createFieldMarkup({ key: "web_server_host", label: "Host", value: settings.web_server_host || "127.0.0.1" })}
                ${createFieldMarkup({ key: "web_server_port", label: "Port", value: settings.web_server_port || 8000 })}
                ${createFieldMarkup({ key: "web_server_public_url", label: "URL publique", value: settings.web_server_public_url || "", wide: true })}
            </div>
            <label class="check-field">
                <input name="web_server_autostart" type="checkbox" ${settings.web_server_autostart ? "checked" : ""}>
                <span>Demarrage automatique</span>
            </label>
            <label class="check-field">
                <input name="web_server_use_public_url" type="checkbox" ${settings.web_server_use_public_url ? "checked" : ""}>
                <span>Utiliser l'URL publique</span>
            </label>
            <p id="modal-webserver-feedback" class="muted inventory-feedback"></p>
            <div class="modal-actions">
                <button class="toolbar-btn" type="button" data-action="modal:close">Annuler</button>
                <button class="primary-btn" type="submit">Enregistrer</button>
            </div>
        </form>
    `;
}

async function applySettingsPatch(patch, feedbackElementId = "") {
    const current = await requestJson("/settings");
    const payload = { ...current, ...patch };
    const feedback = feedbackElementId ? document.getElementById(feedbackElementId) : null;
    if (feedback) {
        feedback.textContent = "Enregistrement...";
    }
    await requestJson("/settings", {
        method: "PUT",
        body: JSON.stringify(payload),
    });
    await loadUiConfig();
    await refreshSnapshot();
    if (feedback) {
        feedback.textContent = "Parametres enregistres.";
    }
}

function buildConfigFilesManagerMarkup(device) {
    const configEnabled = Boolean(typeMeta(device.device_type)?.config_backups_enabled);
    return `
        <section class="modal-form">
            <div class="section-head slim-head">
                <h3>${escapeHtml(typeLabel(device.device_type))} / ${escapeHtml(device.name)}</h3>
                <span id="modal-config-files-state" class="muted">Chargement...</span>
            </div>
            <div id="modal-config-files-list" class="modal-log-list"></div>
            <p id="modal-config-files-feedback" class="muted inventory-feedback"></p>
            <div class="modal-actions">
                <button class="toolbar-btn" type="button" data-action="modal:close">Fermer</button>
                <button class="toolbar-btn" type="button" data-action="config-modal:refresh" ${configEnabled ? "" : "disabled"}>Actualiser</button>
                <button class="toolbar-btn" type="button" data-action="config-modal:download" ${configEnabled ? "" : "disabled"}>Telecharger</button>
                <button class="primary-btn" type="button" data-action="config-modal:import" ${configEnabled ? "" : "disabled"}>Importer</button>
            </div>
        </section>
    `;
}

async function refreshConfigFilesManagerModal() {
    const stateNode = document.getElementById("modal-config-files-state");
    const listNode = document.getElementById("modal-config-files-list");
    if (!stateNode || !listNode) {
        return;
    }
    const device = configManagerDevice();
    if (!device) {
        stateNode.textContent = "Indisponible";
        listNode.innerHTML = `<div class="error-text">Equipement introuvable.</div>`;
        return;
    }
    const meta = typeMeta(device.device_type);
    if (!meta?.config_backups_enabled) {
        stateNode.textContent = "Non disponible";
        listNode.innerHTML = `<div class="muted">Aucune gestion de configuration pour ce type.</div>`;
        return;
    }
    stateNode.textContent = "Chargement...";
    listNode.innerHTML = "";
    try {
        const params = new URLSearchParams({
            device_type_label: typeLabel(device.device_type),
            device_name: device.name,
        });
        const rows = await requestJson(`/config-files?${params.toString()}`);
        const liveStateNode = document.getElementById("modal-config-files-state");
        const liveListNode = document.getElementById("modal-config-files-list");
        if (!liveStateNode || !liveListNode || deviceKey(device) !== state.configManagerDeviceKey) {
            return;
        }
        if (!rows.length) {
            liveStateNode.textContent = "Aucun fichier";
            liveListNode.innerHTML = `<div class="muted">Aucune version locale disponible.</div>`;
            return;
        }
        liveStateNode.textContent = `${rows.length} fichier(s)`;
        liveListNode.innerHTML = rows
            .map((row) => `
                <article class="log-item">
                    <div class="config-item-title">${escapeHtml(row.name)}</div>
                    <div class="config-item-meta">${escapeHtml(row.modified_at)}</div>
                    ${row.detail ? `<div class="log-item-body">${escapeHtml(row.detail)}</div>` : ""}
                </article>
            `)
            .join("");
    } catch (error) {
        const liveStateNode = document.getElementById("modal-config-files-state");
        const liveListNode = document.getElementById("modal-config-files-list");
        if (!liveStateNode || !liveListNode || deviceKey(device) !== state.configManagerDeviceKey) {
            return;
        }
        liveStateNode.textContent = "Erreur";
        liveListNode.innerHTML = `<div class="error-text">${escapeHtml(normalizeErrorMessage(error.message))}</div>`;
    }
}

function setConfigFilesModalFeedback(message = "") {
    const feedback = document.getElementById("modal-config-files-feedback");
    if (feedback) {
        feedback.textContent = String(message || "");
    }
}

async function openConfigFilesManagerModal(device) {
    state.configManagerDeviceKey = deviceKey(device);
    openModal(
        "Gestion des fichiers de configuration",
        buildConfigFilesManagerMarkup(device),
        { width: "min(900px, calc(100vw - 40px))" },
    );
    await refreshConfigFilesManagerModal();
}

async function openNotificationSettingsModal() {
    const settings = await requestJson("/settings");
    openModal("Notifications (email + popup)", buildNotificationSettingsMarkup(settings), {
        width: "min(860px, calc(100vw - 40px))",
    });
}

async function openWebServerSettingsModal() {
    const settings = await requestJson("/settings");
    openModal("Parametres serveur web", buildWebServerSettingsMarkup(settings), {
        width: "min(860px, calc(100vw - 40px))",
    });
}

async function loadConfigStorageState() {
    try {
        state.configStorageState = await requestJson("/config-storage/state");
    } catch (_error) {
        state.configStorageState = {
            mode: "local",
            can_open_backup_folder: false,
            has_smb_password: false,
            message: "Etat indisponible",
        };
    }
    return state.configStorageState;
}

function buildConfigStorageSettingsMarkup(settings, storageState) {
    const mode = String(settings.config_storage_mode || "local").trim().toLowerCase();
    return `
        <form id="modal-config-storage-form" class="modal-form">
            <div class="modal-settings-grid">
                ${createFieldMarkup({
                    key: "config_storage_mode",
                    label: "Mode",
                    value: mode,
                    options: [
                        { value: "local", label: "Dossier local" },
                        { value: "smb3", label: "Dossier reseau SMB3" },
                    ],
                })}
                ${createFieldMarkup({ key: "switch_configs_dir", label: "Chemin local", value: settings.switch_configs_dir || "", wide: true })}
                ${createFieldMarkup({ key: "config_smb_unc_path", label: "Chemin UNC SMB3", value: settings.config_smb_unc_path || "", wide: true })}
                ${createFieldMarkup({ key: "config_smb_username", label: "Utilisateur SMB", value: settings.config_smb_username || "" })}
                ${createFieldMarkup({ key: "config_auto_sync_interval_seconds", label: "Intervalle auto (s)", value: settings.config_auto_sync_interval_seconds || 3600 })}
            </div>
            <label class="check-field">
                <input name="config_auto_sync_enabled" type="checkbox" ${settings.config_auto_sync_enabled ? "checked" : ""}>
                <span>Sauvegarde automatique</span>
            </label>
            <p class="muted">Mot de passe SMB configure: ${storageState?.has_smb_password ? "Oui" : "Non (a configurer depuis le desktop)"}</p>
            <p id="modal-config-storage-feedback" class="muted inventory-feedback"></p>
            <div class="modal-actions">
                <button class="toolbar-btn" type="button" data-action="modal:close">Annuler</button>
                <button class="primary-btn" type="submit">Enregistrer</button>
            </div>
        </form>
    `;
}

async function openConfigStorageSettingsModal() {
    const [settings, storageState] = await Promise.all([
        requestJson("/settings"),
        loadConfigStorageState(),
    ]);
    openModal("Configurer sauvegarde", buildConfigStorageSettingsMarkup(settings, storageState), {
        width: "min(920px, calc(100vw - 40px))",
    });
}

async function submitConfigStorageSettings(form) {
    const formData = new window.FormData(form);
    const mode = String(formData.get("config_storage_mode") || "local").trim().toLowerCase();
    const intervalRaw = Number(formData.get("config_auto_sync_interval_seconds") || 3600);
    const interval = Number.isFinite(intervalRaw) ? Math.max(5, Math.trunc(intervalRaw)) : 3600;
    await applySettingsPatch(
        {
            config_storage_mode: mode === "smb3" ? "smb3" : "local",
            switch_configs_dir: String(formData.get("switch_configs_dir") || "").trim(),
            config_smb_unc_path: String(formData.get("config_smb_unc_path") || "").trim(),
            config_smb_username: String(formData.get("config_smb_username") || "").trim(),
            config_auto_sync_enabled: form.querySelector('[name="config_auto_sync_enabled"]')?.checked ?? false,
            config_auto_sync_interval_seconds: interval,
        },
        "modal-config-storage-feedback",
    );
    await loadConfigStorageState();
    window.setTimeout(() => closeModal(), 400);
}

function messagePathToFileUrl(message) {
    const text = String(message || "");
    const marker = ":";
    const idx = text.indexOf(marker);
    if (idx < 0) {
        return "";
    }
    const rawPath = text.slice(idx + marker.length).trim();
    if (!rawPath) {
        return "";
    }
    if (rawPath.startsWith("\\\\")) {
        const unc = rawPath.replaceAll("\\", "/");
        return `file:${unc}`;
    }
    if (/^[a-zA-Z]:\\/.test(rawPath)) {
        const winPath = rawPath.replaceAll("\\", "/");
        return `file:///${winPath}`;
    }
    return "";
}

async function runConfigStorageAction(path, options = {}) {
    try {
        const result = await requestJson(path, { method: "POST" });
        await loadConfigStorageState();
        if (options.openClientPath) {
            const fileUrl = messagePathToFileUrl(result?.message || "");
            if (fileUrl) {
                window.open(fileUrl, "_blank", "noopener,noreferrer");
            }
        }
        inventoryFeedback.textContent = "Operation terminee.";
    } catch (error) {
        openModal(
            "Fichiers de configuration",
            `
                <section class="modal-section">
                    <p class="error-text">${escapeHtml(normalizeErrorMessage(error.message))}</p>
                </section>
            `,
            { width: "min(620px, calc(100vw - 40px))" },
        );
    }
}

function buildDeviceTypesSettingsMarkup(types) {
    const rows = (types || []).map((item) => {
        const code = String(item.code || "");
        const canDelete = !Boolean(item.is_system);
        return `
            <tr data-type-code="${escapeAttribute(code)}">
                <td><code>${escapeHtml(code)}</code></td>
                <td>
                    <input data-field="label" type="text" value="${escapeAttribute(item.label || "")}" />
                </td>
                <td class="cell-center">
                    <input data-field="monitoring_enabled" type="checkbox" ${item.monitoring_enabled ? "checked" : ""} />
                </td>
                <td class="cell-center">
                    <input data-field="config_backups_enabled" type="checkbox" ${item.config_backups_enabled ? "checked" : ""} />
                </td>
                <td class="cell-actions">
                    <button class="toolbar-btn" type="button" data-action="types:save" data-type-code="${escapeAttribute(code)}">Enregistrer</button>
                    <button class="toolbar-btn" type="button" data-action="types:delete" data-type-code="${escapeAttribute(code)}" ${canDelete ? "" : "disabled"}>Supprimer</button>
                </td>
            </tr>
        `;
    }).join("");
    return `
        <section class="modal-section">
            <h3>Creer un type</h3>
            <form id="modal-device-type-create-form" class="modal-form compact-create-form">
                <div class="modal-settings-grid">
                    ${createFieldMarkup({ key: "label", label: "Libelle", value: "" })}
                </div>
                <label class="check-field">
                    <input name="monitoring_enabled" type="checkbox" checked>
                    <span>Type monitorable</span>
                </label>
                <label class="check-field">
                    <input name="config_backups_enabled" type="checkbox">
                    <span>Sauvegardes de configuration</span>
                </label>
                <div class="modal-actions">
                    <button class="primary-btn" type="submit">Ajouter</button>
                </div>
            </form>
        </section>
        <section class="modal-section">
            <h3>Types existants</h3>
            <div class="table-wrap">
                <table class="device-table">
                    <thead>
                    <tr>
                        <th>Code</th>
                        <th>Libelle</th>
                        <th>Monitoring</th>
                        <th>Configs</th>
                        <th>Actions</th>
                    </tr>
                    </thead>
                    <tbody id="device-types-body">
                    ${rows}
                    </tbody>
                </table>
            </div>
            <p id="modal-device-types-feedback" class="muted inventory-feedback"></p>
        </section>
    `;
}

async function openDeviceTypesModal() {
    const types = await requestJson("/device-types");
    openModal("Types d'equipements", buildDeviceTypesSettingsMarkup(types), {
        width: "min(980px, calc(100vw - 40px))",
    });
}

async function openInventoryEditMode(device = getSelectedDevice(), options = {}) {
    const mode = options.mode || "edit";
    const targetType = options.deviceType || device?.device_type || inventoryTypeFilter.value || state.deviceTypes[0]?.code || "";
    if (!targetType) {
        inventoryFormFeedback.textContent = "Aucun type disponible.";
        return;
    }
    inventoryFormFeedback.textContent = "";
    state.inventoryFormMode = mode;
    await ensureDeviceTypeSchema(targetType);
    const customFields = customFieldDefinitions(targetType);
    const current = device || {
        name: "",
        ip: "",
        description: "",
        id_Teamviewer: "",
        device_subtype: "",
        action_double_click: "",
        web_url: "",
        ssh_user: "",
        notify: true,
        custom_data: {},
        device_type: targetType,
    };
    const typeField = mode === "create"
        ? `
            <label class="field">
                <span>Type</span>
                <select name="device_type">
                    ${state.deviceTypes.map((item) => `<option value="${escapeHtml(item.code)}"${item.code === targetType ? " selected" : ""}>${escapeHtml(item.label)}</option>`).join("")}
                </select>
            </label>
        `
        : "";
    inventoryEditFields.innerHTML = [
        typeField,
        createFieldMarkup({ key: "name", label: fieldLabel("name"), value: current.name }),
        createFieldMarkup({ key: "ip", label: fieldLabel("ip"), value: current.ip }),
        createFieldMarkup({ key: "description", label: fieldLabel("description"), value: current.description, multiline: true, wide: true }),
        createFieldMarkup({ key: "id_Teamviewer", label: fieldLabel("id_Teamviewer"), value: current.id_Teamviewer }),
        createFieldMarkup({ key: "device_subtype", label: fieldLabel("device_subtype"), value: current.device_subtype }),
        createFieldMarkup({ key: "action_double_click", label: fieldLabel("action_double_click"), value: current.action_double_click }),
        createFieldMarkup({ key: "web_url", label: fieldLabel("web_url"), value: current.web_url }),
        createFieldMarkup({ key: "ssh_user", label: fieldLabel("ssh_user"), value: current.ssh_user }),
        ...customFields.map((field) => createFieldMarkup({
            key: `custom:${field.field_key}`,
            label: fieldLabel(field.field_key, field.label),
            value: current.custom_data?.[field.field_key] || "",
            multiline: String(field.field_kind || "").toLowerCase() === "textarea",
            wide: String(field.field_kind || "").toLowerCase() === "textarea",
        })),
    ].join("");
    inventoryNotify.checked = Boolean(current.notify);
    inventoryEditForm.hidden = false;
    inventoryCancelButton.hidden = false;
    inventorySaveButton.textContent = mode === "create" ? "Ajouter" : "Enregistrer";
    inventoryEditForm.dataset.mode = mode;
}

async function openDeviceModal(device = getSelectedDevice(), options = {}) {
    const mode = options.mode || "edit";
    const targetType = options.deviceType || device?.device_type || inventoryTypeFilter.value || state.deviceTypes[0]?.code || "";
    if (!targetType) {
        inventoryFeedback.textContent = "Aucun type disponible.";
        return;
    }
    await ensureDeviceTypeSchema(targetType);
    const current = device || {
        name: "",
        ip: "",
        description: "",
        id_Teamviewer: "",
        device_subtype: "",
        action_double_click: "",
        web_url: "",
        ssh_user: "",
        notify: true,
        custom_data: {},
        device_type: targetType,
    };
    openModal(mode === "create" ? "Ajouter un equipement" : `Modifier ${current.name}`, buildDeviceFormMarkup(current, mode, targetType));
    const form = document.getElementById("modal-device-form");
    form.dataset.mode = mode;
    form.dataset.deviceType = current.device_type || targetType;
    form.dataset.deviceId = current.id || "";
}

async function openLogsModal(options = {}) {
    const params = new URLSearchParams({ limit: String(options.limit || 100) });
    if (options.device_type) {
        params.set("device_type", options.device_type);
    }
    if (options.device_id) {
        params.set("device_id", options.device_id);
    }
    const rows = await requestJson(`/logs?${params.toString()}`);
    openModal(options.title || "Journaux", buildLogsModalMarkup(rows, { heading: options.heading || options.title || "Journaux" }), {
        width: "min(1040px, calc(100vw - 40px))",
    });
}

async function openMonitoringSettingsModal() {
    const settings = await requestJson("/settings");
    openModal("Parametres de monitoring", buildMonitoringSettingsMarkup(settings), {
        width: "min(820px, calc(100vw - 40px))",
    });
}

function closeInventoryEditMode() {
    inventoryEditForm.hidden = true;
    inventoryCancelButton.hidden = true;
}

function createMenuButton(label, action, hint = "", disabled = false) {
    return `
        <button
            class="context-menu-item"
            type="button"
            data-action="${escapeAttribute(action)}"
            ${disabled ? "disabled" : ""}
        >
            <span>${escapeHtml(label)}</span>
            <span class="context-menu-hint">${escapeHtml(hint)}</span>
        </button>
    `;
}

function createSubmenu(label, itemsMarkup, disabled = false) {
    return `
        <div class="context-menu-submenu">
            <button class="context-menu-summary" type="button" ${disabled ? "disabled" : ""}>
                <span>${escapeHtml(label)}</span>
                <span class="context-menu-hint">${disabled ? "Indisponible" : ">"}</span>
            </button>
            ${disabled ? "" : `<div class="context-menu-submenu-panel">${itemsMarkup}</div>`}
        </div>
    `;
}

function createTopMenuEntry(label, action = "", disabled = false) {
    return createMenuButton(label, action, "", disabled);
}

function topMenuDefinitions() {
    const typeLogs = (state.deviceTypes || [])
        .map((item) => ({
            label: `Journal ${item.label}...`,
            action: `menu:logs:type:${item.code}`,
        }));
    const configState = state.configStorageState || {};
    const canOpenBackup = Boolean(configState.can_open_backup_folder);
    return {
        supervision: [
            { label: "Notifications (email + popup)...", action: "menu:notifications" },
            { label: "Parametres de monitoring...", action: "menu:monitoring" },
            { label: "Parametres serveur web...", action: "menu:web" },
            { label: "Exporter le certificat HTTPS...", action: "menu:cert", disabled: true },
            {
                label: "Journaux",
                items: [
                    { label: "Journal global des changements...", action: "menu:logs:global" },
                    ...typeLogs,
                ],
            },
            { label: "Mises a jour...", action: "menu:updates", disabled: true },
        ],
        equipments: [
            { label: "Inventaire detaille", action: "view:inventory" },
            { label: "Types d'equipements...", action: "menu:types" },
            {
                label: "Fichiers de configuration",
                items: [
                    { label: "Ouvrir dossier de configuration", action: "menu:config-open-local" },
                    { label: "Ouvrir dossier de sauvegarde", action: "menu:config-open-backup", disabled: !canOpenBackup },
                    { label: "Configurer sauvegarde...", action: "menu:config-storage" },
                    { label: "Sauvegarder maintenant", action: "menu:config-sync", disabled: !canOpenBackup },
                ],
            },
        ],
        display: [
            {
                label: "Theme",
                items: [
                    { label: "Clair", action: "menu:theme-light" },
                    { label: "Sombre", action: "menu:theme-dark" },
                ],
            },
            {
                label: "Indicateurs de statut",
                items: [
                    { label: "Badge coche / croix", action: "menu:status-badge" },
                    { label: "Pastille moderne", action: "menu:status-dot" },
                ],
            },
            { label: "Image de fond...", action: "menu:watermark", disabled: true },
        ],
        help: [
            { label: "A propos...", action: "menu:about" },
        ],
    };
}

function renderTopMenuEntry(entry) {
    if (Array.isArray(entry?.items) && entry.items.length) {
        const itemsMarkup = entry.items
            .map((item) => createTopMenuEntry(item.label, item.action, Boolean(item.disabled)))
            .join("");
        return createSubmenu(entry.label, itemsMarkup, Boolean(entry.disabled));
    }
    return createTopMenuEntry(entry.label, entry.action, Boolean(entry.disabled));
}

function topMenuMarkup(menuKey) {
    const definitions = topMenuDefinitions();
    const entries = definitions[menuKey] || definitions.help;
    return `
        <div class="context-menu-group">
            ${entries.map((entry) => renderTopMenuEntry(entry)).join("")}
        </div>
    `;
}

async function openTopMenu(button, menuKey) {
    if (state.openTopMenu === menuKey && !topMenuPanel.hidden) {
        closeTopMenu();
        return;
    }
    if (menuKey === "equipments") {
        await loadConfigStorageState();
    }
    closeContextMenu();
    state.openTopMenu = menuKey;
    topMenuPanel.innerHTML = topMenuMarkup(menuKey);
    topMenuPanel.hidden = false;
    [menuSupervision, menuEquipments, menuDisplay, menuHelp].forEach((entry) => {
        entry.classList.toggle("active", entry === button);
    });
    const rect = button.getBoundingClientRect();
    topMenuPanel.style.left = `${Math.max(8, rect.left)}px`;
    topMenuPanel.style.top = `${rect.bottom + 4}px`;
}

async function buildContextMenuMarkup(device) {
    const schema = await ensureDeviceTypeSchema(device.device_type);
    const configEnabled = Boolean(typeMeta(device.device_type)?.config_backups_enabled);
    const dynamicActions = (schema.actions || [])
        .filter((item) => ["builtin"].includes(String(item.target_kind || "").trim().toLowerCase()))
        .map((item) => {
            const builtin = String(item.target_value || item.action_key || "").trim().toLowerCase();
            const label = String(item.label || item.action_key || "").trim() || builtin;
            const supported = ["teamviewer", "web"].includes(builtin);
            return createMenuButton(label, `builtin:${builtin}`, "", !supported || !canRunBuiltinAction(device, builtin));
        })
        .join("");

    const configMenu = createSubmenu(
        "Fichiers de configuration",
        [
            createMenuButton("Telecharger", "config:download", "", !configEnabled),
            createMenuButton("Importer un fichier de conf", "config:import", "", !configEnabled),
            createMenuButton("Gestion des fichiers", "config:manage", "", !configEnabled),
        ].join(""),
        !configEnabled,
    );

    const toolsMenu = createSubmenu(
        "Outils reseau",
        [
            createMenuButton("Ping", "tool:ping", "", true),
            createMenuButton("Port check", "tool:port", "", true),
            createMenuButton("Traceroute", "tool:traceroute", "", true),
            createMenuButton("DNS lookup", "tool:dns", "", true),
            createMenuButton("HTTP(S) check (avec certificat)", "tool:http", "", true),
            createMenuButton("SNMP", "tool:snmp", "", true),
        ].join(""),
        false,
    );
    const copyMenu = createSubmenu(
        "Copier",
        [
            createMenuButton("Nom", "device:copy-name"),
            createMenuButton("IP", "device:copy-ip"),
        ].join(""),
        false,
    );

    return `
        <div class="context-menu-group">
            ${dynamicActions}
            ${dynamicActions ? '<div class="context-menu-sep"></div>' : ""}
            ${createMenuButton("Ajouter", "device:add")}
            ${createMenuButton("Modifier", "device:edit")}
            ${createMenuButton("Supprimer", "device:delete")}
        </div>
        <div class="context-menu-group">
            ${createMenuButton(
                "Alerte sur changement de statut",
                "device:notify",
                device.notify ? "Oui" : "Non",
            )}
            ${createMenuButton("Afficher logs", "device:logs")}
            ${copyMenu}
        </div>
        <div class="context-menu-group">
            ${configMenu}
            ${toolsMenu}
        </div>
    `;
}

async function openContextMenu(x, y, device) {
    state.contextMenuDeviceKey = deviceKey(device);
    contextMenu.innerHTML = await buildContextMenuMarkup(device);
    contextMenu.hidden = false;
    const maxX = window.innerWidth - contextMenu.offsetWidth - 12;
    const maxY = window.innerHeight - contextMenu.offsetHeight - 12;
    contextMenu.style.left = `${Math.max(8, Math.min(x, maxX))}px`;
    contextMenu.style.top = `${Math.max(8, Math.min(y, maxY))}px`;
}

function buildInventoryBackgroundContextMenuMarkup() {
    const preferredType = String(inventoryTypeFilter.value || "").trim()
        || String(state.deviceTypes?.[0]?.code || "").trim();
    const canCreate = Boolean(preferredType);
    const addAction = canCreate ? `device:add-type:${preferredType}` : "device:add";
    return `
        <div class="context-menu-group">
            ${createMenuButton("Ajouter", addAction, canCreate ? typeLabel(preferredType) : "", !canCreate)}
        </div>
    `;
}

function openInventoryBackgroundContextMenu(x, y) {
    state.contextMenuDeviceKey = "";
    contextMenu.innerHTML = buildInventoryBackgroundContextMenuMarkup();
    contextMenu.hidden = false;
    const maxX = window.innerWidth - contextMenu.offsetWidth - 12;
    const maxY = window.innerHeight - contextMenu.offsetHeight - 12;
    contextMenu.style.left = `${Math.max(8, Math.min(x, maxX))}px`;
    contextMenu.style.top = `${Math.max(8, Math.min(y, maxY))}px`;
}

async function copyToClipboard(value, successLabel) {
    try {
        await navigator.clipboard.writeText(String(value || ""));
        inventoryFeedback.textContent = `${successLabel} copie.`;
    } catch (_error) {
        inventoryFeedback.textContent = "Copie impossible depuis ce navigateur.";
    }
}

async function toggleDeviceNotify(device) {
    await requestJson(`/devices/${encodeURIComponent(device.device_type)}/${encodeURIComponent(device.id)}`, {
        method: "PUT",
        body: JSON.stringify({
            name: device.name,
            ip: device.ip,
            description: device.description,
            id_Teamviewer: device.id_Teamviewer || "",
            device_subtype: device.device_subtype || "",
            action_double_click: device.action_double_click || "",
            web_url: device.web_url || "",
            ssh_user: device.ssh_user || "",
            custom_data: device.custom_data || {},
            notify: !device.notify,
        }),
    });
    await loadInventory();
    renderInventoryDetail();
}

async function deleteDevice(device) {
    const confirmed = window.confirm(`Supprimer ${typeLabel(device.device_type)} "${device.name}" ?`);
    if (!confirmed) {
        return;
    }
    await requestJson(`/devices/${encodeURIComponent(device.device_type)}/${encodeURIComponent(device.id)}`, {
        method: "DELETE",
    });
    await loadInventory();
    renderInventoryDetail();
}

function serializeDeviceForm(form) {
    const formData = new window.FormData(form);
    const customData = {};
    for (const [key, value] of formData.entries()) {
        if (String(key).startsWith("custom:")) {
            customData[String(key).slice(7)] = String(value || "");
        }
    }
    const deviceType = String(formData.get("device_type") || "").trim();
    return {
        device_type: deviceType,
        payload: {
            name: String(formData.get("name") || "").trim(),
            ip: String(formData.get("ip") || "").trim(),
            description: String(formData.get("description") || "").trim(),
            id_Teamviewer: String(formData.get("id_Teamviewer") || "").trim(),
            device_subtype: String(formData.get("device_subtype") || "").trim(),
            action_double_click: String(formData.get("action_double_click") || "").trim(),
            web_url: String(formData.get("web_url") || "").trim(),
            ssh_user: String(formData.get("ssh_user") || "").trim(),
            custom_data: customData,
            notify: form.querySelector('[name="notify"]')?.checked ?? true,
        },
    };
}

async function submitDeviceModal(form) {
    const mode = form.dataset.mode || "edit";
    const { device_type: createdType, payload } = serializeDeviceForm(form);
    const feedback = document.getElementById("modal-device-feedback");
    feedback.textContent = "Enregistrement...";
    const deviceId = String(form.dataset.deviceId || "");
    const editType = String(form.dataset.deviceType || "");
    try {
        if (mode === "create") {
            await requestJson("/devices", {
                method: "POST",
                body: JSON.stringify({
                    ...payload,
                    device_type: createdType || editType,
                }),
            });
        } else {
            await requestJson(`/devices/${encodeURIComponent(editType)}/${encodeURIComponent(deviceId)}`, {
                method: "PUT",
                body: JSON.stringify(payload),
            });
        }
        await loadInventory();
        await refreshSnapshot();
        renderInventoryDetail();
        closeModal();
    } catch (error) {
        feedback.textContent = normalizeErrorMessage(error.message);
    }
}

async function submitMonitoringSettings(form) {
    const current = await requestJson("/settings");
    const formData = new window.FormData(form);
    const payload = {
        ...current,
        offline_delay_seconds: Number(formData.get("offline_delay_seconds") || current.offline_delay_seconds),
        online_recovery_delay_seconds: Number(formData.get("online_recovery_delay_seconds") || current.online_recovery_delay_seconds),
        notification_cooldown_seconds: Number(formData.get("notification_cooldown_seconds") || current.notification_cooldown_seconds),
        failures_for_offline: Number(formData.get("failures_for_offline") || current.failures_for_offline),
        successes_for_online: Number(formData.get("successes_for_online") || current.successes_for_online),
        ping_timeout_ms: Number(formData.get("ping_timeout_ms") || current.ping_timeout_ms),
        probe_interval_ms: Number(formData.get("probe_interval_ms") || current.probe_interval_ms),
        ui_theme: String(formData.get("ui_theme") || current.ui_theme),
        log_diagnostic_events: form.querySelector('[name="log_diagnostic_events"]')?.checked ?? current.log_diagnostic_events,
        show_status_popup: form.querySelector('[name="show_status_popup"]')?.checked ?? current.show_status_popup,
    };
    const feedback = document.getElementById("modal-settings-feedback");
    feedback.textContent = "Enregistrement...";
    try {
        await requestJson("/settings", {
            method: "PUT",
            body: JSON.stringify(payload),
        });
        await loadUiConfig();
        await refreshSnapshot();
        feedback.textContent = "Parametres enregistres.";
        window.setTimeout(() => closeModal(), 400);
    } catch (error) {
        feedback.textContent = normalizeErrorMessage(error.message);
    }
}

async function downloadLatestDeviceConfig(device) {
    const params = new URLSearchParams({
        device_type: String(device.device_type || ""),
        device_name: String(device.name || ""),
        device_ip: String(device.ip || ""),
    });
    const response = await fetch(`/config-files/latest-download?${params.toString()}`, {
        method: "GET",
        headers: {
            ...headers(),
        },
    });
    if (!response.ok) {
        let detail = `${response.status} ${response.statusText}`;
        try {
            const body = await response.json();
            detail = body.detail || body.message || detail;
        } catch (_error) {
        }
        throw new Error(normalizeErrorMessage(detail));
    }
    const blob = await response.blob();
    const disposition = String(response.headers.get("Content-Disposition") || "");
    const match = disposition.match(/filename=\"?([^\";]+)\"?/i);
    const filename = (match && match[1]) ? match[1] : "config.cfg";
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
}

async function importDeviceConfigFromFile(device) {
    const picker = document.createElement("input");
    picker.type = "file";
    picker.accept = ".cfg,.conf,.txt,*/*";
    const file = await new Promise((resolve) => {
        picker.addEventListener("change", () => resolve(picker.files && picker.files[0] ? picker.files[0] : null), { once: true });
        picker.click();
    });
    if (!file) {
        return;
    }
    const contentBase64 = await new Promise((resolve, reject) => {
        const reader = new window.FileReader();
        reader.onload = () => {
            const result = String(reader.result || "");
            const marker = "base64,";
            const idx = result.indexOf(marker);
            if (idx < 0) {
                reject(new Error("Encodage fichier impossible."));
                return;
            }
            resolve(result.slice(idx + marker.length));
        };
        reader.onerror = () => reject(new Error("Lecture fichier impossible."));
        reader.readAsDataURL(file);
    });
    await requestJson("/config-files/import", {
        method: "POST",
        body: JSON.stringify({
            device_type: String(device.device_type || ""),
            device_name: String(device.name || ""),
            filename: String(file.name || "import.cfg"),
            content_base64: String(contentBase64 || ""),
            detail: "Import web",
        }),
    });
    inventoryFeedback.textContent = "Fichier de configuration importe.";
    await loadInventoryConfigs(device);
}

async function submitNotificationSettings(form) {
    const formData = new window.FormData(form);
    const smtpPort = Number(formData.get("smtp_port") || 0);
    await applySettingsPatch(
        {
            smtp_host: String(formData.get("smtp_host") || "").trim(),
            smtp_port: Number.isFinite(smtpPort) ? smtpPort : 0,
            user: String(formData.get("user") || "").trim(),
            recipients: String(formData.get("recipients") || "").trim(),
            use_tls: form.querySelector('[name="use_tls"]')?.checked ?? false,
            show_status_popup: form.querySelector('[name="show_status_popup"]')?.checked ?? true,
        },
        "modal-notification-feedback",
    );
    window.setTimeout(() => closeModal(), 400);
}

async function submitWebServerSettings(form) {
    const formData = new window.FormData(form);
    const parsedPort = Number(formData.get("web_server_port") || 8000);
    const port = Number.isFinite(parsedPort) ? Math.max(1, Math.min(65535, Math.trunc(parsedPort))) : 8000;
    await applySettingsPatch(
        {
            web_server_host: String(formData.get("web_server_host") || "127.0.0.1").trim() || "127.0.0.1",
            web_server_port: port,
            web_server_autostart: form.querySelector('[name="web_server_autostart"]')?.checked ?? false,
            web_server_public_url: String(formData.get("web_server_public_url") || "").trim(),
            web_server_use_public_url: form.querySelector('[name="web_server_use_public_url"]')?.checked ?? false,
        },
        "modal-webserver-feedback",
    );
    window.setTimeout(() => closeModal(), 400);
}

function typeRowPayload(row) {
    const labelInput = row.querySelector('[data-field="label"]');
    const monitoringInput = row.querySelector('[data-field="monitoring_enabled"]');
    const configInput = row.querySelector('[data-field="config_backups_enabled"]');
    return {
        label: String(labelInput?.value || "").trim(),
        monitoring_enabled: Boolean(monitoringInput?.checked),
        config_backups_enabled: Boolean(configInput?.checked),
    };
}

async function submitCreateDeviceType(form) {
    const feedback = document.getElementById("modal-device-types-feedback");
    const formData = new window.FormData(form);
    const payload = {
        label: String(formData.get("label") || "").trim(),
        monitoring_enabled: form.querySelector('[name="monitoring_enabled"]')?.checked ?? true,
        config_backups_enabled: form.querySelector('[name="config_backups_enabled"]')?.checked ?? false,
    };
    if (!payload.label) {
        feedback.textContent = "Libelle requis.";
        return;
    }
    feedback.textContent = "Creation...";
    await requestJson("/device-types", {
        method: "POST",
        body: JSON.stringify(payload),
    });
    await loadDeviceTypes();
    await refreshSnapshot();
    feedback.textContent = "Type ajoute.";
    await openDeviceTypesModal();
}

async function saveDeviceTypeRow(typeCode) {
    const feedback = document.getElementById("modal-device-types-feedback");
    const row = Array.from(appModalBody.querySelectorAll("tr[data-type-code]"))
        .find((item) => String(item.dataset.typeCode || "") === String(typeCode || ""));
    if (!row) {
        return;
    }
    const payload = typeRowPayload(row);
    if (!payload.label) {
        feedback.textContent = "Libelle requis.";
        return;
    }
    feedback.textContent = `Mise a jour ${typeCode}...`;
    await requestJson(`/device-types/${encodeURIComponent(typeCode)}`, {
        method: "PUT",
        body: JSON.stringify(payload),
    });
    await loadDeviceTypes();
    await refreshSnapshot();
    feedback.textContent = `Type ${typeCode} mis a jour.`;
}

async function deleteDeviceTypeRow(typeCode) {
    const feedback = document.getElementById("modal-device-types-feedback");
    if (!window.confirm(`Supprimer le type "${typeCode}" ?`)) {
        return;
    }
    feedback.textContent = `Suppression ${typeCode}...`;
    await requestJson(`/device-types/${encodeURIComponent(typeCode)}?cascade_devices=false`, {
        method: "DELETE",
    });
    await loadDeviceTypes();
    await refreshSnapshot();
    feedback.textContent = `Type ${typeCode} supprime.`;
    await openDeviceTypesModal();
}

function renderSection() {
    const summary = state.snapshot?.summary || {};
    const runningAny = Boolean(summary.running_any);
    renderNavigation(state.snapshot?.types || []);

    if (state.currentSection === "inventory") {
        detailPanel.classList.remove("detail-focus-mode");
        cardsGrid.hidden = true;
        monitoringToolbar.hidden = true;
        placeholderPanel.hidden = true;
        detailPanel.hidden = false;
        supervisionSection.hidden = true;
        inventorySection.hidden = false;
        runtimeStrip.hidden = true;
        detailTitle.textContent = "Equipements";
        renderInventoryFilters();
        renderInventoryDetail();
        return;
    }

    const dashboardMode = state.currentView === "dashboard";
    cardsGrid.hidden = !dashboardMode;
    monitoringToolbar.hidden = !dashboardMode;
    supervisionSection.hidden = false;
    inventorySection.hidden = true;
    runtimeStrip.hidden = !dashboardMode;
    if (dashboardMode) {
        renderCards(state.snapshot || { summary: {}, types: [] });
        renderMonitoringToolbar(state.snapshot?.types || [], summary);
    }
    if (dashboardMode) {
        renderTypes(state.snapshot?.types || []);
    }
    devicesSection.hidden = false;
    if (!runningAny && state.currentView === "dashboard") {
        detailPanel.hidden = true;
        placeholderPanel.hidden = false;
        return;
    }
    placeholderPanel.hidden = true;
    detailPanel.hidden = false;
    applyCurrentView();
}

function renderSnapshot(snapshot) {
    state.snapshot = snapshot;
    const summary = snapshot.summary || {};
    document.getElementById("runtime-running").textContent = summary.running_any ? "Oui" : "Non";
    document.getElementById("runtime-types").textContent = String((summary.running_types || []).length);
    renderSection();
}

function snapshotTypeSignature(snapshot) {
    const rows = Array.isArray(snapshot?.types) ? snapshot.types : [];
    const normalized = rows
        .map((item) => [
            String(item.type_code || "").trim().toLowerCase(),
            String(item.label || "").trim(),
            Boolean(item.monitoring_enabled),
            Boolean(item.config_backups_enabled),
        ])
        .sort((a, b) => `${a[0]}:${a[1]}`.localeCompare(`${b[0]}:${b[1]}`));
    return JSON.stringify(normalized);
}

function scheduleTypeMetadataRefreshFromSnapshot(snapshot) {
    const signature = snapshotTypeSignature(snapshot);
    if (!signature || signature === state.lastSnapshotTypeSignature) {
        return;
    }
    state.lastSnapshotTypeSignature = signature;
    if (state.typeSyncTimer) {
        window.clearTimeout(state.typeSyncTimer);
    }
    state.typeSyncTimer = window.setTimeout(async () => {
        state.typeSyncTimer = null;
        try {
            await Promise.all([loadDeviceTypes(), loadInventory()]);
            if (state.currentSection === "inventory") {
                renderInventoryDetail();
            }
        } catch (_error) {
        }
    }, 120);
}

async function refreshSnapshot() {
    const snapshot = await requestJson("/monitoring/snapshot");
    renderSnapshot(snapshot);
    scheduleTypeMetadataRefreshFromSnapshot(snapshot);
}

async function loadInventory() {
    state.inventory = await requestJson("/devices");
    ensureSelectedDevice();
    if (state.currentSection === "inventory") {
        renderInventoryDetail();
        const selected = getSelectedDevice();
        if (selected) {
            await ensureInventorySideData(selected);
        }
    }
}

async function loadDeviceTypes() {
    state.deviceTypes = await requestJson("/device-types");
    if (state.currentSection === "inventory") {
        renderInventoryFilters();
    }
}

async function refreshWorkspaceData() {
    await Promise.all([
        refreshSnapshot(),
        loadInventory(),
        loadDeviceTypes(),
    ]);
}

async function postMonitoringCommand(path) {
    await requestJson(path, { method: "POST" });
    await refreshSnapshot();
}

function startPollingLoop() {
    clearRealtimeTimers();
    state.fallbackToPolling = true;
    const run = async () => {
        if (!state.token) {
            return;
        }
        try {
            await refreshSnapshot();
            setLiveStatus("Polling");
        } catch (_error) {
            setLiveStatus("Polling en echec");
        }
        state.pollingTimer = window.setTimeout(run, 3000);
    };
    state.pollingTimer = window.setTimeout(run, 3000);
}

async function loadMonitoringCapabilities() {
    try {
        state.capabilities = await requestJson("/monitoring/capabilities");
    } catch (_error) {
        state.capabilities = { websocket_supported: false, recommended_transport: "polling" };
    }
}

async function loadUiConfig() {
    try {
        applyUiConfig(await requestJson("/ui/config"));
    } catch (_error) {
        applyUiConfig(null);
    }
}

async function loadPublicUiConfig() {
    try {
        applyUiConfig(await requestJson("/ui/auth-config", { headers: {} }));
    } catch (_error) {
        applyUiConfig(null);
    }
}

function connectWebSocket() {
    if (!state.token) {
        return;
    }
    if (state.capabilities && state.capabilities.websocket_supported === false) {
        setLiveStatus("Actualisation");
        startPollingLoop();
        return;
    }
    clearRealtimeTimers();
    if (state.websocket) {
        state.websocket.close();
    }
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/monitoring/ws?token=${encodeURIComponent(state.token)}&interval_ms=1000`;
    const websocket = new window.WebSocket(url);
    state.websocket = websocket;
    setLiveStatus("Connexion...");

    websocket.addEventListener("open", () => {
        state.fallbackToPolling = false;
        setLiveStatus("Connecte");
    });

    websocket.addEventListener("message", (event) => {
        const payload = JSON.parse(event.data);
        if (payload.event === "monitoring.snapshot") {
            renderSnapshot(payload.data);
            scheduleTypeMetadataRefreshFromSnapshot(payload.data);
        }
    });

    websocket.addEventListener("close", () => {
        state.websocket = null;
        if (!state.token) {
            setLiveStatus("Deconnecte");
            return;
        }
        if (!state.fallbackToPolling) {
            setLiveStatus("Actualisation de secours");
            startPollingLoop();
            return;
        }
        setLiveStatus("Actualisation");
    });

    websocket.addEventListener("error", () => {
        if (!state.fallbackToPolling) {
            setLiveStatus("Temps reel indisponible");
            if (state.websocket) {
                state.websocket.close();
            }
            startPollingLoop();
        }
    });
}

async function authenticate(password) {
    const mode = authForm.dataset.mode || "login";
    if (mode === "bootstrap") {
        await requestJson("/auth/bootstrap", {
            method: "POST",
            body: JSON.stringify({ password }),
            headers: {},
        });
    }
    const login = await requestJson("/auth/login", {
        method: "POST",
        body: JSON.stringify({ password }),
        headers: {},
    });
    persistToken(login.access_token);
}

async function restoreSession() {
    if (!state.token) {
        return false;
    }
    try {
        await requestJson("/auth/me");
        return true;
    } catch (_error) {
        persistToken("");
        return false;
    }
}

async function boot() {
    await loadAuthMode();
    const sessionOk = await restoreSession();
    if (!sessionOk) {
        showAuth();
        return;
    }
    await loadUiConfig();
    showDashboard();
    await loadMonitoringCapabilities();
    await refreshWorkspaceData();
    connectWebSocket();
}

authForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    setError("");
    authSubmit.disabled = true;
    try {
        await authenticate(passwordInput.value);
        passwordInput.value = "";
        await loadUiConfig();
        showDashboard();
        await loadMonitoringCapabilities();
        await refreshWorkspaceData();
        connectWebSocket();
    } catch (error) {
        teardownRealtime();
        persistToken("");
        state.snapshot = null;
        setError(normalizeErrorMessage(error.message));
        await loadAuthMode();
        showAuth();
    } finally {
        authSubmit.disabled = false;
    }
});

refreshButton.addEventListener("click", async () => {
    await refreshWorkspaceData();
});

logoutButton.addEventListener("click", async () => {
    try {
        if (state.token) {
            await requestJson("/auth/logout", { method: "POST" });
        }
    } catch (_error) {
    }
    teardownRealtime();
    persistToken("");
    state.snapshot = null;
    state.inventory = [];
    state.deviceTypes = [];
    state.deviceSchemas = {};
    state.selectedDeviceKey = "";
    state.currentView = "dashboard";
    state.currentSection = "supervision";
    applyUiConfig(null);
    await loadAuthMode();
    showAuth();
});

deviceFilter.addEventListener("input", () => {
    if (state.snapshot) {
        renderDevices(state.snapshot);
    }
});

inventoryTypeFilter.addEventListener("change", async () => {
    ensureSelectedDevice();
    closeInventoryEditMode();
    renderInventoryDetail();
    const selected = getSelectedDevice();
    if (selected) {
        await ensureInventorySideData(selected);
    }
});

inventorySearch.addEventListener("input", async () => {
    ensureSelectedDevice();
    closeInventoryEditMode();
    renderInventoryDetail();
    const selected = getSelectedDevice();
    if (selected) {
        await ensureInventorySideData(selected);
    }
});

menuSupervision.addEventListener("click", async () => openTopMenu(menuSupervision, "supervision"));
menuEquipments.addEventListener("click", async () => openTopMenu(menuEquipments, "equipments"));
menuDisplay.addEventListener("click", async () => openTopMenu(menuDisplay, "display"));
menuHelp.addEventListener("click", async () => openTopMenu(menuHelp, "help"));

inventoryEditButton.addEventListener("click", async () => {
    try {
        inventoryEditButton.disabled = true;
        await openDeviceModal(getSelectedDevice(), { mode: "edit" });
    } catch (error) {
        inventoryFormFeedback.textContent = normalizeErrorMessage(error.message);
    } finally {
        inventoryEditButton.disabled = false;
    }
});

if (inventoryAddButton) {
    inventoryAddButton.addEventListener("click", async () => {
        const preferredType = String(inventoryTypeFilter.value || "").trim()
            || String(state.deviceTypes?.[0]?.code || "").trim();
        if (!preferredType) {
            inventoryFeedback.textContent = "Aucun type disponible pour ajouter un equipement.";
            return;
        }
        await openDeviceModal(null, { mode: "create", deviceType: preferredType });
    });
}

inventoryCancelButton.addEventListener("click", () => {
    closeInventoryEditMode();
});

contextMenu.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action]");
    if (!button || button.disabled) {
        return;
    }
    const action = String(button.dataset.action || "");
    const device = contextMenuDevice();
    closeContextMenu();
    if (action.startsWith("device:add-type:")) {
        const deviceType = action.slice("device:add-type:".length).trim();
        await openDeviceModal(null, { mode: "create", deviceType });
        return;
    }
    if (action === "device:add") {
        await openDeviceModal(null, { mode: "create" });
        return;
    }
    if (!device) {
        return;
    }
    if (action === "device:edit") {
        await openDeviceModal(device, { mode: "edit" });
        return;
    }
    if (action === "device:delete") {
        await deleteDevice(device);
        return;
    }
    if (action === "device:notify") {
        await toggleDeviceNotify(device);
        return;
    }
    if (action === "device:logs") {
        await openLogsModal({
            title: `Logs ${device.name}`,
            heading: `${typeLabel(device.device_type)} / ${device.name}`,
            device_type: device.device_type,
            device_id: device.id,
            limit: 120,
        });
        return;
    }
    if (action === "device:copy-ip") {
        await copyToClipboard(device.ip, "IP");
        return;
    }
    if (action === "device:copy-name") {
        await copyToClipboard(device.name, "Nom");
        return;
    }
    if (action === "config:manage") {
        state.selectedDeviceKey = deviceKey(device);
        renderInventoryDetail();
        await openConfigFilesManagerModal(device);
        return;
    }
    if (action === "config:download") {
        try {
            await downloadLatestDeviceConfig(device);
            inventoryFeedback.textContent = "Telechargement de configuration lance.";
        } catch (error) {
            inventoryFeedback.textContent = normalizeErrorMessage(error.message);
        }
        return;
    }
    if (action === "config:import") {
        try {
            await importDeviceConfigFromFile(device);
        } catch (error) {
            inventoryFeedback.textContent = normalizeErrorMessage(error.message);
        }
        return;
    }
    if (action.startsWith("builtin:")) {
        await runBuiltinAction(device, action.slice(8));
    }
});

topMenuPanel.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action]");
    if (!button || button.disabled) {
        return;
    }
    const action = String(button.dataset.action || "");
    closeTopMenu();
    if (action === "view:dashboard") {
        state.currentSection = "supervision";
        state.currentView = "dashboard";
        renderSection();
        return;
    }
    if (action === "view:global") {
        state.currentSection = "supervision";
        state.currentView = "global";
        renderSection();
        return;
    }
    if (action.startsWith("view:type:")) {
        state.currentSection = "supervision";
        state.currentView = action.slice("view:type:".length);
        renderSection();
        return;
    }
    if (action === "view:inventory") {
        state.currentSection = "inventory";
        renderSection();
        return;
    }
    const menuActions = {
        "menu:logs:global": () => openLogsModal({ title: "Journaux", heading: "Journal global des changements", limit: 200 }),
        "menu:monitoring": () => openMonitoringSettingsModal(),
        "menu:notifications": () => openNotificationSettingsModal(),
        "menu:web": () => openWebServerSettingsModal(),
        "menu:types": () => openDeviceTypesModal(),
        "menu:config-open-local": () => runConfigStorageAction("/config-storage/open-local-folder", { openClientPath: true }),
        "menu:config-open-backup": () => runConfigStorageAction("/config-storage/open-backup-folder", { openClientPath: true }),
        "menu:config-storage": () => openConfigStorageSettingsModal(),
        "menu:config-sync": () => runConfigStorageAction("/config-storage/sync-now"),
        "menu:theme-light": () => applySettingsPatch({ ui_theme: "light" }),
        "menu:theme-dark": () => applySettingsPatch({ ui_theme: "dark" }),
        "menu:status-badge": () => applySettingsPatch({ status_indicator_style: "badge" }),
        "menu:status-dot": () => applySettingsPatch({ status_indicator_style: "dot" }),
        "menu:about": () => openModal(
            "A propos",
            `
                <section class="modal-section">
                    <h3>NetworkMonitoringProject</h3>
                    <p class="muted">Version web: ${escapeHtml(document.getElementById("app-version").textContent || "-")}</p>
                    <p class="muted">Interface web alignee au runtime desktop.</p>
                </section>
            `,
            { width: "min(560px, calc(100vw - 40px))" },
        ),
    };
    const handler = menuActions[action];
    if (handler) {
        await handler();
        return;
    }
    if (action.startsWith("menu:logs:type:")) {
        const typeCode = action.slice("menu:logs:type:".length);
        const label = typeLabel(typeCode);
        await openLogsModal({
            title: `Journal ${label}`,
            heading: `Journal des changements - ${label}`,
            device_type: typeCode,
            limit: 200,
        });
    }
});

document.addEventListener("click", (event) => {
    if (!contextMenu.hidden && !contextMenu.contains(event.target)) {
        closeContextMenu();
    }
    if (!topMenuPanel.hidden && !topMenuPanel.contains(event.target) && !event.target.closest(".menu-btn")) {
        closeTopMenu();
    }
});

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
        closeContextMenu();
        closeTopMenu();
        closeModal();
    }
});

window.addEventListener("scroll", () => {
    if (!contextMenu.hidden) {
        closeContextMenu();
    }
    if (!topMenuPanel.hidden) {
        closeTopMenu();
    }
}, true);

appModalClose.addEventListener("click", () => {
    closeModal();
});

appModalBackdrop.addEventListener("click", () => {
    closeModal();
});

appModalBody.addEventListener("click", (event) => {
    const closeButton = event.target.closest('[data-action="modal:close"]');
    if (closeButton) {
        closeModal();
        return;
    }
    const actionButton = event.target.closest("[data-action]");
    if (!actionButton || actionButton.disabled) {
        return;
    }
    const action = String(actionButton.dataset.action || "");
    const typeCode = String(actionButton.dataset.typeCode || "");
    if (action === "types:save" && typeCode) {
        saveDeviceTypeRow(typeCode).catch((error) => {
            const feedback = document.getElementById("modal-device-types-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        });
        return;
    }
    if (action === "types:delete" && typeCode) {
        deleteDeviceTypeRow(typeCode).catch((error) => {
            const feedback = document.getElementById("modal-device-types-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        });
        return;
    }
    if (action === "config-modal:refresh") {
        setConfigFilesModalFeedback("");
        refreshConfigFilesManagerModal().catch((error) => {
            setConfigFilesModalFeedback(normalizeErrorMessage(error.message));
        });
        return;
    }
    if (action === "config-modal:download") {
        const device = configManagerDevice();
        if (!device) {
            setConfigFilesModalFeedback("Equipement introuvable.");
            return;
        }
        setConfigFilesModalFeedback("Telechargement...");
        downloadLatestDeviceConfig(device)
            .then(() => {
                setConfigFilesModalFeedback("Telechargement lance.");
            })
            .catch((error) => {
                setConfigFilesModalFeedback(normalizeErrorMessage(error.message));
            });
        return;
    }
    if (action === "config-modal:import") {
        const device = configManagerDevice();
        if (!device) {
            setConfigFilesModalFeedback("Equipement introuvable.");
            return;
        }
        setConfigFilesModalFeedback("");
        importDeviceConfigFromFile(device)
            .then(async () => {
                setConfigFilesModalFeedback("Fichier importe.");
                await refreshConfigFilesManagerModal();
            })
            .catch((error) => {
                setConfigFilesModalFeedback(normalizeErrorMessage(error.message));
            });
    }
});

if (inventoryTableWrap) {
    inventoryTableWrap.addEventListener("contextmenu", (event) => {
        const target = event.target;
        if (!(target instanceof Element)) {
            return;
        }
        if (target.closest("tbody tr")) {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        closeTopMenu();
        openInventoryBackgroundContextMenu(event.clientX, event.clientY);
    });
}

if (inventoryBody) {
    inventoryBody.addEventListener("contextmenu", (event) => {
        const target = event.target;
        if (!(target instanceof Element)) {
            return;
        }
        if (target.closest("tr")) {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        closeTopMenu();
        openInventoryBackgroundContextMenu(event.clientX, event.clientY);
    });
}

if (devicesHead) {
    devicesHead.addEventListener("click", (event) => {
        const target = event.target;
        if (!(target instanceof Element)) {
            return;
        }
        const th = target.closest("th[data-col]");
        if (!th) {
            return;
        }
        const col = String(th.getAttribute("data-col") || "").trim();
        if (!col) {
            return;
        }
        if (state.supervisionSort.column === col) {
            state.supervisionSort.direction = state.supervisionSort.direction === "asc" ? "desc" : "asc";
        } else {
            state.supervisionSort.column = col;
            state.supervisionSort.direction = "asc";
        }
        if (state.snapshot) {
            renderDevices(state.snapshot);
        }
    });
}

if (inventoryHead) {
    inventoryHead.addEventListener("click", async (event) => {
        const target = event.target;
        if (!(target instanceof Element)) {
            return;
        }
        const th = target.closest("th[data-col]");
        if (!th) {
            return;
        }
        const col = String(th.getAttribute("data-col") || "").trim();
        if (!col) {
            return;
        }
        if (state.inventorySort.column === col) {
            state.inventorySort.direction = state.inventorySort.direction === "asc" ? "desc" : "asc";
        } else {
            state.inventorySort.column = col;
            state.inventorySort.direction = "asc";
        }
        renderInventoryDetail();
        const selected = getSelectedDevice();
        if (selected) {
            await ensureInventorySideData(selected);
        }
    });
}

appModalBody.addEventListener("submit", async (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) {
        return;
    }
    event.preventDefault();
    if (form.id === "modal-device-form") {
        await submitDeviceModal(form);
        return;
    }
    if (form.id === "modal-settings-form") {
        await submitMonitoringSettings(form);
        return;
    }
    if (form.id === "modal-notification-form") {
        await submitNotificationSettings(form);
        return;
    }
    if (form.id === "modal-webserver-form") {
        await submitWebServerSettings(form);
        return;
    }
    if (form.id === "modal-config-storage-form") {
        await submitConfigStorageSettings(form);
        return;
    }
    if (form.id === "modal-device-type-create-form") {
        await submitCreateDeviceType(form);
    }
});

appModalBody.addEventListener("change", async (event) => {
    const target = event.target;
    const form = target?.closest?.("#modal-device-form");
    if (form && form.dataset.mode === "create" && target instanceof HTMLSelectElement && target.name === "device_type") {
        await openDeviceModal(null, { mode: "create", deviceType: target.value });
    }
});

inventoryEditForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const mode = inventoryEditForm.dataset.mode || "edit";
    const device = getSelectedDevice();
    if (mode === "edit" && !device) {
        return;
    }
    inventorySaveButton.disabled = true;
    inventoryFormFeedback.textContent = "Enregistrement...";
    const formData = new window.FormData(inventoryEditForm);
    const customData = {};
    for (const [key, value] of formData.entries()) {
        if (String(key).startsWith("custom:")) {
            customData[String(key).slice(7)] = String(value || "");
        }
    }
    const deviceType = mode === "create"
        ? String(formData.get("device_type") || inventoryTypeFilter.value || "").trim()
        : device.device_type;
    const payload = {
        name: String(formData.get("name") || "").trim(),
        ip: String(formData.get("ip") || "").trim(),
        description: String(formData.get("description") || "").trim(),
        id_Teamviewer: String(formData.get("id_Teamviewer") || "").trim(),
        device_subtype: String(formData.get("device_subtype") || "").trim(),
        action_double_click: String(formData.get("action_double_click") || "").trim(),
        web_url: String(formData.get("web_url") || "").trim(),
        ssh_user: String(formData.get("ssh_user") || "").trim(),
        custom_data: customData,
        notify: inventoryNotify.checked,
    };

    try {
        if (mode === "create") {
            await requestJson("/devices", {
                method: "POST",
                body: JSON.stringify({
                    ...payload,
                    device_type: deviceType,
                }),
            });
            inventoryFormFeedback.textContent = "Equipement ajoute.";
        } else {
            await requestJson(`/devices/${encodeURIComponent(device.device_type)}/${encodeURIComponent(device.id)}`, {
                method: "PUT",
                body: JSON.stringify(payload),
            });
            inventoryFormFeedback.textContent = "Equipement mis a jour.";
        }
        await loadInventory();
        renderInventoryDetail();
        const selected = getSelectedDevice();
        if (selected) {
            await ensureInventorySideData(selected);
        }
        closeInventoryEditMode();
    } catch (error) {
        inventoryFormFeedback.textContent = normalizeErrorMessage(error.message);
    } finally {
        inventorySaveButton.disabled = false;
    }
});

inventoryEditForm.addEventListener("change", async (event) => {
    const target = event.target;
    if (inventoryEditForm.dataset.mode === "create" && target instanceof HTMLSelectElement && target.name === "device_type") {
        await openInventoryEditMode(null, { mode: "create", deviceType: target.value });
    }
});

boot().catch((error) => {
    setError(error.message || "Initialisation web impossible.");
    showAuth();
});
