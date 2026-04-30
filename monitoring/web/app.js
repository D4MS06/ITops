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
    notify: "Notifications",
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
    "action_double_click",
    "action_default_by_os",
]);
const TYPE_SCHEMA_CORE_FIELDS = {
    name: { label: "Nom", field_kind: "text", required: true, options: "", default_value: "" },
    description: { label: "Description", field_kind: "text", required: false, options: "", default_value: "" },
    type: { label: "OS", field_kind: "choice", required: true, options: PLATFORM_OPTIONS.join(","), default_value: PLATFORM_OPTIONS[0] },
    ip: { label: "IP", field_kind: "ip", required: true, options: "", default_value: "" },
};
const TYPE_SCHEMA_PLUGIN_BLOCKS = [
    { key: "ssh", title: "SSH", badge: "SSH" },
    { key: "teamviewer", title: "TeamViewer", badge: "TV" },
    { key: "remote_desktop", title: "Remote Desktop", badge: "RDP" },
    { key: "web", title: "Web", badge: "WEB" },
];

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
    networkToolAbortController: null,
    networkScanAbortController: null,
    deviceTypesModalSort: { column: "label", direction: "asc" },
    networkScanRows: [],
    networkScanContextIp: "",
    moduleAccess: [],
    moduleAccessLoaded: false,
    typeSchemaEditor: null,
    typeSchemaDrag: null,
    deviceImportDraft: null,
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
const logoutButton = document.getElementById("logout-button");
const deviceFilter = document.getElementById("device-filter");
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
const runtimeStrip = document.querySelector(".runtime-strip");
const menuModules = document.getElementById("menu-modules");
const menuSupervision = document.getElementById("menu-supervision");
const menuEquipments = document.getElementById("menu-equipments");
const menuTools = document.getElementById("menu-tools");
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
const inventoryImportButton = document.getElementById("inventory-import-button");
const inventoryExportButton = document.getElementById("inventory-export-button");
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
const sessionProfileLabel = document.getElementById("session-profile-label");
let inventoryTreeView = null;
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
    },
}) || null;
const topMenuController = window.NMPSharedUi?.shell?.createTopMenuController?.({
    state,
    panel: topMenuPanel,
    buttons: [menuModules, menuSupervision, menuEquipments, menuTools, menuDisplay, menuHelp],
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
    const label = String(state.sessionLabel || state.sessionSubject || "-").trim() || "-";
    const roleLabel = String(state.sessionRoleLabel || state.sessionRoleCode || "").trim();
    const icon = roleIcon(state.sessionRoleCode);
    sessionProfileLabel.textContent = roleLabel ? `${icon} ${label} (${roleLabel})` : `${icon} ${label}`;
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
        throw new Error(normalizeErrorMessage(detail));
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
        return;
    }
    state.sessionSubject = "";
    state.sessionLabel = "";
    state.sessionRoleCode = "";
    state.sessionRoleLabel = "";
    state.moduleAccess = [];
    state.moduleAccessLoaded = false;
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

function bindHeaderSort(headElement, options = {}) {
    const shared = window.NMPSharedUi?.tableTools?.bindHeaderSort;
    if (typeof shared !== "function") {
        return;
    }
    shared(headElement, options);
}

class MonitoringInventoryTreeView extends (window.NMPSharedUi?.treeView?.SharedTreeView || class {}) {
    constructor() {
        super({
            headElement: inventoryHead,
            bodyElement: inventoryBody,
            searchInput: inventorySearch,
            sortState: state.inventorySort,
            renderHead: false,
            manageSortBinding: false,
            manageSearchBinding: false,
            searchThreshold: 5,
            emptyMessage: "Aucun equipement",
            getRows: () => inventorySourceRows(),
            searchText: (item) => [
                item.device_type,
                typeLabel(item.device_type),
                item.name,
                item.ip,
                item.description,
                item.web_url,
                item.ssh_user,
                item.has_saved_config ? "oui" : "non",
            ].join(" "),
            compareRows: (column, direction, left, right) => compareByColumn(column, direction, left, right),
            getRowKey: (item) => deviceKey(item),
            getRowClassName: (item) => (deviceKey(item) === state.selectedDeviceKey ? "is-selected" : ""),
            getRowAttributes: (item) => ({
                "data-device-key": deviceKey(item),
            }),
            renderRowCells: (item) => {
                const showCfg = this._showCfgColumn;
                return `
                    <td>${escapeHtml(typeLabel(item.device_type))}</td>
                    <td>${escapeHtml(item.name)}</td>
                    <td>${escapeHtml(item.ip)}</td>
                    <td>${item.notify ? "Oui" : "Non"}</td>
                    ${showCfg ? `<td>${item.has_saved_config ? "&#10003;" : "-"}</td>` : ""}
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
            },
        });
        this._showCfgColumn = false;
    }

    render() {
        const rows = inventorySourceRows();
        const filterType = String(inventoryTypeFilter.value || "").trim();
        this._showCfgColumn = filterType
            ? typeHasConfigSupport(filterType)
            : rows.some((item) => typeHasConfigSupport(item.device_type));
        const cfgHead = document.querySelector('#inventory-head th[data-col="config_saved"]');
        if (cfgHead) {
            cfgHead.hidden = !this._showCfgColumn;
        }
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

function formatDetailValue(value) {
    const normalized = String(value ?? "").trim();
    return normalized || "-";
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
    state.networkScanContextIp = "";
}

function closeTopMenu() {
    if (topMenuController) {
        topMenuController.close();
        return;
    }
    const sharedCloseTopMenu = window.NMPSharedUi?.closeTopMenu;
    if (typeof sharedCloseTopMenu === "function") {
        sharedCloseTopMenu(state, topMenuPanel, [menuModules, menuSupervision, menuEquipments, menuTools, menuDisplay, menuHelp]);
    }
}

function openModal(title, bodyMarkup, options = {}) {
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
    state.configManagerDeviceKey = "";
    state.typeSchemaEditor = null;
    state.typeSchemaDrag = null;
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
    return key === "remote_desktop" || key === "ssh";
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
    if (builtin === "remote_desktop" && ip) {
        return `ms-rd:full%20address=s:${encodeURIComponent(ip)}`;
    }
    return "";
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
    const content = buildRdpFileContent(device);
    const filename = `${sanitizeFilePart(device?.name, "remote")}_${sanitizeFilePart(ip, "host")}.rdp`;
    downloadTextFile(content, filename, "application/rdp");
    const wantsOpen = window.confirm("Fichier .rdp telecharge. Ouvrir la connexion Remote Desktop maintenant ?");
    if (wantsOpen) {
        const url = builtinActionUrl(device, "remote_desktop");
        if (url) {
            window.location.href = url;
        }
    }
}

function escapeAttribute(value) {
    return escapeHtml(String(value || "")).replaceAll("`", "&#96;");
}

async function runBuiltinAction(device, builtin) {
    if (builtin === "remote_desktop") {
        await downloadRemoteDesktopShortcut(device);
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
        return !["name", "ip", "description", "id_teamviewer", "type", "device_subtype", "action_double_click", "action_default_by_os", "web_url", "ssh_user", "notify"].includes(key);
    });
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
    const mustChangePassword = Boolean(status?.first_start_required) || !Boolean(status?.has_admin_password);
    authTitle.textContent = "Connexion";
    authHelp.textContent = mustChangePassword
        ? "Premiere connexion: utilise le compte sa puis definis un nouveau mot de passe."
        : "Connecte-toi avec ton compte pour ouvrir le dashboard web.";
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
    setLiveStatus("Deconnecte");
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
}

function redirectToPortal() {
    window.location.replace("/");
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
            state.currentSection = "supervision";
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
    const totalAll = Number(summary.total || 0);
    const onlineAll = Number(summary.online || 0);
    const offlineAll = Number(summary.offline || 0);
    const idleAll = Math.max(0, totalAll - onlineAll - offlineAll);
    const cards = [
        {
            title: "Equipements",
            value: `${onlineAll}/${totalAll}`,
            sub: "En ligne / total",
            stats: { online: onlineAll, offline: offlineAll, idle: idleAll },
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
            value: `${Number(item.online || 0)}/${Number(item.total || 0)}`,
            sub: `En ligne / total (${item.running ? "actif" : "arrete"})`,
            stats: {
                online: Number(item.online || 0),
                offline: Number(item.offline || 0),
                idle: Number(item.idle || 0),
            },
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
                ${card.stats ? `<span>Inactif: <span>${escapeHtml(card.stats.idle)}</span></span>` : "<span></span>"}
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
    const tbody = document.getElementById("devices-body");
    tbody.innerHTML = "";
    const rows = visibleRowsForCurrentView(snapshot).map((item) => resolveDeviceRecord(item));
    const showCfg = state.currentView === "dashboard" || state.currentView === "global"
        ? rows.some((item) => typeHasConfigSupport(item.device_type))
        : typeHasConfigSupport(state.currentView);
    const cfgHead = document.querySelector('#devices-head th[data-col="config_saved"]');
    if (cfgHead) {
        cfgHead.hidden = !showCfg;
    }
    updateSearchVisibility(deviceFilter, rows.length, 5);
    const query = (deviceFilter.value || "").trim().toLowerCase();
    filterAndSortRows(rows, {
        query,
        searchText: (item) => [
            item.device_type,
            item.name,
            item.ip,
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
                <td><span class="status-badge ${statusClass(item.status)}">${escapeHtml(localizeStatus(item.status || "idle"))}</span></td>
                ${showCfg ? `<td>${device.has_saved_config ? "✓" : "-"}</td>` : ""}
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
    const cfgHead = document.querySelector('#inventory-head th[data-col="config_saved"]');
    if (cfgHead) {
        cfgHead.hidden = !showCfg;
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
        ["Notifications", device.notify ? "Oui" : "Non"],
        ["TeamViewer", device.id_Teamviewer],
        ["Sous-type", device.device_subtype],
        ["Double-clic", device.action_double_click],
        ["URL web", device.web_url],
        ["Utilisateur SSH", device.ssh_user],
    ];
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

function createFieldMarkup({ key, label, value, multiline = false, wide = false, inputType = "text" }) {
    const sharedFieldMarkup = window.NMPSharedUi?.createFieldMarkup;
    if (typeof sharedFieldMarkup === "function") {
        return sharedFieldMarkup({
            key,
            label,
            value,
            multiline,
            wide,
            inputType,
            escapeHtml,
        });
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
        return createFieldMarkup({ key: name, label, value: currentValue, inputType: "url" });
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
                <span>Notifications actives</span>
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
            ${createModalActionsMarkup({
                buttons: [{ preset: "cancel" }, { preset: "save" }],
            })}
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
            ${createModalActionsMarkup({
                buttons: [{ preset: "cancel" }, { preset: "save" }],
            })}
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
        };
    } else {
        delete byKey.ip;
    }

    const ordered = [];
    for (const key of ["name", "description", "type", "ip"]) {
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
    const editor = {
        createMode,
        typeCode: code,
        typeLabel: String(overrides.label || meta.label || "").trim(),
        monitoringEnabled: Boolean(overrides.monitoring_enabled ?? meta.monitoring_enabled ?? true),
        configBackupsEnabled: Boolean(overrides.config_backups_enabled ?? meta.config_backups_enabled ?? false),
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
                    <h3>Champs personnalises</h3>
                    ${createIconActionButtonMarkup({
                        icon: "add",
                        action: "types:field:add",
                        title: "Ajouter un champ",
                    })}
                </div>
                <p class="muted">Ajoute des champs sans code (texte, IP, URL, liste deroulante).</p>
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
    const fieldOptionsWrap = document.getElementById("type-schema-field-options-wrap");
    const fieldOptionsInput = document.getElementById("type-schema-field-options");
    const fieldDefaultInput = document.getElementById("type-schema-field-default");
    if (
        fieldEditorPanel instanceof HTMLElement
        && fieldEditorTitle instanceof HTMLElement
        && fieldLabelInput instanceof HTMLInputElement
        && fieldKindSelect instanceof HTMLSelectElement
        && fieldRequiredCheckbox instanceof HTMLInputElement
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
    state.typeSchemaEditor = createTypeSchemaEditorState(code, schema, overrides);
    state.typeSchemaDrag = null;
    openModal(`Edition type: ${state.typeSchemaEditor.typeLabel || code}`, buildDeviceTypeSchemaEditorMarkup(), {
        width: "min(1120px, calc(100vw - 40px))",
    });
    renderDeviceTypeSchemaEditor();
}

function openCreateDeviceTypeEditorModal() {
    state.typeSchemaEditor = createTypeSchemaEditorState("", { fields: [], actions: [] }, { create_mode: true });
    state.typeSchemaDrag = null;
    openModal("Ajouter un type d'equipement", buildDeviceTypeSchemaEditorMarkup(), {
        width: "min(1120px, calc(100vw - 40px))",
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
    const rows = (types || []).map((item) => {
        const code = String(item.code || "");
        const canDelete = !Boolean(item.is_system);
        const monitoringEnabled = Boolean(item.monitoring_enabled);
        const configEnabled = Boolean(item.config_backups_enabled);
        const label = String(item.label || code || "");
        return `
            <tr
                data-type-code="${escapeAttribute(code)}"
                data-type-label="${escapeAttribute(label)}"
                data-monitoring-enabled="${monitoringEnabled ? "1" : "0"}"
                data-config-backups-enabled="${configEnabled ? "1" : "0"}"
            >
                <td>${escapeHtml(label)}</td>
                <td class="cell-center">${monitoringEnabled ? "Oui" : "Non"}</td>
                <td class="cell-center">${configEnabled ? "Oui" : "Non"}</td>
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
                        disabled: !canDelete,
                    })}
                </td>
            </tr>
        `;
    }).join("");
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
                    <thead>
                    <tr>
                        <th data-types-col="label">Libelle</th>
                        <th data-types-col="monitoring_enabled">Monitoring</th>
                        <th data-types-col="config_backups_enabled">Configs</th>
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
    state.typeSchemaEditor = null;
    state.typeSchemaDrag = null;
    const types = await requestJson("/device-types");
    openModal("Types d'equipements", buildDeviceTypesSettingsMarkup(types), {
        width: "min(980px, calc(100vw - 40px))",
    });
    applyDeviceTypesModalFilterSort();
}

function applyDeviceTypesModalFilterSort() {
    const tbody = document.getElementById("device-types-body");
    if (!tbody) {
        return;
    }
    const searchInput = document.getElementById("modal-device-types-search");
    const rows = Array.from(tbody.querySelectorAll("tr[data-type-code]"));
    updateSearchVisibility(searchInput instanceof HTMLInputElement ? searchInput : null, rows.length, 5);
    const query = String(searchInput?.value || "").trim().toLowerCase();
    const sortColumn = String(state.deviceTypesModalSort.column || "label");
    const direction = state.deviceTypesModalSort.direction === "desc" ? -1 : 1;
    const byText = (left, right) => String(left || "").localeCompare(String(right || ""), undefined, { sensitivity: "base" }) * direction;
    const rowValue = (row, col) => {
        if (col === "label") {
            return String(row.dataset.typeLabel || "");
        }
        if (col === "monitoring_enabled" || col === "config_backups_enabled") {
            return String(row.dataset[col === "monitoring_enabled" ? "monitoringEnabled" : "configBackupsEnabled"] || "0");
        }
        return "";
    };
    rows.sort((left, right) => byText(rowValue(left, sortColumn), rowValue(right, sortColumn)));
    rows.forEach((row) => {
        const text = String(row.dataset.typeLabel || "").toLowerCase();
        row.hidden = Boolean(query) && !text.includes(query);
        tbody.appendChild(row);
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
    const teamviewerInput = form.querySelector('[name="id_Teamviewer"]');
    const webUrlInput = form.querySelector('[name="web_url"]');
    const sshUserInput = form.querySelector('[name="ssh_user"]');

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
        dynamic.push(createFieldMarkup({
            key: "web_url",
            label: fieldLabel("web_url"),
            value: String(webUrlInput?.value || form.dataset.initialWebUrl || ""),
        }));
    }
    if (selectedAction === "ssh" && hasField(selectedType, "ssh_user")) {
        dynamic.push(createFieldMarkup({
            key: "ssh_user",
            label: fieldLabel("ssh_user"),
            value: String(sshUserInput?.value || form.dataset.initialSshUser || ""),
        }));
    }

    const customFields = customFieldDefinitions(selectedType);
    dynamic.push(...customFields.map((field) => createSchemaDynamicFieldMarkup(
        field,
        String(customData[field.field_key] || ""),
        { keyPrefix: "custom:" },
    )));

    container.innerHTML = `<div class="modal-grid">${dynamic.join("")}</div>`;
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
    const moduleRows = (Array.isArray(state.moduleAccess) ? state.moduleAccess : [])
        .filter((row) => Boolean(row?.granted))
        .filter((row) => !["monitoring", "admin", "users_admin"].includes(String(row?.code || "").toLowerCase()));
    const moduleEntries = [
        { label: "Portail", action: "menu:portal" },
        ...moduleRows.map((row) => {
            const routePath = String(row?.route_path || "").trim();
            const isAvailable = Boolean(row?.granted && row?.is_active && routePath);
            return {
                label: String(row?.label || row?.code || "Module"),
                action: routePath ? `menu:modules:open:${encodeURIComponent(routePath)}` : "menu:modules:open:",
                disabled: !isAvailable,
            };
        }),
    ];
    const typeLogs = (state.deviceTypes || [])
        .filter((item) => Boolean(item.monitoring_enabled))
        .map((item) => ({
            label: `Journal ${item.label}...`,
            action: `menu:logs:type:${item.code}`,
        }));
    const configState = state.configStorageState || {};
    const canOpenBackup = Boolean(configState.can_open_backup_folder);
    return {
        modules: moduleEntries,
        supervision: [
            { label: "Notifications (email + popup)...", action: "menu:notifications" },
            { label: "Parametres de monitoring...", action: "menu:monitoring" },
            ...(sharedDefs.supervision || []),
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
        tools: [
            { label: "Scan reseau...", action: "menu:scan" },
        ],
        display: [
            ...(sharedDefs.display || []),
            {
                label: "Indicateurs de statut",
                items: [
                    { label: "Badge coche / croix", action: "menu:status-badge" },
                    { label: "Pastille moderne", action: "menu:status-dot" },
                ],
            },
            { label: "Image de fond...", action: "menu:watermark", disabled: true },
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
            buttons: [menuModules, menuSupervision, menuEquipments, menuTools, menuDisplay, menuHelp],
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
    [menuModules, menuSupervision, menuEquipments, menuTools, menuDisplay, menuHelp].forEach((entry) => {
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
            let disabled = !status.ok;
            let hint = isDefault ? "Defaut" : "";
            if (!status.ok) {
                hint = status.hint || hint;
            }
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
            version_token: String(device.version_token || ""),
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
    const deletePath = String(device.version_token || "").trim()
        ? `/devices/${encodeURIComponent(device.device_type)}/${encodeURIComponent(device.id)}?version_token=${encodeURIComponent(String(device.version_token || ""))}`
        : `/devices/${encodeURIComponent(device.device_type)}/${encodeURIComponent(device.id)}`;
    await requestJson(deletePath, {
        method: "DELETE",
    });
    await loadInventory();
    renderInventoryDetail();
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
            version_token: String(form.dataset.versionToken || ""),
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
    if (mode !== "create") {
        const existing = findInventoryDevice(editType, deviceId);
        if (existing) {
            payload.custom_data = mergeCustomDataMaps(existing.custom_data, payload.custom_data);
            payload.version_token = String(existing.version_token || payload.version_token || "");
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
            device_name: String(device.name || ""),
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
    { value: "notify", label: "Notifications" },
    { value: "custom", label: "Champ personnalise" },
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

function _buildDeviceImportSourceTable(headers = [], rows = []) {
    const normalizedHeaders = Array.isArray(headers) ? headers : [];
    const normalizedRows = Array.isArray(rows) ? rows : [];
    if (!normalizedHeaders.length) {
        return '<div class="muted">Aucune colonne detectee.</div>';
    }
    const headCells = normalizedHeaders.map((header) => `<th>${escapeHtml(header)}</th>`).join("");
    const bodyRows = normalizedRows.length
        ? normalizedRows.map((row) => {
            const cells = normalizedHeaders.map((_header, index) => `<td>${escapeHtml(String(row?.[index] || ""))}</td>`).join("");
            return `<tr>${cells}</tr>`;
        }).join("")
        : `<tr><td colspan="${normalizedHeaders.length}" class="muted">Aucune ligne de previsualisation.</td></tr>`;
    return `
        <div class="inventory-table-wrap">
            <table class="inventory-table">
                <thead><tr>${headCells}</tr></thead>
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
                    <input name="device_import_custom" value="${escapeAttribute(selectedCustom)}" placeholder="Ex: site" ${selectedTarget === "custom" ? "" : "disabled"}>
                </td>
            </tr>
        `;
    }).join("");
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
            </tr>
        `).join("")
        : '<tr><td colspan="4" class="muted">Aucune ligne exploitable avec ce mapping.</td></tr>';
    return `
        <div class="inventory-table-wrap">
            <table class="inventory-table">
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Nom</th>
                        <th>IP</th>
                        <th>Description</th>
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
    const issues = Array.isArray(draft?.preview?.issues) ? draft.preview.issues : [];
    const issueText = issues.length
        ? `<p class="error-text">Alertes: ${escapeHtml(issues.slice(0, 3).join(" | "))}${issues.length > 3 ? " ..." : ""}</p>`
        : `<p class="muted">Alerte: aucune</p>`;
    const mappingRows = _buildDeviceImportMappingRows(
        sourceHeaders,
        draft?.preview?.effectiveMapping || [],
        draft?.mapping || [],
    );
    return `
        <form id="modal-device-import-form" class="modal-form">
            <section class="modal-section">
                <h3>Fichier</h3>
                <p class="muted">${escapeHtml(String(draft?.file?.name || ""))}</p>
                <p class="muted">Colonnes detectees: ${Number(draft?.preview?.detectedColumns || 0)} | Lignes detectees: ${Number(draft?.preview?.detectedRows || 0)}</p>
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
        mapping: _normalizeDeviceImportMappingRows(draft.mapping || []),
        preview: {
            rows: Array.isArray(draft.preview?.rows) ? draft.preview.rows : [],
            detectedRows: Number(draft.preview?.detectedRows || 0),
            detectedColumns: Number(draft.preview?.detectedColumns || 0),
            issues: Array.isArray(draft.preview?.issues) ? draft.preview.issues : [],
            sourceHeaders: Array.isArray(draft.preview?.sourceHeaders) ? draft.preview.sourceHeaders : [],
            sourceRowsPreview: Array.isArray(draft.preview?.sourceRowsPreview) ? draft.preview.sourceRowsPreview : [],
            effectiveMapping: _normalizeDeviceImportMappingRows(draft.preview?.effectiveMapping || []),
        },
    };
    openModal(
        "Import equipements",
        buildDeviceImportWizardMarkup(state.deviceImportDraft),
        { width: "min(1160px, calc(100vw - 36px))" },
    );
}

async function previewDeviceInventoryImportFromFile(file, defaultDeviceType, columnMappings = []) {
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
        }),
        responseMapper: (payload) => ({
            rows: Array.isArray(payload?.rows) ? payload.rows : [],
            detectedRows: Number(payload?.detected_rows || 0),
            detectedColumns: Number(payload?.detected_columns || 0),
            issues: Array.isArray(payload?.issues) ? payload.issues : [],
            sourceHeaders: Array.isArray(payload?.source_headers) ? payload.source_headers : [],
            sourceRowsPreview: Array.isArray(payload?.source_rows_preview) ? payload.source_rows_preview : [],
            effectiveMapping: _normalizeDeviceImportMappingRows(payload?.effective_mapping || []),
        }),
    });
}

async function applyDeviceInventoryImportFromFile(file, defaultDeviceType, columnMappings = []) {
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
    const feedback = document.getElementById("modal-device-import-feedback");
    if (feedback) {
        feedback.textContent = "Recalcul de l'apercu...";
    }
    const preview = await previewDeviceInventoryImportFromFile(
        state.deviceImportDraft.file,
        state.deviceImportDraft.defaultDeviceType,
        mapping,
    );
    openDeviceImportWizardModal({
        file: state.deviceImportDraft.file,
        defaultDeviceType: state.deviceImportDraft.defaultDeviceType,
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
    if (feedback) {
        feedback.textContent = "Validation de l'apercu...";
    }
    const preview = await previewDeviceInventoryImportFromFile(
        state.deviceImportDraft.file,
        state.deviceImportDraft.defaultDeviceType,
        mapping,
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
    );
    await Promise.all([loadInventory(), refreshSnapshot()]);
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
    const defaultDeviceType = String(inventoryTypeFilter?.value || "").trim().toLowerCase();
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

async function confirmTypeDisableSideEffects(typeCode, payload, feedback) {
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
                `Desactiver le monitoring pour "${typeCode}" ?\n\nLes logs de ce type seront supprimes.`,
            );
            if (!confirmed) {
                if (feedback) {
                    feedback.textContent = "Operation annulee.";
                }
                return false;
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
                return false;
            }
        }
    }
    return true;
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
    if (!payload.label) {
        feedback.textContent = "Libelle requis.";
        return;
    }
    if (!editor.createMode) {
        const canContinue = await confirmTypeDisableSideEffects(editor.typeCode, payload, feedback);
        if (!canContinue) {
            return;
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
    await loadDeviceTypes();
    await refreshSnapshot();
    state.typeSchemaEditor = null;
    state.typeSchemaDrag = null;
    await openDeviceTypesModal();
    const listFeedback = document.getElementById("modal-device-types-feedback");
    if (listFeedback) {
        listFeedback.textContent = `${editor.typeLabel || editor.typeCode} enregistre.`;
    }
}

async function deleteDeviceTypeRow(typeCode) {
    const feedback = document.getElementById("modal-device-types-feedback");
    const meta = typeMeta(typeCode);
    const label = String(meta?.label || typeCode || "").trim();
    if (!window.confirm(`Supprimer le type "${label}" ?`)) {
        return;
    }
    feedback.textContent = `Suppression ${label}...`;
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
    await loadDeviceTypes();
    await refreshSnapshot();
    feedback.textContent = `Type ${label} supprime.`;
    await openDeviceTypesModal();
}

function renderSection() {
    const summary = state.snapshot?.summary || {};
    const runningAny = Boolean(summary.running_any);
    renderNavigation(state.snapshot?.types || []);
    const showDashboardHeaderTitle = state.currentSection === "supervision" && state.currentView === "dashboard";
    if (topbarTitle instanceof HTMLElement) {
        topbarTitle.hidden = !showDashboardHeaderTitle;
    }
    if (topbar instanceof HTMLElement) {
        topbar.classList.toggle("topbar-title-hidden", !showDashboardHeaderTitle);
    }

    if (state.currentSection === "inventory") {
        detailPanel.classList.remove("detail-focus-mode");
        cardsGrid.hidden = true;
        monitoringToolbar.hidden = true;
        placeholderPanel.hidden = true;
        detailPanel.hidden = false;
        supervisionSection.hidden = true;
        inventorySection.hidden = false;
        inventorySection.classList.add("management-mode");
        runtimeStrip.hidden = true;
        detailTitle.textContent = "Gestion des equipements";
        renderInventoryFilters();
        renderInventoryDetail();
        return;
    }

    const dashboardMode = state.currentView === "dashboard";
    cardsGrid.hidden = !dashboardMode;
    monitoringToolbar.hidden = !dashboardMode;
    supervisionSection.hidden = false;
    inventorySection.hidden = true;
    inventorySection.classList.remove("management-mode");
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

function enablePasswordChangeMode() {
    authForm.dataset.forcePasswordChange = "1";
    authSubmit.textContent = "Se connecter et changer le mot de passe";
    newPasswordField.hidden = false;
    newPasswordInput.required = true;
    confirmPasswordField.hidden = false;
    confirmPasswordInput.required = true;
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
    ]);
    showDashboard();
    connectWebSocket();
    refreshWorkspaceData().catch(() => {
        setLiveStatus("Chargement initial partiel");
    });
}

authForm.addEventListener("submit", (event) => {
    event.preventDefault();
    redirectToPortal();
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
    clearSessionState();
    renderSessionProfile();
    state.snapshot = null;
    state.inventory = [];
    state.deviceTypes = [];
    state.deviceSchemas = {};
    state.selectedDeviceKey = "";
    state.currentView = "dashboard";
    state.currentSection = "supervision";
    applyUiConfig(null);
    redirectToPortal();
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

menuModules.addEventListener("click", () => openTopMenu(menuModules, "modules").catch(() => {}));
menuSupervision.addEventListener("click", () => openTopMenu(menuSupervision, "supervision").catch(() => {}));
menuEquipments.addEventListener("click", () => openTopMenu(menuEquipments, "equipments").catch(() => {}));
menuTools.addEventListener("click", () => openTopMenu(menuTools, "tools").catch(() => {}));
menuDisplay.addEventListener("click", () => openTopMenu(menuDisplay, "display").catch(() => {}));
menuHelp.addEventListener("click", () => openTopMenu(menuHelp, "help").catch(() => {}));

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
    closeContextMenu();
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
            "menu:types": () => openDeviceTypesModal(),
            "menu:config-open-local": () => runConfigStorageAction("/config-storage/open-local-folder", { openClientPath: true }),
            "menu:config-open-backup": () => runConfigStorageAction("/config-storage/open-backup-folder", { openClientPath: true }),
            "menu:config-storage": () => openConfigStorageSettingsModal(),
            "menu:config-sync": () => runConfigStorageAction("/config-storage/sync-now"),
            "menu:scan": () => openNetworkScanModal(),
            "menu:status-badge": () => applySettingsPatch({ status_indicator_style: "badge" }),
            "menu:status-dot": () => applySettingsPatch({ status_indicator_style: "dot" }),
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
        openDeviceTypesModal().catch((error) => {
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
        const optionsInput = document.getElementById("type-schema-field-options");
        const defaultInput = document.getElementById("type-schema-field-default");
        if (
            !(labelInput instanceof HTMLInputElement)
            || !(kindSelect instanceof HTMLSelectElement)
            || !(requiredCheckbox instanceof HTMLInputElement)
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
        openDeviceTypeEditorModal(typeCode).catch((error) => {
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
    if (target.matches('select[name="device_import_target"]')) {
        const row = target.closest("tr");
        const customInput = row?.querySelector?.('input[name="device_import_custom"]');
        if (customInput instanceof HTMLInputElement) {
            const isCustom = String(target.value || "").trim() === "custom";
            customInput.disabled = !isCustom;
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
    inventoryBody.addEventListener("click", async (event) => {
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
        await openDeviceModal(item, { mode: "edit" });
    });

    inventoryBody.addEventListener("contextmenu", (event) => {
        const target = event.target;
        if (!(target instanceof Element)) {
            return;
        }
        const row = target.closest("tr[data-device-key]");
        if (!row) {
            event.preventDefault();
            event.stopPropagation();
            closeTopMenu();
            openInventoryBackgroundContextMenu(event.clientX, event.clientY);
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
        if (event.button !== 0) {
            return;
        }
        closeContextMenu();
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
});

appModalBody.addEventListener("change", async (event) => {
    const target = event.target;
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
        form.dataset.initialWebUrl = String(form.querySelector('[name="web_url"]')?.value || "");
        form.dataset.initialSshUser = String(form.querySelector('[name="ssh_user"]')?.value || "");
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
        web_url: String(formData.get("web_url") || "").trim(),
        ssh_user: String(formData.get("ssh_user") || "").trim(),
        custom_data: mergedCustomData,
        notify: inventoryNotify.checked,
        version_token: mode === "edit" ? String(device?.version_token || inventoryEditForm.dataset.versionToken || "") : "",
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
    redirectToPortal();
});
