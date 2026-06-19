const STANDARD_FIELDS = new Set([
    "name",
    "ip",
    "description",
    "id_Teamviewer",
    "type",
    "device_subtype",
    "action_double_click",
    "web_url",
    "ssh_user",
    "device_login",
    "device_password",
    "config_saved",
    "notify",
]);

const FIELD_LABELS = {
    name: "Nom",
    ip: "IP",
    description: "Description",
    id_Teamviewer: "TeamViewer",
    type: "OS",
    device_subtype: "Sous-type",
    action_double_click: "Action double-clic",
    web_url: "URL web",
    ssh_user: "Utilisateur SSH",
    device_login: "Login",
    device_password: "Mot de passe",
    config_saved: "Cfg",
    notify: "Alertes changement",
};

const PLATFORM_OPTIONS = ["Windows", "Linux", "Firmware", "Autre"];
const DEFAULT_PLATFORM_KEYS = new Set(["windows", "linux", "firmware", "autre"]);
const ACTION_LABELS = {
    ssh: "SSH",
    web: "Web (URL)",
    teamviewer: "TeamViewer",
    remote_desktop: "Remote Desktop",
};
const TYPE_SCHEMA_FIELD_KINDS = ["text", "ip", "url", "choice"];
const TYPE_SCHEMA_FIELD_KIND_LABELS = {
    text: "Text",
    ip: "IP",
    url: "URL",
    choice: "List",
};
const TYPE_SCHEMA_SYSTEM_FIELD_KEYS = new Set([
    "name",
    "description",
    "type",
    "ip",
    "id_teamviewer",
    "web_url",
    "ssh_user",
    "device_login",
    "device_password",
    "config_saved",
    "notify",
    "action_double_click",
    "action_default_by_os",
]);
const TYPE_SCHEMA_CORE_FIELDS = {
    name: { label: "Nom", field_kind: "text", required: true, options: "", default_value: "", show_in_table: true },
    description: { label: "Description", field_kind: "text", required: false, options: "", default_value: "", show_in_table: false },
    type: { label: "OS", field_kind: "choice", required: true, options: PLATFORM_OPTIONS.join(","), default_value: PLATFORM_OPTIONS[0], show_in_table: false },
    ip: { label: "IP", field_kind: "ip", required: true, options: "", default_value: "", show_in_table: true },
    config_saved: { label: "Cfg", field_kind: "text", required: false, options: "", default_value: "", show_in_table: true },
    notify: { label: "Alertes changement", field_kind: "text", required: false, options: "", default_value: "", show_in_table: true },
};
const TYPE_SCHEMA_CREDENTIAL_FIELDS = {
    device_login: { label: "Login", field_kind: "text", required: false, options: "", default_value: "", show_in_table: true },
    device_password: { label: "Mot de passe", field_kind: "text", required: false, options: "", default_value: "", show_in_table: true },
};
const TYPE_SCHEMA_TABLE_SYSTEM_FIELD_KEYS = ["name", "ip", "description", "device_login", "device_password", "config_saved", "notify"];
const TYPE_SCHEMA_PLUGIN_BLOCKS = [
    { key: "ssh", title: "SSH", badge: "SSH" },
    { key: "teamviewer", title: "TeamViewer", badge: "TV" },
    { key: "remote_desktop", title: "Remote Desktop", badge: "RDP" },
    { key: "web", title: "Web", badge: "WEB" },
];
const DEFAULT_CREDENTIAL_REVEAL_UNLOCK_SECONDS = 300;
const MIN_CREDENTIAL_REVEAL_UNLOCK_SECONDS = 30;
const MAX_CREDENTIAL_REVEAL_UNLOCK_SECONDS = 3600;

const state = {
    token: window.localStorage.getItem("nmp_token") || "",
    sessionSubject: "",
    sessionLabel: "",
    sessionRoleCode: "",
    sessionRoleLabel: "",
    snapshot: null,
    websocket: null,
    reconnectTimer: null,
    pollingTimer: null,
    fallbackToPolling: false,
    capabilities: null,
    uiConfig: null,
    currentView: "dashboard",
    supervisionStatusFilter: "",
    currentSection: "supervision",
    inventory: [],
    deviceTypes: [],
    deviceSchemas: {},
    selectedDeviceKey: "",
    inventoryFormMode: "edit",
    contextMenuDeviceKey: "",
    contextMenuTypeCode: "",
    deviceBatchContextRows: [],
    deviceTypeBatchContextRows: [],
    openTopMenu: "",
    configStorageState: null,
    configFilesModalRows: [],
    configFilesModalSort: { column: "modified_at", direction: "desc" },
    configLibraryRows: [],
    configLibrarySort: { column: "modified_at", direction: "desc" },
    storageExplorer: {
        roots: [],
        rootId: "",
        path: "",
        items: [],
        parentPath: "",
        rootLabel: "",
    },
    supervisionSort: { column: "type", direction: "asc" },
    inventorySort: { column: "type", direction: "asc" },
    typeSyncTimer: null,
    lastSnapshotTypeSignature: "",
    configManagerDeviceKey: "",
    networkToolAbortController: null,
    networkScanAbortController: null,
    deviceTypesModalSort: { column: "label", direction: "asc" },
    deviceTypesModalRows: [],
    deviceTypesPageOpening: false,
    activeInlineModalHost: "",
    networkScanRows: [],
    networkScanContextIp: "",
    moduleAccess: [],
    moduleAccessLoaded: false,
    typeSchemaEditor: null,
    typeSchemaDrag: null,
    typeSchemaEditorContext: null,
    deviceImportDraft: null,
    watermarkEditorDraft: null,
    remoteDesktopLaunchDeviceKey: "",
    credentialRevealUnlockDurationSeconds: DEFAULT_CREDENTIAL_REVEAL_UNLOCK_SECONDS,
    credentialRevealSessionPassword: "",
    credentialRevealUnlockUntilMs: 0,
    credentialRevealUnlockTimer: null,
    revealedDevicePasswords: {},
    monitoringDashboardCardSignature: "",
    monitoringDashboardPrefsLoaded: false,
};

const authScreen = document.getElementById("auth-screen");
const dashboardPanel = document.getElementById("dashboard-panel");
const authTitle = document.getElementById("auth-title");
const authHelp = document.getElementById("auth-help");
const authForm = document.getElementById("auth-form");
const authSubmit = document.getElementById("auth-submit");
const usernameInput = document.getElementById("username-input");
const passwordInput = document.getElementById("password-input");
const newPasswordField = document.getElementById("new-password-field");
const newPasswordInput = document.getElementById("new-password-input");
const confirmPasswordField = document.getElementById("confirm-password-field");
const confirmPasswordInput = document.getElementById("confirm-password-input");
const authError = document.getElementById("auth-error");
const refreshButton = document.getElementById("refresh-button");
const profileMenuButton = document.getElementById("profile-menu-button");
const dashboardEditButton = document.getElementById("dashboard-edit-button");
const deviceFilter = document.getElementById("device-filter");
const supervisionTypeFilter = document.getElementById("supervision-type-filter");
const supervisionStatusFilter = document.getElementById("supervision-status-filter");
const supervisionEditTypeButton = document.getElementById("supervision-edit-type-button");
const navToolbar = document.getElementById("nav-toolbar");
const cardsGrid = document.getElementById("cards-grid");
const monitoringToolbar = document.getElementById("monitoring-toolbar");
const placeholderPanel = document.getElementById("dashboard-placeholder");
const detailPanel = document.getElementById("detail-panel");
const detailTitle = document.getElementById("detail-title");
const inventoryTitle = document.getElementById("inventory-title");
const topbar = dashboardPanel?.querySelector?.(".topbar");
const topbarTitle = dashboardPanel?.querySelector?.(".topbar-title");
const devicesSection = document.getElementById("devices-section");
const typesPanel = document.getElementById("types-panel");
const supervisionSection = document.getElementById("supervision-section");
const inventorySection = document.getElementById("inventory-section");
const inventoryMainPanel = inventorySection?.querySelector?.(".inventory-main") || null;
const runtimeStrip = document.querySelector(".runtime-strip");
const menuModules = document.getElementById("menu-modules");
const menuSupervision = document.getElementById("menu-supervision");
const menuEquipments = document.getElementById("menu-equipments");
const menuTools = document.getElementById("menu-tools");
const menuHelp = document.getElementById("menu-help");
const inventoryTypeFilter = document.getElementById("inventory-type-filter");
const inventoryEditTypeButton = document.getElementById("inventory-edit-type-button");
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
const inventoryImportButton = document.getElementById("inventory-import-button");
const inventoryExportButton = document.getElementById("inventory-export-button");
const inventoryInlineModalHost = document.getElementById("inventory-inline-modal-host");
const appModal = document.getElementById("app-modal");
const appModalBackdrop = document.getElementById("app-modal-backdrop");
const appModalPanel = document.getElementById("app-modal-panel");
const appModalTitle = document.getElementById("app-modal-title");
const appModalBody = document.getElementById("app-modal-body");
const appModalClose = document.getElementById("app-modal-close");
const appModalDefaultParent = appModal?.parentElement || null;
const appModalDefaultNextSibling = appModal?.nextSibling || null;
const topMenuPanel = document.getElementById("top-menu-panel");
const profileMenuPanel = document.getElementById("profile-menu-panel");
const contextMenu = document.getElementById("context-menu");
const devicesHead = document.getElementById("devices-head");
const inventoryHead = document.getElementById("inventory-head");
const sessionProfileLabel = document.getElementById("session-profile-label");
let supervisionTreeView = null;
let inventoryTreeView = null;
let deviceTypesTreeView = null;
let configFilesTreeView = null;
let configLibraryTreeView = null;
let monitoringDashboardEditor = null;
let profileMenuController = null;
let authFailureHandling = false;
const modalController = window.NMPSharedUi?.shell?.createModalController?.({
    modal: appModal,
    titleNode: appModalTitle,
    bodyNode: appModalBody,
    panelNode: appModalPanel,
    defaultWidth: "min(980px, calc(100vw - 40px))",
    onBeforeClose: () => {
        if (state.networkToolAbortController) {
            state.networkToolAbortController.abort();
            state.networkToolAbortController = null;
        }
        if (state.networkScanAbortController) {
            state.networkScanAbortController.abort();
            state.networkScanAbortController = null;
        }
        state.configManagerDeviceKey = "";
        state.typeSchemaEditor = null;
        state.typeSchemaDrag = null;
        clearWatermarkEditorDraft();
    },
}) || null;
const topMenuController = window.NMPSharedUi?.shell?.createTopMenuController?.({
    state,
    panel: topMenuPanel,
    buttons: [menuModules, menuSupervision, menuEquipments, menuTools, menuHelp],
    buildMarkup: (menuKey) => topMenuMarkup(menuKey),
    onBeforeOpen: () => closeContextMenu(),
    onAfterOpen: (openedKey) => {
        if (openedKey === "equipments") {
            refreshEquipmentsTopMenuIfOpen();
        }
    },
}) || null;

function setError(message = "") {
    authError.hidden = !message;
    authError.textContent = message;
}

function roleIcon(roleCode) {
    const sharedRoleIcon = window.NMPSharedAuth?.roleIcon;
    if (typeof sharedRoleIcon === "function") {
        return sharedRoleIcon(roleCode);
    }
    const normalized = String(roleCode || "").trim().toLowerCase();
    if (normalized === "admin") {
        return "🛡";
    }
    if (normalized === "technician") {
        return "🛠";
    }
    return "👤";
}

function renderSessionProfile() {
    if (!sessionProfileLabel) {
        return;
    }
    profileMenuController?.renderLabel?.();
    if (!profileMenuController) {
        sessionProfileLabel.textContent = String(state.sessionLabel || state.sessionSubject || "-").trim() || "-";
    }
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
    const sharedHeaders = window.NMPSharedApi?.authHeaders;
    if (typeof sharedHeaders === "function") {
        return sharedHeaders(state.token);
    }
    return state.token ? { Authorization: `Bearer ${state.token}` } : {};
}

function normalizeErrorMessage(message) {
    const sharedNormalize = window.NMPSharedApi?.normalizeErrorMessage;
    if (typeof sharedNormalize === "function") {
        return sharedNormalize(message);
    }
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
    const sharedRequest = window.NMPSharedApi?.requestJson;
    if (typeof sharedRequest === "function") {
        return sharedRequest(path, options, {
            token: state.token,
            normalizeErrorMessage,
            onAuthFailure: handleAuthFailure,
        });
    }
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
        const message = normalizeErrorMessage(detail);
        const lowered = String(detail || "").toLowerCase();
        if ((response.status === 401 && state.token) || lowered.includes("invalid or expired session")) {
            await handleAuthFailure();
        }
        throw new Error(message);
    }
    if (response.status === 204) {
        return null;
    }
    return response.json();
}

function persistToken(token) {
    const sharedPersist = window.NMPSharedApi?.persistToken;
    if (typeof sharedPersist === "function") {
        sharedPersist(state, token, "nmp_token");
        return;
    }
    state.token = token || "";
    if (state.token) {
        window.localStorage.setItem("nmp_token", state.token);
        return;
    }
    window.localStorage.removeItem("nmp_token");
}

function clearSessionState() {
    const sharedClear = window.NMPSharedAuth?.clearSessionContext;
    if (typeof sharedClear === "function") {
        sharedClear(state);
        clearCredentialRevealState({ refresh: false });
        return;
    }
    state.sessionSubject = "";
    state.sessionLabel = "";
    state.sessionRoleCode = "";
    state.sessionRoleLabel = "";
    state.moduleAccess = [];
    state.moduleAccessLoaded = false;
    clearCredentialRevealState({ refresh: false });
}

function escapeHtml(value) {
    const sharedEscapeHtml = window.NMPSharedApi?.escapeHtml;
    if (typeof sharedEscapeHtml === "function") {
        return sharedEscapeHtml(value);
    }
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

function normalizeStatusFilter(status = "") {
    const normalized = String(status || "").trim().toLowerCase();
    return ["online", "offline", "idle"].includes(normalized) ? normalized : "";
}

function normalizeMonitoringTypeFilter(typeCode = "global") {
    const normalized = String(typeCode || "").trim().toLowerCase();
    return normalized && normalized !== "dashboard" && normalized !== "global" ? normalized : "global";
}

function currentMonitoringTreeFilters() {
    return {
        typeCode: normalizeMonitoringTypeFilter(state.currentView),
        status: normalizeStatusFilter(state.supervisionStatusFilter),
    };
}

function applyMonitoringTreeFilters({ typeCode = "global", status = "" } = {}) {
    const rawType = String(typeCode || "").trim().toLowerCase();
    const normalizedType = normalizeMonitoringTypeFilter(typeCode);
    state.currentSection = "supervision";
    state.currentView = rawType === "dashboard" ? "dashboard" : normalizedType;
    state.supervisionStatusFilter = normalizeStatusFilter(status);
    syncMonitoringTreeFilterControls();
}

function openSupervisionFilteredView(typeCode = "global", status = "") {
    applyMonitoringTreeFilters({ typeCode, status });
    renderSection();
}

function createSupervisionStatButtonMarkup({ typeCode = "global", status = "", label = "", value = 0, className = "", available = true } = {}) {
    const normalizedStatus = normalizeStatusFilter(status);
    const count = Math.max(0, Number(value || 0));
    const displayValue = available ? String(count) : "-";
    const disabled = !available || count <= 0 ? " disabled" : "";
    return `
        <button
            class="stat-filter-btn ${escapeHtml(className)}"
            type="button"
            data-supervision-type="${escapeHtml(typeCode || "global")}"
            data-supervision-status="${escapeHtml(normalizedStatus)}"
            ${disabled}
        >
            <span>${escapeHtml(label)}</span>
            <strong>${escapeHtml(displayValue)}</strong>
        </button>
    `;
}

function createSupervisionStatsMarkup(typeCode, stats = {}) {
    const total = Math.max(0, Number(stats.total || 0));
    const online = Math.max(0, Number(stats.online || 0));
    const offline = Math.max(0, Number(stats.offline || 0));
    const monitoringRunning = stats.running !== false;
    const entries = [
        createSupervisionStatButtonMarkup({ typeCode, label: "Total", value: total }),
        createSupervisionStatButtonMarkup({ typeCode, status: "online", label: "En ligne", value: online, className: "stat-online", available: monitoringRunning }),
        createSupervisionStatButtonMarkup({ typeCode, status: "offline", label: "Hors ligne", value: offline, className: "stat-offline", available: monitoringRunning }),
    ];
    return entries.join("");
}

function bindSupervisionStatFilterButtons(container, fallbackTypeCode = "global") {
    if (!(container instanceof HTMLElement)) {
        return;
    }
    for (const button of Array.from(container.querySelectorAll("[data-supervision-type]"))) {
        button.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            if (button.disabled) {
                return;
            }
            openSupervisionFilteredView(
                button.dataset.supervisionType || fallbackTypeCode,
                button.dataset.supervisionStatus || "",
            );
        });
    }
}

function statusTransitionClass(oldStatus, newStatus) {
    const oldNorm = String(oldStatus || "").trim().toLowerCase();
    const newNorm = String(newStatus || "").trim().toLowerCase();
    if (oldNorm === "online" && newNorm === "offline") {
        return "log-item-status-down";
    }
    if (oldNorm === "offline" && newNorm === "online") {
        return "log-item-status-up";
    }
    return "";
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

function typeHasConfigSupport(typeCode) {
    return Boolean(typeMeta(typeCode)?.config_backups_enabled);
}

function typeHasCredentialsSupport(typeCode) {
    const code = String(typeCode || "").trim();
    if (!code) {
        return false;
    }
    const meta = typeMeta(code);
    if (meta && Object.prototype.hasOwnProperty.call(meta, "credentials_enabled")) {
        return Boolean(meta.credentials_enabled);
    }
    const fields = Array.isArray(state.deviceSchemas?.[code]?.fields) ? state.deviceSchemas[code].fields : [];
    const keys = new Set(
        fields.map((field) => String(field?.field_key || "").trim().toLowerCase()),
    );
    return keys.has("device_login") && keys.has("device_password");
}

function schemaFieldVisibleInTable(field, fallback = false) {
    return Boolean(field?.show_in_table ?? fallback);
}

function defaultShowInTableForField(fieldKey) {
    const key = String(fieldKey || "").trim().toLowerCase();
    if (key === "name" || key === "ip" || key === "device_login" || key === "device_password" || key === "config_saved" || key === "notify") {
        return true;
    }
    return false;
}

function currentSupervisionTypeCode() {
    const code = currentMonitoringTreeFilters().typeCode;
    return code === "global" ? "" : code;
}

function updateSupervisionTypeEditButton() {
    if (!(supervisionEditTypeButton instanceof HTMLButtonElement)) {
        return;
    }
    const typeCode = state.currentSection === "supervision" ? currentSupervisionTypeCode() : "";
    const meta = typeCode ? typeMeta(typeCode) : null;
    const canEdit = Boolean(typeCode && meta);
    supervisionEditTypeButton.hidden = !canEdit;
    supervisionEditTypeButton.disabled = !canEdit;
    if (!canEdit) {
        supervisionEditTypeButton.dataset.typeCode = "";
        supervisionEditTypeButton.textContent = "Modifier le type";
        return;
    }
    const label = String(meta?.label || displayLabelForView(typeCode) || typeCode).trim();
    supervisionEditTypeButton.dataset.typeCode = typeCode;
    supervisionEditTypeButton.textContent = `Modifier type ${label}`;
}

function networkToolTitle(action) {
    const labels = {
        "tool:ping": "Ping",
        "tool:port": "Port check",
        "tool:traceroute": "Traceroute",
        "tool:dns": "DNS lookup",
        "tool:http": "HTTP(S) check",
        "tool:snmp": "SNMP",
    };
    return labels[action] || "Outil reseau";
}

function networkToolEndpoint(action) {
    const endpoints = {
        "tool:ping": "/network-tools/ping",
        "tool:port": "/network-tools/port-check",
        "tool:traceroute": "/network-tools/traceroute",
        "tool:dns": "/network-tools/dns-lookup",
        "tool:http": "/network-tools/http-check",
        "tool:snmp": "/network-tools/snmp-check",
    };
    return endpoints[action] || "";
}

function networkToolStreamEndpoint(action) {
    const endpoints = {
        "tool:ping": "/network-tools/ping/stream",
        "tool:traceroute": "/network-tools/traceroute/stream",
        "tool:dns": "/network-tools/dns-lookup/stream",
    };
    return endpoints[action] || "";
}

function networkToolFieldsMarkup(action, device) {
    const ip = String(device?.ip || "").trim();
    if (action === "tool:ping") {
        return createFieldMarkup({ key: "ip", label: "IP cible", value: ip });
    }
    if (action === "tool:port") {
        return [
            createFieldMarkup({ key: "ip", label: "IP cible", value: ip }),
            createFieldMarkup({ key: "port", label: "Port TCP", value: "22" }),
        ].join("");
    }
    if (action === "tool:traceroute") {
        return createFieldMarkup({ key: "ip", label: "IP cible", value: ip });
    }
    if (action === "tool:dns") {
        return createFieldMarkup({ key: "target", label: "Domaine ou IP", value: ip });
    }
    if (action === "tool:http") {
        return createFieldMarkup({ key: "url", label: "URL", value: ip ? `http://${ip}` : "http://" });
    }
    if (action === "tool:snmp") {
        return [
            createFieldMarkup({ key: "ip", label: "IP cible", value: ip }),
            createFieldMarkup({ key: "community", label: "Community", value: "public" }),
            createFieldMarkup({ key: "oid", label: "OID", value: "1.3.6.1.2.1.1.1.0", wide: true }),
        ].join("");
    }
    return "";
}

function networkToolPayload(action, formData) {
    if (action === "tool:ping" || action === "tool:traceroute") {
        return { ip: String(formData.get("ip") || "").trim() };
    }
    if (action === "tool:port") {
        const port = Number(formData.get("port") || 0);
        return {
            ip: String(formData.get("ip") || "").trim(),
            port: Number.isFinite(port) ? Math.trunc(port) : 0,
        };
    }
    if (action === "tool:dns") {
        return { target: String(formData.get("target") || "").trim() };
    }
    if (action === "tool:http") {
        return { url: String(formData.get("url") || "").trim() };
    }
    if (action === "tool:snmp") {
        return {
            ip: String(formData.get("ip") || "").trim(),
            community: String(formData.get("community") || "").trim(),
            oid: String(formData.get("oid") || "").trim(),
        };
    }
    return {};
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
    if (column === "config_saved") {
        const leftValue = Boolean(left.has_saved_config);
        const rightValue = Boolean(right.has_saved_config);
        return ((leftValue === rightValue ? 0 : leftValue ? 1 : -1) * dir);
    }
    if (column === "device_password") {
        const leftValue = Boolean(left.has_device_password);
        const rightValue = Boolean(right.has_device_password);
        return ((leftValue === rightValue ? 0 : leftValue ? 1 : -1) * dir);
    }
    if (column === "device_login") {
        return byText(left.device_login, right.device_login);
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
    if (String(column || "").startsWith("custom:")) {
        const key = String(column || "").slice("custom:".length);
        return byText(left.custom_data?.[key], right.custom_data?.[key]);
    }
    return byText(left.name, right.name);
}

function updateSearchVisibility(input, rowCount, threshold = 5) {
    const shared = window.NMPSharedUi?.tableTools?.updateSearchVisibility;
    if (typeof shared !== "function") {
        return;
    }
    shared(input, rowCount, threshold);
}

function filterAndSortRows(rows, options = {}) {
    const shared = window.NMPSharedUi?.tableTools?.filterAndSortRows;
    if (typeof shared === "function") {
        return shared(rows, options);
    }
    return Array.isArray(rows) ? rows.slice() : [];
}

function normalizeSearchText(value) {
    const shared = window.NMPSharedUi?.tableTools?.normalizeSearchText;
    if (typeof shared === "function") {
        return shared(value);
    }
    return String(value || "")
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase()
        .trim();
}

function bindHeaderSort(headElement, options = {}) {
    const shared = window.NMPSharedUi?.tableTools?.bindHeaderSort;
    if (typeof shared !== "function") {
        return;
    }
    shared(headElement, options);
}

function supervisionSourceRows() {
    if (!state.snapshot) {
        return [];
    }
    return visibleRowsForCurrentView(state.snapshot).map((item) => resolveDeviceRecord(item));
}

class SupervisionDevicesTreeView extends (window.NMPSharedUi?.treeView?.SharedTreeView || class {}) {
    constructor() {
        super({
            headElement: devicesHead,
            bodyElement: document.getElementById("devices-body"),
            searchInput: deviceFilter,
            sortState: state.supervisionSort,
            renderHead: true,
            manageSortBinding: false,
            manageSearchBinding: false,
            selectable: true,
            searchThreshold: 5,
            emptyMessage: "Aucun equipement",
            getColumns: () => this._columns,
            getRows: () => supervisionSourceRows(),
            searchText: (item) => [
                item.device_type,
                item.name,
                item.ip,
                item.device_login,
                item.status,
                item.description,
                item.has_saved_config ? "oui" : "non",
                ...(Array.isArray(this._columns) ? this._columns.map((column) => {
                    const key = String(column?.key || "");
                    return key.startsWith("custom:") ? String(item.custom_data?.[key.slice("custom:".length)] || "") : "";
                }) : []),
            ].join(" "),
            compareRows: (column, direction, left, right) => compareByColumn(column, direction, left, right),
            getRowKey: (item) => deviceKey(item),
            getRowClassName: (item) => (deviceKey(item) === state.selectedDeviceKey ? "is-selected" : ""),
            getRowAttributes: (item) => ({
                "data-device-key": deviceKey(item),
            }),
            onBackgroundContextMenu: ({ event, x, y }) => {
                closeTopMenu();
                if (openDeviceBatchContextMenu(x, y, selectedSupervisionRows())) {
                    return;
                }
                if (openSelectedDeviceContextMenuFromTreeBody(event)) {
                    return;
                }
                openSupervisionBackgroundContextMenu(x, y);
            },
            onRowsRendered: (rows) => {
                const body = this.bodyElement;
                if (!(body instanceof HTMLElement)) {
                    return;
                }
                const rowsByKey = new Map(rows.map((row) => [deviceKey(row), row]));
                for (const tr of Array.from(body.querySelectorAll("tr[data-device-key]"))) {
                    const key = String(tr.getAttribute("data-device-key") || "").trim();
                    const device = rowsByKey.get(key);
                    if (!device) {
                        continue;
                    }
                    const revealButton = tr.querySelector('[data-row-action="reveal_password"]');
                    if (revealButton instanceof HTMLButtonElement) {
                        revealButton.addEventListener("click", async (event) => {
                            event.preventDefault();
                            event.stopPropagation();
                            await openDevicePasswordRevealModal(device);
                        });
                    }
                    tr.addEventListener("click", (event) => {
                        const target = event.target;
                        if (target instanceof Element && target.closest("[data-tree-select-row]")) {
                            return;
                        }
                        state.selectedDeviceKey = deviceKey(device);
                        closeContextMenu();
                        closeTopMenu();
                        if (state.snapshot) {
                            renderDevices(state.snapshot);
                        }
                    });
                    tr.addEventListener("dblclick", async (event) => {
                        const target = event.target;
                        if (target instanceof Element && target.closest("[data-tree-select-row]")) {
                            return;
                        }
                        state.selectedDeviceKey = deviceKey(device);
                        closeTopMenu();
                        await runDeviceDoubleClickAction(device);
                    });
                    tr.addEventListener("contextmenu", async (event) => {
                        const target = event.target;
                        if (target instanceof Element && target.closest("[data-tree-select-row]")) {
                            return;
                        }
                        event.preventDefault();
                        event.stopPropagation();
                        const selectedRows = selectedSupervisionRowsIncluding(device);
                        if (selectedRows.length) {
                            closeTopMenu();
                            openDeviceBatchContextMenu(event.clientX, event.clientY, selectedRows);
                            return;
                        }
                        state.selectedDeviceKey = deviceKey(device);
                        if (state.snapshot) {
                            renderDevices(state.snapshot);
                        }
                        await openContextMenu(event.clientX, event.clientY, device);
                    });
                }
            },
        });
        this._columns = [];
    }

    render() {
        const rows = supervisionSourceRows();
        const filterType = currentMonitoringTreeFilters().typeCode;
        const scopedType = filterType === "global" ? "" : filterType;
        this._columns = buildDeviceTreeColumns({
            rows,
            typeCode: scopedType,
            includeType: !scopedType,
            includeNotify: true,
            includeStatus: true,
            includeConfig: true,
            includeDescription: true,
            includeCustomFields: Boolean(scopedType),
        });
        return super.render();
    }
}

function ensureSupervisionTreeView() {
    const BaseClass = window.NMPSharedUi?.treeView?.SharedTreeView;
    if (!BaseClass) {
        return null;
    }
    const body = document.getElementById("devices-body");
    if (!(devicesHead instanceof HTMLElement) || !(body instanceof HTMLElement)) {
        return null;
    }
    if (
        supervisionTreeView instanceof SupervisionDevicesTreeView
        && supervisionTreeView.headElement === devicesHead
        && supervisionTreeView.bodyElement === body
    ) {
        return supervisionTreeView;
    }
    supervisionTreeView = new SupervisionDevicesTreeView();
    return supervisionTreeView;
}

class MonitoringInventoryTreeView extends (window.NMPSharedUi?.treeView?.SharedTreeView || class {}) {
    constructor() {
        super({
            headElement: inventoryHead,
            bodyElement: inventoryBody,
            searchInput: inventorySearch,
            sortState: state.inventorySort,
            renderHead: true,
            manageSortBinding: false,
            manageSearchBinding: false,
            selectable: true,
            searchThreshold: 5,
            emptyMessage: "Aucun equipement",
            getColumns: () => this._columns,
            getRows: () => inventorySourceRows(),
            searchText: (item) => [
                item.device_type,
                typeLabel(item.device_type),
                item.name,
                item.ip,
                item.description,
                item.web_url,
                item.ssh_user,
                item.device_login,
                item.has_saved_config ? "oui" : "non",
                ...(Array.isArray(this._columns) ? this._columns.map((column) => {
                    const key = String(column?.key || "");
                    return key.startsWith("custom:") ? String(item.custom_data?.[key.slice("custom:".length)] || "") : "";
                }) : []),
            ].join(" "),
            compareRows: (column, direction, left, right) => compareByColumn(column, direction, left, right),
            getRowKey: (item) => deviceKey(item),
            getRowClassName: (item) => (deviceKey(item) === state.selectedDeviceKey ? "is-selected" : ""),
            getRowAttributes: (item) => ({
                "data-device-key": deviceKey(item),
            }),
            onBackgroundContextMenu: ({ event, x, y }) => {
                closeTopMenu();
                if (openInventoryBatchContextMenu(x, y)) {
                    return;
                }
                if (openSelectedDeviceContextMenuFromTreeBody(event)) {
                    return;
                }
                openInventoryBackgroundContextMenu(x, y);
            },
        });
        this._columns = [];
    }

    render() {
        const rows = inventorySourceRows();
        const filterType = String(inventoryTypeFilter.value || "").trim();
        this._columns = buildDeviceTreeColumns({
            rows,
            typeCode: filterType,
            includeType: true,
            includeNotify: true,
            includeConfig: true,
            includeActions: true,
            includeCustomFields: Boolean(filterType),
        });
        return super.render();
    }
}

function ensureInventoryTreeView() {
    const BaseClass = window.NMPSharedUi?.treeView?.SharedTreeView;
    if (!BaseClass) {
        return null;
    }
    if (!(inventoryTreeView instanceof MonitoringInventoryTreeView)) {
        inventoryTreeView = new MonitoringInventoryTreeView();
    }
    return inventoryTreeView;
}

function compareDeviceTypesModalRows(column, direction, left, right) {
    const dir = direction === "desc" ? -1 : 1;
    if (column === "monitoring_enabled" || column === "config_backups_enabled" || column === "credentials_enabled") {
        const leftValue = Boolean(left?.[column]);
        const rightValue = Boolean(right?.[column]);
        if (leftValue !== rightValue) {
            return (leftValue ? 1 : -1) * dir;
        }
    }
    return String(left?.label || "").localeCompare(String(right?.label || ""), undefined, { sensitivity: "base" }) * dir;
}

function compareConfigFileRows(column, direction, left, right) {
    const dir = direction === "desc" ? -1 : 1;
    if (column === "size_bytes") {
        return (Number(left?.size_bytes || 0) - Number(right?.size_bytes || 0)) * dir;
    }
    return String(left?.[column] || "").localeCompare(String(right?.[column] || ""), undefined, { sensitivity: "base" }) * dir;
}

function configFileDeviceLabel(row) {
    return [
        String(row?.device_type_label || row?.device_type || "").trim(),
        String(row?.device_name || "").trim(),
    ].filter(Boolean).join(" / ") || "Equipement inconnu";
}

function normalizeConfigFileRow(row) {
    return {
        id: String(row?.id || "").trim(),
        name: String(row?.name || "config.cfg").trim() || "config.cfg",
        path: String(row?.path || "").trim(),
        modified_at: String(row?.modified_at || "").trim(),
        detail: String(row?.detail || "").trim(),
        size_bytes: Number(row?.size_bytes || 0),
        sync_status: String(row?.sync_status || "").trim(),
        sync_error: String(row?.sync_error || "").trim(),
        device_type: String(row?.device_type || "").trim(),
        device_type_label: String(row?.device_type_label || "").trim(),
        device_name: String(row?.device_name || "").trim(),
        device_ip: String(row?.device_ip || "").trim(),
        legacy: !String(row?.id || "").trim(),
    };
}

class ConfigFilesTreeView extends (window.NMPSharedUi?.treeView?.SharedTreeView || class {}) {
    constructor(options = {}) {
        const mode = String(options.mode || "device").trim();
        const prefix = mode === "library" ? "config-library" : "config-files";
        super({
            headElement: document.getElementById(`${prefix}-head`),
            bodyElement: document.getElementById(`${prefix}-body`),
            searchInput: document.getElementById(`${prefix}-search`),
            sortState: mode === "library" ? state.configLibrarySort : state.configFilesModalSort,
            columnAttr: `${prefix}-col`,
            renderHead: true,
            manageSortBinding: true,
            manageSearchBinding: true,
            searchThreshold: 5,
            emptyMessage: "Aucun fichier de configuration.",
            getColumns: () => [
                { key: "name", label: "Nom" },
                ...(mode === "library" ? [{ key: "device_name", label: "Equipement" }] : []),
                { key: "modified_at", label: "Modifie" },
                { key: "size_bytes", label: "Taille" },
                { key: "sync_status", label: "Etat" },
                { key: "", label: "Actions" },
            ],
            getRows: () => (mode === "library" ? state.configLibraryRows : state.configFilesModalRows),
            searchText: (row) => [
                row?.name,
                row?.detail,
                row?.modified_at,
                row?.sync_status,
                row?.sync_error,
                configFileDeviceLabel(row),
            ].join(" "),
            compareRows: (column, direction, left, right) => compareConfigFileRows(column, direction, left, right),
            getRowKey: (row, index) => String(row?.id || row?.path || `config-file-${index}`),
            renderRowCells: (row) => {
                const fileId = String(row?.id || "").trim();
                const canDelete = Boolean(fileId);
                const status = [
                    String(row?.sync_status || "").trim(),
                    row?.legacy ? "heritage" : "",
                ].filter(Boolean).join(" / ");
                return `
                    <td>
                        <strong>${escapeHtml(row?.name || "config.cfg")}</strong>
                        ${row?.detail ? `<p class="muted">${escapeHtml(row.detail)}</p>` : ""}
                        ${row?.sync_error ? `<p class="error-text">${escapeHtml(row.sync_error)}</p>` : ""}
                    </td>
                    ${mode === "library" ? `<td>${escapeHtml(configFileDeviceLabel(row))}</td>` : ""}
                    <td>${escapeHtml(row?.modified_at || "")}</td>
                    <td>${escapeHtml(formatFileSize(row?.size_bytes))}</td>
                    <td>${escapeHtml(status || "-")}</td>
                    <td class="inventory-row-actions">
                        ${fileId ? createIconActionButtonMarkup({
                            icon: "download",
                            action: "config-file:download",
                            title: "Telecharger",
                            data: { file_id: fileId },
                        }) : ""}
                        ${createIconActionButtonMarkup({
                            icon: "delete",
                            danger: true,
                            action: "config-file:delete",
                            title: canDelete ? "Supprimer" : "Ancien fichier non supprimable depuis cette vue",
                            data: { file_id: fileId, file_name: row?.name || "" },
                            disabled: !canDelete,
                        })}
                    </td>
                `;
            },
        });
        this.mode = mode;
    }
}

class DeviceTypesModalTreeView extends (window.NMPSharedUi?.treeView?.SharedTreeView || class {}) {
    constructor() {
        super({
            headElement: document.getElementById("device-types-head"),
            bodyElement: document.getElementById("device-types-body"),
            searchInput: document.getElementById("modal-device-types-search"),
            sortState: state.deviceTypesModalSort,
            columnAttr: "types-col",
            renderHead: true,
            manageSortBinding: false,
            manageSearchBinding: false,
            selectable: true,
            searchThreshold: 5,
            emptyMessage: "Aucun type d'equipement.",
            getColumns: () => [
                { key: "label", label: "Libelle" },
                { key: "monitoring_enabled", label: "Monitoring", className: "cell-center" },
                { key: "config_backups_enabled", label: "Configs", className: "cell-center" },
                { key: "credentials_enabled", label: "Gestion identifiants", className: "cell-center" },
                { key: "", label: "Actions" },
            ],
            getRows: () => (Array.isArray(state.deviceTypesModalRows) ? state.deviceTypesModalRows : []),
            searchText: (item) => `${String(item?.label || "")} ${String(item?.code || "")}`,
            compareRows: (column, direction, left, right) => compareDeviceTypesModalRows(column, direction, left, right),
            getRowKey: (item) => String(item?.code || ""),
            getRowAttributes: (item) => ({
                "data-type-code": String(item?.code || ""),
            }),
            onBackgroundContextMenu: ({ x, y }) => {
                closeTopMenu();
                openDeviceTypesBackgroundContextMenu(x, y);
            },
            renderRowCells: (item) => {
                const code = String(item?.code || "");
                return `
                    <td>${escapeHtml(String(item?.label || code))}</td>
                    <td class="cell-center">${item?.monitoring_enabled ? "Oui" : "Non"}</td>
                    <td class="cell-center">${item?.config_backups_enabled ? "Oui" : "Non"}</td>
                    <td class="cell-center">${item?.credentials_enabled ? "Oui" : "Non"}</td>
                    <td class="cell-actions">
                        ${createActionButtonMarkup({
                            preset: "settings",
                            action: "types:edit",
                            title: "Modifier",
                            data: { type_code: code },
                            showLabel: false,
                            label: "",
                        })}
                        ${createActionButtonMarkup({
                            className: "toolbar-btn",
                            type: "button",
                            action: "types:delete",
                            label: "Supprimer",
                            iconHtml: "&#128465;",
                            data: { type_code: code },
                            disabled: !item?.can_delete,
                        })}
                    </td>
                `;
            },
            onRowsRendered: (rows) => {
                const body = this.bodyElement;
                if (!(body instanceof HTMLElement)) {
                    return;
                }
                const rowsByCode = new Set((Array.isArray(rows) ? rows : []).map((row) => String(row?.code || "").trim()));
                for (const tr of Array.from(body.querySelectorAll("tr[data-type-code]"))) {
                    const typeCode = String(tr.getAttribute("data-type-code") || "").trim();
                    if (!typeCode || !rowsByCode.has(typeCode)) {
                        continue;
                    }
                    tr.addEventListener("dblclick", async (event) => {
                        const target = event.target;
                        if (target instanceof Element && target.closest("[data-tree-select-row]")) {
                            return;
                        }
                        event.preventDefault();
                        closeContextMenu();
                        await openDeviceTypeEditorModal(typeCode, {});
                    });
                    tr.addEventListener("contextmenu", (event) => {
                        const target = event.target;
                        if (target instanceof Element && target.closest("[data-tree-select-row]")) {
                            return;
                        }
                        event.preventDefault();
                        event.stopPropagation();
                        closeTopMenu();
                        const selectedRows = selectedDeviceTypeRowsIncluding(typeCode);
                        if (selectedRows.length) {
                            openDeviceTypeBatchContextMenu(event.clientX, event.clientY, selectedRows);
                            return;
                        }
                        openDeviceTypeContextMenu(event.clientX, event.clientY, typeCode);
                    });
                }
            },
        });
    }
}

function ensureDeviceTypesTreeView() {
    const BaseClass = window.NMPSharedUi?.treeView?.SharedTreeView;
    if (!BaseClass) {
        return null;
    }
    const head = document.getElementById("device-types-head");
    const body = document.getElementById("device-types-body");
    if (!(head instanceof HTMLElement) || !(body instanceof HTMLElement)) {
        return null;
    }
    if (
        deviceTypesTreeView instanceof DeviceTypesModalTreeView
        && deviceTypesTreeView.headElement === head
        && deviceTypesTreeView.bodyElement === body
    ) {
        return deviceTypesTreeView;
    }
    deviceTypesTreeView = new DeviceTypesModalTreeView();
    return deviceTypesTreeView;
}

function deviceTypesModalRowsFromTypes(types) {
    return (Array.isArray(types) ? types : []).map((item) => {
        const code = String(item?.code || "");
        const label = String(item?.label || code || "");
        return {
            code,
            label,
            monitoring_enabled: Boolean(item?.monitoring_enabled),
            config_backups_enabled: Boolean(item?.config_backups_enabled),
            credentials_enabled: Boolean(item?.credentials_enabled),
            can_delete: !Boolean(item?.is_system),
            is_system: Boolean(item?.is_system),
            version_token: String(item?.version_token || ""),
        };
    });
}

function formatDetailValue(value) {
    const normalized = String(value ?? "").trim();
    return normalized || "-";
}

function normalizeCredentialRevealUnlockSeconds(value) {
    const parsed = Number.parseInt(String(value ?? DEFAULT_CREDENTIAL_REVEAL_UNLOCK_SECONDS), 10);
    if (!Number.isFinite(parsed)) {
        return DEFAULT_CREDENTIAL_REVEAL_UNLOCK_SECONDS;
    }
    return Math.max(MIN_CREDENTIAL_REVEAL_UNLOCK_SECONDS, Math.min(MAX_CREDENTIAL_REVEAL_UNLOCK_SECONDS, parsed));
}

function ensureCredentialRevealSessionFresh() {
    if (!state.credentialRevealSessionPassword || !state.credentialRevealUnlockUntilMs) {
        return false;
    }
    if (Date.now() < state.credentialRevealUnlockUntilMs) {
        return true;
    }
    clearCredentialRevealState({ refresh: false });
    return false;
}

function clearCredentialRevealState(options = {}) {
    const refresh = Boolean(options?.refresh);
    state.credentialRevealSessionPassword = "";
    state.credentialRevealUnlockUntilMs = 0;
    state.revealedDevicePasswords = {};
    if (state.credentialRevealUnlockTimer) {
        window.clearTimeout(state.credentialRevealUnlockTimer);
        state.credentialRevealUnlockTimer = null;
    }
    if (refresh) {
        if (state.snapshot) {
            renderDevices(state.snapshot);
        }
        renderInventoryDetail();
    }
}

function applyCredentialRevealUnlockDurationFromSettings(settings) {
    const configured = normalizeCredentialRevealUnlockSeconds(settings?.credential_reveal_unlock_seconds);
    state.credentialRevealUnlockDurationSeconds = configured;
}

function applyCredentialRevealSessionPassword(sessionPassword) {
    state.credentialRevealSessionPassword = String(sessionPassword || "");
    state.credentialRevealUnlockUntilMs = Date.now() + (state.credentialRevealUnlockDurationSeconds * 1000);
    if (state.credentialRevealUnlockTimer) {
        window.clearTimeout(state.credentialRevealUnlockTimer);
    }
    state.credentialRevealUnlockTimer = window.setTimeout(() => {
        clearCredentialRevealState({ refresh: true });
        inventoryFeedback.textContent = "Session d'affichage des identifiants expiree.";
    }, Math.max(1, state.credentialRevealUnlockDurationSeconds * 1000));
}

function isCredentialRevealSessionUnlocked() {
    return ensureCredentialRevealSessionFresh();
}

function revealedDevicePassword(device) {
    if (!ensureCredentialRevealSessionFresh()) {
        return "";
    }
    return String(state.revealedDevicePasswords[deviceKey(device)] || "");
}

function devicePasswordMask(device) {
    const explicitMask = String(device?.device_password_masked || "").trim();
    if (explicitMask) {
        return explicitMask;
    }
    return Boolean(device?.has_device_password) ? "****" : "";
}

function hasStoredDevicePassword(device) {
    return Boolean(devicePasswordMask(device));
}

function hasStoredDeviceCredentials(device) {
    return Boolean(String(device?.device_login || "").trim()) || hasStoredDevicePassword(device);
}

async function typeHasStoredDeviceCredentials(typeCode) {
    const normalizedTypeCode = String(typeCode || "").trim().toLowerCase();
    let credentialRows = [];
    try {
        const query = normalizedTypeCode ? `?device_type=${encodeURIComponent(normalizedTypeCode)}` : "";
        credentialRows = await requestJson(`/devices${query}`);
    } catch (_error) {
        credentialRows = state.inventory.filter((item) => (
            String(item?.device_type || "").trim().toLowerCase() === normalizedTypeCode
        ));
    }
    return Array.isArray(credentialRows) && credentialRows.some((item) => {
        if (String(item?.device_type || "").trim().toLowerCase() !== normalizedTypeCode) {
            return false;
        }
        return hasStoredDeviceCredentials(item);
    });
}

function renderInventoryPasswordCell(device) {
    const revealed = revealedDevicePassword(device);
    const masked = devicePasswordMask(device);
    const hasStored = Boolean(masked);
    const hasRevealed = Boolean(revealed);
    const displayValue = hasRevealed ? revealed : (hasStored ? masked : "-");
    const valueClass = hasRevealed ? "inventory-password-mask is-clear" : "inventory-password-mask";
    const revealButton = createIconActionButtonMarkup({
        iconHtml: "&#128065;",
        iconClass: "reveal-password",
        title: hasStored ? "Afficher le mot de passe" : "Aucun mot de passe stocke",
        ariaLabel: hasStored ? `Afficher le mot de passe de ${device?.name || "cet equipement"}` : "Aucun mot de passe stocke",
        data: { row_action: "reveal_password" },
        disabled: !hasStored,
    });
    return `<div class="inventory-password-cell"><span class="${valueClass}">${escapeHtml(displayValue)}</span>${revealButton}</div>`;
}

function createDevicePasswordEditFieldMarkup({ device = null, value = "", wide = false } = {}) {
    const hasStored = Boolean(device && hasStoredDevicePassword(device));
    const revealed = device ? revealedDevicePassword(device) : "";
    const statusValue = revealed || (hasStored ? devicePasswordMask(device) : "");
    const statusClass = revealed ? "inventory-password-mask is-clear" : "inventory-password-mask";
    const revealButton = createIconActionButtonMarkup({
        iconHtml: "&#128065;",
        iconClass: "reveal-password",
        title: hasStored ? "Afficher le mot de passe stocke" : "Aucun mot de passe stocke",
        ariaLabel: hasStored ? `Afficher le mot de passe de ${device?.name || "cet equipement"}` : "Aucun mot de passe stocke",
        action: "device-password:reveal-form",
        data: {
            device_type: String(device?.device_type || ""),
            device_id: String(device?.id || ""),
        },
        disabled: !hasStored,
    });
    return `
        <label class="field ${wide ? "wide" : ""}">
            <span>${escapeHtml(fieldLabel("device_password"))}</span>
            <div class="device-password-edit-control">
                <input
                    name="device_password"
                    type="${revealed ? "text" : "password"}"
                    value="${escapeHtml(value || "")}"
                    placeholder="${hasStored ? escapeAttribute(devicePasswordMask(device)) : ""}"
                    autocomplete="new-password"
                >
                ${revealButton}
            </div>
            <span class="device-password-edit-status" data-device-password-status>
                ${statusValue ? `Stocke: <span class="${statusClass}">${escapeHtml(statusValue)}</span>` : "Aucun mot de passe stocke."}
            </span>
        </label>
    `;
}

function deviceKey(device) {
    return `${device.device_type}:${device.id}`;
}

function normalizeIpKey(value) {
    const raw = String(value || "").trim();
    if (!raw) {
        return "";
    }
    const parts = raw.split(".");
    if (parts.length !== 4) {
        return raw.toLowerCase();
    }
    const normalized = parts.map((part) => Number.parseInt(part, 10));
    if (normalized.some((part) => !Number.isInteger(part) || part < 0 || part > 255)) {
        return raw.toLowerCase();
    }
    return normalized.join(".");
}

function knownInventoryIpSet() {
    const out = new Set();
    for (const item of state.inventory || []) {
        const key = normalizeIpKey(item?.ip || "");
        if (key) {
            out.add(key);
        }
    }
    return out;
}

function inventoryDeviceByIp(ip) {
    const wanted = normalizeIpKey(ip);
    if (!wanted) {
        return null;
    }
    return (state.inventory || []).find((item) => normalizeIpKey(item?.ip || "") === wanted) || null;
}

function inventoryDeviceByTypeAndId(deviceType, deviceId) {
    const normalizedType = String(deviceType || "").trim().toLowerCase();
    const normalizedId = String(deviceId || "").trim();
    if (!normalizedType || !normalizedId) {
        return null;
    }
    return (state.inventory || []).find((item) => (
        String(item?.device_type || "").trim().toLowerCase() === normalizedType
        && String(item?.id || "").trim() === normalizedId
    )) || null;
}

async function revealDevicePasswordIntoForm(actionButton, form, feedbackNode) {
    if (!(actionButton instanceof HTMLElement) || !(form instanceof HTMLElement)) {
        return;
    }
    const deviceType = String(actionButton.dataset.deviceType || form.dataset.deviceType || "").trim();
    const deviceId = String(actionButton.dataset.deviceId || form.dataset.deviceId || "").trim();
    const device = inventoryDeviceByTypeAndId(deviceType, deviceId);
    if (!device) {
        if (feedbackNode instanceof HTMLElement) {
            feedbackNode.textContent = "Equipement introuvable pour afficher le mot de passe.";
        }
        return;
    }
    const payload = await requestDevicePasswordReveal(device, { feedbackNode });
    const password = String(payload?.device_password || "");
    if (!password) {
        return;
    }
    const passwordInput = form.querySelector('[name="device_password"]');
    if (passwordInput instanceof HTMLInputElement) {
        passwordInput.type = "text";
        passwordInput.value = password;
    }
    const status = form.querySelector("[data-device-password-status]");
    if (status instanceof HTMLElement) {
        status.innerHTML = `Stocke: <span class="inventory-password-mask is-clear">${escapeHtml(password)}</span>`;
    }
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
    state.contextMenuTypeCode = "";
    state.networkScanContextIp = "";
}

function closeTopMenu() {
    if (topMenuController) {
        topMenuController.close();
        return;
    }
    const sharedCloseTopMenu = window.NMPSharedUi?.closeTopMenu;
    if (typeof sharedCloseTopMenu === "function") {
        sharedCloseTopMenu(state, topMenuPanel, [menuModules, menuSupervision, menuEquipments, menuTools, menuHelp]);
    }
}

async function handleAuthFailure() {
    if (authFailureHandling) {
        return;
    }
    authFailureHandling = true;
    teardownRealtime();
    persistToken("");
    clearSessionState();
    state.snapshot = null;
    state.inventory = [];
    state.deviceTypes = [];
    closeProfileMenu();
    closeTopMenu();
    closeContextMenu();
    closeModal();
    redirectToPortal();
}

function closeProfileMenu() {
    profileMenuController?.close?.();
}

function resolveInlineModalHost(hostKey) {
    const normalized = String(hostKey || "").trim().toLowerCase();
    if (normalized === "inventory") {
        return inventoryInlineModalHost;
    }
    return null;
}

function exitInlineModalMode() {
    if (!(appModal instanceof HTMLElement)) {
        return;
    }
    const activeHost = resolveInlineModalHost(state.activeInlineModalHost);
    if (activeHost instanceof HTMLElement) {
        activeHost.hidden = true;
    }
    appModal.classList.remove("app-modal-inline");
    if (appModalDefaultParent instanceof HTMLElement) {
        if (appModalDefaultNextSibling && appModalDefaultNextSibling.parentNode === appModalDefaultParent) {
            appModalDefaultParent.insertBefore(appModal, appModalDefaultNextSibling);
        } else {
            appModalDefaultParent.appendChild(appModal);
        }
    }
    state.activeInlineModalHost = "";
}

function enterInlineModalMode(hostKey) {
    if (!(appModal instanceof HTMLElement)) {
        return false;
    }
    const host = resolveInlineModalHost(hostKey);
    if (!(host instanceof HTMLElement)) {
        exitInlineModalMode();
        return false;
    }
    if (state.activeInlineModalHost && state.activeInlineModalHost !== hostKey) {
        exitInlineModalMode();
    }
    host.hidden = false;
    host.appendChild(appModal);
    appModal.classList.add("app-modal-inline");
    state.activeInlineModalHost = hostKey;
    return true;
}

function openModal(title, bodyMarkup, options = {}) {
    const inlineHostKey = String(options.inlineHost || "").trim().toLowerCase();
    if (inlineHostKey) {
        enterInlineModalMode(inlineHostKey);
    } else {
        exitInlineModalMode();
    }
    if (appModalClose instanceof HTMLElement) {
        appModalClose.hidden = Boolean(options.hideClose);
    }
    if (modalController) {
        modalController.open(title, bodyMarkup, options);
        return;
    }
    appModalTitle.textContent = title;
    appModalBody.innerHTML = bodyMarkup;
    appModalPanel.style.width = options.width || "min(980px, calc(100vw - 40px))";
    appModal.hidden = false;
}

function closeModal() {
    if (modalController) {
        modalController.close("manual");
        exitInlineModalMode();
        return;
    }
    if (state.networkToolAbortController) {
        state.networkToolAbortController.abort();
        state.networkToolAbortController = null;
    }
    if (state.networkScanAbortController) {
        state.networkScanAbortController.abort();
        state.networkScanAbortController = null;
    }
    appModal.hidden = true;
    appModalBody.innerHTML = "";
    if (appModalClose instanceof HTMLElement) {
        appModalClose.hidden = false;
    }
    exitInlineModalMode();
    state.configManagerDeviceKey = "";
    clearTypeSchemaEditorNavigationState();
    clearWatermarkEditorDraft();
    state.remoteDesktopLaunchDeviceKey = "";
}

function clearTypeSchemaEditorState() {
    state.typeSchemaEditor = null;
    state.typeSchemaDrag = null;
}

function clearTypeSchemaEditorNavigationState() {
    clearTypeSchemaEditorState();
    state.typeSchemaEditorContext = null;
}

function captureTypeSchemaEditorContext() {
    return {
        returnToTypesList: hasInlineDeviceTypesView(),
        callerSection: String(state.currentSection || "").trim().toLowerCase(),
    };
}

async function reopenDeviceTypesSection(message = "") {
    state.currentSection = "device_types";
    closeModal();
    await openDeviceTypesModal();
    if (message) {
        const listFeedback = document.getElementById("modal-device-types-feedback");
        if (listFeedback) {
            listFeedback.textContent = message;
        }
    }
}

async function returnFromTypeSchemaEditor(message = "") {
    const context = state.typeSchemaEditorContext && typeof state.typeSchemaEditorContext === "object"
        ? state.typeSchemaEditorContext
        : { returnToTypesList: false, callerSection: "" };
    clearTypeSchemaEditorNavigationState();

    if (context.returnToTypesList || context.callerSection === "device_types") {
        await reopenDeviceTypesSection(message);
        return;
    }

    closeModal();
    if (context.callerSection) {
        state.currentSection = context.callerSection;
    }
    renderSection();
    if (message && isInventoryWorkspaceSection(context.callerSection) && inventoryFeedback instanceof HTMLElement) {
        inventoryFeedback.textContent = message;
    }
}

function closeActiveModal() {
    if (state.typeSchemaEditor && state.typeSchemaEditorContext) {
        returnFromTypeSchemaEditor().catch((error) => {
            const feedback = document.getElementById("modal-device-type-schema-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        });
        return;
    }
    closeModal();
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
    if (builtin === "remote_desktop") {
        return Boolean(ip);
    }
    return false;
}

function builtinUnsupportedInBrowser(builtin) {
    const key = String(builtin || "").trim().toLowerCase();
    return key === "ssh";
}

function devicePlatformLabel(device) {
    return String(device?.device_subtype || device?.type || "Autre").trim() || "Autre";
}

function schemaRemoteActionsForDevice(schema, device) {
    const platform = devicePlatformLabel(device);
    return (schema?.actions || [])
        .filter((row) => actionAllowsOs(String(row?.os_scope || ""), platform))
        .map((row) => ({
            ...row,
            action_key: String(row?.action_key || "").trim().toLowerCase(),
            target_kind: String(row?.target_kind || "").trim().toLowerCase(),
            target_value: String(row?.target_value || row?.action_key || "").trim().toLowerCase(),
            sort_order: Number(row?.sort_order || 0),
        }))
        .filter((row) => Boolean(row.action_key))
        .sort((left, right) => {
            const byOrder = Number(left.sort_order || 0) - Number(right.sort_order || 0);
            if (byOrder !== 0) {
                return byOrder;
            }
            return String(left.label || left.action_key || "").localeCompare(String(right.label || right.action_key || ""), undefined, { sensitivity: "base" });
        });
}

function resolveRemoteActionForDevice(device, schema, preferredActionKey = "") {
    const actions = schemaRemoteActionsForDevice(schema, device);
    if (!actions.length) {
        return { actions, selected: null };
    }
    const normalize = (value) => String(value || "").trim().toLowerCase();
    const preferred = normalize(preferredActionKey);
    const configured = normalize(device?.action_double_click || "");
    const fallback = normalize(defaultActionForPlatform(device?.device_type || "", devicePlatformLabel(device)));
    const matches = (row, key) => {
        if (!key) {
            return false;
        }
        return normalize(row?.action_key) === key || normalize(row?.target_value) === key;
    };
    const selected = actions.find((row) => matches(row, preferred))
        || actions.find((row) => matches(row, configured))
        || actions.find((row) => matches(row, fallback))
        || actions[0];
    return { actions, selected: selected || null };
}

function remoteActionWebStatus(device, actionRow) {
    const actionKey = String(actionRow?.action_key || "").trim().toLowerCase();
    if (!actionKey) {
        return {
            ok: false,
            builtin: "",
            hint: "Indisponible",
            message: "Action distante introuvable.",
        };
    }
    const targetKind = String(actionRow?.target_kind || "").trim().toLowerCase();
    if (targetKind !== "builtin") {
        return {
            ok: false,
            builtin: "",
            hint: "Non supporte web",
            message: `Action ${actionKey} non supportee sur l'interface web.`,
        };
    }
    const builtin = String(actionRow?.target_value || actionRow?.action_key || "").trim().toLowerCase();
    if (builtinUnsupportedInBrowser(builtin)) {
        return {
            ok: false,
            builtin,
            hint: "Bientot web",
            message: `${actionLabel(builtin)} n'est pas encore disponible depuis le navigateur.`,
        };
    }
    if (!canRunBuiltinAction(device, builtin)) {
        return {
            ok: false,
            builtin,
            hint: "Infos manquantes",
            message: `Informations manquantes pour lancer ${actionLabel(builtin)}.`,
        };
    }
    return { ok: true, builtin, hint: "", message: "" };
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
        const resolvedWebUrl = resolveDeviceWebUrl({ ip, subtype, webUrl });
        if (resolvedWebUrl) {
            return resolvedWebUrl;
        }
    }
    return "";
}

function resolveDeviceWebUrl({ ip, subtype, webUrl }) {
    const normalizedIp = String(ip || "").trim();
    const normalizedSubtype = String(subtype || "").trim().toLowerCase();
    const raw = String(webUrl || "").trim();
    if (!raw) {
        if (normalizedSubtype === "dsm" && normalizedIp) {
            return `http://${normalizedIp}:5000`;
        }
        return normalizedIp ? `http://${normalizedIp}` : "";
    }
    const numeric = raw.match(/^:?(?<port>\d{1,5})$/);
    if (numeric && numeric.groups?.port) {
        const port = Number(numeric.groups.port);
        return normalizedIp && port >= 1 && port <= 65535 ? `http://${normalizedIp}:${port}` : "";
    }
    if (/^[a-z][a-z0-9+.-]*:\/\//i.test(raw)) {
        return raw;
    }
    if (/^[^/\s:]+:\d{1,5}(?:[/?#]|$)/.test(raw)) {
        return `http://${raw}`;
    }
    if (raw.startsWith(":")) {
        const port = Number(raw.slice(1));
        return normalizedIp && port >= 1 && port <= 65535 ? `http://${normalizedIp}:${port}` : "";
    }
    if (raw.startsWith("/") && normalizedIp) {
        return `http://${normalizedIp}${raw}`;
    }
    return /^[^\s/]+(?:[/?#].*)?$/.test(raw) ? `http://${raw}` : raw;
}

function splitDeviceWebUrlForForm({ ip = "", subtype = "", webUrl = "" } = {}) {
    const resolved = resolveDeviceWebUrl({ ip, subtype, webUrl }) || (String(ip || "").trim() ? `http://${String(ip || "").trim()}` : "http://");
    const fallback = {
        url: resolved,
        port: "",
        placeholder: resolved.toLowerCase().startsWith("https://") ? "443" : "80",
    };
    try {
        const parsed = new URL(resolved);
        const defaultPort = parsed.protocol === "https:" ? "443" : "80";
        const explicitPort = String(parsed.port || "");
        parsed.port = "";
        return {
            url: parsed.toString().replace(/\/$/, ""),
            port: explicitPort && explicitPort !== defaultPort ? explicitPort : "",
            placeholder: defaultPort,
        };
    } catch (_error) {
        const match = resolved.match(/^(?<prefix>https?:\/\/[^/:?#]+)(?::(?<port>\d{1,5}))(?<suffix>[/?#].*)?$/i);
        if (match?.groups) {
            const prefix = String(match.groups.prefix || "");
            const suffix = String(match.groups.suffix || "");
            const port = String(match.groups.port || "");
            const placeholder = prefix.toLowerCase().startsWith("https://") ? "443" : "80";
            return {
                url: `${prefix}${suffix}`,
                port: port && port !== placeholder ? port : "",
                placeholder,
            };
        }
    }
    return fallback;
}

function composeDeviceWebUrlFromParts(urlValue, portValue, ipValue = "") {
    const fallbackUrl = String(ipValue || "").trim() ? `http://${String(ipValue || "").trim()}` : "";
    const rawUrl = String(urlValue || fallbackUrl || "").trim();
    const rawPort = String(portValue || "").trim();
    if (!rawPort) {
        return rawUrl;
    }
    const port = Number.parseInt(rawPort, 10);
    if (!Number.isFinite(port) || port < 1 || port > 65535) {
        return rawUrl;
    }
    const withScheme = /^[a-z][a-z0-9+.-]*:\/\//i.test(rawUrl) ? rawUrl : `http://${rawUrl}`;
    try {
        const parsed = new URL(withScheme);
        parsed.port = String(port);
        return parsed.toString().replace(/\/$/, "");
    } catch (_error) {
        return `${rawUrl.replace(/:\d{1,5}$/, "")}:${port}`;
    }
}

function switchProxyDeviceLocator(device) {
    const normalize = (value) => String(value || "")
        .trim()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/\s+/g, "_")
        .replace(/[^A-Za-z0-9_-]+/g, "_")
        .replace(/_+/g, "_")
        .replace(/^_+|_+$/g, "");
    const nameLocator = normalize(device?.name);
    if (nameLocator) {
        return nameLocator;
    }
    return normalize(device?.id);
}

function switchUiProxyUrl(device) {
    const typeCode = String(device?.device_type || "").trim();
    const deviceLocator = switchProxyDeviceLocator(device);
    if (!typeCode || !deviceLocator) {
        return "";
    }
    const token = String(state.token || "").trim();
    if (!token) {
        return "";
    }
    const path = `/devices/${encodeURIComponent(typeCode)}/${encodeURIComponent(deviceLocator)}/web-ui`;
    return `${path}?token=${encodeURIComponent(token)}`;
}

function shouldUseSwitchWebProxy(device) {
    return String(device?.device_type || "").trim().toLowerCase() === "switch";
}

function sanitizeFilePart(value, fallback = "device") {
    const raw = String(value || "").trim();
    if (!raw) {
        return fallback;
    }
    return raw.replace(/[<>:"/\\|?*\x00-\x1F]/g, "_").replace(/\s+/g, "_");
}

function buildRdpFileContent(device) {
    const ip = String(device?.ip || "").trim();
    const label = String(device?.name || ip || "Remote Desktop").trim();
    return [
        "screen mode id:i:2",
        "use multimon:i:0",
        "desktopwidth:i:1920",
        "desktopheight:i:1080",
        "session bpp:i:32",
        "compression:i:1",
        "keyboardhook:i:2",
        "audiocapturemode:i:0",
        "videoplaybackmode:i:1",
        "connection type:i:7",
        "networkautodetect:i:1",
        "bandwidthautodetect:i:1",
        "displayconnectionbar:i:1",
        "disable wallpaper:i:0",
        "allow font smoothing:i:1",
        "allow desktop composition:i:1",
        "prompt for credentials:i:1",
        `full address:s:${ip}`,
        `alternate full address:s:${ip}`,
        `remoteapplicationname:s:${label}`,
    ].join("\r\n");
}

function buildRemoteDesktopBlob(device) {
    return new Blob([buildRdpFileContent(device)], { type: "application/x-rdp" });
}

function remoteDesktopShortcutFilename(device) {
    const ip = String(device?.ip || "").trim();
    return `${sanitizeFilePart(device?.name, "remote")}_${sanitizeFilePart(ip, "host")}.rdp`;
}

function remoteDesktopShortcutDownloadUrl(device) {
    const typeCode = String(device?.device_type || "").trim();
    const deviceId = String(device?.id || "").trim();
    const token = String(state.token || "").trim();
    if (!typeCode || !deviceId || !token) {
        return "";
    }
    return `/devices/${encodeURIComponent(typeCode)}/${encodeURIComponent(deviceId)}/remote-desktop/shortcut?token=${encodeURIComponent(token)}`;
}

function downloadTextFile(content, filename, mimeType = "text/plain;charset=utf-8") {
    const blob = new Blob([content], { type: mimeType });
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => window.URL.revokeObjectURL(url), 1200);
}

async function downloadRemoteDesktopShortcut(device) {
    const ip = String(device?.ip || "").trim();
    if (!ip) {
        throw new Error("IP manquante pour creer le raccourci Remote Desktop.");
    }
    const filename = remoteDesktopShortcutFilename(device);
    const blob = buildRemoteDesktopBlob(device);
    const legacyNavigator = window.navigator;
    if (legacyNavigator && typeof legacyNavigator.msSaveOrOpenBlob === "function") {
        legacyNavigator.msSaveOrOpenBlob(blob, filename);
        return "prompted";
    }
    const sharedDownload = window.NMPSharedDownload;
    if (sharedDownload && typeof sharedDownload.triggerBrowserDownload === "function") {
        sharedDownload.triggerBrowserDownload(blob, filename);
        return "downloaded";
    }
    downloadTextFile(buildRdpFileContent(device), filename, "application/x-rdp");
    return "downloaded";
}

async function saveRemoteDesktopShortcutAs(device) {
    const ip = String(device?.ip || "").trim();
    if (!ip) {
        throw new Error("IP manquante pour enregistrer le raccourci Remote Desktop.");
    }
    const filename = remoteDesktopShortcutFilename(device);
    const blob = buildRemoteDesktopBlob(device);
    if (window.isSecureContext && typeof window.showSaveFilePicker === "function") {
        try {
            const handle = await window.showSaveFilePicker({
                suggestedName: filename,
                types: [
                    {
                        description: "Raccourci Remote Desktop",
                        accept: { "application/x-rdp": [".rdp"] },
                    },
                ],
            });
            const writable = await handle.createWritable();
            await writable.write(blob);
            await writable.close();
            return "saved_as";
        } catch (error) {
            if (error && (error.name === "AbortError" || error.name === "NotAllowedError")) {
                return "cancelled";
            }
            return downloadRemoteDesktopShortcut(device);
        }
    }
    return downloadRemoteDesktopShortcut(device);
}

function openRemoteDesktopShortcut(device) {
    const ip = String(device?.ip || "").trim();
    if (!ip) {
        throw new Error("IP manquante pour lancer Remote Desktop.");
    }
    const downloadUrl = remoteDesktopShortcutDownloadUrl(device);
    if (!downloadUrl) {
        return downloadRemoteDesktopShortcut(device);
    }
    const launcher = document.createElement("a");
    launcher.href = downloadUrl;
    launcher.rel = "noopener";
    launcher.style.display = "none";
    document.body.appendChild(launcher);
    launcher.click();
    launcher.remove();
    return "server_download";
}

function buildRemoteDesktopLaunchMarkup(device) {
    const deviceName = String(device?.name || "").trim() || "Equipement";
    const ip = String(device?.ip || "").trim() || "-";
    return `
        <section class="modal-section">
            <p class="muted">Prise en main Remote Desktop pour <strong>${escapeHtml(deviceName)}</strong> (${escapeHtml(ip)}).</p>
            <p class="muted">Choisir l'action a executer.</p>
        </section>
        ${createModalActionsMarkup({
            buttons: [
                { className: "primary-btn", type: "button", action: "rdp:launch-open", label: "Ouvrir" },
                { className: "toolbar-btn", type: "button", action: "rdp:launch-save", label: "Enregistrer" },
                { preset: "cancel" },
            ],
        })}
    `;
}

function openRemoteDesktopLaunchModal(device) {
    const key = deviceKey(device);
    state.remoteDesktopLaunchDeviceKey = key;
    openModal("Prise en main Remote Desktop", buildRemoteDesktopLaunchMarkup(device), {
        width: "min(680px, calc(100vw - 40px))",
    });
}

function resolveRemoteDesktopLaunchDevice() {
    const key = String(state.remoteDesktopLaunchDeviceKey || "").trim();
    if (!key) {
        return null;
    }
    return state.inventory.find((item) => deviceKey(item) === key) || null;
}

function escapeAttribute(value) {
    return escapeHtml(String(value || "")).replaceAll("`", "&#96;");
}

async function runBuiltinAction(device, builtin) {
    if (builtin === "remote_desktop") {
        openRemoteDesktopLaunchModal(device);
        return;
    }
    if (builtin === "web") {
        if (shouldUseSwitchWebProxy(device)) {
            const proxyUrl = switchUiProxyUrl(device);
            if (!proxyUrl) {
                inventoryFeedback.textContent = "Session invalide ou equipement incomplet pour l'ouverture UI web.";
                return;
            }
            window.open(proxyUrl, "_blank", "noopener,noreferrer");
            return;
        }
        const url = builtinActionUrl(device, "web");
        if (!url) {
            inventoryFeedback.textContent = "Action web indisponible sur cette interface web.";
            return;
        }
        window.open(url, "_blank", "noopener,noreferrer");
        return;
    }
    const url = builtinActionUrl(device, builtin);
    if (!url) {
        inventoryFeedback.textContent = `Action ${builtin} indisponible sur cette interface web.`;
        return;
    }
    window.open(url, "_blank", "noopener,noreferrer");
}

async function runRemoteAction(device, actionKey) {
    await ensureDeviceTypeSchema(device.device_type);
    const schema = state.deviceSchemas[device.device_type] || { actions: [] };
    const { selected } = resolveRemoteActionForDevice(device, schema, actionKey);
    if (!selected) {
        inventoryFeedback.textContent = "Action non disponible pour ce type / OS.";
        return;
    }
    const status = remoteActionWebStatus(device, selected);
    if (!status.ok) {
        inventoryFeedback.textContent = status.message;
        return;
    }
    await runBuiltinAction(device, status.builtin);
}

async function runDeviceDoubleClickAction(device) {
    await ensureDeviceTypeSchema(device.device_type);
    const schema = state.deviceSchemas[device.device_type] || { actions: [] };
    const { actions, selected } = resolveRemoteActionForDevice(device, schema, device.action_double_click || "");
    if (!actions.length) {
        inventoryFeedback.textContent = "Aucune action distante disponible pour ce type / OS.";
        return;
    }
    if (selected) {
        const preferredStatus = remoteActionWebStatus(device, selected);
        if (preferredStatus.ok) {
            await runBuiltinAction(device, preferredStatus.builtin);
            return;
        }
    }
    const fallback = actions.find((row) => remoteActionWebStatus(device, row).ok);
    if (!fallback) {
        inventoryFeedback.textContent = "Aucune action distante executable depuis le navigateur pour ce device.";
        return;
    }
    const fallbackStatus = remoteActionWebStatus(device, fallback);
    await runBuiltinAction(device, fallbackStatus.builtin);
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

function inventorySourceRows() {
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
        .filter((item) => !filterType || item.device_type === filterType);
}

function inventoryRows() {
    const tree = ensureInventoryTreeView();
    if (tree) {
        return tree.getVisibleRows();
    }
    const typedRows = inventorySourceRows();
    updateSearchVisibility(inventorySearch, typedRows.length, 5);
    return filterAndSortRows(typedRows, {
        query: String(inventorySearch.value || "").trim().toLowerCase(),
        searchText: (item) => [
            item.device_type,
            typeLabel(item.device_type),
            item.name,
            item.ip,
            item.description,
            item.web_url,
            item.ssh_user,
            item.device_login,
            item.has_saved_config ? "oui" : "non",
        ].join(" "),
        sortColumn: state.inventorySort.column,
        sortDirection: state.inventorySort.direction,
        compare: compareByColumn,
    });
}

function getSelectedDevice() {
    return inventoryRows().find((item) => deviceKey(item) === state.selectedDeviceKey) || null;
}

function getSelectedDeviceFromInventoryStore() {
    const selectedKey = String(state.selectedDeviceKey || "").trim();
    if (!selectedKey) {
        return null;
    }
    const statuses = statusMap();
    const item = (Array.isArray(state.inventory) ? state.inventory : []).find((entry) => deviceKey(entry) === selectedKey);
    if (!item) {
        return null;
    }
    const runtime = statuses.get(deviceKey(item)) || {};
    return {
        ...item,
        status: runtime.status || item.status || "idle",
        has_saved_config: Boolean(item.has_saved_config),
    };
}

function selectedInventoryRows() {
    const tree = ensureInventoryTreeView();
    if (!tree || typeof tree.getSelectedRows !== "function") {
        return [];
    }
    return tree.getSelectedRows();
}

function selectedSupervisionRows() {
    const tree = supervisionTreeView instanceof SupervisionDevicesTreeView ? supervisionTreeView : null;
    if (!tree || typeof tree.getSelectedRows !== "function") {
        return [];
    }
    return tree.getSelectedRows();
}

function selectedDeviceRows() {
    const rows = [...selectedInventoryRows(), ...selectedSupervisionRows()];
    const seen = new Set();
    return rows.filter((item) => {
        const key = deviceKey(item);
        if (!key || seen.has(key)) {
            return false;
        }
        seen.add(key);
        return true;
    });
}

function clearDeviceBatchSelection() {
    const tree = ensureInventoryTreeView();
    if (tree && typeof tree.clearSelection === "function") {
        tree.clearSelection();
    }
    const supervisionTree = supervisionTreeView instanceof SupervisionDevicesTreeView ? supervisionTreeView : null;
    if (supervisionTree && typeof supervisionTree.clearSelection === "function") {
        supervisionTree.clearSelection();
    }
    state.deviceBatchContextRows = [];
}

function selectedRowsIncluding(rows, target, keyFn) {
    const selected = Array.isArray(rows) ? rows : [];
    const resolveKey = typeof keyFn === "function" ? keyFn : (item) => String(item || "");
    const targetKey = target ? resolveKey(target) : "";
    if (!targetKey) {
        return selected;
    }
    return selected.some((item) => resolveKey(item) === targetKey) ? selected : [];
}

function selectedInventoryRowsIncluding(device) {
    return selectedRowsIncluding(selectedInventoryRows(), device, deviceKey);
}

function selectedSupervisionRowsIncluding(device) {
    return selectedRowsIncluding(selectedSupervisionRows(), device, deviceKey);
}

function activeDeviceBatchRows() {
    if (Array.isArray(state.deviceBatchContextRows) && state.deviceBatchContextRows.length) {
        return state.deviceBatchContextRows;
    }
    return selectedDeviceRows();
}

function selectedDeviceTypeRows() {
    const tree = ensureDeviceTypesTreeView();
    if (!tree || typeof tree.getSelectedRows !== "function") {
        return [];
    }
    return tree.getSelectedRows();
}

function selectedDeviceTypeRowsIncluding(typeCode) {
    const normalized = String(typeCode || "").trim();
    return selectedRowsIncluding(
        selectedDeviceTypeRows(),
        { code: normalized },
        (item) => String(item?.code || "").trim(),
    );
}

function activeDeviceTypeBatchRows() {
    if (Array.isArray(state.deviceTypeBatchContextRows) && state.deviceTypeBatchContextRows.length) {
        return state.deviceTypeBatchContextRows;
    }
    return selectedDeviceTypeRows();
}

function clearDeviceTypeBatchSelection() {
    const tree = ensureDeviceTypesTreeView();
    if (tree && typeof tree.clearSelection === "function") {
        tree.clearSelection();
    }
    state.deviceTypeBatchContextRows = [];
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
    return fields.filter((field) => {
        const key = String(field.field_key || "").trim().toLowerCase();
        return !["name", "ip", "description", "id_teamviewer", "type", "device_subtype", "action_double_click", "action_default_by_os", "web_url", "ssh_user", "device_login", "device_password", "config_saved", "notify"].includes(key);
    });
}

function tableCustomFieldDefinitions(deviceType) {
    return customFieldDefinitions(deviceType).filter((field) => schemaFieldVisibleInTable(field, false));
}

function systemFieldDefinition(deviceType, fieldKey) {
    const schema = state.deviceSchemas[deviceType];
    const fields = Array.isArray(schema?.fields) ? schema.fields : [];
    const target = String(fieldKey || "").trim().toLowerCase();
    return fields.find((field) => String(field?.field_key || "").trim().toLowerCase() === target) || null;
}

function typeFieldVisibleInTable(deviceType, fieldKey, fallback = false) {
    return schemaFieldVisibleInTable(systemFieldDefinition(deviceType, fieldKey), fallback);
}

function typeFieldVisibleInTableByDefault(deviceType, fieldKey) {
    return typeFieldVisibleInTable(deviceType, fieldKey, defaultShowInTableForField(fieldKey));
}

function contextFieldVisibleInTable({ rows = [], typeCode = "", fieldKey = "" } = {}) {
    const normalizedType = String(typeCode || "").trim().toLowerCase();
    if (normalizedType) {
        return typeFieldVisibleInTableByDefault(normalizedType, fieldKey);
    }
    return (Array.isArray(rows) ? rows : []).some((item) => (
        typeFieldVisibleInTableByDefault(item?.device_type, fieldKey)
    ));
}

function contextCustomTableFields({ typeCode = "" } = {}) {
    const normalizedType = String(typeCode || "").trim().toLowerCase();
    return normalizedType ? tableCustomFieldDefinitions(normalizedType) : [];
}

function buildDeviceTreeColumns({
    rows = [],
    typeCode = "",
    includeType = false,
    includeNotify = false,
    includeStatus = false,
    includeConfig = false,
    includeActions = false,
    includeDescription = false,
    includeCustomFields = false,
} = {}) {
    const normalizedType = String(typeCode || "").trim().toLowerCase();
    const columns = [];
    if (includeType) {
        columns.push({
            key: "type",
            label: "Type",
            renderCell: (item) => escapeHtml(typeLabel(item.device_type)),
        });
    }
    if (contextFieldVisibleInTable({ rows, typeCode: normalizedType, fieldKey: "name" })) {
        columns.push({ key: "name", label: "Nom" });
    }
    if (contextFieldVisibleInTable({ rows, typeCode: normalizedType, fieldKey: "ip" })) {
        columns.push({ key: "ip", label: "IP" });
    }
    const showLogin = (normalizedType
        ? typeHasCredentialsSupport(normalizedType)
        : rows.some((item) => typeHasCredentialsSupport(item.device_type)))
        && contextFieldVisibleInTable({ rows, typeCode: normalizedType, fieldKey: "device_login" });
    if (showLogin) {
        columns.push({ key: "device_login", label: "Login" });
    }
    const showPassword = (normalizedType
        ? typeHasCredentialsSupport(normalizedType)
        : rows.some((item) => typeHasCredentialsSupport(item.device_type)))
        && contextFieldVisibleInTable({ rows, typeCode: normalizedType, fieldKey: "device_password" });
    if (showPassword) {
        columns.push({
            key: "device_password",
            label: "Mot de passe",
            renderCell: (item) => renderInventoryPasswordCell(item),
        });
    }
    if (includeNotify && contextFieldVisibleInTable({ rows, typeCode: normalizedType, fieldKey: "notify" })) {
        columns.push({
            key: "notify",
            label: "Alertes changement",
            renderCell: (item) => item.notify ? "Oui" : "Non",
        });
    }
    if (includeStatus) {
        columns.push({
            key: "status",
            label: "Statut",
            renderCell: (item) => `<span class="status-badge ${statusClass(item.status)}">${escapeHtml(localizeStatus(item.status || "idle"))}</span>`,
        });
    }
    const showCfg = includeConfig && (normalizedType
        ? typeHasConfigSupport(normalizedType)
        : rows.some((item) => typeHasConfigSupport(item.device_type)))
        && contextFieldVisibleInTable({ rows, typeCode: normalizedType, fieldKey: "config_saved" });
    if (showCfg) {
        columns.push({
            key: "config_saved",
            label: "Cfg",
            renderCell: (item) => item.has_saved_config ? "&#10003;" : "-",
        });
    }
    if (includeDescription && contextFieldVisibleInTable({ rows, typeCode: normalizedType, fieldKey: "description" })) {
        columns.push({ key: "description", label: "Description" });
    }
    if (includeCustomFields) {
        for (const field of contextCustomTableFields({ typeCode: normalizedType })) {
            const key = String(field?.field_key || "").trim();
            if (!key) {
                continue;
            }
            columns.push({
                key: `custom:${key}`,
                label: fieldLabel(key, field?.label || ""),
                renderCell: (item) => escapeHtml(item.custom_data?.[key] || ""),
            });
        }
    }
    if (includeActions) {
        columns.push({
            key: "actions",
            label: "Actions",
            sortable: false,
            cellClassName: "inventory-row-actions",
            renderCell: (item) => `
                ${createIconActionButtonMarkup({
                    icon: "edit",
                    title: "Modifier",
                    ariaLabel: `Modifier ${item.name}`,
                    data: { row_action: "edit" },
                })}
                ${createIconActionButtonMarkup({
                    icon: "delete",
                    danger: true,
                    title: "Supprimer",
                    ariaLabel: `Supprimer ${item.name}`,
                    data: { row_action: "delete" },
                })}
            `,
        });
    }
    return columns;
}

function fieldLabel(fieldKey, explicitLabel = "") {
    return explicitLabel || FIELD_LABELS[fieldKey] || fieldKey;
}

function normalizePlatform(value) {
    const normalized = String(value || "")
        .replaceAll(",", " ")
        .trim()
        .toLowerCase()
        .replace(/\s+/g, " ");
    return normalized || "autre";
}

function parseOsScope(rawScope) {
    return Array.from(new Set(
        String(rawScope || "")
            .split(",")
            .map((value) => String(value || "").trim())
            .filter(Boolean)
            .map((value) => normalizePlatform(value))
            .filter(Boolean),
    ));
}

function formatOsScope(scopeValues) {
    const ordered = [];
    const seen = new Set();
    for (const item of Array.isArray(scopeValues) ? scopeValues : []) {
        if (!String(item || "").trim()) {
            continue;
        }
        const key = normalizePlatform(item);
        if (seen.has(key)) {
            continue;
        }
        seen.add(key);
        ordered.push(key);
    }
    return ordered.join(",");
}

function actionAllowsOs(rawScope, platformLabel) {
    const scope = parseOsScope(rawScope);
    if (!scope.length) {
        return true;
    }
    const normalizedPlatform = normalizePlatform(platformLabel);
    if (scope.includes(normalizedPlatform)) {
        return true;
    }
    return !DEFAULT_PLATFORM_KEYS.has(normalizedPlatform) && scope.includes("autre");
}

function actionLabel(actionKey) {
    const key = String(actionKey || "").trim().toLowerCase();
    return ACTION_LABELS[key] || key.replaceAll("_", " ").replace(/\b\w/g, (ch) => ch.toUpperCase());
}

function actionKeyFromSelection(value, options) {
    const raw = String(value || "").trim();
    const asKey = raw.toLowerCase();
    if (options.includes(asKey)) {
        return asKey;
    }
    for (const option of options) {
        if (raw === actionLabel(option)) {
            return option;
        }
    }
    return "";
}

function schemaFields(deviceType) {
    const schema = state.deviceSchemas[deviceType];
    return Array.isArray(schema?.fields) ? schema.fields : [];
}

function schemaActions(deviceType) {
    const schema = state.deviceSchemas[deviceType];
    return Array.isArray(schema?.actions) ? schema.actions : [];
}

function fieldDefinition(deviceType, wantedKey) {
    const target = String(wantedKey || "").trim().toLowerCase();
    return schemaFields(deviceType).find((field) => String(field.field_key || "").trim().toLowerCase() === target) || null;
}

function hasField(deviceType, fieldKey) {
    return Boolean(fieldDefinition(deviceType, fieldKey));
}

function fieldChoiceOptions(deviceType, fieldKey) {
    const field = fieldDefinition(deviceType, fieldKey);
    const raw = String(field?.options || "").trim();
    if (!raw) {
        return [];
    }
    return raw.split(",").map((item) => item.trim()).filter(Boolean);
}

function actionOptionsForPlatform(deviceType, platformLabel) {
    const platform = normalizePlatform(platformLabel);
    return schemaActions(deviceType)
        .map((action) => {
            const actionKey = String(action.action_key || "").trim().toLowerCase();
            if (!actionKey) {
                return null;
            }
            if (actionAllowsOs(String(action.os_scope || ""), platform)) {
                return {
                    key: actionKey,
                    label: String(action.label || "").trim() || actionLabel(actionKey),
                    is_default: Boolean(action.is_default),
                };
            }
            return null;
        })
        .filter(Boolean);
}

function defaultActionForPlatform(deviceType, platformLabel) {
    const options = actionOptionsForPlatform(deviceType, platformLabel);
    const normalizedPlatform = normalizePlatform(platformLabel);
    const mapField = fieldDefinition(deviceType, "action_default_by_os");
    if (mapField) {
        try {
            const parsed = JSON.parse(String(mapField.default_value || "{}"));
            const mapped = String(parsed?.[normalizedPlatform] || "").trim().toLowerCase();
            if (mapped && options.some((item) => item.key === mapped)) {
                return mapped;
            }
        } catch (_error) {
        }
    }
    const preferred = options.find((item) => item.is_default);
    return preferred ? preferred.key : (options[0]?.key || "");
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
            device_type: device.device_type,
            device_id: device.id || "",
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
    const resolver = window.NMPSharedUi?.theme?.resolveLocalUiConfig;
    window.NMPSharedUi?.applyThemeConfig?.(typeof resolver === "function" ? resolver(config) : config);
    const root = document.documentElement;
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
    root.style.setProperty("--dashboard-watermark-image", dashboardWatermark);
    root.style.setProperty("--dashboard-watermark-opacity", String(watermarkEnabled && !isAuthWatermark ? watermarkOpacity : 0));
    root.style.setProperty("--auth-watermark-image", "none");
    root.style.setProperty("--auth-watermark-opacity", "0");
    const versionNode = document.getElementById("app-version");
    if (versionNode instanceof HTMLElement) {
        versionNode.textContent = config?.app_version || "-";
    }
}

async function loadAuthMode() {
    const status = await requestJson("/auth/status", { headers: {} });
    const mustChangePassword = Boolean(status?.first_start_required) || !Boolean(status?.has_admin_password);
    authTitle.textContent = "Connexion";
    authHelp.textContent = mustChangePassword
        ? "Premiere connexion: utiliser le compte sa puis definir un nouveau mot de passe."
        : "Connexion requise avec un compte pour ouvrir le dashboard web.";
    authSubmit.textContent = mustChangePassword ? "Se connecter et changer le mot de passe" : "Se connecter";
    passwordInput.autocomplete = "current-password";
    usernameInput.autocomplete = "username";
    if (!String(usernameInput.value || "").trim()) {
        usernameInput.value = "sa";
    }
    newPasswordField.hidden = !mustChangePassword;
    newPasswordInput.required = mustChangePassword;
    confirmPasswordField.hidden = !mustChangePassword;
    confirmPasswordInput.required = mustChangePassword;
    authForm.dataset.forcePasswordChange = mustChangePassword ? "1" : "0";
    await loadPublicUiConfig();
    return { mustChangePassword };
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
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
}

function redirectToPortal() {
    window.location.replace("/");
}

function renderNavigation(types) {
    if (state.currentView !== "dashboard" && state.currentView !== "global" && !types.some((item) => item.type_code === state.currentView)) {
        applyMonitoringTreeFilters({ typeCode: "dashboard", status: "" });
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
            applyMonitoringTreeFilters({ typeCode: entry.key, status: "" });
            renderSection();
        });
        navToolbar.appendChild(button);
    });
    navToolbar.hidden = state.currentSection === "supervision" && state.currentView === "dashboard";
}

function createMonitorScreenMarkup(stateKey, { large = false } = {}) {
    const normalizedState = ["running", "partial", "stopped"].includes(String(stateKey || ""))
        ? String(stateKey)
        : "stopped";
    const path = normalizedState === "stopped"
        ? "M4 32 L156 32"
        : "M4 34 L28 34 L38 9 L52 55 L66 34 L94 34 L106 17 L120 34 L156 34";
    return `
        <span class="monitor-trace ${large ? "monitor-trace-large" : "monitor-trace-small"} is-${escapeAttribute(normalizedState)}" aria-hidden="true">
            <svg class="monitor-trace-svg" viewBox="0 0 160 64" preserveAspectRatio="none">
                <path class="monitor-trace-base" d="${path}" pathLength="100"></path>
                <path class="monitor-trace-draw" d="${path}" pathLength="100"></path>
            </svg>
            <span class="monitor-trace-dot"></span>
        </span>
    `;
}

function setNodeText(node, value) {
    if (!(node instanceof HTMLElement)) {
        return;
    }
    const nextValue = String(value ?? "");
    if (node.textContent !== nextValue) {
        node.textContent = nextValue;
    }
}

function setNodeHtml(node, value) {
    if (!(node instanceof HTMLElement)) {
        return;
    }
    const nextValue = String(value ?? "");
    if (node.innerHTML !== nextValue) {
        node.innerHTML = nextValue;
    }
}

function escapeCssIdentifier(value) {
    const raw = String(value ?? "");
    if (window.CSS && typeof window.CSS.escape === "function") {
        return window.CSS.escape(raw);
    }
    return raw.replace(/["\\]/g, "\\$&");
}

function createDashboardCardShell(card) {
    const article = document.createElement("article");
    article.innerHTML = `
        <div class="dash-card-title"></div>
        <div class="monitor-card-screen" hidden></div>
        <div class="dash-card-value"></div>
        <div class="dash-card-sub"></div>
        <button class="monitor-type-toggle" type="button" data-monitoring-type-toggle hidden></button>
        <div class="dash-card-stats"><span></span></div>
    `;
    article.dataset.dashboardCardId = String(card.id || card.clickView || "").trim();
    return article;
}

function ensureDetailTitleMonitoringToggle() {
    let button = document.getElementById("detail-title-monitoring-toggle");
    if (button instanceof HTMLButtonElement) {
        return button;
    }
    button = document.createElement("button");
    button.id = "detail-title-monitoring-toggle";
    button.type = "button";
    button.className = "detail-title-monitoring-toggle";
    button.hidden = true;
    detailTitle.parentElement?.classList?.add("detail-title-wrap");
    detailTitle.insertAdjacentElement("afterend", button);
    return button;
}

function updateDetailTitleMonitoringToggle(typeCode) {
    const button = ensureDetailTitleMonitoringToggle();
    const normalizedType = String(typeCode || "").trim().toLowerCase();
    const typeInfo = (state.snapshot?.types || []).find((item) => String(item.type_code || "").trim().toLowerCase() === normalizedType);
    if (!normalizedType || normalizedType === "global" || normalizedType === "dashboard" || !typeInfo) {
        button.hidden = true;
        button.onclick = null;
        return;
    }
    const running = Boolean(typeInfo.running);
    const actionLabel = `${running ? "Arreter" : "Demarrer"} monitoring ${typeInfo.label || normalizedType}`;
    button.hidden = false;
    button.className = `detail-title-monitoring-toggle is-${running ? "running" : "stopped"}`;
    button.title = actionLabel;
    button.setAttribute("aria-label", actionLabel);
    if (button.dataset.monitorState !== (running ? "running" : "stopped")) {
        button.innerHTML = createMonitorScreenMarkup(running ? "running" : "stopped");
        button.dataset.monitorState = running ? "running" : "stopped";
    }
    button.onclick = async (event) => {
        event.preventDefault();
        event.stopPropagation();
        await postMonitoringCommand(`/monitoring/${running ? "stop" : "start"}/${encodeURIComponent(normalizedType)}`);
    };
}

function updateDashboardStickyMetrics() {
    if (!(cardsGrid instanceof HTMLElement) || !(detailPanel instanceof HTMLElement)) {
        return;
    }
    const cardsHeight = cardsGrid.hidden ? 0 : Math.ceil(cardsGrid.getBoundingClientRect().height);
    const filters = devicesSection instanceof HTMLElement ? devicesSection.querySelector(":scope > .section-head") : null;
    const filtersHeight = filters instanceof HTMLElement ? Math.ceil(filters.getBoundingClientRect().height) : 0;
    detailPanel.style.setProperty("--dashboard-cards-sticky-height", `${cardsHeight}px`);
    detailPanel.style.setProperty("--dashboard-filter-sticky-height", `${filtersHeight}px`);
}

function renderCards(snapshot) {
    const summary = snapshot.summary || {};
    const runningAny = Boolean(summary.running_any);
    const runningAll = Boolean(summary.running_all);
    const totalAll = Number(summary.total || 0);
    const onlineAll = Number(summary.online || 0);
    const offlineAll = Number(summary.offline || 0);
    const monitoringValue = runningAll ? "Globale" : (runningAny ? "Partiel" : "Arrete");
    const cards = [
        {
            id: "global",
            title: "Equipements",
            value: `${onlineAll}/${totalAll}`,
            sub: "En ligne / total",
            stats: { total: totalAll, online: onlineAll, offline: offlineAll, running: runningAny },
            clickView: "global",
        },
        {
            id: "monitoring",
            title: "Monitoring",
            value: monitoringValue,
            sub: "Etat des sondes",
            stats: null,
            clickView: "monitoring-toggle",
            detailView: "global",
            running: runningAny,
            monitorState: runningAll ? "running" : (runningAny ? "partial" : "stopped"),
        },
        ...snapshot.types.map((item) => ({
            id: String(item.type_code || "").trim(),
            title: `Etat ${item.label}`,
            value: `${Number(item.online || 0)}/${Number(item.total || 0)}`,
            sub: "En ligne / total",
            stats: {
                total: Number(item.total || 0),
                online: Number(item.online || 0),
                offline: Number(item.offline || 0),
                running: Boolean(item.running),
            },
            clickView: item.type_code,
            typeCode: item.type_code,
        })),
    ];
    const previousCardIds = new Set(
        Array.from(cardsGrid.querySelectorAll("[data-dashboard-card-id]"))
            .map((node) => String(node.dataset.dashboardCardId || "").trim())
            .filter(Boolean)
    );
    const nextCardIds = new Set(cards.map((card) => String(card.id || card.clickView || "").trim()).filter(Boolean));
    previousCardIds.forEach((id) => {
        if (!nextCardIds.has(id)) {
            cardsGrid.querySelector(`[data-dashboard-card-id="${escapeCssIdentifier(id)}"]`)?.remove();
        }
    });
    const nextSignature = Array.from(nextCardIds).join("|");
    const structureChanged = state.monitoringDashboardCardSignature !== nextSignature;
    state.monitoringDashboardCardSignature = nextSignature;

    cards.forEach((card) => {
        const isMonitoringCard = card.id === "monitoring";
        const isTypeCard = Boolean(card.typeCode);
        const cardId = String(card.id || card.clickView || "").trim();
        let article = cardsGrid.querySelector(`[data-dashboard-card-id="${escapeCssIdentifier(cardId)}"]`);
        if (!(article instanceof HTMLElement)) {
            article = createDashboardCardShell(card);
            cardsGrid.appendChild(article);
        }
        article.className = `dash-card panel${card.clickView ? " clickable" : ""}${isMonitoringCard ? " monitoring-action-card" : ""}${isTypeCard ? " monitoring-type-card" : ""}`;
        article.dataset.dashboardCardActive = card.id === "monitoring" || card.id === "global"
            ? String(runningAny)
            : String(Boolean(card.stats?.running));

        setNodeText(article.querySelector(".dash-card-title"), card.title);

        const valueNode = article.querySelector(".dash-card-value");
        const subNode = article.querySelector(".dash-card-sub");
        if (card.stats) {
            if (valueNode instanceof HTMLElement) {
                valueNode.hidden = true;
            }
            if (subNode instanceof HTMLElement) {
                subNode.hidden = true;
            }
        } else {
            if (valueNode instanceof HTMLElement) {
                valueNode.hidden = false;
            }
            if (subNode instanceof HTMLElement) {
                subNode.hidden = false;
            }
            setNodeText(valueNode, card.value);
            setNodeText(subNode, card.sub);
        }

        const monitorScreen = article.querySelector(".monitor-card-screen");
        if (isMonitoringCard && monitorScreen instanceof HTMLElement) {
            monitorScreen.hidden = false;
            monitorScreen.className = `monitor-card-screen is-${card.monitorState}`;
            if (monitorScreen.dataset.monitorState !== card.monitorState) {
                monitorScreen.innerHTML = createMonitorScreenMarkup(card.monitorState, { large: true });
                monitorScreen.dataset.monitorState = card.monitorState;
            }
        } else if (monitorScreen instanceof HTMLElement) {
            monitorScreen.hidden = true;
        }

        const typeToggle = article.querySelector("[data-monitoring-type-toggle]");
        if (isTypeCard && typeToggle instanceof HTMLButtonElement) {
            const typeState = card.stats?.running ? "running" : "stopped";
            const actionLabel = `${card.stats?.running ? "Arreter" : "Demarrer"} ${card.title}`;
            typeToggle.hidden = false;
            typeToggle.className = `monitor-type-toggle is-${typeState}`;
            typeToggle.title = actionLabel;
            typeToggle.setAttribute("aria-label", actionLabel);
            if (typeToggle.dataset.monitorState !== typeState) {
                typeToggle.innerHTML = createMonitorScreenMarkup(typeState);
                typeToggle.dataset.monitorState = typeState;
            }
        } else if (typeToggle instanceof HTMLButtonElement) {
            typeToggle.hidden = true;
        }

        const statsNode = article.querySelector(".dash-card-stats");
        if (card.stats && statsNode instanceof HTMLElement) {
            const statsMarkup = createSupervisionStatsMarkup(card.clickView || "global", card.stats);
            if (statsNode.dataset.statsMarkup !== statsMarkup) {
                setNodeHtml(statsNode, statsMarkup);
                statsNode.dataset.statsMarkup = statsMarkup;
                bindSupervisionStatFilterButtons(article, card.clickView);
            }
        } else {
            setNodeHtml(statsNode, "<span></span>");
            if (statsNode instanceof HTMLElement) {
                statsNode.dataset.statsMarkup = "<span></span>";
            }
        }

        if (isMonitoringCard) {
            article.onclick = async () => {
                if (ensureMonitoringDashboardEditor().isEditing()) {
                    return;
                }
                await postMonitoringCommand(runningAny ? "/monitoring/stop-all" : "/monitoring/start-all");
            };
        } else if (card.clickView) {
            article.onclick = async (event) => {
                if (ensureMonitoringDashboardEditor().isEditing()) {
                    return;
                }
                const toggleButton = event.target instanceof Element ? event.target.closest("[data-monitoring-type-toggle]") : null;
                if (toggleButton && card.typeCode) {
                    event.preventDefault();
                    event.stopPropagation();
                    await postMonitoringCommand(`/monitoring/${card.stats?.running ? "stop" : "start"}/${encodeURIComponent(card.typeCode)}`);
                    return;
                }
                openSupervisionFilteredView(card.clickView, "");
            };
        } else {
            article.onclick = null;
        }
    });
    const editor = ensureMonitoringDashboardEditor();
    if (!state.monitoringDashboardPrefsLoaded || structureChanged) {
        state.monitoringDashboardPrefsLoaded = true;
        editor.refresh().catch(() => {
            editor.decorateCards();
        });
    } else {
        editor.decorateCards();
    }
    window.requestAnimationFrame?.(() => updateDashboardStickyMetrics());
}

function ensureMonitoringDashboardEditor() {
    if (monitoringDashboardEditor) {
        return monitoringDashboardEditor;
    }
    const createEditor = window.NMPSharedUi?.dashboard?.createEditor;
    if (typeof createEditor !== "function") {
        return { decorateCards: () => {}, refresh: async () => {}, isEditing: () => false };
    }
    monitoringDashboardEditor = createEditor({
        scope: "monitoring",
        grid: cardsGrid,
        editButton: dashboardEditButton,
        loadPreferences: () => requestJson("/dashboard-preferences/monitoring"),
        savePreferences: (payload) => requestJson("/dashboard-preferences/monitoring", {
            method: "PUT",
            body: JSON.stringify(payload),
        }),
        getCardId: (card) => String(card?.dataset?.dashboardCardId || "").trim(),
        isCardActive: (_id, card) => String(card?.dataset?.dashboardCardActive || "false") === "true",
        toggleCardActive: async (id, card) => {
            const running = String(card?.dataset?.dashboardCardActive || "false") === "true";
            if (id === "global" || id === "monitoring") {
                await postMonitoringCommand(running ? "/monitoring/stop-all" : "/monitoring/start-all");
                return;
            }
            await postMonitoringCommand(`/monitoring/${running ? "stop" : "start"}/${encodeURIComponent(id)}`);
        },
        onChanged: ({ action } = {}) => {
            if (action === "power") {
                refreshWorkspaceData().catch(() => {});
            }
        },
    });
    return monitoringDashboardEditor;
}

function renderMonitoringToolbar(types, summary) {
    const runningAll = Boolean(summary?.running_all);
    monitoringToolbar.innerHTML = "";

    const createMonitorPulseButton = ({ label, running, onClick }) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = `monitor-pulse-btn${running ? " is-running" : " is-stopped"}`;
        button.title = `${running ? "Arreter" : "Demarrer"} ${label}`;
        button.setAttribute("aria-label", button.title);
        button.innerHTML = `
            ${createMonitorScreenMarkup(running ? "running" : "stopped")}
            <span class="monitor-pulse-label">${escapeHtml(label)}</span>
        `;
        button.addEventListener("click", onClick);
        return button;
    };

    monitoringToolbar.appendChild(createMonitorPulseButton({
        label: "Globale",
        running: runningAll,
        onClick: async () => {
            await postMonitoringCommand(runningAll ? "/monitoring/stop-all" : "/monitoring/start-all");
        },
    }));

    types.forEach((item) => {
        monitoringToolbar.appendChild(createMonitorPulseButton({
            label: item.label,
            running: Boolean(item.running),
            onClick: async () => {
                await postMonitoringCommand(`/monitoring/${item.running ? "stop" : "start"}/${encodeURIComponent(item.type_code)}`);
            },
        }));
    });
}

function renderTypes(types) {
    const container = document.getElementById("types-list");
    container.innerHTML = "";
    types.forEach((item) => {
        const article = document.createElement("article");
        article.className = "type-row";
        const typeCode = String(item.type_code || "").trim();
        const stats = {
            total: Number(item.total || 0),
            online: Number(item.online || 0),
            offline: Number(item.offline || 0),
            running: Boolean(item.running),
        };
        article.innerHTML = `
            <div class="type-row-head">
                <div>
                    <strong>${escapeHtml(item.label)}</strong>
                    <div class="muted">${escapeHtml(typeCode)}</div>
                </div>
                <span class="state-badge ${item.running ? "state-live" : "state-idle"}">${item.running ? "Actif" : "Arrete"}</span>
            </div>
            <div class="type-row-stats">
                ${createSupervisionStatsMarkup(typeCode, stats)}
            </div>
        `;
        article.addEventListener("click", () => {
            openSupervisionFilteredView(typeCode, "");
        });
        bindSupervisionStatFilterButtons(article, typeCode);
        container.appendChild(article);
    });
}

function visibleRowsForCurrentView(snapshot) {
    const filters = currentMonitoringTreeFilters();
    const rows = Object.entries(snapshot.devices || {}).flatMap(([typeCode, items]) =>
        items.map((item) => ({ ...item, device_type: item.device_type || typeCode })),
    );
    const statusFilter = filters.status;
    const filterByStatus = (items) => statusFilter
        ? items.filter((item) => String(item.status || "idle").trim().toLowerCase() === statusFilter)
        : items;
    if (filters.typeCode === "global") {
        return filterByStatus(rows);
    }
    return filterByStatus(rows.filter((item) => String(item.device_type || "").trim().toLowerCase() === filters.typeCode));
}

function supervisionStatusFilterLabel() {
    const statusFilter = currentMonitoringTreeFilters().status;
    return statusFilter ? localizeStatus(statusFilter) : "";
}

function syncMonitoringTreeFilterControls() {
    const filters = currentMonitoringTreeFilters();
    if (supervisionTypeFilter instanceof HTMLSelectElement) {
        const types = Array.isArray(state.snapshot?.types) ? state.snapshot.types : [];
        const currentValue = filters.typeCode;
        supervisionTypeFilter.innerHTML = [
            '<option value="global">Tous</option>',
            ...types.map((item) => {
                const typeCode = String(item?.type_code || "").trim().toLowerCase();
                const label = String(item?.label || typeCode || "Type").trim();
                return typeCode ? `<option value="${escapeHtml(typeCode)}">${escapeHtml(label)}</option>` : "";
            }),
        ].join("");
        supervisionTypeFilter.value = types.some((item) => String(item?.type_code || "").trim().toLowerCase() === currentValue)
            ? currentValue
            : "global";
    }
    if (supervisionStatusFilter instanceof HTMLSelectElement) {
        supervisionStatusFilter.value = filters.status;
    }
}

function resolveDeviceRecord(item) {
    const key = `${item.device_type}:${item.id}`;
    const stored = state.inventory.find((entry) => deviceKey(entry) === key);
    return stored ? { ...stored, status: item.status || "idle" } : { ...item };
}

function renderDevices(snapshot) {
    syncMonitoringTreeFilterControls();
    const tree = ensureSupervisionTreeView();
    if (tree) {
        tree.render();
        return;
    }
    const tbody = document.getElementById("devices-body");
    if (!(tbody instanceof HTMLElement)) {
        return;
    }
    tbody.innerHTML = "";
    const rows = visibleRowsForCurrentView(snapshot).map((item) => resolveDeviceRecord(item));
    const filterType = currentMonitoringTreeFilters().typeCode;
    const showCfg = filterType === "global"
        ? rows.some((item) => typeHasConfigSupport(item.device_type))
        : typeHasConfigSupport(filterType);
    const showCredentials = filterType === "global"
        ? rows.some((item) => typeHasCredentialsSupport(item.device_type))
        : typeHasCredentialsSupport(filterType);
    const cfgHead = document.querySelector('#devices-head th[data-col="config_saved"]');
    if (cfgHead) {
        cfgHead.hidden = !showCfg;
    }
    const loginHead = document.querySelector('#devices-head th[data-col="device_login"]');
    if (loginHead) {
        loginHead.hidden = !showCredentials;
    }
    const passwordHead = document.querySelector('#devices-head th[data-col="device_password"]');
    if (passwordHead) {
        passwordHead.hidden = !showCredentials;
    }
    updateSearchVisibility(deviceFilter, rows.length, 5);
    const query = (deviceFilter.value || "").trim().toLowerCase();
    filterAndSortRows(rows, {
        query,
        searchText: (item) => [
            item.device_type,
            item.name,
            item.ip,
            item.device_login,
            item.status,
            item.description,
            item.has_saved_config ? "oui" : "non",
        ].join(" "),
        sortColumn: state.supervisionSort.column,
        sortDirection: state.supervisionSort.direction,
        compare: compareByColumn,
    }).forEach((item) => {
            const device = item;
            const tr = document.createElement("tr");
            if (deviceKey(device) === state.selectedDeviceKey) {
                tr.classList.add("is-selected");
            }
            tr.innerHTML = `
                <td>${escapeHtml(item.device_type || "")}</td>
                <td>${escapeHtml(item.name || "")}</td>
                <td>${escapeHtml(item.ip || "")}</td>
                ${showCredentials ? `<td>${escapeHtml(item.device_login || "")}</td>` : ""}
                ${showCredentials ? `<td>${renderInventoryPasswordCell(device)}</td>` : ""}
                <td><span class="status-badge ${statusClass(item.status)}">${escapeHtml(localizeStatus(item.status || "idle"))}</span></td>
                ${showCfg ? `<td>${device.has_saved_config ? "✓" : "-"}</td>` : ""}
                <td>${escapeHtml(item.description || "")}</td>
            `;
            const revealButton = tr.querySelector('[data-row-action="reveal_password"]');
            if (revealButton instanceof HTMLButtonElement) {
                revealButton.addEventListener("click", async (event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    await openDevicePasswordRevealModal(device);
                });
            }
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
                event.stopPropagation();
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
    const runningAny = Boolean(summary.running_any);
    const focusView = state.currentView !== "dashboard";

    renderNavigation(state.snapshot.types || []);
    updateSupervisionTypeEditButton();
    syncMonitoringTreeFilterControls();
    detailPanel.classList.toggle("detail-focus-mode", (focusView || state.currentView === "dashboard") && state.currentSection === "supervision");

    const filters = currentMonitoringTreeFilters();
    if (state.currentView === "dashboard") {
        updateDetailTitleMonitoringToggle("");
        if (!runningAny) {
            detailPanel.hidden = true;
            placeholderPanel.hidden = false;
            return;
        }
        placeholderPanel.hidden = true;
        detailPanel.hidden = false;
        detailTitle.textContent = "Globale";
        inventoryTitle.textContent = supervisionStatusFilterLabel()
            ? `Inventaire global - ${supervisionStatusFilterLabel()}`
            : "Inventaire global";
        typesPanel.hidden = true;
        devicesSection.hidden = false;
        renderDevices(state.snapshot);
        return;
    }

    placeholderPanel.hidden = true;
    detailPanel.hidden = false;
    typesPanel.hidden = filters.typeCode === "global" && state.currentView === "global" ? false : true;
    devicesSection.hidden = false;
    detailTitle.textContent = filters.typeCode === "global" ? "Globale" : displayLabelForView(filters.typeCode);
    updateDetailTitleMonitoringToggle(filters.typeCode === "global" ? "" : filters.typeCode);
    const baseInventoryTitle = filters.typeCode === "global"
        ? "Inventaire global"
        : `Inventaire ${displayLabelForView(filters.typeCode)}`;
    inventoryTitle.textContent = supervisionStatusFilterLabel()
        ? `${baseInventoryTitle} - ${supervisionStatusFilterLabel()}`
        : baseInventoryTitle;
    renderDevices(state.snapshot);
}

function renderInventoryFilters() {
    const selectedType = String(inventoryTypeFilter.value || "").trim();
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
    if (selectedType && options.some((item) => item.value === selectedType)) {
        inventoryTypeFilter.value = selectedType;
    }
    updateInventoryEditTypeButton();
}

function updateInventoryEditTypeButton() {
    if (!(inventoryEditTypeButton instanceof HTMLButtonElement)) {
        return;
    }
    const selectedType = String(inventoryTypeFilter?.value || "").trim();
    const hasType = Boolean(selectedType && typeMeta(selectedType));
    inventoryEditTypeButton.hidden = !hasType;
    inventoryEditTypeButton.disabled = !hasType;
    inventoryEditTypeButton.dataset.typeCode = hasType ? selectedType : "";
    if (hasType) {
        inventoryEditTypeButton.textContent = `Modifier type ${typeLabel(selectedType)}`;
    } else {
        inventoryEditTypeButton.textContent = "Modifier le type";
    }
}

function renderInventoryList() {
    const tree = ensureInventoryTreeView();
    if (tree) {
        const rowsFromTree = tree.render();
        inventoryFeedback.textContent = `${rowsFromTree.length} equipement(s) affiches`;
        return;
    }
    const rows = inventoryRows();
    const filterType = String(inventoryTypeFilter.value || "").trim();
    const showCfg = filterType
        ? typeHasConfigSupport(filterType)
        : rows.some((item) => typeHasConfigSupport(item.device_type));
    const showCredentials = filterType
        ? typeHasCredentialsSupport(filterType)
        : rows.some((item) => typeHasCredentialsSupport(item.device_type));
    const cfgHead = document.querySelector('#inventory-head th[data-col="config_saved"]');
    if (cfgHead) {
        cfgHead.hidden = !showCfg;
    }
    const loginHead = document.querySelector('#inventory-head th[data-col="device_login"]');
    if (loginHead) {
        loginHead.hidden = !showCredentials;
    }
    const passwordHead = document.querySelector('#inventory-head th[data-col="device_password"]');
    if (passwordHead) {
        passwordHead.hidden = !showCredentials;
    }
    inventoryBody.innerHTML = "";
    inventoryFeedback.textContent = `${rows.length} equipement(s) affiches`;
    rows.forEach((item) => {
        const selected = deviceKey(item) === state.selectedDeviceKey;
        const tr = document.createElement("tr");
        tr.dataset.deviceKey = deviceKey(item);
        if (selected) {
            tr.classList.add("is-selected");
        }
        tr.innerHTML = `
            <td>${escapeHtml(typeLabel(item.device_type))}</td>
            <td>${escapeHtml(item.name)}</td>
            <td>${escapeHtml(item.ip)}</td>
            ${showCredentials ? `<td>${escapeHtml(item.device_login || "")}</td>` : ""}
            ${showCredentials ? `<td>${renderInventoryPasswordCell(item)}</td>` : ""}
            <td>${item.notify ? "Oui" : "Non"}</td>
            ${showCfg ? `<td>${item.has_saved_config ? "✓" : "-"}</td>` : ""}
            <td class="inventory-row-actions">
                ${createIconActionButtonMarkup({
                    icon: "edit",
                    title: "Modifier",
                    ariaLabel: `Modifier ${item.name}`,
                    data: { row_action: "edit" },
                })}
                ${createIconActionButtonMarkup({
                    icon: "delete",
                    danger: true,
                    title: "Supprimer",
                    ariaLabel: `Supprimer ${item.name}`,
                    data: { row_action: "delete" },
                })}
            </td>
        `;
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
        ["Alertes changement", device.notify ? "Oui" : "Non"],
        ["TeamViewer", device.id_Teamviewer],
        ["Sous-type", device.device_subtype],
        ["Double-clic", device.action_double_click],
        ["URL web", device.web_url],
        ["Utilisateur SSH", device.ssh_user],
    ];
    if (typeHasCredentialsSupport(device.device_type)) {
        details.push(["Login", device.device_login || ""]);
        details.push(["Mot de passe", revealedDevicePassword(device) || devicePasswordMask(device) || ""]);
    }
    if (typeHasConfigSupport(device.device_type)) {
        details.push(["Cfg", device.has_saved_config ? "✓" : "-"]);
    }

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
                <article class="log-item ${statusTransitionClass(row.old_status, row.new_status)}">
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

function createFieldMarkup({ key, label, value, multiline = false, wide = false, inputType = "text", options = null }) {
    const sharedFieldMarkup = window.NMPSharedUi?.createFieldMarkup;
    if (typeof sharedFieldMarkup === "function") {
        return sharedFieldMarkup({
            key,
            label,
            value,
            multiline,
            wide,
            inputType,
            options,
            escapeHtml,
        });
    }
    if (Array.isArray(options) && options.length) {
        const normalizedValue = String(value ?? "");
        return `
            <label class="field ${wide ? "wide" : ""}">
                <span>${escapeHtml(label)}</span>
                <select name="${escapeAttribute(key)}">
                    ${options.map((option) => {
                        const optionValue = String(option?.value ?? "");
                        return `
                            <option value="${escapeAttribute(optionValue)}" ${optionValue === normalizedValue ? "selected" : ""}>
                                ${escapeHtml(option?.label ?? optionValue)}
                            </option>
                        `;
                    }).join("")}
                </select>
            </label>
        `;
    }
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
            <input name="${escapeHtml(key)}" type="${escapeHtml(inputType || "text")}" value="${escapeHtml(value)}">
    </label>
    `;
}

function createDeviceWebUrlFieldMarkup({ ip = "", subtype = "", webUrl = "", wide = false } = {}) {
    const parts = splitDeviceWebUrlForForm({ ip, subtype, webUrl });
    return `
        <div class="field web-url-field ${wide ? "wide" : ""}">
            <span>${escapeHtml(fieldLabel("web_url"))}</span>
            <div class="web-url-grid">
                <input
                    name="web_url"
                    type="text"
                    value="${escapeAttribute(parts.url)}"
                    placeholder="${escapeAttribute(ip ? `http://${ip}` : "http://serveur")}"
                >
                <input
                    name="web_url_port"
                    type="number"
                    min="1"
                    max="65535"
                    value="${escapeAttribute(parts.port)}"
                    placeholder="${escapeAttribute(parts.placeholder)}"
                    aria-label="Port web"
                >
            </div>
        </div>
    `;
}

function createActionButtonMarkup(options = {}) {
    const sharedBuilder = window.NMPSharedUi?.formControls?.createActionButtonMarkup;
    if (typeof sharedBuilder === "function") {
        return sharedBuilder({
            ...options,
            escapeHtml,
            escapeAttribute,
        });
    }
    const classes = String(options.className || "toolbar-btn").trim() || "toolbar-btn";
    const type = String(options.type || "button").trim() || "button";
    const action = String(options.action || "").trim();
    const label = String(options.label || "").trim();
    const title = String(options.title || "").trim();
    const id = String(options.id || "").trim();
    const name = String(options.name || "").trim();
    const value = String(options.value || "").trim();
    const iconHtml = String(options.iconHtml || "").trim();
    const showIcon = options.showIcon !== false && Boolean(iconHtml);
    const attrs = [
        `class="${escapeAttribute(classes)}"`,
        `type="${escapeAttribute(type)}"`,
    ];
    if (action) {
        attrs.push(`data-action="${escapeAttribute(action)}"`);
    }
    if (title) {
        attrs.push(`title="${escapeAttribute(title)}"`);
    }
    if (id) {
        attrs.push(`id="${escapeAttribute(id)}"`);
    }
    if (name) {
        attrs.push(`name="${escapeAttribute(name)}"`);
    }
    if (value) {
        attrs.push(`value="${escapeAttribute(value)}"`);
    }
    const dataAttrs = options.data && typeof options.data === "object" ? options.data : {};
    Object.entries(dataAttrs).forEach(([rawName, rawValue]) => {
        const dataName = String(rawName || "").trim();
        if (!dataName || rawValue === undefined || rawValue === null || rawValue === false) {
            return;
        }
        const normalized = dataName
            .replaceAll("_", "-")
            .replaceAll(" ", "-")
            .replace(/[A-Z]/g, (match) => `-${match.toLowerCase()}`);
        if (rawValue === true) {
            attrs.push(`data-${normalized}`);
            return;
        }
        attrs.push(`data-${normalized}="${escapeAttribute(String(rawValue))}"`);
    });
    const extraAttrs = options.attrs && typeof options.attrs === "object" ? options.attrs : {};
    Object.entries(extraAttrs).forEach(([rawName, rawValue]) => {
        const nameAttr = String(rawName || "").trim();
        if (!nameAttr || rawValue === undefined || rawValue === null || rawValue === false) {
            return;
        }
        if (rawValue === true) {
            attrs.push(nameAttr);
            return;
        }
        attrs.push(`${nameAttr}="${escapeAttribute(String(rawValue))}"`);
    });
    if (options.disabled) {
        attrs.push("disabled");
    }
    const iconMarkup = showIcon ? `<span class="ui-action-btn-icon" aria-hidden="true">${iconHtml}</span>` : "";
    const labelMarkup = label ? `<span class="ui-action-btn-label">${escapeHtml(label)}</span>` : "";
    return `<button ${attrs.join(" ")}>${iconMarkup}${labelMarkup}</button>`;
}

function createIconActionButtonMarkup(options = {}) {
    const sharedBuilder = window.NMPSharedUi?.formControls?.createIconActionButtonMarkup;
    if (typeof sharedBuilder === "function") {
        return sharedBuilder({
            ...options,
            escapeHtml,
            escapeAttribute,
        });
    }
    const className = String(options.className || "inventory-action-btn").trim() || "inventory-action-btn";
    return createActionButtonMarkup({
        ...options,
        className: options.danger ? `${className} danger` : className,
        type: String(options.type || "button").trim() || "button",
        showIcon: options.showIcon !== false,
    });
}

function createModalActionsMarkup(options = {}) {
    const sharedBuilder = window.NMPSharedUi?.formControls?.createModalActionsMarkup;
    if (typeof sharedBuilder === "function") {
        return sharedBuilder({
            ...options,
            escapeHtml,
            escapeAttribute,
        });
    }
    const buttons = Array.isArray(options.buttons) && options.buttons.length
        ? options.buttons
        : [{ className: "toolbar-btn", type: "button", action: "modal:close", label: "Annuler" }, { className: "primary-btn", type: "submit", label: "Enregistrer" }];
    const className = ["modal-actions", String(options.className || "").trim()].filter(Boolean).join(" ");
    return `<div class="${escapeAttribute(className)}">${buttons.map((button) => createActionButtonMarkup(button)).join("")}</div>`;
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

function parseChoiceOptions(raw) {
    return Array.from(new Set(
        String(raw || "")
            .split(",")
            .map((item) => String(item || "").trim())
            .filter(Boolean),
    ));
}

function createSchemaDynamicFieldMarkup(field, value, { keyPrefix = "custom:" } = {}) {
    const fieldKey = String(field?.field_key || "").trim();
    if (!fieldKey) {
        return "";
    }
    const name = `${keyPrefix}${fieldKey}`;
    const label = fieldLabel(fieldKey, field?.label || fieldKey);
    const kind = String(field?.field_kind || "text").trim().toLowerCase();
    const currentValue = String(value ?? field?.default_value ?? "");
    if (kind === "choice") {
        const options = parseChoiceOptions(field?.options);
        if (!options.length) {
            return createFieldMarkup({ key: name, label, value: currentValue });
        }
        const selected = options.find((item) => item.toLowerCase() === currentValue.toLowerCase()) || options[0];
        return createSelectMarkup({
            key: name,
            label,
            value: selected,
            options: options.map((item) => ({ value: item, label: item })),
        });
    }
    if (kind === "ip") {
        return createFieldMarkup({ key: name, label, value: currentValue, inputType: "text" });
    }
    if (kind === "url") {
        return createFieldMarkup({ key: name, label, value: currentValue, inputType: fieldKey === "web_url" ? "text" : "url" });
    }
    return createFieldMarkup({ key: name, label, value: currentValue });
}

function createRemotePluginsListMarkup({ actions, selectedAction, platformLabel }) {
    const rows = Array.isArray(actions) ? actions : [];
    if (!rows.length) {
        return `
            <section class="device-plugins-panel wide">
                <h4 class="device-plugins-title">Plugins de prise en main disponibles (${escapeHtml(platformLabel || "OS")})</h4>
                <div class="muted">Aucun plugin disponible pour cet OS.</div>
            </section>
        `;
    }
    return `
        <section class="device-plugins-panel wide">
            <h4 class="device-plugins-title">Plugins de prise en main disponibles (${escapeHtml(platformLabel || "OS")})</h4>
            <div class="device-plugins-list">
                ${rows.map((item) => {
                    const key = String(item?.key || "").trim().toLowerCase();
                    const label = String(item?.label || actionLabel(key)).trim() || actionLabel(key);
                    const isSelected = key === String(selectedAction || "").trim().toLowerCase();
                    const badge = typeSchemaPluginBadge(key);
                    return `
                        <div class="device-plugin-chip${isSelected ? " is-selected" : ""}">
                            <span class="device-plugin-badge">${escapeHtml(badge)}</span>
                            <span>${escapeHtml(label)}</span>
                            ${isSelected ? '<span class="device-plugin-tag">Selectionne</span>' : ""}
                        </div>
                    `;
                }).join("")}
            </div>
        </section>
    `;
}

function buildDeviceFormMarkup(current, mode, targetType) {
    const submitPreset = mode === "create" ? "add" : "save";
    const submitLabel = mode === "create" ? "Ajouter" : "Enregistrer";
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
                <div id="modal-device-dynamic-fields" class="wide"></div>
            </div>
            <label class="check-field">
                <input id="modal-device-notify" name="notify" type="checkbox" ${current.notify ? "checked" : ""}>
                <span>Alertes changement actives</span>
            </label>
            <p id="modal-device-feedback" class="muted inventory-feedback"></p>
            ${createModalActionsMarkup({
                buttons: [
                    { preset: "cancel" },
                    { preset: submitPreset, label: submitLabel },
                ],
            })}
        </form>
    `;
}

function applyRevealedCredentialsToInventory(device, payload) {
    const normalizedType = String(device?.device_type || "").trim().toLowerCase();
    const targetId = String(device?.id || "").trim();
    if (!normalizedType || !targetId) {
        return;
    }
    const login = String(payload?.device_login || "").trim();
    const password = String(payload?.device_password || "");
    for (const row of state.inventory || []) {
        if (
            String(row?.device_type || "").trim().toLowerCase() === normalizedType
            && String(row?.id || "").trim() === targetId
        ) {
            if (login) {
                row.device_login = login;
            }
            break;
        }
    }
    const key = `${normalizedType}:${targetId}`;
    state.revealedDevicePasswords[key] = password;
}

function promptCredentialRevealSessionPassword() {
    return new Promise((resolve) => {
        const overlay = document.createElement("div");
        overlay.className = "credential-prompt-overlay";
        overlay.innerHTML = `
            <section class="credential-prompt-dialog" role="dialog" aria-modal="true" aria-labelledby="credential-prompt-title">
                <h3 id="credential-prompt-title">Afficher les identifiants</h3>
                <label class="field">
                    <span>Mot de passe de session ITOPS</span>
                    <input name="session_password" type="password" autocomplete="current-password">
                </label>
                <p class="muted credential-prompt-help">Le mot de passe est masque pendant la saisie.</p>
                <div class="modal-actions">
                    <button type="button" class="toolbar-btn" data-credential-prompt="cancel">Annuler</button>
                    <button type="button" class="primary-btn" data-credential-prompt="submit">Afficher</button>
                </div>
            </section>
        `;
        const cleanup = (value) => {
            overlay.remove();
            resolve(value);
        };
        overlay.addEventListener("click", (event) => {
            const target = event.target;
            if (!(target instanceof Element)) {
                return;
            }
            if (target === overlay || target.closest('[data-credential-prompt="cancel"]')) {
                cleanup(null);
                return;
            }
            if (target.closest('[data-credential-prompt="submit"]')) {
                const input = overlay.querySelector('input[name="session_password"]');
                cleanup(input instanceof HTMLInputElement ? input.value : "");
            }
        });
        overlay.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                event.preventDefault();
                cleanup(null);
                return;
            }
            if (event.key === "Enter") {
                event.preventDefault();
                const input = overlay.querySelector('input[name="session_password"]');
                cleanup(input instanceof HTMLInputElement ? input.value : "");
            }
        });
        document.body.appendChild(overlay);
        const input = overlay.querySelector('input[name="session_password"]');
        if (input instanceof HTMLInputElement) {
            input.focus();
        }
    });
}

async function requestDevicePasswordReveal(device, options = {}) {
    const feedbackNode = options.feedbackNode instanceof HTMLElement ? options.feedbackNode : inventoryFeedback;
    if (!hasStoredDevicePassword(device)) {
        if (feedbackNode) {
            feedbackNode.textContent = "Aucun mot de passe stocke pour cet equipement.";
        }
        return null;
    }
    const unlocked = isCredentialRevealSessionUnlocked();
    let sessionPassword = unlocked ? String(state.credentialRevealSessionPassword || "") : "";
    if (!sessionPassword) {
        const prompted = await promptCredentialRevealSessionPassword();
        if (prompted === null) {
            if (feedbackNode) {
                feedbackNode.textContent = "Affichage du mot de passe annule.";
            }
            return null;
        }
        sessionPassword = String(prompted || "");
        if (!sessionPassword) {
            if (feedbackNode) {
                feedbackNode.textContent = "Mot de passe de session requis.";
            }
            return null;
        }
    }
    if (feedbackNode) {
        feedbackNode.textContent = "Verification en cours...";
    }
    try {
        const payload = await requestJson(
            `/devices/${encodeURIComponent(String(device?.device_type || ""))}/${encodeURIComponent(String(device?.id || ""))}/credentials/reveal`,
            {
                method: "POST",
                body: JSON.stringify({ session_password: sessionPassword }),
            },
        );
        if (!unlocked) {
            applyCredentialRevealSessionPassword(sessionPassword);
        }
        applyRevealedCredentialsToInventory(device, payload);
        if (feedbackNode) {
            feedbackNode.textContent = "Mot de passe affiche.";
        }
        return payload;
    } catch (error) {
        const message = normalizeErrorMessage(error.message);
        if (message.toLowerCase().includes("mot de passe de session invalide")) {
            clearCredentialRevealState({ refresh: false });
        }
        if (feedbackNode) {
            feedbackNode.textContent = message;
        }
        return null;
    }
}

async function openDevicePasswordRevealModal(device) {
    const payload = await requestDevicePasswordReveal(device, { feedbackNode: inventoryFeedback });
    if (!payload) {
        return;
    }
    if (state.snapshot) {
        renderDevices(state.snapshot);
    }
    renderInventoryDetail();
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
                    <article class="log-item ${statusTransitionClass(row.old_status, row.new_status)}">
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
                ${createFieldMarkup({
                    key: "credential_reveal_unlock_seconds",
                    label: "Duree affichage identifiants (s)",
                    value: normalizeCredentialRevealUnlockSeconds(settings.credential_reveal_unlock_seconds),
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
            ${createModalActionsMarkup({
                buttons: [{ preset: "cancel" }, { preset: "save" }],
            })}
        </form>
    `;
}

function buildNotificationSettingsMarkup(settings) {
    const smtpPort = Number(settings.smtp_port || 0);
    const smtpPortValue = Number.isFinite(smtpPort) ? smtpPort : 0;
    const authEnabled = Boolean(settings.smtp_auth_enabled);
    return `
        <form id="modal-notification-form" class="modal-form">
            <div class="modal-settings-grid">
                ${createFieldMarkup({ key: "smtp_host", label: "SMTP host", value: settings.smtp_host || "" })}
                <label class="field">
                    <span>Port SMTP</span>
                    <select name="smtp_port">
                        <option value="25" ${smtpPortValue === 25 ? "selected" : ""}>25</option>
                        <option value="465" ${smtpPortValue === 465 ? "selected" : ""}>465</option>
                        <option value="587" ${smtpPortValue === 587 ? "selected" : ""}>587</option>
                        <option value="2525" ${smtpPortValue === 2525 ? "selected" : ""}>2525</option>
                        <option value="1025" ${smtpPortValue === 1025 ? "selected" : ""}>1025</option>
                    </select>
                </label>
                ${createFieldMarkup({ key: "recipients", label: "Destinataires", value: settings.recipients || "", wide: true })}
            </div>
            <label class="check-field">
                <input name="smtp_auth_enabled" type="checkbox" ${authEnabled ? "checked" : ""}>
                <span>Authentification SMTP requise</span>
            </label>
            <div class="modal-settings-grid" data-smtp-auth-fields ${authEnabled ? "" : "hidden"}>
                ${createFieldMarkup({ key: "user", label: "Utilisateur SMTP", value: settings.user || "" })}
                <label class="field">
                    <span>Mot de passe SMTP</span>
                    <input name="smtp_password" type="password" value="" autocomplete="new-password" placeholder="Laisser vide pour conserver">
                </label>
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
            ${createModalActionsMarkup({
                buttons: [{ preset: "cancel" }, { preset: "save" }],
            })}
        </form>
    `;
}

function buildMonitoringNotificationSettingsMarkup(settings) {
    const subject = String(
        settings.monitoring_notification_subject_template
            || "[Monitoring] {device_type} {device_name}: {old_status} -> {new_status}",
    );
    const body = String(
        settings.monitoring_notification_body_template
            || "Equipement: {device_name}\nType: {device_type}\nIP: {device_ip}\nStatut: {old_status} -> {new_status}",
    );
    return `
        <form id="modal-monitoring-notification-form" class="modal-form">
            <div class="modal-settings-grid">
                ${createFieldMarkup({ key: "notification_cooldown_seconds", label: "Cooldown notif (s)", value: settings.notification_cooldown_seconds || 120 })}
                <label class="field wide">
                    <span>Objet email</span>
                    <input name="monitoring_notification_subject_template" type="text" value="${escapeHtml(subject)}">
                </label>
                <label class="field wide">
                    <span>Corps email</span>
                    <textarea name="monitoring_notification_body_template" rows="6">${escapeHtml(body)}</textarea>
                </label>
            </div>
            <label class="check-field">
                <input name="monitoring_notify_on_outage" type="checkbox" ${settings.monitoring_notify_on_outage !== false ? "checked" : ""}>
                <span>Notifier le passage online -> offline</span>
            </label>
            <label class="check-field">
                <input name="monitoring_notify_on_recovery" type="checkbox" ${settings.monitoring_notify_on_recovery !== false ? "checked" : ""}>
                <span>Notifier le passage offline -> online</span>
            </label>
            <p class="muted">Variables: {device_type}, {device_name}, {device_ip}, {old_status}, {new_status}</p>
            <p id="modal-monitoring-notification-feedback" class="muted inventory-feedback"></p>
            ${createModalActionsMarkup({
                buttons: [{ preset: "cancel" }, { preset: "save" }],
            })}
        </form>
    `;
}

function buildWebServerSettingsMarkup(settings) {
    const sharedBuilder = window.NMPSharedUi?.webServer?.buildSettingsMarkup;
    if (typeof sharedBuilder === "function") {
        return sharedBuilder({
            settings,
            field: (key, label, value, wide = false) => createFieldMarkup({ key, label, value, wide }),
        });
    }
    const rawProxy = String(settings.web_server_reverse_proxy_type || "aucun").trim().toLowerCase();
    const reverseProxyType = ["aucun", "nginx", "caddy"].includes(rawProxy) ? rawProxy : "aucun";
    return `
        <form id="modal-webserver-form" class="modal-form">
            <div class="modal-settings-grid">
                ${createFieldMarkup({ key: "web_server_host", label: "Host", value: settings.web_server_host || "127.0.0.1" })}
                ${createFieldMarkup({ key: "web_server_port", label: "Port", value: settings.web_server_port || 8000 })}
                ${createFieldMarkup({ key: "web_server_public_url", label: "URL publique", value: settings.web_server_public_url || "", wide: true })}
                <label class="field">
                    <span>Reverse proxy</span>
                    <select name="web_server_reverse_proxy_type">
                        <option value="aucun" ${reverseProxyType === "aucun" ? "selected" : ""}>Aucun</option>
                        <option value="nginx" ${reverseProxyType === "nginx" ? "selected" : ""}>Nginx</option>
                        <option value="caddy" ${reverseProxyType === "caddy" ? "selected" : ""}>Caddy</option>
                    </select>
                </label>
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
            ${createModalActionsMarkup({
                buttons: [{ preset: "cancel" }, { preset: "save" }],
            })}
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

function clampNumber(value, minimum, maximum, fallback) {
    const parsed = Number(value);
    const base = Number.isFinite(parsed) ? parsed : fallback;
    return Math.max(minimum, Math.min(maximum, base));
}

function revokeWatermarkDraftPreviewUrl() {
    const current = state.watermarkEditorDraft;
    if (!current) {
        return;
    }
    const previewUrl = String(current.previewUrl || "").trim();
    if (previewUrl.startsWith("blob:")) {
        try {
            window.URL.revokeObjectURL(previewUrl);
        } catch (_error) {
        }
    }
}

function clearWatermarkEditorDraft() {
    revokeWatermarkDraftPreviewUrl();
    state.watermarkEditorDraft = null;
}

async function fetchWatermarkState() {
    return requestJson("/settings/watermark/state");
}

function watermarkPreviewTokenizedUrl(rawPath) {
    const path = String(rawPath || "").trim();
    if (!path) {
        return "";
    }
    const queryParts = [];
    const token = String(state.token || "").trim();
    if (token && path.includes("/ui/watermark-image")) {
        queryParts.push(`token=${encodeURIComponent(token)}`);
    }
    queryParts.push(`v=${encodeURIComponent(String(Date.now()))}`);
    const separator = path.includes("?") ? "&" : "?";
    return `${path}${separator}${queryParts.join("&")}`;
}

function createWatermarkEditorDraft(statePayload, override = {}) {
    const enabled = Boolean(statePayload?.enabled);
    const basePreviewUrl = enabled ? watermarkPreviewTokenizedUrl(statePayload?.image_url || "/ui/watermark-image") : "";
    return {
        hasExisting: enabled,
        sourceFileName: String(override.sourceFileName || "").trim(),
        sourceContentBase64: String(override.sourceContentBase64 || "").trim(),
        previewUrl: String(override.previewUrl || basePreviewUrl || "").trim(),
        opacity: clampNumber(override.opacity ?? statePayload?.opacity ?? 0.16, 0.05, 1.0, 0.16),
        offsetX: Math.round(clampNumber(override.offsetX ?? statePayload?.offset_x ?? 0, -300, 300, 0)),
        offsetY: Math.round(clampNumber(override.offsetY ?? statePayload?.offset_y ?? 0, -220, 220, 0)),
        zoomPercent: Math.round(clampNumber(override.zoomPercent ?? statePayload?.zoom_percent ?? 100, 40, 220, 100)),
    };
}

function buildWatermarkEditorMarkup(draft) {
    const sourceLabel = draft?.sourceFileName
        ? `Fichier selectionne: ${String(draft.sourceFileName)}`
        : (draft?.hasExisting ? "Image actuelle chargee." : "Aucune image selectionnee.");
    const opacityPercent = Math.round(clampNumber((draft?.opacity || 0.16) * 100, 5, 100, 16));
    return `
        <form id="modal-watermark-form" class="modal-form">
            <section class="modal-section watermark-editor-section">
                <div class="watermark-editor-head">
                    <p id="modal-watermark-source" class="muted">${escapeHtml(sourceLabel)}</p>
                    ${createActionButtonMarkup({
                        type: "button",
                        className: "toolbar-btn",
                        action: "watermark:pick-file",
                        label: "Importer",
                    })}
                </div>
                <div class="watermark-preview-shell">
                    <div id="modal-watermark-preview-image" class="watermark-preview-image"></div>
                </div>
            </section>

            <section class="watermark-controls">
                <label class="field wide">
                    <span>Opacite (<strong id="modal-watermark-opacity-value">${opacityPercent}%</strong>)</span>
                    <input id="modal-watermark-opacity" type="range" min="5" max="100" step="1" value="${opacityPercent}">
                </label>
                <label class="field">
                    <span>Cadrage horizontal (<strong id="modal-watermark-offset-x-value">${escapeHtml(String(draft?.offsetX || 0))}</strong> px)</span>
                    <input id="modal-watermark-offset-x" type="range" min="-300" max="300" step="1" value="${escapeHtml(String(draft?.offsetX || 0))}">
                </label>
                <label class="field">
                    <span>Cadrage vertical (<strong id="modal-watermark-offset-y-value">${escapeHtml(String(draft?.offsetY || 0))}</strong> px)</span>
                    <input id="modal-watermark-offset-y" type="range" min="-220" max="220" step="1" value="${escapeHtml(String(draft?.offsetY || 0))}">
                </label>
                <label class="field wide">
                    <span>Zoom (<strong id="modal-watermark-zoom-value">${escapeHtml(String(draft?.zoomPercent || 100))}%</strong>)</span>
                    <input id="modal-watermark-zoom" type="range" min="40" max="220" step="1" value="${escapeHtml(String(draft?.zoomPercent || 100))}">
                </label>
            </section>

            <p id="modal-watermark-feedback" class="muted inventory-feedback"></p>
            ${createModalActionsMarkup({
                buttons: [{ preset: "cancel" }, { preset: "save", label: "Appliquer" }],
            })}
        </form>
    `;
}

function renderWatermarkEditorPreview() {
    const draft = state.watermarkEditorDraft;
    const previewNode = document.getElementById("modal-watermark-preview-image");
    if (!draft || !(previewNode instanceof HTMLElement)) {
        return;
    }
    const previewUrl = String(draft.previewUrl || "").trim();
    previewNode.style.backgroundImage = previewUrl ? `url("${previewUrl.replaceAll('"', "%22")}")` : "none";
    previewNode.style.opacity = String(clampNumber(draft.opacity, 0.05, 1.0, 0.16));
    previewNode.style.backgroundPosition = `calc(50% + ${Math.round(draft.offsetX)}px) calc(50% + ${Math.round(draft.offsetY)}px)`;
    previewNode.style.backgroundSize = `${Math.round(clampNumber(draft.zoomPercent, 40, 220, 100))}% auto`;
    previewNode.classList.toggle("is-empty", !previewUrl);

    const sourceNode = document.getElementById("modal-watermark-source");
    if (sourceNode instanceof HTMLElement) {
        const sourceLabel = draft.sourceFileName
            ? `Fichier selectionne: ${String(draft.sourceFileName)}`
            : (draft.hasExisting ? "Image actuelle chargee." : "Aucune image selectionnee.");
        sourceNode.textContent = sourceLabel;
    }
    const opacityValue = document.getElementById("modal-watermark-opacity-value");
    if (opacityValue instanceof HTMLElement) {
        opacityValue.textContent = `${Math.round(clampNumber(draft.opacity * 100, 5, 100, 16))}%`;
    }
    const offsetXValue = document.getElementById("modal-watermark-offset-x-value");
    if (offsetXValue instanceof HTMLElement) {
        offsetXValue.textContent = String(Math.round(draft.offsetX));
    }
    const offsetYValue = document.getElementById("modal-watermark-offset-y-value");
    if (offsetYValue instanceof HTMLElement) {
        offsetYValue.textContent = String(Math.round(draft.offsetY));
    }
    const zoomValue = document.getElementById("modal-watermark-zoom-value");
    if (zoomValue instanceof HTMLElement) {
        zoomValue.textContent = `${Math.round(clampNumber(draft.zoomPercent, 40, 220, 100))}%`;
    }
}

async function pickWatermarkSourceIntoEditor() {
    const sharedImport = window.NMPSharedImport;
    const file = sharedImport && typeof sharedImport.pickFile === "function"
        ? await sharedImport.pickFile({ accept: ".png,.jpg,.jpeg,.webp,.bmp,.gif,image/*" })
        : await new Promise((resolve) => {
            const input = document.createElement("input");
            input.type = "file";
            input.accept = ".png,.jpg,.jpeg,.webp,.bmp,.gif,image/*";
            input.addEventListener("change", () => resolve(input.files && input.files[0] ? input.files[0] : null), { once: true });
            input.click();
        });
    if (!file) {
        return;
    }
    const base64Reader = sharedImport && typeof sharedImport.readAsBase64 === "function"
        ? sharedImport.readAsBase64(file)
        : new Promise((resolve, reject) => {
            const reader = new window.FileReader();
            reader.onload = () => {
                const result = String(reader.result || "");
                const marker = "base64,";
                const markerIndex = result.indexOf(marker);
                if (markerIndex < 0) {
                    reject(new Error("Encodage image impossible."));
                    return;
                }
                resolve(result.slice(markerIndex + marker.length));
            };
            reader.onerror = () => reject(new Error("Lecture image impossible."));
            reader.readAsDataURL(file);
        });
    const contentBase64 = String(await base64Reader);
    const previewUrl = window.URL.createObjectURL(file);
    const current = state.watermarkEditorDraft || createWatermarkEditorDraft({}, {});
    revokeWatermarkDraftPreviewUrl();
    state.watermarkEditorDraft = {
        ...current,
        sourceFileName: String(file.name || "watermark.png"),
        sourceContentBase64: contentBase64,
        previewUrl,
    };
    renderWatermarkEditorPreview();
}

async function openWatermarkEditorModal({ forceImport = false } = {}) {
    const watermarkState = await fetchWatermarkState().catch((error) => {
        if (forceImport) {
            return {
                enabled: false,
                opacity: 0.16,
                offset_x: 0,
                offset_y: 0,
                zoom_percent: 100,
                image_url: "",
            };
        }
        throw error;
    });
    clearWatermarkEditorDraft();
    state.watermarkEditorDraft = createWatermarkEditorDraft(watermarkState || {}, {});
    openModal("Image de fond", buildWatermarkEditorMarkup(state.watermarkEditorDraft), {
        width: "min(940px, calc(100vw - 40px))",
    });
    renderWatermarkEditorPreview();
    if (forceImport) {
        await pickWatermarkSourceIntoEditor();
    }
}

async function submitWatermarkEditorForm(form) {
    const draft = state.watermarkEditorDraft;
    const feedback = document.getElementById("modal-watermark-feedback");
    if (!draft) {
        throw new Error("Editeur image de fond indisponible.");
    }
    if (!String(draft.sourceContentBase64 || "").trim() && !draft.hasExisting) {
        throw new Error("Importer une image avant validation.");
    }
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton instanceof HTMLButtonElement) {
        submitButton.disabled = true;
    }
    if (feedback instanceof HTMLElement) {
        feedback.textContent = "Application en cours...";
    }
    try {
        await requestJson("/settings/watermark/apply", {
            method: "POST",
            body: JSON.stringify({
                filename: String(draft.sourceFileName || "watermark.png"),
                content_base64: String(draft.sourceContentBase64 || ""),
                opacity: clampNumber(draft.opacity, 0.05, 1.0, 0.16),
                offset_x: Math.round(clampNumber(draft.offsetX, -300, 300, 0)),
                offset_y: Math.round(clampNumber(draft.offsetY, -220, 220, 0)),
                zoom_percent: Math.round(clampNumber(draft.zoomPercent, 40, 220, 100)),
            }),
        });
        await loadUiConfig();
        if (state.snapshot) {
            await refreshSnapshot();
        }
        if (feedback instanceof HTMLElement) {
            feedback.textContent = "Image de fond appliquee.";
        }
        closeModal();
    } finally {
        if (submitButton instanceof HTMLButtonElement) {
            submitButton.disabled = false;
        }
    }
}

function buildConfigFilesManagerMarkup(device) {
    const configEnabled = Boolean(typeMeta(device.device_type)?.config_backups_enabled);
    const treeMarkup = window.NMPSharedUi?.treeView?.buildSectionMarkup?.({
        title: `${typeLabel(device.device_type)} / ${device.name}`,
        searchId: "config-files-search",
        searchPlaceholder: "Fichier, date, etat",
        searchInTitleRow: true,
        headId: "config-files-head",
        bodyId: "config-files-body",
        feedbackId: "modal-config-files-feedback",
        escapeHtml,
        escapeAttribute,
    }) || `
        <section class="modal-section">
            <div class="section-head slim-head">
                <h3>${escapeHtml(typeLabel(device.device_type))} / ${escapeHtml(device.name)}</h3>
                <span id="modal-config-files-state" class="muted">Chargement...</span>
            </div>
            <div id="modal-config-files-list" class="modal-log-list"></div>
            <p id="modal-config-files-feedback" class="muted inventory-feedback"></p>
        </section>
    `;
    return `
        <section class="modal-form">
            <p id="modal-config-files-state" class="muted">Chargement...</p>
            ${treeMarkup}
            ${createModalActionsMarkup({
                buttons: [
                    { preset: "close" },
                    { preset: "refresh", action: "config-modal:refresh", disabled: !configEnabled },
                    { preset: "download", action: "config-modal:download", disabled: !configEnabled },
                    { preset: "import", action: "config-modal:import", disabled: !configEnabled },
                ],
            })}
        </section>
    `;
}

async function refreshConfigFilesManagerModal() {
    const stateNode = document.getElementById("modal-config-files-state");
    if (!stateNode) {
        return;
    }
    const device = configManagerDevice();
    if (!device) {
        stateNode.textContent = "Indisponible";
        state.configFilesModalRows = [];
        configFilesTreeView?.render?.();
        return;
    }
    const meta = typeMeta(device.device_type);
    if (!meta?.config_backups_enabled) {
        stateNode.textContent = "Non disponible";
        state.configFilesModalRows = [];
        configFilesTreeView?.render?.();
        return;
    }
    stateNode.textContent = "Chargement...";
    try {
        const params = new URLSearchParams({
            device_type: device.device_type,
            device_id: device.id || "",
            device_type_label: typeLabel(device.device_type),
            device_name: device.name,
        });
        const rows = await requestJson(`/config-files?${params.toString()}`);
        const liveStateNode = document.getElementById("modal-config-files-state");
        if (!liveStateNode || deviceKey(device) !== state.configManagerDeviceKey) {
            return;
        }
        state.configFilesModalRows = (Array.isArray(rows) ? rows : []).map(normalizeConfigFileRow);
        liveStateNode.textContent = state.configFilesModalRows.length ? `${state.configFilesModalRows.length} fichier(s)` : "Aucun fichier";
        ensureConfigFilesTreeView()?.render?.();
    } catch (error) {
        const liveStateNode = document.getElementById("modal-config-files-state");
        if (!liveStateNode || deviceKey(device) !== state.configManagerDeviceKey) {
            return;
        }
        liveStateNode.textContent = "Erreur";
        setConfigFilesModalFeedback(normalizeErrorMessage(error.message));
    }
}

function setConfigFilesModalFeedback(message = "") {
    const feedback = document.getElementById("modal-config-files-feedback");
    if (feedback) {
        feedback.textContent = String(message || "");
    }
}

function ensureConfigFilesTreeView() {
    const BaseClass = window.NMPSharedUi?.treeView?.SharedTreeView;
    if (!BaseClass) {
        return null;
    }
    const head = document.getElementById("config-files-head");
    const body = document.getElementById("config-files-body");
    if (!head || !body) {
        return null;
    }
    if (
        configFilesTreeView instanceof ConfigFilesTreeView
        && configFilesTreeView.headElement === head
        && configFilesTreeView.bodyElement === body
    ) {
        return configFilesTreeView;
    }
    configFilesTreeView = new ConfigFilesTreeView({ mode: "device" });
    return configFilesTreeView;
}

function ensureConfigLibraryTreeView() {
    const BaseClass = window.NMPSharedUi?.treeView?.SharedTreeView;
    if (!BaseClass) {
        return null;
    }
    const head = document.getElementById("config-library-head");
    const body = document.getElementById("config-library-body");
    if (!head || !body) {
        return null;
    }
    if (
        configLibraryTreeView instanceof ConfigFilesTreeView
        && configLibraryTreeView.headElement === head
        && configLibraryTreeView.bodyElement === body
    ) {
        return configLibraryTreeView;
    }
    configLibraryTreeView = new ConfigFilesTreeView({ mode: "library" });
    return configLibraryTreeView;
}

async function openConfigFilesManagerModal(device) {
    state.configManagerDeviceKey = deviceKey(device);
    state.configFilesModalRows = [];
    configFilesTreeView = null;
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

async function openMonitoringNotificationSettingsModal() {
    const settings = await requestJson("/settings");
    openModal("Notifications Monitoring", buildMonitoringNotificationSettingsMarkup(settings), {
        width: "min(920px, calc(100vw - 40px))",
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
    const remoteHiddenAttr = mode === "smb3" ? "" : " hidden";
    return `
        <form id="modal-config-storage-form" class="modal-form">
            <div class="modal-settings-grid">
                ${createConfigStorageModeFieldMarkup(mode)}
            </div>
            <section id="modal-config-storage-remote-fields" class="config-storage-remote-fields"${remoteHiddenAttr}>
                <div class="modal-settings-grid">
                    ${createFieldMarkup({ key: "config_smb_unc_path", label: "Destination distante", value: settings.config_smb_unc_path || "", wide: true })}
                    ${createFieldMarkup({ key: "config_smb_username", label: "Utilisateur SMB", value: settings.config_smb_username || "" })}
                    ${createFieldMarkup({ key: "config_smb_password", label: "Mot de passe SMB", value: "", inputType: "password" })}
                    ${createFieldMarkup({ key: "config_auto_sync_interval_seconds", label: "Intervalle copie auto (s)", value: settings.config_auto_sync_interval_seconds || 3600 })}
                </div>
                <p class="muted config-storage-help">
                    Sous Linux, indiquez un chemin deja monte sur le serveur, par exemple /mnt/sauvegardes. Un chemin UNC Windows ne peut pas etre monte automatiquement par l'application.
                </p>
                <label class="check-field">
                    <input name="config_auto_sync_enabled" type="checkbox" ${settings.config_auto_sync_enabled ? "checked" : ""}>
                    <span>Copie distante automatique</span>
                </label>
            </section>
            ${renderConfigStorageStatePanel(storageState)}
            <p id="modal-config-storage-feedback" class="muted inventory-feedback"></p>
            ${createModalActionsMarkup({
                buttons: [
                    { preset: "cancel" },
                    { label: "Gestion fichiers de configuration", type: "button", action: "config-storage:explore" },
                    { label: "Tester", type: "button", action: "config-storage:test" },
                    { preset: "save" },
                ],
            })}
        </form>
    `;
}

function syncConfigStorageModeUi(form) {
    if (!(form instanceof HTMLFormElement)) {
        return;
    }
    const mode = String(form.querySelector('[name="config_storage_mode"]')?.value || "local").trim().toLowerCase();
    const remoteFields = form.querySelector("#modal-config-storage-remote-fields");
    if (remoteFields instanceof HTMLElement) {
        remoteFields.hidden = mode !== "smb3";
    }
}

function createConfigStorageModeFieldMarkup(mode) {
    const normalized = String(mode || "local").trim().toLowerCase() === "smb3" ? "smb3" : "local";
    const options = [
        { value: "local", label: "Local serveur uniquement" },
        { value: "smb3", label: "Redondance SMB3" },
    ];
    return `
        <label class="field">
            <span>Mode</span>
            <select name="config_storage_mode">
                ${options.map((option) => `
                    <option value="${escapeAttribute(option.value)}" ${option.value === normalized ? "selected" : ""}>
                        ${escapeHtml(option.label)}
                    </option>
                `).join("")}
            </select>
        </label>
    `;
}

function configStorageModeLabel(mode) {
    return String(mode || "").trim().toLowerCase() === "smb3" ? "Redondance SMB3" : "Local serveur uniquement";
}

function renderConfigStorageStatePanel(storageState) {
    const mode = String(storageState?.mode || "local").trim().toLowerCase();
    const ok = Boolean(storageState?.can_open_backup_folder);
    const statusClassName = mode === "smb3" ? (ok ? "tool-output-ok" : "tool-output-ko") : "tool-output-warning";
    const statusLabel = mode === "smb3" ? (ok ? "Accessible" : "Non accessible") : "Local actif";
    const message = String(storageState?.message || "Non teste").trim() || "Non teste";
    const passwordLabel = storageState?.has_smb_password ? "Oui" : "Non";
    const localPath = String(storageState?.local_storage_path || "").trim();
    const backupPath = String(storageState?.backup_path || "").trim();
    return `
        <div id="modal-config-storage-state" class="modal-tool-output config-storage-state ${statusClassName}">
            <strong>${escapeHtml(statusLabel)}</strong>
            <span>Mode teste: ${escapeHtml(configStorageModeLabel(mode))}</span>
            <span>${escapeHtml(message)}</span>
            ${localPath ? `<span>Stockage local serveur: ${escapeHtml(localPath)}</span>` : ""}
            ${backupPath ? `<span>Destination sauvegarde: ${escapeHtml(backupPath)}</span>` : ""}
            <span>Mot de passe SMB configure: ${escapeHtml(passwordLabel)}</span>
        </div>
    `;
}

function updateConfigStorageStatePanel(storageState) {
    const panel = document.getElementById("modal-config-storage-state");
    if (!panel) {
        return;
    }
    const wrapper = document.createElement("div");
    wrapper.innerHTML = renderConfigStorageStatePanel(storageState).trim();
    const nextPanel = wrapper.firstElementChild;
    if (nextPanel) {
        panel.replaceWith(nextPanel);
    }
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

function formatFileSize(bytes) {
    const value = Number(bytes || 0);
    if (!Number.isFinite(value) || value <= 0) {
        return "0 o";
    }
    if (value < 1024) {
        return `${Math.trunc(value)} o`;
    }
    const units = ["Ko", "Mo", "Go", "To"];
    let current = value / 1024;
    let unitIndex = 0;
    while (current >= 1024 && unitIndex < units.length - 1) {
        current /= 1024;
        unitIndex += 1;
    }
    return `${current.toFixed(current >= 10 ? 1 : 2)} ${units[unitIndex]}`;
}

function buildConfigLibraryExplorerMarkup() {
    const treeMarkup = window.NMPSharedUi?.treeView?.buildSectionMarkup?.({
        title: "Bibliotheque locale serveur",
        searchId: "config-library-search",
        searchPlaceholder: "Fichier, equipement, etat",
        searchInTitleRow: true,
        headId: "config-library-head",
        bodyId: "config-library-body",
        feedbackId: "modal-config-library-feedback",
        escapeHtml,
        escapeAttribute,
    }) || `
        <section class="modal-section">
            <div class="section-head slim-head">
                <h3>Bibliotheque locale serveur</h3>
                <span id="modal-config-library-state" class="muted">Chargement...</span>
            </div>
            <div id="modal-config-library-list" class="modal-log-list config-library-list"></div>
            <p id="modal-config-library-feedback" class="muted inventory-feedback"></p>
        </section>
    `;
    return `
        <section class="modal-form">
            <p id="modal-config-library-state" class="muted">Chargement...</p>
            ${treeMarkup}
            ${createModalActionsMarkup({
                buttons: [
                    { preset: "close" },
                    { preset: "refresh", action: "config-library:refresh" },
                ],
            })}
        </section>
    `;
}

async function refreshConfigLibraryExplorer() {
    const stateNode = document.getElementById("modal-config-library-state");
    if (!stateNode) {
        return;
    }
    stateNode.textContent = "Chargement...";
    try {
        const rows = await requestJson("/config-storage/files?limit=1000");
        state.configLibraryRows = (Array.isArray(rows) ? rows : []).map(normalizeConfigFileRow);
        stateNode.textContent = state.configLibraryRows.length ? `${state.configLibraryRows.length} fichier(s)` : "Aucun fichier";
        ensureConfigLibraryTreeView()?.render?.();
    } catch (error) {
        stateNode.textContent = "Erreur";
        const message = normalizeErrorMessage(error.message);
        const detail = String(message || "").toLowerCase().includes("not found")
            ? "Route d'exploration introuvable cote serveur. Redemarrez le backend PyCharm puis rechargez la page avec Ctrl+F5."
            : message;
        const feedback = document.getElementById("modal-config-library-feedback");
        if (feedback) {
            feedback.textContent = detail;
        }
    }
}

function renderConfigLibraryRow(row) {
    const deviceLabel = [
        String(row?.device_type_label || row?.device_type || "").trim(),
        String(row?.device_name || "").trim(),
    ].filter(Boolean).join(" / ") || "Equipement inconnu";
    const meta = [
        String(row?.modified_at || "").trim(),
        formatFileSize(row?.size_bytes),
        String(row?.sync_status || "").trim(),
    ].filter(Boolean).join(" | ");
    return `
        <article class="log-item config-library-item">
            <div class="config-library-item-main">
                <div>
                    <div class="config-item-title">${escapeHtml(row?.name || "config.cfg")}</div>
                    <div class="config-item-meta">${escapeHtml(deviceLabel)}</div>
                    <div class="config-item-meta">${escapeHtml(meta)}</div>
                    ${row?.detail ? `<div class="log-item-body">${escapeHtml(row.detail)}</div>` : ""}
                    ${row?.sync_error ? `<div class="error-text">${escapeHtml(row.sync_error)}</div>` : ""}
                </div>
                ${createIconActionButtonMarkup({
                    icon: "download",
                    label: "Telecharger",
                    action: "config-library:download",
                    title: "Telecharger ce fichier",
                    data: { file_id: row?.id || "" },
                })}
            </div>
        </article>
    `;
}

async function openConfigLibraryExplorerModal() {
    state.configLibraryRows = [];
    configLibraryTreeView = null;
    openModal("Gestion fichiers de configuration", buildConfigLibraryExplorerMarkup(), {
        width: "min(1040px, calc(100vw - 40px))",
    });
    await refreshConfigLibraryExplorer();
}

async function downloadConfigLibraryFile(fileId) {
    const normalizedId = String(fileId || "").trim();
    if (!normalizedId) {
        throw new Error("Fichier introuvable.");
    }
    const url = `/config-files/${encodeURIComponent(normalizedId)}/download`;
    const sharedDownload = window.NMPSharedDownload?.downloadFile;
    if (typeof sharedDownload === "function") {
        await sharedDownload({
            url,
            method: "GET",
            headers: {
                ...headers(),
            },
            defaultFilename: "config.cfg",
            normalizeErrorMessage,
        });
        return;
    }
    const response = await fetch(url, {
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
        throw new Error(detail);
    }
    const blob = await response.blob();
    const objectUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = "config.cfg";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(objectUrl);
}

async function deleteConfigFile(fileId, fileName = "") {
    const normalizedId = String(fileId || "").trim();
    if (!normalizedId) {
        throw new Error("Ce fichier ne peut pas etre supprime depuis cette vue car il n'est pas encore associe au moteur de fichiers lies.");
    }
    if (!window.confirm(`Supprimer '${fileName || "ce fichier"}' ?`)) {
        return false;
    }
    await requestJson(`/config-files/${encodeURIComponent(normalizedId)}`, { method: "DELETE" });
    return true;
}

function storageExplorerCurrentRoot() {
    return (Array.isArray(state.storageExplorer.roots) ? state.storageExplorer.roots : [])
        .find((root) => String(root?.id || "") === String(state.storageExplorer.rootId || "")) || null;
}

function buildStorageExplorerMarkup() {
    const roots = Array.isArray(state.storageExplorer.roots) ? state.storageExplorer.roots : [];
    const currentRootId = String(state.storageExplorer.rootId || "");
    const currentRoot = storageExplorerCurrentRoot();
    const pathLabel = String(state.storageExplorer.path || "/").trim() || "/";
    const rootOptions = roots.map((root) => `
        <option value="${escapeAttribute(String(root?.id || ""))}" ${String(root?.id || "") === currentRootId ? "selected" : ""}>
            ${escapeHtml(String(root?.label || root?.id || "Stockage"))}
        </option>
    `).join("");
    const rootMeta = currentRoot
        ? [
            String(currentRoot.service_label || currentRoot.service_code || "").trim(),
            String(currentRoot.kind || "").trim(),
            currentRoot.accessible ? "Accessible" : "Non accessible",
        ].filter(Boolean).join(" - ")
        : "";
    return `
        <section class="modal-form">
            <div class="section-head slim-head">
                <div>
                    <h3>Explorateur de stockage</h3>
                    <p class="muted">${escapeHtml(pathLabel === "/" ? "Racine" : pathLabel)}</p>
                    ${rootMeta ? `<p class="muted">${escapeHtml(rootMeta)}</p>` : ""}
                </div>
            </div>
            <div class="inventory-controls">
                <label class="field inline-field">
                    <span>Racine</span>
                    <select id="storage-explorer-root">${rootOptions}</select>
                </label>
                ${createIconActionButtonMarkup({ icon: "refresh", action: "storage-explorer:refresh", title: "Rafraichir" })}
                ${createActionButtonMarkup({
                    className: "toolbar-btn",
                    type: "button",
                    action: "storage-explorer:up",
                    label: "Remonter",
                    disabled: !String(state.storageExplorer.path || "").trim(),
                })}
                ${createActionButtonMarkup({ className: "toolbar-btn", type: "button", action: "storage-explorer:mkdir", label: "Nouveau dossier" })}
                ${createActionButtonMarkup({ className: "toolbar-btn", type: "button", action: "storage-explorer:upload", label: "Importer" })}
            </div>
            <div class="table-wrap shared-treeview-table-wrap">
                <table class="device-table shared-treeview-table">
                    <thead>
                        <tr>
                            <th>Nom</th>
                            <th>Type</th>
                            <th>Taille</th>
                            <th>Modifie</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>${renderStorageExplorerRows()}</tbody>
                </table>
            </div>
            <input id="storage-explorer-upload-input" type="file" hidden>
            <p id="storage-explorer-feedback" class="muted inventory-feedback"></p>
            ${createModalActionsMarkup({
                buttons: [{ preset: "close" }],
            })}
        </section>
    `;
}

function renderStorageExplorerRows() {
    const items = Array.isArray(state.storageExplorer.items) ? state.storageExplorer.items : [];
    if (!items.length) {
        return `<tr><td colspan="5" class="muted">Dossier vide.</td></tr>`;
    }
    return items.map((item) => {
        const path = String(item?.path || "");
        const isFolder = String(item?.kind || "") === "folder";
        return `
            <tr>
                <td>
                    <button class="link-btn" type="button" data-action="${isFolder ? "storage-explorer:enter" : "storage-explorer:download"}" data-path="${escapeAttribute(path)}">
                        ${escapeHtml(String(item?.name || ""))}
                    </button>
                </td>
                <td>${isFolder ? "Dossier" : "Fichier"}</td>
                <td>${isFolder ? "-" : escapeHtml(formatFileSize(item?.size_bytes))}</td>
                <td>${escapeHtml(String(item?.modified_at || ""))}</td>
                <td class="inventory-row-actions">
                    ${isFolder ? "" : createIconActionButtonMarkup({
                        icon: "download",
                        action: "storage-explorer:download",
                        title: "Telecharger",
                        data: { path },
                    })}
                    ${createIconActionButtonMarkup({
                        icon: "delete",
                        danger: true,
                        action: "storage-explorer:delete",
                        title: "Supprimer",
                        data: { path, item_name: String(item?.name || "") },
                    })}
                </td>
            </tr>
        `;
    }).join("");
}

async function loadStorageExplorerRoots(preferredRootId = "", options = {}) {
    const serviceCode = String(options.serviceCode || "").trim();
    const params = new URLSearchParams();
    if (serviceCode) {
        params.set("service_code", serviceCode);
    }
    const suffix = params.toString() ? `?${params.toString()}` : "";
    const roots = await requestJson(`/storage/explorer/roots${suffix}`);
    state.storageExplorer.roots = Array.isArray(roots) ? roots : [];
    const preferred = String(preferredRootId || "").trim();
    const existing = state.storageExplorer.roots.some((root) => String(root?.id || "") === preferred);
    if (existing) {
        state.storageExplorer.rootId = preferred;
        return;
    }
    const remoteRoot = state.storageExplorer.roots.find((root) => String(root?.id || "").startsWith("target:"));
    state.storageExplorer.rootId = String((remoteRoot || state.storageExplorer.roots[0])?.id || "");
}

async function refreshStorageExplorer(path = state.storageExplorer.path) {
    const rootId = String(state.storageExplorer.rootId || "").trim();
    if (!rootId) {
        state.storageExplorer.items = [];
        state.storageExplorer.path = "";
        return;
    }
    const params = new URLSearchParams({ root_id: rootId, path: String(path || "") });
    const result = await requestJson(`/storage/explorer/list?${params.toString()}`);
    state.storageExplorer.rootId = String(result?.root_id || rootId);
    state.storageExplorer.rootLabel = String(result?.root_label || "");
    state.storageExplorer.path = String(result?.path || "");
    state.storageExplorer.parentPath = String(result?.parent_path || "");
    state.storageExplorer.items = Array.isArray(result?.items) ? result.items : [];
    state.storageExplorer.roots = (Array.isArray(state.storageExplorer.roots) ? state.storageExplorer.roots : []).map((root) => (
        String(root?.id || "") === state.storageExplorer.rootId
            ? { ...root, accessible: true }
            : root
    ));
}

function renderStorageExplorerModal() {
    openModal("Explorateur de stockage", buildStorageExplorerMarkup(), {
        width: "min(1040px, calc(100vw - 40px))",
    });
}

async function openMonitoringStorageExplorerModal() {
    await loadStorageExplorerRoots("", { serviceCode: "monitoring.device_config_files" });
    await refreshStorageExplorer("");
    renderStorageExplorerModal();
}

async function reloadStorageExplorerModal(path = state.storageExplorer.path) {
    await refreshStorageExplorer(path);
    renderStorageExplorerModal();
}

async function downloadStorageExplorerItem(path) {
    const rootId = String(state.storageExplorer.rootId || "").trim();
    if (!rootId) {
        throw new Error("Racine de stockage introuvable.");
    }
    const params = new URLSearchParams({ root_id: rootId, path: String(path || "") });
    const url = `/storage/explorer/download?${params.toString()}`;
    const sharedDownload = window.NMPSharedDownload?.downloadFile;
    if (typeof sharedDownload === "function") {
        await sharedDownload({
            url,
            method: "GET",
            headers: { ...headers() },
            defaultFilename: String(path || "fichier").split("/").pop() || "fichier",
            normalizeErrorMessage,
        });
        return;
    }
    window.open(url, "_blank", "noopener,noreferrer");
}

async function createStorageExplorerFolder() {
    const name = window.prompt("Nom du nouveau dossier");
    if (!name) {
        return;
    }
    await requestJson("/storage/explorer/folders", {
        method: "POST",
        body: JSON.stringify({
            root_id: state.storageExplorer.rootId,
            path: state.storageExplorer.path,
            name,
        }),
    });
    await reloadStorageExplorerModal();
}

async function deleteStorageExplorerItem(path, name = "") {
    if (!path || !window.confirm(`Supprimer '${name || path}' ?`)) {
        return;
    }
    await requestJson("/storage/explorer/items", {
        method: "DELETE",
        body: JSON.stringify({
            root_id: state.storageExplorer.rootId,
            path,
        }),
    });
    await reloadStorageExplorerModal();
}

async function uploadStorageExplorerFile(file) {
    if (!file) {
        return;
    }
    const readAsBase64 = window.NMPSharedImport?.readAsBase64;
    if (typeof readAsBase64 !== "function") {
        throw new Error("Module d'import indisponible.");
    }
    const contentBase64 = String(await readAsBase64(file));
    await requestJson("/storage/explorer/upload", {
        method: "POST",
        body: JSON.stringify({
            root_id: state.storageExplorer.rootId,
            path: state.storageExplorer.path,
            filename: String(file.name || "upload.bin"),
            content_base64: contentBase64,
        }),
    });
    await reloadStorageExplorerModal();
}

async function submitConfigStorageSettings(form, options = {}) {
    const formData = new window.FormData(form);
    const mode = String(formData.get("config_storage_mode") || "local").trim().toLowerCase();
    const intervalRaw = Number(formData.get("config_auto_sync_interval_seconds") || 3600);
    const interval = Number.isFinite(intervalRaw) ? Math.max(5, Math.trunc(intervalRaw)) : 3600;
    await applySettingsPatch(
        {
            config_storage_mode: mode === "smb3" ? "smb3" : "local",
            switch_configs_dir: "",
            config_smb_unc_path: mode === "smb3" ? String(formData.get("config_smb_unc_path") || "").trim() : "",
            config_smb_username: mode === "smb3" ? String(formData.get("config_smb_username") || "").trim() : "",
            config_smb_password: mode === "smb3" ? String(formData.get("config_smb_password") || "") : "",
            config_auto_sync_enabled: mode === "smb3" && (form.querySelector('[name="config_auto_sync_enabled"]')?.checked ?? false),
            config_auto_sync_interval_seconds: interval,
        },
        options.silent ? "" : "modal-config-storage-feedback",
    );
    await loadConfigStorageState();
    if (!options.keepOpen) {
        window.setTimeout(() => closeModal(), 400);
    }
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
        const message = String(result?.message || "").trim();
        if (options.openClientPath) {
            const fileUrl = messagePathToFileUrl(message);
            if (fileUrl) {
                window.open(fileUrl, "_blank", "noopener,noreferrer");
                inventoryFeedback.textContent = message || "Ouverture du dossier demandee.";
                return;
            }
            openModal(
                "Dossier de sauvegarde",
                `
                    <section class="modal-section">
                        <p class="muted">${escapeHtml(message || "Le dossier est disponible sur le serveur ITops.")}</p>
                        <p class="muted">Depuis l'interface web, un chemin Linux serveur ne peut pas ouvrir directement l'explorateur du poste utilisateur.</p>
                    </section>
                    ${createModalActionsMarkup({
                        buttons: [
                            { preset: "cancel", label: "Fermer" },
                            { label: "Gestion fichiers de configuration", type: "button", action: "config-storage:explore" },
                        ],
                    })}
                `,
                { width: "min(680px, calc(100vw - 40px))" },
            );
            return;
        }
        inventoryFeedback.textContent = message || "Operation terminee.";
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

function platformLabelFromKey(platformKey) {
    const raw = String(platformKey || "").replaceAll(",", " ").trim().replace(/\s+/g, " ");
    if (!raw) {
        return "";
    }
    const normalized = normalizePlatform(platformKey);
    if (normalized === "windows") {
        return "Windows";
    }
    if (normalized === "linux") {
        return "Linux";
    }
    if (normalized === "firmware") {
        return "Firmware";
    }
    if (normalized === "autre") {
        return "Autre";
    }
    return raw;
}

function shallowCloneRows(rows) {
    return Array.isArray(rows) ? rows.map((row) => ({ ...(row || {}) })) : [];
}

function typeSchemaFieldByKey(editor, fieldKey) {
    const target = String(fieldKey || "").trim();
    return (editor.fields || []).find((field) => String(field.field_key || "").trim() === target) || null;
}

function typeSchemaEnsureCoreFields(editor) {
    const byKey = {};
    for (const field of editor.fields || []) {
        const key = String(field.field_key || "").trim();
        if (!key) {
            continue;
        }
        byKey[key] = { ...field, field_key: key };
    }
    for (const key of ["name", "description", "type"]) {
        if (!byKey[key]) {
            byKey[key] = { field_key: key, ...TYPE_SCHEMA_CORE_FIELDS[key] };
        }
        byKey[key] = {
            ...byKey[key],
            show_in_table: schemaFieldVisibleInTable(byKey[key], Boolean(TYPE_SCHEMA_CORE_FIELDS[key]?.show_in_table)),
        };
    }
    let typeOptions = String(byKey.type?.options || TYPE_SCHEMA_CORE_FIELDS.type.options)
        .split(",")
        .map((item) => platformLabelFromKey(item))
        .filter(Boolean);
    typeOptions = Array.from(new Set(typeOptions));
    if (!typeOptions.length) {
        typeOptions = [...PLATFORM_OPTIONS];
    }
    let typeDefault = platformLabelFromKey(String(byKey.type?.default_value || ""));
    if (!typeOptions.includes(typeDefault)) {
        typeDefault = typeOptions[0] || PLATFORM_OPTIONS[0];
    }
    byKey.type = {
        ...byKey.type,
        field_key: "type",
        label: String(byKey.type?.label || "OS").trim() || "OS",
        field_kind: "choice",
        required: true,
        options: typeOptions.join(","),
        default_value: typeDefault,
        show_in_table: schemaFieldVisibleInTable(byKey.type, false),
    };
    if (editor.monitoringEnabled) {
        if (!byKey.ip) {
            byKey.ip = { field_key: "ip", ...TYPE_SCHEMA_CORE_FIELDS.ip };
        }
        byKey.ip = {
            ...byKey.ip,
            field_key: "ip",
            label: String(byKey.ip.label || "IP").trim() || "IP",
            field_kind: "ip",
            required: true,
            options: "",
            show_in_table: schemaFieldVisibleInTable(byKey.ip, true),
        };
    } else {
        delete byKey.ip;
    }

    if (editor.configBackupsEnabled) {
        if (!byKey.config_saved) {
            byKey.config_saved = { field_key: "config_saved", ...TYPE_SCHEMA_CORE_FIELDS.config_saved };
        }
        byKey.config_saved = {
            ...byKey.config_saved,
            field_key: "config_saved",
            label: String(byKey.config_saved.label || "Cfg").trim() || "Cfg",
            field_kind: "text",
            required: false,
            options: "",
            show_in_table: schemaFieldVisibleInTable(byKey.config_saved, true),
        };
    } else {
        delete byKey.config_saved;
    }

    if (!byKey.notify) {
        byKey.notify = { field_key: "notify", ...TYPE_SCHEMA_CORE_FIELDS.notify };
    }
    byKey.notify = {
        ...byKey.notify,
        field_key: "notify",
        label: String(byKey.notify.label || "Alertes changement").trim() || "Alertes changement",
        field_kind: "text",
        required: false,
        options: "",
        show_in_table: schemaFieldVisibleInTable(byKey.notify, true),
    };

    if (editor.credentialsEnabled) {
        if (!byKey.device_login) {
            byKey.device_login = { field_key: "device_login", ...TYPE_SCHEMA_CREDENTIAL_FIELDS.device_login };
        }
        byKey.device_login = {
            ...byKey.device_login,
            field_key: "device_login",
            label: String(byKey.device_login.label || "Login").trim() || "Login",
            field_kind: "text",
            required: false,
            options: "",
            show_in_table: schemaFieldVisibleInTable(byKey.device_login, true),
        };
        if (!byKey.device_password) {
            byKey.device_password = { field_key: "device_password", ...TYPE_SCHEMA_CREDENTIAL_FIELDS.device_password };
        }
        byKey.device_password = {
            ...byKey.device_password,
            field_key: "device_password",
            label: String(byKey.device_password.label || "Mot de passe").trim() || "Mot de passe",
            field_kind: "text",
            required: false,
            options: "",
            show_in_table: schemaFieldVisibleInTable(byKey.device_password, true),
        };
    } else {
        delete byKey.device_login;
        delete byKey.device_password;
    }

    const ordered = [];
    for (const key of ["name", "description", "type", "ip", "device_login", "device_password", "config_saved"]) {
        if (byKey[key]) {
            ordered.push(byKey[key]);
            delete byKey[key];
        }
    }
    const customExisting = (editor.fields || []).filter((field) => byKey[String(field.field_key || "").trim()]);
    const seen = new Set(ordered.map((field) => String(field.field_key || "").trim()));
    for (const field of customExisting) {
        const key = String(field.field_key || "").trim();
        if (!key || seen.has(key) || !byKey[key]) {
            continue;
        }
        ordered.push(byKey[key]);
        seen.add(key);
        delete byKey[key];
    }
    for (const field of Object.values(byKey)) {
        const key = String(field.field_key || "").trim();
        if (!key || seen.has(key)) {
            continue;
        }
        ordered.push(field);
        seen.add(key);
    }
    editor.fields = ordered;
}

function typeSchemaReindexSorts(editor) {
    editor.fields = (editor.fields || []).map((field, idx) => ({
        ...(field || {}),
        sort_order: (idx + 1) * 10,
    }));
    editor.actions = (editor.actions || []).map((action, idx) => ({
        ...(action || {}),
        sort_order: (idx + 1) * 10,
    }));
}

function typeSchemaIsSystemField(fieldKey) {
    const key = String(fieldKey || "").trim().toLowerCase();
    return TYPE_SCHEMA_SYSTEM_FIELD_KEYS.has(key);
}

function typeSchemaCustomFieldUsageCount(editor, fieldKey) {
    const typeCode = String(editor?.typeCode || "").trim().toLowerCase();
    const key = String(fieldKey || "").trim();
    if (!typeCode || !key) {
        return 0;
    }
    return (state.inventory || []).reduce((count, device) => {
        if (String(device?.device_type || "").trim().toLowerCase() !== typeCode) {
            return count;
        }
        const value = device?.custom_data?.[key];
        if (value == null) {
            return count;
        }
        return String(value).trim() ? count + 1 : count;
    }, 0);
}

function typeSchemaEditableCustomFields(editor) {
    return (editor.fields || []).filter((field) => !typeSchemaIsSystemField(field?.field_key));
}

function typeSchemaVisibleSystemFields(editor) {
    const fields = [];
    for (const key of TYPE_SCHEMA_TABLE_SYSTEM_FIELD_KEYS) {
        const field = typeSchemaFieldByKey(editor, key);
        if (field) {
            fields.push(field);
        }
    }
    return fields;
}

function typeSchemaNormalizeFieldKind(rawKind) {
    const normalized = String(rawKind || "text").trim().toLowerCase();
    return TYPE_SCHEMA_FIELD_KINDS.includes(normalized) ? normalized : "text";
}

function typeSchemaFieldKindLabel(kind) {
    const normalized = typeSchemaNormalizeFieldKind(kind);
    return TYPE_SCHEMA_FIELD_KIND_LABELS[normalized] || normalized;
}

function typeSchemaBuildCustomFieldKey(editor, label) {
    let base = String(label || "")
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "");
    if (!base) {
        base = "custom_field";
    }
    if (typeSchemaIsSystemField(base)) {
        base = `custom_${base}`;
    }
    const keys = new Set((editor.fields || []).map((field) => String(field?.field_key || "").trim().toLowerCase()));
    let candidate = base;
    let idx = 2;
    while (keys.has(candidate)) {
        candidate = `${base}_${idx}`;
        idx += 1;
    }
    return candidate;
}

function typeSchemaStartCustomFieldEditor(editor, fieldKey = "") {
    const key = String(fieldKey || "").trim();
    const existing = key
        ? (editor.fields || []).find((field) => String(field?.field_key || "").trim() === key)
        : null;
    if (existing && typeSchemaIsSystemField(existing.field_key)) {
        return { ok: false, message: "Ce champ est gere automatiquement." };
    }
    editor.fieldEditor = {
        key: existing ? String(existing.field_key || "").trim() : "",
        label: existing ? String(existing.label || "").trim() : "",
        field_kind: typeSchemaNormalizeFieldKind(existing?.field_kind || "text"),
        required: Boolean(existing?.required),
        options: existing ? String(existing.options || "") : "",
        default_value: existing ? String(existing.default_value || "") : "",
        show_in_table: existing ? schemaFieldVisibleInTable(existing, false) : true,
        mode: existing ? "edit" : "create",
    };
    return { ok: true };
}

function typeSchemaCancelCustomFieldEditor(editor) {
    editor.fieldEditor = null;
}

function typeSchemaSaveCustomFieldEditor(editor, payload) {
    const label = String(payload?.label || "").trim();
    if (!label) {
        return { ok: false, message: "Libelle de champ requis." };
    }
    const kind = typeSchemaNormalizeFieldKind(payload?.field_kind);
    const required = Boolean(payload?.required);
    const options = parseChoiceOptions(payload?.options);
    let defaultValue = String(payload?.default_value || "").trim();
    if (kind === "choice") {
        if (!options.length) {
            return { ok: false, message: "Ajoute au moins une option pour une liste." };
        }
        if (!options.some((item) => item.toLowerCase() === defaultValue.toLowerCase())) {
            defaultValue = options[0];
        } else {
            defaultValue = options.find((item) => item.toLowerCase() === defaultValue.toLowerCase()) || options[0];
        }
    } else {
        defaultValue = String(payload?.default_value || "");
    }

    const draftKey = String(editor.fieldEditor?.key || "").trim();
    const editIndex = draftKey
        ? (editor.fields || []).findIndex((field) => String(field?.field_key || "").trim() === draftKey)
        : -1;
    const fieldKey = draftKey || typeSchemaBuildCustomFieldKey(editor, label);
    const existingShowInTable = editIndex >= 0
        ? schemaFieldVisibleInTable(editor.fields[editIndex], false)
        : true;
    if (editIndex >= 0) {
        const currentKind = typeSchemaNormalizeFieldKind(editor.fields[editIndex]?.field_kind || "text");
        if (currentKind !== kind) {
            const usageCount = typeSchemaCustomFieldUsageCount(editor, fieldKey);
            if (usageCount > 0) {
                return {
                    ok: false,
                    message: `Nature verrouillee: ${usageCount} equipement(s) utilisent deja ce champ. Cree un nouveau champ.`,
                };
            }
        }
    }
    const nextField = {
        field_key: fieldKey,
        label,
        field_kind: kind,
        required,
        options: kind === "choice" ? options.join(",") : "",
        default_value: defaultValue,
        show_in_table: Boolean(payload?.show_in_table ?? editor.fieldEditor?.show_in_table ?? existingShowInTable),
    };
    if (editIndex >= 0) {
        editor.fields[editIndex] = {
            ...(editor.fields[editIndex] || {}),
            ...nextField,
        };
    } else {
        editor.fields.push(nextField);
    }
    typeSchemaReindexSorts(editor);
    editor.fieldEditor = null;
    return { ok: true };
}

function typeSchemaDeleteCustomField(editor, fieldKey) {
    const key = String(fieldKey || "").trim();
    if (!key) {
        return { ok: false, message: "Champ introuvable." };
    }
    if (typeSchemaIsSystemField(key)) {
        return { ok: false, message: "Ce champ est gere automatiquement." };
    }
    const before = (editor.fields || []).length;
    editor.fields = (editor.fields || []).filter((field) => String(field?.field_key || "").trim() !== key);
    if ((editor.fields || []).length === before) {
        return { ok: false, message: "Champ introuvable." };
    }
    typeSchemaReindexSorts(editor);
    if (String(editor.fieldEditor?.key || "").trim() === key) {
        editor.fieldEditor = null;
    }
    return { ok: true };
}

function typeSchemaOsOptions(editor) {
    const typeField = typeSchemaFieldByKey(editor, "type");
    const parsed = String(typeField?.options || "")
        .split(",")
        .map((item) => platformLabelFromKey(item))
        .filter(Boolean);
    const unique = Array.from(new Set(parsed));
    return unique.length ? unique : [...PLATFORM_OPTIONS];
}

function typeSchemaSetOsOptions(editor, options) {
    const selected = Array.from(new Set((Array.isArray(options) ? options : []).map((item) => platformLabelFromKey(item))));
    const finalOptions = selected.length ? selected : [PLATFORM_OPTIONS[0]];
    typeSchemaEnsureCoreFields(editor);
    const idx = (editor.fields || []).findIndex((field) => String(field.field_key || "").trim() === "type");
    if (idx < 0) {
        return;
    }
    const current = editor.fields[idx] || {};
    let nextDefault = platformLabelFromKey(String(current.default_value || ""));
    if (!finalOptions.includes(nextDefault)) {
        nextDefault = finalOptions[0];
    }
    editor.fields[idx] = {
        ...current,
        field_key: "type",
        label: String(current.label || "OS").trim() || "OS",
        field_kind: "choice",
        required: true,
        options: finalOptions.join(","),
        default_value: nextDefault,
    };
    if (!finalOptions.includes(editor.selectedOs)) {
        editor.selectedOs = finalOptions[0];
    }
}

function typeSchemaNormalizedOsSet(options) {
    const out = new Set();
    for (const item of Array.isArray(options) ? options : []) {
        out.add(normalizePlatform(item));
    }
    return out;
}

function typeSchemaHiddenDefaultField(editor) {
    return typeSchemaFieldByKey(editor, "action_default_by_os");
}

function typeSchemaReadDefaultMap(editor) {
    const field = typeSchemaHiddenDefaultField(editor);
    const raw = String(field?.default_value || "").trim();
    if (!raw) {
        return {};
    }
    try {
        const parsed = JSON.parse(raw);
        if (!parsed || typeof parsed !== "object") {
            return {};
        }
        const map = {};
        for (const [osKey, actionKey] of Object.entries(parsed)) {
            const normalizedOs = normalizePlatform(osKey);
            const normalizedAction = String(actionKey || "").trim().toLowerCase();
            if (!normalizedAction) {
                continue;
            }
            map[normalizedOs] = normalizedAction;
        }
        return map;
    } catch (_error) {
        return {};
    }
}

function typeSchemaWriteDefaultMap(editor, map) {
    const cleaned = {};
    for (const [osKey, actionKey] of Object.entries(map || {})) {
        const normalizedOs = normalizePlatform(osKey);
        const normalizedAction = String(actionKey || "").trim().toLowerCase();
        if (!normalizedAction) {
            continue;
        }
        cleaned[normalizedOs] = normalizedAction;
    }
    typeSchemaEnsureField(editor, "action_default_by_os", {
        label: "Action par defaut par OS",
        field_kind: "text",
        required: false,
        options: "",
        default_value: JSON.stringify(cleaned),
    });
}

function typeSchemaCleanupDefaultMapForOs(editor) {
    const allowedNorm = typeSchemaNormalizedOsSet(typeSchemaOsOptions(editor));
    const current = typeSchemaReadDefaultMap(editor);
    const next = {};
    for (const [osKey, actionKey] of Object.entries(current)) {
        if (!allowedNorm.has(normalizePlatform(osKey))) {
            continue;
        }
        next[normalizePlatform(osKey)] = String(actionKey || "").trim().toLowerCase();
    }
    typeSchemaWriteDefaultMap(editor, next);
}

function typeSchemaCleanupDefaultMapForActions(editor) {
    const current = typeSchemaReadDefaultMap(editor);
    const next = {};
    for (const [osKey, actionKey] of Object.entries(current)) {
        const normalizedOs = normalizePlatform(osKey);
        const normalizedAction = String(actionKey || "").trim().toLowerCase();
        if (!normalizedAction) {
            continue;
        }
        const action = (editor.actions || [])
            .find((item) => String(item?.action_key || "").trim().toLowerCase() === normalizedAction);
        if (!action) {
            continue;
        }
        if (!actionAllowsOs(String(action.os_scope || ""), normalizedOs)) {
            continue;
        }
        next[normalizedOs] = normalizedAction;
    }
    typeSchemaWriteDefaultMap(editor, next);
}

function typeSchemaSetDefaultActionForSelectedOs(editor, actionKey) {
    const normalizedOs = normalizePlatform(editor.selectedOs);
    const key = String(actionKey || "").trim().toLowerCase();
    if (!key) {
        return;
    }
    const current = typeSchemaReadDefaultMap(editor);
    current[normalizedOs] = key;
    typeSchemaWriteDefaultMap(editor, current);
    typeSchemaSetDefaultAction(editor, key);
    typeSchemaSetDoubleClickAction(editor, key);
}

function typeSchemaValidateOsLabel(label) {
    const value = String(label || "").trim();
    if (!value) {
        return { ok: false, message: "Nom OS requis." };
    }
    if (value.includes(",")) {
        return { ok: false, message: "Le nom OS ne peut pas contenir de virgule." };
    }
    return { ok: true };
}

function typeSchemaAddOsOption(editor, label) {
    const value = String(label || "").trim();
    const validity = typeSchemaValidateOsLabel(value);
    if (!validity.ok) {
        return validity;
    }
    const options = typeSchemaOsOptions(editor);
    if (options.some((item) => item.toLowerCase() === value.toLowerCase())) {
        return { ok: false, message: "OS deja present." };
    }
    const next = [...options, value];
    typeSchemaSetOsOptions(editor, next);
    editor.selectedOs = value;
    typeSchemaCleanupDefaultMapForOs(editor);
    typeSchemaEnsureActionDoubleClickField(editor);
    typeSchemaReindexSorts(editor);
    return { ok: true };
}

function typeSchemaRenameOsOption(editor, oldLabel, newLabel) {
    const oldValue = String(oldLabel || "").trim();
    const nextValue = String(newLabel || "").trim();
    if (!oldValue) {
        return { ok: false, message: "OS source introuvable." };
    }
    const validity = typeSchemaValidateOsLabel(nextValue);
    if (!validity.ok) {
        return validity;
    }
    const options = typeSchemaOsOptions(editor);
    const idx = options.findIndex((item) => item.toLowerCase() === oldValue.toLowerCase());
    if (idx < 0) {
        return { ok: false, message: "OS source introuvable." };
    }
    const clash = options.find((item, i) => i !== idx && item.toLowerCase() === nextValue.toLowerCase());
    if (clash) {
        return { ok: false, message: "OS deja present." };
    }
    const updated = [...options];
    updated[idx] = nextValue;
    const oldNorm = normalizePlatform(oldValue);
    const newNorm = normalizePlatform(nextValue);
    if (oldNorm !== newNorm) {
        editor.actions = (editor.actions || []).map((action) => {
            const scope = parseOsScope(String(action.os_scope || ""));
            if (!scope.includes(oldNorm)) {
                return action;
            }
            const nextScope = new Set(scope);
            nextScope.delete(oldNorm);
            nextScope.add(newNorm);
            return { ...(action || {}), os_scope: formatOsScope(Array.from(nextScope)) };
        });
        const defaults = typeSchemaReadDefaultMap(editor);
        if (defaults[oldNorm]) {
            defaults[newNorm] = defaults[oldNorm];
            delete defaults[oldNorm];
            typeSchemaWriteDefaultMap(editor, defaults);
        }
    }
    typeSchemaSetOsOptions(editor, updated);
    if (String(editor.selectedOs || "").toLowerCase() === oldValue.toLowerCase()) {
        editor.selectedOs = nextValue;
    }
    typeSchemaCleanupDefaultMapForOs(editor);
    typeSchemaCleanupDefaultMapForActions(editor);
    typeSchemaEnsureActionDoubleClickField(editor);
    typeSchemaReindexSorts(editor);
    return { ok: true };
}

function typeSchemaDeleteOsOption(editor, label) {
    const value = String(label || "").trim();
    const options = typeSchemaOsOptions(editor);
    const idx = options.findIndex((item) => item.toLowerCase() === value.toLowerCase());
    if (idx < 0) {
        return { ok: false, message: "OS introuvable." };
    }
    if (options.length <= 1) {
        return { ok: false, message: "Au moins un OS est requis." };
    }
    const removedNorm = normalizePlatform(options[idx]);
    const nextOptions = options.filter((_item, i) => i !== idx);
    const remainingNormSet = typeSchemaNormalizedOsSet(nextOptions);
    if (!remainingNormSet.has(removedNorm)) {
        editor.actions = (editor.actions || []).map((action) => {
            const scope = parseOsScope(String(action.os_scope || ""));
            if (!scope.includes(removedNorm)) {
                return action;
            }
            const nextScope = scope.filter((item) => item !== removedNorm);
            return { ...(action || {}), os_scope: formatOsScope(nextScope) };
        }).filter((action) => String(action.os_scope || "").trim());
        const defaults = typeSchemaReadDefaultMap(editor);
        if (defaults[removedNorm]) {
            delete defaults[removedNorm];
            typeSchemaWriteDefaultMap(editor, defaults);
        }
    }
    typeSchemaSetOsOptions(editor, nextOptions);
    if (String(editor.selectedOs || "").toLowerCase() === value.toLowerCase()) {
        editor.selectedOs = nextOptions[0];
    }
    typeSchemaCleanupDefaultMapForOs(editor);
    typeSchemaCleanupDefaultMapForActions(editor);
    typeSchemaEnsureActionDoubleClickField(editor);
    typeSchemaReindexSorts(editor);
    return { ok: true };
}

function typeSchemaEnsureField(editor, fieldKey, payload = {}) {
    const key = String(fieldKey || "").trim();
    if (!key) {
        return;
    }
    const idx = (editor.fields || []).findIndex((field) => String(field.field_key || "").trim() === key);
    const normalized = { field_key: key, ...(payload || {}) };
    if (idx < 0) {
        editor.fields.push(normalized);
        return;
    }
    editor.fields[idx] = { ...(editor.fields[idx] || {}), ...normalized };
}

function typeSchemaSetDefaultAction(editor, actionKey) {
    const key = String(actionKey || "").trim().toLowerCase();
    if (!key) {
        return;
    }
    editor.actions = (editor.actions || []).map((action) => ({
        ...(action || {}),
        is_default: String(action?.action_key || "").trim().toLowerCase() === key,
    }));
}

function typeSchemaEnsureAction(editor, actionKey, payload = {}, includeSelectedOs = false) {
    const key = String(actionKey || "").trim().toLowerCase();
    if (!key) {
        return;
    }
    const idx = (editor.actions || []).findIndex((action) => String(action.action_key || "").trim().toLowerCase() === key);
    const current = idx >= 0 ? { ...(editor.actions[idx] || {}) } : {};
    const targetScope = includeSelectedOs
        ? parseOsScope(String(current.os_scope || "")).concat([normalizePlatform(editor.selectedOs)])
        : parseOsScope(String(current.os_scope || ""));
    const merged = {
        action_key: key,
        label: String(payload.label || current.label || actionLabel(key)).trim() || actionLabel(key),
        target_kind: String(payload.target_kind || current.target_kind || "builtin").trim().toLowerCase() || "builtin",
        target_value: String(payload.target_value || current.target_value || key).trim(),
        os_scope: formatOsScope(targetScope),
        is_default: Boolean(payload.is_default ?? current.is_default),
    };
    if (idx < 0) {
        editor.actions.push(merged);
    } else {
        editor.actions[idx] = merged;
    }
    if (merged.is_default) {
        typeSchemaSetDefaultAction(editor, key);
    }
}

function typeSchemaEnsureActionDoubleClickField(editor) {
    const actionKeys = (editor.actions || [])
        .map((action) => String(action.action_key || "").trim().toLowerCase())
        .filter(Boolean);
    const uniqueActionKeys = Array.from(new Set(actionKeys));
    const existing = typeSchemaFieldByKey(editor, "action_double_click");
    const previousDefault = String(existing?.default_value || "").trim().toLowerCase();
    const defaultValue = uniqueActionKeys.includes(previousDefault) ? previousDefault : (uniqueActionKeys[0] || "");
    typeSchemaEnsureField(editor, "action_double_click", {
        label: "Action double-clic",
        field_kind: "choice",
        required: false,
        options: uniqueActionKeys.join(","),
        default_value: defaultValue,
    });
}

function typeSchemaSetDoubleClickAction(editor, actionKey) {
    const key = String(actionKey || "").trim().toLowerCase();
    if (!key) {
        return;
    }
    typeSchemaEnsureActionDoubleClickField(editor);
    const idx = (editor.fields || []).findIndex((field) => String(field.field_key || "").trim() === "action_double_click");
    if (idx < 0) {
        return;
    }
    editor.fields[idx] = {
        ...(editor.fields[idx] || {}),
        default_value: key,
    };
}

function typeSchemaApplyPluginBlock(editor, blockKey) {
    const key = String(blockKey || "").trim().toLowerCase();
    if (key === "ssh") {
        typeSchemaEnsureField(editor, "ssh_user", {
            label: "Login SSH",
            field_kind: "text",
            required: false,
            options: "",
            default_value: "",
        });
        typeSchemaEnsureAction(editor, "ssh", { label: "Ouvrir SSH", target_kind: "builtin", target_value: "ssh" }, true);
    }
    if (key === "teamviewer") {
        typeSchemaEnsureField(editor, "id_Teamviewer", {
            label: "ID TeamViewer",
            field_kind: "text",
            required: false,
            options: "",
            default_value: "",
        });
        typeSchemaEnsureAction(
            editor,
            "teamviewer",
            { label: "Ouvrir TeamViewer", target_kind: "builtin", target_value: "teamviewer" },
            true,
        );
    }
    if (key === "remote_desktop") {
        typeSchemaEnsureAction(
            editor,
            "remote_desktop",
            { label: "Ouvrir Remote Desktop", target_kind: "builtin", target_value: "remote_desktop" },
            true,
        );
    }
    if (key === "web") {
        typeSchemaEnsureField(editor, "web_url", {
            label: "URL interface web",
            field_kind: "url",
            required: false,
            options: "",
            default_value: "",
        });
        typeSchemaEnsureAction(editor, "web", { label: "Ouvrir Web", target_kind: "builtin", target_value: "web" }, true);
    }
    typeSchemaEnsureCoreFields(editor);
    typeSchemaEnsureActionDoubleClickField(editor);
    typeSchemaReindexSorts(editor);
}

function typeSchemaActionInSelectedOs(editor, action) {
    return actionAllowsOs(String(action?.os_scope || ""), editor.selectedOs);
}

function typeSchemaVisibleActionKeys(editor) {
    return (editor.actions || [])
        .filter((action) => typeSchemaActionInSelectedOs(editor, action))
        .map((action) => String(action.action_key || "").trim().toLowerCase())
        .filter(Boolean);
}

function typeSchemaInsertIndexForX(otherKeys, xClient) {
    const tiles = Array.from(appModalBody.querySelectorAll("[data-schema-action-key]"));
    const tileMap = new Map(tiles.map((tile) => [String(tile.getAttribute("data-schema-action-key") || "").trim().toLowerCase(), tile]));
    let insertIdx = otherKeys.length;
    for (let idx = 0; idx < otherKeys.length; idx += 1) {
        const key = String(otherKeys[idx] || "").trim().toLowerCase();
        const tile = tileMap.get(key);
        if (!(tile instanceof HTMLElement)) {
            continue;
        }
        const rect = tile.getBoundingClientRect();
        const centerX = rect.left + (rect.width / 2);
        if (xClient < centerX) {
            insertIdx = idx;
            break;
        }
    }
    return insertIdx;
}

function typeSchemaReorderActionByPosition(editor, actionKey, xClient) {
    const draggedKey = String(actionKey || "").trim().toLowerCase();
    if (!draggedKey) {
        return;
    }
    const currentKeys = (editor.actions || [])
        .map((action) => String(action.action_key || "").trim().toLowerCase())
        .filter(Boolean);
    const visibleKeys = typeSchemaVisibleActionKeys(editor);
    if (!currentKeys.includes(draggedKey) || !visibleKeys.includes(draggedKey)) {
        return;
    }
    if (visibleKeys.length <= 1) {
        return;
    }
    const otherKeys = visibleKeys.filter((key) => key !== draggedKey);
    const insertIdx = typeSchemaInsertIndexForX(otherKeys, xClient);
    const reorderedVisible = [...otherKeys];
    reorderedVisible.splice(insertIdx, 0, draggedKey);
    if (JSON.stringify(reorderedVisible) === JSON.stringify(visibleKeys)) {
        return;
    }
    const visibleSet = new Set(visibleKeys);
    let replacementIdx = 0;
    const orderedKeys = currentKeys.map((key) => {
        if (!visibleSet.has(key)) {
            return key;
        }
        const nextKey = reorderedVisible[replacementIdx] || key;
        replacementIdx += 1;
        return nextKey;
    });
    const actionByKey = new Map(
        (editor.actions || [])
            .map((action) => [String(action.action_key || "").trim().toLowerCase(), action]),
    );
    editor.actions = orderedKeys
        .map((key) => actionByKey.get(key))
        .filter(Boolean);
    typeSchemaEnsureActionDoubleClickField(editor);
    typeSchemaReindexSorts(editor);
}

function typeSchemaSetActionMembership(editor, actionKey, enabled) {
    const key = String(actionKey || "").trim().toLowerCase();
    if (!key) {
        return false;
    }
    const targetOs = normalizePlatform(editor.selectedOs);
    let changed = false;
    editor.actions = (editor.actions || []).map((action) => {
        if (String(action.action_key || "").trim().toLowerCase() !== key) {
            return action;
        }
        const previous = parseOsScope(String(action.os_scope || ""));
        const beforeSignature = previous.join(",");
        const nextSet = new Set(previous);
        if (enabled) {
            nextSet.add(targetOs);
        } else {
            nextSet.delete(targetOs);
        }
        const nextScope = formatOsScope(Array.from(nextSet));
        changed = changed || beforeSignature !== parseOsScope(nextScope).join(",");
        return {
            ...action,
            os_scope: nextScope,
        };
    });
    return changed;
}

function typeSchemaRemoveActionForSelectedOs(editor, actionKey) {
    const changed = typeSchemaSetActionMembership(editor, actionKey, false);
    editor.actions = (editor.actions || []).filter((action) => String(action.os_scope || "").trim());
    typeSchemaCleanupDefaultMapForActions(editor);
    typeSchemaEnsureActionDoubleClickField(editor);
    typeSchemaReindexSorts(editor);
    return changed;
}

function typeSchemaPluginBadge(blockKey) {
    const key = String(blockKey || "").trim().toLowerCase();
    const row = TYPE_SCHEMA_PLUGIN_BLOCKS.find((item) => String(item.key || "").trim().toLowerCase() === key);
    return row ? String(row.badge || "ACT") : "ACT";
}

function createTypeSchemaEditorState(typeCode, schema, overrides = {}) {
    const code = String(typeCode || "").trim().toLowerCase();
    const createMode = Boolean(overrides.create_mode) || !code;
    const meta = createMode ? {} : (typeMeta(code) || {});
    const fields = createMode
        ? []
        : shallowCloneRows(schema?.fields).filter((field) => String(field.field_key || "").trim() !== "action_double_click");
    const actions = createMode ? [] : shallowCloneRows(schema?.actions);
    const credentialsEnabled = Boolean(
        overrides.credentials_enabled
        ?? meta.credentials_enabled
        ?? fields.some((field) => {
            const key = String(field?.field_key || "").trim().toLowerCase();
            return key === "device_login" || key === "device_password";
        }),
    );
    const editor = {
        createMode,
        typeCode: code,
        typeLabel: String(overrides.label || meta.label || "").trim(),
        monitoringEnabled: Boolean(overrides.monitoring_enabled ?? meta.monitoring_enabled ?? true),
        configBackupsEnabled: Boolean(overrides.config_backups_enabled ?? meta.config_backups_enabled ?? false),
        credentialsEnabled,
        initialCredentialsEnabled: credentialsEnabled,
        purgeTypeCredentialsOnSave: null,
        typeVersionToken: String(overrides.version_token || meta.version_token || ""),
        schemaVersionToken: String(schema?.version_token || ""),
        fields,
        actions,
        selectedOs: PLATFORM_OPTIONS[0],
        fieldEditor: null,
    };
    typeSchemaEnsureCoreFields(editor);
    typeSchemaEnsureActionDoubleClickField(editor);
    typeSchemaReindexSorts(editor);
    const osOptions = typeSchemaOsOptions(editor);
    editor.selectedOs = osOptions[0] || PLATFORM_OPTIONS[0];
    const defaults = typeSchemaReadDefaultMap(editor);
    if (!Object.keys(defaults).length) {
        const fallbackDefault = (editor.actions || []).find((action) => Boolean(action?.is_default));
        if (fallbackDefault) {
            const actionKey = String(fallbackDefault.action_key || "").trim().toLowerCase();
            const scope = parseOsScope(String(fallbackDefault.os_scope || ""));
            const targetOs = scope.length ? scope : Array.from(typeSchemaNormalizedOsSet(osOptions));
            const map = {};
            for (const osKey of targetOs) {
                map[normalizePlatform(osKey)] = actionKey;
            }
            typeSchemaWriteDefaultMap(editor, map);
        }
    } else {
        typeSchemaCleanupDefaultMapForOs(editor);
    }
    return editor;
}

function buildDeviceTypeSchemaEditorMarkup() {
    const editor = state.typeSchemaEditor;
    if (!editor) {
        return "";
    }
    const title = editor.createMode ? "Nouveau type" : `Edition du type: ${editor.typeLabel || editor.typeCode}`;
    return `
        <form id="modal-device-type-schema-form" class="modal-form">
            <section class="modal-section">
                <h3>${escapeHtml(title)}</h3>
                <div class="modal-settings-grid">
                    ${createFieldMarkup({ key: "type_schema_label", label: "Libelle", value: editor.typeLabel })}
                </div>
                <label class="check-field">
                    <input id="type-schema-monitoring" name="type_schema_monitoring_enabled" type="checkbox" ${editor.monitoringEnabled ? "checked" : ""}>
                    <span>Type monitorable</span>
                </label>
                <label class="check-field">
                    <input id="type-schema-config" name="type_schema_config_backups_enabled" type="checkbox" ${editor.configBackupsEnabled ? "checked" : ""}>
                    <span>Sauvegardes de configuration</span>
                </label>
                <label class="check-field">
                    <input id="type-schema-credentials" name="type_schema_credentials_enabled" type="checkbox" ${editor.credentialsEnabled ? "checked" : ""}>
                    <span>Gestion des identifiants</span>
                </label>
            </section>
            <section class="modal-section type-schema-layout">
                <div class="type-schema-panel type-schema-panel-os">
                    <div class="type-schema-os-head">
                        <h3>Liste OS</h3>
                        ${createIconActionButtonMarkup({
                            icon: "add",
                            action: "types:os:add",
                            title: "Ajouter un OS",
                        })}
                    </div>
                    <p class="muted">Selectionner un OS, puis gerer ses plugins a droite.</p>
                    <div id="type-schema-os-options" class="type-schema-os-options"></div>
                </div>
                <div class="type-schema-panel">
                    <div class="type-schema-toolbar">
                        <span class="type-schema-os-context">OS cible: <strong id="type-schema-selected-os-label">${escapeHtml(editor.selectedOs || PLATFORM_OPTIONS[0])}</strong></span>
                    </div>
                    <h3>Plugins de prise en main a distance</h3>
                    <p class="muted">Glisser-deposer un plugin vers la zone menu pour l'associer a l'OS cible.</p>
                    <div id="type-schema-plugin-catalog" class="type-schema-plugin-catalog"></div>
                    <h3>Menu contextuel (OS cible)</h3>
                    <div id="type-schema-drop-zone" class="type-schema-drop-zone">
                        <div id="type-schema-menu-actions" class="type-schema-menu-actions"></div>
                    </div>
                    <div id="type-schema-remove-zone" class="type-schema-remove-zone">Deposer ici pour retirer le plugin de cet OS</div>
                </div>
            </section>
            <section class="modal-section type-schema-fields-section">
                <div class="type-schema-fields-head">
                    <h3>Champs systeme</h3>
                </div>
                <p class="muted">Champs geres par l'application. Ils ne sont pas supprimables.</p>
                <div id="type-schema-system-fields-list" class="type-schema-custom-fields-list"></div>
                <div class="type-schema-fields-head">
                    <h3>Champs personnalisables</h3>
                    ${createIconActionButtonMarkup({
                        icon: "add",
                        action: "types:field:add",
                        title: "Ajouter un champ",
                    })}
                </div>
                <p class="muted">Ajoute des champs sans code et choisis ceux qui doivent apparaitre dans le tableau.</p>
                <div id="type-schema-custom-fields-list" class="type-schema-custom-fields-list"></div>
                <div id="type-schema-field-editor" class="type-schema-field-editor" hidden>
                    <div class="type-schema-field-editor-title" id="type-schema-field-editor-title">Nouveau champ</div>
                    <div class="type-schema-field-grid">
                        <label class="field">
                            <span>Libelle</span>
                            <input id="type-schema-field-label" type="text" value="">
                        </label>
                        <label class="field">
                            <span>Nature</span>
                            <select id="type-schema-field-kind">
                                ${TYPE_SCHEMA_FIELD_KINDS.map((kind) => `<option value="${escapeHtml(kind)}">${escapeHtml(typeSchemaFieldKindLabel(kind))}</option>`).join("")}
                            </select>
                        </label>
                        <label class="field">
                            <span>Valeur par defaut</span>
                            <input id="type-schema-field-default" type="text" value="">
                        </label>
                        <label class="field wide" id="type-schema-field-options-wrap">
                            <span>Options (liste, separees par des virgules)</span>
                            <input id="type-schema-field-options" type="text" value="">
                        </label>
                    </div>
                    <label class="check-field">
                        <input id="type-schema-field-required" type="checkbox">
                        <span>Champ obligatoire</span>
                    </label>
                    <label class="check-field">
                        <input id="type-schema-field-show-table" type="checkbox">
                        <span>Afficher dans le tableau</span>
                    </label>
                    <div class="type-schema-field-actions">
                        ${createActionButtonMarkup({ preset: "cancel", action: "types:field:cancel" })}
                        ${createActionButtonMarkup({ preset: "save", type: "button", action: "types:field:save", label: "Enregistrer le champ" })}
                    </div>
                </div>
            </section>
            <p id="modal-device-type-schema-feedback" class="muted inventory-feedback"></p>
            ${createModalActionsMarkup({
                buttons: [
                    { preset: "back", action: "types:back" },
                    {
                        preset: editor.createMode ? "add" : "save",
                        label: editor.createMode ? "Ajouter le type" : "Enregistrer",
                    },
                ],
            })}
        </form>
    `;
}

function renderDeviceTypeSchemaEditor() {
    const editor = state.typeSchemaEditor;
    if (!editor) {
        return;
    }
    const osOptions = typeSchemaOsOptions(editor);
    if (!osOptions.includes(editor.selectedOs)) {
        editor.selectedOs = osOptions[0] || PLATFORM_OPTIONS[0];
    }

    const osOptionsWrap = document.getElementById("type-schema-os-options");
    if (osOptionsWrap instanceof HTMLElement) {
        osOptionsWrap.innerHTML = osOptions.map((label) => {
            const selected = label === editor.selectedOs;
            return `
            <div class="type-schema-os-item${selected ? " is-selected" : ""}">
                <button
                    class="type-schema-os-select-btn"
                    type="button"
                    data-action="types:os:select"
                    data-os-label="${escapeAttribute(label)}"
                >${escapeHtml(label)}</button>
                ${createIconActionButtonMarkup({
                    icon: "settings",
                    action: "types:os:edit",
                    title: "Modifier cet OS",
                    data: { os_label: label },
                })}
                ${createIconActionButtonMarkup({
                    icon: "delete",
                    danger: true,
                    action: "types:os:delete",
                    title: "Supprimer cet OS",
                    data: { os_label: label },
                    disabled: osOptions.length <= 1,
                })}
            </div>
        `;
        }).join("");
    }
    const selectedOsLabel = document.getElementById("type-schema-selected-os-label");
    if (selectedOsLabel instanceof HTMLElement) {
        selectedOsLabel.textContent = editor.selectedOs || PLATFORM_OPTIONS[0];
    }

    const pluginCatalog = document.getElementById("type-schema-plugin-catalog");
    if (pluginCatalog instanceof HTMLElement) {
        pluginCatalog.innerHTML = TYPE_SCHEMA_PLUGIN_BLOCKS.map((plugin) => `
            <button
                class="type-schema-plugin"
                type="button"
                draggable="true"
                data-schema-plugin-key="${escapeAttribute(plugin.key)}"
                title="${escapeAttribute(plugin.title)}"
            >
                <span class="type-schema-plugin-badge">${escapeHtml(plugin.badge)}</span>
                <span>${escapeHtml(plugin.title)}</span>
            </button>
        `).join("");
    }

    const menuActions = document.getElementById("type-schema-menu-actions");
    if (menuActions instanceof HTMLElement) {
        const defaultMap = typeSchemaReadDefaultMap(editor);
        const selectedNorm = normalizePlatform(editor.selectedOs);
        const visibleActions = (editor.actions || []).filter((action) => typeSchemaActionInSelectedOs(editor, action));
        if (!visibleActions.length) {
            menuActions.innerHTML = `<div class="muted">Aucun plugin affecte a ${escapeHtml(editor.selectedOs)}.</div>`;
        } else {
            menuActions.innerHTML = visibleActions.map((action) => {
                const actionKey = String(action.action_key || "").trim().toLowerCase();
                const badge = typeSchemaPluginBadge(actionKey);
                const label = String(action.label || actionLabel(actionKey)).trim() || actionLabel(actionKey);
                const isDefault = String(defaultMap[selectedNorm] || "").trim().toLowerCase() === actionKey
                    || (Boolean(action.is_default) && !defaultMap[selectedNorm]);
                return `
                    <div class="type-schema-action-tile" draggable="true" data-schema-action-key="${escapeAttribute(actionKey)}" title="${escapeAttribute(label)}">
                        <span class="type-schema-action-badge">${escapeHtml(badge)}</span>
                        <span class="type-schema-action-label">${escapeHtml(label)}</span>
                        <button
                            class="type-schema-default-btn${isDefault ? " is-default" : ""}"
                            type="button"
                            draggable="false"
                            data-action="types:plugins:set-default"
                            data-action-key="${escapeAttribute(actionKey)}"
                            title="Definir action double-clic"
                        >${isDefault ? "Defaut" : "Par defaut"}</button>
                    </div>
                `;
            }).join("");
        }
    }

    const systemFieldsWrap = document.getElementById("type-schema-system-fields-list");
    if (systemFieldsWrap instanceof HTMLElement) {
        const systemFields = typeSchemaVisibleSystemFields(editor);
        if (!systemFields.length) {
            systemFieldsWrap.innerHTML = `<div class="muted">Aucun champ systeme visible pour ce type.</div>`;
        } else {
            systemFieldsWrap.innerHTML = systemFields.map((field) => {
                const key = String(field?.field_key || "").trim();
                const label = String(field?.label || fieldLabel(key)).trim() || key;
                const kindLabel = typeSchemaFieldKindLabel(field?.field_kind || "text");
                const required = Boolean(field?.required);
                return `
                    <div class="type-schema-custom-field-row type-schema-custom-field-row-system">
                        <div class="type-schema-custom-field-meta">
                            <strong>${escapeHtml(label)}</strong>
                            <span>${escapeHtml(kindLabel)}${required ? " | obligatoire" : ""} | non supprimable</span>
                        </div>
                        <label class="type-schema-table-toggle">
                            <input
                                type="checkbox"
                                data-action="types:field:toggle-table"
                                data-field-key="${escapeAttribute(key)}"
                                ${schemaFieldVisibleInTable(field, defaultShowInTableForField(key)) ? "checked" : ""}
                            >
                            <span>Tableau</span>
                        </label>
                    </div>
                `;
            }).join("");
        }
    }

    const customFieldsWrap = document.getElementById("type-schema-custom-fields-list");
    if (customFieldsWrap instanceof HTMLElement) {
        const customFields = typeSchemaEditableCustomFields(editor);
        if (!customFields.length) {
            customFieldsWrap.innerHTML = `<div class="muted">Aucun champ personnalise.</div>`;
        } else {
            customFieldsWrap.innerHTML = customFields.map((field) => {
                const key = String(field?.field_key || "").trim();
                const label = String(field?.label || key).trim() || key;
                const kind = typeSchemaNormalizeFieldKind(field?.field_kind || "text");
                const kindLabel = typeSchemaFieldKindLabel(kind);
                const required = Boolean(field?.required);
                return `
                    <div class="type-schema-custom-field-row">
                        <div class="type-schema-custom-field-meta">
                            <strong>${escapeHtml(label)}</strong>
                            <span>${escapeHtml(kindLabel)}${required ? " | obligatoire" : ""}</span>
                        </div>
                        <label class="type-schema-table-toggle">
                            <input
                                type="checkbox"
                                data-action="types:field:toggle-table"
                                data-field-key="${escapeAttribute(key)}"
                                ${schemaFieldVisibleInTable(field, false) ? "checked" : ""}
                            >
                            <span>Tableau</span>
                        </label>
                        ${createIconActionButtonMarkup({
                            icon: "settings",
                            action: "types:field:edit",
                            title: "Modifier ce champ",
                            data: { field_key: key },
                        })}
                        ${createIconActionButtonMarkup({
                            icon: "delete",
                            danger: true,
                            action: "types:field:delete",
                            title: "Supprimer ce champ",
                            data: { field_key: key },
                        })}
                    </div>
                `;
            }).join("");
        }
    }

    const fieldEditorPanel = document.getElementById("type-schema-field-editor");
    const fieldEditorTitle = document.getElementById("type-schema-field-editor-title");
    const fieldLabelInput = document.getElementById("type-schema-field-label");
    const fieldKindSelect = document.getElementById("type-schema-field-kind");
    const fieldRequiredCheckbox = document.getElementById("type-schema-field-required");
    const fieldShowTableCheckbox = document.getElementById("type-schema-field-show-table");
    const fieldOptionsWrap = document.getElementById("type-schema-field-options-wrap");
    const fieldOptionsInput = document.getElementById("type-schema-field-options");
    const fieldDefaultInput = document.getElementById("type-schema-field-default");
    if (
        fieldEditorPanel instanceof HTMLElement
        && fieldEditorTitle instanceof HTMLElement
        && fieldLabelInput instanceof HTMLInputElement
        && fieldKindSelect instanceof HTMLSelectElement
        && fieldRequiredCheckbox instanceof HTMLInputElement
        && fieldShowTableCheckbox instanceof HTMLInputElement
        && fieldOptionsWrap instanceof HTMLElement
        && fieldOptionsInput instanceof HTMLInputElement
        && fieldDefaultInput instanceof HTMLInputElement
    ) {
        const draft = editor.fieldEditor && typeof editor.fieldEditor === "object" ? editor.fieldEditor : null;
        fieldEditorPanel.hidden = !draft;
        if (draft) {
            fieldEditorTitle.textContent = draft.mode === "edit" ? "Modifier le champ" : "Nouveau champ";
            fieldLabelInput.value = String(draft.label || "");
            fieldKindSelect.value = typeSchemaNormalizeFieldKind(draft.field_kind || "text");
            fieldRequiredCheckbox.checked = Boolean(draft.required);
            fieldShowTableCheckbox.checked = Boolean(draft.show_in_table ?? true);
            fieldOptionsInput.value = String(draft.options || "");
            fieldDefaultInput.value = String(draft.default_value || "");
            fieldOptionsWrap.hidden = typeSchemaNormalizeFieldKind(draft.field_kind || "text") !== "choice";
        }
    }
}

async function openDeviceTypeEditorModal(typeCode, overrides = {}) {
    const code = String(typeCode || "").trim().toLowerCase();
    if (!code) {
        return;
    }
    const schema = await ensureDeviceTypeSchema(code);
    state.typeSchemaEditorContext = captureTypeSchemaEditorContext();
    state.typeSchemaEditor = createTypeSchemaEditorState(code, schema, overrides);
    state.typeSchemaDrag = null;
    const modalOptions = {
        width: "min(1120px, calc(100vw - 40px))",
    };
    openModal(`Edition type: ${state.typeSchemaEditor.typeLabel || code}`, buildDeviceTypeSchemaEditorMarkup(), {
        ...modalOptions,
    });
    renderDeviceTypeSchemaEditor();
}

function openCreateDeviceTypeEditorModal() {
    state.typeSchemaEditorContext = captureTypeSchemaEditorContext();
    state.typeSchemaEditor = createTypeSchemaEditorState("", { fields: [], actions: [] }, { create_mode: true });
    state.typeSchemaDrag = null;
    const modalOptions = {
        width: "min(1120px, calc(100vw - 40px))",
    };
    openModal("Ajouter un type d'equipement", buildDeviceTypeSchemaEditorMarkup(), {
        ...modalOptions,
    });
    renderDeviceTypeSchemaEditor();
}

function clearTypeSchemaDragVisuals() {
    const dropZone = document.getElementById("type-schema-drop-zone");
    const removeZone = document.getElementById("type-schema-remove-zone");
    if (dropZone instanceof HTMLElement) {
        dropZone.classList.remove("is-drop-target");
    }
    if (removeZone instanceof HTMLElement) {
        removeZone.classList.remove("is-drop-target");
    }
    for (const tile of appModalBody.querySelectorAll(".type-schema-action-tile.dragging")) {
        tile.classList.remove("dragging");
    }
}

function buildDeviceTypesSettingsMarkup(types) {
    state.deviceTypesModalRows = deviceTypesModalRowsFromTypes(types);
    return `
        <section class="modal-section">
            <div class="modal-inline-tools types-tools">
                <label class="modal-inline-search">
                    <span>Recherche</span>
                    <input id="modal-device-types-search" type="search" placeholder="Libelle">
                </label>
                ${createActionButtonMarkup({
                    preset: "add",
                    type: "button",
                    action: "types:add",
                    label: "Ajouter",
                })}
            </div>
            <div class="table-wrap">
                <table class="device-table">
                    <thead id="device-types-head">
                    <tr>
                        <th data-types-col="label">Libelle</th>
                        <th data-types-col="monitoring_enabled">Monitoring</th>
                        <th data-types-col="config_backups_enabled">Configs</th>
                        <th data-types-col="credentials_enabled">Gestion identifiants</th>
                        <th>Actions</th>
                    </tr>
                    </thead>
                    <tbody id="device-types-body"></tbody>
                </table>
            </div>
            <p id="modal-device-types-feedback" class="muted inventory-feedback"></p>
        </section>
    `;
}

async function openDeviceTypesModal() {
    clearTypeSchemaEditorNavigationState();
    const types = await requestJson("/device-types");
    openModal("Types d'equipements", buildDeviceTypesSettingsMarkup(types), {
        width: "min(980px, calc(100vw - 40px))",
        inlineHost: "inventory",
        hideClose: true,
    });
    applyDeviceTypesModalFilterSort();
}

function applyDeviceTypesModalFilterSort() {
    const tree = ensureDeviceTypesTreeView();
    if (tree) {
        tree.render();
        return;
    }
    const tbody = document.getElementById("device-types-body");
    const searchInput = document.getElementById("modal-device-types-search");
    if (!(tbody instanceof HTMLElement)) {
        return;
    }
    const source = Array.isArray(state.deviceTypesModalRows) ? state.deviceTypesModalRows.slice() : [];
    updateSearchVisibility(searchInput instanceof HTMLInputElement ? searchInput : null, source.length, 5);
    const query = normalizeSearchText(searchInput?.value || "");
    const col = String(state.deviceTypesModalSort.column || "label");
    const direction = String(state.deviceTypesModalSort.direction || "asc");
    const rows = source
        .filter((item) => !query || normalizeSearchText(`${String(item?.label || "")} ${String(item?.code || "")}`).includes(query))
        .sort((left, right) => compareDeviceTypesModalRows(col, direction, left, right));
    if (!rows.length) {
        tbody.innerHTML = '<tr><td colspan="5">Aucun type d\'equipement.</td></tr>';
        return;
    }
    tbody.innerHTML = rows.map((item) => {
        const code = String(item?.code || "");
        return `
            <tr data-type-code="${escapeAttribute(code)}">
                <td>${escapeHtml(String(item?.label || code))}</td>
                <td class="cell-center">${item?.monitoring_enabled ? "Oui" : "Non"}</td>
                <td class="cell-center">${item?.config_backups_enabled ? "Oui" : "Non"}</td>
                <td class="cell-center">${item?.credentials_enabled ? "Oui" : "Non"}</td>
                <td class="cell-actions">
                    ${createActionButtonMarkup({
                        preset: "settings",
                        action: "types:edit",
                        title: "Modifier",
                        data: { type_code: code },
                        showLabel: false,
                        label: "",
                    })}
                    ${createActionButtonMarkup({
                        className: "toolbar-btn",
                        type: "button",
                        action: "types:delete",
                        label: "Supprimer",
                        iconHtml: "&#128465;",
                        data: { type_code: code },
                        disabled: !item?.can_delete,
                    })}
                </td>
            </tr>
        `;
    }).join("");
    if (deviceTypesTreeView) {
        deviceTypesTreeView = null;
    }
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
    const hasLoginField = hasField(targetType, "device_login");
    const hasPasswordField = hasField(targetType, "device_password");
    const current = device || {
        name: "",
        ip: "",
        description: "",
        id_Teamviewer: "",
        device_subtype: "",
        action_double_click: "",
        web_url: "",
        ssh_user: "",
        device_login: "",
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
        createDeviceWebUrlFieldMarkup({
            ip: current.ip,
            subtype: current.device_subtype,
            webUrl: current.web_url,
        }),
        createFieldMarkup({ key: "ssh_user", label: fieldLabel("ssh_user"), value: current.ssh_user }),
        ...((hasLoginField || hasPasswordField)
            ? [
                ...(hasLoginField ? [createFieldMarkup({ key: "device_login", label: fieldLabel("device_login"), value: current.device_login || "" })] : []),
                ...(hasPasswordField ? [createDevicePasswordEditFieldMarkup({
                    device: mode === "edit" ? current : null,
                    value: "",
                })] : []),
                ...(hasPasswordField ? ['<p class="muted inventory-password-help wide">Laisser vide pour conserver le mot de passe enregistre.</p>'] : []),
            ]
            : []),
        ...customFields.map((field) => createSchemaDynamicFieldMarkup(
            field,
            current.custom_data?.[field.field_key] || "",
            { keyPrefix: "custom:" },
        )),
    ].join("");
    inventoryNotify.checked = Boolean(current.notify);
    inventoryEditForm.hidden = false;
    inventoryCancelButton.hidden = false;
    inventorySaveButton.textContent = mode === "create" ? "Ajouter" : "Enregistrer";
    inventoryEditForm.dataset.mode = mode;
    inventoryEditForm.dataset.deviceType = mode === "edit" ? String(current.device_type || targetType || "") : "";
    inventoryEditForm.dataset.deviceId = mode === "edit" ? String(current.id || "") : "";
    inventoryEditForm.dataset.versionToken = mode === "edit" ? String(current.version_token || "") : "";
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
        device_login: "",
        notify: true,
        custom_data: {},
        device_type: targetType,
    };
    openModal(mode === "create" ? "Ajouter un equipement" : `Modifier ${current.name}`, buildDeviceFormMarkup(current, mode, targetType));
    const form = document.getElementById("modal-device-form");
    form.dataset.mode = mode;
    form.dataset.deviceType = current.device_type || targetType;
    form.dataset.deviceId = current.id || "";
    form.dataset.initialSubtype = current.device_subtype || "";
    form.dataset.initialAction = current.action_double_click || "";
    form.dataset.initialTeamviewer = current.id_Teamviewer || "";
    form.dataset.initialWebUrl = current.web_url || "";
    form.dataset.initialSshUser = current.ssh_user || "";
    form.dataset.initialDeviceLogin = current.device_login || "";
    form.dataset.initialHasDevicePassword = current.has_device_password ? "1" : "0";
    form.dataset.initialDevicePasswordMasked = current.device_password_masked || "";
    form.dataset.initialCustomData = JSON.stringify(current.custom_data || {});
    form.dataset.versionToken = String(current.version_token || "");
    renderDeviceModalDynamicFields(form);
}

function renderDeviceModalDynamicFields(form) {
    const mode = String(form.dataset.mode || "edit");
    const selectedType = mode === "create"
        ? String(form.querySelector('[name="device_type"]')?.value || "").trim()
        : String(form.dataset.deviceType || "").trim();
    if (!selectedType) {
        return;
    }
    const container = form.querySelector("#modal-device-dynamic-fields");
    if (!(container instanceof HTMLElement)) {
        return;
    }

    const customData = (() => {
        try {
            const fromDataset = JSON.parse(String(form.dataset.initialCustomData || "{}"));
            if (fromDataset && typeof fromDataset === "object") {
                return fromDataset;
            }
        } catch (_error) {
        }
        return {};
    })();

    const subtypeInput = form.querySelector('[name="device_subtype"]');
    const actionInput = form.querySelector('[name="action_double_click"]');
    const ipInput = form.querySelector('[name="ip"]');
    const teamviewerInput = form.querySelector('[name="id_Teamviewer"]');
    const webUrlInput = form.querySelector('[name="web_url"]');
    const sshUserInput = form.querySelector('[name="ssh_user"]');
    const deviceLoginInput = form.querySelector('[name="device_login"]');
    const devicePasswordInput = form.querySelector('[name="device_password"]');
    const passwordDevice = mode === "edit"
        ? {
            device_type: String(form.dataset.deviceType || selectedType || ""),
            id: String(form.dataset.deviceId || ""),
            name: String(form.querySelector('[name="name"]')?.value || ""),
            has_device_password: String(form.dataset.initialHasDevicePassword || "") === "1",
            device_password_masked: String(form.dataset.initialDevicePasswordMasked || ""),
        }
        : null;

    const subtypeValueRaw = String(subtypeInput?.value || form.dataset.initialSubtype || "");
    const subtypeOptions = fieldChoiceOptions(selectedType, "type");
    const hasOsField = hasField(selectedType, "type");
    const subtypeValue = hasOsField
        ? (
            subtypeOptions.find((item) => item.toLowerCase() === subtypeValueRaw.toLowerCase())
            || subtypeValueRaw
            || subtypeOptions[0]
            || PLATFORM_OPTIONS[0]
        )
        : "Autre";

    const actions = actionOptionsForPlatform(selectedType, subtypeValue);
    const actionKeys = actions.map((item) => item.key);
    const selectedAction = (() => {
        const fallback = defaultActionForPlatform(selectedType, subtypeValue);
        const current = actionKeyFromSelection(String(actionInput?.value || form.dataset.initialAction || ""), actionKeys);
        return current || fallback || "";
    })();

    const dynamic = [];
    if (hasField(selectedType, "type")) {
        const options = subtypeOptions.length ? subtypeOptions : PLATFORM_OPTIONS;
        dynamic.push(createSelectMarkup({
            key: "device_subtype",
            label: fieldLabel("type", fieldLabel("device_subtype")),
            value: subtypeValue,
            options: options.map((item) => ({ value: item, label: item })),
        }));
    }
    if (actions.length) {
        dynamic.push(createSelectMarkup({
            key: "action_double_click",
            label: fieldLabel("action_double_click"),
            value: selectedAction,
            options: actions.map((item) => ({ value: item.key, label: item.label || actionLabel(item.key) })),
        }));
    }
    dynamic.push(createRemotePluginsListMarkup({
        actions,
        selectedAction,
        platformLabel: subtypeValue,
    }));

    if (hasField(selectedType, "id_Teamviewer") && actionKeys.includes("teamviewer")) {
        dynamic.push(createFieldMarkup({
            key: "id_Teamviewer",
            label: fieldLabel("id_Teamviewer"),
            value: String(teamviewerInput?.value || form.dataset.initialTeamviewer || ""),
        }));
    }
    if (selectedAction === "web" && hasField(selectedType, "web_url")) {
        dynamic.push(createDeviceWebUrlFieldMarkup({
            ip: String(ipInput?.value || ""),
            subtype: subtypeValue,
            webUrl: String(webUrlInput?.value || form.dataset.initialWebUrl || ""),
            wide: false,
        }));
    }
    if (selectedAction === "ssh" && hasField(selectedType, "ssh_user")) {
        dynamic.push(createFieldMarkup({
            key: "ssh_user",
            label: fieldLabel("ssh_user"),
            value: String(sshUserInput?.value || form.dataset.initialSshUser || ""),
        }));
    }
    const hasLoginField = hasField(selectedType, "device_login");
    const hasPasswordField = hasField(selectedType, "device_password");
    if (hasLoginField) {
        dynamic.push(createFieldMarkup({
            key: "device_login",
            label: fieldLabel("device_login"),
            value: String(deviceLoginInput?.value || form.dataset.initialDeviceLogin || ""),
        }));
    }
    if (hasPasswordField) {
        dynamic.push(createDevicePasswordEditFieldMarkup({
            device: passwordDevice,
            value: String(devicePasswordInput?.value || ""),
        }));
        dynamic.push('<p class="muted inventory-password-help wide">Laisser vide pour conserver le mot de passe enregistre.</p>');
    }

    const customFields = customFieldDefinitions(selectedType);
    dynamic.push(...customFields.map((field) => createSchemaDynamicFieldMarkup(
        field,
        String(customData[field.field_key] || ""),
        { keyPrefix: "custom:" },
    )));

    container.innerHTML = `<div class="modal-grid">${dynamic.join("")}</div>`;
    form.dataset.initialSubtype = String(form.querySelector('[name="device_subtype"]')?.value || subtypeValue || "");
    form.dataset.initialAction = String(form.querySelector('[name="action_double_click"]')?.value || selectedAction || "");
    const renderedWebUrlInput = form.querySelector('[name="web_url"]');
    if (renderedWebUrlInput instanceof HTMLInputElement) {
        form.dataset.initialWebUrl = composeDeviceWebUrlFromParts(
            renderedWebUrlInput.value,
            form.querySelector('[name="web_url_port"]')?.value || "",
            form.querySelector('[name="ip"]')?.value || "",
        );
    }
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
    applyCredentialRevealUnlockDurationFromSettings(settings);
    openModal("Parametres de monitoring", buildMonitoringSettingsMarkup(settings), {
        width: "min(820px, calc(100vw - 40px))",
    });
}

function closeInventoryEditMode() {
    inventoryEditForm.hidden = true;
    inventoryCancelButton.hidden = true;
}

function createMenuButton(label, action, hint = "", disabled = false) {
    const shared = window.NMPSharedMenu;
    if (shared && typeof shared.createMenuButton === "function") {
        return shared.createMenuButton(escapeHtml(label), escapeAttribute(action), escapeHtml(hint), disabled);
    }
    return `
    <button class="context-menu-item" type="button" data-action="${escapeAttribute(action)}" ${disabled ? "disabled" : ""}>
        <span>${escapeHtml(label)}</span>
        <span class="context-menu-hint">${escapeHtml(hint)}</span>
    </button>
    `;
}

function createSubmenu(label, itemsMarkup, disabled = false) {
    const shared = window.NMPSharedMenu;
    if (shared && typeof shared.createSubmenu === "function") {
        return shared.createSubmenu(escapeHtml(label), itemsMarkup, disabled);
    }
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
    const sharedDefs = window.NMPSharedMenu?.commonDefinitions?.() || {};
    const legacyHiddenModuleCodes = new Set(["admin", "users_admin", "imprimantes", "comptes", "interventions"]);
    const moduleRows = (Array.isArray(state.moduleAccess) ? state.moduleAccess : [])
        .filter((row) => Boolean(row?.granted))
        .filter((row) => !legacyHiddenModuleCodes.has(String(row?.code || "").trim().toLowerCase()));
    const hasMonitoring = moduleRows.some((row) => String(row?.code || "").trim().toLowerCase() === "monitoring");
    if (!hasMonitoring) {
        moduleRows.unshift({
            code: "monitoring",
            label: "Monitoring",
            route_path: "/monitoring",
            is_active: true,
            granted: true,
        });
    }
    moduleRows.sort((left, right) => {
        const leftCode = String(left?.code || "").trim().toLowerCase();
        const rightCode = String(right?.code || "").trim().toLowerCase();
        if (leftCode === "monitoring" && rightCode !== "monitoring") {
            return -1;
        }
        if (rightCode === "monitoring" && leftCode !== "monitoring") {
            return 1;
        }
        return String(left?.label || left?.code || "")
            .localeCompare(String(right?.label || right?.code || ""), undefined, { sensitivity: "base" });
    });
    const moduleEntries = moduleRows.map((row) => {
        const routePath = String(row?.route_path || "").trim();
        const isAvailable = Boolean(row?.granted && row?.is_active && routePath);
        return {
            label: String(row?.label || row?.code || "Module"),
            action: routePath ? `menu:modules:open:${encodeURIComponent(routePath)}` : "menu:modules:open:",
            disabled: !isAvailable,
        };
    });
    moduleEntries.unshift({
        label: "Portail",
        action: "menu:portal",
        disabled: false,
    });
    const typeLogs = (state.deviceTypes || [])
        .filter((item) => Boolean(item.monitoring_enabled))
        .map((item) => ({
            label: `Journal ${item.label}...`,
            action: `menu:logs:type:${item.code}`,
        }));
    const configState = state.configStorageState || {};
    const configStorageMode = String(configState.mode || "local").trim().toLowerCase();
    const canUseRemoteBackup = configStorageMode === "smb3" && Boolean(configState.can_open_backup_folder);
    return {
        modules: moduleEntries,
        supervision: [
            { label: "Parametres de monitoring...", action: "menu:monitoring" },
            { label: "Notification...", action: "menu:monitoring-notifications" },
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
            { label: "Gestion des equipements", action: "view:inventory" },
            { label: "Types d'equipements...", action: "view:device-types" },
            {
                label: "Fichiers de configuration",
                items: [
                    { label: "Gerer les fichiers de configuration", action: "menu:config-open-local" },
                    ...(configStorageMode === "smb3"
                        ? [{ label: "Ouvrir dossier de sauvegarde", action: "menu:config-open-backup", disabled: !canUseRemoteBackup }]
                        : []),
                    { label: "Configurer sauvegarde...", action: "menu:config-storage" },
                    ...(configStorageMode === "smb3"
                        ? [{ label: "Sauvegarder maintenant", action: "menu:config-sync", disabled: !canUseRemoteBackup }]
                        : []),
                ],
            },
        ],
        tools: [
            { label: "Scan reseau...", action: "menu:scan" },
        ],
        help: [...(sharedDefs.help || [])],
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
    const shared = window.NMPSharedMenu;
    if (shared && typeof shared.renderTopMenuGroup === "function") {
        return shared.renderTopMenuGroup(entries);
    }
    return `<div class="context-menu-group">${entries.map((entry) => renderTopMenuEntry(entry)).join("")}</div>`;
}

function refreshEquipmentsTopMenuIfOpen() {
    loadConfigStorageState()
        .then(() => {
            if (state.openTopMenu === "equipments" && !topMenuPanel.hidden) {
                topMenuPanel.innerHTML = topMenuMarkup("equipments");
            }
        })
        .catch(() => {
        });
}

async function openTopMenu(button, menuKey) {
    closeProfileMenu();
    if (topMenuController) {
        topMenuController.open(button, menuKey, {
            buildMarkup: topMenuMarkup,
            onBeforeOpen: () => closeContextMenu(),
            onAfterOpen: (openedKey) => {
                if (openedKey === "equipments") {
                    refreshEquipmentsTopMenuIfOpen();
                }
            },
        });
        return;
    }
    const sharedOpenTopMenu = window.NMPSharedUi?.openTopMenu;
    if (typeof sharedOpenTopMenu === "function") {
        sharedOpenTopMenu({
            state,
            panel: topMenuPanel,
            buttons: [menuModules, menuSupervision, menuEquipments, menuTools, menuHelp],
            button,
            menuKey,
            buildMarkup: topMenuMarkup,
            onBeforeOpen: () => closeContextMenu(),
            onAfterOpen: (openedKey) => {
                if (openedKey === "equipments") {
                    refreshEquipmentsTopMenuIfOpen();
                }
            },
        });
        return;
    }
    if (state.openTopMenu === menuKey && !topMenuPanel.hidden) {
        closeTopMenu();
        return;
    }
    closeContextMenu();
    state.openTopMenu = menuKey;
    topMenuPanel.innerHTML = topMenuMarkup(menuKey);
    topMenuPanel.hidden = false;
    [menuModules, menuSupervision, menuEquipments, menuTools, menuHelp].forEach((entry) => {
        entry.classList.toggle("active", entry === button);
    });
    const rect = button.getBoundingClientRect();
    topMenuPanel.style.left = `${Math.max(8, rect.left)}px`;
    topMenuPanel.style.top = `${rect.bottom + 4}px`;
    if (menuKey === "equipments") {
        refreshEquipmentsTopMenuIfOpen();
    }
}

async function buildContextMenuMarkup(device) {
    const schema = await ensureDeviceTypeSchema(device.device_type);
    const configEnabled = Boolean(typeMeta(device.device_type)?.config_backups_enabled);
    const remoteRows = schemaRemoteActionsForDevice(schema, device);
    const currentDefault = String(device?.action_double_click || "").trim().toLowerCase();
    const dynamicActions = remoteRows
        .map((item) => {
            const actionKey = String(item.action_key || "").trim().toLowerCase();
            const label = String(item.label || actionLabel(actionKey)).trim() || actionLabel(actionKey);
            const isDefault = currentDefault === actionKey || currentDefault === String(item.target_value || "").trim().toLowerCase();
            const status = remoteActionWebStatus(device, item);
            const disabled = !status.ok;
            const hint = isDefault ? "Defaut" : "";
            return createMenuButton(
                label,
                `remote:${encodeURIComponent(actionKey)}`,
                hint,
                disabled,
            );
        })
        .join("");
    const openMenu = createSubmenu(
        "Prise en main a distance",
        dynamicActions || `<div class="muted">Aucune action disponible</div>`,
        !dynamicActions,
    );

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
            createMenuButton("Ping", "tool:ping"),
            createMenuButton("Port check", "tool:port"),
            createMenuButton("Traceroute", "tool:traceroute"),
            createMenuButton("DNS lookup", "tool:dns"),
            createMenuButton("HTTP(S) check (avec certificat)", "tool:http"),
            createMenuButton("SNMP", "tool:snmp"),
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

    const notifyActionLabel = device.notify
        ? "Desactiver les alertes changement"
        : "Activer les alertes changement";

    return `
        <div class="context-menu-group">
            ${openMenu}
        </div>
        <div class="context-menu-group">
            ${createMenuButton("Ajouter", "device:add")}
            ${createMenuButton("Modifier", "device:edit")}
            ${createMenuButton("Supprimer", "device:delete")}
        </div>
        <div class="context-menu-group">
            ${createMenuButton(notifyActionLabel, "device:notify")}
            ${createMenuButton("Afficher logs", "device:logs")}
            ${copyMenu}
        </div>
        <div class="context-menu-group">
            ${configMenu}
            ${toolsMenu}
        </div>
    `;
}

function buildBooleanStateMenuButtons(rows, options = {}) {
    const safeRows = Array.isArray(rows) ? rows : [];
    const key = String(options.key || "").trim();
    const actionPrefix = String(options.actionPrefix || "").trim();
    const enableLabel = String(options.enableLabel || "Activer").trim();
    const disableLabel = String(options.disableLabel || "Desactiver").trim();
    if (!key || !actionPrefix) {
        return "";
    }
    if (!safeRows.length) {
        return [
            createMenuButton(enableLabel, `${actionPrefix}-on`, "", true),
            createMenuButton(disableLabel, `${actionPrefix}-off`, "", true),
        ].join("");
    }
    const enabledCount = safeRows.filter((item) => Boolean(item?.[key])).length;
    const disabledCount = safeRows.length - enabledCount;
    if (enabledCount === safeRows.length) {
        return createMenuButton(disableLabel, `${actionPrefix}-off`);
    }
    if (disabledCount === safeRows.length) {
        return createMenuButton(enableLabel, `${actionPrefix}-on`);
    }
    return [
        createMenuButton(enableLabel, `${actionPrefix}-on`),
        createMenuButton(disableLabel, `${actionPrefix}-off`),
    ].join("");
}

async function openContextMenu(x, y, device) {
    state.contextMenuDeviceKey = deviceKey(device);
    state.contextMenuTypeCode = "";
    state.deviceBatchContextRows = [];
    state.deviceTypeBatchContextRows = [];
    contextMenu.innerHTML = await buildContextMenuMarkup(device);
    contextMenu.hidden = false;
    const maxX = window.innerWidth - contextMenu.offsetWidth - 12;
    const maxY = window.innerHeight - contextMenu.offsetHeight - 12;
    contextMenu.style.left = `${Math.max(8, Math.min(x, maxX))}px`;
    contextMenu.style.top = `${Math.max(8, Math.min(y, maxY))}px`;
}

function buildDeviceBatchContextMenuMarkup(rows) {
    const count = Array.isArray(rows) ? rows.length : 0;
    const countLabel = `${count} equipement${count > 1 ? "s" : ""} selectionne${count > 1 ? "s" : ""}`;
    return `
        <div class="context-menu-group">
            <div class="context-menu-title">${escapeHtml(countLabel)}</div>
            ${buildBooleanStateMenuButtons(rows, {
                key: "notify",
                actionPrefix: "device:batch-notify",
                enableLabel: "Activer les alertes changement",
                disableLabel: "Desactiver les alertes changement",
            })}
        </div>
        <div class="context-menu-group">
            ${createMenuButton("Supprimer la selection", "device:batch-delete", "", count <= 0)}
        </div>
    `;
}

function openDeviceBatchContextMenu(x, y, rows = selectedDeviceRows()) {
    const selectedRows = Array.isArray(rows) ? rows : [];
    if (!selectedRows.length) {
        return false;
    }
    state.contextMenuDeviceKey = "";
    state.contextMenuTypeCode = "";
    state.deviceBatchContextRows = selectedRows;
    contextMenu.innerHTML = buildDeviceBatchContextMenuMarkup(selectedRows);
    contextMenu.hidden = false;
    const maxX = window.innerWidth - contextMenu.offsetWidth - 12;
    const maxY = window.innerHeight - contextMenu.offsetHeight - 12;
    contextMenu.style.left = `${Math.max(8, Math.min(x, maxX))}px`;
    contextMenu.style.top = `${Math.max(8, Math.min(y, maxY))}px`;
    return true;
}

function openInventoryBatchContextMenu(x, y, rows = selectedInventoryRows()) {
    return openDeviceBatchContextMenu(x, y, rows);
}

function isTreeBodyContextTarget(event) {
    const target = event?.target;
    if (!(target instanceof Element)) {
        return false;
    }
    if (target.closest("thead")) {
        return false;
    }
    return Boolean(target.closest("tbody") || target.closest(".shared-treeview-wrap"));
}

function openSelectedDeviceContextMenuFromTreeBody(event) {
    if (!isTreeBodyContextTarget(event)) {
        return false;
    }
    const selected = getSelectedDeviceFromInventoryStore() || getSelectedDevice();
    if (!selected) {
        return false;
    }
    closeTopMenu();
    openContextMenu(event.clientX, event.clientY, selected).catch((error) => {
        inventoryFeedback.textContent = normalizeErrorMessage(error.message);
    });
    return true;
}

function buildDeviceTreeBackgroundContextMenuMarkup(preferredTypeCode = "") {
    const preferredType = String(preferredTypeCode || "").trim()
        || String(state.deviceTypes?.[0]?.code || "").trim();
    const canCreate = Boolean(preferredType);
    const addAction = canCreate ? `device:add-type:${preferredType}` : "device:add";
    return `
        <div class="context-menu-group">
            ${createMenuButton("Ajouter", addAction, canCreate ? typeLabel(preferredType) : "", !canCreate)}
        </div>
    `;
}

function buildInventoryBackgroundContextMenuMarkup() {
    return buildDeviceTreeBackgroundContextMenuMarkup(String(inventoryTypeFilter.value || "").trim());
}

function positionContextMenu(x, y) {
    contextMenu.hidden = false;
    const maxX = window.innerWidth - contextMenu.offsetWidth - 12;
    const maxY = window.innerHeight - contextMenu.offsetHeight - 12;
    contextMenu.style.left = `${Math.max(8, Math.min(x, maxX))}px`;
    contextMenu.style.top = `${Math.max(8, Math.min(y, maxY))}px`;
}

function openInventoryBackgroundContextMenu(x, y) {
    state.contextMenuDeviceKey = "";
    state.contextMenuTypeCode = "";
    state.deviceBatchContextRows = [];
    state.deviceTypeBatchContextRows = [];
    contextMenu.innerHTML = buildInventoryBackgroundContextMenuMarkup();
    positionContextMenu(x, y);
}

function openSupervisionBackgroundContextMenu(x, y) {
    if (openDeviceBatchContextMenu(x, y, selectedSupervisionRows())) {
        return;
    }
    const filterType = currentMonitoringTreeFilters().typeCode;
    const preferredType = filterType && filterType !== "global" ? filterType : "";
    state.contextMenuDeviceKey = "";
    state.contextMenuTypeCode = "";
    state.deviceBatchContextRows = [];
    state.deviceTypeBatchContextRows = [];
    contextMenu.innerHTML = buildDeviceTreeBackgroundContextMenuMarkup(preferredType);
    positionContextMenu(x, y);
}

function buildDeviceTypeContextMenuMarkup(typeCode) {
    const normalizedType = String(typeCode || "").trim();
    const meta = typeMeta(normalizedType);
    const row = (state.deviceTypesModalRows || []).find((item) => String(item?.code || "").trim() === normalizedType);
    const typeRow = row || meta || {};
    const canDelete = row ? Boolean(row.can_delete) : !Boolean(meta?.is_system);
    return `
        <div class="context-menu-group">
            ${createMenuButton("Voir", "type:view", typeLabel(normalizedType))}
        </div>
        <div class="context-menu-group">
            ${buildBooleanStateMenuButtons([typeRow], {
                key: "monitoring_enabled",
                actionPrefix: "type:monitoring",
                enableLabel: "Activer le monitoring",
                disableLabel: "Desactiver le monitoring",
            })}
            ${buildBooleanStateMenuButtons([typeRow], {
                key: "config_backups_enabled",
                actionPrefix: "type:config",
                enableLabel: "Activer la gestion de la configuration",
                disableLabel: "Desactiver la gestion de la configuration",
            })}
            ${buildBooleanStateMenuButtons([typeRow], {
                key: "credentials_enabled",
                actionPrefix: "type:credentials",
                enableLabel: "Activer la gestion des identifiants",
                disableLabel: "Desactiver la gestion des identifiants",
            })}
        </div>
        <div class="context-menu-group">
            ${createMenuButton("Modifier", "type:edit")}
            ${createMenuButton("Supprimer", "type:delete", "", !canDelete)}
        </div>
    `;
}

function buildDeviceTypeBatchContextMenuMarkup(rows) {
    const safeRows = Array.isArray(rows) ? rows : [];
    const deletableCount = safeRows.filter((item) => Boolean(item?.can_delete)).length;
    const count = safeRows.length;
    const countLabel = `${count} type${count > 1 ? "s" : ""} selectionne${count > 1 ? "s" : ""}`;
    return `
        <div class="context-menu-group">
            <div class="context-menu-title">${escapeHtml(countLabel)}</div>
            ${buildBooleanStateMenuButtons(safeRows, {
                key: "monitoring_enabled",
                actionPrefix: "type:batch-monitoring",
                enableLabel: "Activer le monitoring",
                disableLabel: "Desactiver le monitoring",
            })}
            ${buildBooleanStateMenuButtons(safeRows, {
                key: "config_backups_enabled",
                actionPrefix: "type:batch-config",
                enableLabel: "Activer la gestion de la configuration",
                disableLabel: "Desactiver la gestion de la configuration",
            })}
            ${buildBooleanStateMenuButtons(safeRows, {
                key: "credentials_enabled",
                actionPrefix: "type:batch-credentials",
                enableLabel: "Activer la gestion des identifiants",
                disableLabel: "Desactiver la gestion des identifiants",
            })}
        </div>
        <div class="context-menu-group">
            ${createMenuButton("Supprimer la selection", "type:batch-delete", "", deletableCount <= 0)}
        </div>
    `;
}

function openDeviceTypeBatchContextMenu(x, y, rows = selectedDeviceTypeRows()) {
    const selectedRows = Array.isArray(rows) ? rows : [];
    if (!selectedRows.length) {
        return false;
    }
    state.contextMenuDeviceKey = "";
    state.contextMenuTypeCode = "";
    state.deviceTypeBatchContextRows = selectedRows;
    contextMenu.innerHTML = buildDeviceTypeBatchContextMenuMarkup(selectedRows);
    contextMenu.hidden = false;
    const maxX = window.innerWidth - contextMenu.offsetWidth - 12;
    const maxY = window.innerHeight - contextMenu.offsetHeight - 12;
    contextMenu.style.left = `${Math.max(8, Math.min(x, maxX))}px`;
    contextMenu.style.top = `${Math.max(8, Math.min(y, maxY))}px`;
    return true;
}

function openDeviceTypesBackgroundContextMenu(x, y) {
    if (openDeviceTypeBatchContextMenu(x, y, selectedDeviceTypeRows())) {
        return;
    }
    state.contextMenuDeviceKey = "";
    state.contextMenuTypeCode = "";
    state.deviceBatchContextRows = [];
    state.deviceTypeBatchContextRows = [];
    contextMenu.innerHTML = `
        <div class="context-menu-group">
            ${createMenuButton("Ajouter un type", "types:add")}
        </div>
    `;
    positionContextMenu(x, y);
}

function openDeviceTypeContextMenu(x, y, typeCode) {
    const normalizedType = String(typeCode || "").trim();
    if (!normalizedType) {
        return;
    }
    state.contextMenuDeviceKey = "";
    state.contextMenuTypeCode = normalizedType;
    state.deviceBatchContextRows = [];
    state.deviceTypeBatchContextRows = [];
    contextMenu.innerHTML = buildDeviceTypeContextMenuMarkup(normalizedType);
    contextMenu.hidden = false;
    const maxX = window.innerWidth - contextMenu.offsetWidth - 12;
    const maxY = window.innerHeight - contextMenu.offsetHeight - 12;
    contextMenu.style.left = `${Math.max(8, Math.min(x, maxX))}px`;
    contextMenu.style.top = `${Math.max(8, Math.min(y, maxY))}px`;
}

async function viewDeviceTypeInventory(typeCode) {
    const normalizedType = String(typeCode || "").trim();
    if (!normalizedType) {
        return;
    }
    closeModal();
    state.currentSection = "inventory";
    closeInventoryEditMode();
    renderSection();
    if (inventoryTypeFilter instanceof HTMLSelectElement) {
        inventoryTypeFilter.value = normalizedType;
    }
    try {
        await ensureDeviceTypeSchema(normalizedType);
    } catch (error) {
        inventoryFeedback.textContent = normalizeErrorMessage(error.message);
    }
    ensureSelectedDevice();
    renderInventoryDetail();
    const selected = getSelectedDevice();
    if (selected) {
        await ensureInventorySideData(selected);
    }
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
    await setDeviceNotify(device, !device.notify);
    await loadInventory();
    renderInventoryDetail();
}

async function setDeviceNotify(device, enabled) {
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
            device_login: device.device_login || "",
            custom_data: device.custom_data || {},
            notify: Boolean(enabled),
            version_token: String(device.version_token || ""),
        }),
    });
}

async function deleteDeviceRequest(device) {
    const deletePath = String(device.version_token || "").trim()
        ? `/devices/${encodeURIComponent(device.device_type)}/${encodeURIComponent(device.id)}?version_token=${encodeURIComponent(String(device.version_token || ""))}`
        : `/devices/${encodeURIComponent(device.device_type)}/${encodeURIComponent(device.id)}`;
    await requestJson(deletePath, {
        method: "DELETE",
    });
}

async function deleteDevice(device) {
    const confirmed = window.confirm(`Supprimer ${typeLabel(device.device_type)} "${device.name}" ?`);
    if (!confirmed) {
        return;
    }
    await deleteDeviceRequest(device);
    await loadInventory();
    renderInventoryDetail();
}

async function deleteSelectedInventoryDevices() {
    const rows = activeDeviceBatchRows();
    if (!rows.length) {
        inventoryFeedback.textContent = "Aucun equipement selectionne.";
        return;
    }
    const confirmed = window.confirm(`Supprimer ${rows.length} equipement(s) selectionne(s) ?`);
    if (!confirmed) {
        return;
    }
    for (const device of rows) {
        await deleteDeviceRequest(device);
    }
    clearDeviceBatchSelection();
    await loadInventory();
    renderInventoryDetail();
    inventoryFeedback.textContent = `${rows.length} equipement(s) supprime(s).`;
}

async function setSelectedInventoryNotify(enabled) {
    const rows = activeDeviceBatchRows();
    if (!rows.length) {
        inventoryFeedback.textContent = "Aucun equipement selectionne.";
        return;
    }
    for (const device of rows) {
        await setDeviceNotify(device, enabled);
    }
    clearDeviceBatchSelection();
    await loadInventory();
    renderInventoryDetail();
    inventoryFeedback.textContent = `Alertes changement ${enabled ? "activees" : "desactivees"} pour ${rows.length} equipement(s).`;
}

function normalizeCustomDataMap(raw) {
    if (!raw || typeof raw !== "object") {
        return {};
    }
    const out = {};
    for (const [key, value] of Object.entries(raw)) {
        const normalizedKey = String(key || "").trim();
        if (!normalizedKey) {
            continue;
        }
        out[normalizedKey] = String(value ?? "");
    }
    return out;
}

function mergeCustomDataMaps(base, updates) {
    return {
        ...normalizeCustomDataMap(base),
        ...normalizeCustomDataMap(updates),
    };
}

function findInventoryDevice(deviceType, deviceId) {
    const normalizedType = String(deviceType || "").trim().toLowerCase();
    const normalizedId = String(deviceId || "").trim();
    if (!normalizedType || !normalizedId) {
        return null;
    }
    return (state.inventory || []).find((row) => (
        String(row?.device_type || "").trim().toLowerCase() === normalizedType
        && String(row?.id || "").trim() === normalizedId
    )) || null;
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
    const payload = {
        name: String(formData.get("name") || "").trim(),
        ip: String(formData.get("ip") || "").trim(),
        description: String(formData.get("description") || "").trim(),
        id_Teamviewer: String(formData.get("id_Teamviewer") || "").trim(),
        device_subtype: String(formData.get("device_subtype") || "").trim(),
        action_double_click: String(formData.get("action_double_click") || "").trim(),
        web_url: composeDeviceWebUrlFromParts(
            formData.get("web_url"),
            formData.get("web_url_port"),
            formData.get("ip"),
        ),
        ssh_user: String(formData.get("ssh_user") || "").trim(),
        custom_data: customData,
        notify: form.querySelector('[name="notify"]')?.checked ?? true,
        version_token: String(form.dataset.versionToken || ""),
    };
    if (form.querySelector('[name="device_login"]')) {
        payload.device_login = String(formData.get("device_login") || "").trim();
    }
    if (form.querySelector('[name="device_password"]')) {
        payload.device_password = String(formData.get("device_password") ?? "");
    }
    return {
        device_type: deviceType,
        payload,
    };
}

async function submitDeviceModal(form) {
    const mode = form.dataset.mode || "edit";
    const { device_type: createdType, payload } = serializeDeviceForm(form);
    const feedback = document.getElementById("modal-device-feedback");
    feedback.textContent = "Enregistrement...";
    const deviceId = String(form.dataset.deviceId || "");
    const editType = String(form.dataset.deviceType || "");
    if (mode !== "create") {
        const existing = findInventoryDevice(editType, deviceId);
        if (existing) {
            payload.custom_data = mergeCustomDataMaps(existing.custom_data, payload.custom_data);
            payload.version_token = String(existing.version_token || payload.version_token || "");
        }
        if (Object.prototype.hasOwnProperty.call(payload, "device_password") && payload.device_password === "") {
            delete payload.device_password;
        }
    }
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
        credential_reveal_unlock_seconds: normalizeCredentialRevealUnlockSeconds(
            formData.get("credential_reveal_unlock_seconds") || current.credential_reveal_unlock_seconds,
        ),
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
        applyCredentialRevealUnlockDurationFromSettings(payload);
        if (!isCredentialRevealSessionUnlocked()) {
            clearCredentialRevealState({ refresh: true });
        }
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
        device_id: String(device.id || ""),
        device_name: String(device.name || ""),
        device_ip: String(device.ip || ""),
    });
    const sharedDownload = window.NMPSharedDownload?.downloadBinary;
    if (typeof sharedDownload === "function") {
        await sharedDownload({
            url: `/config-files/latest-download?${params.toString()}`,
            method: "GET",
            headers: {
                ...headers(),
            },
            defaultFilename: "config.cfg",
            normalizeErrorMessage,
        });
        return;
    }
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

async function downloadHttpsRootCertificate() {
    const sharedDownload = window.NMPSharedDownload?.downloadBinary;
    if (typeof sharedDownload === "function") {
        await sharedDownload({
            url: "/ui/https-root-certificate/download",
            method: "GET",
            headers: {
                ...headers(),
            },
            defaultFilename: "monitoring-mvl-root.crt",
            normalizeErrorMessage,
        });
        return;
    }
    const response = await fetch("/ui/https-root-certificate/download", {
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
    const filename = (match && match[1]) ? match[1] : "monitoring-mvl-root.crt";
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
            device_id: String(device.id || ""),
            device_name: String(device.name || ""),
            device_ip: String(device.ip || ""),
            filename: String(file.name || "import.cfg"),
            content_base64: String(contentBase64 || ""),
            detail: "Import web",
        }),
    });
    inventoryFeedback.textContent = "Fichier de configuration importe.";
    await loadInventory();
    await loadInventoryConfigs(device);
    renderInventoryDetail();
}

async function pickDeviceInventoryImportFile() {
    const sharedImport = window.NMPSharedImport;
    if (sharedImport && typeof sharedImport.pickFile === "function") {
        return sharedImport.pickFile({ accept: ".xlsx,.csv,.txt,.tsv" });
    }
    const picker = document.createElement("input");
    picker.type = "file";
    picker.accept = ".xlsx,.csv,.txt,.tsv";
    return new Promise((resolve) => {
        picker.addEventListener("change", () => resolve(picker.files && picker.files[0] ? picker.files[0] : null), { once: true });
        picker.click();
    });
}

const DEVICE_IMPORT_TARGET_FIELDS = [
    { value: "__auto__", label: "Auto" },
    { value: "__ignore__", label: "Ignorer" },
    { value: "device_type", label: "Type equipement" },
    { value: "name", label: "Nom" },
    { value: "ip", label: "IP" },
    { value: "description", label: "Description" },
    { value: "id_Teamviewer", label: "TeamViewer ID" },
    { value: "device_subtype", label: "Sous-type / OS" },
    { value: "action_double_click", label: "Action double-clic" },
    { value: "web_url", label: "URL Web" },
    { value: "ssh_user", label: "Utilisateur SSH" },
    { value: "device_login", label: "Login" },
    { value: "device_password", label: "Mot de passe" },
    { value: "notify", label: "Alertes changement" },
    { value: "custom", label: "Champ personnalise" },
];
const DEVICE_IMPORT_CREDENTIAL_MODES = [
    { value: "preserve_on_blank", label: "Conserver si vide (recommande)" },
    { value: "overwrite", label: "Ecraser avec le fichier" },
    { value: "ignore", label: "Ignorer les identifiants du fichier" },
];
const DEVICE_IMPORT_HEADER_MODES = [
    { value: "auto", label: "Auto-detection" },
    { value: "manual", label: "Ligne manuelle" },
    { value: "first", label: "Premiere ligne" },
];

function setInventoryImportProgress(value, label, visible = true) {
    const wrap = document.getElementById("inventory-import-progress-wrap");
    const bar = document.getElementById("inventory-import-progress");
    const status = document.getElementById("inventory-import-progress-status");
    if (wrap instanceof HTMLElement) {
        wrap.hidden = !visible;
    }
    if (bar instanceof HTMLProgressElement) {
        bar.value = Math.max(0, Math.min(100, Number(value || 0)));
    }
    if (status instanceof HTMLElement) {
        status.textContent = String(label || "");
    }
}

function _normalizeDeviceImportMappingRows(rows = []) {
    return (Array.isArray(rows) ? rows : [])
        .map((row) => ({
            source_column: String(row?.source_column || "").trim(),
            target_field: String(row?.target_field || "__auto__").trim() || "__auto__",
            custom_key: String(row?.custom_key || "").trim(),
        }))
        .filter((row) => row.source_column);
}

function normalizeImportCredentialMode(value) {
    const raw = String(value || "").trim().toLowerCase();
    if (raw === "overwrite" || raw === "ignore" || raw === "preserve_on_blank") {
        return raw;
    }
    return "preserve_on_blank";
}

function normalizeImportHeaderMode(value) {
    const raw = String(value || "").trim().toLowerCase();
    if (raw === "auto" || raw === "manual" || raw === "first") {
        return raw;
    }
    return "auto";
}

function normalizeImportHeaderRowNumber(value) {
    const parsed = Number(value || 1);
    if (!Number.isFinite(parsed)) {
        return 1;
    }
    return Math.max(1, Math.trunc(parsed));
}

function _collectDeviceImportMappingsFromForm(form) {
    const tableRows = Array.from(form.querySelectorAll("tr[data-source-column]"));
    return tableRows.map((row) => {
        const sourceColumn = String(row.getAttribute("data-source-column") || "").trim();
        const selector = row.querySelector('select[name="device_import_target"]');
        const customInput = row.querySelector('input[name="device_import_custom"]');
        return {
            source_column: sourceColumn,
            target_field: String(selector?.value || "__auto__").trim() || "__auto__",
            custom_key: String(customInput?.value || "").trim(),
        };
    }).filter((row) => row.source_column);
}

function _collectDeviceImportCredentialModeFromForm(form) {
    const selector = form.querySelector('select[name="device_import_credential_mode"]');
    return normalizeImportCredentialMode(selector?.value || state.deviceImportDraft?.credentialMode);
}

function _collectDeviceImportSheetNameFromForm(form) {
    const selector = form.querySelector('select[name="device_import_sheet"]');
    const selected = String(selector?.value || state.deviceImportDraft?.selectedSheetName || "").trim();
    return selected;
}

function _collectDeviceImportHeaderModeFromForm(form) {
    const selector = form.querySelector('select[name="device_import_header_mode"]');
    return normalizeImportHeaderMode(selector?.value || state.deviceImportDraft?.headerMode);
}

function _collectDeviceImportHeaderRowFromForm(form) {
    const input = form.querySelector('input[name="device_import_header_row"]');
    return normalizeImportHeaderRowNumber(input?.value || state.deviceImportDraft?.headerRowNumber);
}

function _buildDeviceImportSourceTable(headers = [], rows = []) {
    const normalizedHeaders = Array.isArray(headers) ? headers : [];
    const normalizedRows = Array.isArray(rows) ? rows : [];
    if (!normalizedRows.length) {
        return '<div class="muted">Aucune colonne detectee.</div>';
    }
    const maxColumns = Math.max(
        normalizedHeaders.length,
        ...normalizedRows.map((row) => (Array.isArray(row) ? row.length : 0)),
        0,
    );
    const resolvedHeaders = maxColumns
        ? Array.from({ length: maxColumns }, (_value, index) => String(normalizedHeaders[index] || `Colonne ${index + 1}`))
        : [];
    const headCells = resolvedHeaders.map((header) => `<th>${escapeHtml(header)}</th>`).join("");
    const bodyRows = normalizedRows.length
        ? normalizedRows.map((row, index) => {
            const cells = resolvedHeaders.map((_header, columnIndex) => `<td>${escapeHtml(String(row?.[columnIndex] || ""))}</td>`).join("");
            return `<tr><td class="muted">${index + 1}</td>${cells}</tr>`;
        }).join("")
        : `<tr><td colspan="${resolvedHeaders.length + 1}" class="muted">Aucune ligne de previsualisation.</td></tr>`;
    return `
        <div class="inventory-table-wrap">
            <table class="inventory-table">
                <thead><tr><th>#</th>${headCells}</tr></thead>
                <tbody>${bodyRows}</tbody>
            </table>
        </div>
    `;
}

function _buildDeviceImportMappingRows(headers = [], effectiveMapping = [], draftMapping = []) {
    const effectiveBySource = new Map(
        _normalizeDeviceImportMappingRows(effectiveMapping).map((row) => [row.source_column, row]),
    );
    const draftBySource = new Map(
        _normalizeDeviceImportMappingRows(draftMapping).map((row) => [row.source_column, row]),
    );
    return (Array.isArray(headers) ? headers : []).map((sourceHeader) => {
        const sourceColumn = String(sourceHeader || "");
        const mapped = draftBySource.get(sourceColumn) || effectiveBySource.get(sourceColumn) || {
            source_column: sourceColumn,
            target_field: "__auto__",
            custom_key: "",
        };
        const selectedTarget = String(mapped.target_field || "__auto__");
        const selectedCustom = String(mapped.custom_key || "");
        const options = DEVICE_IMPORT_TARGET_FIELDS
            .map((option) => `<option value="${escapeAttribute(option.value)}" ${selectedTarget === option.value ? "selected" : ""}>${escapeHtml(option.label)}</option>`)
            .join("");
        return `
            <tr data-source-column="${escapeAttribute(sourceColumn)}">
                <td>${escapeHtml(sourceColumn)}</td>
                <td>
                    <select name="device_import_target">
                        ${options}
                    </select>
                </td>
                <td>
                    <input
                        name="device_import_custom"
                        value="${escapeAttribute(selectedCustom)}"
                        placeholder="Ex: site"
                        ${selectedTarget === "custom" ? "" : "disabled"}
                        style="${selectedTarget === "custom" ? "" : "display:none;"}"
                    >
                </td>
            </tr>
        `;
    }).join("");
}

function isInventoryWorkspaceSection(sectionCode = "") {
    const code = String(sectionCode || "").trim().toLowerCase();
    return code === "inventory" || code === "device_types";
}

function hasInlineDeviceTypesView() {
    if (state.activeInlineModalHost !== "inventory" || !(appModal instanceof HTMLElement) || appModal.hidden) {
        return false;
    }
    return appModalBody instanceof HTMLElement && Boolean(appModalBody.querySelector("#device-types-body"));
}

function ensureDeviceTypesPageOpened() {
    if (hasInlineDeviceTypesView()) {
        applyDeviceTypesModalFilterSort();
        return;
    }
    if (state.deviceTypesPageOpening) {
        return;
    }
    state.deviceTypesPageOpening = true;
    openDeviceTypesModal()
        .catch((error) => {
            inventoryFeedback.textContent = normalizeErrorMessage(error.message);
        })
        .finally(() => {
            state.deviceTypesPageOpening = false;
        });
}

function _buildDeviceImportMappedPreview(rows = []) {
    const normalizedRows = Array.isArray(rows) ? rows : [];
    const previewRows = normalizedRows.slice(0, 12);
    const body = previewRows.length
        ? previewRows.map((row) => `
            <tr>
                <td>${escapeHtml(String(row?.device_type || ""))}</td>
                <td>${escapeHtml(String(row?.name || ""))}</td>
                <td>${escapeHtml(String(row?.ip || ""))}</td>
                <td>${escapeHtml(String(row?.description || ""))}</td>
                <td>${escapeHtml(String(row?.device_login || ""))}</td>
                <td>${escapeHtml(String(row?.device_password ? "••••" : ""))}</td>
            </tr>
        `).join("")
        : '<tr><td colspan="6" class="muted">Aucune ligne exploitable avec ce mapping.</td></tr>';
    return `
        <div class="inventory-table-wrap">
            <table class="inventory-table">
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Nom</th>
                        <th>IP</th>
                        <th>Description</th>
                        <th>Login</th>
                        <th>Mot de passe</th>
                    </tr>
                </thead>
                <tbody>${body}</tbody>
            </table>
        </div>
    `;
}

function buildDeviceImportWizardMarkup(draft) {
    const sourceHeaders = Array.isArray(draft?.preview?.sourceHeaders) ? draft.preview.sourceHeaders : [];
    const sourceRowsPreview = Array.isArray(draft?.preview?.sourceRowsPreview) ? draft.preview.sourceRowsPreview : [];
    const mappedRows = Array.isArray(draft?.preview?.rows) ? draft.preview.rows : [];
    const availableSheets = Array.isArray(draft?.preview?.availableSheets) ? draft.preview.availableSheets : [];
    const selectedSheetName = String(draft?.preview?.selectedSheetName || draft?.selectedSheetName || "").trim();
    const credentialMode = normalizeImportCredentialMode(draft?.credentialMode);
    const headerMode = normalizeImportHeaderMode(draft?.headerMode || draft?.preview?.effectiveHeaderMode || "auto");
    const headerRowNumber = normalizeImportHeaderRowNumber(draft?.headerRowNumber || draft?.preview?.detectedHeaderRowNumber || 1);
    const detectedHeaderRowNumber = normalizeImportHeaderRowNumber(draft?.preview?.detectedHeaderRowNumber || headerRowNumber);
    const effectiveHeaderMode = normalizeImportHeaderMode(draft?.preview?.effectiveHeaderMode || headerMode);
    const issues = Array.isArray(draft?.preview?.issues) ? draft.preview.issues : [];
    const issueText = issues.length
        ? `<p class="error-text">Alertes: ${escapeHtml(issues.slice(0, 3).join(" | "))}${issues.length > 3 ? " ..." : ""}</p>`
        : `<p class="muted">Alerte: aucune</p>`;
    const mappingRows = _buildDeviceImportMappingRows(
        sourceHeaders,
        draft?.preview?.effectiveMapping || [],
        draft?.mapping || [],
    );
    const credentialModeOptions = DEVICE_IMPORT_CREDENTIAL_MODES
        .map((option) => (
            `<option value="${escapeAttribute(option.value)}" ${credentialMode === option.value ? "selected" : ""}>${escapeHtml(option.label)}</option>`
        ))
        .join("");
    const headerModeOptions = DEVICE_IMPORT_HEADER_MODES
        .map((option) => (
            `<option value="${escapeAttribute(option.value)}" ${headerMode === option.value ? "selected" : ""}>${escapeHtml(option.label)}</option>`
        ))
        .join("");
    const sheetSelectorMarkup = availableSheets.length > 1
        ? `
            <label class="field">
                <span>Feuille Excel</span>
                <select name="device_import_sheet">
                    ${availableSheets.map((sheet) => {
                        const label = String(sheet || "").trim();
                        const selected = label && label === selectedSheetName;
                        return `<option value="${escapeAttribute(label)}" ${selected ? "selected" : ""}>${escapeHtml(label)}</option>`;
                    }).join("")}
                </select>
            </label>
        `
        : "";
    const manualHeaderFieldMarkup = `
        <label class="field">
            <span>Ligne entete</span>
            <input name="device_import_header_row" type="number" min="1" step="1" value="${escapeAttribute(String(headerRowNumber))}" ${headerMode === "manual" ? "" : "disabled"}>
        </label>
    `;
    return `
        <form id="modal-device-import-form" class="modal-form">
            <section class="modal-section">
                <h3>Fichier</h3>
                <p class="muted">${escapeHtml(String(draft?.file?.name || ""))}</p>
                <p class="muted">Colonnes detectees: ${Number(draft?.preview?.detectedColumns || 0)} | Lignes detectees: ${Number(draft?.preview?.detectedRows || 0)}</p>
                <p class="muted">Entete active: ligne ${detectedHeaderRowNumber} (${effectiveHeaderMode}).</p>
                <div class="modal-settings-grid">
                    ${sheetSelectorMarkup}
                    <label class="field">
                        <span>Detection entete</span>
                        <select name="device_import_header_mode">
                            ${headerModeOptions}
                        </select>
                    </label>
                    ${manualHeaderFieldMarkup}
                    <label class="field">
                        <span>Identifiants existants</span>
                        <select name="device_import_credential_mode">
                            ${credentialModeOptions}
                        </select>
                    </label>
                </div>
                ${issueText}
            </section>
            <section class="modal-section">
                <h3>Previsualisation source</h3>
                ${_buildDeviceImportSourceTable(sourceHeaders, sourceRowsPreview)}
            </section>
            <section class="modal-section">
                <h3>Mapping des colonnes</h3>
                <div class="inventory-table-wrap">
                    <table class="inventory-table">
                        <thead>
                            <tr>
                                <th>Colonne source</th>
                                <th>Champ cible</th>
                                <th>Cle custom</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${mappingRows || '<tr><td colspan="3" class="muted">Aucune colonne detectee.</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </section>
            <section class="modal-section">
                <h3>Apercu des donnees mappees</h3>
                ${_buildDeviceImportMappedPreview(mappedRows)}
            </section>
            <p id="modal-device-import-feedback" class="muted inventory-feedback"></p>
            <div class="modal-actions">
                <button type="button" class="toolbar-btn" data-action="device-import:refresh-preview">Recalculer apercu</button>
                <button type="button" class="toolbar-btn" data-action="modal:close">Annuler</button>
                <button type="submit" class="toolbar-btn primary">Importer</button>
            </div>
        </form>
    `;
}

function openDeviceImportWizardModal(draft) {
    state.deviceImportDraft = {
        file: draft.file,
        defaultDeviceType: String(draft.defaultDeviceType || "").trim().toLowerCase(),
        credentialMode: normalizeImportCredentialMode(draft.credentialMode),
        headerMode: normalizeImportHeaderMode(draft.headerMode || draft.preview?.effectiveHeaderMode || "auto"),
        headerRowNumber: normalizeImportHeaderRowNumber(draft.headerRowNumber || draft.preview?.detectedHeaderRowNumber || 1),
        selectedSheetName: String(draft.selectedSheetName || draft.preview?.selectedSheetName || "").trim(),
        mapping: _normalizeDeviceImportMappingRows(draft.mapping || []),
        preview: {
            rows: Array.isArray(draft.preview?.rows) ? draft.preview.rows : [],
            detectedRows: Number(draft.preview?.detectedRows || 0),
            detectedColumns: Number(draft.preview?.detectedColumns || 0),
            issues: Array.isArray(draft.preview?.issues) ? draft.preview.issues : [],
            sourceHeaders: Array.isArray(draft.preview?.sourceHeaders) ? draft.preview.sourceHeaders : [],
            sourceRowsPreview: Array.isArray(draft.preview?.sourceRowsPreview) ? draft.preview.sourceRowsPreview : [],
            availableSheets: Array.isArray(draft.preview?.availableSheets) ? draft.preview.availableSheets : [],
            selectedSheetName: String(draft.preview?.selectedSheetName || draft.selectedSheetName || "").trim(),
            detectedHeaderRowNumber: Number(draft.preview?.detectedHeaderRowNumber || draft.headerRowNumber || 1),
            effectiveHeaderMode: normalizeImportHeaderMode(draft.preview?.effectiveHeaderMode || draft.headerMode || "auto"),
            effectiveMapping: _normalizeDeviceImportMappingRows(draft.preview?.effectiveMapping || []),
        },
    };
    openModal(
        "Import equipements",
        buildDeviceImportWizardMarkup(state.deviceImportDraft),
        { width: "min(1160px, calc(100vw - 36px))" },
    );
}

async function previewDeviceInventoryImportFromFile(
    file,
    defaultDeviceType,
    columnMappings = [],
    credentialMode = "preserve_on_blank",
    sheetName = "",
    headerMode = "auto",
    headerRowNumber = 1,
) {
    const sharedImport = window.NMPSharedImport;
    if (!(sharedImport && typeof sharedImport.postImport === "function")) {
        throw new Error("Module d'import indisponible.");
    }
    return sharedImport.postImport({
        file,
        headersFactory: headers,
        candidatePaths: ["/devices/import/preview"],
        normalizeErrorMessage,
        requestBodyBuilder: (ctx) => ({
            filename: String(ctx.file?.name || ""),
            content_base64: String(ctx.contentBase64 || ""),
            default_device_type: String(defaultDeviceType || ""),
            upsert_existing: true,
            column_mappings: _normalizeDeviceImportMappingRows(columnMappings),
            credential_mode: normalizeImportCredentialMode(credentialMode),
            sheet_name: String(sheetName || "").trim(),
            header_mode: normalizeImportHeaderMode(headerMode),
            header_row_number: normalizeImportHeaderRowNumber(headerRowNumber),
        }),
        responseMapper: (payload) => ({
            rows: Array.isArray(payload?.rows) ? payload.rows : [],
            detectedRows: Number(payload?.detected_rows || 0),
            detectedColumns: Number(payload?.detected_columns || 0),
            issues: Array.isArray(payload?.issues) ? payload.issues : [],
            sourceHeaders: Array.isArray(payload?.source_headers) ? payload.source_headers : [],
            sourceRowsPreview: Array.isArray(payload?.source_rows_preview) ? payload.source_rows_preview : [],
            availableSheets: Array.isArray(payload?.available_sheets) ? payload.available_sheets : [],
            selectedSheetName: String(payload?.selected_sheet_name || "").trim(),
            detectedHeaderRowNumber: Number(payload?.detected_header_row_number || 1),
            effectiveHeaderMode: normalizeImportHeaderMode(payload?.effective_header_mode || "auto"),
            effectiveMapping: _normalizeDeviceImportMappingRows(payload?.effective_mapping || []),
        }),
    });
}

async function applyDeviceInventoryImportFromFile(
    file,
    defaultDeviceType,
    columnMappings = [],
    credentialMode = "preserve_on_blank",
    sheetName = "",
    headerMode = "auto",
    headerRowNumber = 1,
) {
    const sharedImport = window.NMPSharedImport;
    if (!(sharedImport && typeof sharedImport.postImport === "function")) {
        throw new Error("Module d'import indisponible.");
    }
    return sharedImport.postImport({
        file,
        headersFactory: headers,
        candidatePaths: ["/devices/import/apply"],
        normalizeErrorMessage,
        requestBodyBuilder: (ctx) => ({
            filename: String(ctx.file?.name || ""),
            content_base64: String(ctx.contentBase64 || ""),
            default_device_type: String(defaultDeviceType || ""),
            upsert_existing: true,
            column_mappings: _normalizeDeviceImportMappingRows(columnMappings),
            credential_mode: normalizeImportCredentialMode(credentialMode),
            sheet_name: String(sheetName || "").trim(),
            header_mode: normalizeImportHeaderMode(headerMode),
            header_row_number: normalizeImportHeaderRowNumber(headerRowNumber),
        }),
        responseMapper: (payload) => ({
            processed: Number(payload?.processed || 0),
            created: Number(payload?.created || 0),
            updated: Number(payload?.updated || 0),
            skipped: Number(payload?.skipped || 0),
            issues: Array.isArray(payload?.issues) ? payload.issues : [],
        }),
    });
}

async function refreshDeviceImportWizardPreviewFromForm(form) {
    if (!state.deviceImportDraft?.file) {
        throw new Error("Fichier d'import introuvable.");
    }
    const mapping = _collectDeviceImportMappingsFromForm(form);
    const credentialMode = _collectDeviceImportCredentialModeFromForm(form);
    const sheetName = _collectDeviceImportSheetNameFromForm(form);
    const headerMode = _collectDeviceImportHeaderModeFromForm(form);
    const headerRowNumber = _collectDeviceImportHeaderRowFromForm(form);
    const feedback = document.getElementById("modal-device-import-feedback");
    if (feedback) {
        feedback.textContent = "Recalcul de l'apercu...";
    }
    const preview = await previewDeviceInventoryImportFromFile(
        state.deviceImportDraft.file,
        state.deviceImportDraft.defaultDeviceType,
        mapping,
        credentialMode,
        sheetName,
        headerMode,
        headerRowNumber,
    );
    openDeviceImportWizardModal({
        file: state.deviceImportDraft.file,
        defaultDeviceType: state.deviceImportDraft.defaultDeviceType,
        credentialMode,
        headerMode,
        headerRowNumber,
        selectedSheetName: preview.selectedSheetName || sheetName,
        mapping,
        preview,
    });
}

async function submitDeviceImportWizard(form) {
    if (!state.deviceImportDraft?.file) {
        throw new Error("Fichier d'import introuvable.");
    }
    const feedback = document.getElementById("modal-device-import-feedback");
    const mapping = _collectDeviceImportMappingsFromForm(form);
    const credentialMode = _collectDeviceImportCredentialModeFromForm(form);
    const sheetName = _collectDeviceImportSheetNameFromForm(form);
    const headerMode = _collectDeviceImportHeaderModeFromForm(form);
    const headerRowNumber = _collectDeviceImportHeaderRowFromForm(form);
    if (feedback) {
        feedback.textContent = "Validation de l'apercu...";
    }
    const preview = await previewDeviceInventoryImportFromFile(
        state.deviceImportDraft.file,
        state.deviceImportDraft.defaultDeviceType,
        mapping,
        credentialMode,
        sheetName,
        headerMode,
        headerRowNumber,
    );
    if (!Array.isArray(preview.rows) || !preview.rows.length) {
        if (feedback) {
            feedback.textContent = "Aucune ligne exploitable avec ce mapping.";
        }
        return;
    }
    if (feedback) {
        feedback.textContent = "Import en cours...";
    }
    const applied = await applyDeviceInventoryImportFromFile(
        state.deviceImportDraft.file,
        state.deviceImportDraft.defaultDeviceType,
        mapping,
        credentialMode,
        sheetName,
        headerMode,
        headerRowNumber,
    );
    const importedTypes = Array.from(new Set(
        preview.rows
            .map((row) => String(row?.device_type || "").trim())
            .filter(Boolean),
    ));
    importedTypes.forEach((typeCode) => {
        delete state.deviceSchemas[typeCode];
    });
    await Promise.all([
        loadDeviceTypes(),
        loadInventory(),
        refreshSnapshot(),
        ...importedTypes.map((typeCode) => ensureDeviceTypeSchema(typeCode)),
    ]);
    renderInventoryDetail();
    closeModal();
    const issuesCount = Array.isArray(applied.issues) ? applied.issues.length : 0;
    inventoryFeedback.textContent = `Import termine: ${applied.created} cree(s), ${applied.updated} mis a jour, ${applied.skipped} ignore(s).${issuesCount ? ` (${issuesCount} alerte(s))` : ""}`;
}

async function runDeviceInventoryImportFlow() {
    const file = await pickDeviceInventoryImportFile();
    if (!file) {
        return;
    }
    const selectedTypeFilter = String(inventoryTypeFilter?.value || "").trim().toLowerCase();
    const defaultDeviceType = selectedTypeFilter && selectedTypeFilter !== "all" ? selectedTypeFilter : "";
    setInventoryImportProgress(10, "Analyse du fichier...", true);
    inventoryFeedback.textContent = "Analyse du fichier en cours...";
    const preview = await previewDeviceInventoryImportFromFile(file, defaultDeviceType, []);
    if (!Array.isArray(preview.sourceHeaders) || !preview.sourceHeaders.length) {
        setInventoryImportProgress(0, "", false);
        inventoryFeedback.textContent = "Aucune colonne detectee dans le fichier.";
        return;
    }
    setInventoryImportProgress(100, "Apercu pret", true);
    openDeviceImportWizardModal({
        file,
        defaultDeviceType,
        credentialMode: "preserve_on_blank",
        selectedSheetName: preview.selectedSheetName || "",
        mapping: preview.effectiveMapping || [],
        preview,
    });
    setInventoryImportProgress(0, "", false);
    if (!Array.isArray(preview.rows) || !preview.rows.length) {
        inventoryFeedback.textContent = "Apercu charge. Aucun enregistrement exploitable pour l'instant: ajuste le mapping des colonnes.";
    } else {
        inventoryFeedback.textContent = "Apercu import charge. Ajuste le mapping puis valide.";
    }
}

async function runDeviceInventoryExportFlow() {
    const selectedType = String(inventoryTypeFilter?.value || "").trim().toLowerCase();
    const params = new URLSearchParams();
    if (selectedType) {
        params.set("device_type", selectedType);
    }
    const query = params.toString();
    const primaryPath = `/devices/export${query ? `?${query}` : ""}`;
    const fallbackPath = `/devices/export/csv${query ? `?${query}` : ""}`;
    const sharedImport = window.NMPSharedImport;
    if (!(sharedImport && typeof sharedImport.downloadExport === "function")) {
        throw new Error("Module d'export indisponible.");
    }
    inventoryFeedback.textContent = "Preparation de l'export...";
    const outcome = await sharedImport.downloadExport({
        candidatePaths: [primaryPath, fallbackPath],
        headersFactory: headers,
        normalizeErrorMessage,
        defaultFilename: selectedType ? `devices_${selectedType}.csv` : "devices_all.csv",
    });
    inventoryFeedback.textContent = `Export termine (${outcome.filename}).`;
}

async function submitNotificationSettings(form) {
    const formData = new window.FormData(form);
    const smtpPort = Number(formData.get("smtp_port") || 0);
    const feedback = document.getElementById("modal-notification-feedback");
    try {
        await applySettingsPatch(
            {
                smtp_host: String(formData.get("smtp_host") || "").trim(),
                smtp_port: Number.isFinite(smtpPort) ? smtpPort : 0,
                smtp_auth_enabled: form.querySelector('[name="smtp_auth_enabled"]')?.checked ?? false,
                user: String(formData.get("user") || "").trim(),
                smtp_password: String(formData.get("smtp_password") || ""),
                recipients: String(formData.get("recipients") || "").trim(),
                use_tls: form.querySelector('[name="use_tls"]')?.checked ?? false,
                show_status_popup: form.querySelector('[name="show_status_popup"]')?.checked ?? true,
            },
            "modal-notification-feedback",
        );
        window.setTimeout(() => closeModal(), 400);
    } catch (error) {
        if (feedback instanceof HTMLElement) {
            feedback.textContent = normalizeErrorMessage(error.message);
        }
        return;
    }
}

async function submitMonitoringNotificationSettings(form) {
    const formData = new window.FormData(form);
    const cooldownRaw = Number(formData.get("notification_cooldown_seconds") || 120);
    const feedback = document.getElementById("modal-monitoring-notification-feedback");
    try {
        await applySettingsPatch(
            {
                notification_cooldown_seconds: Number.isFinite(cooldownRaw) ? Math.max(0, Math.trunc(cooldownRaw)) : 120,
                monitoring_notify_on_outage: form.querySelector('[name="monitoring_notify_on_outage"]')?.checked ?? true,
                monitoring_notify_on_recovery: form.querySelector('[name="monitoring_notify_on_recovery"]')?.checked ?? true,
                monitoring_notification_subject_template: String(formData.get("monitoring_notification_subject_template") || "").trim(),
                monitoring_notification_body_template: String(formData.get("monitoring_notification_body_template") || "").trim(),
            },
            "modal-monitoring-notification-feedback",
        );
        window.setTimeout(() => closeModal(), 400);
    } catch (error) {
        if (feedback instanceof HTMLElement) {
            feedback.textContent = normalizeErrorMessage(error.message);
        }
        return;
    }
}

async function submitWebServerSettings(form) {
    const sharedParser = window.NMPSharedUi?.webServer?.parseSettingsForm;
    const payload = typeof sharedParser === "function"
        ? sharedParser(form)
        : (() => {
            const formData = new window.FormData(form);
            const parsedPort = Number(formData.get("web_server_port") || 8000);
            const port = Number.isFinite(parsedPort) ? Math.max(1, Math.min(65535, Math.trunc(parsedPort))) : 8000;
            const rawProxy = String(formData.get("web_server_reverse_proxy_type") || "aucun").trim().toLowerCase();
            const reverseProxyType = ["aucun", "nginx", "caddy"].includes(rawProxy) ? rawProxy : "aucun";
            return {
                web_server_host: String(formData.get("web_server_host") || "127.0.0.1").trim() || "127.0.0.1",
                web_server_port: port,
                web_server_autostart: form.querySelector('[name="web_server_autostart"]')?.checked ?? false,
                web_server_public_url: String(formData.get("web_server_public_url") || "").trim(),
                web_server_use_public_url: form.querySelector('[name="web_server_use_public_url"]')?.checked ?? false,
                web_server_reverse_proxy_type: reverseProxyType,
            };
        })();
    await applySettingsPatch(
        payload,
        "modal-webserver-feedback",
    );
    window.setTimeout(() => closeModal(), 400);
}

async function confirmTypeDisableSideEffects(typeCode, payload, feedback, options = {}) {
    let purgeTypeCredentials = false;
    const credentialsWillBeEnabled = Boolean(options.credentials_enabled ?? true);
    const normalizedTypeCode = String(typeCode || "").trim().toLowerCase();
    const currentMeta = typeMeta(typeCode);
    const wasMonitoringEnabled = Boolean(currentMeta?.monitoring_enabled);
    if (wasMonitoringEnabled && !payload.monitoring_enabled) {
        let hasLogs = false;
        try {
            const params = new URLSearchParams({ limit: "1", device_type: String(typeCode || "") });
            const rows = await requestJson(`/logs?${params.toString()}`);
            hasLogs = Array.isArray(rows) && rows.length > 0;
        } catch (_error) {
            hasLogs = false;
        }
        if (hasLogs) {
            const confirmed = window.confirm(
                `Desactiver le monitoring pour "${typeCode}" ?\n\nCe type ne sera plus ajoute au moteur de monitoring et ses logs seront supprimes.`,
            );
            if (!confirmed) {
                if (feedback) {
                    feedback.textContent = "Operation annulee.";
                }
                return { proceed: false, purgeTypeCredentials };
            }
        }
    }
    const wasConfigEnabled = Boolean(currentMeta?.config_backups_enabled);
    if (wasConfigEnabled && !payload.config_backups_enabled) {
        const hasAnyConfig = state.inventory.some((item) => item.device_type === typeCode && item.has_saved_config);
        if (hasAnyConfig) {
            const confirmed = window.confirm(
                `Desactiver les fichiers de configuration pour "${typeCode}" ?\n\nLes fichiers existants seront supprimes.`,
            );
            if (!confirmed) {
                if (feedback) {
                    feedback.textContent = "Operation annulee.";
                }
                return { proceed: false, purgeTypeCredentials };
            }
        }
    }
    const wasCredentialsEnabled = Boolean(options.was_credentials_enabled ?? currentMeta?.credentials_enabled ?? typeHasCredentialsSupport(typeCode));
    if (wasCredentialsEnabled && !credentialsWillBeEnabled) {
        const hasAnyStoredCredentials = await typeHasStoredDeviceCredentials(normalizedTypeCode);
        if (hasAnyStoredCredentials) {
            const purgeChosen = window.confirm(
                `Gestion des identifiants desactivee pour "${typeCode}".\n\nOK: supprimer les identifiants deja enregistres\nAnnuler: conserver les identifiants en base`,
            );
            purgeTypeCredentials = Boolean(purgeChosen);
        }
    }
    return { proceed: true, purgeTypeCredentials };
}

async function submitDeviceTypeSchemaForm(form) {
    const editor = state.typeSchemaEditor;
    const feedback = document.getElementById("modal-device-type-schema-feedback");
    if (!editor || !feedback) {
        return;
    }
    const formData = new window.FormData(form);
    const payload = {
        label: String(formData.get("type_schema_label") || "").trim(),
        monitoring_enabled: form.querySelector('[name="type_schema_monitoring_enabled"]')?.checked ?? true,
        config_backups_enabled: form.querySelector('[name="type_schema_config_backups_enabled"]')?.checked ?? false,
        version_token: String(editor.typeVersionToken || ""),
    };
    editor.credentialsEnabled = form.querySelector('[name="type_schema_credentials_enabled"]')?.checked ?? false;
    if (!payload.label) {
        feedback.textContent = "Libelle requis.";
        return;
    }
    let purgeTypeCredentials = false;
    if (!editor.createMode) {
        if (editor.initialCredentialsEnabled && !editor.credentialsEnabled && editor.purgeTypeCredentialsOnSave !== null) {
            const confirmation = await confirmTypeDisableSideEffects(
                editor.typeCode,
                payload,
                feedback,
                {
                    credentials_enabled: true,
                    was_credentials_enabled: false,
                },
            );
            if (!confirmation?.proceed) {
                return;
            }
            purgeTypeCredentials = Boolean(editor.purgeTypeCredentialsOnSave);
        } else {
            const confirmation = await confirmTypeDisableSideEffects(
                editor.typeCode,
                payload,
                feedback,
                {
                    credentials_enabled: editor.credentialsEnabled,
                    was_credentials_enabled: editor.initialCredentialsEnabled,
                },
            );
            if (!confirmation?.proceed) {
                return;
            }
            purgeTypeCredentials = Boolean(confirmation?.purgeTypeCredentials);
        }
    }

    editor.typeLabel = payload.label;
    editor.monitoringEnabled = payload.monitoring_enabled;
    editor.configBackupsEnabled = payload.config_backups_enabled;
    typeSchemaEnsureCoreFields(editor);
    typeSchemaCleanupDefaultMapForOs(editor);
    typeSchemaCleanupDefaultMapForActions(editor);
    typeSchemaEnsureActionDoubleClickField(editor);
    typeSchemaReindexSorts(editor);

    feedback.textContent = "Enregistrement...";
    if (editor.createMode) {
        const created = await requestJson("/device-types", {
            method: "POST",
            body: JSON.stringify(payload),
        });
        editor.typeCode = String(created?.code || "").trim().toLowerCase();
        editor.createMode = false;
        editor.typeVersionToken = String(created?.version_token || "");
    } else {
        const updatedType = await requestJson(`/device-types/${encodeURIComponent(editor.typeCode)}`, {
            method: "PUT",
            body: JSON.stringify(payload),
        });
        editor.typeVersionToken = String(updatedType?.version_token || editor.typeVersionToken || "");
    }
    const savedSchema = await requestJson(`/device-types/${encodeURIComponent(editor.typeCode)}/schema`, {
        method: "PUT",
        body: JSON.stringify({
            fields: editor.fields || [],
            actions: editor.actions || [],
            version_token: String(editor.schemaVersionToken || ""),
        }),
    });
    editor.schemaVersionToken = String(savedSchema?.version_token || editor.schemaVersionToken || "");
    state.deviceSchemas[editor.typeCode] = savedSchema;
    let purgeMessage = "";
    if (purgeTypeCredentials && !editor.credentialsEnabled) {
        const purgeResult = await requestJson(`/device-types/${encodeURIComponent(editor.typeCode)}/credentials/purge`, {
            method: "POST",
        });
        purgeMessage = String(purgeResult?.message || "").trim();
        await loadInventory();
    }
    await loadDeviceTypes();
    await refreshSnapshot();
    await returnFromTypeSchemaEditor(`${editor.typeLabel || editor.typeCode} enregistre.${purgeMessage ? ` ${purgeMessage}` : ""}`);
}

async function deleteDeviceTypeRequest(typeCode) {
    const meta = typeMeta(typeCode);
    const token = String(meta?.version_token || "").trim();
    const deletePath = token
        ? `/device-types/${encodeURIComponent(typeCode)}?cascade_devices=false&version_token=${encodeURIComponent(token)}`
        : `/device-types/${encodeURIComponent(typeCode)}?cascade_devices=false`;
    await requestJson(deletePath, {
        method: "DELETE",
    });
    if (state.deviceSchemas[typeCode]) {
        delete state.deviceSchemas[typeCode];
    }
}

async function deleteDeviceTypeRow(typeCode, options = {}) {
    const feedback = document.getElementById("modal-device-types-feedback");
    const meta = typeMeta(typeCode);
    const label = String(meta?.label || typeCode || "").trim();
    const confirmFirst = options.confirm !== false;
    const refreshAfter = options.refresh !== false;
    const reopenAfter = options.reopen !== false;
    if (confirmFirst && !window.confirm(`Supprimer le type "${label}" ?`)) {
        return false;
    }
    if (feedback) {
        feedback.textContent = `Suppression ${label}...`;
    }
    await deleteDeviceTypeRequest(typeCode);
    if (!refreshAfter) {
        return true;
    }
    await loadDeviceTypes();
    await refreshSnapshot();
    const message = `Type ${label} supprime.`;
    if (feedback) {
        feedback.textContent = message;
    }
    if (reopenAfter) {
        await openDeviceTypesModal();
        const refreshedFeedback = document.getElementById("modal-device-types-feedback");
        if (refreshedFeedback) {
            refreshedFeedback.textContent = message;
        }
    }
    return true;
}

async function deleteSelectedDeviceTypes() {
    const rows = activeDeviceTypeBatchRows()
        .filter((item) => String(item?.code || "").trim() && Boolean(item?.can_delete));
    const feedback = document.getElementById("modal-device-types-feedback");
    if (!rows.length) {
        if (feedback) {
            feedback.textContent = "Aucun type supprimable selectionne.";
        }
        return;
    }
    const confirmed = window.confirm(`Supprimer ${rows.length} type(s) selectionne(s) ?`);
    if (!confirmed) {
        return;
    }
    if (feedback) {
        feedback.textContent = `Suppression de ${rows.length} type(s)...`;
    }
    for (const row of rows) {
        await deleteDeviceTypeRequest(String(row?.code || ""));
    }
    clearDeviceTypeBatchSelection();
    await loadDeviceTypes();
    await refreshSnapshot();
    const message = `${rows.length} type(s) supprime(s).`;
    if (feedback) {
        feedback.textContent = message;
    }
    await openDeviceTypesModal();
    const refreshedFeedback = document.getElementById("modal-device-types-feedback");
    if (refreshedFeedback) {
        refreshedFeedback.textContent = message;
    }
}

function deviceTypeFeatureLabel(feature) {
    if (feature === "monitoring") {
        return "monitoring";
    }
    if (feature === "config") {
        return "configuration";
    }
    if (feature === "credentials") {
        return "gestion des identifiants";
    }
    return "parametre";
}

async function setDeviceTypeFeatureEnabled(row, feature, enabled) {
    const typeCode = String(row?.code || "").trim();
    if (!typeCode) {
        return false;
    }
    const normalizedFeature = String(feature || "").trim().toLowerCase();
    const meta = typeMeta(typeCode) || row || {};
    const schema = await requestJson(`/device-types/${encodeURIComponent(typeCode)}/schema`);
    const editor = createTypeSchemaEditorState(typeCode, schema, {
        ...meta,
        ...row,
    });
    if (normalizedFeature === "monitoring") {
        editor.monitoringEnabled = Boolean(enabled);
    } else if (normalizedFeature === "config") {
        editor.configBackupsEnabled = Boolean(enabled);
    } else if (normalizedFeature === "credentials") {
        editor.credentialsEnabled = Boolean(enabled);
    } else {
        return false;
    }
    typeSchemaEnsureCoreFields(editor);
    typeSchemaEnsureActionDoubleClickField(editor);
    typeSchemaReindexSorts(editor);
    const payload = {
        label: String(meta?.label || row?.label || typeCode).trim(),
        monitoring_enabled: Boolean(editor.monitoringEnabled),
        config_backups_enabled: Boolean(editor.configBackupsEnabled),
        version_token: String(meta?.version_token || row?.version_token || ""),
    };
    const feedback = document.getElementById("modal-device-types-feedback");
    const confirmation = await confirmTypeDisableSideEffects(typeCode, payload, feedback, {
        credentials_enabled: Boolean(editor.credentialsEnabled),
        was_credentials_enabled: Boolean(row?.credentials_enabled ?? meta?.credentials_enabled),
    });
    if (!confirmation?.proceed) {
        return false;
    }
    const updatedType = await requestJson(`/device-types/${encodeURIComponent(typeCode)}`, {
        method: "PUT",
        body: JSON.stringify(payload),
    });
    const savedSchema = await requestJson(`/device-types/${encodeURIComponent(typeCode)}/schema`, {
        method: "PUT",
        body: JSON.stringify({
            fields: editor.fields || [],
            actions: editor.actions || [],
            version_token: String(editor.schemaVersionToken || schema?.version_token || ""),
        }),
    });
    state.deviceSchemas[typeCode] = savedSchema;
    if (normalizedFeature === "credentials" && !editor.credentialsEnabled && confirmation?.purgeTypeCredentials) {
        await requestJson(`/device-types/${encodeURIComponent(typeCode)}/credentials/purge`, {
            method: "POST",
        });
        await loadInventory();
    }
    const index = state.deviceTypes.findIndex((item) => String(item?.code || "").trim() === typeCode);
    if (index >= 0) {
        state.deviceTypes[index] = {
            ...state.deviceTypes[index],
            ...updatedType,
            credentials_enabled: Boolean(editor.credentialsEnabled),
        };
    }
    return true;
}

async function setSelectedDeviceTypesFeature(feature, enabled) {
    const rows = activeDeviceTypeBatchRows();
    const feedback = document.getElementById("modal-device-types-feedback");
    const featureLabel = deviceTypeFeatureLabel(feature);
    if (!rows.length) {
        if (feedback) {
            feedback.textContent = "Aucun type selectionne.";
        }
        return;
    }
    if (feedback) {
        feedback.textContent = `${enabled ? "Activation" : "Desactivation"} ${featureLabel}...`;
    }
    let updated = 0;
    for (const row of rows) {
        const ok = await setDeviceTypeFeatureEnabled(row, feature, enabled);
        if (ok) {
            updated += 1;
        }
    }
    clearDeviceTypeBatchSelection();
    await loadDeviceTypes();
    await refreshSnapshot();
    const message = `${featureLabel} ${enabled ? "active" : "desactive"} pour ${updated} type(s).`;
    if (feedback) {
        feedback.textContent = message;
    }
    await openDeviceTypesModal();
    const refreshedFeedback = document.getElementById("modal-device-types-feedback");
    if (refreshedFeedback) {
        refreshedFeedback.textContent = message;
    }
}

async function setSingleDeviceTypeFeature(typeCode, feature, enabled) {
    const row = (state.deviceTypesModalRows || []).find((item) => String(item?.code || "").trim() === typeCode)
        || typeMeta(typeCode)
        || { code: typeCode };
    const ok = await setDeviceTypeFeatureEnabled(row, feature, enabled);
    if (!ok) {
        return;
    }
    await loadDeviceTypes();
    await refreshSnapshot();
    const featureLabel = deviceTypeFeatureLabel(feature);
    const message = `${featureLabel} ${enabled ? "active" : "desactive"} pour ${typeLabel(typeCode)}.`;
    const feedback = document.getElementById("modal-device-types-feedback");
    if (feedback) {
        feedback.textContent = message;
    }
    await openDeviceTypesModal();
    const refreshedFeedback = document.getElementById("modal-device-types-feedback");
    if (refreshedFeedback) {
        refreshedFeedback.textContent = message;
    }
}

function renderSection() {
    const summary = state.snapshot?.summary || {};
    const runningAny = Boolean(summary.running_any);
    renderNavigation(state.snapshot?.types || []);
    updateSupervisionTypeEditButton();
    const showDashboardHeaderTitle = state.currentSection === "supervision" && state.currentView === "dashboard";
    if (topbarTitle instanceof HTMLElement) {
        topbarTitle.hidden = !showDashboardHeaderTitle;
    }
    if (topbar instanceof HTMLElement) {
        topbar.classList.toggle("topbar-title-hidden", !showDashboardHeaderTitle);
    }
    if (!isInventoryWorkspaceSection(state.currentSection) && state.activeInlineModalHost === "inventory") {
        closeModal();
    }

    if (state.currentSection === "inventory") {
        if (state.activeInlineModalHost === "inventory") {
            closeModal();
        }
        detailPanel.classList.remove("detail-focus-mode");
        detailPanel.classList.remove("dashboard-detail-mode");
        cardsGrid.classList.remove("cards-grid-sticky");
        navToolbar.hidden = false;
        cardsGrid.hidden = true;
        monitoringToolbar.hidden = true;
        placeholderPanel.hidden = true;
        detailPanel.hidden = false;
        supervisionSection.hidden = true;
        inventorySection.hidden = false;
        inventorySection.classList.add("management-mode");
        if (inventoryMainPanel instanceof HTMLElement) {
            inventoryMainPanel.hidden = false;
        }
        runtimeStrip.hidden = true;
        detailTitle.textContent = "Gestion des equipements";
        updateDetailTitleMonitoringToggle("");
        renderInventoryFilters();
        renderInventoryDetail();
        return;
    }

    if (state.currentSection === "device_types") {
        detailPanel.classList.remove("detail-focus-mode");
        detailPanel.classList.remove("dashboard-detail-mode");
        cardsGrid.classList.remove("cards-grid-sticky");
        navToolbar.hidden = false;
        cardsGrid.hidden = true;
        monitoringToolbar.hidden = true;
        placeholderPanel.hidden = true;
        detailPanel.hidden = false;
        supervisionSection.hidden = true;
        inventorySection.hidden = false;
        inventorySection.classList.add("management-mode");
        if (inventoryMainPanel instanceof HTMLElement) {
            inventoryMainPanel.hidden = true;
        }
        runtimeStrip.hidden = true;
        detailTitle.textContent = "Types d'equipements";
        updateDetailTitleMonitoringToggle("");
        ensureDeviceTypesPageOpened();
        return;
    }

    const dashboardMode = state.currentView === "dashboard";
    detailPanel.classList.toggle("dashboard-detail-mode", dashboardMode);
    cardsGrid.hidden = !dashboardMode;
    cardsGrid.classList.toggle("cards-grid-sticky", dashboardMode);
    monitoringToolbar.hidden = true;
    supervisionSection.hidden = false;
    inventorySection.hidden = true;
    inventorySection.classList.remove("management-mode");
    if (inventoryMainPanel instanceof HTMLElement) {
        inventoryMainPanel.hidden = false;
    }
    runtimeStrip.hidden = true;
    if (dashboardMode) {
        renderCards(state.snapshot || { summary: {}, types: [] });
        updateDashboardStickyMetrics();
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
    rebuildNetworkScanKnownFlags();
    renderNetworkScanRows();
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
        } catch (_error) {
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

    websocket.addEventListener("open", () => {
        state.fallbackToPolling = false;
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
            return;
        }
        if (!state.fallbackToPolling) {
            startPollingLoop();
            return;
        }
    });

    websocket.addEventListener("error", () => {
        if (!state.fallbackToPolling) {
            if (state.websocket) {
                state.websocket.close();
            }
            startPollingLoop();
        }
    });
}

function enablePasswordChangeMode() {
    authForm.dataset.forcePasswordChange = "1";
    authSubmit.textContent = "Se connecter et changer le mot de passe";
    newPasswordField.hidden = false;
    newPasswordInput.required = true;
    confirmPasswordField.hidden = false;
    confirmPasswordInput.required = true;
}

async function loadCredentialRevealPolicy() {
    try {
        const settings = await requestJson("/settings");
        applyCredentialRevealUnlockDurationFromSettings(settings);
    } catch (_error) {
        applyCredentialRevealUnlockDurationFromSettings({
            credential_reveal_unlock_seconds: DEFAULT_CREDENTIAL_REVEAL_UNLOCK_SECONDS,
        });
    }
}

async function authenticate(username, password, newPassword) {
    const payload = {
        username: String(username || "").trim() || "sa",
        password: String(password || ""),
    };
    if (String(authForm.dataset.forcePasswordChange || "") === "1") {
        payload.new_password = String(newPassword || "");
    }
    const login = await requestJson("/auth/login", {
        method: "POST",
        body: JSON.stringify(payload),
        headers: {},
    });
    persistToken(login.access_token);
}

async function restoreSession() {
    if (!state.token) {
        return false;
    }
    try {
        const sharedAuth = window.NMPSharedAuth;
        if (sharedAuth && typeof sharedAuth.fetchSessionContext === "function" && typeof sharedAuth.applySessionContext === "function") {
            const context = await sharedAuth.fetchSessionContext(requestJson);
            sharedAuth.applySessionContext(state, context);
        } else {
            const me = await requestJson("/auth/me");
            state.sessionSubject = String(me?.subject || "").trim().toLowerCase();
            state.sessionLabel = state.sessionSubject;
            state.sessionRoleCode = ["sa", "admin"].includes(state.sessionSubject) ? "admin" : "";
            state.sessionRoleLabel = state.sessionRoleCode ? "Administrateur" : "";
            state.moduleAccess = [];
            state.moduleAccessLoaded = false;
        }
        renderSessionProfile();
        return true;
    } catch (_error) {
        persistToken("");
        clearSessionState();
        renderSessionProfile();
        return false;
    }
}

async function loadModuleAccess(options = {}) {
    const forceRefresh = Boolean(options.forceRefresh);
    if (!forceRefresh && state.moduleAccessLoaded) {
        return state.moduleAccess;
    }
    try {
        const rows = await requestJson("/auth/me/modules");
        state.moduleAccess = Array.isArray(rows) ? rows : [];
        state.moduleAccessLoaded = true;
        if (!state.sessionRoleCode) {
            const hasAdminModule = (state.moduleAccess || []).some((row) => String(row?.code || "").trim().toLowerCase() === "admin" && Boolean(row?.granted));
            if (hasAdminModule) {
                state.sessionRoleCode = "admin";
                if (!state.sessionRoleLabel) {
                    state.sessionRoleLabel = "Administrateur";
                }
                renderSessionProfile();
            }
        }
        return state.moduleAccess;
    } catch (_error) {
        state.moduleAccess = [];
        state.moduleAccessLoaded = true;
        return state.moduleAccess;
    }
}

async function boot() {
    if (!state.token) {
        redirectToPortal();
        return;
    }
    const sessionOk = await restoreSession();
    if (!sessionOk) {
        teardownRealtime();
        state.snapshot = null;
        redirectToPortal();
        return;
    }
    await Promise.all([
        loadModuleAccess(),
        loadUiConfig(),
        loadMonitoringCapabilities(),
        loadCredentialRevealPolicy(),
    ]);
    showDashboard();
    connectWebSocket();
    refreshWorkspaceData().catch(() => {});
}

authForm.addEventListener("submit", (event) => {
    event.preventDefault();
    redirectToPortal();
});

refreshButton.addEventListener("click", async () => {
    await refreshWorkspaceData();
});

window.addEventListener("resize", () => {
    if (state.currentSection === "supervision" && state.currentView === "dashboard") {
        updateDashboardStickyMetrics();
    }
});

async function logoutCurrentSession() {
    try {
        if (state.token) {
            await requestJson("/auth/logout", { method: "POST" });
        }
    } catch (_error) {
    }
    teardownRealtime();
    persistToken("");
    clearSessionState();
    renderSessionProfile();
    state.snapshot = null;
    state.inventory = [];
    state.deviceTypes = [];
    state.deviceSchemas = {};
    state.selectedDeviceKey = "";
    applyMonitoringTreeFilters({ typeCode: "dashboard", status: "" });
    applyUiConfig(null);
    redirectToPortal();
}

async function testConfigStorageSettings(form) {
    const feedback = document.getElementById("modal-config-storage-feedback");
    if (feedback) {
        feedback.textContent = "Enregistrement et test...";
    }
    try {
        await submitConfigStorageSettings(form, { keepOpen: true, silent: true });
        const stateResult = await loadConfigStorageState();
        updateConfigStorageStatePanel(stateResult);
        if (feedback) {
            const modeLabel = configStorageModeLabel(stateResult?.mode);
            feedback.textContent = stateResult?.can_open_backup_folder
                ? `Test OK (${modeLabel}). ${stateResult?.message || ""}`
                : `Test KO (${modeLabel}). ${stateResult?.message || ""}`;
        }
    } catch (error) {
        if (feedback) {
            feedback.textContent = `Test impossible: ${normalizeErrorMessage(error)}`;
        }
    }
}

function initProfileMenu() {
    profileMenuController = window.NMPSharedUi?.profileMenu?.createController?.({
        button: profileMenuButton,
        panel: profileMenuPanel,
        state,
        closePeers: () => {
            closeTopMenu();
            closeContextMenu();
        },
        getUiConfig: () => state.uiConfig,
        onThemeChanged: () => applyUiConfig(state.uiConfig),
        canDashboardEdit: () => state.currentSection === "supervision" && state.currentView === "dashboard",
        onDashboardEdit: () => ensureMonitoringDashboardEditor().toggleEditing?.(),
        onLogout: () => logoutCurrentSession(),
        escapeHtml,
        createMenuButton,
    }) || null;
}

deviceFilter.addEventListener("input", () => {
    if (state.snapshot) {
        renderDevices(state.snapshot);
    }
});

if (supervisionTypeFilter) {
    supervisionTypeFilter.addEventListener("change", () => {
        applyMonitoringTreeFilters({
            typeCode: supervisionTypeFilter.value || "global",
            status: state.supervisionStatusFilter,
        });
        if (state.snapshot) {
            applyCurrentView();
        }
    });
}

if (supervisionStatusFilter) {
    supervisionStatusFilter.addEventListener("change", () => {
        applyMonitoringTreeFilters({
            typeCode: currentMonitoringTreeFilters().typeCode,
            status: supervisionStatusFilter.value,
        });
        if (state.snapshot) {
            applyCurrentView();
        }
    });
}

if (supervisionEditTypeButton) {
    supervisionEditTypeButton.addEventListener("click", async () => {
        const typeCode = String(supervisionEditTypeButton.dataset.typeCode || currentSupervisionTypeCode()).trim().toLowerCase();
        if (!typeCode) {
            return;
        }
        try {
            await openDeviceTypeEditorModal(typeCode, {});
        } catch (error) {
            inventoryFeedback.textContent = normalizeErrorMessage(error.message);
        }
    });
}

inventoryTypeFilter.addEventListener("change", async () => {
    const selectedType = String(inventoryTypeFilter.value || "").trim();
    updateInventoryEditTypeButton();
    if (selectedType) {
        try {
            await ensureDeviceTypeSchema(selectedType);
        } catch (error) {
            inventoryFeedback.textContent = normalizeErrorMessage(error.message);
        }
    }
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

menuModules.addEventListener("click", () => openTopMenu(menuModules, "modules").catch(() => {}));
menuSupervision.addEventListener("click", () => openTopMenu(menuSupervision, "supervision").catch(() => {}));
menuEquipments.addEventListener("click", () => openTopMenu(menuEquipments, "equipments").catch(() => {}));
menuTools.addEventListener("click", () => openTopMenu(menuTools, "tools").catch(() => {}));
menuHelp.addEventListener("click", () => openTopMenu(menuHelp, "help").catch(() => {}));
initProfileMenu();

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

if (inventoryEditTypeButton) {
    inventoryEditTypeButton.addEventListener("click", async () => {
        const typeCode = String(inventoryEditTypeButton.dataset.typeCode || inventoryTypeFilter.value || "").trim().toLowerCase();
        if (!typeCode) {
            return;
        }
        try {
            await openDeviceTypeEditorModal(typeCode, {});
        } catch (error) {
            inventoryFeedback.textContent = normalizeErrorMessage(error.message);
        }
    });
}

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

if (inventoryImportButton) {
    inventoryImportButton.addEventListener("click", () => {
        runDeviceInventoryImportFlow().catch((error) => {
            setInventoryImportProgress(0, "", false);
            inventoryFeedback.textContent = normalizeErrorMessage(error.message);
        });
    });
}

if (inventoryExportButton) {
    inventoryExportButton.addEventListener("click", () => {
        runDeviceInventoryExportFlow().catch((error) => {
            inventoryFeedback.textContent = normalizeErrorMessage(error.message);
        });
    });
}

function buildNetworkToolModalMarkup(action, device) {
    return `
        <form id="modal-network-tool-form" class="modal-form" data-tool-action="${escapeAttribute(action)}">
            <div class="modal-grid">
                ${networkToolFieldsMarkup(action, device)}
            </div>
            <p id="modal-network-tool-feedback" class="muted inventory-feedback"></p>
            ${createModalActionsMarkup({
                buttons: [
                    { preset: "cancel" },
                    { preset: "stop", id: "modal-network-tool-stop", action: "network-tool:stop", disabled: true },
                    { preset: "run", label: "Relancer" },
                ],
            })}
            <section class="modal-section">
                <h3>Resultat</h3>
                <div id="modal-network-tool-output" class="modal-tool-output">
                    <div class="muted">Aucun resultat.</div>
                </div>
            </section>
        </form>
    `;
}

async function openNetworkToolModal(action, device) {
    openModal(
        networkToolTitle(action),
        buildNetworkToolModalMarkup(action, device),
        { width: "min(900px, calc(100vw - 40px))" },
    );
    const form = document.getElementById("modal-network-tool-form");
    if (form) {
        const feedback = document.getElementById("modal-network-tool-feedback");
        if (feedback) {
            feedback.textContent = "Demarrage automatique...";
        }
        await submitNetworkToolModal(form);
    }
}

async function submitNetworkToolModal(form) {
    if (form.dataset.running === "1") {
        return;
    }
    form.dataset.running = "1";
    const action = String(form.dataset.toolAction || "").trim();
    const streamEndpoint = networkToolStreamEndpoint(action);
    const endpoint = networkToolEndpoint(action);
    if (!endpoint) {
        form.dataset.running = "0";
        throw new Error("Outil reseau inconnu.");
    }
    const formData = new window.FormData(form);
    const payload = networkToolPayload(action, formData);
    const feedback = document.getElementById("modal-network-tool-feedback");
    const outputNode = document.getElementById("modal-network-tool-output");
    const stopButton = document.getElementById("modal-network-tool-stop");
    if (feedback) {
        feedback.textContent = "Execution en cours...";
    }
    if (stopButton) {
        stopButton.disabled = true;
    }
    if (state.networkToolAbortController) {
        state.networkToolAbortController.abort();
        state.networkToolAbortController = null;
    }

    if (streamEndpoint) {
        if (outputNode) {
            outputNode.innerHTML = `<pre class="tool-output-pre"></pre>`;
            outputNode.classList.remove("tool-output-ok", "tool-output-ko");
        }
        const pre = outputNode ? outputNode.querySelector("pre.tool-output-pre") : null;
        const appendLine = (line) => {
            if (!pre) {
                return;
            }
            pre.textContent = `${pre.textContent}${line}\n`;
            pre.scrollTop = pre.scrollHeight;
        };
        const controller = new AbortController();
        state.networkToolAbortController = controller;
        if (stopButton) {
            stopButton.disabled = false;
        }
        try {
            const response = await fetch(streamEndpoint, {
                method: "POST",
                signal: controller.signal,
                headers: {
                    "Content-Type": "application/json",
                    ...headers(),
                },
                body: JSON.stringify(payload),
            });
            if (!response.ok || !response.body) {
                let detail = `${response.status} ${response.statusText}`;
                try {
                    const body = await response.json();
                    detail = body.detail || body.message || detail;
                } catch (_error) {
                }
                throw new Error(normalizeErrorMessage(detail));
            }
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";
            let doneOk = false;
            while (true) {
                const { value, done } = await reader.read();
                if (done) {
                    break;
                }
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop() || "";
                for (const raw of lines) {
                    const line = String(raw || "").trim();
                    if (!line) {
                        continue;
                    }
                    let event = null;
                    try {
                        event = JSON.parse(line);
                    } catch (_error) {
                        appendLine(line);
                        continue;
                    }
                    if (event.type === "line") {
                        appendLine(String(event.line || ""));
                        continue;
                    }
                    if (event.type === "done") {
                        doneOk = Boolean(event.ok);
                    }
                }
            }
            if (outputNode) {
                outputNode.classList.toggle("tool-output-ok", doneOk);
                outputNode.classList.toggle("tool-output-ko", !doneOk);
            }
            if (feedback) {
                feedback.textContent = doneOk ? "Execution terminee (OK)." : "Execution terminee (ECHEC).";
            }
        } catch (error) {
            if (controller.signal.aborted) {
                if (feedback) {
                    feedback.textContent = "Execution arretee.";
                }
                if (outputNode) {
                    outputNode.classList.remove("tool-output-ok");
                }
            } else {
                if (outputNode) {
                    outputNode.classList.remove("tool-output-ok");
                    outputNode.classList.add("tool-output-ko");
                }
                if (feedback) {
                    feedback.textContent = normalizeErrorMessage(error.message);
                }
            }
        } finally {
            if (state.networkToolAbortController === controller) {
                state.networkToolAbortController = null;
            }
            if (stopButton) {
                stopButton.disabled = true;
            }
            form.dataset.running = "0";
        }
        return;
    }

    try {
        const result = await requestJson(endpoint, {
            method: "POST",
            body: JSON.stringify(payload),
        });
        if (outputNode) {
            outputNode.innerHTML = `<pre class="tool-output-pre">${escapeHtml(String(result?.output || "Aucune sortie."))}</pre>`;
            outputNode.classList.toggle("tool-output-ok", Boolean(result?.ok));
            outputNode.classList.toggle("tool-output-ko", !Boolean(result?.ok));
        }
        if (feedback) {
            feedback.textContent = Boolean(result?.ok) ? "Execution terminee (OK)." : "Execution terminee (ECHEC).";
        }
    } catch (error) {
        if (outputNode) {
            outputNode.innerHTML = `<div class="error-text">${escapeHtml(normalizeErrorMessage(error.message))}</div>`;
            outputNode.classList.remove("tool-output-ok");
            outputNode.classList.add("tool-output-ko");
        }
        if (feedback) {
            feedback.textContent = normalizeErrorMessage(error.message);
        }
    }
    form.dataset.running = "0";
}

function buildNetworkScanModalMarkup() {
    return `
        <form id="modal-network-scan-form" class="modal-form">
            <div class="modal-grid">
                <div class="field wide">
                    <span>Mode</span>
                    <div class="inventory-controls">
                        <label class="field-inline">
                            <input type="radio" name="scan_mode" value="vlan" checked>
                            <span>VLAN</span>
                        </label>
                        <label class="field-inline">
                            <input type="radio" name="scan_mode" value="manual">
                            <span>Plage manuelle</span>
                        </label>
                    </div>
                </div>
                <label class="field" data-scan-vlan-block>
                    <span>VLAN</span>
                    <input name="scan_vlan" value="1">
                </label>
                <label class="field" data-scan-manual-block>
                    <span>Debut IP</span>
                    <input name="scan_start_ip" value="192.168.1.1">
                </label>
                <label class="field" data-scan-manual-block>
                    <span>Fin IP</span>
                    <input name="scan_end_ip" value="192.168.1.254">
                </label>
            </div>
            <div class="modal-grid" data-scan-advanced-block>
                <label class="field">
                    <span>Timeout (ms)</span>
                    <input name="scan_timeout_ms" value="800">
                </label>
                <label class="field">
                    <span>Workers</span>
                    <input name="scan_workers" value="16">
                </label>
            </div>
            <p id="modal-network-scan-feedback" class="muted inventory-feedback"></p>
            <div class="network-scan-toolbar">
                <div class="inventory-controls network-scan-options">
                    <label class="field-inline">
                        <input type="checkbox" name="scan_vendor_online">
                        <span>Fabricants en ligne</span>
                    </label>
                    <label class="field-inline">
                        <input type="checkbox" name="scan_advanced">
                        <span>Parametres avances</span>
                    </label>
                </div>
                <div class="modal-scan-progress modal-scan-progress-inline">
                    <progress id="modal-network-scan-progress" value="0" max="100"></progress>
                    <span id="modal-network-scan-status" class="muted">Pret.</span>
                </div>
                ${createModalActionsMarkup({
                    className: "network-scan-actions",
                    buttons: [
                        { preset: "close" },
                        { preset: "stop", id: "modal-network-scan-stop", action: "network-scan:stop", disabled: true },
                        { preset: "run", id: "modal-network-scan-run", label: "Scanner" },
                    ],
                })}
            </div>
            <section class="modal-section">
                <h3>Resultats</h3>
                <div class="table-wrap inventory-table-wrap network-scan-results-wrap">
                    <table class="device-table inventory-table">
                        <thead>
                        <tr>
                            <th>IP</th>
                            <th>Nom</th>
                            <th>Fabricant</th>
                            <th>MAC</th>
                            <th>Etat</th>
                            <th>Action</th>
                        </tr>
                        </thead>
                        <tbody id="modal-network-scan-body">
                        <tr><td colspan="6" class="muted">Aucun resultat.</td></tr>
                        </tbody>
                    </table>
                </div>
            </section>
        </form>
    `;
}

function syncNetworkScanMode(form) {
    const mode = String(form?.querySelector('[name="scan_mode"]:checked')?.value || "vlan").trim().toLowerCase();
    const vlanBlock = form?.querySelector("[data-scan-vlan-block]");
    const manualBlocks = Array.from(form?.querySelectorAll("[data-scan-manual-block]") || []);
    const vlanMode = mode === "vlan";
    if (vlanBlock instanceof HTMLElement) {
        vlanBlock.style.display = vlanMode ? "" : "none";
    }
    for (const block of manualBlocks) {
        if (!(block instanceof HTMLElement)) {
            continue;
        }
        block.style.display = vlanMode ? "none" : "";
    }
}

function syncNetworkScanAdvanced(form) {
    const advanced = Boolean(form?.querySelector('[name="scan_advanced"]')?.checked);
    const block = form?.querySelector("[data-scan-advanced-block]");
    if (block instanceof HTMLElement) {
        block.style.display = advanced ? "" : "none";
    }
}

function rowToKnownScanRow(row) {
    const knownIps = knownInventoryIpSet();
    const ip = String(row?.ip || "").trim();
    const normalizedIp = normalizeIpKey(ip);
    return {
        ip,
        hostname: String(row?.hostname || "").trim(),
        vendor: String(row?.vendor || "").trim(),
        mac: String(row?.mac || "").trim(),
        status: String(row?.status || "").trim(),
        exists: Boolean(normalizedIp && knownIps.has(normalizedIp)),
    };
}

function rebuildNetworkScanKnownFlags() {
    state.networkScanRows = (state.networkScanRows || []).map((row) => rowToKnownScanRow(row));
}

function renderNetworkScanRows() {
    const tbody = document.getElementById("modal-network-scan-body");
    if (!(tbody instanceof HTMLElement)) {
        return;
    }
    const rows = Array.isArray(state.networkScanRows) ? state.networkScanRows : [];
    if (!rows.length) {
        tbody.innerHTML = `<tr><td colspan="6" class="muted">Aucun resultat.</td></tr>`;
        return;
    }
    tbody.innerHTML = rows
        .map((row) => {
            const rowClass = row.exists ? "scan-row-known" : "scan-row-new";
            const scanState = row.exists ? "Deja gere" : "Nouveau";
            return `
                <tr class="${rowClass}" data-scan-ip="${escapeAttribute(row.ip)}">
                    <td>${escapeHtml(row.ip)}</td>
                    <td>${escapeHtml(row.hostname || "")}</td>
                    <td>${escapeHtml(row.vendor || "")}</td>
                    <td>${escapeHtml(row.mac || "")}</td>
                    <td>${escapeHtml(scanState)}</td>
                    <td class="inventory-row-actions">
                        ${row.exists
                            ? createIconActionButtonMarkup({
                                icon: "settings",
                                title: "Modifier device",
                                data: { scan_edit_ip: row.ip },
                            })
                            : createIconActionButtonMarkup({
                                icon: "add",
                                title: "Ajouter en device",
                                data: { scan_add_ip: row.ip },
                            })}
                    </td>
                </tr>
            `;
        })
        .join("");
}

function scanRowByIp(ip) {
    const wanted = normalizeIpKey(ip);
    return (state.networkScanRows || []).find((row) => normalizeIpKey(row?.ip || "") === wanted) || null;
}

function openNetworkScanContextMenu(x, y, row) {
    state.networkScanContextIp = String(row?.ip || "").trim();
    const isExisting = Boolean(row?.exists);
    contextMenu.innerHTML = `
        <div class="context-menu-group">
            ${
                isExisting
                    ? createMenuButton("Modifier device", `scan:edit:${state.networkScanContextIp}`)
                    : createMenuButton("Ajouter en device", `scan:add:${state.networkScanContextIp}`)
            }
        </div>
    `;
    contextMenu.hidden = false;
    const maxX = window.innerWidth - contextMenu.offsetWidth - 12;
    const maxY = window.innerHeight - contextMenu.offsetHeight - 12;
    contextMenu.style.left = `${Math.max(8, Math.min(x, maxX))}px`;
    contextMenu.style.top = `${Math.max(8, Math.min(y, maxY))}px`;
}

async function openNetworkScanModal() {
    state.networkScanRows = [];
    state.networkScanContextIp = "";
    openModal("Scan reseau", buildNetworkScanModalMarkup(), {
        width: "min(1120px, calc(100vw - 40px))",
    });
    const form = document.getElementById("modal-network-scan-form");
    if (form instanceof HTMLFormElement) {
        syncNetworkScanMode(form);
        syncNetworkScanAdvanced(form);
    }
    renderNetworkScanRows();
}

function buildScanCreateDeviceDescription(row) {
    const parts = ["Decouvert par scan reseau (web)"];
    if (row?.mac) {
        parts.push(`MAC: ${row.mac}`);
    }
    if (row?.vendor) {
        parts.push(`Fabricant: ${row.vendor}`);
    }
    return parts.join(" | ");
}

async function openCreateDeviceFromScanRow(ip) {
    const row = scanRowByIp(ip);
    if (!row || row.exists) {
        return;
    }
    const preferredType = String(inventoryTypeFilter.value || "").trim()
        || String(state.deviceTypes?.[0]?.code || "").trim();
    if (!preferredType) {
        const feedback = document.getElementById("modal-network-scan-feedback");
        if (feedback) {
            feedback.textContent = "Aucun type disponible pour ajouter un equipement.";
        }
        return;
    }
    await openDeviceModal(
        {
            name: row.hostname || row.ip,
            ip: row.ip,
            description: buildScanCreateDeviceDescription(row),
            notify: true,
            device_type: preferredType,
            custom_data: {},
        },
        { mode: "create", deviceType: preferredType },
    );
}

async function openEditDeviceFromScanRow(ip) {
    const existing = inventoryDeviceByIp(ip);
    if (!existing) {
        const feedback = document.getElementById("modal-network-scan-feedback");
        if (feedback) {
            feedback.textContent = "Device existant introuvable.";
        }
        return;
    }
    state.selectedDeviceKey = deviceKey(existing);
    await openDeviceModal(existing, { mode: "edit" });
}

async function submitNetworkScanModal(form) {
    if (form.dataset.running === "1") {
        return;
    }
    form.dataset.running = "1";
    const feedback = document.getElementById("modal-network-scan-feedback");
    const runButton = document.getElementById("modal-network-scan-run");
    const stopButton = document.getElementById("modal-network-scan-stop");
    const progress = document.getElementById("modal-network-scan-progress");
    const status = document.getElementById("modal-network-scan-status");
    const mode = String(form.querySelector('[name="scan_mode"]:checked')?.value || "vlan").trim().toLowerCase();
    const advanced = Boolean(form.querySelector('[name="scan_advanced"]')?.checked);
    const payload = {
        mode,
        vlan: Number(form.querySelector('[name="scan_vlan"]')?.value || 1),
        start_ip: String(form.querySelector('[name="scan_start_ip"]')?.value || "").trim(),
        end_ip: String(form.querySelector('[name="scan_end_ip"]')?.value || "").trim(),
        allow_vendor_online: Boolean(form.querySelector('[name="scan_vendor_online"]')?.checked),
        timeout_ms: advanced ? Number(form.querySelector('[name="scan_timeout_ms"]')?.value || 800) : 800,
        max_workers: advanced ? Number(form.querySelector('[name="scan_workers"]')?.value || 16) : 16,
    };
    if (feedback) {
        feedback.textContent = "Scan en cours...";
    }
    if (status) {
        status.textContent = "Demarrage...";
    }
    if (runButton) {
        runButton.disabled = true;
    }
    if (stopButton) {
        stopButton.disabled = false;
    }
    if (progress) {
        progress.value = 0;
        progress.max = 100;
    }
    try {
        state.networkScanRows = [];
        renderNetworkScanRows();
        if (state.networkScanAbortController) {
            state.networkScanAbortController.abort();
        }
        const controller = new AbortController();
        state.networkScanAbortController = controller;
        const response = await fetch("/network-scan/stream", {
            method: "POST",
            signal: controller.signal,
            headers: {
                "Content-Type": "application/json",
                ...headers(),
            },
            body: JSON.stringify(payload),
        });
        if (!response.ok || !response.body) {
            let detail = `${response.status} ${response.statusText}`;
            try {
                const body = await response.json();
                detail = body.detail || body.message || detail;
            } catch (_error) {
            }
            throw new Error(normalizeErrorMessage(detail));
        }
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let detected = 0;
        let doneOk = true;
        let doneMessage = "";
        while (true) {
            const { value, done } = await reader.read();
            if (done) {
                break;
            }
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";
            for (const raw of lines) {
                const line = String(raw || "").trim();
                if (!line) {
                    continue;
                }
                let eventData = null;
                try {
                    eventData = JSON.parse(line);
                } catch (_error) {
                    continue;
                }
                const eventType = String(eventData?.type || "").trim().toLowerCase();
                if (eventType === "progress") {
                    const doneValue = Number(eventData.done || 0);
                    const totalValue = Math.max(1, Number(eventData.total || 1));
                    if (progress) {
                        progress.max = totalValue;
                        progress.value = Math.min(doneValue, totalValue);
                    }
                    if (status) {
                        status.textContent = `Scan en cours: ${Math.min(doneValue, totalValue)}/${totalValue} | trouves: ${detected}`;
                    }
                    continue;
                }
                if (eventType === "row" && eventData.row) {
                    const newRow = rowToKnownScanRow(eventData.row);
                    const key = normalizeIpKey(newRow.ip);
                    const index = state.networkScanRows.findIndex((item) => normalizeIpKey(item.ip) === key);
                    if (index >= 0) {
                        state.networkScanRows[index] = { ...state.networkScanRows[index], ...newRow };
                    } else {
                        state.networkScanRows.push(newRow);
                        detected += 1;
                    }
                    renderNetworkScanRows();
                    continue;
                }
                if (eventType === "done") {
                    doneOk = Boolean(eventData.ok);
                    doneMessage = String(eventData.message || "").trim();
                }
            }
        }
        if (feedback) {
            feedback.textContent = doneOk
                ? `${state.networkScanRows.length} hote(s) detecte(s).`
                : `Erreur scan: ${doneMessage || "inconnue"}`;
        }
        if (status) {
            status.textContent = doneOk
                ? `Scan termine: ${state.networkScanRows.length} hote(s).`
                : "Scan en erreur.";
        }
    } catch (error) {
        const aborted = Boolean(state.networkScanAbortController?.signal?.aborted);
        if (feedback) {
            feedback.textContent = aborted ? "Scan arrete." : normalizeErrorMessage(error.message);
        }
        if (status) {
            status.textContent = aborted ? "Scan annule." : "Scan en erreur.";
        }
    } finally {
        state.networkScanAbortController = null;
        if (runButton) {
            runButton.disabled = false;
        }
        if (stopButton) {
            stopButton.disabled = true;
        }
        form.dataset.running = "0";
    }
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
    const typeCode = String(state.contextMenuTypeCode || "").trim();
    closeContextMenu();
    if (action === "type:view" && typeCode) {
        await viewDeviceTypeInventory(typeCode);
        return;
    }
    if (action === "types:add") {
        openCreateDeviceTypeEditorModal();
        return;
    }
    if (action === "type:edit" && typeCode) {
        await openDeviceTypeEditorModal(typeCode, {});
        return;
    }
    if (action === "type:delete" && typeCode) {
        await deleteDeviceTypeRow(typeCode);
        return;
    }
    if (action === "type:monitoring-on" && typeCode) {
        await setSingleDeviceTypeFeature(typeCode, "monitoring", true);
        return;
    }
    if (action === "type:monitoring-off" && typeCode) {
        await setSingleDeviceTypeFeature(typeCode, "monitoring", false);
        return;
    }
    if (action === "type:config-on" && typeCode) {
        await setSingleDeviceTypeFeature(typeCode, "config", true);
        return;
    }
    if (action === "type:config-off" && typeCode) {
        await setSingleDeviceTypeFeature(typeCode, "config", false);
        return;
    }
    if (action === "type:credentials-on" && typeCode) {
        await setSingleDeviceTypeFeature(typeCode, "credentials", true);
        return;
    }
    if (action === "type:credentials-off" && typeCode) {
        await setSingleDeviceTypeFeature(typeCode, "credentials", false);
        return;
    }
    if (action === "type:batch-delete") {
        await deleteSelectedDeviceTypes();
        return;
    }
    if (action === "type:batch-monitoring-on") {
        await setSelectedDeviceTypesFeature("monitoring", true);
        return;
    }
    if (action === "type:batch-monitoring-off") {
        await setSelectedDeviceTypesFeature("monitoring", false);
        return;
    }
    if (action === "type:batch-config-on") {
        await setSelectedDeviceTypesFeature("config", true);
        return;
    }
    if (action === "type:batch-config-off") {
        await setSelectedDeviceTypesFeature("config", false);
        return;
    }
    if (action === "type:batch-credentials-on") {
        await setSelectedDeviceTypesFeature("credentials", true);
        return;
    }
    if (action === "type:batch-credentials-off") {
        await setSelectedDeviceTypesFeature("credentials", false);
        return;
    }
    if (action.startsWith("scan:add:")) {
        const ip = action.slice("scan:add:".length).trim();
        await openCreateDeviceFromScanRow(ip);
        return;
    }
    if (action.startsWith("scan:edit:")) {
        const ip = action.slice("scan:edit:".length).trim();
        await openEditDeviceFromScanRow(ip);
        return;
    }
    if (action.startsWith("device:add-type:")) {
        const deviceType = action.slice("device:add-type:".length).trim();
        await openDeviceModal(null, { mode: "create", deviceType });
        return;
    }
    if (action === "device:add") {
        await openDeviceModal(null, { mode: "create" });
        return;
    }
    if (action === "device:batch-delete") {
        await deleteSelectedInventoryDevices();
        return;
    }
    if (action === "device:batch-notify-on") {
        await setSelectedInventoryNotify(true);
        return;
    }
    if (action === "device:batch-notify-off") {
        await setSelectedInventoryNotify(false);
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
    if (action.startsWith("tool:")) {
        await openNetworkToolModal(action, device);
        return;
    }
    if (action.startsWith("remote:")) {
        const remoteActionKey = decodeURIComponent(action.slice("remote:".length) || "");
        await runRemoteAction(device, remoteActionKey);
    }
});

topMenuPanel.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action]");
    if (!button || button.disabled) {
        return;
    }
    const action = String(button.dataset.action || "");
    closeTopMenu();
    try {
        if (action === "view:dashboard") {
            applyMonitoringTreeFilters({ typeCode: "dashboard", status: "" });
            renderSection();
            return;
        }
        if (action === "view:global") {
            applyMonitoringTreeFilters({ typeCode: "global", status: "" });
            renderSection();
            return;
        }
        if (action.startsWith("view:type:")) {
            applyMonitoringTreeFilters({ typeCode: action.slice("view:type:".length), status: "" });
            renderSection();
            return;
        }
        if (action === "view:inventory") {
            state.currentSection = "inventory";
            renderSection();
            return;
        }
        if (action === "view:device-types") {
            state.currentSection = "device_types";
            renderSection();
            return;
        }
        if (action.startsWith("menu:modules:open:")) {
            const encoded = action.slice("menu:modules:open:".length);
            const route = decodeURIComponent(encoded || "");
            if (route) {
                window.location.assign(route);
            }
            return;
        }
        const commonMenuActions = window.NMPSharedMenu?.buildCommonActions?.({
            navigatePortal: () => redirectToPortal(),
            openWebServerSettingsModal,
            downloadHttpsRootCertificate,
            openModal,
            escapeHtml,
            normalizeErrorMessage,
            applySettingsPatch,
            getAppVersionText: () => String(document.getElementById("app-version").textContent || "-"),
            aboutText: "Interface web alignee au runtime desktop.",
        }) || {};

        const menuActions = {
            "menu:logs:global": () => openLogsModal({ title: "Journaux", heading: "Journal global des changements", limit: 200 }),
            "menu:monitoring": () => openMonitoringSettingsModal(),
            "menu:notifications": () => openNotificationSettingsModal(),
            "menu:monitoring-notifications": () => openMonitoringNotificationSettingsModal(),
            "menu:config-open-local": () => openConfigLibraryExplorerModal(),
            "menu:config-open-backup": () => openMonitoringStorageExplorerModal(),
            "menu:config-storage": () => openConfigStorageSettingsModal(),
            "menu:config-sync": () => runConfigStorageAction("/config-storage/sync-now"),
            "menu:scan": () => openNetworkScanModal(),
            ...commonMenuActions,
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
    } catch (error) {
        openModal(
            "Action indisponible",
            `<p class="error-text">${escapeHtml(normalizeErrorMessage(error.message))}</p>`,
            { width: "min(560px, calc(100vw - 40px))" },
        );
    }
});

document.addEventListener("click", (event) => {
    if (!contextMenu.hidden && !contextMenu.contains(event.target)) {
        closeContextMenu();
    }
    if (!topMenuPanel.hidden && !topMenuPanel.contains(event.target) && !event.target.closest(".menu-btn")) {
        closeTopMenu();
    }
    if (profileMenuPanel && !profileMenuPanel.hidden && !profileMenuPanel.contains(event.target) && !event.target.closest("#profile-menu-button")) {
        closeProfileMenu();
    }
});

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
        closeContextMenu();
        closeTopMenu();
        closeProfileMenu();
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
    if (profileMenuPanel && !profileMenuPanel.hidden) {
        closeProfileMenu();
    }
}, true);

appModalClose.addEventListener("click", () => {
    closeActiveModal();
});

appModalBackdrop.addEventListener("click", () => {
    closeActiveModal();
});

appModalBody.addEventListener("click", async (event) => {
    const scanAddButton = event.target?.closest?.("[data-scan-add-ip]");
    if (scanAddButton && !scanAddButton.disabled) {
        const ip = String(scanAddButton.getAttribute("data-scan-add-ip") || "").trim();
        openCreateDeviceFromScanRow(ip).catch((error) => {
            const feedback = document.getElementById("modal-network-scan-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        });
        return;
    }
    const scanEditButton = event.target?.closest?.("[data-scan-edit-ip]");
    if (scanEditButton && !scanEditButton.disabled) {
        const ip = String(scanEditButton.getAttribute("data-scan-edit-ip") || "").trim();
        openEditDeviceFromScanRow(ip).catch((error) => {
            const feedback = document.getElementById("modal-network-scan-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        });
        return;
    }
    const typesHeader = event.target?.closest?.("th[data-types-col]");
    if (typesHeader) {
        const col = String(typesHeader.getAttribute("data-types-col") || "").trim();
        if (col) {
            if (state.deviceTypesModalSort.column === col) {
                state.deviceTypesModalSort.direction = state.deviceTypesModalSort.direction === "asc" ? "desc" : "asc";
            } else {
                state.deviceTypesModalSort.column = col;
                state.deviceTypesModalSort.direction = "asc";
            }
            applyDeviceTypesModalFilterSort();
        }
        return;
    }
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
    if (action === "config-storage:explore") {
        await openConfigLibraryExplorerModal();
        return;
    }
    if (action === "config-storage:test") {
        const form = actionButton.closest("form");
        if (form instanceof HTMLFormElement) {
            await testConfigStorageSettings(form);
        }
        return;
    }
    if (action === "config-library:refresh") {
        await refreshConfigLibraryExplorer();
        return;
    }
    if (action === "config-library:download") {
        const feedback = document.getElementById("modal-config-library-feedback");
        if (feedback) {
            feedback.textContent = "Telechargement...";
        }
        try {
            await downloadConfigLibraryFile(actionButton.dataset.fileId || "");
            if (feedback) {
                feedback.textContent = "Telechargement lance.";
            }
        } catch (error) {
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return;
    }
    if (action === "config-file:download") {
        const feedback = document.getElementById("modal-config-library-feedback")
            || document.getElementById("modal-config-files-feedback");
        if (feedback) {
            feedback.textContent = "Telechargement...";
        }
        try {
            await downloadConfigLibraryFile(actionButton.dataset.fileId || "");
            if (feedback) {
                feedback.textContent = "Telechargement lance.";
            }
        } catch (error) {
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return;
    }
    if (action === "config-file:delete") {
        const feedback = document.getElementById("modal-config-library-feedback")
            || document.getElementById("modal-config-files-feedback");
        try {
            const deleted = await deleteConfigFile(actionButton.dataset.fileId || "", actionButton.dataset.fileName || "");
            if (!deleted) {
                return;
            }
            if (feedback) {
                feedback.textContent = "Fichier supprime.";
            }
            if (document.getElementById("config-library-body")) {
                await refreshConfigLibraryExplorer();
            }
            if (document.getElementById("config-files-body")) {
                await refreshConfigFilesManagerModal();
            }
        } catch (error) {
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return;
    }
    if (action === "storage-explorer:refresh") {
        await reloadStorageExplorerModal();
        return;
    }
    if (action === "storage-explorer:up") {
        await reloadStorageExplorerModal(state.storageExplorer.parentPath);
        return;
    }
    if (action === "storage-explorer:enter") {
        await reloadStorageExplorerModal(actionButton.dataset.path || "");
        return;
    }
    if (action === "storage-explorer:mkdir") {
        const feedback = document.getElementById("storage-explorer-feedback");
        try {
            await createStorageExplorerFolder();
        } catch (error) {
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return;
    }
    if (action === "storage-explorer:upload") {
        const input = document.getElementById("storage-explorer-upload-input");
        if (input instanceof HTMLInputElement) {
            input.value = "";
            input.click();
        }
        return;
    }
    if (action === "storage-explorer:download") {
        const feedback = document.getElementById("storage-explorer-feedback");
        try {
            await downloadStorageExplorerItem(actionButton.dataset.path || "");
            if (feedback) {
                feedback.textContent = "Telechargement lance.";
            }
        } catch (error) {
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return;
    }
    if (action === "storage-explorer:delete") {
        const feedback = document.getElementById("storage-explorer-feedback");
        try {
            await deleteStorageExplorerItem(actionButton.dataset.path || "", actionButton.dataset.itemName || "");
        } catch (error) {
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return;
    }
    if (action === "device-password:reveal-form") {
        const form = actionButton.closest("form");
        const feedback = document.getElementById("modal-device-feedback") || inventoryFeedback;
        await revealDevicePasswordIntoForm(actionButton, form, feedback);
        return;
    }
    if (action === "watermark:pick-file") {
        try {
            await pickWatermarkSourceIntoEditor();
        } catch (error) {
            const feedback = document.getElementById("modal-watermark-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return;
    }
    if (action === "rdp:launch-open") {
        const device = resolveRemoteDesktopLaunchDevice();
        closeModal();
        if (!device) {
            inventoryFeedback.textContent = "Equipement introuvable pour la prise en main Remote Desktop.";
            return;
        }
        try {
            const mode = await openRemoteDesktopShortcut(device);
            if (mode === "prompted") {
                inventoryFeedback.textContent = "Boite de dialogue ouverte: choisir Ouvrir ou Enregistrer.";
            } else if (mode === "server_download") {
                inventoryFeedback.textContent = "Raccourci .rdp transmis au navigateur (ouverture selon politique de securite du poste).";
            } else if (mode === "downloaded") {
                inventoryFeedback.textContent = "Fichier .rdp telecharge. Ouvrir le fichier depuis la barre de telechargement.";
            } else {
                inventoryFeedback.textContent = "Impossible de lancer Remote Desktop depuis le navigateur.";
            }
        } catch (error) {
            inventoryFeedback.textContent = normalizeErrorMessage(error.message);
        }
        return;
    }
    if (action === "rdp:launch-save") {
        const device = resolveRemoteDesktopLaunchDevice();
        closeModal();
        if (!device) {
            inventoryFeedback.textContent = "Equipement introuvable pour l'export Remote Desktop.";
            return;
        }
        try {
            const mode = await saveRemoteDesktopShortcutAs(device);
            if (mode === "saved_as") {
                inventoryFeedback.textContent = "Fichier .rdp enregistre a l'emplacement choisi.";
            } else if (mode === "cancelled") {
                inventoryFeedback.textContent = "Enregistrement annule.";
            } else if (mode === "prompted") {
                inventoryFeedback.textContent = "Boite de dialogue ouverte: choisir Enregistrer sous.";
            } else {
                inventoryFeedback.textContent = "Fichier .rdp telecharge.";
            }
        } catch (error) {
            inventoryFeedback.textContent = normalizeErrorMessage(error.message);
        }
        return;
    }
    if (action === "network-tool:stop") {
        if (state.networkToolAbortController) {
            state.networkToolAbortController.abort();
        }
        return;
    }
    if (action === "network-scan:stop") {
        if (state.networkScanAbortController) {
            state.networkScanAbortController.abort();
        }
        return;
    }
    if (action === "device-import:refresh-preview") {
        const form = actionButton.closest("form");
        if (!(form instanceof HTMLFormElement)) {
            return;
        }
        refreshDeviceImportWizardPreviewFromForm(form).catch((error) => {
            const feedback = document.getElementById("modal-device-import-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        });
        return;
    }
    const typeCode = String(actionButton.dataset.typeCode || "");
    if (action === "types:back") {
        returnFromTypeSchemaEditor().catch((error) => {
            const feedback = document.getElementById("modal-device-type-schema-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        });
        return;
    }
    if (action === "types:plugins:set-default") {
        event.preventDefault();
        event.stopPropagation();
        const editor = state.typeSchemaEditor;
        if (!editor) {
            return;
        }
        const actionKey = String(actionButton.dataset.actionKey || "").trim().toLowerCase();
        if (!actionKey) {
            return;
        }
        typeSchemaSetDefaultActionForSelectedOs(editor, actionKey);
        typeSchemaEnsureActionDoubleClickField(editor);
        typeSchemaReindexSorts(editor);
        renderDeviceTypeSchemaEditor();
        return;
    }
    if (action === "types:field:add") {
        const editor = state.typeSchemaEditor;
        if (!editor) {
            return;
        }
        const feedback = document.getElementById("modal-device-type-schema-feedback");
        const outcome = typeSchemaStartCustomFieldEditor(editor);
        if (!outcome.ok) {
            if (feedback) {
                feedback.textContent = outcome.message || "Ouverture editeur champ impossible.";
            }
            return;
        }
        if (feedback) {
            feedback.textContent = "";
        }
        renderDeviceTypeSchemaEditor();
        return;
    }
    if (action === "types:field:edit") {
        const editor = state.typeSchemaEditor;
        if (!editor) {
            return;
        }
        const feedback = document.getElementById("modal-device-type-schema-feedback");
        const fieldKey = String(actionButton.dataset.fieldKey || "").trim();
        const outcome = typeSchemaStartCustomFieldEditor(editor, fieldKey);
        if (!outcome.ok) {
            if (feedback) {
                feedback.textContent = outcome.message || "Ouverture editeur champ impossible.";
            }
            return;
        }
        if (feedback) {
            feedback.textContent = "";
        }
        renderDeviceTypeSchemaEditor();
        return;
    }
    if (action === "types:field:delete") {
        const editor = state.typeSchemaEditor;
        if (!editor) {
            return;
        }
        const feedback = document.getElementById("modal-device-type-schema-feedback");
        const fieldKey = String(actionButton.dataset.fieldKey || "").trim();
        const usageCount = typeSchemaCustomFieldUsageCount(editor, fieldKey);
        if (usageCount > 0) {
            const confirmed = window.confirm(
                `Ce champ contient des valeurs sur ${usageCount} equipement(s).\n\n`
                + "Le retrait masque ce champ mais conserve les donnees existantes.\n"
                + "Continuer ?",
            );
            if (!confirmed) {
                return;
            }
        }
        const outcome = typeSchemaDeleteCustomField(editor, fieldKey);
        if (!outcome.ok) {
            if (feedback) {
                feedback.textContent = outcome.message || "Suppression du champ impossible.";
            }
            return;
        }
        if (feedback) {
            feedback.textContent = "";
        }
        renderDeviceTypeSchemaEditor();
        return;
    }
    if (action === "types:field:cancel") {
        const editor = state.typeSchemaEditor;
        if (!editor) {
            return;
        }
        typeSchemaCancelCustomFieldEditor(editor);
        renderDeviceTypeSchemaEditor();
        return;
    }
    if (action === "types:field:save") {
        const editor = state.typeSchemaEditor;
        if (!editor) {
            return;
        }
        const feedback = document.getElementById("modal-device-type-schema-feedback");
        const labelInput = document.getElementById("type-schema-field-label");
        const kindSelect = document.getElementById("type-schema-field-kind");
        const requiredCheckbox = document.getElementById("type-schema-field-required");
        const showTableCheckbox = document.getElementById("type-schema-field-show-table");
        const optionsInput = document.getElementById("type-schema-field-options");
        const defaultInput = document.getElementById("type-schema-field-default");
        if (
            !(labelInput instanceof HTMLInputElement)
            || !(kindSelect instanceof HTMLSelectElement)
            || !(requiredCheckbox instanceof HTMLInputElement)
            || !(showTableCheckbox instanceof HTMLInputElement)
            || !(optionsInput instanceof HTMLInputElement)
            || !(defaultInput instanceof HTMLInputElement)
        ) {
            if (feedback) {
                feedback.textContent = "Editeur champ introuvable.";
            }
            return;
        }
        const outcome = typeSchemaSaveCustomFieldEditor(editor, {
            label: labelInput.value,
            field_kind: kindSelect.value,
            required: requiredCheckbox.checked,
            show_in_table: showTableCheckbox.checked,
            options: optionsInput.value,
            default_value: defaultInput.value,
        });
        if (!outcome.ok) {
            if (feedback) {
                feedback.textContent = outcome.message || "Enregistrement du champ impossible.";
            }
            return;
        }
        if (feedback) {
            feedback.textContent = "";
        }
        renderDeviceTypeSchemaEditor();
        return;
    }
    if (action === "types:add") {
        openCreateDeviceTypeEditorModal();
        return;
    }
    if (action === "types:os:add") {
        const editor = state.typeSchemaEditor;
        if (!editor) {
            return;
        }
        const feedback = document.getElementById("modal-device-type-schema-feedback");
        const value = window.prompt("Nom du nouvel OS", "");
        if (value == null) {
            return;
        }
        const outcome = typeSchemaAddOsOption(editor, value);
        if (!outcome.ok) {
            if (feedback) {
                feedback.textContent = outcome.message || "Ajout OS impossible.";
            }
            return;
        }
        if (feedback) {
            feedback.textContent = "";
        }
        renderDeviceTypeSchemaEditor();
        return;
    }
    if (action === "types:os:select") {
        const editor = state.typeSchemaEditor;
        if (!editor) {
            return;
        }
        const label = String(actionButton.dataset.osLabel || "").trim();
        if (!label) {
            return;
        }
        editor.selectedOs = label;
        renderDeviceTypeSchemaEditor();
        return;
    }
    if (action === "types:os:edit") {
        const editor = state.typeSchemaEditor;
        if (!editor) {
            return;
        }
        const feedback = document.getElementById("modal-device-type-schema-feedback");
        const oldLabel = String(actionButton.dataset.osLabel || "").trim();
        if (!oldLabel) {
            return;
        }
        const renamed = window.prompt("Nouveau nom OS", oldLabel);
        if (renamed == null) {
            return;
        }
        const outcome = typeSchemaRenameOsOption(editor, oldLabel, renamed);
        if (!outcome.ok) {
            if (feedback) {
                feedback.textContent = outcome.message || "Renommage OS impossible.";
            }
            return;
        }
        if (feedback) {
            feedback.textContent = "";
        }
        renderDeviceTypeSchemaEditor();
        return;
    }
    if (action === "types:os:delete") {
        const editor = state.typeSchemaEditor;
        if (!editor) {
            return;
        }
        const feedback = document.getElementById("modal-device-type-schema-feedback");
        const label = String(actionButton.dataset.osLabel || "").trim();
        const outcome = typeSchemaDeleteOsOption(editor, label);
        if (!outcome.ok) {
            if (feedback) {
                feedback.textContent = outcome.message || "Suppression OS impossible.";
            }
            return;
        }
        if (feedback) {
            feedback.textContent = "";
        }
        renderDeviceTypeSchemaEditor();
        return;
    }
    if (action === "types:edit" && typeCode) {
        openDeviceTypeEditorModal(typeCode, {}).catch((error) => {
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

appModalBody.addEventListener("input", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) {
        return;
    }
    if (state.typeSchemaEditor && target.matches('input[name="type_schema_label"]')) {
        state.typeSchemaEditor.typeLabel = String(target.value || "").trim();
        return;
    }
    if (target.id === "modal-device-types-search") {
        applyDeviceTypesModalFilterSort();
    }
});

appModalBody.addEventListener("change", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) {
        return;
    }
    if (target instanceof HTMLSelectElement && target.id === "storage-explorer-root") {
        state.storageExplorer.rootId = String(target.value || "");
        reloadStorageExplorerModal("").catch((error) => {
            const feedback = document.getElementById("storage-explorer-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        });
        return;
    }
    if (target instanceof HTMLInputElement && target.id === "storage-explorer-upload-input") {
        const picked = target.files && target.files.length ? target.files[0] : null;
        uploadStorageExplorerFile(picked).catch((error) => {
            const feedback = document.getElementById("storage-explorer-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        });
        return;
    }
    if (target.matches('input[name="smtp_auth_enabled"]')) {
        const form = target.closest("form");
        if (form instanceof HTMLFormElement) {
            const authFields = form.querySelector("[data-smtp-auth-fields]");
            if (authFields instanceof HTMLElement && target instanceof HTMLInputElement) {
                authFields.hidden = !target.checked;
            }
            const passwordInput = form.querySelector('input[name="smtp_password"]');
            if (passwordInput instanceof HTMLInputElement) {
                if (target instanceof HTMLInputElement && !target.checked) {
                    passwordInput.value = "";
                }
            }
        }
        return;
    }
    if (target.matches('input[name="use_tls"]')) {
        const form = target.closest("form");
        if (form instanceof HTMLFormElement) {
            const portSelector = form.querySelector('select[name="smtp_port"]');
            if (portSelector instanceof HTMLSelectElement && target instanceof HTMLInputElement && target.checked) {
                portSelector.value = "587";
            }
        }
        return;
    }
    if (target.matches('select[name="device_import_sheet"]')) {
        const form = target.closest("form");
        if (!(form instanceof HTMLFormElement)) {
            return;
        }
        refreshDeviceImportWizardPreviewFromForm(form).catch((error) => {
            const feedback = document.getElementById("modal-device-import-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        });
        return;
    }
    if (target.matches('select[name="device_import_header_mode"]')) {
        const form = target.closest("form");
        if (!(form instanceof HTMLFormElement)) {
            return;
        }
        const headerMode = normalizeImportHeaderMode(target.value);
        const rowInput = form.querySelector('input[name="device_import_header_row"]');
        if (rowInput instanceof HTMLInputElement) {
            rowInput.disabled = headerMode !== "manual";
            if (headerMode !== "manual") {
                rowInput.value = String(normalizeImportHeaderRowNumber(state.deviceImportDraft?.preview?.detectedHeaderRowNumber || 1));
            }
        }
        refreshDeviceImportWizardPreviewFromForm(form).catch((error) => {
            const feedback = document.getElementById("modal-device-import-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        });
        return;
    }
    if (target.matches('input[name="device_import_header_row"]')) {
        const form = target.closest("form");
        if (!(form instanceof HTMLFormElement)) {
            return;
        }
        const headerMode = _collectDeviceImportHeaderModeFromForm(form);
        if (headerMode !== "manual") {
            return;
        }
        refreshDeviceImportWizardPreviewFromForm(form).catch((error) => {
            const feedback = document.getElementById("modal-device-import-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        });
        return;
    }
    if (target.matches('select[name="device_import_target"]')) {
        const row = target.closest("tr");
        const customInput = row?.querySelector?.('input[name="device_import_custom"]');
        if (customInput instanceof HTMLInputElement) {
            const isCustom = String(target.value || "").trim() === "custom";
            customInput.disabled = !isCustom;
            customInput.style.display = isCustom ? "" : "none";
            if (!isCustom) {
                customInput.value = "";
            }
        }
        return;
    }
    const editor = state.typeSchemaEditor;
    if (editor) {
        if (target.matches('input[name="type_schema_monitoring_enabled"]')) {
            editor.monitoringEnabled = Boolean(target.checked);
            typeSchemaEnsureCoreFields(editor);
            typeSchemaEnsureActionDoubleClickField(editor);
            typeSchemaReindexSorts(editor);
            renderDeviceTypeSchemaEditor();
            return;
        }
        if (target.matches('input[name="type_schema_config_backups_enabled"]')) {
            editor.configBackupsEnabled = Boolean(target.checked);
            typeSchemaEnsureCoreFields(editor);
            typeSchemaEnsureActionDoubleClickField(editor);
            typeSchemaReindexSorts(editor);
            renderDeviceTypeSchemaEditor();
            return;
        }
        if (target.matches('input[name="type_schema_credentials_enabled"]')) {
            const nextEnabled = Boolean(target.checked);
            if (nextEnabled) {
                editor.credentialsEnabled = true;
                editor.purgeTypeCredentialsOnSave = null;
                typeSchemaEnsureCoreFields(editor);
                typeSchemaEnsureActionDoubleClickField(editor);
                typeSchemaReindexSorts(editor);
                renderDeviceTypeSchemaEditor();
                return;
            }
            if (editor.initialCredentialsEnabled) {
                (async () => {
                    const hasAnyStoredCredentials = await typeHasStoredDeviceCredentials(editor.typeCode);
                    if (hasAnyStoredCredentials) {
                        const purgeChosen = window.confirm(
                            `Gestion des identifiants desactivee pour "${editor.typeCode}".\n\nOK: supprimer les identifiants deja enregistres\nAnnuler: conserver les identifiants en base`,
                        );
                        editor.purgeTypeCredentialsOnSave = Boolean(purgeChosen);
                    } else {
                        editor.purgeTypeCredentialsOnSave = false;
                    }
                    editor.credentialsEnabled = false;
                    typeSchemaEnsureCoreFields(editor);
                    typeSchemaEnsureActionDoubleClickField(editor);
                    typeSchemaReindexSorts(editor);
                    renderDeviceTypeSchemaEditor();
                })().catch((error) => {
                    const feedback = document.getElementById("modal-device-type-schema-feedback");
                    if (feedback) {
                        feedback.textContent = normalizeErrorMessage(error.message);
                    }
                    editor.credentialsEnabled = true;
                    target.checked = true;
                });
                return;
            }
            editor.credentialsEnabled = false;
            editor.purgeTypeCredentialsOnSave = false;
            typeSchemaEnsureCoreFields(editor);
            typeSchemaEnsureActionDoubleClickField(editor);
            typeSchemaReindexSorts(editor);
            renderDeviceTypeSchemaEditor();
            return;
        }
        if (target.matches('input[data-action="types:field:toggle-table"]') && target instanceof HTMLInputElement) {
            const fieldKey = String(target.dataset.fieldKey || "").trim();
            const field = typeSchemaFieldByKey(editor, fieldKey);
            if (field) {
                field.show_in_table = target.checked;
                if (editor.fieldEditor?.key && String(editor.fieldEditor.key || "").trim() === fieldKey) {
                    editor.fieldEditor.show_in_table = target.checked;
                }
            }
            renderDeviceTypeSchemaEditor();
            return;
        }
        if (target.id === "type-schema-field-kind" && target instanceof HTMLSelectElement) {
            if (editor.fieldEditor && typeof editor.fieldEditor === "object") {
                editor.fieldEditor.field_kind = typeSchemaNormalizeFieldKind(target.value);
            }
            const optionsWrap = document.getElementById("type-schema-field-options-wrap");
            if (optionsWrap instanceof HTMLElement) {
                optionsWrap.hidden = typeSchemaNormalizeFieldKind(target.value) !== "choice";
            }
            return;
        }
    }
    const networkScanForm = target.closest("#modal-network-scan-form");
    if (networkScanForm instanceof HTMLFormElement) {
        const name = String(target.getAttribute("name") || "").trim();
        if (name === "scan_mode") {
            syncNetworkScanMode(networkScanForm);
            return;
        }
        if (name === "scan_advanced") {
            syncNetworkScanAdvanced(networkScanForm);
            return;
        }
    }
});

appModalBody.addEventListener("keydown", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
        return;
    }
    if (!state.typeSchemaEditor) {
        return;
    }
});

appModalBody.addEventListener("dragstart", (event) => {
    const editor = state.typeSchemaEditor;
    if (!editor) {
        return;
    }
    const target = event.target instanceof Element ? event.target : null;
    if (!target) {
        return;
    }
    if (target.closest(".type-schema-default-btn")) {
        state.typeSchemaDrag = null;
        return;
    }
    const pluginTile = target.closest("[data-schema-plugin-key]");
    if (pluginTile instanceof HTMLElement) {
        const pluginKey = String(pluginTile.getAttribute("data-schema-plugin-key") || "").trim().toLowerCase();
        if (!pluginKey) {
            return;
        }
        state.typeSchemaDrag = { kind: "plugin", key: pluginKey };
        if (event.dataTransfer) {
            event.dataTransfer.effectAllowed = "copy";
            event.dataTransfer.setData("text/plain", `plugin:${pluginKey}`);
        }
        return;
    }
    const actionTile = target.closest("[data-schema-action-key]");
    if (actionTile instanceof HTMLElement) {
        const actionKey = String(actionTile.getAttribute("data-schema-action-key") || "").trim().toLowerCase();
        if (!actionKey) {
            return;
        }
        state.typeSchemaDrag = { kind: "action", key: actionKey };
        actionTile.classList.add("dragging");
        if (event.dataTransfer) {
            event.dataTransfer.effectAllowed = "move";
            event.dataTransfer.setData("text/plain", `action:${actionKey}`);
        }
    }
});

appModalBody.addEventListener("dragover", (event) => {
    const editor = state.typeSchemaEditor;
    const drag = state.typeSchemaDrag;
    if (!editor || !drag) {
        return;
    }
    const target = event.target instanceof Element ? event.target : null;
    if (!target) {
        return;
    }
    const dropZone = target.closest("#type-schema-drop-zone");
    const removeZone = target.closest("#type-schema-remove-zone");
    clearTypeSchemaDragVisuals();
    if (dropZone) {
        event.preventDefault();
        if (dropZone instanceof HTMLElement) {
            dropZone.classList.add("is-drop-target");
        }
        return;
    }
    if (removeZone && drag.kind === "action") {
        event.preventDefault();
        if (removeZone instanceof HTMLElement) {
            removeZone.classList.add("is-drop-target");
        }
    }
});

appModalBody.addEventListener("drop", (event) => {
    const editor = state.typeSchemaEditor;
    const drag = state.typeSchemaDrag;
    if (!editor || !drag) {
        return;
    }
    const target = event.target instanceof Element ? event.target : null;
    if (!target) {
        return;
    }
    const dropZone = target.closest("#type-schema-drop-zone");
    const removeZone = target.closest("#type-schema-remove-zone");
    if (dropZone) {
        event.preventDefault();
        if (drag.kind === "plugin") {
            typeSchemaApplyPluginBlock(editor, drag.key);
            renderDeviceTypeSchemaEditor();
        }
        if (drag.kind === "action") {
            typeSchemaReorderActionByPosition(editor, drag.key, event.clientX);
            renderDeviceTypeSchemaEditor();
        }
    } else if (removeZone && drag.kind === "action") {
        event.preventDefault();
        typeSchemaRemoveActionForSelectedOs(editor, drag.key);
        renderDeviceTypeSchemaEditor();
    }
    clearTypeSchemaDragVisuals();
    state.typeSchemaDrag = null;
});

appModalBody.addEventListener("dragend", () => {
    clearTypeSchemaDragVisuals();
    state.typeSchemaDrag = null;
});

appModalBody.addEventListener("contextmenu", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) {
        return;
    }
    const row = target.closest("tr[data-scan-ip]");
    if (!row) {
        return;
    }
    const ip = String(row.getAttribute("data-scan-ip") || "").trim();
    const scanRow = scanRowByIp(ip);
    if (!scanRow) {
        return;
    }
    event.preventDefault();
    event.stopPropagation();
    closeTopMenu();
    openNetworkScanContextMenu(event.clientX, event.clientY, scanRow);
});

if (inventoryBody) {
    inventoryBody.addEventListener("click", async (event) => {
        const target = event.target;
        if (!(target instanceof Element)) {
            return;
        }
        if (target.closest("[data-tree-select-row]")) {
            closeContextMenu();
            return;
        }
        const row = target.closest("tr[data-device-key]");
        if (!row) {
            return;
        }
        const rowKey = String(row.getAttribute("data-device-key") || "").trim();
        if (!rowKey) {
            return;
        }
        const item = inventoryRows().find((entry) => deviceKey(entry) === rowKey);
        if (!item) {
            return;
        }
        const actionButton = target.closest("[data-row-action]");
        state.selectedDeviceKey = rowKey;
        closeInventoryEditMode();
        closeContextMenu();
        closeTopMenu();
        renderInventoryDetail();
        if (actionButton) {
            event.preventDefault();
            event.stopPropagation();
            const action = String(actionButton.getAttribute("data-row-action") || "").trim();
            if (action === "reveal_password") {
                await openDevicePasswordRevealModal(item);
                return;
            }
            if (action === "edit") {
                await openDeviceModal(item, { mode: "edit" });
                return;
            }
            if (action === "delete") {
                await deleteDevice(item);
                return;
            }
        }
        await ensureInventorySideData(item);
    });

    inventoryBody.addEventListener("dblclick", async (event) => {
        const target = event.target;
        if (!(target instanceof Element)) {
            return;
        }
        if (target.closest("[data-tree-select-row]")) {
            return;
        }
        if (target.closest("[data-row-action]")) {
            return;
        }
        const row = target.closest("tr[data-device-key]");
        if (!row) {
            return;
        }
        const rowKey = String(row.getAttribute("data-device-key") || "").trim();
        if (!rowKey) {
            return;
        }
        const item = inventoryRows().find((entry) => deviceKey(entry) === rowKey);
        if (!item) {
            return;
        }
        state.selectedDeviceKey = rowKey;
        closeTopMenu();
        renderInventoryDetail();
        await runDeviceDoubleClickAction(item);
    });

    inventoryBody.addEventListener("contextmenu", (event) => {
        const target = event.target;
        if (!(target instanceof Element)) {
            return;
        }
        const row = target.closest("tr[data-device-key]");
        if (!row) {
            return;
        }
        const rowKey = String(row.getAttribute("data-device-key") || "").trim();
        if (!rowKey) {
            return;
        }
        const item = inventoryRows().find((entry) => deviceKey(entry) === rowKey);
        if (!item) {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        const selectedRows = selectedInventoryRowsIncluding(item);
        if (selectedRows.length) {
            closeTopMenu();
            renderInventoryDetail();
            openInventoryBatchContextMenu(event.clientX, event.clientY, selectedRows);
            return;
        }
        state.selectedDeviceKey = rowKey;
        closeInventoryEditMode();
        closeTopMenu();
        renderInventoryDetail();
        openContextMenu(event.clientX, event.clientY, item).catch((error) => {
            inventoryFeedback.textContent = normalizeErrorMessage(error.message);
        });
    });

    inventoryBody.addEventListener("mousedown", (event) => {
        const target = event.target;
        if (!(target instanceof Element)) {
            return;
        }
        if (!target.closest("tr[data-device-key]")) {
            return;
        }
        if (target.closest("[data-tree-select-row]")) {
            return;
        }
        if (event.button !== 0) {
            return;
        }
        closeContextMenu();
    });
}

if (inventoryEditForm) {
    inventoryEditForm.addEventListener("click", async (event) => {
        const actionButton = event.target?.closest?.('[data-action="device-password:reveal-form"]');
        if (!actionButton || actionButton.disabled) {
            return;
        }
        event.preventDefault();
        await revealDevicePasswordIntoForm(actionButton, inventoryEditForm, inventoryFormFeedback);
    });
}

bindHeaderSort(devicesHead, {
    sortState: state.supervisionSort,
    columnAttr: "col",
    onChanged: () => {
        if (state.snapshot) {
            renderDevices(state.snapshot);
        }
    },
});

bindHeaderSort(inventoryHead, {
    sortState: state.inventorySort,
    columnAttr: "col",
    onChanged: async () => {
        renderInventoryDetail();
        const selected = getSelectedDevice();
        if (selected) {
            await ensureInventorySideData(selected);
        }
    },
});

appModalBody.addEventListener("submit", async (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) {
        return;
    }
    event.preventDefault();
    try {
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
        if (form.id === "modal-monitoring-notification-form") {
            await submitMonitoringNotificationSettings(form);
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
        if (form.id === "modal-network-tool-form") {
            await submitNetworkToolModal(form);
            return;
        }
        if (form.id === "modal-network-scan-form") {
            await submitNetworkScanModal(form);
            return;
        }
        if (form.id === "modal-device-type-schema-form") {
            await submitDeviceTypeSchemaForm(form);
            return;
        }
        if (form.id === "modal-device-import-form") {
            await submitDeviceImportWizard(form);
            return;
        }
        if (form.id === "modal-watermark-form") {
            await submitWatermarkEditorForm(form);
            return;
        }
    } catch (error) {
        const feedbackByFormId = {
            "modal-notification-form": "modal-notification-feedback",
            "modal-monitoring-notification-form": "modal-monitoring-notification-feedback",
            "modal-settings-form": "modal-settings-feedback",
            "modal-webserver-form": "modal-webserver-feedback",
            "modal-config-storage-form": "modal-config-storage-feedback",
            "modal-device-form": "modal-device-feedback",
            "modal-network-tool-form": "modal-network-tool-feedback",
            "modal-network-scan-form": "modal-scan-feedback",
            "modal-device-type-schema-form": "modal-device-types-feedback",
            "modal-device-import-form": "modal-device-import-feedback",
            "modal-watermark-form": "modal-watermark-feedback",
        };
        const feedbackId = feedbackByFormId[String(form.id || "")] || "";
        const feedback = feedbackId ? document.getElementById(feedbackId) : null;
        if (feedback instanceof HTMLElement) {
            feedback.textContent = normalizeErrorMessage(error?.message || String(error || "Erreur inconnue."));
            return;
        }
        inventoryFeedback.textContent = normalizeErrorMessage(error?.message || String(error || "Erreur inconnue."));
    }
});

appModalBody.addEventListener("input", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLInputElement)) {
        return;
    }
    const draft = state.watermarkEditorDraft;
    if (!draft) {
        return;
    }
    if (target.id === "modal-watermark-opacity") {
        draft.opacity = clampNumber(Number(target.value || 16) / 100.0, 0.05, 1.0, 0.16);
        renderWatermarkEditorPreview();
        return;
    }
    if (target.id === "modal-watermark-offset-x") {
        draft.offsetX = Math.round(clampNumber(target.value, -300, 300, 0));
        renderWatermarkEditorPreview();
        return;
    }
    if (target.id === "modal-watermark-offset-y") {
        draft.offsetY = Math.round(clampNumber(target.value, -220, 220, 0));
        renderWatermarkEditorPreview();
        return;
    }
    if (target.id === "modal-watermark-zoom") {
        draft.zoomPercent = Math.round(clampNumber(target.value, 40, 220, 100));
        renderWatermarkEditorPreview();
    }
});

appModalBody.addEventListener("change", async (event) => {
    const target = event.target;
    const configStorageForm = target?.closest?.("#modal-config-storage-form");
    if (configStorageForm instanceof HTMLFormElement) {
        if (String(target?.getAttribute?.("name") || "") === "config_storage_mode") {
            syncConfigStorageModeUi(configStorageForm);
        }
        return;
    }
    const form = target?.closest?.("#modal-device-form");
    if (form && target instanceof HTMLElement) {
        const watched = ["device_type", "device_subtype", "action_double_click"];
        if (!watched.includes(String(target.getAttribute("name") || "").trim())) {
            return;
        }
        const customData = {};
        for (const [key, value] of new window.FormData(form).entries()) {
            if (String(key).startsWith("custom:")) {
                customData[String(key).slice(7)] = String(value || "");
            }
        }
        form.dataset.initialCustomData = JSON.stringify(customData);
        form.dataset.initialSubtype = String(form.querySelector('[name="device_subtype"]')?.value || "");
        form.dataset.initialAction = String(form.querySelector('[name="action_double_click"]')?.value || "");
        form.dataset.initialTeamviewer = String(form.querySelector('[name="id_Teamviewer"]')?.value || "");
        form.dataset.initialWebUrl = composeDeviceWebUrlFromParts(
            form.querySelector('[name="web_url"]')?.value || "",
            form.querySelector('[name="web_url_port"]')?.value || "",
            form.querySelector('[name="ip"]')?.value || "",
        );
        form.dataset.initialSshUser = String(form.querySelector('[name="ssh_user"]')?.value || "");
        form.dataset.initialDeviceLogin = String(form.querySelector('[name="device_login"]')?.value || "");
        if (form.dataset.mode === "create") {
            form.dataset.deviceType = String(form.querySelector('[name="device_type"]')?.value || "").trim();
        }
        const selectedType = String(form.dataset.deviceType || "").trim();
        if (selectedType) {
            await ensureDeviceTypeSchema(selectedType);
        }
        renderDeviceModalDynamicFields(form);
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
    const mergedCustomData = mode === "edit" && device
        ? mergeCustomDataMaps(device.custom_data, customData)
        : customData;
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
        web_url: composeDeviceWebUrlFromParts(
            formData.get("web_url"),
            formData.get("web_url_port"),
            formData.get("ip"),
        ),
        ssh_user: String(formData.get("ssh_user") || "").trim(),
        custom_data: mergedCustomData,
        notify: inventoryNotify.checked,
        version_token: mode === "edit" ? String(device?.version_token || inventoryEditForm.dataset.versionToken || "") : "",
    };
    if (inventoryEditForm.querySelector('[name="device_login"]')) {
        payload.device_login = String(formData.get("device_login") || "").trim();
    }
    if (inventoryEditForm.querySelector('[name="device_password"]')) {
        payload.device_password = String(formData.get("device_password") ?? "");
    }
    if (mode === "edit" && Object.prototype.hasOwnProperty.call(payload, "device_password") && payload.device_password === "") {
        delete payload.device_password;
    }

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
