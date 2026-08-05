const state = {
    token: window.localStorage.getItem("nmp_token") || "",
    sessionSubject: "",
    sessionLabel: "",
    sessionRoleCode: "",
    sessionRoleLabel: "",
    uiConfig: null,
    openTopMenu: "",
    moduleAccess: [],
    moduleAccessLoaded: false,
    adminData: {
        modules: [],
        roles: [],
        users: [],
        services: [],
        sharedLists: [],
    },
    adminDataLoaded: {
        modules: false,
        roles: false,
        users: false,
        services: false,
        sharedLists: false,
    },
    noCodeServiceEditor: null,
    noCodeRelationDrag: null,
    noCodeRelationConnect: null,
    noCodeRelationContextNodeCode: "",
    noCodeRelationSuppressClickUntil: 0,
    noCodeServiceEditorContext: null,
    noCodeServiceRecordContext: null,
    noCodeRelationLinksContext: null,
    noCodeRecordEditor: null,
    relationAssignmentCreate: null,
    relationAssignmentPicker: null,
    noCodeRecordViewer: null,
    noCodeSharedListEditor: null,
    noCodeSharedListItemsContext: null,
    noCodeSharedListItemEditor: null,
    noCodeSharedListsWarning: "",
    monitoringPrewarmStarted: false,
    monitoringSummary: null,
    monitoringSummaryLoaded: false,
    monitoringSummaryWebSocket: null,
    monitoringSummarySignature: "",
    portalModules: [],
    portalContextModuleCode: "",
    activeModuleMenuContext: null,
    watermarkEditorDraft: null,
    noCodeInlineMode: false,
    adminInlineMode: false,
    adminRolesSort: { column: "code", direction: "asc" },
    adminUsersSort: { column: "subject", direction: "asc" },
    noCodeServicesSort: { column: "code", direction: "asc" },
    sharedListsSort: { column: "code", direction: "asc" },
    sharedListItemsSort: { column: "code", direction: "asc" },
    storageRemoteSort: { column: "label", direction: "asc" },
    storageLocalSort: { column: "name", direction: "asc" },
    directorySort: { column: "label", direction: "asc" },
    notificationTasksSort: { column: "due_at", direction: "asc" },
    notificationTemplatesSort: { column: "label", direction: "asc" },
    notificationTasks: [],
    notificationTemplates: [],
    notificationTemplateEditor: null,
    directoryContext: null,
    directoryRecordEditor: null,
    linkedColumnsPicker: null,
    modalBackStack: [],
    modalDirty: {
        directory: false,
        services: {},
    },
    linkedRecordViewCache: {},
    storageTargets: [],
    storageMounts: [],
    storageFiles: [],
    storageExplorer: {
        roots: [],
        rootId: "",
        path: "",
        items: [],
        parentPath: "",
        rootLabel: "",
    },
    activeInlineModalHost: "",
    modalPreviousFocus: null,
    credentialRevealSessionPassword: "",
    credentialRevealUnlockUntilMs: 0,
    credentialRevealUnlockDurationSeconds: 300,
    credentialRevealUnlockTimer: null,
    revealedNoCodeRecordPasswords: {},
};

const authScreen = document.getElementById("auth-screen");
const portalPanel = document.getElementById("portal-panel");
const authTitle = document.getElementById("auth-title");
const authHelp = document.getElementById("auth-help");
const authForm = document.getElementById("auth-form");
const authSubmit = document.getElementById("auth-submit");
const usernameInput = document.getElementById("username-input");
const usernameField = usernameInput ? usernameInput.closest("label") : null;
const passwordInput = document.getElementById("password-input");
const passwordField = passwordInput ? passwordInput.closest("label") : null;
const newPasswordField = document.getElementById("new-password-field");
const newPasswordInput = document.getElementById("new-password-input");
const confirmPasswordField = document.getElementById("confirm-password-field");
const confirmPasswordInput = document.getElementById("confirm-password-input");
const authError = document.getElementById("auth-error");
const refreshButton = document.getElementById("refresh-button");
const portalSyncBadge = document.getElementById("portal-sync-badge");
const profileMenuButton = document.getElementById("profile-menu-button");
const dashboardEditButton = document.getElementById("dashboard-edit-button");
const cardsGrid = document.getElementById("cards-grid");
const menuSupervision = document.getElementById("menu-supervision");
const menuConfiguration = document.getElementById("menu-configuration");
const menuHelp = document.getElementById("menu-help");
const portalMenuBar = portalPanel?.querySelector?.(".menu-bar") || null;
const portalMenuButtons = [menuSupervision, menuConfiguration, menuHelp].filter((button) => button instanceof HTMLButtonElement);
const portalInlineModalHost = document.getElementById("portal-inline-modal-host");
const topMenuPanel = document.getElementById("top-menu-panel");
const profileMenuPanel = document.getElementById("profile-menu-panel");
const cardsContextMenu = document.getElementById("cards-context-menu");
const appModal = document.getElementById("app-modal");
const appModalBackdrop = document.getElementById("app-modal-backdrop");
const appModalPanel = document.getElementById("app-modal-panel");
const appModalTitle = document.getElementById("app-modal-title");
const appModalBody = document.getElementById("app-modal-body");
const appModalClose = document.getElementById("app-modal-close");
const appModalDefaultParent = appModal?.parentElement || null;
const appModalDefaultNextSibling = appModal?.nextSibling || null;
const sessionProfileLabel = document.getElementById("session-profile-label");
const modalController = window.NMPSharedUi?.shell?.createModalController?.({
    modal: appModal,
    titleNode: appModalTitle,
    bodyNode: appModalBody,
    panelNode: appModalPanel,
    defaultWidth: "min(860px, calc(100vw - 40px))",
    onBeforeClose: () => {
        clearWatermarkEditorDraft();
    },
}) || null;
const topMenuController = window.NMPSharedUi?.shell?.createTopMenuController?.({
    state,
    panel: topMenuPanel,
    buttons: [menuSupervision, menuConfiguration, menuHelp],
    buildMarkup: (menuKey) => topMenuMarkup(menuKey),
    onBeforeOpen: () => {
        closeCardsContextMenu();
        if (!state.activeModuleMenuContext) {
            closeModal();
        }
    },
}) || null;
let adminRolesTreeView = null;
let adminUsersTreeView = null;
let noCodeServicesTreeView = null;
let sharedListsTreeView = null;
let sharedListItemsTreeView = null;
let storageRemoteTreeView = null;
let storageLocalTreeView = null;
let directoryTreeView = null;
let notificationTasksTreeView = null;
let notificationTemplatesTreeView = null;
let portalDashboardEditor = null;
let profileMenuController = null;
let authFailureHandling = false;

function activeModuleMenuContext() {
    const context = state.activeModuleMenuContext;
    return context && typeof context === "object" ? context : null;
}

function applyPortalTopMenuLayout() {
    const layoutName = activeModuleMenuContext() ? "module" : "portal";
    const shared = window.NMPSharedMenu;
    if (shared && typeof shared.applyTopMenuLayout === "function") {
        shared.applyTopMenuLayout(portalMenuBar, layoutName);
        return;
    }
    const fallback = layoutName === "module"
        ? [{ key: "services", label: "Services" }, { key: "data", label: "Données" }, { key: "help", label: "Aide" }]
        : [{ key: "supervision", label: "Gestion" }, { key: "configuration", label: "Configuration" }, { key: "help", label: "Aide" }];
    portalMenuButtons.forEach((button, index) => {
        const entry = fallback[index];
        button.hidden = !entry;
        button.dataset.menuKey = entry?.key || "";
        if (entry) {
            button.textContent = entry.label;
        }
    });
}

function setActiveModuleMenuContext(context = null) {
    state.activeModuleMenuContext = context && typeof context === "object" ? { ...context } : null;
    closeTopMenu();
    applyPortalTopMenuLayout();
}

async function refreshActiveModuleData() {
    const context = activeModuleMenuContext();
    if (!context) {
        return;
    }
    if (context.kind === "directory") {
        await openDirectoryModuleFromPortal(context.directoryKind);
        return;
    }
    await openServiceModuleFromPortal(context.serviceCode || context.code);
}

applyPortalTopMenuLayout();

const MODULE_META = {
    monitoring: {
        title: "Monitoring reseau",
        subtitle: "Supervision, inventaire, actions reseau",
    },
    admin: {
        title: "Administration",
        subtitle: "Comptes applicatifs, roles et habilitations",
    },
    directory_agents: {
        title: "Agents",
        subtitle: "Annuaire AD synchronise",
    },
    directory_services: {
        title: "Services",
        subtitle: "OU AD synchronisees avec l'annuaire",
    },
    service_emails: {
        title: "Emails",
        subtitle: "Module systeme des comptes email prestataire",
    },
};
const SERVICE_ICON_LIBRARY = [
    { code: "", label: "Aucune" },
    { code: "copier", label: "Copieur", svg: '<rect x="22" y="34" width="52" height="34" rx="6"></rect><rect x="30" y="16" width="36" height="18" rx="3"></rect><path d="M31 68h34v12H31z"></path><path d="M33 43h30"></path><circle cx="67" cy="46" r="2"></circle>' },
    { code: "monitor", label: "Ecran", svg: '<rect x="18" y="18" width="60" height="42" rx="6"></rect><path d="M38 78h20"></path><path d="M48 60v18"></path>' },
    { code: "server", label: "Serveur", svg: '<rect x="24" y="14" width="48" height="24" rx="5"></rect><rect x="24" y="48" width="48" height="24" rx="5"></rect><path d="M34 26h14"></path><path d="M34 60h14"></path><circle cx="61" cy="26" r="2"></circle><circle cx="61" cy="60" r="2"></circle>' },
    { code: "network", label: "Reseau", svg: '<circle cx="48" cy="22" r="10"></circle><circle cx="22" cy="70" r="10"></circle><circle cx="74" cy="70" r="10"></circle><path d="M43 31L27 61"></path><path d="M53 31l16 30"></path><path d="M32 70h32"></path>' },
    { code: "key", label: "Cle", svg: '<circle cx="34" cy="48" r="14"></circle><path d="M48 48h30"></path><path d="M64 48v10"></path><path d="M74 48v8"></path>' },
    { code: "phone", label: "Telephone", svg: '<path d="M34 17h28a6 6 0 016 6v50a6 6 0 01-6 6H34a6 6 0 01-6-6V23a6 6 0 016-6z"></path><path d="M42 25h12"></path><path d="M44 70h8"></path>' },
    { code: "building", label: "Batiment", svg: '<rect x="22" y="18" width="36" height="60" rx="3"></rect><path d="M58 36h16v42"></path><path d="M32 30h4"></path><path d="M44 30h4"></path><path d="M32 44h4"></path><path d="M44 44h4"></path><path d="M32 58h4"></path><path d="M44 58h4"></path>' },
    { code: "folder", label: "Dossier", svg: '<path d="M14 30h28l8 10h32v36a6 6 0 01-6 6H20a6 6 0 01-6-6z"></path><path d="M14 40h68"></path>' },
    { code: "database", label: "Base", svg: '<ellipse cx="48" cy="24" rx="28" ry="10"></ellipse><path d="M20 24v36c0 6 13 12 28 12s28-6 28-12V24"></path><path d="M20 42c0 6 13 12 28 12s28-6 28-12"></path>' },
    { code: "app", label: "Application", svg: '<rect x="18" y="18" width="60" height="60" rx="10"></rect><path d="M34 36h28"></path><path d="M34 50h18"></path><path d="M34 64h28"></path>' },
    { code: "stock", label: "Stock", svg: '<path d="M48 14l30 16v36L48 82 18 66V30z"></path><path d="M18 30l30 16 30-16"></path><path d="M48 46v36"></path>' },
    { code: "contract", label: "Contrat", svg: '<path d="M28 14h30l12 12v56H28z"></path><path d="M58 14v12h12"></path><path d="M38 42h20"></path><path d="M38 56h20"></path><path d="M38 70h12"></path>' },
    { code: "vehicle", label: "Vehicule", svg: '<path d="M20 58l8-22h40l8 22"></path><rect x="18" y="50" width="60" height="18" rx="6"></rect><circle cx="32" cy="70" r="6"></circle><circle cx="64" cy="70" r="6"></circle><path d="M34 36l-4 14"></path><path d="M62 36l4 14"></path>' },
];
const NO_CODE_FIELD_KINDS = ["text", "ip", "url", "date", "list"];
const NO_CODE_FIELD_KIND_LABELS = {
    text: "Texte",
    ip: "IP",
    url: "URL",
    date: "Date",
    list: "Liste",
};
const NO_CODE_SERVICE_WIZARD_STEPS = [
    { value: 1, label: "Identite" },
    { value: 2, label: "Champs" },
    { value: 3, label: "Relations" },
    { value: 4, label: "Recapitulatif" },
];
const NO_CODE_CREDENTIAL_LOGIN_KEY = "device_login";
const NO_CODE_CREDENTIAL_PASSWORD_KEY = "device_password";
const NO_CODE_CREDENTIAL_FIELD_KEYS = new Set([
    NO_CODE_CREDENTIAL_LOGIN_KEY,
    NO_CODE_CREDENTIAL_PASSWORD_KEY,
]);
const NO_CODE_CREDENTIAL_LEGACY_LOGIN_KEYS = [NO_CODE_CREDENTIAL_LOGIN_KEY, "login"];
const NO_CODE_CREDENTIAL_LEGACY_PASSWORD_KEYS = [NO_CODE_CREDENTIAL_PASSWORD_KEY, "password"];
const LINKED_RECORD_VIEW_CACHE_LIMIT = 300;
const RECORD_IMPORT_CREDENTIAL_MODES = [
    { value: "preserve_on_blank", label: "Conserver si vide (recommande)" },
    { value: "overwrite", label: "Ecraser avec le fichier" },
    { value: "ignore", label: "Ignorer les identifiants du fichier" },
];
const SYSTEM_SERVICE_MODULE_CODES = ["monitoring", "directory_agents", "directory_services", "service_emails"];
const TABULAR_HEADER_MODES = [
    { value: "auto", label: "Auto-detection" },
    { value: "manual", label: "Ligne manuelle" },
    { value: "first", label: "Premiere ligne" },
];

function normalizeRecordsImportCredentialMode(value) {
    const raw = String(value || "").trim().toLowerCase();
    if (raw === "overwrite" || raw === "ignore" || raw === "preserve_on_blank") {
        return raw;
    }
    return "preserve_on_blank";
}

function normalizeTabularHeaderMode(value) {
    const raw = String(value || "").trim().toLowerCase();
    if (raw === "auto" || raw === "manual" || raw === "first") {
        return raw;
    }
    return "auto";
}

function normalizeTabularHeaderRowNumber(value) {
    const parsed = Number(value || 1);
    if (!Number.isFinite(parsed)) {
        return 1;
    }
    return Math.max(1, Math.trunc(parsed));
}

function normalizeTabularUntilRowNumber(value) {
    const parsed = Number(value || 0);
    if (!Number.isFinite(parsed)) {
        return 0;
    }
    return Math.max(0, Math.trunc(parsed));
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

function createLocalAdminStore() {
    const data = {
        modules: [],
        roles: [],
        users: [],
        services: [],
        sharedLists: [],
    };
    const loaded = {
        modules: false,
        roles: false,
        users: false,
        services: false,
        sharedLists: false,
    };
    return {
        data,
        loaded,
        invalidate(parts = []) {
            const normalized = Array.isArray(parts) && parts.length ? parts : ["modules", "roles", "users", "services", "sharedLists"];
            normalized.forEach((part) => {
                if (part === "modules") {
                    data.modules = [];
                    loaded.modules = false;
                }
                if (part === "roles") {
                    data.roles = [];
                    loaded.roles = false;
                }
                if (part === "users") {
                    data.users = [];
                    loaded.users = false;
                }
                if (part === "services") {
                    data.services = [];
                    loaded.services = false;
                }
                if (part === "sharedLists") {
                    data.sharedLists = [];
                    loaded.sharedLists = false;
                }
            });
        },
        async load(options = {}) {
            const includeModules = options.includeModules !== false;
            const includeRoles = options.includeRoles !== false;
            const includeUsers = options.includeUsers !== false;
            const includeServices = Boolean(options.includeServices);
            const includeSharedLists = Boolean(options.includeSharedLists);
            const forceRefresh = Boolean(options.forceRefresh);
            const tasks = [];
            if (includeModules && (forceRefresh || !loaded.modules)) {
                tasks.push(
                    requestJson("/admin/modules").then((rows) => {
                        data.modules = Array.isArray(rows) ? rows : [];
                        loaded.modules = true;
                    }),
                );
            }
            if (includeRoles && (forceRefresh || !loaded.roles)) {
                tasks.push(
                    requestJson("/admin/roles").then((rows) => {
                        data.roles = Array.isArray(rows) ? rows : [];
                        loaded.roles = true;
                    }),
                );
            }
            if (includeUsers && (forceRefresh || !loaded.users)) {
                tasks.push(
                    requestJson("/admin/users").then((rows) => {
                        data.users = Array.isArray(rows) ? rows : [];
                        loaded.users = true;
                    }),
                );
            }
            if (includeServices && (forceRefresh || !loaded.services)) {
                tasks.push(
                    requestJson("/admin/custom-services").then((rows) => {
                        data.services = Array.isArray(rows) ? rows : [];
                        loaded.services = true;
                    }),
                );
            }
            if (includeSharedLists && (forceRefresh || !loaded.sharedLists)) {
                tasks.push(
                    requestJson("/admin/shared-lists").then((rows) => {
                        data.sharedLists = Array.isArray(rows) ? rows : [];
                        loaded.sharedLists = true;
                    }),
                );
            }
            if (tasks.length) {
                await Promise.all(tasks);
            }
        },
    };
}

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
    if (lowered.includes("invalid credentials")) {
        return "Identifiants invalides.";
    }
    if (lowered.includes("invalid or expired session")) {
        return "Session invalide ou expiree.";
    }
    return normalized;
}

let globalDataLoadingRequests = 0;
function setGlobalDataLoading(visible) {
    const overlay = document.getElementById("global-data-loading");
    if (overlay instanceof HTMLElement) overlay.hidden = !visible;
}
async function requestJson(path, options = {}) {
    globalDataLoadingRequests += 1;
    setGlobalDataLoading(true);
    try {
        const sharedRequest = window.NMPSharedApi?.requestJson;
        if (typeof sharedRequest === "function") {
            return await sharedRequest(path, options, {
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
    } finally {
        globalDataLoadingRequests = Math.max(0, globalDataLoadingRequests - 1);
        setGlobalDataLoading(globalDataLoadingRequests > 0);
    }
}

async function handleAuthFailure() {
    if (authFailureHandling) {
        return;
    }
    authFailureHandling = true;
    persistToken("");
    clearSessionState();
    invalidateAdminData();
    renderSessionProfile();
    closeTopMenu();
    closeModal();
    closeCardsContextMenu();
    try {
        await loadAuthMode();
    } catch (_error) {
    }
    showAuth();
}

async function confirmAbortNoCodeServiceEditor() {
    const editor = state.noCodeServiceEditor;
    if (!editor) {
        return true;
    }
    const label = normalizeNoCodeText(editor.label || "ce service");
    const actionLabel = editor.mode === "edit" ? "Abandonner les modifications" : "Annuler la creation";
    return showItopsConfirm({
        title: actionLabel,
        message: `Confirmer l'abandon de ${label || "ce service"} ? Les changements non enregistres seront perdus.`,
        confirmLabel: actionLabel,
        cancelLabel: "Continuer l'edition",
        danger: true,
    });
}

const adminStore = (() => {
    const createSharedStore = window.NMPSharedAdminStore?.createAdminStore;
    if (typeof createSharedStore === "function") {
        return createSharedStore({ requestJson });
    }
    return createLocalAdminStore();
})();
state.adminData = adminStore.data;
state.adminDataLoaded = adminStore.loaded;

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
    stopPortalMonitoringSummaryRefresh();
    const sharedClear = window.NMPSharedAuth?.clearSessionContext;
    if (typeof sharedClear === "function") {
        sharedClear(state);
        state.monitoringPrewarmStarted = false;
        state.monitoringSummary = null;
        state.monitoringSummaryLoaded = false;
        state.portalModules = [];
        state.portalContextModuleCode = "";
        return;
    }
    state.sessionSubject = "";
    state.sessionLabel = "";
    state.sessionRoleCode = "";
    state.sessionRoleLabel = "";
    state.moduleAccess = [];
    state.moduleAccessLoaded = false;
    state.monitoringPrewarmStarted = false;
    state.monitoringSummary = null;
    state.monitoringSummaryLoaded = false;
    state.portalModules = [];
    state.portalContextModuleCode = "";
}

function invalidateAdminData(parts = []) {
    adminStore.invalidate(parts);
}

function showPortal() {
    authScreen.hidden = true;
    portalPanel.hidden = false;
    authScreen.style.display = "none";
    portalPanel.style.display = "";
    closeCardsContextMenu();
    document.body.dataset.screen = "dashboard";
    document.documentElement.classList.remove("auth-mode");
}

function showAuth() {
    closeTopMenu();
    closeModal();
    closeCardsContextMenu();
    portalPanel.hidden = true;
    authScreen.hidden = false;
    portalPanel.style.display = "none";
    authScreen.style.display = "";
    document.body.dataset.screen = "auth";
    document.documentElement.classList.add("auth-mode");
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

    document.getElementById("app-version").textContent = config?.app_version || "-";
}

async function loadPublicUiConfig() {
    try {
        applyUiConfig(await requestJson("/ui/auth-config", { headers: {} }));
    } catch (_error) {
        applyUiConfig(null);
    }
}

async function loadPrivateUiConfig() {
    try {
        applyUiConfig(await requestJson("/ui/config"));
    } catch (_error) {
        applyUiConfig(null);
    }
}

async function loadAuthMode() {
    const status = await requestJson("/auth/status", { headers: {} });
    const mustChangePassword = Boolean(status?.first_start_required) || !Boolean(status?.has_admin_password);
    authTitle.textContent = "Connexion";
    authHelp.textContent = mustChangePassword
        ? "Premiere connexion: utiliser le compte sa puis definir un nouveau mot de passe."
        : "Connexion requise avec un compte pour ouvrir le portail des modules.";
    authSubmit.textContent = mustChangePassword ? "Se connecter et changer le mot de passe" : "Se connecter";
    passwordInput.autocomplete = "current-password";
    usernameInput.autocomplete = "username";
    if (!String(usernameInput.value || "").trim()) {
        usernameInput.value = "sa";
    }
    if (usernameField) {
        usernameField.hidden = false;
    }
    if (passwordField) {
        passwordField.hidden = false;
    }
    usernameInput.required = true;
    passwordInput.required = true;
    newPasswordField.hidden = !mustChangePassword;
    newPasswordInput.required = mustChangePassword;
    confirmPasswordField.hidden = !mustChangePassword;
    confirmPasswordInput.required = mustChangePassword;
    authForm.dataset.mode = "login";
    authForm.dataset.forcePasswordChange = mustChangePassword ? "1" : "0";
    await loadPublicUiConfig();
    return { mustChangePassword };
}

function enablePasswordChangeMode() {
    authForm.dataset.mode = "login";
    authForm.dataset.forcePasswordChange = "1";
    authSubmit.textContent = "Se connecter et changer le mot de passe";
    if (!String(usernameInput.value || "").trim()) {
        usernameInput.value = "sa";
    }
    if (usernameField) {
        usernameField.hidden = false;
    }
    if (passwordField) {
        passwordField.hidden = false;
    }
    usernameInput.required = true;
    passwordInput.required = true;
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

async function bootstrapAndLogin(newPassword) {
    await requestJson("/auth/bootstrap", {
        method: "POST",
        body: JSON.stringify({ password: String(newPassword || "") }),
        headers: {},
    });
    await authenticate("sa", String(newPassword || ""), "");
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

async function logout() {
    try {
        if (state.token) {
            await requestJson("/auth/logout", { method: "POST" });
        }
    } catch (_error) {
    }
    persistToken("");
    clearSessionState();
    invalidateAdminData();
    renderSessionProfile();
    await loadAuthMode();
    showAuth();
}

function initProfileMenu() {
    profileMenuController = window.NMPSharedUi?.profileMenu?.createController?.({
        button: profileMenuButton,
        panel: profileMenuPanel,
        state,
        closePeers: () => {
            closeTopMenu();
            closeCardsContextMenu();
            closeModal();
        },
        getUiConfig: () => state.uiConfig,
        onThemeChanged: () => applyUiConfig(state.uiConfig),
        onDashboardEdit: () => ensurePortalDashboardEditor().toggleEditing?.(),
        onLogout: () => logout(),
        escapeHtml,
    }) || null;
}

function resolveInlineModalHost(hostKey) {
    const normalized = String(hostKey || "").trim().toLowerCase();
    if (normalized === "portal") {
        return portalInlineModalHost;
    }
    return null;
}

function setPortalServiceEditorFocusMode(enabled) {
    if (portalPanel instanceof HTMLElement) {
        portalPanel.classList.toggle("portal-service-editor-focus", Boolean(enabled));
    }
    applyPortalModuleTileVisibility();
}

function portalModuleTilesShouldCollapse() {
    return Boolean(
        portalPanel instanceof HTMLElement
        && portalPanel.classList.contains("portal-module-open")
        && !(portalPanel instanceof HTMLElement && portalPanel.classList.contains("portal-service-editor-focus"))
        && !(portalDashboardEditor && typeof portalDashboardEditor.isEditing === "function" && portalDashboardEditor.isEditing())
    );
}

function applyPortalModuleTileVisibility() {
    if (!(cardsGrid instanceof HTMLElement)) {
        return;
    }
    const collapse = portalModuleTilesShouldCollapse();
    Array.from(cardsGrid.querySelectorAll("[data-dashboard-card-id]")).forEach((card) => {
        if (!(card instanceof HTMLElement)) {
            return;
        }
        const id = String(card.dataset.dashboardCardId || card.dataset.moduleCode || "").trim().toLowerCase();
        const pinned = String(card.dataset.dashboardCardPinned || "true") === "true";
        card.classList.toggle("dashboard-card-context-hidden", collapse && !pinned);
    });
}

function exitInlineModalMode() {
    if (!(appModal instanceof HTMLElement)) {
        return;
    }
    const wasModuleInline = state.activeInlineModalHost === "portal" && Boolean(activeModuleMenuContext());
    setPortalServiceEditorFocusMode(false);
    const activeHost = resolveInlineModalHost(state.activeInlineModalHost);
    if (activeHost instanceof HTMLElement) {
        activeHost.hidden = true;
    }
    if (portalPanel instanceof HTMLElement) {
        portalPanel.classList.remove("portal-module-open");
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
    if (wasModuleInline) {
        setActiveModuleMenuContext();
    }
    applyPortalModuleTileVisibility();
}

function isNoCodeServiceNotFoundError(error) {
    return String(error?.message || error || "").trim().toLowerCase().includes("service introuvable");
}

async function refreshNoCodeServiceForRecordSave(service) {
    const code = normalizeNoCodeText(service?.code || "").toLowerCase();
    invalidateAdminData(["services"]);
    await loadAdministrationData({
        includeModules: false,
        includeRoles: false,
        includeUsers: false,
        includeServices: true,
        includeSharedLists: false,
        forceRefresh: true,
    });
    const refreshed = findNoCodeService(code);
    if (refreshed) {
        return refreshed;
    }
    const label = String(service?.label || code || "ce module").trim();
    throw new Error(`Le module « ${label} » (code : ${code || "inconnu"}) n'existe plus sur le serveur. Rechargez la page puis verifiez sa configuration.`);
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
    if (portalPanel instanceof HTMLElement && hostKey === "portal") {
        portalPanel.classList.add("portal-module-open");
    }
    applyPortalModuleTileVisibility();
    return true;
}

function isAppModalOpen() {
    return appModal instanceof HTMLElement && appModal.hidden !== true;
}

function isPortalOverlayDialogTarget(target) {
    return target instanceof Element && Boolean(target.closest(".credential-prompt-overlay, .itops-confirm-overlay"));
}

function modalFocusableElements() {
    if (!(appModalPanel instanceof HTMLElement)) {
        return [];
    }
    const selectors = [
        "a[href]",
        "button:not([disabled])",
        "input:not([disabled]):not([type='hidden'])",
        "select:not([disabled])",
        "textarea:not([disabled])",
        "[tabindex]:not([tabindex='-1'])",
    ];
    return Array.from(appModalPanel.querySelectorAll(selectors.join(",")))
        .filter((element) => {
            if (!(element instanceof HTMLElement)) {
                return false;
            }
            if (element.hidden || element.getAttribute("aria-hidden") === "true") {
                return false;
            }
            return Boolean(element.offsetWidth || element.offsetHeight || element.getClientRects().length);
        });
}

function focusFirstModalElement() {
    if (!isAppModalOpen() || !(appModalPanel instanceof HTMLElement)) {
        return;
    }
    const candidates = modalFocusableElements();
    const target = candidates.find((element) => !element.matches("[data-action='modal:close']"))
        || candidates[0]
        || appModalPanel;
    if (!appModalPanel.hasAttribute("tabindex")) {
        appModalPanel.setAttribute("tabindex", "-1");
    }
    target.focus({ preventScroll: true });
}

function rememberModalPreviousFocus() {
    const active = document.activeElement;
    if (active instanceof HTMLElement && !appModal?.contains(active)) {
        state.modalPreviousFocus = active;
    }
}

function restoreModalPreviousFocus() {
    const previous = state.modalPreviousFocus;
    state.modalPreviousFocus = null;
    if (previous instanceof HTMLElement && document.contains(previous)) {
        previous.focus({ preventScroll: true });
    }
}

function keepModalFocusInside(event) {
    if (!isAppModalOpen() || event.key !== "Tab" || isPortalOverlayDialogTarget(event.target)) {
        return;
    }
    const candidates = modalFocusableElements();
    if (!candidates.length) {
        event.preventDefault();
        if (appModalPanel instanceof HTMLElement) {
            appModalPanel.focus({ preventScroll: true });
        }
        return;
    }
    const first = candidates[0];
    const last = candidates[candidates.length - 1];
    const active = document.activeElement;
    if (event.shiftKey && active === first) {
        event.preventDefault();
        last.focus({ preventScroll: true });
        return;
    }
    if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus({ preventScroll: true });
    }
}

function openModal(title, bodyMarkup, options = {}) {
    rememberModalPreviousFocus();
    const inlineHostKey = String(options.inlineHost || "").trim().toLowerCase();
    if (inlineHostKey) {
        enterInlineModalMode(inlineHostKey);
    } else {
        exitInlineModalMode();
    }
    if (modalController) {
        modalController.open(title, bodyMarkup, options);
        applyPortalModuleTileVisibility();
        window.setTimeout(() => focusFirstModalElement(), 0);
        return;
    }
    appModalTitle.textContent = title;
    appModalBody.innerHTML = bodyMarkup;
    appModalPanel.style.width = options.width || "min(860px, calc(100vw - 40px))";
    appModal.hidden = false;
    applyPortalModuleTileVisibility();
    window.setTimeout(() => focusFirstModalElement(), 0);
}

function closeModal() {
    if (modalController) {
        modalController.close("manual");
        exitInlineModalMode();
        applyPortalModuleTileVisibility();
        restoreModalPreviousFocus();
        return;
    }
    appModal.hidden = true;
    appModalBody.innerHTML = "";
    exitInlineModalMode();
    clearWatermarkEditorDraft();
    applyPortalModuleTileVisibility();
    restoreModalPreviousFocus();
}

function cloneModalBackValue(value) {
    return JSON.parse(JSON.stringify(value ?? null, (key, currentValue) => {
        if (String(key || "").startsWith("_")) {
            return undefined;
        }
        if (typeof currentValue === "function") {
            return undefined;
        }
        return currentValue;
    }));
}

function isActiveDirectoryRecordEditorState() {
    const kind = String(state.directoryRecordEditor?.kind || state.directoryContext?.kind || "").trim().toLowerCase();
    const expectedServiceCode = directoryServiceCode(kind);
    const currentServiceCode = String(state.noCodeServiceRecordContext?.service?.code || "").trim().toLowerCase();
    const directoryRecordId = String(state.directoryRecordEditor?.row?.id || "").trim();
    const editorRecordId = String(state.noCodeRecordEditor?.recordId || "").trim();
    return Boolean(
        state.directoryRecordEditor
        && state.noCodeRecordEditor
        && expectedServiceCode
        && currentServiceCode === expectedServiceCode
        && directoryRecordId
        && editorRecordId === directoryRecordId
    );
}

function currentModalBackSnapshot() {
    if (state.noCodeRecordViewer && state.noCodeServiceRecordContext?.service) {
        return {
            type: "service-record-view",
            noCodeServiceRecordContext: cloneModalBackValue(state.noCodeServiceRecordContext),
            noCodeRecordViewer: cloneModalBackValue(state.noCodeRecordViewer),
        };
    }
    if (isActiveDirectoryRecordEditorState()) {
        return {
            type: "directory-record",
            directoryContext: cloneModalBackValue(state.directoryContext),
            directoryRecordEditor: cloneModalBackValue(state.directoryRecordEditor),
            noCodeServiceRecordContext: cloneModalBackValue(state.noCodeServiceRecordContext),
            noCodeRecordEditor: cloneModalBackValue(state.noCodeRecordEditor),
        };
    }
    if (state.noCodeRecordEditor && state.noCodeServiceRecordContext?.service) {
        return {
            type: "service-record",
            noCodeServiceRecordContext: cloneModalBackValue(state.noCodeServiceRecordContext),
            noCodeRecordEditor: cloneModalBackValue(state.noCodeRecordEditor),
        };
    }
    if (state.directoryContext) {
        return {
            type: "directory-list",
            directoryContext: cloneModalBackValue(state.directoryContext),
        };
    }
    if (state.noCodeServiceRecordContext?.service) {
        return {
            type: "service-records",
            noCodeServiceRecordContext: cloneModalBackValue(state.noCodeServiceRecordContext),
        };
    }
    return null;
}

function pushModalBackSnapshot(snapshot = currentModalBackSnapshot()) {
    if (!snapshot?.type) {
        return;
    }
    state.modalBackStack = Array.isArray(state.modalBackStack) ? state.modalBackStack : [];
    state.modalBackStack.push(snapshot);
}

function clearModalBackStack() {
    state.modalBackStack = [];
}

function markModalDirectoryDirty() {
    state.modalDirty = state.modalDirty && typeof state.modalDirty === "object" ? state.modalDirty : {};
    state.modalDirty.directory = true;
}

function consumeModalDirectoryDirty() {
    const dirty = Boolean(state.modalDirty?.directory);
    if (state.modalDirty && typeof state.modalDirty === "object") {
        state.modalDirty.directory = false;
    }
    return dirty;
}

function markModalServiceDirty(serviceCode) {
    const code = normalizeNoCodeText(serviceCode).toLowerCase();
    if (!code) {
        return;
    }
    state.modalDirty = state.modalDirty && typeof state.modalDirty === "object" ? state.modalDirty : {};
    state.modalDirty.services = state.modalDirty.services && typeof state.modalDirty.services === "object"
        ? state.modalDirty.services
        : {};
    state.modalDirty.services[code] = true;
}

function consumeModalServiceDirty(serviceCode) {
    const code = normalizeNoCodeText(serviceCode).toLowerCase();
    if (!code) {
        return false;
    }
    const dirty = Boolean(state.modalDirty?.services?.[code]);
    if (dirty && state.modalDirty?.services) {
        delete state.modalDirty.services[code];
    }
    return dirty;
}

function markModalImpactedViewsDirty(serviceCode) {
    const code = normalizeNoCodeText(serviceCode).toLowerCase();
    markModalServiceDirty(code);
    if (["emails", "services", "utilisateurs"].includes(code)) {
        markModalDirectoryDirty();
    }
}

async function restoreNextModalBackSnapshot(mutator = null) {
    if (!Array.isArray(state.modalBackStack) || !state.modalBackStack.length) {
        return false;
    }
    const snapshot = state.modalBackStack.pop();
    if (typeof mutator === "function") {
        mutator(snapshot);
    }
    return restoreModalBackSnapshot(snapshot);
}

async function restoreModalBackSnapshot(snapshot) {
    const type = String(snapshot?.type || "");
    if (type === "directory-list") {
        const snapshotContext = cloneModalBackValue(snapshot.directoryContext);
        const snapshotKind = String(snapshotContext?.kind || "agents").trim().toLowerCase();
        state.directoryContext = consumeModalDirectoryDirty()
            ? await fetchDirectoryContext(snapshotKind, snapshotContext).catch(() => snapshotContext)
            : snapshotContext;
        state.directoryRecordEditor = null;
        state.noCodeRecordEditor = null;
        state.noCodeServiceRecordContext = null;
        directoryTreeView = null;
        const kind = String(state.directoryContext?.kind || "agents").trim().toLowerCase();
        const rows = Array.isArray(state.directoryContext?.rows) ? state.directoryContext.rows : [];
        openModal(
            kind === "services" ? "Services" : "Agents",
            buildDirectoryModuleMarkup(kind === "services" ? "services" : "agents", rows),
            noCodeInlineOptions("min(1180px, calc(100vw - 40px))", { inline: true }),
        );
        renderDirectoryTreeView();
        return true;
    }
    if (type === "directory-record") {
        const snapshotContext = cloneModalBackValue(snapshot.directoryContext);
        const snapshotEditor = cloneModalBackValue(snapshot.directoryRecordEditor);
        const kind = String(snapshotEditor?.kind || snapshotContext?.kind || "agents").trim().toLowerCase();
        state.directoryContext = consumeModalDirectoryDirty()
            ? await fetchDirectoryContext(kind, snapshotContext).catch(() => snapshotContext)
            : snapshotContext;
        const recordId = String(snapshotEditor?.row?.id || "").trim();
        state.directoryRecordEditor = {
            ...snapshotEditor,
            kind,
            row: directoryRowById(recordId) || snapshotEditor?.row || {},
        };
        state.noCodeRecordViewer = null;
        const row = state.directoryRecordEditor?.row || {};
        state.noCodeServiceRecordContext = directoryRelationContext();
        state.noCodeRecordEditor = createDirectoryRecordRelationEditor(row, kind);
        openModal(
            kind === "services" ? "Edition — Service" : "Edition — Agent",
            buildDirectoryRecordEditorMarkup(),
            noCodeInlineOptions("min(980px, calc(100vw - 40px))", { inline: true }),
        );
        scheduleDirectoryRecordRelationExperienceLoad();
        return true;
    }
    if (type === "service-records") {
        const snapshotContext = cloneModalBackValue(snapshot.noCodeServiceRecordContext);
        const serviceCode = String(snapshotContext?.service?.code || "").trim().toLowerCase();
        if (serviceCode) {
            state.noCodeServiceRecordContext = snapshotContext;
            state.directoryContext = null;
            state.directoryRecordEditor = null;
            state.noCodeRecordEditor = null;
            state.noCodeRecordViewer = null;
            if (consumeModalServiceDirty(serviceCode)) {
                await openNoCodeServiceRecords(serviceCode, { inline: true });
            } else {
                renderNoCodeServiceRecordsModal({ inline: true });
            }
            return true;
        }
        state.directoryContext = null;
        state.directoryRecordEditor = null;
        state.noCodeRecordEditor = null;
        state.noCodeRecordViewer = null;
        state.noCodeServiceRecordContext = snapshotContext;
        renderNoCodeServiceRecordsModal({ inline: true });
        return true;
    }
    if (type === "service-record-view") {
        state.directoryContext = null;
        state.directoryRecordEditor = null;
        state.noCodeRecordEditor = null;
        state.noCodeServiceRecordContext = cloneModalBackValue(snapshot.noCodeServiceRecordContext);
        state.noCodeRecordViewer = cloneModalBackValue(snapshot.noCodeRecordViewer);
        renderLinkedNoCodeRecordViewModal();
        return true;
    }
    if (type === "service-record") {
        state.directoryContext = null;
        state.directoryRecordEditor = null;
        state.noCodeRecordViewer = null;
        state.noCodeServiceRecordContext = cloneModalBackValue(snapshot.noCodeServiceRecordContext);
        state.noCodeRecordEditor = cloneModalBackValue(snapshot.noCodeRecordEditor);
        openModal(
            noCodeRecordEditorModalTitle(state.noCodeServiceRecordContext?.service, state.noCodeRecordEditor?.mode),
            buildNoCodeRecordEditorMarkup(),
            noCodeInlineOptions("min(980px, calc(100vw - 40px))", { inline: true }),
        );
        return true;
    }
    return false;
}

function showItopsConfirm(options = {}) {
    const sharedConfirm = window.NMPSharedUi?.dialogs?.showConfirm;
    if (typeof sharedConfirm === "function") {
        return sharedConfirm(options);
    }
    return Promise.resolve(false);
}

function showItopsPrompt(options = {}) {
    const sharedPrompt = window.NMPSharedUi?.dialogs?.showPrompt || window.NMPSharedUi?.dialogs?.prompt;
    if (typeof sharedPrompt === "function") {
        return sharedPrompt(options);
    }
    return Promise.resolve(null);
}

function showItopsAlert(options = {}) {
    const sharedAlert = window.NMPSharedUi?.dialogs?.showAlert || window.NMPSharedUi?.dialogs?.alert;
    if (typeof sharedAlert === "function") {
        return sharedAlert(options);
    }
    return Promise.resolve(true);
}

let appSaveFeedbackTimer = 0;

function showAppSaveFeedback(options = {}) {
    const message = String(options.message || "Enregistrement effectue.").trim() || "Enregistrement effectue.";
    const kind = String(options.kind || "success").trim().toLowerCase();
    const feedback = options.feedback instanceof HTMLElement
        ? options.feedback
        : (String(options.feedbackId || "").trim() ? document.getElementById(String(options.feedbackId).trim()) : null);
    if (feedback instanceof HTMLElement) {
        feedback.textContent = message;
        feedback.classList.toggle("error-text", kind === "error");
    }
    let toast = document.getElementById("app-save-feedback-toast");
    if (!(toast instanceof HTMLElement)) {
        toast = document.createElement("div");
        toast.id = "app-save-feedback-toast";
        toast.className = "app-save-feedback-toast";
        toast.setAttribute("role", "status");
        toast.setAttribute("aria-live", "polite");
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.dataset.kind = kind;
    toast.hidden = false;
    window.clearTimeout(appSaveFeedbackTimer);
    appSaveFeedbackTimer = window.setTimeout(() => {
        toast.hidden = true;
    }, Math.max(1200, Number(options.durationMs || 2800)));
}

function showItopsChoice(options = {}) {
    const sharedChoice = window.NMPSharedUi?.dialogs?.showChoice || window.NMPSharedUi?.dialogs?.choice;
    if (typeof sharedChoice === "function") {
        return sharedChoice(options);
    }
    return Promise.resolve("cancel");
}

function ensureCredentialRevealSessionFresh() {
    if (!state.credentialRevealSessionPassword || !state.credentialRevealUnlockUntilMs) {
        return false;
    }
    if (Date.now() < state.credentialRevealUnlockUntilMs) {
        return true;
    }
    clearCredentialRevealState();
    return false;
}

function clearCredentialRevealState() {
    state.credentialRevealSessionPassword = "";
    state.credentialRevealUnlockUntilMs = 0;
    state.revealedNoCodeRecordPasswords = {};
    if (state.credentialRevealUnlockTimer) {
        window.clearTimeout(state.credentialRevealUnlockTimer);
        state.credentialRevealUnlockTimer = null;
    }
}

function applyCredentialRevealSessionPassword(sessionPassword) {
    state.credentialRevealSessionPassword = String(sessionPassword || "");
    state.credentialRevealUnlockUntilMs = Date.now() + (Number(state.credentialRevealUnlockDurationSeconds || 300) * 1000);
    if (state.credentialRevealUnlockTimer) {
        window.clearTimeout(state.credentialRevealUnlockTimer);
    }
    state.credentialRevealUnlockTimer = window.setTimeout(() => {
        clearCredentialRevealState();
        if (state.noCodeRecordEditor) {
            renderNoCodeRecordEditor();
        }
    }, Math.max(1, Number(state.credentialRevealUnlockDurationSeconds || 300) * 1000));
}

function isCredentialRevealSessionUnlocked() {
    return ensureCredentialRevealSessionFresh();
}

function promptCredentialRevealSessionPassword() {
    const sharedPrompt = window.NMPSharedUi?.credentialDialogs?.promptSessionPassword;
    if (typeof sharedPrompt === "function") {
        return sharedPrompt();
    }
    return new Promise((resolve) => {
        const overlay = document.createElement("div");
        overlay.className = "credential-prompt-overlay";
        overlay.innerHTML = `
            <form class="credential-prompt-dialog" aria-label="Verification du mot de passe de session">
                <h3>Afficher le mot de passe</h3>
                <label class="field">
                    <span>Mot de passe de session ITOPS</span>
                    <input name="session_password" type="password" autocomplete="current-password" required>
                </label>
                <p class="muted credential-prompt-help">Cette verification est requise avant d'afficher le mot de passe enregistre.</p>
                <div class="modal-actions">
                    <button type="button" class="toolbar-btn" data-credential-prompt="cancel">Annuler</button>
                    <button type="submit" class="primary-btn">Afficher</button>
                </div>
            </form>
        `;
        const close = (value = null) => {
            overlay.remove();
            resolve(value);
        };
        overlay.addEventListener("click", (event) => {
            const target = event.target;
            if (target === overlay || (target instanceof Element && target.closest('[data-credential-prompt="cancel"]'))) {
                close();
            }
        });
        overlay.addEventListener("submit", (event) => {
            event.preventDefault();
            const input = overlay.querySelector('input[name="session_password"]');
            const value = input instanceof HTMLInputElement ? input.value : "";
            if (!value) {
                input?.focus();
                return;
            }
            close(value);
        });
        document.body.appendChild(overlay);
        overlay.querySelector('input[name="session_password"]')?.focus();
    });
}

function showRevealedCredentialPassword(password) {
    const sharedDialog = window.NMPSharedUi?.credentialDialogs?.showPassword;
    if (typeof sharedDialog === "function") {
        return sharedDialog(password);
    }
    return new Promise((resolve) => {
        const overlay = document.createElement("div");
        overlay.className = "credential-prompt-overlay";
        overlay.innerHTML = `
            <section class="credential-prompt-dialog" role="dialog" aria-modal="true" aria-label="Mot de passe revele">
                <h3>Mot de passe revele</h3>
                <label class="field">
                    <span>Mot de passe</span>
                    <input type="text" readonly value="${escapeHtml(String(password || ""))}" autocomplete="off">
                </label>
                <p class="muted credential-prompt-help">Refermez cette fenetre apres consultation.</p>
                <div class="modal-actions">
                    ${createIconActionButtonMarkup({
                        icon: "list",
                        title: "Copier le mot de passe",
                        ariaLabel: "Copier le mot de passe",
                        data: { credential_revealed: "copy" },
                    })}
                    <button type="button" class="primary-btn" data-credential-revealed="close">Fermer</button>
                </div>
                <p class="muted credential-prompt-help" data-credential-revealed-feedback></p>
            </section>
        `;
        const close = () => {
            overlay.remove();
            resolve();
        };
        overlay.addEventListener("click", (event) => {
            const target = event.target;
            if (target === overlay || (target instanceof Element && target.closest('[data-credential-revealed="close"]'))) {
                close();
                return;
            }
            if (target instanceof Element && target.closest('[data-credential-revealed="copy"]')) {
                const value = String(password || "");
                const feedback = overlay.querySelector("[data-credential-revealed-feedback]");
                const copied = () => {
                    if (feedback instanceof HTMLElement) {
                        feedback.textContent = "Mot de passe copie dans le presse-papiers.";
                    }
                };
                if (navigator.clipboard?.writeText) {
                    navigator.clipboard.writeText(value).then(copied).catch(() => {
                        if (feedback instanceof HTMLElement) {
                            feedback.textContent = "Copie impossible : selectionnez le mot de passe puis copiez-le manuellement.";
                        }
                    });
                } else if (feedback instanceof HTMLElement) {
                    feedback.textContent = "Copie non disponible : selectionnez le mot de passe puis copiez-le manuellement.";
                }
            }
        });
        document.body.appendChild(overlay);
        const input = overlay.querySelector("input");
        if (input instanceof HTMLInputElement) {
            input.focus();
            input.select();
        }
    });
}

function requestNotificationReminderDate(options = {}) {
    const title = String(options.title || "Date de rappel").trim();
    const message = String(options.message || "Selectionner la date de rappel.").trim();
    return new Promise((resolve) => {
        const overlay = document.createElement("div");
        overlay.className = "notification-date-overlay";
        overlay.innerHTML = `
            <form class="notification-date-dialog">
                <h3>${escapeHtml(title)}</h3>
                <p class="muted">${escapeHtml(message)}</p>
                <label class="field">
                    <span>Date de rappel</span>
                    <input name="due_date" type="date" required>
                </label>
                <div class="modal-actions">
                    <button class="toolbar-btn" type="button" data-action="notification-date:cancel">Annuler</button>
                    <button class="primary-btn" type="submit">Valider</button>
                </div>
            </form>
        `;
        const cleanup = (value) => {
            overlay.remove();
            resolve(value || "");
        };
        overlay.addEventListener("click", (event) => {
            if (event.target === overlay || event.target.closest('[data-action="notification-date:cancel"]')) {
                cleanup("");
            }
        });
        overlay.querySelector("form")?.addEventListener("submit", (event) => {
            event.preventDefault();
            const input = overlay.querySelector('input[name="due_date"]');
            cleanup(input instanceof HTMLInputElement ? String(input.value || "").trim() : "");
        });
        document.body.appendChild(overlay);
        const input = overlay.querySelector('input[name="due_date"]');
        if (input instanceof HTMLInputElement) {
            input.focus();
            input.showPicker?.();
        }
    });
}

function confirmBatchAction(options = {}) {
    const sharedConfirm = window.NMPSharedUi?.batchActions?.confirm;
    if (typeof sharedConfirm === "function") {
        return sharedConfirm(options);
    }
    return showItopsConfirm(options);
}

function closeTopMenu() {
    if (topMenuController) {
        topMenuController.close();
        return;
    }
    const sharedCloseTopMenu = window.NMPSharedUi?.closeTopMenu;
    if (typeof sharedCloseTopMenu === "function") {
        sharedCloseTopMenu(state, topMenuPanel, [menuSupervision, menuConfiguration, menuHelp]);
    }
}

function closeProfileMenu() {
    profileMenuController?.close?.();
}

function closeCardsContextMenu() {
    if (!(cardsContextMenu instanceof HTMLElement)) {
        return;
    }
    cardsContextMenu.hidden = true;
    cardsContextMenu.innerHTML = "";
    state.portalContextModuleCode = "";
    state.noCodeRelationContextNodeCode = "";
}

function isCurrentModuleMenuEntry(moduleRow, context = activeModuleMenuContext()) {
    if (!context || !moduleRow) {
        return false;
    }
    const moduleCode = String(moduleRow.code || "").trim().toLowerCase();
    if (moduleCode && moduleCode === String(context.code || "").trim().toLowerCase()) {
        return true;
    }
    const routePath = portalModuleRoutePath(moduleRow);
    if (context.kind === "service") {
        return extractServiceCodeFromRoutePath(routePath) === String(context.serviceCode || context.code || "").trim().toLowerCase();
    }
    if (context.kind === "directory") {
        return extractDirectoryKindFromRoutePath(routePath) === String(context.directoryKind || "").trim().toLowerCase();
    }
    return false;
}

function activeModuleServiceMenuEntries(context = activeModuleMenuContext()) {
    const rows = Array.isArray(state.portalModules) ? state.portalModules : [];
    const entries = rows
        .filter((row) => Boolean(row?.granted && row?.is_active && portalModuleRoutePath(row)))
        .filter((row) => !isCurrentModuleMenuEntry(row, context))
        .sort((left, right) => {
            const leftIsMonitoring = isMonitoringPortalModule(left);
            const rightIsMonitoring = isMonitoringPortalModule(right);
            if (leftIsMonitoring !== rightIsMonitoring) {
                return leftIsMonitoring ? -1 : 1;
            }
            return String(left?.label || left?.code || "")
                .localeCompare(String(right?.label || right?.code || ""), undefined, { sensitivity: "base" });
        });
    return entries.map((row) => ({
        label: String(row?.label || row?.code || "Module").trim() || "Module",
        action: `menu:active-module:open:${encodeURIComponent(String(row?.code || "").trim().toLowerCase())}`,
    }));
}

function noCodeServiceActionLabels(service) {
    const serviceLabel = String(service?.label || service?.code || "module").trim() || "module";
    return {
        edit: `Modifier le module ${serviceLabel}`,
        refresh: `Actualiser ${serviceLabel}`,
        export: `Exporter ${serviceLabel}`,
        import: `Importer ${serviceLabel}`,
        duplicates: `Analyser les doublons de ${serviceLabel}`,
        add: `Ajouter ${serviceLabel}`,
    };
}

function activeModuleDataMenuEntries(context = activeModuleMenuContext()) {
    if (!context || context.kind !== "service") {
        return [{ label: "Actualiser les donnees", action: "menu:active-module:refresh" }];
    }
    const service = findNoCodeService(context.serviceCode || context.code) || context;
    const labels = noCodeServiceActionLabels(service);
    const entries = [{ label: labels.refresh, action: "menu:active-module:refresh" }];
    if (!isSystemNoCodeService(service)) {
        entries.push({ label: labels.edit, action: "menu:active-module:data:definition" });
    }
    entries.push(
        { label: labels.add, action: "menu:active-module:data:add" },
        { label: labels.import, action: "menu:active-module:data:import" },
        { label: labels.export, action: "menu:active-module:data:export" },
        { label: labels.duplicates, action: "menu:active-module:data:duplicates" },
    );
    return entries;
}

async function runActiveModuleDataAction(action) {
    const context = activeModuleMenuContext();
    if (!context || context.kind !== "service") {
        return false;
    }
    const serviceCode = String(context.serviceCode || context.code || "").trim().toLowerCase();
    if (!serviceCode) {
        return false;
    }
    const currentServiceCode = String(state.noCodeServiceRecordContext?.service?.code || "").trim().toLowerCase();
    if (currentServiceCode !== serviceCode) {
        await openNoCodeServiceRecords(serviceCode, { inline: true });
    }
    const actionByMenuAction = {
        "menu:active-module:data:definition": "service:definition:edit",
        "menu:active-module:data:add": "service:record:add",
        "menu:active-module:data:import": "service:records:import",
        "menu:active-module:data:export": "service:records:export",
        "menu:active-module:data:duplicates": "service:records:duplicates",
    };
    const serviceAction = actionByMenuAction[action];
    if (!serviceAction) {
        return false;
    }
    return handleNoCodeModalClick({
        dataset: {
            action: serviceAction,
            serviceCode,
        },
    });
}

function topMenuDefinitions() {
    const sharedDefs = window.NMPSharedMenu?.commonDefinitions?.() || {};
    const moduleContext = activeModuleMenuContext();
    if (moduleContext) {
        const availableModules = activeModuleServiceMenuEntries(moduleContext);
        return {
            services: [
                { label: "Retour au portail des services", action: "menu:active-module:portal" },
                ...(availableModules.length
                    ? availableModules
                    : [{ label: "Aucun autre module actif", action: "", disabled: true }]),
            ],
            data: activeModuleDataMenuEntries(moduleContext),
            help: [...(sharedDefs.help || [])],
        };
    }
    const sharedSupervision = Array.isArray(sharedDefs.supervision) ? sharedDefs.supervision : [];
    const sharedDisplay = Array.isArray(sharedDefs.display) ? sharedDefs.display : [];
    const hasUsersAdminAccess = (state.moduleAccess || []).some((row) => {
        const code = String(row?.code || "").trim().toLowerCase();
        return Boolean(row?.granted) && (code === "users_admin" || code === "admin");
    });
    const hasAdminModule = (state.moduleAccess || []).some((row) => String(row?.code || "").trim().toLowerCase() === "admin" && Boolean(row?.granted));
    const canManageRoles = state.sessionRoleCode === "admin" || hasAdminModule || ["sa", "admin"].includes(state.sessionSubject);
    const canManageServices = canManageRoles;
    const sharedServerWebEntries = sharedSupervision.filter((entry) => {
        const label = String(entry?.label || "").trim().toLowerCase();
        const actions = Array.isArray(entry?.items)
            ? entry.items.map((item) => String(item?.action || "").trim().toLowerCase())
            : [];
        return label === "serveur web" || actions.includes("menu:web");
    });
    const sharedSupervisionEntries = sharedSupervision.filter((entry) => !sharedServerWebEntries.includes(entry));
    const displayEntries = [
        ...sharedDisplay,
        {
            label: "Image de fond",
            disabled: !canManageRoles,
            items: [
                { label: "Importer...", action: "menu:watermark:import" },
                { label: "Editer...", action: "menu:watermark:edit" },
            ],
        },
    ];
    const configurationEntries = [
        ...sharedServerWebEntries,
        {
            label: "Notifications",
            disabled: !canManageRoles,
            items: [
                { label: "Parametres SMTP...", action: "menu:notifications:settings" },
                { label: "Taches planifiees...", action: "menu:notifications:tasks" },
                { label: "Templates de mail...", action: "menu:notifications:templates" },
            ],
        },
        {
            label: "Affichage",
            items: displayEntries,
        },
        {
            label: "Stockage",
            disabled: !canManageRoles,
            items: [
                { label: "Bibliotheque de fichiers...", action: "menu:storage:files" },
            ],
        },
        {
            label: "Synchronisation",
            disabled: !canManageRoles,
            items: [
                { label: "Active Directory...", action: "menu:sync:active-directory" },
            ],
        },
        {
            label: "Base de donnees",
            disabled: !canManageRoles,
            items: [
                { label: "Sauvegarder...", action: "menu:database:backup" },
                { label: "Importer une sauvegarde...", action: "menu:database:import" },
            ],
        },
    ];
    return {
        supervision: [
            ...sharedSupervisionEntries,
            ...(canManageServices
                ? [
                    {
                        label: "Services",
                        items: [
                            { label: "Ajouter un service...", action: "menu:services:add" },
                            { label: "Gerer les services...", action: "menu:services:manage" },
                            { label: "Listes partagees...", action: "menu:services:shared-lists" },
                        ],
                    },
                ]
                : []),
            ...((hasUsersAdminAccess || canManageRoles)
                ? [
                    {
                        label: "Administration",
                        items: [
                            ...(canManageRoles ? [{ label: "Roles...", action: "menu:admin:roles" }] : []),
                            ...(hasUsersAdminAccess || canManageRoles ? [{ label: "Comptes applicatifs...", action: "menu:admin:users" }] : []),
                        ],
                    },
                ]
                : []),
        ],
        configuration: configurationEntries,
        help: [...(sharedDefs.help || [])],
    };
}

function topMenuMarkup(menuKey) {
    const defs = topMenuDefinitions();
    const entries = defs[menuKey] || defs.help || [];
    const shared = window.NMPSharedMenu;
    if (shared && typeof shared.renderTopMenuGroup === "function") {
        return shared.renderTopMenuGroup(entries);
    }
    return "";
}

function openTopMenu(button, menuKey) {
    closeProfileMenu();
    if (topMenuController) {
        topMenuController.open(button, menuKey, {
            buildMarkup: topMenuMarkup,
            onBeforeOpen: () => {
                closeProfileMenu();
                closeCardsContextMenu();
                if (!state.activeModuleMenuContext) {
                    closeModal();
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
            buttons: [menuSupervision, menuConfiguration, menuHelp],
            button,
            menuKey,
            buildMarkup: topMenuMarkup,
            onBeforeOpen: () => {
                closeProfileMenu();
                closeCardsContextMenu();
                if (!state.activeModuleMenuContext) {
                    closeModal();
                }
            },
        });
        return;
    }
    if (state.openTopMenu === menuKey && !topMenuPanel.hidden) {
        closeTopMenu();
        return;
    }
    closeCardsContextMenu();
    if (!state.activeModuleMenuContext) {
        closeModal();
    }
    state.openTopMenu = menuKey;
    topMenuPanel.innerHTML = topMenuMarkup(menuKey);
    topMenuPanel.hidden = false;
    [menuSupervision, menuConfiguration, menuHelp].forEach((entry) => {
        entry.classList.toggle("active", entry === button);
    });
    const rect = button.getBoundingClientRect();
    topMenuPanel.style.left = `${Math.max(8, rect.left)}px`;
    topMenuPanel.style.top = `${rect.bottom + 4}px`;
}

function createFieldMarkup(key, label, value, wide = false) {
    const sharedFieldMarkup = window.NMPSharedUi?.createFieldMarkup;
    if (typeof sharedFieldMarkup === "function") {
        return sharedFieldMarkup({
            key,
            label,
            value,
            wide,
            escapeHtml,
        });
    }
    return `
    <label class="field ${wide ? "wide" : ""}">
        <span>${escapeHtml(label)}</span>
        <input name="${escapeHtml(key)}" value="${escapeHtml(value)}">
    </label>
    `;
}

function createActionButtonMarkup(options = {}) {
    const sharedBuilder = window.NMPSharedUi?.formControls?.createActionButtonMarkup;
    if (typeof sharedBuilder === "function") {
        return sharedBuilder({
            ...options,
            escapeHtml,
            escapeAttribute: escapeHtml,
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
        `class="${escapeHtml(classes)}"`,
        `type="${escapeHtml(type)}"`,
    ];
    if (action) {
        attrs.push(`data-action="${escapeHtml(action)}"`);
    }
    if (title) {
        attrs.push(`title="${escapeHtml(title)}"`);
    }
    if (id) {
        attrs.push(`id="${escapeHtml(id)}"`);
    }
    if (name) {
        attrs.push(`name="${escapeHtml(name)}"`);
    }
    if (value) {
        attrs.push(`value="${escapeHtml(value)}"`);
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
        attrs.push(`data-${normalized}="${escapeHtml(String(rawValue))}"`);
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
        attrs.push(`${nameAttr}="${escapeHtml(String(rawValue))}"`);
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
            escapeAttribute: escapeHtml,
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
            escapeAttribute: escapeHtml,
        });
    }
    const buttons = Array.isArray(options.buttons) && options.buttons.length
        ? options.buttons
        : [{ className: "toolbar-btn", type: "button", action: "modal:close", label: "Annuler" }, { className: "primary-btn", type: "submit", label: "Enregistrer" }];
    const className = ["modal-actions", String(options.className || "").trim()].filter(Boolean).join(" ");
    return `<div class="${escapeHtml(className)}">${buttons.map((button) => createActionButtonMarkup(button)).join("")}</div>`;
}

function buildTreeSectionMarkup(options = {}) {
    const sharedBuilder = window.NMPSharedUi?.treeView?.buildSectionMarkup;
    if (typeof sharedBuilder === "function") {
        return sharedBuilder({
            ...options,
            escapeHtml,
            escapeAttribute: escapeHtml,
        });
    }
    const sectionTitle = String(options.title || "").trim();
    const titleActionsMarkup = String(options.titleActionsMarkup || "");
    const searchId = String(options.searchId || "").trim();
    const searchLabel = String(options.searchLabel || "Recherche").trim() || "Recherche";
    const searchPlaceholder = String(options.searchPlaceholder || "").trim();
    const searchValue = String(options.searchValue || "");
    const searchInTitleRow = Boolean(options.searchInTitleRow);
    const extraToolsIsFunction = typeof options.extraToolsMarkup === "function";
    const filtersMarkup = String(options.filtersMarkup || options.filterMarkup || "");
    const beforeTableMarkup = String(options.beforeTableMarkup || "");
    const afterTableMarkup = String(options.afterTableMarkup || "");
    const footerActionsMarkup = String(options.footerActionsMarkup || "");
    const feedbackId = String(options.feedbackId || "").trim();
    const description = String(options.description || "").trim();
    const headId = String(options.headId || "").trim();
    const bodyId = String(options.bodyId || "").trim();
    const headMarkup = String(options.headMarkup || "");
    const bodyMarkup = String(options.bodyMarkup || "");
    const tableClassName = String(options.tableClassName || "device-table inventory-table").trim() || "device-table inventory-table";
    const searchMarkup = searchId
        ? `
            <label class="field inline-field shared-treeview-search">
                <span>${escapeHtml(searchLabel)}</span>
                <input id="${escapeHtml(searchId)}" type="search" placeholder="${escapeHtml(searchPlaceholder)}" value="${escapeHtml(searchValue)}">
            </label>
        `
        : "";
    const extraToolsMarkup = extraToolsIsFunction
        ? String(options.extraToolsMarkup(searchMarkup, { escapeHtml, escapeAttribute: escapeHtml }) || "")
        : String(options.extraToolsMarkup || "");
    const defaultToolsSearchMarkup = !extraToolsIsFunction && !searchInTitleRow ? searchMarkup : "";
    const toolsMarkup = ((!searchInTitleRow && searchMarkup) || extraToolsMarkup)
        ? `
            <div class="inventory-controls shared-treeview-tools">
                ${defaultToolsSearchMarkup}
                ${extraToolsMarkup}
            </div>
        `
        : "";
    return `
        <section class="modal-section shared-treeview-section">
            <div class="section-head shared-treeview-title-row">
                <h3>${escapeHtml(sectionTitle)}</h3>
                ${(titleActionsMarkup || (searchInTitleRow && searchMarkup))
        ? `<div class="inventory-row-actions shared-treeview-title-actions">${titleActionsMarkup}${searchInTitleRow ? searchMarkup : ""}</div>`
        : ""}
            </div>
            ${description ? `<p class="muted shared-treeview-description">${escapeHtml(description)}</p>` : ""}
            ${toolsMarkup}
            ${filtersMarkup}
            ${beforeTableMarkup}
            <div class="table-wrap shared-treeview-table-wrap">
                <table class="${escapeHtml(tableClassName)} shared-treeview-table">
                    <thead ${headId ? `id="${escapeHtml(headId)}"` : ""}>${headMarkup}</thead>
                    <tbody ${bodyId ? `id="${escapeHtml(bodyId)}"` : ""}>${bodyMarkup}</tbody>
                </table>
            </div>
            ${afterTableMarkup}
            ${feedbackId ? `<p id="${escapeHtml(feedbackId)}" class="muted inventory-feedback shared-treeview-feedback"></p>` : ""}
            ${footerActionsMarkup}
        </section>
    `;
}

function tableUpdateSearchVisibility(input, rowCount, threshold = 5) {
    const shared = window.NMPSharedUi?.tableTools?.updateSearchVisibility;
    if (typeof shared !== "function") {
        return;
    }
    shared(input, rowCount, threshold);
}

function tableFilterAndSortRows(rows, options = {}) {
    const shared = window.NMPSharedUi?.tableTools?.filterAndSortRows;
    if (typeof shared === "function") {
        return shared(rows, options);
    }
    return Array.isArray(rows) ? rows.slice() : [];
}

function listFromMaybeArray(value) {
    return Array.isArray(value) ? value : [];
}

function tableBindHeaderSort(headElement, options = {}) {
    const shared = window.NMPSharedUi?.tableTools?.bindHeaderSort;
    if (typeof shared !== "function") {
        return;
    }
    shared(headElement, options);
}

function formatNoCodeHistoryDate(value) {
    const raw = String(value || "").trim();
    if (!raw) {
        return "";
    }
    const parsed = Date.parse(raw.includes("T") ? raw : raw.replace(" ", "T"));
    if (!Number.isFinite(parsed)) {
        return raw;
    }
    return new Date(parsed).toLocaleString("fr-FR", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function formatNoCodeDateTimeLocalValue(value = null) {
    const source = value instanceof Date ? value : new Date();
    const pad = (number) => String(number).padStart(2, "0");
    return [
        source.getFullYear(),
        "-",
        pad(source.getMonth() + 1),
        "-",
        pad(source.getDate()),
        "T",
        pad(source.getHours()),
        ":",
        pad(source.getMinutes()),
    ].join("");
}

function noCodeHistoryDecisionKind(decision) {
    if (typeof decision === "string") {
        return decision || "none";
    }
    return String(decision?.decision || "none");
}

function noCodeHistoryDecisionChangedAt(decision) {
    if (!decision || typeof decision !== "object") {
        return "";
    }
    return String(decision.changedAt || "").trim();
}

function formatNoCodeDisplayDate(value) {
    const raw = String(value || "").trim();
    if (!raw) {
        return "";
    }
    const dateOnly = raw.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (dateOnly) {
        return `${dateOnly[3]}/${dateOnly[2]}/${dateOnly[1]}`;
    }
    const parsed = Date.parse(raw.includes("T") ? raw : raw.replace(" ", "T"));
    if (!Number.isFinite(parsed)) {
        return raw;
    }
    return new Date(parsed).toLocaleDateString("fr-FR", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
    });
}

function formatNoCodeRecordDisplayValue(value, column) {
    if (normalizeNoCodeKind(column?.kind || "text") === "date") {
        return formatNoCodeDisplayDate(value);
    }
    return String(value || "");
}

function noCodeRecordHistoryTooltip(row, column) {
    const fieldKey = String(column?.field_key || "").trim();
    if (!fieldKey || !Boolean(column?.track_history)) {
        return "";
    }
    const summary = row?.history_summary && typeof row.history_summary === "object"
        ? row.history_summary[fieldKey]
        : null;
    const changedAt = formatNoCodeHistoryDate(summary?.changed_at || "");
    if (!changedAt) {
        return "";
    }
    const oldValue = formatNoCodeRecordDisplayValue(summary?.old_value || "", column);
    const newValue = formatNoCodeRecordDisplayValue(summary?.new_value || "", column);
    return [
        `Depuis le ${changedAt}`,
        oldValue && newValue ? `Changement: ${oldValue} -> ${newValue}` : "",
    ].filter(Boolean).join("\n");
}

class ServiceRecordsTreeView extends (window.NMPSharedUi?.treeView?.SharedTreeView || class {}) {
    constructor(context) {
        const headElement = document.getElementById("service-records-head");
        const bodyElement = document.getElementById("service-records-body");
        const searchInput = document.getElementById("service-records-search");
        if (searchInput instanceof HTMLInputElement) {
            searchInput.value = String(context?.searchQuery || "");
        }
        const sortState = normalizeNoCodeRecordSortState(context?.service || null, context?.sort || null);
        if (context) {
            context.sort = sortState;
        }
        super({
            headElement: headElement instanceof HTMLElement ? headElement : null,
            bodyElement: bodyElement instanceof HTMLElement ? bodyElement : null,
            searchInput: searchInput instanceof HTMLInputElement ? searchInput : null,
            sortState,
            columnAttr: "col",
            renderHead: true,
            manageSortBinding: true,
            manageSearchBinding: true,
            searchThreshold: 5,
            emptyMessage: "Aucune fiche",
            selectable: true,
            selectedRowKeys: Array.isArray(context?.selectedRecordKeys) ? context.selectedRecordKeys : [],
            pageSizeControl: true,
            pageSizeOptions: [10, 25, 50, 100, 200, 500],
            pageSizeControlElements: [
                document.getElementById("service-records-page-size-top"),
                document.getElementById("service-records-page-size-bottom"),
            ].filter((element) => element instanceof HTMLElement),
            getPageSize: () => Number(context?.recordsPage?.limit || 50),
            onPageSizeChanged: (limit) => {
                if (!context) {
                    return;
                }
                context.recordsPage = {
                    ...(context.recordsPage || {}),
                    limit: Math.max(1, Math.min(500, Number(limit || 50))),
                    offset: 0,
                };
                reloadNoCodeServiceRecordsPage(context, { offset: 0, limit: context.recordsPage.limit }).catch((error) => {
                    const feedback = document.getElementById("modal-service-records-feedback");
                    if (feedback) {
                        feedback.textContent = normalizeErrorMessage(error.message);
                    }
                });
            },
            getRows: () => noCodeRecordRowsForContext(context),
            getColumns: () => {
                const dynamicCols = recordColumnsForContext(context)
                    .map((column) => ({
                        key: String(column?.key || ""),
                        label: String(column?.label || ""),
                        sortable: true,
                    }));
                return [...dynamicCols, { key: "", label: "Actions", sortable: false }];
            },
            searchText: (row) => {
                const columns = recordColumnsForContext(context);
                const values = [
                    String(row?.id || ""),
                    String(row?.updated_at || ""),
                    ...columns.map((column) => String(noCodeRecordColumnValue(row, column) || "")),
                    ...(Array.isArray(row?.children) ? row.children.map((child) => `${child?.name || ""} ${child?.code || ""}`) : []),
                ];
                return values.join(" ").toLowerCase();
            },
            compareRows: (column, direction, left, right) => {
                const columns = recordColumnsForContext(context);
                const columnsByKey = new Map(columns.map((entry) => [String(entry.key || ""), entry]));
                return noCodeRecordCompareByColumn(columnsByKey, column, direction, left, right);
            },
            getRowKey: (row) => String(row?.id || row?.record_id || ""),
            renderRowCells: (row) => {
                const columns = recordColumnsForContext(context);
                const valueCells = columns
                    .map((column) => {
                        const value = String(noCodeRecordColumnValue(row, column) || "");
                        const tooltip = noCodeRecordHistoryTooltip(row, column);
                        const inlineEditable = noCodeRecordColumnAllowsInlineEdit(context?.service || null, column);
                        const cellClass = [
                            tooltip ? "no-code-history-cell" : "",
                            inlineEditable ? "no-code-inline-edit-cell" : "",
                        ].filter(Boolean).join(" ");
                        const cellAttrs = [
                            tooltip ? `title="${escapeHtml(tooltip)}"` : "",
                            cellClass ? `class="${escapeHtml(cellClass)}"` : "",
                        ].filter(Boolean).join(" ");
                        const cellValue = String(column?.key || "").startsWith("linked:")
                            ? renderLinkedColumnCell(row, column)
                            : (inlineEditable
                                ? buildNoCodeInlineRecordControl(row, column, value)
                                : escapeHtml(formatNoCodeRecordDisplayValue(value, column)));
                        return `<td ${cellAttrs}>${cellValue}</td>`;
                    })
                    .join("");
                return `
                    ${valueCells}
                    <td class="inventory-row-actions">
                        ${Boolean(context?.service?.credentials_enabled) && noCodeRecordHasStoredCredentialPassword(row) ? createIconActionButtonMarkup({
                            iconHtml: "&#128065;",
                            iconClass: "reveal-password",
                            action: "service:record:credential-reveal",
                            title: noCodeRecordHasStoredCredentialPassword(row) ? "Afficher le mot de passe stocke" : "Aucun mot de passe stocke",
                            ariaLabel: noCodeRecordHasStoredCredentialPassword(row) ? "Afficher le mot de passe stocke" : "Aucun mot de passe stocke",
                            data: {
                                service_code: String(context?.service?.code || ""),
                                record_id: String(row?.id || ""),
                            },
                        }) : ""}
                        ${createIconActionButtonMarkup({
                            icon: "settings",
                            action: "service:record:edit",
                            title: "Modifier",
                            data: {
                                record_id: String(row?.id || ""),
                                record_version_token: String(row?.version_token || ""),
                            },
                        })}
                        ${createIconActionButtonMarkup({
                            icon: "delete",
                            danger: true,
                            action: "service:record:delete",
                            title: "Supprimer",
                            data: {
                                record_id: String(row?.id || ""),
                                record_version_token: String(row?.version_token || ""),
                            },
                        })}
                    </td>
                `;
            },
            onSearchChanged: (query) => {
                if (!context) {
                    return;
                }
                context.searchQuery = String(query || "");
                updateNoCodeServiceRecordsFilterActions(context);
                scheduleNoCodeServiceRecordsPageReload(context, { offset: 0 });
            },
            onSelectionChanged: ({ selectedKeys }) => {
                if (!context) {
                    return;
                }
                context.selectedRecordKeys = Array.isArray(selectedKeys) ? selectedKeys : [];
                updateNoCodeServiceRecordsBatchActions(context);
            },
            getColumnMenuExtraMarkup: () => linkedColumnMenuMarkup(context),
            onColumnMenuExtraAction: (action, trigger) => handleLinkedColumnMenuAction(
                context,
                action,
                trigger,
                () => renderNoCodeServiceRecordsModal({ inline: true }),
            ),
        });
        this._context = context;
    }
}

class NoCodeRelationLinksTreeView extends (window.NMPSharedUi?.treeView?.SharedTreeView || class {}) {
    constructor(context) {
        const service = context?.linkedService || null;
        super({
            headElement: document.getElementById("service-relation-links-head"),
            bodyElement: document.getElementById("service-relation-links-body"),
            searchInput: document.getElementById("service-relation-links-search"),
            sortState: context?.sort || { column: "", direction: "asc" },
            columnAttr: "relation-links-col",
            renderHead: true,
            manageSortBinding: true,
            manageSearchBinding: true,
            searchThreshold: 5,
            emptyMessage: "Aucune fiche liee",
            getRows: () => (Array.isArray(context?.links) ? context.links : []),
            getColumns: () => {
                const columns = noCodeRecordColumns(service).slice(0, 8).map((column) => ({
                    key: String(column?.key || ""),
                    label: String(column?.label || ""),
                    sortable: true,
                }));
                const visibleColumns = columns.length ? columns : [{ key: "id", label: "Identifiant", sortable: true }];
                return [...visibleColumns, { key: "", label: "Actions", sortable: false }];
            },
            searchText: (link) => {
                const row = link?.linked_record || {};
                const columns = noCodeRecordColumns(service);
                return [
                    String(row?.id || ""),
                    ...columns.map((column) => String(noCodeRecordColumnValue(row, column) || "")),
                ].join(" ").toLowerCase();
            },
            compareRows: (column, direction, left, right) => {
                const columns = noCodeRecordColumns(service);
                const columnsByKey = new Map(columns.map((entry) => [String(entry.key || ""), entry]));
                return noCodeRecordCompareByColumn(
                    columnsByKey,
                    column,
                    direction,
                    left?.linked_record || {},
                    right?.linked_record || {},
                );
            },
            getRowKey: (link) => String(link?.id || link?.linked_record?.id || ""),
            renderRowCells: (link) => {
                const row = link?.linked_record || {};
                const columns = noCodeRecordColumns(service).slice(0, 8);
                if (!columns.length) {
                    return `
                        <td>${escapeHtml(String(row?.id || ""))}</td>
                        ${this.renderActionCell(link)}
                    `;
                }
                const valueCells = columns.map((column) => {
                    const value = noCodeRecordColumnValue(row, column);
                    return `<td>${escapeHtml(formatNoCodeRecordDisplayValue(value, column))}</td>`;
                }).join("");
                return `${valueCells}${this.renderActionCell(link)}`;
            },
            onSearchChanged: (query) => {
                if (context) {
                    context.searchQuery = String(query || "");
                }
            },
        });
    }

    renderActionCell(link) {
        const service = this._context?.linkedService || null;
        const record = link?.linked_record || {};
        const serviceCode = String(service?.code || "").trim().toLowerCase();
        const recordId = String(record?.id || "").trim();
        const hasPassword = noCodeRecordHasStoredCredentialPassword(record);
        const linkedRecordId = String(record.id || "");
        return `
            <td class="inventory-row-actions">
                ${Boolean(service?.credentials_enabled) && hasPassword ? createIconActionButtonMarkup({
                    iconHtml: "&#128065;",
                    iconClass: "reveal-password",
                    action: "service:record:credential-reveal",
                    title: hasPassword ? "Afficher le mot de passe stocke" : "Aucun mot de passe stocke",
                    ariaLabel: hasPassword ? "Afficher le mot de passe stocke" : "Aucun mot de passe stocke",
                    data: { service_code: serviceCode, record_id: recordId },
                    disabled: !serviceCode || !recordId,
                }) : ""}
                ${createIconActionButtonMarkup({
                    icon: "list",
                    action: "service:relation-link:open",
                    title: "Ouvrir la fiche",
                    data: { linked_record_id: linkedRecordId },
                })}
                ${createIconActionButtonMarkup({
                    icon: "delete",
                    danger: true,
                    action: "service:relation-link:delete",
                    title: "Delier",
                    data: { linked_record_id: linkedRecordId },
                })}
            </td>
        `;
    }
}

function ensureServiceRecordsTreeView(context) {
    const BaseClass = window.NMPSharedUi?.treeView?.SharedTreeView;
    if (!BaseClass || !context) {
        return null;
    }
    const currentHead = document.getElementById("service-records-head");
    const currentBody = document.getElementById("service-records-body");
    const activeTree = context._recordsTreeView;
    if (activeTree instanceof ServiceRecordsTreeView
        && activeTree.headElement === currentHead
        && activeTree.bodyElement === currentBody) {
        return activeTree;
    }
    context._recordsTreeView = new ServiceRecordsTreeView(context);
    return context._recordsTreeView;
}

function ensureNoCodeRelationLinksTreeView(context) {
    const BaseClass = window.NMPSharedUi?.treeView?.SharedTreeView;
    if (!BaseClass || !context) {
        return null;
    }
    const currentHead = document.getElementById("service-relation-links-head");
    const currentBody = document.getElementById("service-relation-links-body");
    const activeTree = context._treeView;
    if (activeTree instanceof NoCodeRelationLinksTreeView
        && activeTree.headElement === currentHead
        && activeTree.bodyElement === currentBody) {
        return activeTree;
    }
    context._treeView = new NoCodeRelationLinksTreeView(context);
    return context._treeView;
}

function adminRoleRows() {
    return Array.isArray(state.adminData?.roles) ? state.adminData.roles : [];
}

function adminUserRows() {
    return Array.isArray(state.adminData?.users) ? state.adminData.users : [];
}

function adminRoleModulesText(row) {
    const modules = Array.isArray(row?.module_codes) ? row.module_codes : [];
    return modules.join(", ");
}

function compareAdminRoleRows(column, direction, left, right) {
    const dir = direction === "desc" ? -1 : 1;
    const byText = (a, b) => String(a || "").localeCompare(String(b || ""), undefined, { sensitivity: "base" }) * dir;
    if (column === "label") {
        return byText(left?.label, right?.label);
    }
    if (column === "modules") {
        return byText(adminRoleModulesText(left), adminRoleModulesText(right));
    }
    return byText(left?.code, right?.code);
}

function compareAdminUserRows(column, direction, left, right) {
    const dir = direction === "desc" ? -1 : 1;
    const byText = (a, b) => String(a || "").localeCompare(String(b || ""), undefined, { sensitivity: "base" }) * dir;
    const leftRole = String((left?.role_codes || [])[0] || "-");
    const rightRole = String((right?.role_codes || [])[0] || "-");
    if (column === "label") {
        return byText(left?.label, right?.label);
    }
    if (column === "role") {
        return byText(leftRole, rightRole);
    }
    return byText(left?.subject, right?.subject);
}

class AdminRolesTreeView extends (window.NMPSharedUi?.treeView?.SharedTreeView || class {}) {
    constructor() {
        super({
            headElement: document.getElementById("admin-roles-head"),
            bodyElement: document.getElementById("admin-roles-body"),
            searchInput: document.getElementById("modal-admin-roles-search"),
            sortState: state.adminRolesSort,
            columnAttr: "admin-roles-col",
            renderHead: false,
            manageSortBinding: false,
            manageSearchBinding: false,
            searchThreshold: 5,
            emptyMessage: "Aucun role",
            getRows: () => adminRoleRows(),
            searchText: (row) => `${String(row?.code || "")} ${String(row?.label || "")} ${adminRoleModulesText(row)}`,
            compareRows: (column, direction, left, right) => compareAdminRoleRows(column, direction, left, right),
            getRowKey: (row) => String(row?.code || ""),
            renderRowCells: (row) => `
                <td>${escapeHtml(String(row?.code || ""))}</td>
                <td>${escapeHtml(String(row?.label || ""))}</td>
                <td>${escapeHtml(adminRoleModulesText(row))}</td>
                <td class="inventory-row-actions">
                    ${createIconActionButtonMarkup({
                        icon: "settings",
                        action: "admin-role-edit",
                        title: "Modifier",
                        data: {
                            role_code: String(row?.code || ""),
                            role_version_token: String(row?.version_token || ""),
                        },
                    })}
                    ${createIconActionButtonMarkup({
                        icon: "delete",
                        danger: true,
                        action: "admin-role-delete",
                        title: "Supprimer",
                        data: {
                            role_code: String(row?.code || ""),
                            role_version_token: String(row?.version_token || ""),
                        },
                    })}
                </td>
            `,
        });
    }
}

class AdminUsersTreeView extends (window.NMPSharedUi?.treeView?.SharedTreeView || class {}) {
    constructor() {
        super({
            headElement: document.getElementById("admin-users-head"),
            bodyElement: document.getElementById("admin-users-body"),
            searchInput: document.getElementById("modal-admin-users-search"),
            sortState: state.adminUsersSort,
            columnAttr: "admin-users-col",
            renderHead: false,
            manageSortBinding: false,
            manageSearchBinding: false,
            searchThreshold: 5,
            emptyMessage: "Aucun compte applicatif",
            getRows: () => adminUserRows(),
            searchText: (row) => `${String(row?.subject || "")} ${String(row?.label || "")} ${String((row?.role_codes || [])[0] || "-")}`,
            compareRows: (column, direction, left, right) => compareAdminUserRows(column, direction, left, right),
            getRowKey: (row) => String(row?.subject || ""),
            renderRowCells: (row) => `
                <td>${escapeHtml(String(row?.subject || ""))}</td>
                <td>${escapeHtml(String(row?.label || ""))}</td>
                <td>${escapeHtml(String((row?.role_codes || [])[0] || "-"))}</td>
                <td class="inventory-row-actions">
                    ${createIconActionButtonMarkup({
                        icon: "settings",
                        action: "admin-user-edit",
                        title: "Modifier",
                        data: {
                            user_subject: String(row?.subject || ""),
                            user_version_token: String(row?.version_token || ""),
                        },
                    })}
                    ${createIconActionButtonMarkup({
                        icon: "delete",
                        danger: true,
                        action: "admin-user-delete",
                        title: "Supprimer",
                        data: {
                            user_subject: String(row?.subject || ""),
                            user_version_token: String(row?.version_token || ""),
                        },
                    })}
                </td>
            `,
        });
    }
}

function ensureAdminRolesTreeView() {
    const BaseClass = window.NMPSharedUi?.treeView?.SharedTreeView;
    if (!BaseClass) {
        return null;
    }
    const currentHead = document.getElementById("admin-roles-head");
    const currentBody = document.getElementById("admin-roles-body");
    if (!(currentHead instanceof HTMLElement) || !(currentBody instanceof HTMLElement)) {
        return null;
    }
    if (
        adminRolesTreeView instanceof AdminRolesTreeView
        && adminRolesTreeView.headElement === currentHead
        && adminRolesTreeView.bodyElement === currentBody
    ) {
        return adminRolesTreeView;
    }
    adminRolesTreeView = new AdminRolesTreeView();
    return adminRolesTreeView;
}

function ensureAdminUsersTreeView() {
    const BaseClass = window.NMPSharedUi?.treeView?.SharedTreeView;
    if (!BaseClass) {
        return null;
    }
    const currentHead = document.getElementById("admin-users-head");
    const currentBody = document.getElementById("admin-users-body");
    if (!(currentHead instanceof HTMLElement) || !(currentBody instanceof HTMLElement)) {
        return null;
    }
    if (
        adminUsersTreeView instanceof AdminUsersTreeView
        && adminUsersTreeView.headElement === currentHead
        && adminUsersTreeView.bodyElement === currentBody
    ) {
        return adminUsersTreeView;
    }
    adminUsersTreeView = new AdminUsersTreeView();
    return adminUsersTreeView;
}

function renderRolesTreeView() {
    const tree = ensureAdminRolesTreeView();
    if (tree) {
        tree.render();
        return;
    }
    const searchInput = document.getElementById("modal-admin-roles-search");
    const query = String(searchInput instanceof HTMLInputElement ? searchInput.value : "").trim().toLowerCase();
    const sourceRows = adminRoleRows();
    tableUpdateSearchVisibility(searchInput instanceof HTMLInputElement ? searchInput : null, sourceRows.length, 5);
    const rows = sourceRows
        .filter((row) => !query || `${String(row?.code || "")} ${String(row?.label || "")} ${adminRoleModulesText(row)}`.toLowerCase().includes(query))
        .sort((left, right) => compareAdminRoleRows(state.adminRolesSort.column, state.adminRolesSort.direction, left, right));
    const tbody = document.getElementById("admin-roles-body");
    if (!(tbody instanceof HTMLElement)) {
        return;
    }
    if (!rows.length) {
        tbody.innerHTML = "<tr><td colspan='4'>Aucun role</td></tr>";
        return;
    }
    tbody.innerHTML = rows.map((row) => `
        <tr>
            <td>${escapeHtml(String(row?.code || ""))}</td>
            <td>${escapeHtml(String(row?.label || ""))}</td>
            <td>${escapeHtml(adminRoleModulesText(row))}</td>
            <td class="inventory-row-actions">
                ${createIconActionButtonMarkup({
                    icon: "settings",
                    action: "admin-role-edit",
                    title: "Modifier",
                    data: {
                        role_code: String(row?.code || ""),
                        role_version_token: String(row?.version_token || ""),
                    },
                })}
                ${createIconActionButtonMarkup({
                    icon: "delete",
                    danger: true,
                    action: "admin-role-delete",
                    title: "Supprimer",
                    data: {
                        role_code: String(row?.code || ""),
                        role_version_token: String(row?.version_token || ""),
                    },
                })}
            </td>
        </tr>
    `).join("");
}

function renderUsersTreeView() {
    const tree = ensureAdminUsersTreeView();
    if (tree) {
        tree.render();
        return;
    }
    const searchInput = document.getElementById("modal-admin-users-search");
    const query = String(searchInput instanceof HTMLInputElement ? searchInput.value : "").trim().toLowerCase();
    const sourceRows = adminUserRows();
    tableUpdateSearchVisibility(searchInput instanceof HTMLInputElement ? searchInput : null, sourceRows.length, 5);
    const rows = sourceRows
        .filter((row) => !query || `${String(row?.subject || "")} ${String(row?.label || "")} ${String((row?.role_codes || [])[0] || "-")}`.toLowerCase().includes(query))
        .sort((left, right) => compareAdminUserRows(state.adminUsersSort.column, state.adminUsersSort.direction, left, right));
    const tbody = document.getElementById("admin-users-body");
    if (!(tbody instanceof HTMLElement)) {
        return;
    }
    if (!rows.length) {
        tbody.innerHTML = "<tr><td colspan='4'>Aucun compte applicatif</td></tr>";
        return;
    }
    tbody.innerHTML = rows.map((row) => `
        <tr>
            <td>${escapeHtml(String(row?.subject || ""))}</td>
            <td>${escapeHtml(String(row?.label || ""))}</td>
            <td>${escapeHtml(String((row?.role_codes || [])[0] || "-"))}</td>
            <td class="inventory-row-actions">
                ${createIconActionButtonMarkup({
                    icon: "settings",
                    action: "admin-user-edit",
                    title: "Modifier",
                    data: {
                        user_subject: String(row?.subject || ""),
                        user_version_token: String(row?.version_token || ""),
                    },
                })}
                ${createIconActionButtonMarkup({
                    icon: "delete",
                    danger: true,
                    action: "admin-user-delete",
                    title: "Supprimer",
                    data: {
                        user_subject: String(row?.subject || ""),
                        user_version_token: String(row?.version_token || ""),
                    },
                })}
            </td>
        </tr>
    `).join("");
}

function noCodeServiceTableRows() {
    const systemRows = SYSTEM_SERVICE_MODULE_CODES
        .map((moduleCode) => {
            const moduleRow = findAdminModuleRow(moduleCode);
            if (!moduleRow) {
                return null;
            }
            const known = MODULE_META[moduleCode] || {};
            const serviceCode = extractServiceCodeFromRoutePath(portalModuleRoutePath(moduleRow));
            const service = serviceCode ? findNoCodeService(serviceCode) : null;
            return {
                row_kind: "system_module",
                code: moduleCode,
                module_code: moduleCode,
                route_path: portalModuleRoutePath(moduleRow),
                label: String(moduleRow?.label || known.title || moduleCode).trim() || moduleCode,
                is_active: Boolean(moduleRow?.is_active),
                is_system: true,
                credentials_enabled: Boolean(service?.credentials_enabled),
                fields_count: service ? noCodeCustomServiceFields(service).length : 0,
                icon: String(service?.icon || ""),
                color: String(service?.color || ""),
                child_label: "",
                version_token: String(service?.version_token || ""),
            };
        })
        .filter(Boolean);
    const dynamicRows = noCodeServiceRows()
        .filter((service) => !isSystemNoCodeService(service))
        .map((service) => ({
            row_kind: "service",
            code: String(service?.code || "").trim(),
            label: String(service?.label || service?.code || "").trim() || String(service?.code || ""),
            is_active: Boolean(service?.is_active),
            is_system: Boolean(service?.is_system),
            credentials_enabled: Boolean(service?.credentials_enabled),
            fields_count: noCodeCustomServiceFields(service).length,
            icon: String(service?.icon || ""),
            color: String(service?.color || ""),
            child_label: Boolean(service?.child_enabled) ? String(service?.child_label || "Elements lies").trim() || "Elements lies" : "",
            version_token: String(service?.version_token || ""),
        }));
    return [...systemRows, ...dynamicRows];
}

function isReservedSystemEntityCode(serviceOrCode) {
    const code = typeof serviceOrCode === "string"
        ? serviceOrCode
        : String(serviceOrCode?.code || "").trim();
    const normalized = normalizeNoCodeText(code).toLowerCase();
    return new Set([
        "utilisateur",
        "utilisateurs",
        "user",
        "users",
        "agent",
        "agents",
        "service",
        "services",
        "ou",
        "ous",
        "organisation",
        "organisations",
        "organization",
        "organizations",
    ]).has(normalized) || ["utilisateurs", "services"].includes(normalizeNoCodeRelationEntityCode(normalized));
}

function isSystemNoCodeService(serviceOrCode) {
    const code = typeof serviceOrCode === "string"
        ? serviceOrCode
        : String(serviceOrCode?.code || "").trim();
    return Boolean(typeof serviceOrCode === "object" && serviceOrCode?.is_system)
        || normalizeNoCodeText(code).toLowerCase() === "emails";
}

function compareNoCodeServiceRows(column, direction, left, right) {
    const dir = direction === "desc" ? -1 : 1;
    const byText = (a, b) => String(a || "").localeCompare(String(b || ""), undefined, { sensitivity: "base" }) * dir;
    if (column === "label") {
        return byText(left?.label, right?.label);
    }
    if (column === "status") {
        return (Number(Boolean(left?.is_active)) - Number(Boolean(right?.is_active))) * dir;
    }
    if (column === "credentials") {
        return (Number(Boolean(left?.credentials_enabled)) - Number(Boolean(right?.credentials_enabled))) * dir;
    }
    if (column === "fields") {
        return (Number(left?.fields_count || 0) - Number(right?.fields_count || 0)) * dir;
    }
    return byText(left?.code, right?.code);
}

class NoCodeServicesTreeView extends (window.NMPSharedUi?.treeView?.SharedTreeView || class {}) {
    constructor() {
        super({
            headElement: document.getElementById("no-code-services-head"),
            bodyElement: document.getElementById("no-code-services-body"),
            searchInput: document.getElementById("no-code-services-search"),
            sortState: state.noCodeServicesSort,
            columnAttr: "no-code-services-col",
            renderHead: false,
            manageSortBinding: true,
            manageSearchBinding: true,
            searchThreshold: 5,
            emptyMessage: "Aucun service",
            getRows: () => noCodeServiceTableRows(),
            searchText: (row) => `${String(row?.code || "")} ${String(row?.label || "")} ${String(row?.child_label || "")}`,
            compareRows: (column, direction, left, right) => compareNoCodeServiceRows(column, direction, left, right),
            getRowKey: (row) => String(row?.code || ""),
            renderRowCells: (row) => {
                const isSystemModule = String(row?.row_kind || "") === "system_module";
                const isSystem = Boolean(row?.is_system);
                const active = Boolean(row?.is_active);
                const credentials = Boolean(row?.credentials_enabled);
                const code = String(row?.code || "");
                const moduleCode = String(row?.module_code || code);
                const token = String(row?.version_token || "");
                return `
                    <td>${escapeHtml(code)}</td>
                    <td>${escapeHtml(String(row?.label || code))}</td>
                    <td>${active ? "actif" : "desactive"}</td>
                    <td>${credentials ? "actifs" : "inactifs"}</td>
                    <td>${isSystemModule ? "-" : escapeHtml(String(row?.fields_count || 0))}</td>
                    <td class="inventory-row-actions">
                        ${isSystemModule
        ? createActionButtonMarkup({
            className: "inventory-action-btn",
            type: "button",
            action: "service:module:toggle-active",
            label: active ? "OFF" : "ON",
            title: active ? "Masquer la tuile" : "Afficher la tuile",
            data: { module_code: moduleCode },
        })
        : [
            createActionButtonMarkup({
                className: "inventory-action-btn",
                type: "button",
                action: "service:definition:toggle-active",
                label: active ? "OFF" : "ON",
                title: active ? "Masquer la tuile" : "Afficher la tuile",
                data: { service_code: code, service_version_token: token },
            }),
            createIconActionButtonMarkup({
                icon: "list",
                action: "service:records:open",
                title: "Donnees",
                data: { service_code: code, service_version_token: token },
            }),
            createIconActionButtonMarkup({
                icon: "settings",
                action: "service:definition:edit",
                title: isSystem ? "Module socle protege: definition non modifiable" : "Modifier",
                data: { service_code: code, service_version_token: token },
                disabled: isSystem,
            }),
            createIconActionButtonMarkup({
                icon: "delete",
                danger: true,
                action: "service:definition:delete",
                title: isSystem ? "Module socle protege: suppression interdite" : "Supprimer",
                data: { service_code: code, service_version_token: token },
                disabled: isSystem,
            }),
        ].join("")}
                    </td>
                `;
            },
        });
    }
}

function sharedListTableRows() {
    return sharedListRows().map((row) => ({
        code: String(row?.code || "").trim().toLowerCase(),
        label: String(row?.label || row?.code || "").trim(),
        item_count: Number(row?.item_count || 0),
        is_system: Boolean(row?.is_system),
        version_token: String(row?.version_token || "").trim(),
    }));
}

function compareSharedListRows(column, direction, left, right) {
    const dir = direction === "desc" ? -1 : 1;
    const byText = (a, b) => String(a || "").localeCompare(String(b || ""), undefined, { sensitivity: "base" }) * dir;
    if (column === "label") {
        return byText(left?.label, right?.label);
    }
    if (column === "item_count") {
        return (Number(left?.item_count || 0) - Number(right?.item_count || 0)) * dir;
    }
    if (column === "is_system") {
        return (Number(Boolean(left?.is_system)) - Number(Boolean(right?.is_system))) * dir;
    }
    return byText(left?.code, right?.code);
}

class SharedListsTreeView extends (window.NMPSharedUi?.treeView?.SharedTreeView || class {}) {
    constructor() {
        super({
            headElement: document.getElementById("shared-lists-head"),
            bodyElement: document.getElementById("shared-lists-body"),
            searchInput: document.getElementById("shared-lists-search"),
            sortState: state.sharedListsSort,
            columnAttr: "shared-lists-col",
            renderHead: false,
            manageSortBinding: true,
            manageSearchBinding: true,
            searchThreshold: 5,
            emptyMessage: "Aucune liste partagee definie.",
            getRows: () => sharedListTableRows(),
            searchText: (row) => `${String(row?.code || "")} ${String(row?.label || "")}`,
            compareRows: (column, direction, left, right) => compareSharedListRows(column, direction, left, right),
            getRowKey: (row) => String(row?.code || ""),
            renderRowCells: (row) => `
                <td>${escapeHtml(String(row?.code || ""))}</td>
                <td>${escapeHtml(String(row?.label || row?.code || ""))}</td>
                <td class="cell-center">${escapeHtml(String(row?.item_count || 0))}</td>
                <td class="cell-center">${row?.is_system ? "Oui" : "Non"}</td>
                <td class="inventory-row-actions">
                    ${createIconActionButtonMarkup({
                        icon: "list",
                        action: "shared-list:items",
                        title: "Valeurs",
                        data: { list_code: String(row?.code || "") },
                    })}
                    ${createIconActionButtonMarkup({
                        icon: "settings",
                        action: "shared-list:edit",
                        title: "Modifier",
                        data: { list_code: String(row?.code || "") },
                    })}
                    ${createIconActionButtonMarkup({
                        icon: "delete",
                        danger: true,
                        action: "shared-list:delete",
                        title: "Supprimer",
                        data: {
                            list_code: String(row?.code || ""),
                            list_version_token: String(row?.version_token || ""),
                        },
                        disabled: Boolean(row?.is_system),
                    })}
                </td>
            `,
        });
    }
}

function sharedListItemRows() {
    const context = state.noCodeSharedListItemsContext;
    return Array.isArray(context?.items) ? context.items.map((item) => ({
        code: String(item?.code || "").trim().toLowerCase(),
        label: String(item?.label || item?.code || "").trim(),
        is_active: Boolean(item?.is_active),
        sort_order: Number(item?.sort_order || 100),
        version_token: String(item?.version_token || "").trim(),
    })) : [];
}

function compareSharedListItemRows(column, direction, left, right) {
    const dir = direction === "desc" ? -1 : 1;
    const byText = (a, b) => String(a || "").localeCompare(String(b || ""), undefined, { sensitivity: "base" }) * dir;
    if (column === "label") {
        return byText(left?.label, right?.label);
    }
    if (column === "is_active") {
        return (Number(Boolean(left?.is_active)) - Number(Boolean(right?.is_active))) * dir;
    }
    if (column === "sort_order") {
        return (Number(left?.sort_order || 0) - Number(right?.sort_order || 0)) * dir;
    }
    return byText(left?.code, right?.code);
}

class SharedListItemsTreeView extends (window.NMPSharedUi?.treeView?.SharedTreeView || class {}) {
    constructor() {
        super({
            headElement: document.getElementById("shared-list-items-head"),
            bodyElement: document.getElementById("shared-list-items-body"),
            searchInput: document.getElementById("shared-list-items-search"),
            sortState: state.sharedListItemsSort,
            columnAttr: "shared-list-items-col",
            renderHead: false,
            manageSortBinding: true,
            manageSearchBinding: true,
            searchThreshold: 5,
            emptyMessage: "Aucune valeur definie.",
            getRows: () => sharedListItemRows(),
            searchText: (row) => `${String(row?.code || "")} ${String(row?.label || "")}`,
            compareRows: (column, direction, left, right) => compareSharedListItemRows(column, direction, left, right),
            getRowKey: (row) => String(row?.code || ""),
            renderRowCells: (row) => `
                <td>${escapeHtml(String(row?.code || ""))}</td>
                <td>${escapeHtml(String(row?.label || row?.code || ""))}</td>
                <td class="cell-center">${row?.is_active ? "Oui" : "Non"}</td>
                <td class="cell-center">${escapeHtml(String(row?.sort_order || 100))}</td>
                <td class="inventory-row-actions">
                    ${createIconActionButtonMarkup({
                        icon: "settings",
                        action: "shared-list-item:edit",
                        title: "Modifier",
                        data: { item_code: String(row?.code || "") },
                    })}
                    ${createIconActionButtonMarkup({
                        icon: "delete",
                        danger: true,
                        action: "shared-list-item:delete",
                        title: "Supprimer",
                        data: {
                            item_code: String(row?.code || ""),
                            item_version_token: String(row?.version_token || ""),
                        },
                    })}
                </td>
            `,
        });
    }
}

function ensureNoCodeServicesTreeView() {
    const BaseClass = window.NMPSharedUi?.treeView?.SharedTreeView;
    if (!BaseClass) {
        return null;
    }
    const currentHead = document.getElementById("no-code-services-head");
    const currentBody = document.getElementById("no-code-services-body");
    if (!(currentHead instanceof HTMLElement) || !(currentBody instanceof HTMLElement)) {
        return null;
    }
    if (
        noCodeServicesTreeView instanceof NoCodeServicesTreeView
        && noCodeServicesTreeView.headElement === currentHead
        && noCodeServicesTreeView.bodyElement === currentBody
    ) {
        return noCodeServicesTreeView;
    }
    noCodeServicesTreeView = new NoCodeServicesTreeView();
    return noCodeServicesTreeView;
}

function ensureSharedListsTreeView() {
    const BaseClass = window.NMPSharedUi?.treeView?.SharedTreeView;
    if (!BaseClass) {
        return null;
    }
    const currentHead = document.getElementById("shared-lists-head");
    const currentBody = document.getElementById("shared-lists-body");
    if (!(currentHead instanceof HTMLElement) || !(currentBody instanceof HTMLElement)) {
        return null;
    }
    if (
        sharedListsTreeView instanceof SharedListsTreeView
        && sharedListsTreeView.headElement === currentHead
        && sharedListsTreeView.bodyElement === currentBody
    ) {
        return sharedListsTreeView;
    }
    sharedListsTreeView = new SharedListsTreeView();
    return sharedListsTreeView;
}

function ensureSharedListItemsTreeView() {
    const BaseClass = window.NMPSharedUi?.treeView?.SharedTreeView;
    if (!BaseClass) {
        return null;
    }
    const currentHead = document.getElementById("shared-list-items-head");
    const currentBody = document.getElementById("shared-list-items-body");
    if (!(currentHead instanceof HTMLElement) || !(currentBody instanceof HTMLElement)) {
        return null;
    }
    if (
        sharedListItemsTreeView instanceof SharedListItemsTreeView
        && sharedListItemsTreeView.headElement === currentHead
        && sharedListItemsTreeView.bodyElement === currentBody
    ) {
        return sharedListItemsTreeView;
    }
    sharedListItemsTreeView = new SharedListItemsTreeView();
    return sharedListItemsTreeView;
}

function renderNoCodeServicesTreeView() {
    const tree = ensureNoCodeServicesTreeView();
    if (tree) {
        tree.render();
    }
}

function renderSharedListsTreeView() {
    const tree = ensureSharedListsTreeView();
    if (tree) {
        tree.render();
    }
}

function renderSharedListItemsTreeView() {
    const tree = ensureSharedListItemsTreeView();
    if (tree) {
        tree.render();
    }
}

function buildWebServerSettingsMarkup(settings) {
    const sharedBuilder = window.NMPSharedUi?.webServer?.buildSettingsMarkup;
    if (typeof sharedBuilder === "function") {
        return sharedBuilder({
            settings,
            field: (key, label, value, wide = false) => createFieldMarkup(key, label, value, wide),
        });
    }
    const rawProxy = String(settings.web_server_reverse_proxy_type || "aucun").trim().toLowerCase();
    const reverseProxyType = ["aucun", "nginx", "caddy"].includes(rawProxy) ? rawProxy : "aucun";
    return `
    <form id="modal-webserver-form" class="modal-form">
        <div class="modal-settings-grid">
            ${createFieldMarkup("web_server_host", "Host", settings.web_server_host || "127.0.0.1")}
            ${createFieldMarkup("web_server_port", "Port", settings.web_server_port || 8000)}
            ${createFieldMarkup("web_server_public_url", "URL publique", settings.web_server_public_url || "", true)}
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

function notificationTaskStatusLabel(status) {
    const value = String(status || "").trim().toLowerCase();
    if (value === "pending") return "En attente";
    if (value === "sent") return "Envoyee";
    if (value === "done") return "Traitee";
    if (value === "cancelled") return "Annulee";
    return value || "-";
}

function formatNotificationTaskDate(value) {
    const raw = String(value || "").trim();
    if (!raw) {
        return "-";
    }
    return raw.slice(0, 16).replace("T", " ");
}

function notificationTaskSourceLabel(task) {
    const serviceCode = String(task?.source_service_code || "").trim();
    const recordId = String(task?.source_record_id || "").trim();
    return [serviceCode, recordId].filter(Boolean).join(" / ") || "-";
}

function compareNotificationTaskRows(column, direction, left, right) {
    const dir = direction === "desc" ? -1 : 1;
    const byText = (a, b) => String(a || "").localeCompare(String(b || ""), undefined, { sensitivity: "base" }) * dir;
    if (column === "title") {
        return byText(left?.title, right?.title);
    }
    if (column === "source") {
        return byText(notificationTaskSourceLabel(left), notificationTaskSourceLabel(right));
    }
    if (column === "status") {
        return byText(notificationTaskStatusLabel(left?.status), notificationTaskStatusLabel(right?.status));
    }
    if (column === "sent_at") {
        return byText(left?.sent_at, right?.sent_at);
    }
    return byText(left?.due_at, right?.due_at);
}

class NotificationTasksTreeView extends (window.NMPSharedUi?.treeView?.SharedTreeView || class {}) {
    constructor() {
        super({
            headElement: document.getElementById("notification-tasks-head"),
            bodyElement: document.getElementById("notification-tasks-body"),
            searchInput: document.getElementById("modal-notification-tasks-search"),
            sortState: state.notificationTasksSort,
            columnAttr: "notification-tasks-col",
            searchThreshold: 5,
            emptyMessage: "Aucune tache de notification.",
            columnVisibilityStorageKey: "nmp:treeview:columns:notification-tasks",
            getRows: () => Array.isArray(state.notificationTasks) ? state.notificationTasks : [],
            getColumns: () => [
                { key: "due_at", label: "Echeance", renderCell: (row) => escapeHtml(formatNotificationTaskDate(row?.due_at)) },
                { key: "title", label: "Tache", renderCell: (row) => `
                    <strong>${escapeHtml(String(row?.title || "-"))}</strong>
                    <span class="muted">${escapeHtml(String(row?.message || ""))}</span>
                ` },
                { key: "source", label: "Source", renderCell: (row) => escapeHtml(notificationTaskSourceLabel(row)) },
                { key: "status", label: "Statut", renderCell: (row) => escapeHtml(notificationTaskStatusLabel(row?.status)) },
                { key: "sent_at", label: "Envoyee le", renderCell: (row) => escapeHtml(formatNotificationTaskDate(row?.sent_at)) },
                { key: "actions", label: "Actions", sortable: false, renderCell: (row) => {
                    const id = String(row?.id || "");
                    const isPending = String(row?.status || "pending").trim().toLowerCase() === "pending";
                    return `
                        <div class="inventory-row-actions">
                            <button class="toolbar-btn compact" type="button" data-action="notification:task:done" data-task-id="${escapeHtml(id)}" ${isPending ? "" : "disabled"}>Cloturer</button>
                            <button class="toolbar-btn compact" type="button" data-action="notification:task:cancel" data-task-id="${escapeHtml(id)}" ${isPending ? "" : "disabled"}>Annuler</button>
                        </div>
                    `;
                } },
            ],
            searchText: (row) => `${String(row?.title || "")} ${String(row?.message || "")} ${notificationTaskSourceLabel(row)} ${notificationTaskStatusLabel(row?.status)}`,
            compareRows: (column, direction, left, right) => compareNotificationTaskRows(column, direction, left, right),
            getRowKey: (row) => String(row?.id || ""),
        });
    }
}

function ensureNotificationTasksTreeView() {
    const BaseClass = window.NMPSharedUi?.treeView?.SharedTreeView;
    if (!BaseClass) {
        return null;
    }
    const currentHead = document.getElementById("notification-tasks-head");
    const currentBody = document.getElementById("notification-tasks-body");
    if (!(currentHead instanceof HTMLElement) || !(currentBody instanceof HTMLElement)) {
        return null;
    }
    if (
        notificationTasksTreeView instanceof NotificationTasksTreeView
        && notificationTasksTreeView.headElement === currentHead
        && notificationTasksTreeView.bodyElement === currentBody
    ) {
        return notificationTasksTreeView;
    }
    notificationTasksTreeView = new NotificationTasksTreeView();
    return notificationTasksTreeView;
}

function renderNotificationTasksTreeView() {
    const tree = ensureNotificationTasksTreeView();
    if (tree) {
        tree.render();
    }
}

const NOTIFICATION_TEMPLATE_TASK_TYPES = [
    { value: "", label: "Toutes les taches" },
    { value: "status:à supprimer", label: "Email a supprimer" },
    { value: "status:a supprimer", label: "Email a supprimer (sans accent)" },
    { value: "status", label: "Changement de statut" },
    { value: "generic:reminder", label: "Rappel general" },
    { value: "monitoring:status_change", label: "Monitoring - changement d'etat" },
];

const NOTIFICATION_TEMPLATE_VARIABLES = [
    { key: "task.label", label: "Nom de la tache" },
    { key: "task.message", label: "Message initial" },
    { key: "task.due_at", label: "Date d'echeance" },
    { key: "module.code", label: "Module" },
    { key: "record.id", label: "Element concerne" },
    { key: "trigger.value", label: "Valeur declencheur" },
    { key: "app.name", label: "Application" },
];

function notificationTemplateTaskTypeLabel(value) {
    const raw = String(value || "").trim().toLowerCase();
    return NOTIFICATION_TEMPLATE_TASK_TYPES.find((item) => item.value.toLowerCase() === raw)?.label || raw || "Toutes les taches";
}

function notificationTemplateModuleLabel(value) {
    const raw = String(value || "").trim().toLowerCase();
    if (!raw) return "Tous les modules";
    if (raw === "emails") return "Emails";
    if (raw === "monitoring") return "Monitoring";
    return raw;
}

function compareNotificationTemplateRows(column, direction, left, right) {
    const dir = direction === "desc" ? -1 : 1;
    const byText = (a, b) => String(a || "").localeCompare(String(b || ""), undefined, { sensitivity: "base" }) * dir;
    if (column === "module_code") return byText(notificationTemplateModuleLabel(left?.module_code), notificationTemplateModuleLabel(right?.module_code));
    if (column === "task_type") return byText(notificationTemplateTaskTypeLabel(left?.task_type), notificationTemplateTaskTypeLabel(right?.task_type));
    if (column === "is_active") return (Number(Boolean(left?.is_active)) - Number(Boolean(right?.is_active))) * dir;
    return byText(left?.label || left?.code, right?.label || right?.code);
}

class NotificationTemplatesTreeView extends (window.NMPSharedUi?.treeView?.SharedTreeView || class {}) {
    constructor() {
        super({
            headElement: document.getElementById("notification-templates-head"),
            bodyElement: document.getElementById("notification-templates-body"),
            searchInput: document.getElementById("modal-notification-templates-search"),
            sortState: state.notificationTemplatesSort,
            columnAttr: "notification-templates-col",
            searchThreshold: 5,
            emptyMessage: "Aucun template de notification.",
            columnVisibilityStorageKey: "nmp:treeview:columns:notification-templates",
            getRows: () => Array.isArray(state.notificationTemplates) ? state.notificationTemplates : [],
            getColumns: () => [
                { key: "label", label: "Template", renderCell: (row) => `
                    <strong>${escapeHtml(String(row?.label || row?.code || "-"))}</strong>
                    <span class="muted">${escapeHtml(String(row?.subject_template || ""))}</span>
                ` },
                { key: "module_code", label: "Module", renderCell: (row) => escapeHtml(notificationTemplateModuleLabel(row?.module_code)) },
                { key: "task_type", label: "Type de tache", renderCell: (row) => escapeHtml(notificationTemplateTaskTypeLabel(row?.task_type)) },
                { key: "is_active", label: "Statut", renderCell: (row) => escapeHtml(row?.is_active ? "Actif" : "Inactif") },
                { key: "actions", label: "Actions", sortable: false, renderCell: (row) => {
                    const code = String(row?.code || "");
                    return `
                        <div class="inventory-row-actions">
                            ${createIconActionButtonMarkup({ icon: "settings", action: "notification:template:edit", title: "Modifier", data: { template_code: code } })}
                            ${createIconActionButtonMarkup({ icon: "delete", danger: true, action: "notification:template:delete", title: "Supprimer", data: { template_code: code } })}
                        </div>
                    `;
                } },
            ],
            searchText: (row) => `${String(row?.code || "")} ${String(row?.label || "")} ${String(row?.subject_template || "")} ${notificationTemplateModuleLabel(row?.module_code)} ${notificationTemplateTaskTypeLabel(row?.task_type)}`,
            compareRows: (column, direction, left, right) => compareNotificationTemplateRows(column, direction, left, right),
            getRowKey: (row) => String(row?.code || ""),
        });
    }
}

function ensureNotificationTemplatesTreeView() {
    const BaseClass = window.NMPSharedUi?.treeView?.SharedTreeView;
    if (!BaseClass) return null;
    const currentHead = document.getElementById("notification-templates-head");
    const currentBody = document.getElementById("notification-templates-body");
    if (!(currentHead instanceof HTMLElement) || !(currentBody instanceof HTMLElement)) return null;
    if (
        notificationTemplatesTreeView instanceof NotificationTemplatesTreeView
        && notificationTemplatesTreeView.headElement === currentHead
        && notificationTemplatesTreeView.bodyElement === currentBody
    ) {
        return notificationTemplatesTreeView;
    }
    notificationTemplatesTreeView = new NotificationTemplatesTreeView();
    return notificationTemplatesTreeView;
}

function renderNotificationTemplatesTreeView() {
    const tree = ensureNotificationTemplatesTreeView();
    if (tree) tree.render();
}

function buildNotificationTemplatesModalMarkup() {
    return buildTreeSectionMarkup({
        title: "Templates de mail",
        description: "Modeles utilises par le moteur de notification selon le module et le type de tache.",
        searchId: "modal-notification-templates-search",
        searchLabel: "Recherche",
        searchPlaceholder: "Template, module, sujet...",
        searchInTitleRow: true,
        headId: "notification-templates-head",
        bodyId: "notification-templates-body",
        feedbackId: "modal-notification-templates-feedback",
        tableClassName: "device-table inventory-table",
        tableWrapClassName: "notification-task-list",
        titleActionsMarkup: `
            <button class="toolbar-btn compact" type="button" data-action="notification:templates:refresh">Rafraichir</button>
            <button class="toolbar-btn compact primary" type="button" data-action="notification:template:create">Ajouter</button>
        `,
        footerActionsMarkup: createModalActionsMarkup({
            buttons: [{ className: "toolbar-btn", type: "button", action: "modal:close", label: "Fermer" }],
        }),
    });
}

function notificationTemplateModuleOptions(selected = "") {
    const normalized = String(selected || "").trim().toLowerCase();
    const dynamic = noCodeServiceRows().map((service) => ({
        value: String(service?.code || "").trim().toLowerCase(),
        label: String(service?.label || service?.code || "").trim(),
    }));
    const options = [
        { value: "", label: "Tous les modules" },
        { value: "emails", label: "Emails" },
        { value: "monitoring", label: "Monitoring" },
        ...dynamic.filter((row) => row.value && !["emails", "monitoring"].includes(row.value)),
    ];
    return options.map((item) => `<option value="${escapeHtml(item.value)}" ${item.value === normalized ? "selected" : ""}>${escapeHtml(item.label)}</option>`).join("");
}

function buildNotificationTemplateEditorMarkup(template = null) {
    const isEdit = Boolean(template?.code);
    const taskType = String(template?.task_type || "");
    return `
    <form id="modal-notification-template-form" class="modal-form notification-template-editor">
        <div class="modal-settings-grid">
            <label class="field">
                <span>Nom du modele</span>
                <input name="label" required value="${escapeHtml(String(template?.label || ""))}" placeholder="Rappel suppression email">
            </label>
            <label class="field">
                <span>Code</span>
                <input name="code" required value="${escapeHtml(String(template?.code || ""))}" ${isEdit ? "readonly" : ""} placeholder="email.delete_reminder">
            </label>
            <label class="field">
                <span>Module</span>
                <select name="module_code">${notificationTemplateModuleOptions(template?.module_code || "")}</select>
            </label>
            <label class="field">
                <span>Type de tache</span>
                <select name="task_type">
                    ${NOTIFICATION_TEMPLATE_TASK_TYPES.map((item) => `<option value="${escapeHtml(item.value)}" ${item.value === taskType ? "selected" : ""}>${escapeHtml(item.label)}</option>`).join("")}
                </select>
            </label>
        </div>
        <label class="field full">
            <span>Sujet du mail</span>
            <input name="subject_template" required data-template-target value="${escapeHtml(String(template?.subject_template || ""))}" placeholder="Rappel ITops - {{task.label}}">
        </label>
        <label class="field full">
            <span>Message</span>
            <textarea name="body_template" rows="9" required data-template-target placeholder="Bonjour,\n\n{{task.message}}\n\nEcheance : {{task.due_at}}">${escapeHtml(String(template?.body_template || ""))}</textarea>
        </label>
        <section class="notification-template-variables">
            <span class="muted">Variables disponibles</span>
            <div>
                ${NOTIFICATION_TEMPLATE_VARIABLES.map((item) => `<button class="toolbar-btn compact" type="button" data-action="notification:template:insert-variable" data-template-variable="${escapeHtml(item.key)}" title="${escapeHtml(item.label)}">{{${escapeHtml(item.key)}}}</button>`).join("")}
            </div>
        </section>
        <div class="modal-settings-grid">
            <label class="check-field"><input name="is_active" type="checkbox" ${template?.is_active !== false ? "checked" : ""}><span>Template actif</span></label>
            <label class="check-field"><input name="is_default" type="checkbox" ${template?.is_default ? "checked" : ""}><span>Template par defaut pour ce module/type</span></label>
        </div>
        <p id="modal-notification-template-feedback" class="muted inventory-feedback"></p>
        ${createModalActionsMarkup({ buttons: [{ preset: "cancel" }, { preset: "save" }] })}
    </form>
    `;
}

function buildNotificationTasksModalMarkup() {
    return buildTreeSectionMarkup({
        title: "Taches planifiees",
        description: "Rappels generaux produits par le moteur de notification.",
        searchId: "modal-notification-tasks-search",
        searchLabel: "Recherche",
        searchPlaceholder: "Titre, source, statut...",
        searchInTitleRow: true,
        headId: "notification-tasks-head",
        bodyId: "notification-tasks-body",
        feedbackId: "modal-notification-tasks-feedback",
        tableClassName: "device-table inventory-table",
        tableWrapClassName: "notification-task-list",
        titleActionsMarkup: `
            <button class="toolbar-btn compact" type="button" data-action="notification:tasks:refresh">Rafraichir</button>
        `,
        footerActionsMarkup: createModalActionsMarkup({
            buttons: [{ className: "toolbar-btn", type: "button", action: "modal:close", label: "Fermer" }],
        }),
    });
}

function buildNotificationSettingsMarkup(settings) {
    const smtpPort = Number(settings.smtp_port || 0);
    const smtpPortValue = Number.isFinite(smtpPort) ? smtpPort : 0;
    const authEnabled = Boolean(settings.smtp_auth_enabled);
    return `
    <form id="modal-notification-form" class="modal-form">
        <div class="modal-settings-grid">
            ${createFieldMarkup("smtp_host", "SMTP host", settings.smtp_host || "")}
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
            ${createFieldMarkup("recipients", "Destinataires", settings.recipients || "", true)}
        </div>
        <label class="check-field">
            <input name="smtp_auth_enabled" type="checkbox" ${authEnabled ? "checked" : ""}>
            <span>Authentification SMTP requise</span>
        </label>
        <div class="modal-settings-grid" data-smtp-auth-fields ${authEnabled ? "" : "hidden"}>
            ${createFieldMarkup("user", "Utilisateur SMTP", settings.user || "")}
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
            buttons: [
                { preset: "cancel" },
                { type: "button", className: "toolbar-btn", action: "notification:test", label: "Tester" },
                { preset: "save" },
            ],
        })}
    </form>
    `;
}

function buildActiveDirectorySettingsMarkup(settings, certificate = {}) {
    const port = Number(settings.active_directory_port || 636);
    const interval = Number(settings.active_directory_sync_interval_seconds || 3600);
    const enabled = Boolean(settings.active_directory_enabled);
    const rawBindUsername = String(settings.active_directory_bind_username || "");
    const bindAccount = activeDirectoryDisplayBindAccount(rawBindUsername);
    const domainSuffix = activeDirectoryDomainSuffix(settings.active_directory_host, rawBindUsername);
    return `
    <form id="modal-active-directory-form" class="modal-form">
        <p class="muted">Connexion LDAP partagee par les futurs profils de synchronisation (Agents, OU, services et groupes). Aucun compte ITops n'est modifie a cette etape.</p>
        <div class="active-directory-sync-toggle">
            <input id="active-directory-enabled" name="active_directory_enabled" type="checkbox" ${enabled ? "checked" : ""} hidden>
            <button class="active-directory-status-btn ${enabled ? "is-enabled" : "is-disabled"}" type="button" data-action="active-directory:toggle-auto-sync" aria-pressed="${enabled ? "true" : "false"}">
                <span class="active-directory-status-dot"></span>
                <span data-active-directory-status-label>${enabled ? "Synchronisation automatique active" : "Synchronisation automatique inactive"}</span>
            </button>
            <span class="muted">Ce bouton active ou suspend les synchronisations planifiees. Le test et la synchro manuelle restent disponibles.</span>
        </div>
        <div class="modal-settings-grid">
            <label class="field"><span>Serveur LDAP / AD</span><input name="active_directory_host" required value="${escapeHtml(String(settings.active_directory_host || ""))}" placeholder="ad.example.local"></label>
            <label class="field"><span>Port</span><input name="active_directory_port" type="number" min="1" max="65535" value="${Number.isFinite(port) ? port : 636}"></label>
            <label class="field"><span>Compte de lecture</span><span class="active-directory-account-input"><input name="active_directory_bind_username" required value="${escapeHtml(bindAccount)}" placeholder="svc_itops_ldap"><span data-active-directory-domain-suffix>${escapeHtml(domainSuffix)}</span></span></label>
            <label class="field"><span>Mot de passe</span><span class="password-reveal-field"><input name="active_directory_bind_password" type="password" autocomplete="new-password" placeholder="Laisser vide pour conserver"><button class="password-reveal-btn" type="button" data-action="password:toggle-visibility" aria-label="Afficher le mot de passe" title="Afficher le mot de passe">${passwordVisibilityIconMarkup(false)}</button></span></label>
            <label class="field full"><span>Base DN</span><input name="active_directory_base_dn" required value="${escapeHtml(String(settings.active_directory_base_dn || ""))}" placeholder="DC=example,DC=local"></label>
            <div class="field full active-directory-certificate-field"><span>Certificat de l'autorite de certification</span><button class="toolbar-btn" type="button" data-action="active-directory:certificate-import">Importer le certificat</button><input id="active-directory-certificate-file" type="file" accept=".pem,.crt,.cer,application/x-pem-file" hidden></div>
        </div>
        <details class="active-directory-advanced">
            <summary>Parametres avances</summary>
            <div class="modal-settings-grid">
                <label class="field full"><span>Filtre agents</span><input name="active_directory_user_filter" value="${escapeHtml(String(settings.active_directory_user_filter || "(&(objectCategory=person)(objectClass=user))"))}"></label>
                <label class="field"><span>Intervalle de synchronisation (secondes)</span><input name="active_directory_sync_interval_seconds" type="number" min="60" value="${Number.isFinite(interval) ? Math.max(60, interval) : 3600}"></label>
                <label class="check-field"><input name="active_directory_sync_email_accounts" type="checkbox" ${settings.active_directory_sync_email_accounts ? "checked" : ""}><span>Synchroniser les comptes Email</span></label>
                <label class="check-field"><input name="active_directory_use_ssl" type="checkbox" ${settings.active_directory_use_ssl !== false ? "checked" : ""}><span>Utiliser LDAPS</span></label>
                <label class="check-field"><input name="active_directory_validate_certificates" type="checkbox" ${settings.active_directory_validate_certificates !== false ? "checked" : ""}><span>Valider le certificat TLS</span></label>
            </div>
        </details>
        <section class="modal-section">
            <h3>Synchronisation manuelle</h3>
            <div class="modal-actions inline-actions">
                <button class="toolbar-btn primary-btn" type="button" data-action="active-directory:sync-now" data-sync-mode="normal">Synchroniser</button>
                <button class="toolbar-btn" type="button" data-action="active-directory:sync-now" data-sync-mode="force_rebuild">Resynchroniser completement</button>
                <button class="toolbar-btn danger" type="button" data-action="active-directory:sync-now" data-sync-mode="reset_ad">Reinitialiser les donnees AD</button>
            </div>
            <p class="muted">La reinitialisation supprime uniquement le cache AD, les liens deduits de l'AD et les comptes Email marques AD. Les donnees saisies manuellement sont conservees.</p>
        </section>
        <p id="modal-active-directory-feedback" class="muted inventory-feedback"></p>
        ${createModalActionsMarkup({ buttons: [{ preset: "cancel" }, { label: "Tester", action: "active-directory:test", type: "button" }, { preset: "save" }] })}
    </form>`;
}

function activeDirectoryDisplayBindAccount(username) {
    const value = String(username || "").trim();
    if (!value || value.includes("\\") || !value.includes("@")) {
        return value;
    }
    return value.split("@", 1)[0] || value;
}

function activeDirectoryDomainFromHost(host) {
    const value = String(host || "").trim().replace(/^\.+|\.+$/g, "");
    if (!value || /^\d{1,3}(?:\.\d{1,3}){3}$/.test(value)) {
        return "";
    }
    const labels = value.split(".").filter(Boolean);
    if (labels.length >= 3) {
        return labels.slice(1).join(".");
    }
    if (labels.length >= 2) {
        return labels.join(".");
    }
    return "";
}

function activeDirectoryDomainSuffix(host, username = "") {
    const value = String(username || "").trim();
    if (value.includes("@") || value.includes("\\")) {
        return "";
    }
    const domain = activeDirectoryDomainFromHost(host);
    return domain ? `@${domain}` : "";
}

function activeDirectoryBuildBindUsername(form) {
    const formData = new window.FormData(form);
    const rawUsername = String(formData.get("active_directory_bind_username") || "").trim();
    if (!rawUsername || rawUsername.includes("@") || rawUsername.includes("\\")) {
        return rawUsername;
    }
    const domain = activeDirectoryDomainFromHost(formData.get("active_directory_host"));
    return domain ? `${rawUsername}@${domain}` : rawUsername;
}

function passwordVisibilityIconMarkup(visible = false) {
    if (visible) {
        return `
            <svg class="password-reveal-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path d="M3 3l18 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                <path d="M10.7 5.1A9.7 9.7 0 0 1 12 5c5 0 8.5 4.2 10 7a17.4 17.4 0 0 1-3.1 4.1" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M6.5 6.5A17.3 17.3 0 0 0 2 12c1.5 2.8 5 7 10 7a9.6 9.6 0 0 0 4.1-.9" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>`;
    }
    return `
        <svg class="password-reveal-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            <circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" stroke-width="2"/>
        </svg>`;
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
            ${createFieldMarkup("notification_cooldown_seconds", "Cooldown notif (s)", settings.notification_cooldown_seconds || 120)}
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
        <p class="muted">Variables disponibles: {device_type}, {device_name}, {device_ip}, {old_status}, {new_status}</p>
        <p id="modal-monitoring-notification-feedback" class="muted inventory-feedback"></p>
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
    await loadPrivateUiConfig();
    showAppSaveFeedback({
        feedback,
        message: "Parametres enregistres.",
    });
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
        await loadPrivateUiConfig();
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

async function openWebServerSettingsModal() {
    const settings = await requestJson("/settings");
    openModal("Parametres serveur web", buildWebServerSettingsMarkup(settings), {
        width: "min(860px, calc(100vw - 40px))",
    });
}

async function openNotificationSettingsModal() {
    const settings = await requestJson("/settings");
    openModal("Notifications - Parametres SMTP", buildNotificationSettingsMarkup(settings), {
        width: "min(860px, calc(100vw - 40px))",
    });
}

async function openNotificationTasksModal() {
    state.notificationTasks = await requestJson("/notifications/tasks");
    notificationTasksTreeView = null;
    openModal("Notifications - Taches planifiees", buildNotificationTasksModalMarkup(), {
        width: "min(1120px, calc(100vw - 40px))",
    });
    renderNotificationTasksTreeView();
}

async function openNotificationTemplatesModal() {
    await loadAdministrationData({
        includeModules: false,
        includeRoles: false,
        includeUsers: false,
        includeServices: true,
        includeSharedLists: false,
    });
    state.notificationTemplates = await requestJson("/notifications/templates");
    notificationTemplatesTreeView = null;
    openModal("Notifications - Templates de mail", buildNotificationTemplatesModalMarkup(), {
        width: "min(1120px, calc(100vw - 40px))",
    });
    renderNotificationTemplatesTreeView();
}

function openNotificationTemplateEditor(template = null) {
    state.notificationTemplateEditor = template ? { ...template } : null;
    openModal(
        template ? "Modifier le template" : "Nouveau template",
        buildNotificationTemplateEditorMarkup(template),
        { width: "min(880px, calc(100vw - 40px))" },
    );
}

async function openMonitoringNotificationSettingsModal() {
    const settings = await requestJson("/settings");
    openModal("Notifications Monitoring", buildMonitoringNotificationSettingsMarkup(settings), {
        width: "min(920px, calc(100vw - 40px))",
    });
}

function buildNotificationPatchFromForm(form) {
    const formData = new window.FormData(form);
    const smtpPort = Number(formData.get("smtp_port") || 0);
    return {
        smtp_host: String(formData.get("smtp_host") || "").trim(),
        smtp_port: Number.isFinite(smtpPort) ? smtpPort : 0,
        smtp_auth_enabled: form.querySelector('[name="smtp_auth_enabled"]')?.checked ?? false,
        user: String(formData.get("user") || "").trim(),
        smtp_password: String(formData.get("smtp_password") || ""),
        recipients: String(formData.get("recipients") || "").trim(),
        use_tls: form.querySelector('[name="use_tls"]')?.checked ?? false,
        show_status_popup: form.querySelector('[name="show_status_popup"]')?.checked ?? true,
    };
}

async function submitNotificationSettings(form, { closeOnSuccess = true } = {}) {
    const feedback = document.getElementById("modal-notification-feedback");
    try {
        await applySettingsPatch(
            buildNotificationPatchFromForm(form),
            "modal-notification-feedback",
        );
        if (closeOnSuccess) {
            window.setTimeout(() => closeModal(), 400);
        }
    } catch (error) {
        if (feedback instanceof HTMLElement) {
            feedback.textContent = normalizeErrorMessage(error.message);
        }
        return false;
    }
    return true;
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
    }
}

async function submitNotificationTemplate(form) {
    const feedback = document.getElementById("modal-notification-template-feedback");
    const formData = new window.FormData(form);
    const payload = {
        code: normalizeNoCodeText(formData.get("code")).toLowerCase(),
        label: String(formData.get("label") || "").trim(),
        module_code: String(formData.get("module_code") || "").trim().toLowerCase(),
        task_type: String(formData.get("task_type") || "").trim().toLowerCase(),
        subject_template: String(formData.get("subject_template") || "").trim(),
        body_template: String(formData.get("body_template") || "").trim(),
        is_active: form.querySelector('[name="is_active"]')?.checked ?? true,
        is_default: form.querySelector('[name="is_default"]')?.checked ?? false,
    };
    if (!payload.code || !payload.label || !payload.subject_template || !payload.body_template) {
        if (feedback instanceof HTMLElement) {
            feedback.textContent = "Nom, code, sujet et message sont obligatoires.";
        }
        return;
    }
    try {
        await requestJson(
            state.notificationTemplateEditor?.code
                ? `/notifications/templates/${encodeURIComponent(String(state.notificationTemplateEditor.code || payload.code))}`
                : "/notifications/templates",
            {
                method: state.notificationTemplateEditor?.code ? "PUT" : "POST",
                body: JSON.stringify(payload),
            },
        );
        await openNotificationTemplatesModal();
    } catch (error) {
        if (feedback instanceof HTMLElement) {
            feedback.textContent = normalizeErrorMessage(error.message);
        }
    }
}

async function deleteNotificationTemplate(code) {
    const normalized = String(code || "").trim().toLowerCase();
    if (!normalized) {
        return;
    }
    const confirmed = await showItopsConfirm({
        title: "Supprimer le template",
        message: "Supprimer ce template de notification ?",
        details: ["Les taches deja creees restent conservees.", "Les prochains envois utiliseront un autre template ou le message de la tache."],
        confirmLabel: "Supprimer",
        cancelLabel: "Annuler",
        danger: true,
    });
    if (!confirmed) {
        return;
    }
    await requestJson(`/notifications/templates/${encodeURIComponent(normalized)}`, { method: "DELETE" });
    await openNotificationTemplatesModal();
}

function insertNotificationTemplateVariable(variableName) {
    const variable = String(variableName || "").trim();
    if (!variable) {
        return;
    }
    const token = `{{${variable}}}`;
    const active = document.activeElement;
    const target = active instanceof HTMLInputElement || active instanceof HTMLTextAreaElement
        ? active
        : document.querySelector('[name="body_template"]');
    if (!(target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement)) {
        return;
    }
    const start = Number(target.selectionStart ?? target.value.length);
    const end = Number(target.selectionEnd ?? target.value.length);
    target.value = `${target.value.slice(0, start)}${token}${target.value.slice(end)}`;
    target.focus();
    target.selectionStart = target.selectionEnd = start + token.length;
}

async function runNotificationSettingsTest(form) {
    const feedback = document.getElementById("modal-notification-feedback");
    const testButton = form.querySelector('[data-action="notification:test"]');
    if (testButton instanceof HTMLButtonElement) {
        testButton.disabled = true;
    }
    try {
        if (feedback instanceof HTMLElement) {
            feedback.textContent = "Enregistrement de la configuration SMTP...";
        }
        const saved = await submitNotificationSettings(form, { closeOnSuccess: false });
        if (!saved) {
            return;
        }
        if (feedback instanceof HTMLElement) {
            feedback.textContent = "Envoi du test SMTP...";
        }
        const result = await requestJson("/settings/notifications/test", { method: "POST" });
        if (feedback instanceof HTMLElement) {
            feedback.textContent = String(result?.message || "Test SMTP envoye.");
        }
    } catch (error) {
        if (feedback instanceof HTMLElement) {
            feedback.textContent = normalizeErrorMessage(error.message);
        }
    } finally {
        if (testButton instanceof HTMLButtonElement) {
            testButton.disabled = false;
        }
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

async function downloadDatabaseBackup() {
    const sharedDownload = window.NMPSharedDownload?.downloadBinary;
    if (typeof sharedDownload !== "function") {
        throw new Error("Module de telechargement indisponible.");
    }
    await sharedDownload({
        url: "/admin/database/backup",
        method: "GET",
        headers: {
            ...headers(),
        },
        defaultFilename: "itops-db.sql",
        normalizeErrorMessage,
    });
}

async function openActiveDirectorySettingsModal() {
    const [settings, certificate] = await Promise.all([requestJson("/settings"), requestJson("/settings/active-directory/certificate")]);
    openModal("Synchronisation Active Directory", buildActiveDirectorySettingsMarkup(settings, certificate), {
        width: "min(860px, calc(100vw - 40px))",
    });
}

function buildActiveDirectorySettingsPatch(form) {
    const formData = new window.FormData(form);
    const port = Number(formData.get("active_directory_port") || 636);
    const interval = Number(formData.get("active_directory_sync_interval_seconds") || 3600);
    return {
        active_directory_enabled: form.querySelector('[name="active_directory_enabled"]')?.checked ?? false,
        active_directory_host: String(formData.get("active_directory_host") || "").trim(),
        active_directory_port: Number.isFinite(port) ? Math.max(1, Math.min(65535, Math.trunc(port))) : 636,
        active_directory_use_ssl: form.querySelector('[name="active_directory_use_ssl"]')?.checked ?? true,
        active_directory_validate_certificates: form.querySelector('[name="active_directory_validate_certificates"]')?.checked ?? true,
        active_directory_bind_username: activeDirectoryBuildBindUsername(form),
        active_directory_bind_password: String(formData.get("active_directory_bind_password") || ""),
        active_directory_base_dn: String(formData.get("active_directory_base_dn") || "").trim(),
        active_directory_user_filter: String(formData.get("active_directory_user_filter") || "").trim(),
        active_directory_sync_interval_seconds: Number.isFinite(interval) ? Math.max(60, Math.trunc(interval)) : 3600,
        active_directory_sync_email_accounts: form.querySelector('[name="active_directory_sync_email_accounts"]')?.checked ?? false,
    };
}

async function submitActiveDirectorySettings(form, { test = false, syncNow = false, syncMode = "normal" } = {}) {
    const feedback = document.getElementById("modal-active-directory-feedback");
    try {
        await applySettingsPatch(buildActiveDirectorySettingsPatch(form), "modal-active-directory-feedback");
        if (test) {
            if (feedback instanceof HTMLElement) feedback.textContent = "Test de connexion LDAP...";
            const result = await requestJson("/settings/active-directory/test", { method: "POST" });
            if (feedback instanceof HTMLElement) feedback.textContent = String(result?.message || "Connexion valide.");
        } else if (syncNow) {
            await runActiveDirectoryManualSync({
                feedback,
                mode: syncMode,
            });
        } else {
            window.setTimeout(() => closeModal(), 400);
        }
    } catch (error) {
        if (feedback instanceof HTMLElement) feedback.textContent = normalizeErrorMessage(error.message);
    }
}

function normalizeActiveDirectoryManualSyncMode(value) {
    const normalized = String(value || "normal").trim().toLowerCase().replace(/-/g, "_");
    return ["normal", "force_rebuild", "reset_ad"].includes(normalized) ? normalized : "normal";
}

async function runActiveDirectoryManualSync({ feedback = null, trigger = null, mode = "normal" } = {}) {
    const syncMode = normalizeActiveDirectoryManualSyncMode(mode);
    if (syncMode === "reset_ad") {
        const confirmed = await showItopsConfirm({
            title: "Reinitialiser les donnees AD ?",
            message: "Cette action supprime le cache Active Directory, les liens deduits de l'AD et les comptes Email marques AD avant de relancer une synchronisation. Les donnees manuelles sont conservees.",
            confirmLabel: "Reinitialiser et synchroniser",
            cancelLabel: "Annuler",
            danger: true,
        });
        if (!confirmed) {
            return null;
        }
    }
    const syncButton = trigger instanceof HTMLButtonElement ? trigger : null;
    const syncDateNode = syncButton?.querySelector("strong");
    const previousDateText = syncDateNode instanceof HTMLElement ? syncDateNode.textContent : "";
    if (syncButton) {
        syncButton.disabled = true;
    }
    if (syncDateNode instanceof HTMLElement) {
        syncDateNode.textContent = "en cours...";
    }
    if (feedback instanceof HTMLElement) {
        feedback.textContent = "Synchronisation Active Directory en cours...";
    }
    try {
        const result = await requestJson("/settings/active-directory/sync-now", {
            method: "POST",
            body: JSON.stringify({ mode: syncMode }),
        });
        state.moduleAccessLoaded = false;
        invalidateAdminData(["modules", "services"]);
        await loadPortalModules({ forceRefresh: true });
        const message = String(result?.message || "Synchronisation terminee.");
        if (feedback instanceof HTMLElement) {
            feedback.textContent = message;
        } else {
            showAppSaveFeedback({ message });
        }
        return result;
    } catch (error) {
        const message = normalizeErrorMessage(error.message);
        if (feedback instanceof HTMLElement) {
            feedback.textContent = message;
        } else {
            showAppSaveFeedback({ kind: "error", message, durationMs: 4200 });
        }
        return null;
    } finally {
        if (syncButton) {
            syncButton.disabled = false;
            if (syncDateNode instanceof HTMLElement && String(syncDateNode.textContent || "") === "en cours...") {
                syncDateNode.textContent = previousDateText || "-";
            }
            updatePortalSyncBadge();
        }
    }
}

async function updateNotificationTaskStatus(taskId, statusValue) {
    const normalizedId = String(taskId || "").trim();
    if (!normalizedId) {
        return;
    }
    const feedback = document.getElementById("modal-notification-tasks-feedback");
    if (feedback instanceof HTMLElement) {
        feedback.textContent = "Mise a jour de la tache...";
    }
    await requestJson(`/notifications/tasks/${encodeURIComponent(normalizedId)}/status`, {
        method: "PUT",
        body: JSON.stringify({ status: statusValue }),
    });
    await openNotificationTasksModal();
}

function activeDirectoryProfileTargetLabel(targetKind) {
    return String(targetKind || "") === "organizational_units" ? "OU / services" : "Agents";
}

function activeDirectoryProfileDefaultFilter(targetKind) {
    return String(targetKind || "") === "organizational_units"
        ? "(objectClass=organizationalUnit)"
        : "(&(objectCategory=person)(objectClass=user))";
}

function normalizeActiveDirectoryProfileTargetKind(value) {
    return String(value || "").trim().toLowerCase() === "organizational_units" ? "organizational_units" : "users";
}

function activeDirectoryProfileOptionList(value) {
    return listFromMaybeArray(value)
        .map((item) => String(item || "").trim())
        .filter(Boolean);
}

function activeDirectoryProfileOptionsForUi(source = {}) {
    const options = source && typeof source === "object" ? source : {};
    return {
        ou_root_dn: String(options.ou_root_dn || options.root_dn || "").trim(),
        ou_max_depth: options.ou_max_depth === 0 || options.ou_max_depth ? String(options.ou_max_depth) : "",
        excluded_ou_names: activeDirectoryProfileOptionList(options.excluded_ou_names || options.ou_excluded_names),
        excluded_ou_dns: activeDirectoryProfileOptionList(options.excluded_ou_dns || options.ou_excluded_dns),
    };
}

function activeDirectoryOuScopeMarkup(prefix, targetKind, sourceOptions = {}) {
    if (normalizeActiveDirectoryProfileTargetKind(targetKind) !== "organizational_units") {
        return "";
    }
    const options = activeDirectoryProfileOptionsForUi(sourceOptions);
    return `
        <div class="modal-settings-grid active-directory-ou-scope" data-ad-ou-scope>
            <label class="field full"><span>OU de depart</span><input name="${prefix}_ou_root_dn" value="${escapeHtml(options.ou_root_dn)}" placeholder="OU=Services,OU=MairieVL,DC=mairieVL,DC=local"></label>
            <label class="field"><span>Profondeur enfant</span><input name="${prefix}_ou_max_depth" type="number" min="0" max="50" value="${escapeHtml(options.ou_max_depth)}" placeholder="Illimitee"></label>
            <label class="field full"><span>OU a exclure par nom</span><textarea name="${prefix}_excluded_ou_names" rows="3" placeholder="Ordinateurs&#10;Utilisateurs&#10;Profils&#10;Prets">${escapeHtml(options.excluded_ou_names.join("\n"))}</textarea></label>
            <label class="field full"><span>OU a exclure par DN</span><textarea name="${prefix}_excluded_ou_dns" rows="3" placeholder="OU=Ordinateurs,OU=MairieVL,DC=mairieVL,DC=local">${escapeHtml(options.excluded_ou_dns.join("\n"))}</textarea></label>
        </div>`;
}

function activeDirectoryReadOuScopeOptions(form, prefix, targetKind, baseOptions = {}) {
    const options = baseOptions && typeof baseOptions === "object" ? { ...baseOptions } : {};
    if (normalizeActiveDirectoryProfileTargetKind(targetKind) !== "organizational_units") {
        delete options.ou_root_dn;
        delete options.ou_max_depth;
        delete options.excluded_ou_names;
        delete options.excluded_ou_dns;
        return options;
    }
    const formData = new window.FormData(form);
    const rootDn = String(formData.get(`${prefix}_ou_root_dn`) || "").trim();
    const rawDepth = String(formData.get(`${prefix}_ou_max_depth`) || "").trim();
    const names = String(formData.get(`${prefix}_excluded_ou_names`) || "")
        .split(/[\n,;]+/)
        .map((item) => item.trim())
        .filter(Boolean);
    const dns = String(formData.get(`${prefix}_excluded_ou_dns`) || "")
        .split(/[\n;]+/)
        .map((item) => item.trim())
        .filter(Boolean);
    if (rootDn) options.ou_root_dn = rootDn;
    else delete options.ou_root_dn;
    if (rawDepth !== "") options.ou_max_depth = Math.max(0, Math.min(50, Math.trunc(Number(rawDepth) || 0)));
    else delete options.ou_max_depth;
    if (names.length) options.excluded_ou_names = names;
    else delete options.excluded_ou_names;
    if (dns.length) options.excluded_ou_dns = dns;
    else delete options.excluded_ou_dns;
    return options;
}

function buildActiveDirectoryProfileOptions(profiles, selectedId = "") {
    const rows = listFromMaybeArray(profiles);
    if (!rows.length) {
        return `<option value="">Nouveau profil</option>`;
    }
    return [
        `<option value="">Nouveau profil</option>`,
        ...rows.map((profile) => `<option value="${escapeHtml(String(profile.id || ""))}" ${String(profile.id || "") === String(selectedId || "") ? "selected" : ""}>${escapeHtml(String(profile.label || profile.code || "Profil AD"))}</option>`),
    ].join("");
}

function buildActiveDirectoryProfileDualList(availableAttributes, selectedAttributes) {
    const selected = listFromMaybeArray(selectedAttributes).map((item) => String(item || "").trim()).filter(Boolean);
    const selectedSet = new Set(selected);
    const available = listFromMaybeArray(availableAttributes)
        .map((item) => String(item || "").trim())
        .filter((item) => item && !selectedSet.has(item));
    const optionMarkup = (values) => listFromMaybeArray(values)
        .map((value) => `<option value="${escapeHtml(String(value))}">${escapeHtml(String(value))}</option>`)
        .join("");
    return `
        <div class="active-directory-field-picker">
            <label class="field">
                <span>Champs AD disponibles</span>
                <select data-ad-profile-available-fields multiple size="10">${optionMarkup(available)}</select>
            </label>
            <div class="active-directory-field-picker-actions">
                <button class="toolbar-btn" type="button" data-action="active-directory-profile:add-field" title="Importer dans le service">↓</button>
                <button class="toolbar-btn" type="button" data-action="active-directory-profile:remove-field" title="Retirer de l'import">↑</button>
                <button class="toolbar-btn" type="button" data-action="active-directory-profile:move-up" title="Remonter le champ">▲</button>
                <button class="toolbar-btn" type="button" data-action="active-directory-profile:move-down" title="Descendre le champ">▼</button>
            </div>
            <label class="field">
                <span>Champs importés dans le service</span>
                <select name="selected_attributes" data-ad-profile-selected-fields multiple size="10">${optionMarkup(selected)}</select>
            </label>
        </div>`;
}

function serviceActiveDirectoryMappingRows(editor, selectedAttributes) {
    const fields = Array.isArray(editor?.fields) ? editor.fields : [];
    const mappings = Array.isArray(editor?.adImportDraft?.field_mappings) ? editor.adImportDraft.field_mappings : [];
    const samples = editor?.adImportDraft?.preview_samples && typeof editor.adImportDraft.preview_samples === "object"
        ? editor.adImportDraft.preview_samples
        : {};
    const hasSamples = Object.keys(samples).length > 0;
    const byAttribute = new Map(
        mappings
            .map((mapping) => [String(mapping?.attribute || "").trim(), mapping])
            .filter(([attribute]) => Boolean(attribute)),
    );
    return listFromMaybeArray(selectedAttributes)
        .map((attribute, index) => {
            const raw = String(attribute || "").trim();
            const current = byAttribute.get(raw) || {};
            const generated = activeDirectoryAttributeToServiceField(raw, index);
            const target = String(current.target || "new").trim();
            const existingFieldKey = String(current.field_key || "").trim();
            const label = String(current.label || generated.label || raw).trim();
            const kind = normalizeNoCodeKind(current.field_kind || generated.field_kind || "text");
            const sample = String(samples[raw] || (hasSamples ? "Valeur vide sur les exemples lus" : "Chargement des exemples AD...")).trim();
            const mappingValue = target === "ignore"
                ? "__ignore__"
                : target === "existing" && existingFieldKey
                    ? `field:${existingFieldKey}`
                    : "__new__";
            const targetClass = target === "ignore" ? "is-ignored" : "is-mapped";
            const existingOptions = fields.map((field) => {
                const fieldKey = String(field.field_key || "").trim();
                const fieldLabel = String(field.label || fieldKey).trim();
                if (!fieldKey) return "";
                return `<option value="field:${escapeHtml(fieldKey)}" ${mappingValue === `field:${fieldKey}` ? "selected" : ""}>${escapeHtml(fieldLabel)}</option>`;
            }).join("");
            return `
                <tr data-ad-mapping-row data-attribute="${escapeHtml(raw)}" class="${target === "ignore" ? "is-ignored" : ""}">
                    <td title="${escapeHtml(sample)}"><code>${escapeHtml(raw)}</code></td>
                    <td>
                        <select name="service_ad_mapping_target" class="${targetClass}">
                            <option value="new" ${target !== "existing" && target !== "ignore" ? "selected" : ""}>Créer un nouveau champ</option>
                            <option value="existing" ${target === "existing" ? "selected" : ""} ${fields.length ? "" : "disabled"}>Mapper sur un champ existant</option>
                            <option value="ignore" ${target === "ignore" ? "selected" : ""}>Ignorer</option>
                        </select>
                    </td>
                    <td>
                        <select name="service_ad_mapping_existing" ${target === "existing" ? "" : "disabled"}>
                            <option value="">Choisir...</option>
                            ${existingOptions}
                        </select>
                    </td>
                    <td><input name="service_ad_mapping_label" value="${escapeHtml(label)}" ${target === "existing" || target === "ignore" ? "disabled" : ""}></td>
                    <td>
                        <select name="service_ad_mapping_kind" ${target === "existing" || target === "ignore" ? "disabled" : ""}>
                            ${NO_CODE_FIELD_KINDS.map((fieldKind) => `<option value="${escapeHtml(fieldKind)}" ${kind === fieldKind ? "selected" : ""}>${escapeHtml(noCodeKindLabel(fieldKind))}</option>`).join("")}
                        </select>
                    </td>
                </tr>`;
        })
        .join("");
}

function serviceActiveDirectoryMappingRowsV2(editor, selectedAttributes) {
    const fields = Array.isArray(editor?.fields) ? editor.fields : [];
    const mappings = Array.isArray(editor?.adImportDraft?.field_mappings) ? editor.adImportDraft.field_mappings : [];
    const samples = editor?.adImportDraft?.preview_samples && typeof editor.adImportDraft.preview_samples === "object"
        ? editor.adImportDraft.preview_samples
        : {};
    const hasSamples = Object.keys(samples).length > 0;
    const byAttribute = new Map(
        mappings
            .map((mapping) => [String(mapping?.attribute || "").trim(), mapping])
            .filter(([attribute]) => Boolean(attribute)),
    );
    return listFromMaybeArray(selectedAttributes)
        .map((attribute, index) => {
            const raw = String(attribute || "").trim();
            const current = byAttribute.get(raw) || {};
            const generated = activeDirectoryAttributeToServiceField(raw, index);
            const matchedExisting = findExistingServiceFieldForActiveDirectoryAttribute(editor, raw, index);
            const currentTarget = String(current.target || "").trim();
            const target = currentTarget === "ignore"
                ? "ignore"
                : currentTarget === "existing" || matchedExisting
                    ? "existing"
                    : "new";
            const existingFieldKey = String(current.field_key || matchedExisting?.field_key || "").trim();
            const mappingValue = target === "ignore"
                ? "__ignore__"
                : target === "existing" && existingFieldKey
                    ? `field:${existingFieldKey}`
                    : "__new__";
            const ignored = mappingValue === "__ignore__";
            const newField = mappingValue === "__new__";
            const label = String(current.label || generated.label || raw).trim();
            const kind = normalizeNoCodeKind(current.field_kind || generated.field_kind || "text");
            const sample = String(samples[raw] || (hasSamples ? "Valeur vide sur les exemples lus" : "Chargement des exemples AD...")).trim();
            const existingOptions = fields.map((field) => {
                const fieldKey = String(field.field_key || "").trim();
                const fieldLabel = String(field.label || fieldKey).trim();
                if (!fieldKey) return "";
                return `<option value="field:${escapeHtml(fieldKey)}" ${mappingValue === `field:${fieldKey}` ? "selected" : ""}>${escapeHtml(fieldLabel)}</option>`;
            }).join("");
            return `
                <tr data-ad-mapping-row data-attribute="${escapeHtml(raw)}" class="${ignored ? "is-ignored" : ""}">
                    <td title="${escapeHtml(sample)}"><code>${escapeHtml(raw)}</code></td>
                    <td>
                        <select name="service_ad_mapping_target" class="${ignored ? "is-ignored" : "is-mapped"}">
                            <option value="__ignore__" ${ignored ? "selected" : ""}>Ignorer</option>
                            <option value="__new__" ${newField ? "selected" : ""}>Ajouter comme nouveau champ</option>
                            ${existingOptions}
                        </select>
                    </td>
                    <td><input name="service_ad_mapping_label" value="${escapeHtml(label)}" ${newField ? "" : "disabled"}></td>
                    <td>
                        <select name="service_ad_mapping_kind" ${newField ? "" : "disabled"}>
                            ${NO_CODE_FIELD_KINDS.map((fieldKind) => `<option value="${escapeHtml(fieldKind)}" ${kind === fieldKind ? "selected" : ""}>${escapeHtml(noCodeKindLabel(fieldKind))}</option>`).join("")}
                        </select>
                    </td>
                </tr>`;
        })
        .join("");
}

function buildServiceActiveDirectoryMappingMarkup(editor, availableAttributes, selectedAttributes) {
    const selectedSet = new Set(listFromMaybeArray(selectedAttributes).map((item) => String(item || "").trim()).filter(Boolean));
    const samples = editor?.adImportDraft?.preview_samples && typeof editor.adImportDraft.preview_samples === "object"
        ? editor.adImportDraft.preview_samples
        : {};
    const hasSamples = Object.keys(samples).length > 0;
    const available = listFromMaybeArray(availableAttributes)
        .map((item) => String(item || "").trim())
        .filter((item) => item && !selectedSet.has(item));
    const availableOptions = available
        .map((attribute) => `<option value="${escapeHtml(attribute)}">${escapeHtml(attribute)}</option>`)
        .join("");
    return `
        <div class="service-ad-source-picker">
            <label class="field">
                <span>Ajouter un attribut AD</span>
                <select data-ad-profile-available-fields multiple size="7">${availableOptions}</select>
            </label>
            <div class="inventory-row-actions">
                <button class="toolbar-btn" type="button" data-action="active-directory-profile:add-field">Ajouter à l'import</button>
                <button class="toolbar-btn" type="button" data-action="active-directory-profile:remove-field">Retirer la ligne sélectionnée</button>
            </div>
        </div>
        <div class="table-wrap shared-treeview-table-wrap service-ad-mapping-table">
            <table class="device-table shared-treeview-table">
                <thead>
                    <tr>
                        <th>Attribut AD <span class="muted">(survol = exemples)</span></th>
                        <th>Mapping</th>
                        <th>Libelle nouveau champ</th>
                        <th>Type</th>
                    </tr>
                </thead>
                <tbody data-ad-profile-selected-fields>
                    ${serviceActiveDirectoryMappingRowsV2(editor, selectedAttributes) || '<tr class="shared-treeview-empty"><td colspan="4">Aucun attribut selectionne.</td></tr>'}
                </tbody>
            </table>
        </div>
        <p class="muted" data-service-ad-preview-status>${hasSamples ? "Exemples AD charges: survole un attribut pour voir les valeurs." : "Chargement automatique des exemples AD..."}</p>`;
}

function buildActiveDirectoryProfilesMarkup(payload = {}, selectedId = "") {
    const profiles = listFromMaybeArray(payload.profiles);
    const availableByTarget = payload.available_attributes || {};
    const selectedProfile = profiles.find((profile) => String(profile.id || "") === String(selectedId || ""))
        || profiles[0]
        || {
            id: "",
            code: "",
            label: "Annuaire agents",
            target_kind: "users",
            search_base: "",
            search_filter: activeDirectoryProfileDefaultFilter("users"),
            selected_attributes: ["sAMAccountName", "displayName", "mail", "department", "distinguishedName", "memberOf"],
            is_active: true,
        };
    const targetKind = normalizeActiveDirectoryProfileTargetKind(selectedProfile.target_kind);
    const availableAttributes = listFromMaybeArray(availableByTarget[targetKind]);
    return `
    <form id="modal-active-directory-profile-form" class="modal-form" data-profile-id="${escapeHtml(String(selectedProfile.id || ""))}">
        <p class="muted">Profils globaux de lecture Active Directory. Ils seront reutilisables par les modules Agents, OU et services dynamiques. Cette etape configure la source et la preview, sans importer en base metier.</p>
        <div class="modal-settings-grid">
            <label class="field">
                <span>Profil</span>
                <select name="profile_selector" data-ad-profile-selector>${buildActiveDirectoryProfileOptions(profiles, selectedProfile.id)}</select>
            </label>
            <label class="field">
                <span>Type d'import</span>
                <select name="target_kind" data-ad-profile-target-kind>
                    <option value="users" ${targetKind === "users" ? "selected" : ""}>Agents AD</option>
                    <option value="organizational_units" ${targetKind === "organizational_units" ? "selected" : ""}>OU / services AD</option>
                </select>
            </label>
            <label class="field"><span>Libelle</span><input name="label" required value="${escapeHtml(String(selectedProfile.label || ""))}" placeholder="Annuaire agents"></label>
            <label class="field"><span>Code technique</span><input name="code" value="${escapeHtml(String(selectedProfile.code || ""))}" placeholder="auto si vide"></label>
            <label class="field full"><span>Base DN specifique</span><input name="search_base" value="${escapeHtml(String(selectedProfile.search_base || ""))}" placeholder="Vide = Base DN de la connexion AD"></label>
            <label class="field full"><span>Filtre LDAP</span><input name="search_filter" value="${escapeHtml(String(selectedProfile.search_filter || activeDirectoryProfileDefaultFilter(targetKind)))}"></label>
        </div>
        ${activeDirectoryOuScopeMarkup("profile", targetKind, selectedProfile.options || {})}
        <label class="check-field"><input name="is_active" type="checkbox" ${selectedProfile.is_active !== false ? "checked" : ""}><span>Profil actif</span></label>
        ${buildActiveDirectoryProfileDualList(availableAttributes, selectedProfile.selected_attributes)}
        <div class="active-directory-profile-preview" data-ad-profile-preview></div>
        <p id="modal-active-directory-profile-feedback" class="muted inventory-feedback"></p>
        ${createModalActionsMarkup({ buttons: [{ preset: "cancel" }, { label: "Nouveau", action: "active-directory-profile:new", type: "button" }, { label: "Supprimer", action: "active-directory-profile:delete", type: "button", className: "toolbar-btn danger" }, { label: "Prévisualiser", action: "active-directory-profile:preview", type: "button" }, { preset: "save" }] })}
    </form>`;
}

async function openActiveDirectoryProfilesModal(selectedId = "") {
    const payload = await requestJson("/sync/active-directory/profiles");
    openModal("Profils d'import Active Directory", buildActiveDirectoryProfilesMarkup(payload, selectedId), {
        width: "min(980px, calc(100vw - 40px))",
    });
}

function selectedOptionsValues(select) {
    if (!(select instanceof HTMLSelectElement)) {
        return [];
    }
    return Array.from(select.selectedOptions).map((option) => String(option.value || "").trim()).filter(Boolean);
}

function activeDirectoryProfileSelectedAttributes(form) {
    const tableBody = form.querySelector("tbody[data-ad-profile-selected-fields]");
    if (tableBody instanceof HTMLElement) {
        return Array.from(tableBody.querySelectorAll("[data-ad-mapping-row]"))
            .map((row) => String(row.getAttribute("data-attribute") || "").trim())
            .filter(Boolean);
    }
    const select = form.querySelector("[data-ad-profile-selected-fields]");
    if (!(select instanceof HTMLSelectElement)) {
        return [];
    }
    return Array.from(select.options).map((option) => String(option.value || "").trim()).filter(Boolean);
}

function readServiceActiveDirectoryFieldMappings(form) {
    return Array.from(form.querySelectorAll("[data-ad-mapping-row]"))
        .map((row) => {
            const attribute = String(row.getAttribute("data-attribute") || "").trim();
            const mappingValue = String(row.querySelector('select[name="service_ad_mapping_target"]')?.value || "__new__").trim();
            const isExisting = mappingValue.startsWith("field:");
            const target = mappingValue === "__ignore__" ? "ignore" : isExisting ? "existing" : "new";
            return {
                attribute,
                target,
                field_key: isExisting ? mappingValue.slice("field:".length).trim() : "",
                label: String(row.querySelector('input[name="service_ad_mapping_label"]')?.value || "").trim(),
                field_kind: normalizeNoCodeKind(row.querySelector('select[name="service_ad_mapping_kind"]')?.value || "text"),
            };
        })
        .filter((mapping) => mapping.attribute);
}

function moveActiveDirectoryProfileField(form, direction) {
    const source = form.querySelector(direction === "add" ? "[data-ad-profile-available-fields]" : "[data-ad-profile-selected-fields]");
    const target = form.querySelector(direction === "add" ? "[data-ad-profile-selected-fields]" : "[data-ad-profile-available-fields]");
    const editor = state.noCodeServiceEditor;
    if (form.id === "modal-service-form" && editor?.adImportDraft) {
        const current = listFromMaybeArray(editor.adImportDraft.selected_attributes).map((item) => String(item || "").trim()).filter(Boolean);
        if (direction === "add" && source instanceof HTMLSelectElement) {
            selectedOptionsValues(source).forEach((value) => {
                if (!current.includes(value)) current.push(value);
            });
            editor.adImportDraft.selected_attributes = current;
            editor.adImportDraft.field_mappings = readServiceActiveDirectoryFieldMappings(form);
            renderNoCodeServiceEditor();
            window.setTimeout(() => loadServiceActiveDirectoryExamples({ silent: true }), 0);
            return;
        }
        const selectedRow = form.querySelector("[data-ad-mapping-row].is-selected") || form.querySelector("[data-ad-mapping-row]");
        const attribute = String(selectedRow?.getAttribute?.("data-attribute") || "").trim();
        if (direction === "remove" && attribute) {
            editor.adImportDraft.selected_attributes = current.filter((item) => item !== attribute);
            editor.adImportDraft.field_mappings = readServiceActiveDirectoryFieldMappings(form).filter((mapping) => mapping.attribute !== attribute);
            renderNoCodeServiceEditor();
            window.setTimeout(() => loadServiceActiveDirectoryExamples({ silent: true }), 0);
            return;
        }
    }
    if (!(source instanceof HTMLSelectElement) || !(target instanceof HTMLSelectElement)) {
        return;
    }
    const values = selectedOptionsValues(source);
    values.forEach((value) => {
        const existing = Array.from(target.options).some((option) => option.value === value);
        if (!existing) {
            target.appendChild(new Option(value, value));
        }
        Array.from(source.options).forEach((option) => {
            if (option.value === value) option.remove();
        });
    });
}

function reorderActiveDirectorySelectedField(form, offset) {
    const select = form.querySelector("[data-ad-profile-selected-fields]");
    if (!(select instanceof HTMLSelectElement)) {
        return;
    }
    const options = Array.from(select.options);
    if (offset < 0) {
        options.forEach((option, index) => {
            if (option.selected && index > 0) {
                select.insertBefore(option, options[index - 1]);
            }
        });
    } else {
        options.reverse().forEach((option, reverseIndex) => {
            const index = options.length - 1 - reverseIndex;
            if (option.selected && index < select.options.length - 1) {
                select.insertBefore(select.options[index + 1], option);
            }
        });
    }
}

function buildActiveDirectoryProfilePayload(form) {
    const formData = new window.FormData(form);
    const targetKind = normalizeActiveDirectoryProfileTargetKind(formData.get("target_kind"));
    return {
        id: String(form.dataset.profileId || "").trim(),
        code: String(formData.get("code") || "").trim(),
        label: String(formData.get("label") || "").trim(),
        target_kind: targetKind,
        search_base: String(formData.get("search_base") || "").trim(),
        search_filter: String(formData.get("search_filter") || activeDirectoryProfileDefaultFilter(targetKind)).trim(),
        selected_attributes: activeDirectoryProfileSelectedAttributes(form),
        options: activeDirectoryReadOuScopeOptions(form, "profile", targetKind, {}),
        is_active: form.querySelector('[name="is_active"]')?.checked ?? true,
    };
}

async function submitActiveDirectoryProfileForm(form, { preview = false } = {}) {
    const feedback = document.getElementById("modal-active-directory-profile-feedback");
    try {
        if (feedback instanceof HTMLElement) feedback.textContent = "Enregistrement du profil...";
        const saved = await requestJson("/sync/active-directory/profiles", {
            method: "POST",
            body: JSON.stringify(buildActiveDirectoryProfilePayload(form)),
        });
        form.dataset.profileId = String(saved.id || "");
        if (preview) {
            if (feedback instanceof HTMLElement) feedback.textContent = "Lecture Active Directory...";
            const result = await requestJson(`/sync/active-directory/profiles/${encodeURIComponent(String(saved.id || ""))}/preview`, { method: "POST" });
            renderActiveDirectoryProfilePreview(result);
            if (feedback instanceof HTMLElement) feedback.textContent = `${Number(result.total_preview_rows || 0)} ligne(s) lue(s) en preview.`;
        } else {
            await openActiveDirectoryProfilesModal(String(saved.id || ""));
        }
    } catch (error) {
        if (feedback instanceof HTMLElement) feedback.textContent = normalizeErrorMessage(error.message);
    }
}

function renderActiveDirectoryProfilePreview(result) {
    const container = document.querySelector("[data-ad-profile-preview]");
    if (!(container instanceof HTMLElement)) {
        return;
    }
    const attributes = listFromMaybeArray(result?.attributes).map((item) => String(item || ""));
    const rows = listFromMaybeArray(result?.rows);
    if (!rows.length) {
        container.innerHTML = `<p class="muted">Aucune ligne retournee par la preview.</p>`;
        return;
    }
    const headers = attributes.map((attribute) => `<th>${escapeHtml(attribute)}</th>`).join("");
    const body = rows.map((row) => `
        <tr>${attributes.map((attribute) => `<td>${escapeHtml(Array.isArray(row?.[attribute]) ? row[attribute].join(", ") : String(row?.[attribute] ?? ""))}</td>`).join("")}</tr>
    `).join("");
    container.innerHTML = `
        <div class="table-wrap shared-treeview-table-wrap">
            <table class="device-table shared-treeview-table">
                <thead><tr>${headers}</tr></thead>
                <tbody>${body}</tbody>
            </table>
        </div>`;
}

function activeDirectoryAttributeToServiceField(attribute, index = 0) {
    const raw = String(attribute || "").trim();
    const labels = {
        objectGUID: "Identifiant AD",
        sAMAccountName: "Compte",
        userPrincipalName: "UPN",
        displayName: "Nom complet",
        givenName: "Prenom",
        sn: "Nom",
        mail: "Email",
        telephoneNumber: "Telephone",
        mobile: "Mobile",
        title: "Fonction",
        department: "Service",
        company: "Organisation",
        manager: "Manager",
        memberOf: "Groupes AD",
        distinguishedName: "DN",
        whenChanged: "Derniere modification AD",
        userAccountControl: "Statut AD",
        ou: "OU",
        name: "Nom",
        description: "Description",
        managedBy: "Responsable",
    };
    const kind = ["mail"].includes(raw) ? "email" : "text";
    return {
        field_key: slugifyNoCodeIdentifier(raw, `ad_field_${index + 1}`),
        label: labels[raw] || raw || `Champ AD ${index + 1}`,
        field_kind: kind,
        required: ["sAMAccountName", "displayName", "ou", "name"].includes(raw),
        options: "",
        default_value: "",
        sort_order: (index + 1) * 10,
        list_source_kind: "local",
        shared_list_code: "",
        track_history: false,
        inline_editable: false,
        batch_editable: false,
        quick_filter: ["department", "ou", "name"].includes(raw),
    };
}

function findExistingServiceFieldForActiveDirectoryAttribute(editor, attribute, index = 0) {
    const fields = Array.isArray(editor?.fields) ? editor.fields : [];
    if (!fields.length) {
        return null;
    }
    const generated = activeDirectoryAttributeToServiceField(attribute, index);
    const candidates = new Set([
        String(generated.field_key || "").trim(),
        slugifyNoCodeIdentifier(generated.label || "", ""),
        slugifyNoCodeIdentifier(attribute || "", ""),
    ].filter(Boolean));
    return fields.find((field) => {
        const fieldKey = String(field?.field_key || "").trim();
        const fieldLabelKey = slugifyNoCodeIdentifier(field?.label || fieldKey, "");
        return candidates.has(fieldKey) || candidates.has(fieldLabelKey);
    }) || null;
}

function buildServiceActiveDirectorySourceMarkup(editor) {
    const payload = editor?.adImportPayload || {};
    const profiles = listFromMaybeArray(payload.profiles);
    const availableByTarget = payload.available_attributes || {};
    const draft = editor?.adImportDraft || {};
    const targetKind = normalizeActiveDirectoryProfileTargetKind(draft.target_kind || "users");
    const selectedProfile = profiles.find((profile) => String(profile.id || "") === String(draft.profile_id || ""));
    const selectedAttributes = listFromMaybeArray(draft.selected_attributes).length
        ? listFromMaybeArray(draft.selected_attributes)
        : listFromMaybeArray(selectedProfile?.selected_attributes).length
            ? listFromMaybeArray(selectedProfile.selected_attributes)
            : listFromMaybeArray(availableByTarget[targetKind]).slice(0, 6);
    const scopeOptions = {
        ...(selectedProfile?.options || {}),
        ...(draft.options || {}),
    };
    const profileOptions = [
        `<option value="">Nouveau profil depuis cette source</option>`,
        ...profiles
            .filter((profile) => normalizeActiveDirectoryProfileTargetKind(profile.target_kind) === targetKind)
            .map((profile) => `<option value="${escapeHtml(String(profile.id || ""))}" ${String(profile.id || "") === String(draft.profile_id || "") ? "selected" : ""}>${escapeHtml(String(profile.label || profile.code || "Profil AD"))}</option>`),
    ].join("");
    return `
        <section class="type-schema-field-editor">
            <div class="type-schema-fields-head">
                <div>
                    <h3>Source Active Directory</h3>
                    <p class="muted">Selectionne les champs AD qui structureront ce service. Les donnees seront branchees dans une phase suivante.</p>
                </div>
                <div class="inventory-row-actions">
                    ${createActionButtonMarkup({ className: "toolbar-btn", type: "button", action: "service:field:ad-source:clear", label: "Ignorer", iconHtml: "&#10005;" })}
                    ${createActionButtonMarkup({ className: "primary-btn", type: "button", action: "service:field:ad-source:apply", label: "Appliquer au service", iconHtml: "&#10003;" })}
                </div>
            </div>
            <div class="modal-settings-grid">
                <label class="field">
                    <span>Type de donnees AD</span>
                    <select name="service_ad_import_target_kind">
                        <option value="users" ${targetKind === "users" ? "selected" : ""}>Agents AD</option>
                        <option value="organizational_units" ${targetKind === "organizational_units" ? "selected" : ""}>OU / services AD</option>
                    </select>
                </label>
                <label class="field">
                    <span>Profil existant</span>
                    <select name="service_ad_import_profile">${profileOptions}</select>
                </label>
                <label class="field"><span>Libelle du profil</span><input name="service_ad_import_label" value="${escapeHtml(String(draft.label || selectedProfile?.label || (targetKind === "users" ? "Annuaire agents" : "Services mairie")))}"></label>
                <label class="field"><span>Code technique</span><input name="service_ad_import_code" value="${escapeHtml(String(draft.code || selectedProfile?.code || ""))}" placeholder="auto si vide"></label>
            </div>
            <details class="active-directory-advanced">
                <summary>Parametres avances LDAP</summary>
                <div class="modal-settings-grid">
                    <label class="field full"><span>Base DN specifique</span><input name="service_ad_import_search_base" value="${escapeHtml(String(draft.search_base ?? selectedProfile?.search_base ?? ""))}" placeholder="Vide = Base DN de la connexion AD"></label>
                    <label class="field full"><span>Filtre LDAP</span><input name="service_ad_import_search_filter" value="${escapeHtml(String(draft.search_filter || selectedProfile?.search_filter || activeDirectoryProfileDefaultFilter(targetKind)))}"></label>
                </div>
                ${activeDirectoryOuScopeMarkup("service_ad_import", targetKind, scopeOptions)}
                <p class="muted">Dans la plupart des cas, le type de donnees AD suffit. Le filtre LDAP sert uniquement aux cas specifiques.</p>
            </details>
            ${buildServiceActiveDirectoryMappingMarkup(editor, listFromMaybeArray(availableByTarget[targetKind]), selectedAttributes)}
            <div class="active-directory-profile-preview" data-service-ad-preview></div>
            <p class="muted">Les attributs AD peuvent creer de nouveaux champs ou alimenter des champs personnalises existants.</p>
        </section>`;
}

function syncServiceActiveDirectoryDraftFromDom() {
    const editor = state.noCodeServiceEditor;
    const form = document.getElementById("modal-service-form");
    if (!editor || !(form instanceof HTMLFormElement)) {
        return;
    }
    const formData = new window.FormData(form);
    const profileId = String(formData.get("service_ad_import_profile") || "").trim();
    const selectedProfile = listFromMaybeArray(editor.adImportPayload?.profiles)
        .find((profile) => String(profile.id || "") === profileId);
    const targetKind = normalizeActiveDirectoryProfileTargetKind(formData.get("service_ad_import_target_kind") || selectedProfile?.target_kind || "users");
    editor.adImportDraft = {
        profile_id: profileId,
        id: profileId,
        target_kind: targetKind,
        label: String(formData.get("service_ad_import_label") || selectedProfile?.label || "").trim(),
        code: String(formData.get("service_ad_import_code") || selectedProfile?.code || "").trim(),
        search_base: String(formData.get("service_ad_import_search_base") || selectedProfile?.search_base || "").trim(),
        search_filter: String(formData.get("service_ad_import_search_filter") || selectedProfile?.search_filter || activeDirectoryProfileDefaultFilter(targetKind)).trim(),
        selected_attributes: activeDirectoryProfileSelectedAttributes(form),
        field_mappings: readServiceActiveDirectoryFieldMappings(form),
        options: activeDirectoryReadOuScopeOptions(form, "service_ad_import", targetKind, selectedProfile?.options || {}),
    };
}

function formatActiveDirectoryPreviewValue(value) {
    if (Array.isArray(value)) {
        return value.map((item) => formatActiveDirectoryPreviewValue(item)).filter(Boolean).slice(0, 3).join(", ");
    }
    if (value && typeof value === "object") {
        return JSON.stringify(value);
    }
    return String(value ?? "").trim();
}

function collectActiveDirectoryPreviewSamples(rows, attributes, limit = 5) {
    const sampleByAttribute = {};
    listFromMaybeArray(attributes).forEach((attribute) => {
        const values = [];
        listFromMaybeArray(rows).forEach((row) => {
            const value = activeDirectoryPreviewRowValue(row, attribute);
            if (value && !values.includes(value)) {
                values.push(value);
            }
        });
        sampleByAttribute[attribute] = values.slice(0, limit).join("\n");
    });
    return sampleByAttribute;
}

function activeDirectoryPreviewRowValue(row, attribute) {
    if (!row || typeof row !== "object") {
        return "";
    }
    const wanted = String(attribute || "").trim().toLowerCase();
    if (!wanted) {
        return "";
    }
    if (Object.prototype.hasOwnProperty.call(row, attribute)) {
        return formatActiveDirectoryPreviewValue(row[attribute]);
    }
    const matchedKey = Object.keys(row).find((key) => String(key || "").trim().toLowerCase() === wanted);
    return matchedKey ? formatActiveDirectoryPreviewValue(row[matchedKey]) : "";
}

function renderServiceActiveDirectoryPreview(result) {
    const editor = state.noCodeServiceEditor;
    const container = document.querySelector("[data-service-ad-preview]");
    const attributes = listFromMaybeArray(result?.attributes).map((item) => String(item || "").trim()).filter(Boolean);
    const rows = listFromMaybeArray(result?.rows);
    const sampleByAttribute = collectActiveDirectoryPreviewSamples(rows, attributes, 5);
    if (editor?.adImportDraft) {
        editor.adImportDraft.preview_samples = sampleByAttribute;
    }
    document.querySelectorAll("[data-ad-mapping-row]").forEach((row) => {
        const attribute = String(row.getAttribute("data-attribute") || "").trim();
        const attributeCell = row.querySelector("td");
        const sample = sampleByAttribute[attribute] || "Valeur vide sur les exemples lus";
        if (attributeCell instanceof HTMLElement) {
            attributeCell.title = sample;
        }
    });
    const statusNode = document.querySelector("[data-service-ad-preview-status]");
    if (statusNode instanceof HTMLElement) {
        statusNode.textContent = rows.length
            ? `Exemples AD charges (${rows.length} objet(s)): survole un attribut pour voir jusqu'a 5 valeurs.`
            : "Aucun exemple disponible dans le cache Active Directory.";
    }
    if (container instanceof HTMLElement) {
        container.innerHTML = "";
    }
}

function updateServiceActiveDirectoryTooltipMessage(message) {
    const text = String(message || "").trim() || "Aucun exemple disponible.";
    document.querySelectorAll("[data-ad-mapping-row]").forEach((row) => {
        const firstCell = row.querySelector("td");
        if (firstCell instanceof HTMLElement) {
            firstCell.title = text;
        }
    });
}

async function loadServiceActiveDirectoryExamples({ silent = false } = {}) {
    const editor = state.noCodeServiceEditor;
    if (!editor?.adImportDraft) {
        return;
    }
    const feedback = document.getElementById("modal-service-form-feedback");
    const statusNode = document.querySelector("[data-service-ad-preview-status]");
    try {
        syncServiceActiveDirectoryDraftFromDom();
        const draft = editor.adImportDraft || {};
        const attributes = listFromMaybeArray(draft.selected_attributes);
        if (!attributes.length) {
            if (statusNode instanceof HTMLElement) {
                statusNode.textContent = "Selectionne au moins un attribut AD pour charger des exemples.";
            }
            updateServiceActiveDirectoryTooltipMessage("Selectionne au moins un attribut AD pour charger des exemples.");
            return;
        }
        if (statusNode instanceof HTMLElement) {
            statusNode.textContent = "Chargement des exemples AD...";
        }
        updateServiceActiveDirectoryTooltipMessage("Chargement des exemples AD...");
        if (!silent && feedback) {
            feedback.textContent = "Lecture d'exemples Active Directory...";
        }
        const targetKind = normalizeActiveDirectoryProfileTargetKind(draft.target_kind);
        const result = await requestJson("/sync/active-directory/preview", {
            method: "POST",
            body: JSON.stringify({
                id: String(draft.profile_id || draft.id || ""),
                code: String(draft.code || ""),
                label: String(draft.label || "Source AD"),
                target_kind: targetKind,
                search_base: String(draft.search_base || ""),
                search_filter: String(draft.search_filter || activeDirectoryProfileDefaultFilter(targetKind)),
                selected_attributes: attributes,
                options: draft.options || {},
                is_active: true,
            }),
        });
        renderServiceActiveDirectoryPreview(result);
        if (!Number(result.total_preview_rows || 0)) {
            updateServiceActiveDirectoryTooltipMessage("Aucun objet AD retourne par le filtre actuel.");
        }
        if (!silent && feedback) {
            feedback.textContent = `${Number(result.total_preview_rows || 0)} exemple(s) lu(s) depuis Active Directory.`;
        }
    } catch (error) {
        const message = normalizeErrorMessage(error.message);
        if (statusNode instanceof HTMLElement) {
            statusNode.textContent = message;
        }
        updateServiceActiveDirectoryTooltipMessage(message);
        if (!silent && feedback) {
            feedback.textContent = message;
        }
    }
}

function updateActiveDirectoryAutoSyncToggle(form) {
    const checkbox = form.querySelector('[name="active_directory_enabled"]');
    const button = form.querySelector('[data-action="active-directory:toggle-auto-sync"]');
    const label = form.querySelector("[data-active-directory-status-label]");
    if (!(checkbox instanceof HTMLInputElement) || !(button instanceof HTMLButtonElement)) {
        return;
    }
    const enabled = checkbox.checked;
    button.classList.toggle("is-enabled", enabled);
    button.classList.toggle("is-disabled", !enabled);
    button.setAttribute("aria-pressed", enabled ? "true" : "false");
    if (label instanceof HTMLElement) {
        label.textContent = enabled ? "Synchronisation automatique active" : "Synchronisation automatique inactive";
    }
}

function updateActiveDirectoryDomainSuffix(form) {
    const suffix = form.querySelector("[data-active-directory-domain-suffix]");
    const usernameInput = form.querySelector('[name="active_directory_bind_username"]');
    const hostInput = form.querySelector('[name="active_directory_host"]');
    if (!(suffix instanceof HTMLElement) || !(usernameInput instanceof HTMLInputElement) || !(hostInput instanceof HTMLInputElement)) {
        return;
    }
    suffix.textContent = activeDirectoryDomainSuffix(hostInput.value, usernameInput.value);
}

function formatStorageFileSize(sizeBytes) {
    const value = Number(sizeBytes || 0);
    if (!Number.isFinite(value) || value <= 0) {
        return "-";
    }
    if (value < 1024) {
        return `${value} o`;
    }
    if (value < 1024 * 1024) {
        return `${(value / 1024).toFixed(value < 10 * 1024 ? 1 : 0)} Ko`;
    }
    if (value < 1024 * 1024 * 1024) {
        return `${(value / (1024 * 1024)).toFixed(value < 10 * 1024 * 1024 ? 1 : 0)} Mo`;
    }
    return `${(value / (1024 * 1024 * 1024)).toFixed(1)} Go`;
}

function formatStorageFileDate(value) {
    if (!value) {
        return "-";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return String(value);
    }
    return date.toLocaleString("fr-FR", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function storageFileDownloadName(file) {
    return String(file?.name || "fichier").trim() || "fichier";
}

async function downloadStorageFile(fileId, filename = "") {
    const normalizedId = String(fileId || "").trim();
    if (!normalizedId) {
        throw new Error("Fichier introuvable.");
    }
    const sharedDownload = window.NMPSharedDownload?.downloadBinary;
    if (typeof sharedDownload !== "function") {
        throw new Error("Module de telechargement indisponible.");
    }
    await sharedDownload({
        url: `/storage/files/${encodeURIComponent(normalizedId)}/download`,
        method: "GET",
        headers: {
            ...headers(),
        },
        defaultFilename: String(filename || "fichier").trim() || "fichier",
        normalizeErrorMessage,
    });
}

function renderStorageFileRow(file) {
    const fileId = String(file?.id || "").trim();
    const title = storageFileDownloadName(file);
    const detailParts = [
        file?.device_type_label || file?.device_type || "",
        file?.device_name || "",
        file?.device_ip || "",
    ].map((part) => String(part || "").trim()).filter(Boolean);
    const detail = detailParts.length ? detailParts.join(" - ") : String(file?.detail || "").trim();
    const syncStatus = String(file?.sync_status || "").trim();
    const syncLabel = syncStatus ? ` - Sync: ${syncStatus}` : "";
    return `
        <article class="inventory-card storage-file-card">
            <div class="storage-file-item-main">
                <div>
                    <strong>${escapeHtml(title)}</strong>
                    <p class="muted">${escapeHtml(detail || "Fichier stocke")}</p>
                    <p class="muted">${escapeHtml(formatStorageFileSize(file?.size_bytes))} - ${escapeHtml(formatStorageFileDate(file?.modified_at))}${escapeHtml(syncLabel)}</p>
                    ${file?.sync_error ? `<p class="error-text">${escapeHtml(file.sync_error)}</p>` : ""}
                </div>
                <div class="inventory-row-actions">
                    <button class="toolbar-btn" type="button" data-action="storage-files:download" data-file-id="${escapeHtml(fileId)}" data-file-name="${escapeHtml(title)}" ${fileId ? "" : "disabled"}>Telecharger</button>
                </div>
            </div>
        </article>
    `;
}

function renderStorageFilesList(files) {
    if (!Array.isArray(files) || files.length === 0) {
        return `<p class="muted">Aucun fichier stocke.</p>`;
    }
    return files.map((file) => renderStorageFileRow(file)).join("");
}

function storageMountStatusLabel(mount) {
    const status = String(mount?.status || "").trim().toLowerCase();
    if (status === "mounted" || status === "accessible" || Boolean(mount?.mounted)) {
        return "Accessible";
    }
    if (status === "automount_active" || Boolean(mount?.automount_active)) {
        return "Automount actif";
    }
    if (status === "inactive") {
        return "Inactif";
    }
    if (status === "missing_config") {
        return "Configuration incomplete";
    }
    if (status === "mounted_unavailable") {
        return "Montage partiel";
    }
    return "Non accessible";
}

function storageServiceLabel(serviceCode) {
    const code = String(serviceCode || "").trim();
    if (code === "monitoring.device_config_files") {
        return "Monitoring - fichiers de configuration";
    }
    if (code === "platform.storage") {
        return "Stockage ITops";
    }
    return code || "Service ITops";
}

function storageTargetById(targetId) {
    const normalizedId = String(targetId || "").trim();
    if (!normalizedId) {
        return null;
    }
    return (Array.isArray(state.storageTargets) ? state.storageTargets : [])
        .find((target) => String(target?.id || "").trim() === normalizedId) || null;
}

function storageMountRuntimeLabel(mount) {
    if (Boolean(mount?.mounted)) {
        return "Monte";
    }
    if (Boolean(mount?.automount_active)) {
        return "Montage a la demande";
    }
    return "Non monte";
}

function storageMountStatusClass(mount) {
    if (Boolean(mount?.accessible) || Boolean(mount?.automount_active)) {
        return "storage-status-ok";
    }
    if (String(mount?.last_error || "").trim()) {
        return "storage-status-error";
    }
    return "storage-status-warning";
}

function storageRemoteMountRows() {
    return (Array.isArray(state.storageMounts) ? state.storageMounts : []).map((mount) => {
        const targetId = String(mount?.id || "").trim();
        const target = storageTargetById(targetId);
        return {
            ...mount,
            label: String(mount?.label || target?.label || mount?.service_label || "Stockage distant").trim(),
            service_label: String(
                mount?.service_label
                || target?.service_label
                || storageServiceLabel(mount?.service_code || target?.service_code)
            ).trim(),
            service_code: String(mount?.service_code || target?.service_code || "").trim(),
            remote_path: String(mount?.remote_path || mount?.source_path || target?.remote_path || "").trim(),
            mount_path: String(mount?.mount_path || mount?.local_mount_path || target?.local_mount_path || "").trim(),
            target_path: String(mount?.target_path || mount?.mount_path || target?.local_mount_path || "").trim(),
            username: String(mount?.username || target?.username || "").trim(),
            managed_by: String(mount?.managed_by || target?.managed_by || "").trim(),
            status_label: storageMountStatusLabel(mount),
            runtime_label: storageMountRuntimeLabel(mount),
            message: String(mount?.last_error || mount?.message || "").trim(),
        };
    });
}

function storageLocalFileRows() {
    return (Array.isArray(state.storageFiles) ? state.storageFiles : []).map((file) => {
        const detailParts = [
            file?.device_type_label || file?.device_type || "",
            file?.device_name || "",
            file?.device_ip || "",
        ].map((part) => String(part || "").trim()).filter(Boolean);
        return {
            ...file,
            id: String(file?.id || "").trim(),
            name: storageFileDownloadName(file),
            service_label: String(file?.service_label || "Monitoring - fichiers de configuration").trim(),
            detail: detailParts.length ? detailParts.join(" - ") : String(file?.detail || "").trim(),
            size_label: formatStorageFileSize(file?.size_bytes),
            modified_label: formatStorageFileDate(file?.modified_at),
            sync_label: String(file?.sync_status || "").trim() || "-",
            sync_error: String(file?.sync_error || "").trim(),
        };
    });
}

function compareStorageRemoteRows(column, direction, left, right) {
    const dir = direction === "desc" ? -1 : 1;
    const byText = (a, b) => String(a || "").localeCompare(String(b || ""), undefined, { sensitivity: "base" }) * dir;
    if (column === "service") {
        return byText(left?.service_label, right?.service_label);
    }
    if (column === "status") {
        return byText(left?.status_label, right?.status_label);
    }
    if (column === "remote_path") {
        return byText(left?.remote_path, right?.remote_path);
    }
    if (column === "mount_path") {
        return byText(left?.mount_path, right?.mount_path);
    }
    return byText(left?.label, right?.label);
}

function compareStorageLocalRows(column, direction, left, right) {
    const dir = direction === "desc" ? -1 : 1;
    const byText = (a, b) => String(a || "").localeCompare(String(b || ""), undefined, { sensitivity: "base" }) * dir;
    if (column === "service") {
        return byText(left?.service_label, right?.service_label);
    }
    if (column === "size") {
        return (Number(left?.size_bytes || 0) - Number(right?.size_bytes || 0)) * dir;
    }
    if (column === "modified") {
        return byText(left?.modified_at, right?.modified_at);
    }
    if (column === "sync") {
        return byText(left?.sync_label, right?.sync_label);
    }
    return byText(left?.name, right?.name);
}

class StorageRemoteTreeView extends (window.NMPSharedUi?.treeView?.SharedTreeView || class {}) {
    constructor() {
        super({
            headElement: document.getElementById("storage-remote-head"),
            bodyElement: document.getElementById("storage-remote-body"),
            searchInput: document.getElementById("storage-remote-search"),
            sortState: state.storageRemoteSort,
            columnAttr: "storage-remote-col",
            renderHead: false,
            manageSortBinding: true,
            manageSearchBinding: true,
            searchThreshold: 5,
            emptyMessage: "Aucun montage distant declare.",
            getRows: () => storageRemoteMountRows(),
            searchText: (row) => [
                row?.label,
                row?.service_label,
                row?.remote_path,
                row?.mount_path,
                row?.status_label,
                row?.message,
            ].map((part) => String(part || "")).join(" "),
            compareRows: (column, direction, left, right) => compareStorageRemoteRows(column, direction, left, right),
            getRowKey: (row, index) => String(row?.id || `remote-${index}`),
            getRowClassName: (row) => storageMountStatusClass(row),
            renderRowCells: (row) => {
                const targetId = String(row?.id || "").trim();
                const canManage = targetId && String(row?.managed_by || "").trim() === "storage_targets";
                return `
                    <td>
                        <strong>${escapeHtml(String(row?.label || "Stockage distant"))}</strong>
                        ${row?.message ? `<p class="${String(row?.last_error || "").trim() ? "error-text" : "muted"}">${escapeHtml(row.message)}</p>` : ""}
                    </td>
                    <td>${escapeHtml(String(row?.service_label || storageServiceLabel(row?.service_code)))}</td>
                    <td>${escapeHtml(String(row?.remote_path || row?.source_path || ""))}</td>
                    <td>${escapeHtml(String(row?.target_path || row?.mount_path || ""))}</td>
                    <td>${escapeHtml(`${storageMountStatusLabel(row)} - ${storageMountRuntimeLabel(row)}`)}</td>
                    <td class="inventory-row-actions">
                        ${canManage ? [
                            createIconActionButtonMarkup({
                                icon: "list",
                                action: "storage-explorer:open",
                                title: "Explorer",
                                data: { root_id: `target:${targetId}` },
                            }),
                            createIconActionButtonMarkup({
                                icon: "check",
                                action: "storage-target:test",
                                title: "Tester le montage",
                                data: { target_id: targetId },
                            }),
                            createIconActionButtonMarkup({
                                icon: "settings",
                                action: "storage-target:edit",
                                title: "Modifier",
                                data: { target_id: targetId },
                            }),
                            createIconActionButtonMarkup({
                                icon: "delete",
                                danger: true,
                                action: "storage-target:delete",
                                title: "Supprimer",
                                data: { target_id: targetId },
                            }),
                        ].join("") : "-"}
                    </td>
                `;
            },
        });
    }
}

class StorageLocalTreeView extends (window.NMPSharedUi?.treeView?.SharedTreeView || class {}) {
    constructor() {
        super({
            headElement: document.getElementById("storage-local-head"),
            bodyElement: document.getElementById("storage-local-body"),
            searchInput: document.getElementById("storage-local-search"),
            sortState: state.storageLocalSort,
            columnAttr: "storage-local-col",
            renderHead: false,
            manageSortBinding: true,
            manageSearchBinding: true,
            searchThreshold: 5,
            emptyMessage: "Aucun fichier stocke localement.",
            getRows: () => storageLocalFileRows(),
            searchText: (row) => [
                row?.name,
                row?.service_label,
                row?.detail,
                row?.sync_label,
                row?.sync_error,
            ].map((part) => String(part || "")).join(" "),
            compareRows: (column, direction, left, right) => compareStorageLocalRows(column, direction, left, right),
            getRowKey: (row, index) => String(row?.id || `local-${index}`),
            renderRowCells: (row) => `
                <td>
                    <strong>${escapeHtml(String(row?.name || "Fichier"))}</strong>
                    ${row?.sync_error ? `<p class="error-text">${escapeHtml(row.sync_error)}</p>` : ""}
                </td>
                <td>${escapeHtml(String(row?.service_label || "Service ITops"))}</td>
                <td>${escapeHtml(String(row?.detail || "Fichier stocke"))}</td>
                <td>${escapeHtml(String(row?.size_label || "-"))}</td>
                <td>${escapeHtml(String(row?.modified_label || "-"))}</td>
                <td>${escapeHtml(String(row?.sync_label || "-"))}</td>
                <td class="inventory-row-actions">
                    ${createIconActionButtonMarkup({
                        icon: "download",
                        action: "storage-files:download",
                        title: "Telecharger",
                        data: {
                            file_id: String(row?.id || ""),
                            file_name: String(row?.name || "fichier"),
                        },
                        disabled: !String(row?.id || "").trim(),
                    })}
                </td>
            `,
        });
    }
}

function directoryRows() {
    const rows = Array.isArray(state.directoryContext?.rows) ? state.directoryContext.rows : [];
    const statusFilter = String(state.directoryContext?.statusFilter || "").trim().toLowerCase();
    if (!statusFilter) {
        return rows;
    }
    return rows.filter((row) => String(row?.status || "Actif").trim().toLowerCase() === statusFilter);
}

function directoryServiceCode(kind = state.directoryContext?.kind || "agents") {
    return String(kind || "").trim().toLowerCase() === "services" ? "services" : "utilisateurs";
}

function directoryRelationRecordFromRow(row, kind = state.directoryContext?.kind || "agents") {
    const serviceCode = directoryServiceCode(kind);
    const values = serviceCode === "utilisateurs"
        ? {
            display_name: String(row?.identity || row?.label || ""),
            login: String(row?.login || ""),
            mail: String(row?.mail || ""),
            service: String(row?.linked_services || row?.service || ""),
            distinguished_name: String(row?.distinguished_name || ""),
        }
        : {
            name: String(row?.label || row?.code || ""),
            code: String(row?.code || ""),
            description: String(row?.description || ""),
            manager: String(row?.manager || ""),
            distinguished_name: String(row?.distinguished_name || ""),
        };
    return {
        id: String(row?.id || ""),
        service_code: serviceCode,
        values,
        children: [],
        updated_at: String(row?.synced_at || row?.updated_at || ""),
    };
}

function directoryRelationContext() {
    const context = state.directoryContext || {};
    const kind = String(context.kind || "agents").trim().toLowerCase();
    const serviceCode = directoryServiceCode(kind);
    const service = findNoCodeRelationSystemEntity(serviceCode) || {
        code: serviceCode,
        label: serviceCode === "utilisateurs" ? "Agents" : "Services",
        relation_kind: "system",
        is_active: true,
    };
    return {
        service,
        records: directoryRows().map((row) => directoryRelationRecordFromRow(row, kind)).filter((row) => row.id),
        relations: Array.isArray(context.relations) ? context.relations : [],
        selectedRecordKeys: Array.isArray(context.selectedRecordKeys) ? context.selectedRecordKeys : [],
        _recordsTreeView: null,
    };
}

function directoryRelationsForRow(row) {
    if (!row || !String(row.id || "").trim()) {
        return [];
    }
    return noCodeRecordRelationsForContext(directoryRelationContext());
}

function directoryRowById(recordId) {
    const normalizedRecordId = String(recordId || "").trim();
    if (!normalizedRecordId) {
        return null;
    }
    return directoryRows().find((row) => String(row?.id || "").trim() === normalizedRecordId)
        || (Array.isArray(state.directoryContext?.rows) ? state.directoryContext.rows : [])
            .find((row) => String(row?.id || "").trim() === normalizedRecordId)
        || null;
}

function directoryRelationIsEditable(relationContext, relation) {
    const currentCode = String(relationContext?.service?.code || "").trim().toLowerCase();
    const linkedCode = noCodeRelationLinkedServiceCodeForContext(relationContext, relation);
    return Boolean(currentCode && linkedCode);
}

function directoryEditableRelationsForContext(relationContext = directoryRelationContext()) {
    return noCodeRecordRelationsForContext(relationContext)
        .filter((relation) => directoryRelationIsEditable(relationContext, relation));
}

function directorySelectedRows() {
    const tree = directoryTreeView || null;
    if (tree && typeof tree.getSelectedRows === "function") {
        return tree.getSelectedRows();
    }
    const selected = new Set(
        Array.isArray(state.directoryContext?.selectedRecordKeys)
            ? state.directoryContext.selectedRecordKeys.map((key) => String(key || "").trim()).filter(Boolean)
            : [],
    );
    return directoryRows().filter((row) => selected.has(String(row?.id || "").trim()));
}

function directoryColumns(kind = "") {
    const linkedColumns = linkedColumnsForContext(state.directoryContext);
    if (String(kind || "").trim().toLowerCase() === "services") {
        return [
            { key: "label", label: "Service" },
            { key: "code", label: "Code" },
            { key: "description", label: "Description" },
            { key: "manager", label: "Responsable" },
            { key: "distinguished_name", label: "DN" },
            ...linkedColumns,
        ];
    }
    return [
        { key: "identity", label: "Identite" },
        { key: "login", label: "Identifiant" },
        { key: "status", label: "Statut" },
        { key: "linked_services", label: "Services" },
        { key: "distinguished_name", label: "DN" },
        ...linkedColumns,
    ];
}

function compareDirectoryRows(column, direction, left, right) {
    const dir = direction === "desc" ? -1 : 1;
    const key = String(column || "label").trim() || "label";
    const valueFor = (row) => key.startsWith("linked:")
        ? String(row?.linked_column_values?.[key] || "")
        : String(row?.[key] || "");
    return valueFor(left).localeCompare(valueFor(right), undefined, { sensitivity: "base" }) * dir;
}

class DirectoryTreeView extends (window.NMPSharedUi?.treeView?.SharedTreeView || class {}) {
    constructor() {
        const kind = String(state.directoryContext?.kind || "agents").trim().toLowerCase();
        super({
            headElement: document.getElementById("directory-head"),
            bodyElement: document.getElementById("directory-body"),
            searchInput: document.getElementById("directory-search"),
            sortState: state.directorySort,
            columnAttr: "directory-col",
            renderHead: true,
            manageSortBinding: true,
            manageSearchBinding: true,
            searchThreshold: 5,
            emptyMessage: "Aucune donnee synchronisee.",
            selectable: true,
            selectedRowKeys: Array.isArray(state.directoryContext?.selectedRecordKeys) ? state.directoryContext.selectedRecordKeys : [],
            columnVisibilityStorageKey: `nmp:treeview:columns:directory:${kind}`,
            hiddenColumnKeys: kind === "agents" ? ["distinguished_name"] : [],
            getColumnMenuExtraMarkup: () => linkedColumnMenuMarkup(state.directoryContext),
            onColumnMenuExtraAction: (action, trigger) => handleLinkedColumnMenuAction(
                state.directoryContext,
                action,
                trigger,
                () => renderDirectoryTreeView(),
            ),
            getRows: () => directoryRows(),
            getColumns: () => [...directoryColumns(kind), { key: "actions", label: "Actions", sortable: false }],
            searchText: (row) => Object.values(row || {}).join(" "),
            compareRows: (column, direction, left, right) => compareDirectoryRows(column, direction, left, right),
            getRowKey: (row, index) => String(row?.id || `${kind}_${index}`),
            onSelectionChanged: ({ selectedKeys }) => {
                if (state.directoryContext) {
                    state.directoryContext.selectedRecordKeys = Array.isArray(selectedKeys) ? selectedKeys : [];
                }
                updateDirectoryBatchActions();
            },
            renderRowCells: (row) => {
                const actions = createIconActionButtonMarkup({
                    icon: "settings",
                    action: "directory:record:edit",
                    title: kind === "agents" ? "Ouvrir la fiche agent" : "Ouvrir la fiche service",
                    data: { record_id: String(row?.id || "") },
                });
                return `
                    ${directoryColumns(kind).map((column) => {
                        const isLinkedColumn = String(column.key || "").startsWith("linked:");
                        const value = isLinkedColumn
                            ? String(row?.linked_column_values?.[column.key] || "")
                            : String(row?.[column.key] || "");
                        return `<td>${isLinkedColumn ? renderLinkedColumnCell(row, column) : escapeHtml(value)}</td>`;
                    }).join("")}
                    <td class="inventory-row-actions">${actions}</td>
                `;
            },
        });
    }
}

function renderStorageTreeViews() {
    if (storageRemoteTreeView instanceof StorageRemoteTreeView) {
        storageRemoteTreeView.render();
    }
    if (storageLocalTreeView instanceof StorageLocalTreeView) {
        storageLocalTreeView.render();
    }
}

function ensureDirectoryTreeView() {
    const BaseClass = window.NMPSharedUi?.treeView?.SharedTreeView;
    if (!BaseClass) {
        return null;
    }
    const currentHead = document.getElementById("directory-head");
    const currentBody = document.getElementById("directory-body");
    if (!(currentHead instanceof HTMLElement) || !(currentBody instanceof HTMLElement)) {
        return null;
    }
    if (
        directoryTreeView instanceof DirectoryTreeView
        && directoryTreeView.headElement === currentHead
        && directoryTreeView.bodyElement === currentBody
    ) {
        return directoryTreeView;
    }
    directoryTreeView = new DirectoryTreeView();
    return directoryTreeView;
}

function renderDirectoryTreeView() {
    const tree = ensureDirectoryTreeView();
    if (tree) {
        tree.render();
    }
    bindDirectoryContextMenu();
    bindDirectoryDoubleClick();
    bindDirectoryFilters();
    updateDirectoryBatchActions();
}

async function fetchDirectoryContext(kind, previousContext = {}) {
    const normalizedKind = String(kind || "").trim().toLowerCase() === "services" ? "services" : "agents";
    await loadAdministrationData({
        includeModules: false,
        includeRoles: false,
        includeUsers: false,
        includeServices: true,
        includeSharedLists: false,
    });
    const payload = await requestJson(`/directory/${encodeURIComponent(normalizedKind)}`);
    const rows = Array.isArray(payload?.items) ? payload.items : [];
    const relationServiceCode = directoryServiceCode(normalizedKind);
    const relations = await fetchNoCodeServiceRelations(relationServiceCode).catch(() => []);
    const context = {
        kind: normalizedKind,
        rows,
        relations,
        selectedRecordKeys: Array.isArray(previousContext?.selectedRecordKeys)
            ? previousContext.selectedRecordKeys.map((value) => String(value || "").trim()).filter(Boolean)
            : [],
        linkedColumns: Array.isArray(previousContext?.linkedColumns) ? previousContext.linkedColumns : [],
        statusFilter: String(previousContext?.statusFilter ?? (normalizedKind === "agents" ? "Actif" : "")).trim(),
    };
    for (const column of linkedColumnsForContext(context)) {
        await hydrateLinkedColumn(context, column).catch(() => {});
    }
    return context;
}

async function refreshDirectoryContextRows(kind = state.directoryContext?.kind || "agents") {
    const previousContext = state.directoryContext || {};
    state.directoryContext = await fetchDirectoryContext(kind, previousContext);
    if (state.directoryRecordEditor?.row?.id) {
        const recordId = String(state.directoryRecordEditor.row.id || "").trim();
        const refreshedRow = directoryRowById(recordId);
        if (refreshedRow) {
            state.directoryRecordEditor = {
                ...state.directoryRecordEditor,
                row: refreshedRow,
            };
        }
    }
    if (directoryTreeView) {
        directoryTreeView = null;
        renderDirectoryTreeView();
    }
    return state.directoryContext;
}

async function fetchDirectoryRow(kind, recordId) {
    const normalizedKind = String(kind || "").trim().toLowerCase() === "services" ? "services" : "agents";
    const normalizedRecordId = String(recordId || "").trim();
    if (!normalizedRecordId) {
        return null;
    }
    const params = new URLSearchParams({ record_id: normalizedRecordId });
    const payload = await requestJson(`/directory/${encodeURIComponent(normalizedKind)}?${params.toString()}`);
    const rows = Array.isArray(payload?.items) ? payload.items : [];
    return rows.find((row) => String(row?.id || "").trim() === normalizedRecordId) || null;
}

function replaceDirectoryContextRow(context, kind, refreshedRow) {
    if (!context || typeof context !== "object" || !refreshedRow) {
        return context;
    }
    const normalizedKind = String(kind || context.kind || "agents").trim().toLowerCase() === "services" ? "services" : "agents";
    const recordId = String(refreshedRow?.id || "").trim();
    if (!recordId) {
        return context;
    }
    const rows = Array.isArray(context.rows) ? [...context.rows] : [];
    const index = rows.findIndex((row) => String(row?.id || "").trim() === recordId);
    if (index >= 0) {
        rows[index] = refreshedRow;
    } else {
        rows.push(refreshedRow);
    }
    return {
        ...context,
        kind: normalizedKind,
        rows,
    };
}

function refreshDirectoryBackSnapshotsRow(kind, refreshedRow) {
    const normalizedKind = String(kind || "").trim().toLowerCase() === "services" ? "services" : "agents";
    const recordId = String(refreshedRow?.id || "").trim();
    if (!recordId || !Array.isArray(state.modalBackStack)) {
        return;
    }
    state.modalBackStack = state.modalBackStack.map((snapshot) => {
        if (!snapshot || typeof snapshot !== "object") {
            return snapshot;
        }
        const nextSnapshot = { ...snapshot };
        if (nextSnapshot.directoryContext && typeof nextSnapshot.directoryContext === "object") {
            const snapshotKind = String(nextSnapshot.directoryContext.kind || normalizedKind).trim().toLowerCase() === "services" ? "services" : "agents";
            if (snapshotKind === normalizedKind) {
                nextSnapshot.directoryContext = replaceDirectoryContextRow(nextSnapshot.directoryContext, normalizedKind, refreshedRow);
            }
        }
        if (
            nextSnapshot.directoryRecordEditor
            && String(nextSnapshot.directoryRecordEditor?.row?.id || "").trim() === recordId
        ) {
            nextSnapshot.directoryRecordEditor = {
                ...nextSnapshot.directoryRecordEditor,
                kind: normalizedKind,
                row: refreshedRow,
            };
        }
        return nextSnapshot;
    });
}

async function refreshDirectoryContextRow(kind = state.directoryContext?.kind || "agents", recordId = state.directoryRecordEditor?.row?.id || "") {
    const normalizedKind = String(kind || "").trim().toLowerCase() === "services" ? "services" : "agents";
    const normalizedRecordId = String(recordId || "").trim();
    if (!state.directoryContext || !normalizedRecordId) {
        return null;
    }
    const refreshedRow = await fetchDirectoryRow(normalizedKind, normalizedRecordId);
    if (!refreshedRow) {
        return null;
    }
    state.directoryContext = replaceDirectoryContextRow(state.directoryContext, normalizedKind, refreshedRow);
    refreshDirectoryBackSnapshotsRow(normalizedKind, refreshedRow);
    if (state.directoryRecordEditor?.row?.id && String(state.directoryRecordEditor.row.id || "").trim() === normalizedRecordId) {
        state.directoryRecordEditor = {
            ...state.directoryRecordEditor,
            kind: normalizedKind,
            row: refreshedRow,
        };
    }
    if (directoryTreeView) {
        directoryTreeView.render();
    } else {
        renderDirectoryTreeView();
    }
    return refreshedRow;
}

function updateDirectoryBatchActions() {
    const button = document.getElementById("directory-batch-relation-assign");
    if (!(button instanceof HTMLButtonElement)) {
        return;
    }
    const selectedCount = directorySelectedRows().length;
    const hasEditableRelations = directoryEditableRelationsForContext().length > 0;
    button.disabled = selectedCount <= 0 || !hasEditableRelations;
    const label = selectedCount > 0
        ? `Assigner element lie (${selectedCount})`
        : "Assigner element lie";
    const labelNode = button.querySelector(".ui-action-btn-label") || button.querySelector("span:last-child");
    if (labelNode instanceof HTMLElement) {
        labelNode.textContent = label;
    } else {
        button.textContent = label;
    }
}

function bindDirectoryFilters() {
    const statusSelect = document.getElementById("directory-status-filter");
    if (!(statusSelect instanceof HTMLSelectElement) || statusSelect.dataset.directoryFilterBound === "1") {
        return;
    }
    statusSelect.dataset.directoryFilterBound = "1";
    statusSelect.addEventListener("change", () => {
        if (state.directoryContext) {
            state.directoryContext.statusFilter = String(statusSelect.value || "");
            state.directoryContext.selectedRecordKeys = [];
        }
        if (directoryTreeView) {
            directoryTreeView.selectedRowKeys = new Set();
            directoryTreeView.render();
        } else {
            renderDirectoryTreeView();
        }
        updateDirectoryBatchActions();
    });
}

function buildDirectoryContextMenuMarkup(rows) {
    const selectedRows = Array.isArray(rows) ? rows : [];
    const singleRecord = selectedRows.length === 1 ? selectedRows[0] : null;
    const relationContext = directoryRelationContext();
    const relations = singleRecord ? noCodeRecordRelationsForContext(relationContext) : [];
    const batchRelations = selectedRows.length ? directoryEditableRelationsForContext(relationContext) : [];
    const recordId = String(singleRecord?.id || "");
    const batchMarkup = batchRelations.length
        ? `
            <button class="context-menu-item" type="button" data-action="directory:batch:relation-assign">
                <span>Assigner un element lie</span>
            </button>
        `
        : "";
    const relationsMarkup = relations.length
        ? `
            <div class="context-menu-sep"></div>
            <div class="context-menu-label">Relations</div>
            ${relations.map((relation) => `
                <button class="context-menu-item" type="button"
                    data-action="directory:record:relation-open"
                    data-relation-id="${escapeHtml(String(relation?.id || ""))}"
                    data-record-id="${escapeHtml(recordId)}">
                    <span>${escapeHtml(noCodeRelationMenuLabel(relationContext, relation))}</span>
                </button>
            `).join("")}
        `
        : "";
    return `
        <div class="context-menu-group">
            <div class="context-menu-title">${escapeHtml(`${selectedRows.length} ligne${selectedRows.length > 1 ? "s" : ""} selectionnee${selectedRows.length > 1 ? "s" : ""}`)}</div>
            ${singleRecord ? `
                <button class="context-menu-item" type="button"
                    data-action="directory:record:edit"
                    data-record-id="${escapeHtml(recordId)}">
                    <span>Ouvrir la fiche</span>
                </button>
            ` : ""}
            ${batchMarkup}
            ${relationsMarkup}
            ${singleRecord || batchMarkup || relationsMarkup ? "" : '<div class="context-menu-label">Aucune action disponible pour cette selection.</div>'}
        </div>
    `;
}

function openDirectoryContextMenu(x, y, rows = directorySelectedRows()) {
    const selectedRows = Array.isArray(rows) ? rows : [];
    if (!selectedRows.length || !(cardsContextMenu instanceof HTMLElement)) {
        return false;
    }
    state.noCodeServiceRecordContext = directoryRelationContext();
    cardsContextMenu.innerHTML = buildDirectoryContextMenuMarkup(selectedRows);
    cardsContextMenu.hidden = false;
    const maxX = window.innerWidth - cardsContextMenu.offsetWidth - 12;
    const maxY = window.innerHeight - cardsContextMenu.offsetHeight - 12;
    cardsContextMenu.style.left = `${Math.max(8, Math.min(x, maxX))}px`;
    cardsContextMenu.style.top = `${Math.max(8, Math.min(y, maxY))}px`;
    return true;
}

function bindDirectoryContextMenu() {
    const body = document.getElementById("directory-body");
    if (!(body instanceof HTMLElement) || body.dataset.directoryContextMenuBound === "1") {
        return;
    }
    body.dataset.directoryContextMenuBound = "1";
    body.addEventListener("contextmenu", (event) => {
        const target = event.target;
        if (!(target instanceof Element) || target.closest("button, a, input, select, textarea")) {
            return;
        }
        const rowElement = target.closest("tr[data-tree-row-key]");
        if (!(rowElement instanceof HTMLElement)) {
            return;
        }
        const recordId = String(rowElement.dataset.treeRowKey || "").trim();
        if (!recordId || !state.directoryContext) {
            return;
        }
        const selectedKeys = new Set(
            Array.isArray(state.directoryContext.selectedRecordKeys)
                ? state.directoryContext.selectedRecordKeys.map((key) => String(key || "").trim()).filter(Boolean)
                : [],
        );
        if (!selectedKeys.has(recordId)) {
            state.directoryContext.selectedRecordKeys = [recordId];
            if (directoryTreeView) {
                directoryTreeView.selectedRowKeys = new Set([recordId]);
                directoryTreeView.render();
            }
        }
        const selectedRows = directorySelectedRows();
        if (!selectedRows.length) {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        openDirectoryContextMenu(event.clientX, event.clientY, selectedRows);
    });
}

function bindDirectoryDoubleClick() {
    const body = document.getElementById("directory-body");
    if (!(body instanceof HTMLElement) || body.dataset.directoryDblclickBound === "1") {
        return;
    }
    body.dataset.directoryDblclickBound = "1";
    body.addEventListener("dblclick", (event) => {
        const target = event.target;
        if (!(target instanceof Element) || target.closest("button, a, input, select, textarea")) {
            return;
        }
        const rowElement = target.closest("tr[data-tree-row-key]");
        if (!(rowElement instanceof HTMLElement)) {
            return;
        }
        const recordId = String(rowElement.dataset.treeRowKey || "").trim();
        if (!recordId) {
            return;
        }
        openDirectoryRecordEditor(recordId).catch((error) => {
            openModal("Fiche indisponible", `<p class="muted">${escapeHtml(normalizeErrorMessage(error.message))}</p>`);
        });
    });
}

async function openDirectoryRecordRelationLinks(recordId, relationId) {
    const normalizedRecordId = String(recordId || "").trim();
    const normalizedRelationId = Number(relationId || 0);
    if (!normalizedRecordId || normalizedRelationId <= 0) {
        throw new Error("Relation introuvable.");
    }
    const relationContext = directoryRelationContext();
    state.noCodeServiceRecordContext = relationContext;
    await openNoCodeRecordRelationLinksModal({
        serviceCode: relationContext.service?.code,
        recordId: normalizedRecordId,
        relationId: normalizedRelationId,
    });
}

function directoryRecordDetailFields(row, kind = state.directoryContext?.kind || "agents") {
    const normalizedKind = String(kind || "").trim().toLowerCase();
    if (normalizedKind === "services") {
        return [
            ["Service", row?.label],
            ["Code", row?.code],
            ["Description", row?.description],
            ["Responsable", row?.manager],
        ];
    }
    return [
        ["Identite", row?.identity || row?.label],
        ["Identifiant", row?.login],
        ["Statut AD", row?.status],
    ];
}

function directoryRecordTechnicalFields(row, kind = state.directoryContext?.kind || "agents") {
    const normalizedKind = String(kind || "").trim().toLowerCase();
    if (normalizedKind === "services") {
        return [
            ["DN", row?.distinguished_name],
        ];
    }
    return [
        ["DN", row?.distinguished_name],
    ];
}

function buildDirectoryRecordEditorMarkup() {
    const editor = state.directoryRecordEditor;
    const row = editor?.row || {};
    const kind = String(editor?.kind || state.directoryContext?.kind || "agents").trim().toLowerCase();
    const relationContext = state.noCodeServiceRecordContext || directoryRelationContext();
    const relationMarkup = buildNoCodeRecordRelationExperienceMarkup(relationContext, state.noCodeRecordEditor);
    const recordAssignmentMarkup = buildRecordAssignmentMarkup(relationContext, state.noCodeRecordEditor);
    const fieldsMarkup = directoryRecordDetailFields(row, kind).map(([label, value]) => `
        <label class="field">
            <span>${escapeHtml(String(label || ""))}</span>
            <input type="text" value="${escapeHtml(String(value || ""))}" readonly>
        </label>
    `).join("");
    const technicalFieldsMarkup = directoryRecordTechnicalFields(row, kind)
        .filter(([_label, value]) => String(value || "").trim())
        .map(([label, value]) => `
            <label class="field">
                <span>${escapeHtml(String(label || ""))}</span>
                <input type="text" value="${escapeHtml(String(value || ""))}" readonly>
            </label>
        `).join("");
    const recordLabel = kind === "agents"
        ? String(row?.identity || row?.label || row?.login || row?.id || "Agent")
        : String(row?.label || row?.code || row?.id || "Service");
    return `
        <form id="modal-directory-record-form" class="modal-form" data-record-id="${escapeHtml(String(row?.id || ""))}">
            <section class="modal-section">
                <h3>${escapeHtml(recordLabel)}</h3>
                <div class="modal-settings-grid">
                    ${fieldsMarkup}
                </div>
            </section>
            ${relationMarkup || recordAssignmentMarkup ? "" : `
                <section class="modal-section">
                    <h3>Relations</h3>
                    <p class="muted">Aucune relation editable n'est disponible pour cette entite.</p>
                </section>
            `}
            ${recordAssignmentMarkup}
            ${technicalFieldsMarkup ? `
                <section class="modal-section">
                    <details class="record-technical-accordion">
                        <summary>Informations supplementaires</summary>
                        <div class="modal-settings-grid">
                            ${technicalFieldsMarkup}
                        </div>
                    </details>
                </section>
            ` : ""}
            <p id="modal-directory-record-feedback" class="muted inventory-feedback"></p>
            ${createModalActionsMarkup({
                buttons: [
                    { className: "toolbar-btn", type: "button", action: "modal:close", label: "Fermer" },
                    { className: "primary-btn", type: "submit", label: "Enregistrer les modifications", disabled: !relationMarkup },
                ],
            })}
        </form>
    `;
}

function createDirectoryRecordRelationEditor(row, kind) {
    const record = directoryRelationRecordFromRow(row, kind);
    return {
        mode: "edit",
        recordId: String(record.id || ""),
        versionToken: "",
        values: record.values || {},
        credentials: {},
        hasCredentialPassword: false,
        credentialPasswordMask: "",
        children: [],
        relationStates: {},
        indirectRelationSections: [],
        openRelationEditorIds: [],
    };
}

function directoryRecordSnapshotIsCoherent(snapshot, kind) {
    const expectedServiceCode = directoryServiceCode(kind);
    const snapshotServiceCode = String(snapshot?.noCodeServiceRecordContext?.service?.code || "").trim().toLowerCase();
    const snapshotRecordId = String(snapshot?.noCodeRecordEditor?.recordId || "").trim();
    const directoryRecordId = String(snapshot?.directoryRecordEditor?.row?.id || "").trim();
    return Boolean(
        expectedServiceCode
        && snapshotServiceCode === expectedServiceCode
        && snapshotRecordId
        && snapshotRecordId === directoryRecordId
    );
}

function scheduleDirectoryRecordRelationExperienceLoad() {
    window.setTimeout(() => {
        loadNoCodeRecordRelationExperience().catch((error) => {
            const feedback = document.getElementById("modal-directory-record-feedback");
            if (feedback instanceof HTMLElement) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        });
    }, 0);
}

async function openDirectoryRecordEditor(recordId, options = {}) {
    const row = directoryRowById(recordId);
    if (!row) {
        throw new Error("Fiche introuvable.");
    }
    if (options.pushBack !== false) {
        pushModalBackSnapshot();
    }
    const kind = String(state.directoryContext?.kind || "agents").trim().toLowerCase();
    const relationContext = directoryRelationContext();
    state.directoryRecordEditor = { kind, row };
    state.noCodeServiceRecordContext = relationContext;
    state.noCodeRecordViewer = null;
    state.noCodeRecordEditor = createDirectoryRecordRelationEditor(row, kind);
    openModal(
        kind === "agents" ? "Edition — Agent" : "Edition — Service",
        buildDirectoryRecordEditorMarkup(),
        noCodeInlineOptions("min(980px, calc(100vw - 40px))", { inline: options.inline !== false }),
    );
    scheduleDirectoryRecordRelationExperienceLoad();
}

async function submitDirectoryRecordEditorForm() {
    const feedback = document.getElementById("modal-directory-record-feedback");
    if (feedback instanceof HTMLElement) {
        feedback.textContent = "";
    }
    const context = state.noCodeServiceRecordContext;
    const editor = state.noCodeRecordEditor;
    if (!context?.service || !editor?.recordId) {
        if (feedback instanceof HTMLElement) {
            feedback.textContent = "Fiche introuvable.";
        }
        return;
    }
    if (!validateRecordRelationSelectionLimits(feedback)) {
        return;
    }
    try {
        const result = await syncNoCodeRecordRelationSelections({
            serviceCode: String(context.service.code || ""),
            recordId: String(editor.recordId || ""),
            selections: readNoCodeRecordRelationSelectionsFromDom(),
            editor,
            context,
        });
        const changed = Number(result?.created || 0) + Number(result?.deleted || 0);
        if (changed) {
            const kind = state.directoryContext?.kind || state.directoryRecordEditor?.kind || "agents";
            const refreshedRow = await refreshDirectoryContextRow(kind, String(editor.recordId || ""));
            if (!refreshedRow) {
                await refreshDirectoryContextRows(kind);
            }
            consumeModalDirectoryDirty();
            await loadNoCodeRecordRelationExperience();
        }
        showAppSaveFeedback({
            feedback: document.getElementById("modal-directory-record-feedback"),
            message: changed
                ? `Fiche mise a jour: ${Number(result.created || 0)} lien(s) ajoute(s), ${Number(result.deleted || 0)} retire(s).`
                : "Fiche enregistree. Aucune relation modifiee.",
        });
    } catch (error) {
        showAppSaveFeedback({
            feedback,
            kind: "error",
            message: normalizeErrorMessage(error.message),
            durationMs: 4200,
        });
    }
}

function directoryBatchRelationRows() {
    return directorySelectedRows()
        .map((row) => directoryRelationRecordFromRow(row))
        .filter((row) => String(row?.id || "").trim());
}

function buildDirectoryBatchRelationAssignMarkup(context) {
    const selectedRows = Array.isArray(context?.selectedRows) ? context.selectedRows : [];
    const relations = Array.isArray(context?.relations) ? context.relations : [];
    const selectedRelationId = String(context?.relation?.id || "");
    const candidates = Array.isArray(context?.candidates) ? context.candidates : [];
    const linkedService = context?.linkedService || {};
    const selectedIds = Array.isArray(context?.selectedLinkedRecordIds) ? context.selectedLinkedRecordIds : [];
    const relationOptions = relations.map((relation) => `
        <option value="${escapeHtml(String(relation?.id || ""))}" ${String(relation?.id || "") === selectedRelationId ? "selected" : ""}>
            ${escapeHtml(noCodeRelationLabelForContext(context?.relationContext, relation))}
        </option>
    `).join("");
    const candidatePicker = buildRelationAssignmentCandidatePickerMarkup({
        linkedService,
        relationContext: context?.relationContext,
        relation: context?.relation,
        candidates,
        selectedIds,
    });
    return `
        <form id="modal-directory-batch-relation-form" class="modal-form" data-relation-id="${escapeHtml(selectedRelationId)}">
            <div class="modal-stack">
                <p class="muted">${escapeHtml(`${selectedRows.length} agent${selectedRows.length > 1 ? "s" : ""} selectionne${selectedRows.length > 1 ? "s" : ""}.`)}</p>
                <div class="modal-settings-grid">
                    <label class="field">
                        <span>Relation</span>
                        <select name="relation_id" data-directory-batch-relation-select>
                            ${relationOptions}
                        </select>
                    </label>
                </div>
                ${candidatePicker}
                <p id="modal-directory-batch-relation-feedback" class="muted inventory-feedback"></p>
                <div class="modal-actions">
                    <button type="button" class="ghost-button" data-action="modal:close">Annuler</button>
                    <button type="submit" class="primary-button" ${candidates.length ? "" : "disabled"}>Assigner</button>
                </div>
            </div>
        </form>
    `;
}

async function loadDirectoryBatchRelationAssignContext(relationId = "") {
    const relationContext = directoryRelationContext();
    const selectedRows = directoryBatchRelationRows();
    if (!selectedRows.length) {
        throw new Error("Selectionnez au moins un agent.");
    }
    const relations = directoryEditableRelationsForContext(relationContext);
    if (!relations.length) {
        throw new Error("Aucune relation n'est disponible pour cet annuaire.");
    }
    const wantedRelationId = Number(relationId || 0);
    const relation = relations.find((row) => Number(row?.id || 0) === wantedRelationId) || relations[0];
    const linkedServiceCode = noCodeRelationLinkedServiceCodeForContext(relationContext, relation);
    let linkedService = findNoCodeRelationEntity(linkedServiceCode);
    if (!linkedService) {
        await loadAdministrationData({
            includeModules: false,
            includeRoles: false,
            includeUsers: false,
            includeServices: true,
            includeSharedLists: false,
        });
        linkedService = findNoCodeRelationEntity(linkedServiceCode);
    }
    const candidatePage = await fetchNoCodeServiceRecordsPage(linkedServiceCode, {
        search: "",
        activeOnly: true,
        limit: 500,
        offset: 0,
        sort: "label",
        direction: "asc",
    }).catch(() => ({ items: [] }));
    return {
        relationContext,
        selectedRows,
        relations,
        relation,
        linkedService: linkedService || { code: linkedServiceCode, label: linkedServiceCode },
        candidates: Array.isArray(candidatePage?.items) ? candidatePage.items : [],
    };
}

async function openDirectoryBatchRelationAssignModal(relationId = "") {
    const context = await loadDirectoryBatchRelationAssignContext(relationId);
    state.directoryBatchRelationContext = context;
    openModal(
        "Assigner un element lie",
        buildDirectoryBatchRelationAssignMarkup(context),
        { width: "min(720px, calc(100vw - 32px))" },
    );
}

async function reloadDirectoryBatchRelationAssignModal(relationId) {
    const feedback = document.getElementById("modal-directory-batch-relation-feedback");
    try {
        const context = await loadDirectoryBatchRelationAssignContext(relationId);
        state.directoryBatchRelationContext = context;
        const form = document.getElementById("modal-directory-batch-relation-form");
        const parent = form?.parentElement;
        if (parent instanceof HTMLElement) {
            parent.innerHTML = buildDirectoryBatchRelationAssignMarkup(context);
        }
    } catch (error) {
        if (feedback instanceof HTMLElement) {
            feedback.textContent = normalizeErrorMessage(error.message);
        }
    }
}

async function submitDirectoryBatchRelationAssignForm(form) {
    const feedback = document.getElementById("modal-directory-batch-relation-feedback");
    if (feedback instanceof HTMLElement) {
        feedback.textContent = "";
    }
    const data = new window.FormData(form);
    const relationId = Number(data.get("relation_id") || 0);
    const linkedRecordIds = readRelationAssignmentSelectedIds(form);
    const context = state.directoryBatchRelationContext || await loadDirectoryBatchRelationAssignContext(relationId);
    const rows = Array.isArray(context?.selectedRows) ? context.selectedRows : [];
    if (!rows.length || relationId <= 0 || !linkedRecordIds.length) {
        if (feedback instanceof HTMLElement) {
            feedback.textContent = "Selectionnez une relation et au moins un element a lier.";
        }
        return;
    }
    const relation = noCodeRecordRelationsForContext(context.relationContext)
        .find((row) => Number(row?.id || 0) === relationId);
    if (!noCodeRelationAllowsMultipleLinkedFromCurrent(context.relationContext, relation) && linkedRecordIds.length > 1) {
        if (feedback instanceof HTMLElement) {
            feedback.textContent = "Cette relation accepte un seul element lie par fiche.";
        }
        return;
    }
    try {
        const totals = { created: 0, replaced: 0, skipped: 0, errors: [] };
        for (const linkedRecordId of linkedRecordIds) {
            const result = await assignNoCodeRelationLinkToRecords({
                context: context.relationContext,
                records: rows,
                relation,
                linkedRecordId,
            });
            totals.created += Number(result.created || 0);
            totals.replaced += Number(result.replaced || 0);
            totals.skipped += Number(result.skipped || 0);
            totals.errors.push(...(Array.isArray(result.errors) ? result.errors : []));
        }
        if (feedback instanceof HTMLElement) {
            const skippedSuffix = totals.skipped ? ` ${totals.skipped} deja lie(s) ou ignore(s).` : "";
            const replacedSuffix = totals.replaced ? ` ${totals.replaced} ancien(s) lien(s) remplace(s).` : "";
            feedback.textContent = totals.errors.length
                ? `Lien applique a ${totals.created} agent(s).${replacedSuffix}${skippedSuffix} Erreurs: ${totals.errors.slice(0, 3).join(" | ")}`
                : `Lien applique a ${totals.created} agent(s).${replacedSuffix}${skippedSuffix}`;
        }
    } catch (error) {
        if (feedback instanceof HTMLElement) {
            feedback.textContent = normalizeErrorMessage(error.message);
        }
    }
}

function ensureStorageTreeViews() {
    const BaseClass = window.NMPSharedUi?.treeView?.SharedTreeView;
    if (typeof BaseClass !== "function") {
        return null;
    }
    if (!(storageRemoteTreeView instanceof StorageRemoteTreeView)) {
        storageRemoteTreeView = new StorageRemoteTreeView();
    }
    if (!(storageLocalTreeView instanceof StorageLocalTreeView)) {
        storageLocalTreeView = new StorageLocalTreeView();
    }
    return { remote: storageRemoteTreeView, local: storageLocalTreeView };
}

function syncStorageTargetFormType(form) {
    const normalizedType = String(form?.querySelector?.('[name="storage_target_type"]')?.value || "smb3").trim().toLowerCase();
    const remoteFields = form?.querySelector?.('[data-storage-target-kind="smb3"]');
    const localInfo = form?.querySelector?.('[data-storage-target-kind="local"]');
    const isLocal = normalizedType === "local";
    if (remoteFields instanceof HTMLElement) {
        remoteFields.hidden = isLocal;
    }
    if (localInfo instanceof HTMLElement) {
        localInfo.hidden = !isLocal;
    }
    const submitButton = form?.querySelector?.('[type="submit"]');
    if (submitButton instanceof HTMLButtonElement) {
        submitButton.disabled = isLocal;
    }
}

function resetStorageTargetForm(form) {
    if (!(form instanceof HTMLFormElement)) {
        return;
    }
    form.reset();
    form.dataset.editTargetId = "";
    form.hidden = true;
    const title = document.getElementById("modal-storage-target-form-title");
    if (title) {
        title.textContent = "Nouvel emplacement distant";
    }
    const submitButton = form.querySelector('[type="submit"]');
    if (submitButton instanceof HTMLButtonElement) {
        submitButton.textContent = "Declarer l'emplacement";
    }
    const autoMount = form.querySelector('[name="auto_mount_enabled"]');
    if (autoMount instanceof HTMLInputElement) {
        autoMount.checked = true;
    }
    const feedback = document.getElementById("modal-storage-target-feedback");
    if (feedback) {
        feedback.textContent = "";
    }
    syncStorageTargetFormType(form);
}

function openStorageTargetForm(target = null) {
    const form = document.getElementById("modal-storage-target-form");
    if (!(form instanceof HTMLFormElement)) {
        return;
    }
    resetStorageTargetForm(form);
    const editTarget = target || null;
    form.hidden = false;
    form.dataset.editTargetId = String(editTarget?.id || "");
    const title = document.getElementById("modal-storage-target-form-title");
    if (title) {
        title.textContent = editTarget ? "Modifier l'emplacement distant" : "Nouvel emplacement distant";
    }
    const submitButton = form.querySelector('[type="submit"]');
    if (submitButton instanceof HTMLButtonElement) {
        submitButton.textContent = editTarget ? "Enregistrer" : "Declarer l'emplacement";
    }
    form.querySelector('[name="label"]').value = String(editTarget?.label || "Sauvegarde fichiers");
    form.querySelector('[name="service_code"]').value = String(editTarget?.service_code || "monitoring.device_config_files");
    form.querySelector('[name="remote_path"]').value = String(editTarget?.remote_path || "");
    form.querySelector('[name="username"]').value = String(editTarget?.username || "");
    form.querySelector('[name="password"]').value = "";
    form.querySelector('[name="local_mount_path"]').value = String(editTarget?.local_mount_path || "");
    const autoMount = form.querySelector('[name="auto_mount_enabled"]');
    if (autoMount instanceof HTMLInputElement) {
        autoMount.checked = editTarget ? Boolean(editTarget?.auto_mount_enabled) : true;
    }
    const typeField = form.querySelector('[name="storage_target_type"]');
    if (typeField instanceof HTMLSelectElement) {
        typeField.value = "smb3";
    }
    syncStorageTargetFormType(form);
    form.scrollIntoView({ behavior: "smooth", block: "start" });
}

function storageTargetFormMarkup() {
    return `
        <form id="modal-storage-target-form" class="modal-form storage-target-form" hidden>
            <section class="modal-section">
                <div class="section-head">
                    <div>
                        <h3 id="modal-storage-target-form-title">Nouvel emplacement distant</h3>
                        <p class="muted">Declaration dynamique d'un stockage utilisable par un service ITops.</p>
                    </div>
                    ${createIconActionButtonMarkup({
                        icon: "close",
                        action: "storage-target:cancel",
                        title: "Fermer le formulaire",
                    })}
                </div>
                <div class="modal-settings-grid">
                    <label class="field">
                        <span>Type d'emplacement</span>
                        <select name="storage_target_type">
                            <option value="smb3">Montage distant SMB3</option>
                            <option value="local">Stockage local serveur</option>
                        </select>
                    </label>
                    <label class="field">
                        <span>Service</span>
                        <select name="service_code">
                            <option value="monitoring.device_config_files">Monitoring - fichiers de configuration</option>
                            <option value="platform.storage">Stockage ITops</option>
                        </select>
                    </label>
                    <label class="field wide">
                        <span>Nom</span>
                        <input name="label" type="text" value="Sauvegarde fichiers" required>
                    </label>
                </div>
                <div class="modal-settings-grid" data-storage-target-kind="smb3">
                    <label class="field wide">
                        <span>Chemin distant SMB</span>
                        <input name="remote_path" type="text" placeholder="\\\\serveur\\partage\\dossier" required>
                    </label>
                    <label class="field">
                        <span>Utilisateur SMB</span>
                        <input name="username" type="text" autocomplete="username">
                    </label>
                    <label class="field">
                        <span>Mot de passe SMB</span>
                        <input name="password" type="password" autocomplete="new-password">
                    </label>
                    <label class="field wide">
                        <span>Point de montage local</span>
                        <input name="local_mount_path" type="text" placeholder="Automatique si vide">
                    </label>
                    <label class="check-field">
                        <input name="auto_mount_enabled" type="checkbox" checked>
                        <span>Activer le montage automatique via le service systeme ITops</span>
                    </label>
                </div>
                <div class="modal-tool-output" data-storage-target-kind="local" hidden>
                    <strong>Stockage local serveur</strong>
                    <span>Le stockage local est gere automatiquement par ITops. La creation d'espaces locaux parametrables sera branchee sur une API dediee.</span>
                </div>
                <p id="modal-storage-target-feedback" class="muted inventory-feedback"></p>
                <div class="modal-inline-tools">
                    <button class="toolbar-btn" type="button" data-action="storage-target:cancel">Annuler</button>
                    <button class="primary-btn" type="submit">Declarer l'emplacement</button>
                </div>
            </section>
        </form>
    `;
}

function storageRemoteTreeMarkup() {
    return buildTreeSectionMarkup({
        title: "Montages distants",
        description: "Partages distants declares pour la redondance ou l'acces fichier des services.",
        searchId: "storage-remote-search",
        searchPlaceholder: "Nom, service, chemin, etat",
        searchInTitleRow: true,
        titleActionsMarkup: createIconActionButtonMarkup({
            icon: "add",
            action: "storage-target:add",
            title: "Ajouter un stockage",
        }),
        headId: "storage-remote-head",
        bodyId: "storage-remote-body",
        headMarkup: `
            <tr>
                <th data-storage-remote-col="label">Nom</th>
                <th data-storage-remote-col="service">Service</th>
                <th data-storage-remote-col="remote_path">Source distante</th>
                <th data-storage-remote-col="mount_path">Point local</th>
                <th data-storage-remote-col="status">Etat</th>
                <th>Actions</th>
            </tr>
        `,
        feedbackId: "modal-storage-remote-feedback",
    });
}

function storageLocalTreeMarkup() {
    return buildTreeSectionMarkup({
        title: "Stockage local",
        description: "Fichiers actuellement stockes localement par ITops.",
        searchId: "storage-local-search",
        searchPlaceholder: "Fichier, service, device, sync",
        searchInTitleRow: true,
        titleActionsMarkup: [
            createIconActionButtonMarkup({
                icon: "list",
                action: "storage-explorer:open",
                title: "Explorer le stockage local",
                data: { root_id: "local:linked_files" },
            }),
            createIconActionButtonMarkup({
                icon: "refresh",
                action: "storage-files:refresh",
                title: "Rafraichir",
            }),
        ].join(""),
        headId: "storage-local-head",
        bodyId: "storage-local-body",
        headMarkup: `
            <tr>
                <th data-storage-local-col="name">Fichier</th>
                <th data-storage-local-col="service">Service</th>
                <th data-storage-local-col="detail">Contexte</th>
                <th data-storage-local-col="size">Taille</th>
                <th data-storage-local-col="modified">Modifie</th>
                <th data-storage-local-col="sync">Sync</th>
                <th>Actions</th>
            </tr>
        `,
        feedbackId: "modal-storage-files-feedback",
    });
}

function buildStorageFilesModalMarkup() {
    return `
        ${storageRemoteTreeMarkup()}
        ${storageTargetFormMarkup()}
        ${storageLocalTreeMarkup()}
        ${createModalActionsMarkup({
            buttons: [{ preset: "cancel", label: "Fermer" }],
        })}
    `;
}

async function refreshStorageFilesModal() {
    const filesFeedback = document.getElementById("modal-storage-files-feedback");
    const remoteFeedback = document.getElementById("modal-storage-remote-feedback");
    if (filesFeedback) {
        filesFeedback.textContent = "Chargement...";
    }
    if (remoteFeedback) {
        remoteFeedback.textContent = "Chargement...";
    }
    const [files, mounts, targets] = await Promise.all([
        requestJson("/storage/files?limit=1000"),
        requestJson("/storage/remote-mounts"),
        requestJson("/storage/targets"),
    ]);
    state.storageFiles = Array.isArray(files) ? files : [];
    state.storageMounts = Array.isArray(mounts) ? mounts : [];
    state.storageTargets = Array.isArray(targets) ? targets : [];
    ensureStorageTreeViews();
    renderStorageTreeViews();
    if (filesFeedback) {
        filesFeedback.textContent = `${state.storageFiles.length} fichier(s) localement stocke(s).`;
    }
    if (remoteFeedback) {
        remoteFeedback.textContent = `${state.storageMounts.length} montage(s) distant(s).`;
    }
}

async function openStorageFilesModal() {
    storageRemoteTreeView = null;
    storageLocalTreeView = null;
    openModal("Gestion du stockage", buildStorageFilesModalMarkup(), {
        width: "min(1180px, calc(100vw - 40px))",
    });
    ensureStorageTreeViews();
    await refreshStorageFilesModal();
}

async function submitStorageTargetForm(form) {
    const formData = new window.FormData(form);
    const targetType = String(formData.get("storage_target_type") || "smb3").trim().toLowerCase();
    const serviceCode = String(formData.get("service_code") || "platform.storage").trim();
    const feedback = document.getElementById("modal-storage-target-feedback");
    if (targetType === "local") {
        if (feedback) {
            feedback.textContent = "Le stockage local parametrable n'est pas encore disponible.";
        }
        return;
    }
    if (feedback) {
        feedback.textContent = "Enregistrement en cours...";
    }
    await requestJson("/storage/targets", {
        method: "POST",
        body: JSON.stringify({
            id: String(form.dataset.editTargetId || "").trim(),
            label: String(formData.get("label") || "").trim(),
            service_code: serviceCode,
            service_label: storageServiceLabel(serviceCode),
            kind: "smb3",
            remote_path: String(formData.get("remote_path") || "").trim(),
            username: String(formData.get("username") || "").trim(),
            password: String(formData.get("password") || ""),
            local_mount_path: String(formData.get("local_mount_path") || "").trim(),
            auto_mount_enabled: form.querySelector('[name="auto_mount_enabled"]')?.checked ?? true,
        }),
    });
    resetStorageTargetForm(form);
    await refreshStorageFilesModal();
    const remoteFeedback = document.getElementById("modal-storage-remote-feedback");
    if (remoteFeedback) {
        remoteFeedback.textContent = "Emplacement enregistre.";
    }
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
        <option value="${escapeHtml(String(root?.id || ""))}" ${String(root?.id || "") === currentRootId ? "selected" : ""}>
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
        <section class="modal-section">
            <div class="section-head">
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
                ${createIconActionButtonMarkup({
                    icon: "refresh",
                    action: "storage-explorer:refresh",
                    title: "Rafraichir",
                })}
                ${createActionButtonMarkup({
                    className: "toolbar-btn",
                    type: "button",
                    action: "storage-explorer:up",
                    label: "Remonter",
                    disabled: !String(state.storageExplorer.path || "").trim(),
                })}
                ${createActionButtonMarkup({
                    className: "toolbar-btn",
                    type: "button",
                    action: "storage-explorer:mkdir",
                    label: "Nouveau dossier",
                })}
                ${createActionButtonMarkup({
                    className: "toolbar-btn",
                    type: "button",
                    action: "storage-explorer:upload",
                    label: "Importer",
                })}
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
                    <tbody id="storage-explorer-body">
                        ${renderStorageExplorerRows()}
                    </tbody>
                </table>
            </div>
            <input id="storage-explorer-upload-input" type="file" hidden>
            <p id="storage-explorer-feedback" class="muted inventory-feedback"></p>
        </section>
        ${createModalActionsMarkup({
            buttons: [
                { label: "Retour gestion stockage", type: "button", action: "storage-explorer:back" },
                { preset: "cancel", label: "Fermer" },
            ],
        })}
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
                    <button class="link-btn" type="button" data-action="${isFolder ? "storage-explorer:enter" : "storage-explorer:download"}" data-path="${escapeHtml(path)}">
                        ${escapeHtml(String(item?.name || ""))}
                    </button>
                </td>
                <td>${isFolder ? "Dossier" : "Fichier"}</td>
                <td>${isFolder ? "-" : escapeHtml(formatStorageFileSize(item?.size_bytes))}</td>
                <td>${escapeHtml(formatStorageFileDate(item?.modified_at))}</td>
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

async function loadStorageExplorerRoots(preferredRootId = "") {
    const roots = await requestJson("/storage/explorer/roots");
    state.storageExplorer.roots = Array.isArray(roots) ? roots : [];
    const preferred = String(preferredRootId || "").trim();
    const existing = state.storageExplorer.roots.some((root) => String(root?.id || "") === preferred);
    state.storageExplorer.rootId = existing
        ? preferred
        : String(state.storageExplorer.roots[0]?.id || "");
}

async function refreshStorageExplorer(path = state.storageExplorer.path) {
    const rootId = String(state.storageExplorer.rootId || "").trim();
    if (!rootId) {
        state.storageExplorer.items = [];
        state.storageExplorer.path = "";
        return;
    }
    const params = new URLSearchParams({
        root_id: rootId,
        path: String(path || ""),
    });
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

async function openStorageExplorerModal(rootId = "") {
    await loadStorageExplorerRoots(rootId);
    await refreshStorageExplorer("");
    renderStorageExplorerModal();
}

async function reloadStorageExplorerModal(path = state.storageExplorer.path) {
    await refreshStorageExplorer(path);
    renderStorageExplorerModal();
}

async function downloadStorageExplorerItem(path) {
    const rootId = String(state.storageExplorer.rootId || "").trim();
    const sharedDownload = window.NMPSharedDownload?.downloadBinary;
    if (!rootId || typeof sharedDownload !== "function") {
        throw new Error("Telechargement indisponible.");
    }
    const params = new URLSearchParams({ root_id: rootId, path: String(path || "") });
    await sharedDownload({
        url: `/storage/explorer/download?${params.toString()}`,
        method: "GET",
        headers: { ...headers() },
        defaultFilename: String(path || "fichier").split("/").pop() || "fichier",
        normalizeErrorMessage,
    });
}

async function createStorageExplorerFolder() {
    const name = await showItopsPrompt({
        title: "Nouveau dossier",
        label: "Nom du dossier",
        confirmLabel: "Creer",
    });
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
    if (!path || !(await showItopsConfirm({
        title: "Supprimer",
        message: `Supprimer '${name || path}' ?`,
        confirmLabel: "Supprimer",
        danger: true,
    }))) {
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

function buildDatabaseImportModalMarkup() {
    return `
        <form id="modal-database-import-form" class="modal-form">
            <section class="modal-section">
                <p class="muted">Importe une sauvegarde SQL ITops. Cette action restaure la base generale de l'application.</p>
                <label class="field wide">
                    <span>Fichier SQL</span>
                    <input name="database_backup_file" type="file" accept=".sql,.dump,.txt" required>
                </label>
                <label class="check-field">
                    <input name="database_import_confirm" type="checkbox" required>
                    <span>Je confirme vouloir importer cette sauvegarde dans la base actuelle.</span>
                </label>
                <p id="modal-database-import-feedback" class="muted inventory-feedback"></p>
            </section>
            ${createModalActionsMarkup({
                buttons: [{ preset: "cancel" }, { label: "Importer", type: "submit", className: "danger-btn" }],
            })}
        </form>
    `;
}

function openDatabaseImportModal() {
    openModal("Importer la base de donnees", buildDatabaseImportModalMarkup(), {
        width: "min(680px, calc(100vw - 40px))",
    });
}

async function submitDatabaseImportForm(form) {
    const feedback = document.getElementById("modal-database-import-feedback");
    if (feedback) {
        feedback.textContent = "";
    }
    const fileInput = form.querySelector('input[name="database_backup_file"]');
    const file = fileInput?.files && fileInput.files[0] ? fileInput.files[0] : null;
    if (!file) {
        throw new Error("Selectionne un fichier SQL.");
    }
    const confirmed = form.querySelector('[name="database_import_confirm"]')?.checked ?? false;
    if (!confirmed) {
        throw new Error("Confirmation obligatoire avant import.");
    }
    const readAsBase64 = window.NMPSharedImport?.readAsBase64;
    if (typeof readAsBase64 !== "function") {
        throw new Error("Module d'import indisponible.");
    }
    if (feedback) {
        feedback.textContent = "Lecture du fichier...";
    }
    const contentBase64 = String(await readAsBase64(file));
    if (feedback) {
        feedback.textContent = "Import de la base...";
    }
    const response = await requestJson("/admin/database/import", {
        method: "POST",
        body: JSON.stringify({
            filename: String(file.name || "backup.sql"),
            content_base64: contentBase64,
            confirm_replace: true,
        }),
    });
    if (feedback) {
        feedback.textContent = response?.message || "Base importee.";
    }
}

function extractServiceCodeFromRoutePath(routePath) {
    const raw = String(routePath || "").trim();
    if (!raw) {
        return "";
    }
    const normalized = raw.startsWith("/") ? raw.slice(1) : raw;
    if (!normalized.startsWith("#service=")) {
        return "";
    }
    try {
        return normalizeNoCodeText(window.decodeURIComponent(normalized.slice("#service=".length))).toLowerCase();
    } catch (_error) {
        return "";
    }
}

function extractDirectoryKindFromRoutePath(routePath) {
    const raw = String(routePath || "").trim();
    if (!raw) {
        return "";
    }
    const normalized = raw.startsWith("/") ? raw.slice(1) : raw;
    if (!normalized.startsWith("#directory=")) {
        return "";
    }
    try {
        const kind = normalizeNoCodeText(window.decodeURIComponent(normalized.slice("#directory=".length))).toLowerCase();
        return kind === "services" ? "services" : (kind === "agents" ? "agents" : "");
    } catch (_error) {
        return "";
    }
}

function buildDirectoryModuleMarkup(kind, rows) {
    const normalizedKind = String(kind || "").trim().toLowerCase();
    const items = Array.isArray(rows) ? rows : [];
    const isAgents = normalizedKind === "agents";
    const statusFilter = String(state.directoryContext?.statusFilter || (isAgents ? "Actif" : "")).trim();
    const directoryFiltersMarkup = isAgents
        ? `
            <section class="shared-treeview-filter-section no-code-quick-filters">
                <div class="content-filter-grid no-code-quick-filter-grid">
                    <label class="field no-code-quick-filter-field">
                        <span>Statut</span>
                        <select id="directory-status-filter">
                            <option value="">Tous</option>
                            <option value="Actif" ${statusFilter.toLowerCase() === "actif" ? "selected" : ""}>Actif</option>
                            <option value="Desactive" ${statusFilter.toLowerCase() === "desactive" ? "selected" : ""}>Desactive</option>
                        </select>
                    </label>
                </div>
            </section>
        `
        : "";
    return buildTreeSectionMarkup({
        title: isAgents ? "Base agents" : "Base services",
        description: isAgents
            ? "Annuaire metier synchronise depuis Active Directory."
            : "OU AD synchronisees depuis Active Directory.",
        titleActionsMarkup: `
            <span class="meta-badge">${Number(items.length || 0)} element(s)</span>
            ${isAgents ? createActionButtonMarkup({
                icon: "link",
                action: "directory:batch:relation-assign",
                label: "Assigner element lie",
                id: "directory-batch-relation-assign",
                disabled: true,
            }) : ""}
        `,
        searchId: "directory-search",
        searchPlaceholder: isAgents ? "Identite, identifiant, mail, email lie, service lie" : "Service, code, description, responsable",
        headId: "directory-head",
        bodyId: "directory-body",
        headMarkup: "",
        filtersMarkup: directoryFiltersMarkup,
        feedbackId: "directory-feedback",
        footerActionsMarkup: '<p class="muted inventory-feedback">Ces entites servent de socle aux relations avec les services dynamiques.</p>',
    });
}

async function openServiceModuleFromPortal(serviceCode) {
    const normalizedCode = normalizeNoCodeText(serviceCode).toLowerCase();
    if (!normalizedCode) {
        throw new Error("Service introuvable.");
    }
    clearModalBackStack();
    await loadAdministrationData({
        includeModules: false,
        includeRoles: false,
        includeUsers: false,
        includeServices: true,
        includeSharedLists: false,
    });
    const service = findNoCodeService(normalizedCode);
    setActiveModuleMenuContext({
        kind: "service",
        code: normalizedCode,
        serviceCode: normalizedCode,
        label: String(service?.label || normalizedCode).trim() || normalizedCode,
    });
    try {
        await openNoCodeServiceRecords(normalizedCode, { inline: true });
    } catch (error) {
        setActiveModuleMenuContext();
        throw error;
    }
}

async function openDirectoryModuleFromPortal(kind) {
    const normalizedKind = String(kind || "").trim().toLowerCase();
    if (!["agents", "services"].includes(normalizedKind)) {
        throw new Error("Annuaire introuvable.");
    }
    clearModalBackStack();
    const title = normalizedKind === "agents" ? "Agents" : "Services";
    state.directoryContext = {
        kind: normalizedKind,
        rows: [],
        relations: [],
        selectedRecordKeys: [],
        statusFilter: normalizedKind === "agents" ? "Actif" : "",
    };
    state.directoryRecordEditor = null;
    state.noCodeRecordEditor = null;
    state.directorySort = { column: "label", direction: "asc" };
    directoryTreeView = null;
    setActiveModuleMenuContext({
        kind: "directory",
        code: `directory_${normalizedKind}`,
        directoryKind: normalizedKind,
        label: title,
    });
    openModal(
        title,
        buildDirectoryModuleMarkup(normalizedKind, []),
        noCodeInlineOptions("min(1180px, calc(100vw - 40px))", { inline: true }),
    );
    renderDirectoryTreeView();
    try {
        const nextContext = await fetchDirectoryContext(normalizedKind, {
            statusFilter: normalizedKind === "agents" ? "Actif" : "",
            selectedRecordKeys: [],
        });
        state.directoryContext = nextContext;
        state.directoryRecordEditor = null;
        state.noCodeRecordEditor = null;
        state.directorySort = { column: "label", direction: "asc" };
        directoryTreeView = null;
        renderDirectoryTreeView();
    } catch (error) {
        throw error;
    }
}

async function openServiceEditorFromPortal(serviceCode) {
    const normalizedCode = normalizeNoCodeText(serviceCode).toLowerCase();
    if (!normalizedCode || normalizedCode === "monitoring") {
        throw new Error("Service introuvable.");
    }
    await loadAdministrationData({
        includeModules: false,
        includeRoles: false,
        includeUsers: false,
        includeServices: true,
        includeSharedLists: true,
    });
    const service = findNoCodeService(normalizedCode);
    if (!service) {
        throw new Error("Service introuvable.");
    }
    if (isSystemNoCodeService(service)) {
        throw new Error("Module socle protege: la definition n'est pas modifiable.");
    }
    await openNoCodeServiceEditor(service, { inline: true, context: { source: "standalone" } });
}

function normalizeMonitoringSummary(summary) {
    if (!summary || typeof summary !== "object") {
        return null;
    }
    return {
        running_any: Boolean(summary.running_any),
        running_all: Boolean(summary.running_all),
        total: Math.max(0, Number(summary.total || 0)),
        online: Math.max(0, Number(summary.online || 0)),
        offline: Math.max(0, Number(summary.offline || 0)),
        types: Array.isArray(summary.types) ? summary.types : [],
    };
}

function monitoringSummarySignature(summary = state.monitoringSummary) {
    if (!summary || typeof summary !== "object") {
        return "";
    }
    return JSON.stringify({
        running_any: Boolean(summary.running_any),
        running_all: Boolean(summary.running_all),
        total: Number(summary.total || 0),
        online: Number(summary.online || 0),
        offline: Number(summary.offline || 0),
        types: (Array.isArray(summary.types) ? summary.types : []).map((row) => ({
            type_code: String(row?.type_code || ""),
            label: String(row?.label || ""),
            running: Boolean(row?.running),
            total: Number(row?.total || 0),
            online: Number(row?.online || 0),
            offline: Number(row?.offline || 0),
        })),
    });
}

async function loadPortalMonitoringSummary(options = {}) {
    const forceRefresh = Boolean(options.forceRefresh);
    if (!forceRefresh && state.monitoringSummaryLoaded) {
        return state.monitoringSummary;
    }
    try {
        const snapshot = await requestJson("/monitoring/snapshot");
        state.monitoringSummary = normalizeMonitoringSummary({
            ...(snapshot?.summary || {}),
            types: Array.isArray(snapshot?.types) ? snapshot.types : [],
        });
        state.monitoringSummarySignature = monitoringSummarySignature(state.monitoringSummary);
    } catch (_error) {
        state.monitoringSummary = null;
        state.monitoringSummarySignature = "";
    } finally {
        state.monitoringSummaryLoaded = true;
    }
    return state.monitoringSummary;
}

function portalMonitoringModuleVisible() {
    return (Array.isArray(state.portalModules) ? state.portalModules : []).some((row) => {
        return isMonitoringPortalModule(row)
            && Boolean(row?.granted)
            && Boolean(row?.is_active)
            && Boolean(portalModuleRoutePath(row));
    });
}

async function reloadPortalMonitoringSummaryForTile() {
    const previousSignature = state.monitoringSummarySignature;
    await loadPortalMonitoringSummary({ forceRefresh: true });
    if (state.monitoringSummarySignature !== previousSignature && Array.isArray(state.moduleAccess)) {
        renderModuleCards(state.moduleAccess);
    }
}

function applyPortalMonitoringSnapshot(snapshot) {
    const previousSignature = state.monitoringSummarySignature;
    state.monitoringSummary = normalizeMonitoringSummary({
        ...(snapshot?.summary || {}),
        types: Array.isArray(snapshot?.types) ? snapshot.types : [],
    });
    state.monitoringSummaryLoaded = true;
    state.monitoringSummarySignature = monitoringSummarySignature(state.monitoringSummary);
    if (state.monitoringSummarySignature !== previousSignature && Array.isArray(state.moduleAccess)) {
        renderModuleCards(state.moduleAccess);
    }
}

function startPortalMonitoringSummaryRefresh() {
    if (!state.token || document.hidden || !portalMonitoringModuleVisible()) {
        return;
    }
    if (state.monitoringSummaryWebSocket instanceof WebSocket || !("WebSocket" in window)) {
        return;
    }
    try {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const url = `${protocol}//${window.location.host}/monitoring/ws?token=${encodeURIComponent(state.token)}&interval_ms=1000`;
        const websocket = new WebSocket(url);
        state.monitoringSummaryWebSocket = websocket;
        websocket.addEventListener("message", (event) => {
            try {
                const payload = JSON.parse(event.data);
                if (payload?.event === "monitoring.snapshot") {
                    applyPortalMonitoringSnapshot(payload.data);
                }
            } catch (_error) {
            }
        });
        websocket.addEventListener("close", () => {
            if (state.monitoringSummaryWebSocket === websocket) {
                state.monitoringSummaryWebSocket = null;
            }
        });
        websocket.addEventListener("error", () => {
            try {
                websocket.close();
            } catch (_error) {
            }
        });
    } catch (_error) {
        state.monitoringSummaryWebSocket = null;
    }
}

function stopPortalMonitoringSummaryRefresh() {
    if (state.monitoringSummaryWebSocket) {
        try {
            state.monitoringSummaryWebSocket.close();
        } catch (_error) {
        }
        state.monitoringSummaryWebSocket = null;
    }
}

function findPortalModuleByCode(moduleCode) {
    const normalized = String(moduleCode || "").trim().toLowerCase();
    if (!normalized) {
        return null;
    }
    const rows = Array.isArray(state.portalModules) ? state.portalModules : [];
    return rows.find((row) => String(row?.code || "").trim().toLowerCase() === normalized)
        || (normalized === "monitoring" ? rows.find((row) => isMonitoringPortalModule(row)) : null)
        || null;
}

function isMonitoringPortalModule(moduleRow) {
    if (!moduleRow || typeof moduleRow !== "object") {
        return false;
    }
    const code = String(moduleRow.code || "").trim().toLowerCase();
    const routePath = String(moduleRow.route_path || "").trim().toLowerCase();
    const label = String(moduleRow.label || "").trim().toLowerCase();
    return code === "monitoring" || routePath === "/monitoring" || label === "monitoring" || label === "monitoring reseau";
}

function portalModuleRoutePath(moduleRow) {
    if (isMonitoringPortalModule(moduleRow)) {
        return "/monitoring";
    }
    return String(moduleRow?.route_path || "").trim();
}

function buildModuleBlockedReason(moduleRow) {
    const granted = Boolean(moduleRow?.granted);
    return granted
        ? "Module indisponible pour le moment."
        : "Vous n'avez pas les droits sur ce module.";
}

async function openPortalModuleCard(moduleRow) {
    if (!moduleRow || typeof moduleRow !== "object") {
        return;
    }
    const isActive = Boolean(moduleRow.is_active);
    const granted = Boolean(moduleRow.granted);
    if (isMonitoringPortalModule(moduleRow)) {
        if (!isActive || !granted) {
            openModal("Module non disponible", `<p class="muted">${escapeHtml(buildModuleBlockedReason(moduleRow))}</p>`);
            return;
        }
        persistToken(state.token || window.localStorage.getItem("nmp_token") || "");
        window.location.assign(portalModuleRoutePath(moduleRow));
        return;
    }
    const routePath = portalModuleRoutePath(moduleRow);
    const serviceCode = extractServiceCodeFromRoutePath(routePath);
    const directoryKind = extractDirectoryKindFromRoutePath(routePath);
    const canOpen = Boolean(isActive && granted && routePath);
    if (!canOpen) {
        openModal("Module non disponible", `<p class="muted">${escapeHtml(buildModuleBlockedReason(moduleRow))}</p>`);
        return;
    }
    if (directoryKind) {
        await openDirectoryModuleFromPortal(directoryKind);
        return;
    }
    if (serviceCode) {
        await openServiceModuleFromPortal(serviceCode);
        return;
    }
    window.location.assign(routePath);
}

async function setCustomServiceActiveFromPortal(serviceCode, isActive) {
    const normalizedCode = normalizeNoCodeText(serviceCode).toLowerCase();
    if (!normalizedCode) {
        throw new Error("Service introuvable.");
    }
    await loadAdministrationData({
        includeModules: false,
        includeRoles: false,
        includeUsers: false,
        includeServices: true,
        includeSharedLists: false,
    });
    const service = findNoCodeService(normalizedCode);
    if (!service) {
        throw new Error("Service introuvable.");
    }
    const payload = {
        code: normalizedCode,
        label: String(service.label || "").trim(),
        is_active: Boolean(isActive),
        is_technical: Boolean(service.is_technical),
        credentials_enabled: Boolean(service.credentials_enabled),
        child_enabled: Boolean(service.child_enabled),
        child_label: String(service.child_label || "Elements lies").trim() || "Elements lies",
        sort_order: Number(service.sort_order || 100),
        version_token: String(service.version_token || ""),
        fields: noCodeCustomServiceFields(service),
    };
    await requestJson(`/admin/custom-services/${encodeURIComponent(normalizedCode)}`, {
        method: "PUT",
        body: JSON.stringify(payload),
    });
}

async function setPortalModuleActivation(moduleRow, nextActive) {
    const code = String(moduleRow?.code || "").trim().toLowerCase();
    const routePath = String(moduleRow?.route_path || "").trim();
    if (!code) {
        throw new Error("Module introuvable.");
    }
    const serviceCode = extractServiceCodeFromRoutePath(routePath);
    if (serviceCode) {
        await setCustomServiceActiveFromPortal(serviceCode, Boolean(nextActive));
    } else {
        await requestJson(`/admin/modules/${encodeURIComponent(code)}/activation`, {
            method: "PUT",
            body: JSON.stringify({ is_active: Boolean(nextActive) }),
        });
    }
    state.moduleAccessLoaded = false;
    invalidateAdminData(["services", "modules"]);
    await loadPortalModules({ forceRefresh: true });
}

function monitoringRuntimeStatusMeta(moduleRow) {
    if (!isMonitoringPortalModule(moduleRow)) {
        return null;
    }
    if (!Boolean(moduleRow?.is_active)) {
        return { className: "stat-offline", label: "Arrete" };
    }
    const running = Boolean(state.monitoringSummary && state.monitoringSummary.running_any);
    return {
        className: running ? "stat-online" : "stat-offline",
        label: running ? "En cours" : "Arrete",
    };
}

function createPortalContextMenuButton({ label, action = "", hint = "", disabled = false }) {
    return `
        <button class="context-menu-item" type="button" data-action="${escapeHtml(action)}" ${disabled ? "disabled" : ""}>
            <span>${escapeHtml(label)}</span>
            <span class="context-menu-hint">${escapeHtml(hint)}</span>
        </button>
    `;
}

function buildPortalCardsContextMenuMarkup(moduleRow) {
    const isMonitoring = isMonitoringPortalModule(moduleRow);
    const routePath = portalModuleRoutePath(moduleRow);
    const serviceCode = extractServiceCodeFromRoutePath(routePath);
    const directoryKind = extractDirectoryKindFromRoutePath(routePath);
    const isActive = Boolean(moduleRow?.is_active);
    const granted = Boolean(moduleRow?.granted);
    const canOpen = Boolean(isActive && granted && routePath);
    const service = serviceCode ? findNoCodeService(serviceCode) : null;
    const canEditDynamicService = Boolean(serviceCode) && serviceCode !== "monitoring" && !isSystemNoCodeService(service || serviceCode);
    const monitoringMeta = monitoringRuntimeStatusMeta(moduleRow);
    const monitoringControlDisabled = !Boolean(isActive && granted);
    const serviceItems = [
        `<div class="context-menu-label">${directoryKind ? "Annuaire" : "Service"}</div>`,
        createPortalContextMenuButton({
            label: "Ouvrir",
            action: "portal-card:open",
            hint: canOpen ? "" : "Indisponible",
            disabled: !canOpen,
        }),
        ...(canEditDynamicService
            ? [createPortalContextMenuButton({
                label: "Modifier",
                action: "portal-card:service-edit",
                hint: "",
                disabled: false,
            })]
            : []),
        createPortalContextMenuButton({
            label: isActive ? "Desactiver" : "Activer",
            action: "portal-card:toggle-service",
            hint: "",
            disabled: false,
        }),
    ];
    const items = [...serviceItems];
    if (isMonitoring) {
        items.push('<div class="context-menu-sep"></div>');
        items.push('<div class="context-menu-label">Monitoring</div>');
        items.push(
            createPortalContextMenuButton({
                label: "Status monitoring",
                action: "portal-card:monitoring-status",
                hint: monitoringMeta ? monitoringMeta.label : "Arrete",
                disabled: true,
            }),
        );
        items.push(
            createPortalContextMenuButton({
                label: Boolean(state.monitoringSummary?.running_any) ? "Arreter le monitoring global" : "Activer le monitoring global",
                action: "portal-card:toggle-monitoring-global",
                hint: monitoringControlDisabled ? "Indisponible" : "",
                disabled: monitoringControlDisabled,
            }),
        );
    }
    return `<div class="context-menu-group">${items.join("")}</div>`;
}

function openPortalCardsContextMenu(x, y, moduleRow) {
    if (!(cardsContextMenu instanceof HTMLElement)) {
        return;
    }
    state.portalContextModuleCode = String(moduleRow?.code || "").trim().toLowerCase();
    cardsContextMenu.innerHTML = buildPortalCardsContextMenuMarkup(moduleRow);
    cardsContextMenu.hidden = false;
    const maxX = window.innerWidth - cardsContextMenu.offsetWidth - 12;
    const maxY = window.innerHeight - cardsContextMenu.offsetHeight - 12;
    cardsContextMenu.style.left = `${Math.max(8, Math.min(x, maxX))}px`;
    cardsContextMenu.style.top = `${Math.max(8, Math.min(y, maxY))}px`;
}

function buildNoCodeRelationNodeContextMenuMarkup(serviceCode) {
    const service = findNoCodeRelationEntity(serviceCode) || { label: serviceCode };
    return `
        <div class="context-menu-group">
            <div class="context-menu-label">${escapeHtml(String(service.label || serviceCode))}</div>
            <button class="context-menu-item danger" type="button" data-action="service:relation-node:delete">
                <span>Supprimer</span>
                <span class="context-menu-hint">Retirer du canvas</span>
            </button>
        </div>
    `;
}

function openNoCodeRelationNodeContextMenu(x, y, serviceCode) {
    if (!(cardsContextMenu instanceof HTMLElement)) {
        return;
    }
    closeCardsContextMenu();
    state.noCodeRelationContextNodeCode = String(serviceCode || "").trim().toLowerCase();
    cardsContextMenu.innerHTML = buildNoCodeRelationNodeContextMenuMarkup(state.noCodeRelationContextNodeCode);
    cardsContextMenu.hidden = false;
    const maxX = window.innerWidth - cardsContextMenu.offsetWidth - 12;
    const maxY = window.innerHeight - cardsContextMenu.offsetHeight - 12;
    cardsContextMenu.style.left = `${Math.max(8, Math.min(x, maxX))}px`;
    cardsContextMenu.style.top = `${Math.max(8, Math.min(y, maxY))}px`;
}

async function deleteNoCodeRelationContextNode() {
    const editor = state.noCodeServiceEditor;
    const serviceCode = String(state.noCodeRelationContextNodeCode || "").trim().toLowerCase();
    if (!editor || !serviceCode || serviceCode === noCodeRelationCurrentServiceCode(editor)) {
        return;
    }
    const service = findNoCodeRelationEntity(serviceCode) || { label: serviceCode };
    const relatedCount = noCodeRelationDrafts(editor).filter((relation) => {
        const sourceCode = String(relation?.source_service_code || "").trim().toLowerCase();
        const targetCode = normalizeNoCodeRelationEntityCode(relation?.target_service_code || relation?.service_code || "");
        return sourceCode === serviceCode || targetCode === serviceCode;
    }).length;
    const confirmed = await showItopsConfirm({
        title: "Retirer du canvas",
        message: `Retirer '${String(service.label || serviceCode)}' du canvas de relations ?`,
        details: relatedCount
            ? [`${relatedCount} relation(s) liee(s) a cette table seront aussi retiree(s) du schema.`]
            : ["Aucune relation liee ne sera supprimee."],
        confirmLabel: "Retirer",
        cancelLabel: "Annuler",
        danger: true,
    });
    if (!confirmed) {
        return;
    }
    removeNoCodeRelationCanvasNode(editor, serviceCode);
    renderNoCodeServiceEditorShell();
}

async function handleModuleCardsClick(event) {
    if (ensurePortalDashboardEditor().isEditing()) {
        return;
    }
    const target = event.target;
    if (!(target instanceof Element)) {
        return;
    }
    const visualAction = target.closest("[data-card-visual-action]");
    if (visualAction instanceof HTMLButtonElement) {
        event.preventDefault();
        event.stopPropagation();
        if (visualAction.disabled) {
            return;
        }
        const card = visualAction.closest("[data-module-code]");
        const moduleCode = String(card instanceof HTMLElement ? card.dataset.moduleCode || "" : "").trim().toLowerCase();
        const moduleRow = findPortalModuleByCode(moduleCode);
        try {
            await handlePortalCardsContextMenuAction(String(visualAction.dataset.action || ""), moduleRow);
        } catch (error) {
            openModal("Action indisponible", `<p class="muted">${escapeHtml(normalizeErrorMessage(error.message))}</p>`);
        }
        return;
    }
    const card = target.closest("[data-module-code]");
    if (!(card instanceof HTMLElement)) {
        return;
    }
    const moduleCode = String(card.dataset.moduleCode || "").trim().toLowerCase();
    const moduleRow = findPortalModuleByCode(moduleCode);
    if (!moduleRow) {
        return;
    }
    try {
        await openPortalModuleCard(moduleRow);
    } catch (error) {
        openModal("Module non disponible", `<p class="muted">${escapeHtml(normalizeErrorMessage(error.message))}</p>`);
    }
}

async function handlePortalCardsContextMenuAction(action, moduleRow) {
    const normalizedAction = String(action || "").trim().toLowerCase();
    if (!normalizedAction || !moduleRow) {
        return;
    }
    if (normalizedAction === "portal-card:open") {
        await openPortalModuleCard(moduleRow);
        return;
    }
    if (normalizedAction === "portal-card:service-edit") {
        const routePath = portalModuleRoutePath(moduleRow);
        const serviceCode = extractServiceCodeFromRoutePath(routePath);
        await openServiceEditorFromPortal(serviceCode);
        return;
    }
    if (normalizedAction === "portal-card:toggle-service") {
        await setPortalModuleActivation(moduleRow, !Boolean(moduleRow.is_active));
        return;
    }
    if (normalizedAction === "portal-card:toggle-monitoring-global") {
        const running = Boolean(state.monitoringSummary && state.monitoringSummary.running_any);
        await requestJson(running ? "/monitoring/stop-all" : "/monitoring/start-all", {
            method: "POST",
        });
        state.monitoringSummaryLoaded = false;
        await loadPortalMonitoringSummary({ forceRefresh: true });
        renderModuleCards(state.moduleAccess);
        startPortalMonitoringSummaryRefresh();
        return;
    }
}

function scheduleMonitoringPrewarm(rows) {
    if (state.monitoringPrewarmStarted) {
        return;
    }
    const monitoringModule = (Array.isArray(rows) ? rows : []).find((row) => {
        const routePath = portalModuleRoutePath(row);
        return isMonitoringPortalModule(row) && Boolean(row?.granted) && Boolean(row?.is_active) && Boolean(routePath);
    });
    if (!monitoringModule) {
        return;
    }
    state.monitoringPrewarmStarted = true;
    const routePath = portalModuleRoutePath(monitoringModule);
    const urls = [
        routePath,
        "/web/app.js",
        "/web/app.css",
        "/web/shared_menu.js",
        "/web/shared_api.js",
        "/web/shared_auth.js",
        "/web/shared_ui.js",
        "/web/shared_import.js",
        "/web/shared_download.js",
        "/web/shared_admin_ui.js",
        "/web/shared_admin_store.js",
        "/web/shared_admin_controller.js",
    ];
    const run = () => {
        urls.forEach((url) => {
            fetch(url, { method: "GET", credentials: "same-origin" }).catch(() => {
            });
        });
    };
    if (typeof window.requestIdleCallback === "function") {
        window.requestIdleCallback(run, { timeout: 1200 });
        return;
    }
    window.setTimeout(run, 180);
}

function moduleStatusMeta(moduleRow) {
    const isActive = Boolean(moduleRow.is_active);
    const granted = Boolean(moduleRow.granted);
    const hasRoute = Boolean(String(moduleRow.route_path || "").trim());
    const canOpen = Boolean(isActive && granted && hasRoute);
    if (canOpen) {
        return { badgeClass: "stat-online", text: "Actif", ghost: false };
    }
    if (!isActive) {
        return { badgeClass: "stat-ghost", text: "Desactive", ghost: true };
    }
    if (!granted) {
        return { badgeClass: "stat-offline", text: "Acces refuse", ghost: false };
    }
    return { badgeClass: "stat-offline", text: "Indisponible", ghost: false };
}

function formatModuleLastSync(value) {
    const raw = String(value || "").trim();
    if (!raw) {
        return "";
    }
    const normalized = raw.includes("T") ? raw : raw.replace(" ", "T");
    const date = new Date(normalized);
    if (!Number.isFinite(date.getTime())) {
        return raw;
    }
    return date.toLocaleString("fr-FR", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function serviceIconDefinition(iconCode) {
    const normalized = String(iconCode || "").trim().toLowerCase();
    return SERVICE_ICON_LIBRARY.find((item) => item.code === normalized) || SERVICE_ICON_LIBRARY[0];
}

function renderServiceIconSvg(iconCode) {
    const icon = serviceIconDefinition(iconCode);
    if (!icon?.code || !icon.svg) {
        return "";
    }
    return `<svg viewBox="0 0 96 96" role="img" aria-hidden="true">${icon.svg}</svg>`;
}

function sanitizeServiceIconColor(value) {
    const raw = String(value || "").trim();
    if (/^#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?$/.test(raw)) {
        return raw;
    }
    if (/^var\(--[a-zA-Z0-9_-]+\)$/.test(raw)) {
        return raw;
    }
    return "";
}

function renderSystemModuleCardVisual(code, status = {}, options = {}) {
    const normalizedCode = String(code || "").trim().toLowerCase();
    const isGhost = Boolean(status?.ghost);
    if (normalizedCode === "monitoring") {
        const running = Boolean(state.monitoringSummary?.running_any);
        const runningAll = Boolean(state.monitoringSummary?.running_all);
        const stateClass = runningAll ? "is-running" : (running ? "is-partial" : "is-stopped");
        const label = running ? "Arreter le monitoring global" : "Activer le monitoring global";
        const disabled = !Boolean(options.canControl);
        return `
            <button class="dash-card-visual dash-card-visual-monitor ${stateClass}" type="button"
                data-action="portal-card:toggle-monitoring-global"
                data-card-visual-action="monitoring-global"
                aria-label="${escapeHtml(label)}"
                title="${escapeHtml(label)}"
                ${disabled ? "disabled" : ""}>
                <div class="dash-monitor-screen">
                    <span class="dash-monitor-line">
                        <svg viewBox="0 0 148 32" focusable="false">
                            ${stateClass === "is-stopped"
                                ? "<polyline points=\"0,18 148,18\"></polyline>"
                                : "<polyline points=\"0,18 22,18 30,5 40,28 50,18 72,18 80,10 90,18 112,18 120,2 132,18 148,18\"></polyline>"}
                        </svg>
                    </span>
                </div>
            </button>
        `;
    }
    const icons = {
        service_emails: `
            <svg viewBox="0 0 96 96" role="img" aria-hidden="true">
                <rect x="16" y="26" width="64" height="44" rx="8"></rect>
                <path d="M20 32l28 23 28-23"></path>
                <path d="M21 67l22-19"></path>
                <path d="M75 67L53 48"></path>
            </svg>
        `,
        directory_agents: `
            <svg viewBox="0 0 96 96" role="img" aria-hidden="true">
                <circle cx="48" cy="33" r="15"></circle>
                <path d="M23 75c4-16 14-25 25-25s21 9 25 25"></path>
            </svg>
        `,
        directory_services: `
            <svg viewBox="0 0 96 96" role="img" aria-hidden="true">
                <rect x="34" y="16" width="28" height="18" rx="4"></rect>
                <rect x="12" y="62" width="26" height="18" rx="4"></rect>
                <rect x="58" y="62" width="26" height="18" rx="4"></rect>
                <path d="M48 34v14"></path>
                <path d="M25 62V48h46v14"></path>
            </svg>
        `,
    };
    const icon = icons[normalizedCode] || "";
    if (!icon) {
        return "";
    }
    return `
        <div class="dash-card-visual ${isGhost ? "is-muted" : ""}" aria-hidden="true">
            ${icon}
        </div>
    `;
}

function monitoringTypeMetricRows(types = []) {
    const source = Array.isArray(types) ? types : [];
    const wanted = [
        { key: "switch", fallbackLabel: "Switch" },
        { key: "server", fallbackLabel: "Serveur" },
    ];
    const rows = wanted
        .map((wantedRow) => {
            const row = source.find((item) => {
                const code = String(item?.type_code || "").trim().toLowerCase();
                const label = String(item?.label || "").trim().toLowerCase();
                return code === wantedRow.key || label === wantedRow.key || (wantedRow.key === "server" && label === "serveur");
            });
            if (!row) {
                return null;
            }
            return {
                label: String(row.label || wantedRow.fallbackLabel).trim() || wantedRow.fallbackLabel,
                online: Math.max(0, Number(row.online || 0)),
                total: Math.max(0, Number(row.total || 0)),
            };
        })
        .filter(Boolean);
    if (rows.length) {
        return rows;
    }
    return source.slice(0, 2).map((row) => ({
        label: String(row?.label || row?.type_code || "Type").trim() || "Type",
        online: Math.max(0, Number(row?.online || 0)),
        total: Math.max(0, Number(row?.total || 0)),
    }));
}

function portalMonitoringMetricsMarkup() {
    const rows = monitoringTypeMetricRows(state.monitoringSummary?.types || []);
    if (!rows.length) {
        return "";
    }
    return `
        <div class="portal-monitoring-metrics" aria-label="Devices en ligne">
            ${rows.map((row) => `
                <span class="monitoring-type-metric-row">
                    <span>${escapeHtml(row.label)}</span>
                    <strong>${escapeHtml(`${row.online}/${row.total}`)}</strong>
                </span>
            `).join("")}
        </div>
    `;
}

function customServiceCodeFromModule(moduleRow, serviceCode = "") {
    const explicitCode = normalizeNoCodeText(serviceCode).toLowerCase();
    if (explicitCode) {
        return explicitCode;
    }
    const routeCode = extractServiceCodeFromRoutePath(portalModuleRoutePath(moduleRow));
    if (routeCode) {
        return routeCode;
    }
    const code = String(moduleRow?.code || "").trim().toLowerCase();
    return code.startsWith("service_") ? normalizeNoCodeText(code.slice("service_".length)).toLowerCase() : "";
}

function renderCustomModuleCardVisual(moduleRow, serviceCode = "") {
    const resolvedServiceCode = customServiceCodeFromModule(moduleRow, serviceCode);
    const fallbackService = resolvedServiceCode ? findNoCodeService(resolvedServiceCode) : null;
    const iconCode = String(moduleRow?.icon || fallbackService?.icon || "").trim().toLowerCase();
    const icon = renderServiceIconSvg(iconCode);
    if (!icon) {
        return "";
    }
    const color = sanitizeServiceIconColor(moduleRow?.color || fallbackService?.color || "");
    const style = color ? ` style="--service-card-icon-color: ${escapeHtml(color)}"` : "";
    return `<div class="dash-card-visual dash-card-visual-custom"${style} aria-hidden="true">${icon}</div>`;
}

function moduleTileCountLabel(moduleRow, serviceCode = "") {
    const code = String(moduleRow?.code || "").trim().toLowerCase();
    if (code === "monitoring") {
        return "";
    }
    const isSystemCounter = ["directory_agents", "directory_services", "service_emails"].includes(code);
    if (!isSystemCounter && moduleRow?.tile_config?.show_count === false) {
        return "";
    }
    const count = Number(moduleRow?.item_count || 0);
    if (!Number.isFinite(count)) {
        return "";
    }
    if (code === "directory_agents") {
        return `${count} agent${count > 1 ? "s" : ""}`;
    }
    if (code === "directory_services") {
        return `${count} service${count > 1 ? "s" : ""}`;
    }
    if (code === "service_emails" || String(serviceCode || "").trim().toLowerCase() === "emails") {
        return `${count} email${count > 1 ? "s" : ""}`;
    }
    const customLabel = customServiceTileEntityLabel(moduleRow, serviceCode, count);
    return `${count} ${customLabel}`;
}

function customServiceTileEntityLabel(moduleRow, serviceCode = "", count = 0) {
    const rawLabel = String(moduleRow?.label || serviceCode || "element").trim();
    let label = rawLabel.toLowerCase();
    if (!label) {
        label = "element";
    }
    if (Number(count) === 1) {
        return label.replace(/[sx]$/i, "") || label;
    }
    return /[sx]$/i.test(label) ? label : `${label}s`;
}

function updatePortalSyncBadge(rows = state.moduleAccess) {
    const badge = document.getElementById("portal-sync-badge");
    const dateNode = document.getElementById("portal-sync-date");
    if (!(badge instanceof HTMLElement) || !(dateNode instanceof HTMLElement)) {
        return;
    }
    const timestamps = (Array.isArray(rows) ? rows : [])
        .map((row) => String(row?.last_sync_at || "").trim())
        .filter(Boolean)
        .map((raw) => {
            const normalized = raw.includes("T") ? raw : raw.replace(" ", "T");
            const date = new Date(normalized);
            return Number.isFinite(date.getTime()) ? { raw, time: date.getTime() } : { raw, time: 0 };
        })
        .sort((left, right) => right.time - left.time);
    const latest = timestamps[0] || null;
    if (!latest) {
        badge.hidden = true;
        return;
    }
    dateNode.textContent = formatModuleLastSync(latest.raw) || latest.raw;
    badge.hidden = false;
}

function renderModuleCard(moduleRow) {
    const code = String(moduleRow.code || "").trim().toLowerCase();
    const routePath = portalModuleRoutePath(moduleRow);
    const serviceCode = extractServiceCodeFromRoutePath(routePath);
    const isActive = Boolean(moduleRow.is_active);
    const granted = Boolean(moduleRow.granted);
    const canOpen = Boolean(isActive && granted && routePath);
    const known = MODULE_META[code] || {};
    const status = moduleStatusMeta({ is_active: isActive, granted, route_path: routePath });
    const title = String(moduleRow.label || known.title || code || "Module");
    const subtitle = String(known.subtitle || (serviceCode ? "Service personnalise" : "Module de service IT"));
    const systemVisualMarkup = renderSystemModuleCardVisual(code, status, {
        canControl: isMonitoringPortalModule(moduleRow) && canOpen,
    });
    const customVisualMarkup = systemVisualMarkup ? "" : renderCustomModuleCardVisual(moduleRow, serviceCode);
    const visualMarkup = systemVisualMarkup || customVisualMarkup;
    const countLabel = moduleTileCountLabel(moduleRow, serviceCode);
    const monitoringMetrics = isMonitoringPortalModule(moduleRow) ? portalMonitoringMetricsMarkup() : "";

    return `
        <article class="dash-card panel ${canOpen ? "clickable" : ""} ${status.ghost ? "module-ghost" : ""} ${visualMarkup ? "system-module-card" : ""}" data-module-code="${escapeHtml(code)}" data-dashboard-card-id="${escapeHtml(code)}" data-dashboard-card-active="${isActive ? "true" : "false"}" data-dashboard-card-technical="${moduleRow?.is_technical ? "true" : "false"}">
            <div class="dash-card-title">${escapeHtml(title)}</div>
            <div class="dash-card-sub">${escapeHtml(subtitle)}</div>
            ${monitoringMetrics}
            ${visualMarkup}
            <div class="dash-card-stats">
                <span class="${escapeHtml(status.badgeClass)}">${escapeHtml(status.text)}</span>
                ${countLabel ? `<span class="meta-badge">${escapeHtml(countLabel)}</span>` : ""}
            </div>
        </article>
    `;
}

function ensurePortalDashboardEditor() {
    if (portalDashboardEditor) {
        return portalDashboardEditor;
    }
    const createEditor = window.NMPSharedUi?.dashboard?.createEditor;
    if (typeof createEditor !== "function") {
        return { decorateCards: () => {}, refresh: async () => {}, isEditing: () => false };
    }
    portalDashboardEditor = createEditor({
        scope: "portal",
        grid: cardsGrid,
        editButton: dashboardEditButton,
        loadPreferences: () => requestJson("/dashboard-preferences/portal"),
        savePreferences: (payload) => requestJson("/dashboard-preferences/portal", {
            method: "PUT",
            body: JSON.stringify(payload),
        }),
        getCardId: (card) => String(card?.dataset?.dashboardCardId || card?.dataset?.moduleCode || "").trim(),
        isCardActive: (_id, card) => String(card?.dataset?.dashboardCardActive || "false") === "true",
        canToggleCardActive: (_id, card) => String(card?.dataset?.dashboardCardTechnical || "false") !== "true",
        canPinCard: () => true,
        defaultCardPinned: (_id, card) => String(card?.dataset?.dashboardCardTechnical || "false") !== "true",
        defaultCardHidden: (_id, card) => String(card?.dataset?.dashboardCardTechnical || "false") === "true",
        toggleCardActive: async (id) => {
            const moduleRow = findPortalModuleByCode(id);
            if (!moduleRow) {
                return;
            }
            await setPortalModuleActivation(moduleRow, !Boolean(moduleRow.is_active));
        },
        onChanged: ({ action } = {}) => {
            if (action === "power") {
                loadPortalModules({ forceRefresh: true }).catch(() => {});
            }
            applyPortalModuleTileVisibility();
        },
    });
    return portalDashboardEditor;
}

function renderModuleCards(rows) {
    const modules = (Array.isArray(rows) ? rows : [])
        .filter((row) => Boolean(row?.granted))
        .filter((row) => !["admin", "users_admin", "imprimantes", "comptes", "interventions"].includes(String(row?.code || "").trim().toLowerCase()));
    const hasMonitoring = modules.some((row) => isMonitoringPortalModule(row));
    if (!hasMonitoring) {
        modules.unshift({
            code: "monitoring",
            label: "Monitoring reseau",
            route_path: "/monitoring",
            is_active: true,
            granted: state.sessionRoleCode === "admin" || ["sa", "admin"].includes(String(state.sessionSubject || "").trim().toLowerCase()),
        });
    }
    state.portalModules = modules;
    updatePortalSyncBadge(modules);
    if (!modules.length) {
        state.portalModules = [];
        updatePortalSyncBadge([]);
        stopPortalMonitoringSummaryRefresh();
        cardsGrid.innerHTML = `
            <article class="dash-card panel">
                <div class="dash-card-title">Modules</div>
                <div class="dash-card-sub">Aucun module visible pour cet utilisateur.</div>
                <div class="dash-card-stats">
                    <span class="stat-offline">Aucun acces</span>
                </div>
            </article>
        `;
        return;
    }
    cardsGrid.innerHTML = modules.map((moduleRow) => renderModuleCard(moduleRow)).join("");
    if (portalMonitoringModuleVisible()) {
        startPortalMonitoringSummaryRefresh();
    } else {
        stopPortalMonitoringSummaryRefresh();
    }
    ensurePortalDashboardEditor().refresh()
        .catch(() => {
            ensurePortalDashboardEditor().decorateCards();
        })
        .finally(() => {
            applyPortalModuleTileVisibility();
        });
}

async function loadPortalModules(options = {}) {
    const forceRefresh = Boolean(options.forceRefresh);
    if (!forceRefresh && state.moduleAccessLoaded) {
        renderModuleCards(state.moduleAccess);
        loadPortalMonitoringSummary({ forceRefresh: false })
            .then(() => renderModuleCards(state.moduleAccess))
            .catch(() => {});
        return state.moduleAccess;
    }
    try {
        const modules = await requestJson("/auth/me/modules");
        state.moduleAccess = Array.isArray(modules) ? modules : [];
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
        state.monitoringSummaryLoaded = false;
        renderModuleCards(state.moduleAccess);
        loadPortalMonitoringSummary({ forceRefresh: true })
            .then(() => renderModuleCards(state.moduleAccess))
            .catch(() => {});
        scheduleMonitoringPrewarm(state.moduleAccess);
        return state.moduleAccess;
    } catch (_error) {
        state.moduleAccess = [];
        state.moduleAccessLoaded = true;
        state.monitoringSummaryLoaded = false;
        const fallbackRows = [
            {
                code: "monitoring",
                label: "Monitoring",
                route_path: "/monitoring",
                is_active: true,
                granted: true,
            },
        ];
        renderModuleCards(fallbackRows);
        loadPortalMonitoringSummary({ forceRefresh: true })
            .then(() => renderModuleCards(fallbackRows))
            .catch(() => {});
        scheduleMonitoringPrewarm(fallbackRows);
        return state.moduleAccess;
    }
}

async function consumeServiceHashNavigation() {
    const serviceCode = extractServiceCodeFromRoutePath(window.location.hash || "");
    if (!serviceCode) {
        return;
    }
    const cleanUrl = `${window.location.pathname}${window.location.search}`;
    if (window.history && typeof window.history.replaceState === "function") {
        window.history.replaceState(null, document.title, cleanUrl);
    }
    try {
        await openServiceModuleFromPortal(serviceCode);
    } catch (error) {
        openModal("Module non disponible", `<p class="muted">${escapeHtml(normalizeErrorMessage(error.message))}</p>`);
    }
}

async function loadAdministrationData(options = {}) {
    state.noCodeSharedListsWarning = "";
    try {
        await adminStore.load(options);
    } catch (error) {
        const wantsSharedLists = Boolean(options.includeSharedLists);
        if (!wantsSharedLists) {
            throw error;
        }
        const fallback = { ...options, includeSharedLists: false };
        await adminStore.load(fallback);
        if (state.adminData && Array.isArray(state.adminData.sharedLists)) {
            state.adminData.sharedLists = [];
        }
        if (state.adminDataLoaded && Object.prototype.hasOwnProperty.call(state.adminDataLoaded, "sharedLists")) {
            state.adminDataLoaded.sharedLists = true;
        }
        state.noCodeSharedListsWarning = "Listes partagees indisponibles sur ce serveur (mise a jour/restart requis).";
    }
}

function buildRolesModalMarkup() {
    const shared = window.NMPSharedAdminUi;
    if (shared && typeof shared.buildRolesModalMarkup === "function") {
        return shared.buildRolesModalMarkup({
            roles: state.adminData.roles || [],
            escapeHtml,
        });
    }
    return `<section class="modal-section"><p class="error-text">Interface roles indisponible.</p></section>`;
}

function buildUsersModalMarkup() {
    const shared = window.NMPSharedAdminUi;
    if (shared && typeof shared.buildUsersModalMarkup === "function") {
        return shared.buildUsersModalMarkup({
            users: state.adminData.users || [],
            escapeHtml,
        });
    }
    return `<section class="modal-section"><p class="error-text">Interface comptes applicatifs indisponible.</p></section>`;
}

function roleFormMarkup(role = null) {
    const shared = window.NMPSharedAdminUi;
    if (shared && typeof shared.buildRoleFormMarkup === "function") {
        return shared.buildRoleFormMarkup({
            role,
            modules: state.adminData.modules || [],
            createFieldMarkup,
            escapeHtml,
        });
    }
    return `<section class="modal-section"><p class="error-text">Formulaire role indisponible.</p></section>`;
}

function userFormMarkup(user = null) {
    const shared = window.NMPSharedAdminUi;
    if (shared && typeof shared.buildUserFormMarkup === "function") {
        return shared.buildUserFormMarkup({
            user,
            roles: state.adminData.roles || [],
            createFieldMarkup,
            escapeHtml,
        });
    }
    return `<section class="modal-section"><p class="error-text">Formulaire compte applicatif indisponible.</p></section>`;
}

function normalizeNoCodeText(value) {
    return String(value || "").trim();
}

function normalizeNoCodeKind(value) {
    const raw = normalizeNoCodeText(value).toLowerCase();
    if (["choice", "select", "dropdown", "liste"].includes(raw)) {
        return "list";
    }
    return NO_CODE_FIELD_KINDS.includes(raw) ? raw : "text";
}

function normalizeListSourceKind(value) {
    const raw = normalizeNoCodeText(value).toLowerCase();
    return raw === "shared" ? "shared" : "local";
}

function noCodeKindLabel(kind) {
    const key = normalizeNoCodeKind(kind);
    return NO_CODE_FIELD_KIND_LABELS[key] || "Texte";
}

function sharedListRows() {
    return Array.isArray(state.adminData?.sharedLists) ? state.adminData.sharedLists : [];
}

function findSharedList(listCode) {
    const wanted = normalizeNoCodeText(listCode).toLowerCase();
    if (!wanted) {
        return null;
    }
    return sharedListRows().find((row) => String(row?.code || "").trim().toLowerCase() === wanted) || null;
}

function createSharedListEditor(list = null) {
    return {
        mode: list ? "edit" : "create",
        code: String(list?.code || "").trim().toLowerCase(),
        label: String(list?.label || "").trim(),
        is_system: Boolean(list?.is_system),
        sort_order: Number(list?.sort_order || 100),
        version_token: String(list?.version_token || "").trim(),
    };
}

function createSharedListItemEditor(item = null) {
    return {
        mode: item ? "edit" : "create",
        code: String(item?.code || "").trim().toLowerCase(),
        label: String(item?.label || "").trim(),
        is_active: item ? Boolean(item?.is_active) : true,
        sort_order: Number(item?.sort_order || 100),
        version_token: String(item?.version_token || "").trim(),
    };
}

function buildSharedListsModalMarkup() {
    return buildTreeSectionMarkup({
        title: "Listes partagees",
        description: "Une liste partagee permet de reutiliser la meme liste de valeurs dans plusieurs services.",
        titleActionsMarkup: createIconActionButtonMarkup({
            icon: "add",
            action: "shared-list:add",
            title: "Ajouter une liste partagee",
        }),
        searchId: "shared-lists-search",
        searchPlaceholder: "Code, libelle",
        headId: "shared-lists-head",
        bodyId: "shared-lists-body",
        headMarkup: `
            <tr>
                <th data-shared-lists-col="code">Code</th>
                <th data-shared-lists-col="label">Libelle</th>
                <th data-shared-lists-col="item_count">Valeurs</th>
                <th data-shared-lists-col="is_system">Systeme</th>
                <th>Actions</th>
            </tr>
        `,
        feedbackId: "modal-shared-list-feedback",
        footerActionsMarkup: createModalActionsMarkup({
            buttons: [{ preset: "back", action: "shared-list:back-services", label: "Retour services" }],
        }),
    });
}

function buildSharedListEditorMarkup() {
    const editor = state.noCodeSharedListEditor;
    if (!editor) {
        return "";
    }
    const isEdit = editor.mode === "edit";
    return `
        <form id="modal-shared-list-form" class="modal-form" data-edit-code="${escapeHtml(editor.code)}" data-version-token="${escapeHtml(editor.version_token)}">
            <section class="modal-section">
                <h3>${escapeHtml(isEdit ? "Modifier la liste partagee" : "Nouvelle liste partagee")}</h3>
                <div class="modal-settings-grid">
                    <label class="field">
                        <span>Code technique</span>
                        <input name="shared_list_code" value="${escapeHtml(editor.code)}" ${isEdit ? "disabled aria-disabled='true'" : ""} placeholder="Ex: services_mairie">
                    </label>
                    <label class="field">
                        <span>Libelle</span>
                        <input name="shared_list_label" value="${escapeHtml(editor.label)}" placeholder="Ex: Services de la mairie">
                    </label>
                    <label class="field">
                        <span>Ordre</span>
                        <input name="shared_list_sort_order" type="number" value="${Number(editor.sort_order || 100)}">
                    </label>
                </div>
                <label class="check-field">
                    <input name="shared_list_is_system" type="checkbox" ${editor.is_system ? "checked" : ""} ${isEdit ? "disabled aria-disabled='true'" : ""}>
                    <span>Liste systeme (non supprimable)</span>
                </label>
                <p id="modal-shared-list-form-feedback" class="muted inventory-feedback"></p>
                ${createModalActionsMarkup({
                    buttons: [
                        { preset: "back", action: "shared-list:back" },
                        {
                            preset: isEdit ? "save" : "add",
                            label: isEdit ? "Enregistrer" : "Ajouter",
                        },
                    ],
                })}
            </section>
        </form>
    `;
}

function buildSharedListItemsModalMarkup() {
    const context = state.noCodeSharedListItemsContext;
    if (!context?.list) {
        return "";
    }
    const list = context.list;
    const code = String(list.code || "").trim().toLowerCase();
    const label = String(list.label || code).trim() || code;
    return buildTreeSectionMarkup({
        title: label,
        description: `${code} | Valeurs disponibles pour les champs lies a cette liste partagee.`,
        titleActionsMarkup: `
            ${createActionButtonMarkup({
                preset: "export",
                action: "shared-list-item:export",
                label: "Exporter CSV",
                title: "Exporter la liste au format CSV",
            })}
            ${createActionButtonMarkup({
                preset: "import",
                className: "toolbar-btn",
                action: "shared-list-item:import",
                label: "Importer",
                title: "Importer un fichier CSV ou XLSX (detection automatique)",
            })}
            ${createIconActionButtonMarkup({
                icon: "add",
                action: "shared-list-item:add",
                title: "Ajouter une valeur",
            })}
        `,
        searchId: "shared-list-items-search",
        searchPlaceholder: "Code, libelle",
        headId: "shared-list-items-head",
        bodyId: "shared-list-items-body",
        headMarkup: `
            <tr>
                <th data-shared-list-items-col="code">Code</th>
                <th data-shared-list-items-col="label">Libelle</th>
                <th data-shared-list-items-col="is_active">Actif</th>
                <th data-shared-list-items-col="sort_order">Ordre</th>
                <th>Actions</th>
            </tr>
        `,
        feedbackId: "modal-shared-list-items-feedback",
        footerActionsMarkup: createModalActionsMarkup({
            buttons: [{ preset: "back", action: "shared-list-item:back" }],
        }),
    });
}

function buildSharedListItemEditorMarkup() {
    const context = state.noCodeSharedListItemsContext;
    const editor = state.noCodeSharedListItemEditor;
    if (!context?.list || !editor) {
        return "";
    }
    const isEdit = editor.mode === "edit";
    return `
        <form id="modal-shared-list-item-form" class="modal-form" data-edit-code="${escapeHtml(editor.code)}" data-version-token="${escapeHtml(editor.version_token)}">
            <section class="modal-section">
                <h3>${escapeHtml(isEdit ? "Modifier la valeur" : "Nouvelle valeur")}</h3>
                <div class="modal-settings-grid">
                    <label class="field">
                        <span>Code technique</span>
                        <input name="shared_list_item_code" value="${escapeHtml(editor.code)}" ${isEdit ? "disabled aria-disabled='true'" : ""}>
                    </label>
                    <label class="field">
                        <span>Libelle</span>
                        <input name="shared_list_item_label" value="${escapeHtml(editor.label)}">
                    </label>
                    <label class="field">
                        <span>Ordre</span>
                        <input name="shared_list_item_sort_order" type="number" value="${Number(editor.sort_order || 100)}">
                    </label>
                </div>
                <label class="check-field">
                    <input name="shared_list_item_is_active" type="checkbox" ${editor.is_active ? "checked" : ""}>
                    <span>Valeur active</span>
                </label>
                <p id="modal-shared-list-item-form-feedback" class="muted inventory-feedback"></p>
                ${createModalActionsMarkup({
                    buttons: [
                        { preset: "back", action: "shared-list-item:back" },
                        {
                            preset: isEdit ? "save" : "add",
                            label: isEdit ? "Enregistrer" : "Ajouter",
                        },
                    ],
                })}
            </section>
        </form>
    `;
}

function noCodeInlineOptions(width, options = {}) {
    const inlineMode = options.inline !== undefined ? Boolean(options.inline) : true;
    state.noCodeInlineMode = inlineMode;
    return {
        width,
        inlineHost: inlineMode ? "portal" : "",
    };
}

function adminInlineOptions(width, options = {}) {
    const inlineMode = options.inline !== undefined ? Boolean(options.inline) : Boolean(state.adminInlineMode);
    state.adminInlineMode = inlineMode;
    return {
        width,
        inlineHost: inlineMode ? "portal" : "",
    };
}

async function openSharedListsModal(options = {}) {
    await loadAdministrationData({
        includeModules: false,
        includeRoles: false,
        includeUsers: false,
        includeServices: false,
        includeSharedLists: true,
    });
    state.noCodeServiceEditor = null;
    state.noCodeServiceEditorContext = null;
    state.noCodeServiceRecordContext = null;
    state.noCodeRecordEditor = null;
    state.noCodeSharedListEditor = null;
    state.noCodeSharedListItemsContext = null;
    state.noCodeSharedListItemEditor = null;
    openModal("Services - Listes partagees", buildSharedListsModalMarkup(), noCodeInlineOptions("min(1080px, calc(100vw - 40px))", options));
    renderSharedListsTreeView();
}

function openSharedListEditor(list = null, options = {}) {
    state.noCodeSharedListEditor = createSharedListEditor(list);
    state.noCodeSharedListItemsContext = null;
    state.noCodeSharedListItemEditor = null;
    openModal(
        list ? "Liste partagee - Edition" : "Liste partagee - Creation",
        buildSharedListEditorMarkup(),
        noCodeInlineOptions("min(860px, calc(100vw - 40px))", options),
    );
}

async function openSharedListItemsModal(listCode, options = {}) {
    let list = findSharedList(listCode);
    if (!list) {
        await loadAdministrationData({
            includeModules: false,
            includeRoles: false,
            includeUsers: false,
            includeServices: false,
            includeSharedLists: true,
        });
        list = findSharedList(listCode);
    }
    if (!list) {
        throw new Error("Liste partagee introuvable.");
    }
    const code = String(list.code || "").trim().toLowerCase();
    const items = await requestJson(`/admin/shared-lists/${encodeURIComponent(code)}/items`);
    state.noCodeSharedListEditor = null;
    state.noCodeSharedListItemsContext = {
        list,
        items: Array.isArray(items) ? items : [],
    };
    state.noCodeSharedListItemEditor = null;
    openModal(
        `Liste partagee - ${list.label || list.code}`,
        buildSharedListItemsModalMarkup(),
        noCodeInlineOptions("min(1080px, calc(100vw - 40px))", options),
    );
    renderSharedListItemsTreeView();
}

function openSharedListItemEditor(item = null, options = {}) {
    if (!state.noCodeSharedListItemsContext?.list) {
        return;
    }
    state.noCodeSharedListEditor = null;
    state.noCodeSharedListItemEditor = createSharedListItemEditor(item);
    openModal(
        item ? "Valeur - Edition" : "Valeur - Creation",
        buildSharedListItemEditorMarkup(),
        noCodeInlineOptions("min(860px, calc(100vw - 40px))", options),
    );
}

function slugifyNoCodeIdentifier(value, fallback = "item") {
    let normalized = normalizeNoCodeText(value).toLowerCase();
    normalized = normalized.replace(/[^a-z0-9]+/g, "_");
    normalized = normalized.replace(/_+/g, "_").replace(/^_+|_+$/g, "");
    if (!normalized) {
        normalized = fallback;
    }
    if (/^[0-9]/.test(normalized)) {
        normalized = `${fallback}_${normalized}`;
    }
    return normalized;
}

function parseNoCodeOptions(raw) {
    const values = String(raw || "")
        .split(/[,;\n\r]+/)
        .map((item) => item.trim())
        .filter(Boolean);
    const seen = new Set();
    const cleaned = [];
    for (const value of values) {
        const key = value.toLowerCase();
        if (seen.has(key)) {
            continue;
        }
        seen.add(key);
        cleaned.push(value);
    }
    return cleaned;
}

function buildTabularSourcePreviewTable(headers = [], rows = []) {
    const normalizedHeaders = Array.isArray(headers) ? headers : [];
    const normalizedRows = Array.isArray(rows) ? rows : [];
    if (!normalizedRows.length) {
        return '<p class="muted">Aucune colonne detectee.</p>';
    }
    const maxColumns = Math.max(
        normalizedHeaders.length,
        ...normalizedRows.map((row) => (Array.isArray(row) ? row.length : 0)),
        0,
    );
    const resolvedHeaders = maxColumns
        ? Array.from({ length: maxColumns }, (_value, index) => String(normalizedHeaders[index] || `Colonne ${index + 1}`))
        : [];
    const headCells = resolvedHeaders.map((header) => `<th>${escapeHtml(String(header || ""))}</th>`).join("");
    const bodyRows = normalizedRows.length
        ? normalizedRows.map((row, index) => {
            const cells = resolvedHeaders.map((_header, columnIndex) => (
                `<td>${escapeHtml(String(row?.[columnIndex] || ""))}</td>`
            )).join("");
            return `<tr><td class="muted">${index + 1}</td>${cells}</tr>`;
        }).join("")
        : `<tr><td colspan="${resolvedHeaders.length + 1}" class="muted">Aucune ligne de previsualisation.</td></tr>`;
    return `
        <div class="table-wrap">
            <table class="device-table">
                <thead><tr><th>#</th>${headCells}</tr></thead>
                <tbody>${bodyRows}</tbody>
            </table>
        </div>
    `;
}

async function pickServiceDefinitionImportFile() {
    const sharedImport = window.NMPSharedImport;
    if (sharedImport && typeof sharedImport.pickFile === "function") {
        return sharedImport.pickFile({ accept: ".xlsx,.csv,.txt,.tsv" });
    }
    const picker = document.createElement("input");
    picker.type = "file";
    picker.accept = ".xlsx,.csv,.txt,.tsv";
    return new Promise((resolve) => {
        picker.addEventListener("change", () => {
            resolve(picker.files && picker.files[0] ? picker.files[0] : null);
        }, { once: true });
        picker.click();
    });
}

function normalizeImportedServiceFields(rows = []) {
    return (Array.isArray(rows) ? rows : []).map((row, index) => ({
        field_key: String(row?.field_key || `field_${index + 1}`).trim(),
        label: String(row?.label || "").trim(),
        field_kind: normalizeNoCodeKind(row?.field_kind || "text"),
        required: Boolean(row?.required),
        options: String(row?.options || ""),
        default_value: String(row?.default_value || ""),
        sort_order: Number(row?.sort_order || ((index + 1) * 10)),
        list_source_kind: normalizeListSourceKind(row?.list_source_kind || "local"),
        shared_list_code: String(row?.shared_list_code || "").trim().toLowerCase(),
        track_history: Boolean(row?.track_history),
    }));
}

function normalizeServiceFieldImportMappings(mappings) {
    return (Array.isArray(mappings) ? mappings : [])
        .map((row) => ({
            source_column: String(row?.source_column || "").trim(),
            target_field: String(row?.target_field || "__create_field__").trim() || "__create_field__",
            custom_key: String(row?.custom_key || "").trim(),
            field_kind: String(row?.field_kind || "auto").trim().toLowerCase() || "auto",
        }))
        .filter((row) => row.source_column);
}

function mergeServiceFieldImportMappings(baseMappings, changedMappings) {
    const merged = new Map();
    normalizeServiceFieldImportMappings(baseMappings).forEach((row) => {
        merged.set(row.source_column, row);
    });
    normalizeServiceFieldImportMappings(changedMappings).forEach((row) => {
        merged.set(row.source_column, row);
    });
    return Array.from(merged.values());
}

function readServiceFieldImportMappingsFromDom() {
    const sharedImport = window.NMPSharedImport;
    if (sharedImport && typeof sharedImport.collectColumnMappings === "function") {
        return sharedImport.collectColumnMappings(document, {
            rowSelector: "th[data-source-column]",
            targetName: "service_field_import_target",
            customName: "service_field_import_custom",
            fieldKindName: "service_field_import_kind",
        });
    }
    return Array.from(document.querySelectorAll('select[name="service_field_import_target"]'))
        .map((select) => ({
            source_column: String(select.closest("[data-source-column]")?.getAttribute("data-source-column") || "").trim(),
            target_field: String(select.value || "__create_field__").trim() || "__create_field__",
            custom_key: String(select.closest("[data-source-column]")?.querySelector?.('input[name="service_field_import_custom"]')?.value || "").trim(),
            field_kind: String(select.closest("[data-source-column]")?.querySelector?.('select[name="service_field_import_kind"]')?.value || "auto").trim(),
        }))
        .filter((row) => row.source_column);
}

function readServiceFieldImportUntilRowFromForm(form = document) {
    const input = form?.querySelector?.('input[name="service_field_import_until_row"]');
    return normalizeTabularUntilRowNumber(input instanceof HTMLInputElement ? input.value : state.noCodeServiceEditor?.importUntilRowNumber);
}

function buildRecordMappingsFromAppliedServiceFieldImport(appliedImport) {
    const headers = Array.isArray(appliedImport?.sourceHeaders) ? appliedImport.sourceHeaders : [];
    const fields = Array.isArray(appliedImport?.fields) ? appliedImport.fields : [];
    const mappings = normalizeServiceFieldImportMappings(appliedImport?.columnMappings || []);
    const mappingBySource = new Map(mappings.map((row) => [String(row.source_column || "").trim(), row]));
    let fieldIndex = 0;
    return headers
        .map((header) => {
            const sourceColumn = String(header || "").trim();
            const mapping = mappingBySource.get(sourceColumn) || { target_field: "__create_field__" };
            if (!sourceColumn || String(mapping.target_field || "").trim() === "__ignore__") {
                return null;
            }
            const field = fields[fieldIndex] || null;
            fieldIndex += 1;
            const fieldKey = String(field?.field_key || "").trim();
            return fieldKey
                ? { source_column: sourceColumn, target_field: fieldKey, custom_key: "" }
                : null;
        })
        .filter(Boolean);
}

function buildServiceFieldImportMappingMarkup(editor, sourceHeaders, sourceRowsPreview) {
    const headers = (Array.isArray(sourceHeaders) ? sourceHeaders : [])
        .map((header) => String(header || "").trim())
        .filter(Boolean);
    if (!headers.length) {
        return buildTabularSourcePreviewTable(headers, sourceRowsPreview);
    }
    const sharedImport = window.NMPSharedImport;
    const existingFieldOptions = (Array.isArray(editor?.fields) ? editor.fields : [])
        .map((field) => {
            const fieldKey = String(field?.field_key || "").trim();
            const label = String(field?.label || fieldKey).trim();
            return fieldKey ? { value: fieldKey, label: `Champ existant: ${label}` } : null;
        })
        .filter(Boolean);
    const detectedHeaderRowNumber = Number(editor?.importPreview?.detectedHeaderRowNumber || 1);
    const sampleRows = Array.isArray(sourceRowsPreview)
        ? sourceRowsPreview.slice(Math.max(0, detectedHeaderRowNumber - 1), Math.max(0, detectedHeaderRowNumber))
        : [];
    if (sharedImport && typeof sharedImport.buildIntegratedMappingPreviewTable === "function") {
        return sharedImport.buildIntegratedMappingPreviewTable({
            headers,
            rows: Array.isArray(sourceRowsPreview) ? sourceRowsPreview : [],
            sampleRows,
            targetOptions: [
                { value: "__create_field__", label: "Ajouter" },
                ...existingFieldOptions,
                { value: "__ignore__", label: "Ignorer" },
            ],
            effectiveMapping: editor?.importPreview?.effectiveMapping || [],
            draftMapping: editor?.importColumnMappings || [],
            defaultTarget: "__create_field__",
            ignoreValue: "__ignore__",
            selectName: "service_field_import_target",
            customName: "service_field_import_custom",
            fieldKindName: "service_field_import_kind",
            fieldKindOptions: [
                { value: "auto", label: "Auto" },
                { value: "text", label: "Texte" },
                { value: "date", label: "Date" },
                { value: "list", label: "Liste" },
                { value: "ip", label: "IP" },
                { value: "url", label: "URL" },
            ],
            showCustomKey: true,
            customTargetValue: "__create_field__",
            customTargetValues: ["__create_field__"],
            customPlaceholder: "Nom du champ",
            tableClassName: "device-table import-mapping-table",
            wrapClassName: "table-wrap import-mapping-table-wrap",
            columnsPerPage: 6,
            columnPage: Number(editor?.importColumnPage || 0),
        });
    }
    return buildTabularSourcePreviewTable(headers, sourceRowsPreview);
}

async function importServiceFieldsFromFile(
    file,
    sheetName = "",
    headerMode = "auto",
    headerRowNumber = 1,
    columnMappings = [],
    importUntilRowNumber = 0,
) {
    const candidatePaths = [
        "/admin/custom-services/import/fields",
        "/admin/custom-services/import-fields",
        "/admin/custom-services/fields/import",
        "/admin/custom-services/import",
    ];
    const sharedImport = window.NMPSharedImport;
    if (sharedImport && typeof sharedImport.postImport === "function") {
        return sharedImport.postImport({
            file,
            headersFactory: headers,
            candidatePaths,
            normalizeErrorMessage,
            requestBodyBuilder: (ctx) => ({
                filename: String(ctx.file?.name || ""),
                content_base64: String(ctx.contentBase64 || ""),
                sheet_name: String(sheetName || "").trim(),
                header_mode: normalizeTabularHeaderMode(headerMode),
                header_row_number: normalizeTabularHeaderRowNumber(headerRowNumber),
                import_until_row_number: normalizeTabularUntilRowNumber(importUntilRowNumber),
                column_mappings: Array.isArray(columnMappings) ? columnMappings : [],
            }),
            responseMapper: (payload) => {
                const fields = normalizeImportedServiceFields(payload?.fields || []);
                return {
                    fields,
                    detectedRows: Number(payload?.detected_rows || 0),
                    detectedColumns: Number(payload?.detected_columns || fields.length),
                    sourceHeaders: Array.isArray(payload?.source_headers) ? payload.source_headers : [],
                    sourceRowsPreview: Array.isArray(payload?.source_rows_preview) ? payload.source_rows_preview : [],
                    availableSheets: Array.isArray(payload?.available_sheets) ? payload.available_sheets : [],
                    selectedSheetName: String(payload?.selected_sheet_name || "").trim(),
                    detectedHeaderRowNumber: Number(payload?.detected_header_row_number || 1),
                    effectiveHeaderMode: normalizeTabularHeaderMode(payload?.effective_header_mode || "auto"),
                    effectiveMapping: Array.isArray(payload?.effective_mapping) ? payload.effective_mapping : [],
                };
            },
        });
    }
    throw new Error("Module d'import indisponible.");
}

async function exportServiceFieldsToFile(serviceCode) {
    const code = String(serviceCode || "").trim().toLowerCase();
    if (!code) {
        throw new Error("Service introuvable.");
    }
    const candidatePaths = [
        `/admin/custom-services/${encodeURIComponent(code)}/fields/export`,
        `/admin/custom-services/${encodeURIComponent(code)}/export/fields`,
    ];
    const sharedImport = window.NMPSharedImport;
    if (!(sharedImport && typeof sharedImport.downloadExport === "function")) {
        throw new Error("Module d'export indisponible.");
    }
    return sharedImport.downloadExport({
        candidatePaths,
        headersFactory: headers,
        normalizeErrorMessage,
        defaultFilename: `service_fields_${code}.csv`,
    });
}

async function fetchNoCodeServiceRelations(serviceCode) {
    const code = String(serviceCode || "").trim().toLowerCase();
    if (!code) {
        return [];
    }
    const rows = await requestJson(`/admin/custom-services/${encodeURIComponent(code)}/relations`);
    return Array.isArray(rows) ? rows : [];
}

async function fetchNoCodeServiceRecordRelationLinks(serviceCode, recordId, relationId) {
    const code = String(serviceCode || "").trim().toLowerCase();
    const rid = String(recordId || "").trim();
    const relId = Number(relationId || 0);
    if (!code || !rid || relId <= 0) {
        return [];
    }
    const rows = await requestJson(
        `/admin/custom-services/${encodeURIComponent(code)}/records/${encodeURIComponent(rid)}/relations/${encodeURIComponent(String(relId))}/links`,
    );
    return Array.isArray(rows) ? rows : [];
}

async function fetchNoCodeServiceRecordRelationLinksBatch(serviceCode, recordIds, relationId) {
    const code = String(serviceCode || "").trim().toLowerCase();
    const relId = Number(relationId || 0);
    const ids = Array.from(new Set((Array.isArray(recordIds) ? recordIds : [])
        .map((recordId) => String(recordId || "").trim())
        .filter(Boolean)));
    if (!code || relId <= 0 || !ids.length) {
        return {};
    }
    const output = {};
    for (let index = 0; index < ids.length; index += 500) {
        const batch = ids.slice(index, index + 500);
        const payload = await requestJson(
            `/admin/custom-services/${encodeURIComponent(code)}/records/relations/${encodeURIComponent(String(relId))}/links/batch`,
            {
                method: "POST",
                body: JSON.stringify({ record_ids: batch }),
            },
        );
        Object.assign(output, payload && typeof payload === "object" ? payload : {});
    }
    return output;
}

async function createNoCodeServiceRecordRelationLink(serviceCode, recordId, relationId, linkedRecordId) {
    const code = String(serviceCode || "").trim().toLowerCase();
    const rid = String(recordId || "").trim();
    const relId = Number(relationId || 0);
    const linkedId = String(linkedRecordId || "").trim();
    if (!code || !rid || relId <= 0 || !linkedId) {
        throw new Error("Lien relation invalide.");
    }
    return requestJson(
        `/admin/custom-services/${encodeURIComponent(code)}/records/${encodeURIComponent(rid)}/relations/${encodeURIComponent(String(relId))}/links`,
        {
            method: "POST",
            body: JSON.stringify({ linked_record_id: linkedId }),
        },
    );
}

async function assignNoCodeRelationLinkToRecords({ context, records, relation, linkedRecordId }) {
    const activeContext = context || {};
    const serviceCode = String(activeContext?.service?.code || activeContext?.currentService?.code || "").trim().toLowerCase();
    const relationId = Number(relation?.id || 0);
    const linkedId = String(linkedRecordId || "").trim();
    const rows = Array.isArray(records) ? records : [];
    if (!serviceCode || relationId <= 0 || !linkedId || !rows.length) {
        throw new Error("Lien relation invalide.");
    }
    const linkedAcceptsManyCurrent = noCodeRelationAllowsMultipleCurrentFromLinked(activeContext, relation);
    if (!linkedAcceptsManyCurrent && rows.length > 1) {
        throw new Error("Cette cardinalite ne permet pas d'assigner le meme element lie a plusieurs fiches en une seule action.");
    }
    const currentAcceptsManyLinked = noCodeRelationAllowsMultipleLinkedFromCurrent(activeContext, relation);
    let created = 0;
    let replaced = 0;
    let skipped = 0;
    const errors = [];
    for (const row of rows) {
        const recordId = String(row?.id || row?.record_id || "").trim();
        if (!recordId) {
            skipped += 1;
            continue;
        }
        try {
            if (!currentAcceptsManyLinked) {
                const existingLinks = await fetchNoCodeServiceRecordRelationLinks(serviceCode, recordId, relationId);
                for (const link of existingLinks) {
                    const existingId = String(link?.linked_record?.id || "").trim();
                    if (existingId && existingId !== linkedId) {
                        await deleteNoCodeServiceRecordRelationLink(serviceCode, recordId, relationId, existingId);
                        replaced += 1;
                    }
                }
                if (existingLinks.some((link) => String(link?.linked_record?.id || "").trim() === linkedId)) {
                    skipped += 1;
                    continue;
                }
            }
            await createNoCodeServiceRecordRelationLink(serviceCode, recordId, relationId, linkedId);
            created += 1;
        } catch (error) {
            const message = normalizeErrorMessage(error.message);
            if (message.toLowerCase().includes("existe") || message.toLowerCase().includes("already")) {
                skipped += 1;
            } else {
                errors.push(`${noCodeRecordPrimaryLabel(activeContext?.service || activeContext?.currentService, row) || recordId}: ${message}`);
            }
        }
    }
    return { created, replaced, skipped, errors };
}

async function deleteNoCodeServiceRecordRelationLink(serviceCode, recordId, relationId, linkedRecordId) {
    const code = String(serviceCode || "").trim().toLowerCase();
    const rid = String(recordId || "").trim();
    const relId = Number(relationId || 0);
    const linkedId = String(linkedRecordId || "").trim();
    if (!code || !rid || relId <= 0 || !linkedId) {
        throw new Error("Lien relation invalide.");
    }
    return requestJson(
        `/admin/custom-services/${encodeURIComponent(code)}/records/${encodeURIComponent(rid)}/relations/${encodeURIComponent(String(relId))}/links/${encodeURIComponent(linkedId)}`,
        { method: "DELETE" },
    );
}

async function replaceNoCodeServiceRelations(serviceCode, relations, { allowLinkedRelationDeletion = false } = {}) {
    const code = String(serviceCode || "").trim().toLowerCase();
    if (!code) {
        return [];
    }
    const rows = await requestJson(`/admin/custom-services/${encodeURIComponent(code)}/relations`, {
        method: "PUT",
        body: JSON.stringify({
            relations: Array.isArray(relations) ? relations : [],
            allow_linked_relation_deletion: Boolean(allowLinkedRelationDeletion),
        }),
    });
    return Array.isArray(rows) ? rows : [];
}

async function fetchNoCodeRelationImpact(serviceCode, relationId) {
    const code = String(serviceCode || "").trim().toLowerCase();
    const id = Number(relationId || 0);
    if (!code || id <= 0) {
        return null;
    }
    return requestJson(`/admin/custom-services/${encodeURIComponent(code)}/relations/${encodeURIComponent(String(id))}/impact`);
}

async function fetchNoCodeServiceDeleteImpact(serviceCode) {
    const code = String(serviceCode || "").trim().toLowerCase();
    if (!code) {
        return null;
    }
    return requestJson(`/admin/custom-services/${encodeURIComponent(code)}/delete-impact`);
}

function normalizeImportedSharedListItems(rows = []) {
    return (Array.isArray(rows) ? rows : []).map((row, index) => ({
        code: String(row?.code || "").trim().toLowerCase(),
        label: String(row?.label || "").trim(),
        is_active: row?.is_active !== false,
        sort_order: Number(row?.sort_order || ((index + 1) * 10)),
    })).filter((row) => row.code && row.label);
}

async function importSharedListItemsFromFile(file, listCode, sheetName = "", headerMode = "auto", headerRowNumber = 1) {
    const code = String(listCode || "").trim().toLowerCase();
    if (!code) {
        throw new Error("Liste partagee introuvable.");
    }
    const candidatePaths = [
        `/admin/shared-lists/${encodeURIComponent(code)}/items/import`,
        `/admin/shared-lists/${encodeURIComponent(code)}/import-items`,
    ];
    const sharedImport = window.NMPSharedImport;
    if (!(sharedImport && typeof sharedImport.postImport === "function")) {
        throw new Error("Module d'import indisponible.");
    }
    return sharedImport.postImport({
        file,
        headersFactory: headers,
        candidatePaths,
        normalizeErrorMessage,
        requestBodyBuilder: (ctx) => ({
            filename: String(ctx.file?.name || ""),
            content_base64: String(ctx.contentBase64 || ""),
            sheet_name: String(sheetName || "").trim(),
            header_mode: normalizeTabularHeaderMode(headerMode),
            header_row_number: normalizeTabularHeaderRowNumber(headerRowNumber),
        }),
        responseMapper: (payload) => {
            const items = normalizeImportedSharedListItems(payload?.items || []);
            return {
                items,
                detectedRows: Number(payload?.detected_rows || 0),
                detectedColumns: Number(payload?.detected_columns || 0),
                availableSheets: Array.isArray(payload?.available_sheets) ? payload.available_sheets : [],
                selectedSheetName: String(payload?.selected_sheet_name || "").trim(),
                detectedHeaderRowNumber: Number(payload?.detected_header_row_number || 1),
                effectiveHeaderMode: normalizeTabularHeaderMode(payload?.effective_header_mode || "auto"),
            };
        },
    });
}

async function exportSharedListItemsToFile(listCode) {
    const code = String(listCode || "").trim().toLowerCase();
    if (!code) {
        throw new Error("Liste partagee introuvable.");
    }
    const candidatePaths = [
        `/admin/shared-lists/${encodeURIComponent(code)}/items/export`,
        `/admin/shared-lists/${encodeURIComponent(code)}/export-items`,
    ];
    const sharedImport = window.NMPSharedImport;
    if (!(sharedImport && typeof sharedImport.downloadExport === "function")) {
        throw new Error("Module d'export indisponible.");
    }
    return sharedImport.downloadExport({
        candidatePaths,
        headersFactory: headers,
        normalizeErrorMessage,
        defaultFilename: `shared_list_${code}.csv`,
    });
}

async function previewServiceRecordsFromFile(
    file,
    serviceCode,
    credentialMode = "preserve_on_blank",
    sheetName = "",
    headerMode = "auto",
    headerRowNumber = 1,
    columnMappings = [],
) {
    const code = String(serviceCode || "").trim().toLowerCase();
    if (!code) {
        throw new Error("Service introuvable.");
    }
    const sharedImport = window.NMPSharedImport;
    if (!(sharedImport && typeof sharedImport.postImport === "function")) {
        throw new Error("Module d'import indisponible.");
    }
    return sharedImport.postImport({
        file,
        headersFactory: headers,
        candidatePaths: [
            `/admin/custom-services/${encodeURIComponent(code)}/records/import/preview`,
        ],
        normalizeErrorMessage,
        requestBodyBuilder: (ctx) => ({
            filename: String(ctx.file?.name || ""),
            content_base64: String(ctx.contentBase64 || ""),
            upsert_existing: true,
            credential_mode: normalizeRecordsImportCredentialMode(credentialMode),
            sheet_name: String(sheetName || "").trim(),
            header_mode: normalizeTabularHeaderMode(headerMode),
            header_row_number: normalizeTabularHeaderRowNumber(headerRowNumber),
            column_mappings: Array.isArray(columnMappings) ? columnMappings : [],
        }),
        responseMapper: (payload) => ({
            rows: Array.isArray(payload?.rows) ? payload.rows : [],
            fields: Array.isArray(payload?.fields) ? payload.fields : [],
            detectedRows: Number(payload?.detected_rows || 0),
            detectedColumns: Number(payload?.detected_columns || 0),
            issues: Array.isArray(payload?.issues) ? payload.issues : [],
            sourceHeaders: Array.isArray(payload?.source_headers) ? payload.source_headers : [],
            sourceRowsPreview: Array.isArray(payload?.source_rows_preview) ? payload.source_rows_preview : [],
            availableSheets: Array.isArray(payload?.available_sheets) ? payload.available_sheets : [],
            selectedSheetName: String(payload?.selected_sheet_name || "").trim(),
            detectedHeaderRowNumber: Number(payload?.detected_header_row_number || 1),
            effectiveHeaderMode: normalizeTabularHeaderMode(payload?.effective_header_mode || "auto"),
            effectiveMapping: Array.isArray(payload?.effective_mapping) ? payload.effective_mapping : [],
        }),
    });
}

async function applyServiceRecordsImportFromFile(
    file,
    serviceCode,
    credentialMode = "preserve_on_blank",
    sheetName = "",
    headerMode = "auto",
    headerRowNumber = 1,
    columnMappings = [],
    importUntilRowNumber = 0,
    relaxedValidation = false,
    duplicatePolicy = "skip",
    duplicateFieldKey = "",
) {
    const code = String(serviceCode || "").trim().toLowerCase();
    if (!code) {
        throw new Error("Service introuvable.");
    }
    const sharedImport = window.NMPSharedImport;
    if (!(sharedImport && typeof sharedImport.postImport === "function")) {
        throw new Error("Module d'import indisponible.");
    }
    return sharedImport.postImport({
        file,
        headersFactory: headers,
        candidatePaths: [
            `/admin/custom-services/${encodeURIComponent(code)}/records/import/apply`,
        ],
        normalizeErrorMessage,
        requestBodyBuilder: (ctx) => ({
            filename: String(ctx.file?.name || ""),
            content_base64: String(ctx.contentBase64 || ""),
            upsert_existing: true,
            credential_mode: normalizeRecordsImportCredentialMode(credentialMode),
            sheet_name: String(sheetName || "").trim(),
            header_mode: normalizeTabularHeaderMode(headerMode),
            header_row_number: normalizeTabularHeaderRowNumber(headerRowNumber),
            import_until_row_number: normalizeTabularUntilRowNumber(importUntilRowNumber),
            column_mappings: Array.isArray(columnMappings) ? columnMappings : [],
            relaxed_validation: Boolean(relaxedValidation),
            duplicate_policy: String(duplicatePolicy || "skip"),
            duplicate_field_key: String(duplicateFieldKey || "").trim(),
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

async function applyServiceRecordsImportFromActiveDirectory(serviceCode, source = {}, relaxedValidation = false) {
    const code = String(serviceCode || "").trim().toLowerCase();
    if (!code) {
        throw new Error("Service introuvable.");
    }
    const payload = {
        target_kind: normalizeActiveDirectoryProfileTargetKind(source.targetKind || source.target_kind || "organizational_units"),
        field_mappings: Array.isArray(source.fieldMappings) ? source.fieldMappings : Array.isArray(source.field_mappings) ? source.field_mappings : [],
        upsert_existing: true,
        relaxed_validation: Boolean(relaxedValidation),
        limit: 5000,
    };
    return requestJson(`/admin/custom-services/${encodeURIComponent(code)}/records/import/active-directory`, {
        method: "POST",
        body: JSON.stringify(payload),
    });
}

async function applyServiceRecordsImportFromActiveDirectoryWithRelaxedFallback(serviceCode, source = {}) {
    const first = await applyServiceRecordsImportFromActiveDirectory(serviceCode, source, false);
    const created = Number(first?.created || 0);
    const updated = Number(first?.updated || 0);
    const skipped = Number(first?.skipped || 0);
    const processed = Number(first?.processed || 0);
    if ((created > 0 || updated > 0) || skipped <= 0 || processed <= 0) {
        return { applied: first, relaxed: false };
    }
    const second = await applyServiceRecordsImportFromActiveDirectory(serviceCode, source, true);
    return { applied: second, relaxed: true, strictIssues: Array.isArray(first?.issues) ? first.issues : [] };
}

async function exportServiceRecordsToFile(serviceCode) {
    const code = String(serviceCode || "").trim().toLowerCase();
    if (!code) {
        throw new Error("Service introuvable.");
    }
    const sharedImport = window.NMPSharedImport;
    if (!(sharedImport && typeof sharedImport.downloadExport === "function")) {
        throw new Error("Module d'export indisponible.");
    }
    return sharedImport.downloadExport({
        candidatePaths: [
            `/admin/custom-services/${encodeURIComponent(code)}/records/export`,
            `/admin/custom-services/${encodeURIComponent(code)}/export/records`,
        ],
        headersFactory: headers,
        normalizeErrorMessage,
        defaultFilename: `service_records_${code}.csv`,
    });
}

function summarizeImportedSharedListItems(items) {
    const rows = Array.isArray(items) ? items : [];
    if (!rows.length) {
        return "-";
    }
    const limit = 8;
    const labels = rows.slice(0, limit).map((row) => String(row?.label || row?.code || "").trim()).filter(Boolean);
    const suffix = rows.length > limit ? ` (+${rows.length - limit})` : "";
    return `${labels.join(", ")}${suffix}`;
}

function applyImportedSharedListItemsToContext(importedItems = []) {
    const context = state.noCodeSharedListItemsContext;
    if (!context || !context.list) {
        return;
    }
    context.items = normalizeImportedSharedListItems(importedItems).map((row) => ({
        list_code: String(context.list.code || "").trim().toLowerCase(),
        code: row.code,
        label: row.label,
        is_active: row.is_active,
        sort_order: row.sort_order,
        version_token: "",
    }));
}

async function persistSharedListItemsFromContext() {
    const context = state.noCodeSharedListItemsContext;
    if (!context?.list?.code) {
        throw new Error("Liste partagee introuvable.");
    }
    const listCode = String(context.list.code || "").trim().toLowerCase();
    const rows = Array.isArray(context.items) ? context.items : [];
    for (const row of rows) {
        await requestJson(`/admin/shared-lists/${encodeURIComponent(listCode)}/items`, {
            method: "POST",
            body: JSON.stringify({
                code: String(row.code || "").trim().toLowerCase(),
                label: String(row.label || "").trim(),
                is_active: row.is_active !== false,
                sort_order: Number(row.sort_order || 100),
            }),
        });
    }
}

async function promptSharedListImportSheetSelection(availableSheets = [], selectedSheetName = "") {
    const sheets = Array.isArray(availableSheets)
        ? availableSheets.map((item) => String(item || "").trim()).filter(Boolean)
        : [];
    if (sheets.length <= 1) {
        return sheets[0] || "";
    }
    const defaultSheet = String(selectedSheetName || sheets[0] || "").trim();
    const promptLabel = sheets.map((name, index) => `${index + 1}. ${name}`).join("\n");
    const rawInput = await showItopsPrompt({
        title: "Feuille a importer",
        message: `Plusieurs feuilles detectees.\n${promptLabel}`,
        label: "Numero ou nom de la feuille",
        value: defaultSheet,
        confirmLabel: "Continuer",
    });
    if (rawInput == null) {
        return null;
    }
    const token = String(rawInput || "").trim();
    if (!token) {
        return defaultSheet;
    }
    const asIndex = Number(token);
    if (Number.isInteger(asIndex) && asIndex >= 1 && asIndex <= sheets.length) {
        return sheets[asIndex - 1];
    }
    const normalized = token.toLowerCase();
    const matched = sheets.find((name) => name.toLowerCase() === normalized);
    return matched || defaultSheet;
}

async function promptTabularHeaderSelection(defaultMode = "auto", defaultRow = 1) {
    const initialMode = normalizeTabularHeaderMode(defaultMode);
    const rawMode = await showItopsPrompt({
        title: "Entete du tableau",
        label: "Mode d'entete (auto, manual ou first)",
        value: initialMode,
        confirmLabel: "Continuer",
    });
    if (rawMode == null) {
        return null;
    }
    const mode = normalizeTabularHeaderMode(rawMode);
    if (mode !== "manual") {
        return { mode, rowNumber: 1 };
    }
    const rawRow = await showItopsPrompt({
        title: "Ligne d'entete",
        label: "Numero de ligne pour l'entete",
        value: String(normalizeTabularHeaderRowNumber(defaultRow)),
        confirmLabel: "Continuer",
    });
    if (rawRow == null) {
        return null;
    }
    return {
        mode,
        rowNumber: normalizeTabularHeaderRowNumber(rawRow),
    };
}

async function runSharedListItemsImportFlow() {
    const context = state.noCodeSharedListItemsContext;
    const listCode = String(context?.list?.code || "").trim().toLowerCase();
    if (!listCode) {
        const feedback = document.getElementById("modal-shared-list-items-feedback");
        if (feedback) {
            feedback.textContent = "Liste partagee introuvable.";
        }
        return;
    }
    const file = await pickServiceDefinitionImportFile();
    if (!file) {
        return;
    }
    const feedback = document.getElementById("modal-shared-list-items-feedback");
    try {
        if (feedback) {
            feedback.textContent = "Analyse du fichier en cours...";
        }
        let imported = await importSharedListItemsFromFile(file, listCode, "", "auto", 1);
        const selectedSheet = await promptSharedListImportSheetSelection(imported.availableSheets, imported.selectedSheetName);
        if (selectedSheet == null) {
            if (feedback) {
                feedback.textContent = "Import annule.";
            }
            return;
        }
        const initialSheet = String(imported.selectedSheetName || "").trim();
        if (selectedSheet && selectedSheet !== initialSheet) {
            imported = await importSharedListItemsFromFile(file, listCode, selectedSheet, "auto", 1);
        }
        const headerChoice = await promptTabularHeaderSelection(imported.effectiveHeaderMode, imported.detectedHeaderRowNumber);
        if (headerChoice == null) {
            if (feedback) {
                feedback.textContent = "Import annule.";
            }
            return;
        }
        if (
            normalizeTabularHeaderMode(imported.effectiveHeaderMode) !== normalizeTabularHeaderMode(headerChoice.mode)
            || normalizeTabularHeaderRowNumber(imported.detectedHeaderRowNumber) !== normalizeTabularHeaderRowNumber(headerChoice.rowNumber)
        ) {
            imported = await importSharedListItemsFromFile(
                file,
                listCode,
                selectedSheet,
                headerChoice.mode,
                headerChoice.rowNumber,
            );
        }
        if (!Array.isArray(imported?.items) || !imported.items.length) {
            if (feedback) {
                feedback.textContent = "Aucune valeur exploitable detectee.";
            }
            return;
        }
        const rowsCount = Number(imported.detectedRows || 0);
        const preview = summarizeImportedSharedListItems(imported.items);
        const confirmed = await confirmBatchAction({
            title: "Importer les valeurs",
            count: imported.items.length,
            itemLabel: "valeur",
            itemPluralLabel: "valeurs",
            actionLabel: `Importer dans la liste partagee '${listCode}'`,
            details: [`Apercu: ${preview}`],
            confirmLabel: "Importer",
        });
        if (!confirmed) {
            if (feedback) {
                feedback.textContent = "Import annule.";
            }
            return;
        }
        applyImportedSharedListItemsToContext(imported.items);
        await persistSharedListItemsFromContext();
        invalidateAdminData(["sharedLists", "services"]);
        await openSharedListItemsModal(listCode);
        if (feedback) {
            feedback.textContent = `Import termine: ${imported.items.length} valeur(s) (${rowsCount} ligne(s) analysee(s)).`;
        }
    } catch (error) {
        if (feedback) {
            feedback.textContent = normalizeErrorMessage(error.message);
        }
    }
}

function noCodeFieldEditorSeed(field = null) {
    if (!field) {
        return {
            mode: "create",
            originalKey: "",
            label: "",
            field_kind: "text",
            required: false,
            options: "",
            default_value: "",
            list_source_kind: "local",
            shared_list_code: "",
            track_history: false,
            inline_editable: false,
            batch_editable: false,
            quick_filter: false,
        };
    }
    return {
        mode: "edit",
        originalKey: String(field.field_key || "").trim(),
        label: String(field.label || "").trim(),
        field_kind: normalizeNoCodeKind(field.field_kind || "text"),
        required: Boolean(field.required),
        options: String(field.options || ""),
        default_value: String(field.default_value || ""),
        list_source_kind: normalizeListSourceKind(field.list_source_kind || "local"),
        shared_list_code: String(field.shared_list_code || "").trim().toLowerCase(),
        track_history: Boolean(field.track_history),
        inline_editable: Boolean(field.inline_editable),
        batch_editable: Boolean(field.batch_editable),
        quick_filter: Boolean(field.quick_filter),
    };
}

function normalizeNoCodeCredentialFieldKey(value) {
    return String(value || "").trim().toLowerCase();
}

function isNoCodeCredentialFieldKey(value) {
    return NO_CODE_CREDENTIAL_FIELD_KEYS.has(normalizeNoCodeCredentialFieldKey(value));
}

function noCodeCustomServiceFields(service) {
    const fields = Array.isArray(service?.fields) ? service.fields : [];
    return fields.filter((row) => !isNoCodeCredentialFieldKey(row?.field_key));
}

function noCodeCredentialValueFromMap(values, kind) {
    const source = values && typeof values === "object" ? values : {};
    const candidates = kind === "password"
        ? NO_CODE_CREDENTIAL_LEGACY_PASSWORD_KEYS
        : NO_CODE_CREDENTIAL_LEGACY_LOGIN_KEYS;
    for (const key of candidates) {
        const value = String(source?.[key] || "").trim();
        if (value) {
            return value;
        }
    }
    return "";
}

function noCodeRecordCredentialKey(serviceCode, recordId) {
    return `${normalizeNoCodeText(serviceCode).toLowerCase()}:${String(recordId || "").trim()}`;
}

function noCodeRecordHasStoredCredentialPassword(record) {
    return Boolean(
        record?.has_credential_password
        || record?.has_device_password
        || String(record?.credential_password_masked || record?.device_password_masked || "").trim()
        || noCodeCredentialValueFromMap(record?.values || {}, "password"),
    );
}

function noCodeRecordCredentialPasswordMask(record) {
    const explicit = String(record?.credential_password_masked || record?.device_password_masked || "").trim();
    if (explicit) {
        return explicit;
    }
    return noCodeRecordHasStoredCredentialPassword(record) ? "********" : "";
}

function revealedNoCodeRecordPassword(serviceCode, recordId) {
    if (!ensureCredentialRevealSessionFresh()) {
        return "";
    }
    return String(state.revealedNoCodeRecordPasswords[noCodeRecordCredentialKey(serviceCode, recordId)] || "");
}

function noCodeRecordHasCredentialValues(record) {
    const values = record?.values && typeof record.values === "object" ? record.values : {};
    return Boolean(
        noCodeCredentialValueFromMap(values, "login")
        || noCodeRecordHasStoredCredentialPassword(record),
    );
}

function createNoCodeServiceEditor(service = null) {
    const serviceFields = noCodeCustomServiceFields(service);
    const fields = Array.isArray(serviceFields)
        ? serviceFields.map((row, index) => ({
            field_key: String(row?.field_key || `field_${index + 1}`).trim(),
            label: String(row?.label || "").trim(),
            field_kind: normalizeNoCodeKind(row?.field_kind || "text"),
            required: Boolean(row?.required),
            options: String(row?.options || ""),
            default_value: String(row?.default_value || ""),
            sort_order: Number(row?.sort_order || ((index + 1) * 10)),
            list_source_kind: normalizeListSourceKind(row?.list_source_kind || "local"),
            shared_list_code: String(row?.shared_list_code || "").trim().toLowerCase(),
            track_history: Boolean(row?.track_history),
            inline_editable: Boolean(row?.inline_editable),
            quick_filter: Boolean(row?.quick_filter),
        }))
        : [];
    return {
        mode: service ? "edit" : "create",
        wizardStep: 1,
        code: String(service?.code || "").trim(),
        label: String(service?.label || "").trim(),
        icon: String(service?.icon || "").trim().toLowerCase(),
        color: String(service?.color || "").trim(),
        tile_config: {
            show_count: service?.tile_config?.show_count !== false,
            remote_access: service?.tile_config?.remote_access && typeof service.tile_config.remote_access === "object"
                ? { ...service.tile_config.remote_access }
                : {},
        },
        is_active: service ? Boolean(service?.is_active) : true,
        is_technical: Boolean(service?.is_technical),
        credentials_enabled: Boolean(service?.credentials_enabled),
        initial_credentials_enabled: Boolean(service?.credentials_enabled),
        child_enabled: Boolean(service?.child_enabled),
        child_label: String(service?.child_label || "Elements lies").trim() || "Elements lies",
        sort_order: Number(service?.sort_order || 100),
        version_token: String(service?.version_token || "").trim(),
        fields,
        fieldEditor: null,
        importFile: null,
        importPreview: null,
        importRecordsEnabled: true,
        appliedImportForRecords: null,
        importHeaderMode: "auto",
        importHeaderRowNumber: 1,
        importAdvancedEnabled: false,
        importUntilRowNumber: 0,
        importColumnMappings: [],
        importColumnPage: 0,
        adImportPayload: null,
        adImportDraft: null,
        appliedActiveDirectoryImportForRecords: null,
        relationCanvas: {
            zoom: 1,
            currentX: 36,
            currentY: 176,
        },
        relationDrafts: [],
        assignmentAssistantFeedbacks: {},
        selectedRelationServiceCode: "",
    };
}

function noCodeServiceRows() {
    return Array.isArray(state.adminData.services)
        ? state.adminData.services.filter((row) => !isReservedSystemEntityCode(row))
        : [];
}

const NO_CODE_RELATION_SYSTEM_ENTITIES = [
    {
        code: "utilisateurs",
        label: "Agents",
        relation_kind: "system",
        fields: [
            { label: "Nom", field_key: "display_name", field_kind: "text" },
            { label: "Identifiant", field_key: "login", field_kind: "text" },
            { label: "Service", field_key: "service", field_kind: "text" },
        ],
    },
    {
        code: "services",
        label: "Services",
        relation_kind: "system",
        fields: [
            { label: "Nom", field_key: "name", field_kind: "text" },
            { label: "Parent", field_key: "parent", field_kind: "text" },
            { label: "Source", field_key: "source", field_kind: "text" },
        ],
    },
];

function normalizeNoCodeRelationEntityCode(value) {
    const code = normalizeNoCodeText(value).toLowerCase();
    const aliases = {
        utilisateur: "utilisateurs",
        user: "utilisateurs",
        users: "utilisateurs",
        agent: "utilisateurs",
        agents: "utilisateurs",
        service: "services",
        ou: "services",
        ous: "services",
        organisation: "services",
        organisations: "services",
        organization: "services",
        organizations: "services",
    };
    return aliases[code] || code;
}

function findNoCodeRelationSystemEntity(code) {
    const wanted = normalizeNoCodeRelationEntityCode(code);
    return NO_CODE_RELATION_SYSTEM_ENTITIES.find((row) => row.code === wanted) || null;
}

function findAdminModuleRow(moduleCode) {
    const wanted = normalizeNoCodeText(moduleCode).toLowerCase();
    if (!wanted) {
        return null;
    }
    const rows = Array.isArray(state.adminData.modules) ? state.adminData.modules : [];
    return rows.find((row) => String(row?.code || "").trim().toLowerCase() === wanted) || null;
}

function findNoCodeService(serviceCode) {
    const wanted = normalizeNoCodeText(serviceCode).toLowerCase();
    if (!wanted) {
        return null;
    }
    return noCodeServiceRows().find((row) => String(row?.code || "").trim().toLowerCase() === wanted) || null;
}

function findNoCodeRelationEntity(entityCode) {
    const wanted = normalizeNoCodeRelationEntityCode(entityCode);
    if (!wanted) {
        return null;
    }
    return findNoCodeService(wanted) || findNoCodeRelationSystemEntity(wanted);
}

function noCodeRelationEntityFields(entity) {
    return Array.isArray(entity?.fields) ? entity.fields : noCodeCustomServiceFields(entity);
}

function buildNoCodeServicesModalMarkup() {
    return buildTreeSectionMarkup({
        title: "Services",
        description: "Creer des services et gerer leurs fiches.",
        titleActionsMarkup: createIconActionButtonMarkup({
            icon: "add",
            action: "service:definition:add",
            title: "Ajouter un service",
        }),
        searchId: "no-code-services-search",
        searchPlaceholder: "Code, libelle, sous-liste",
        headId: "no-code-services-head",
        bodyId: "no-code-services-body",
        headMarkup: `
            <tr>
                <th data-no-code-services-col="code">Code</th>
                <th data-no-code-services-col="label">Libelle</th>
                <th data-no-code-services-col="status">Statut</th>
                <th data-no-code-services-col="credentials">Identifiants</th>
                <th data-no-code-services-col="fields">Champs</th>
                <th>Actions</th>
            </tr>
        `,
        feedbackId: "modal-service-feedback",
    });
}

function buildNoCodeFieldEditorAccordionMarkup(draft) {
    const fieldKind = normalizeNoCodeKind(draft?.field_kind || "text");
    const sourceKind = normalizeListSourceKind(draft?.list_source_kind || "local");
    const sharedCode = String(draft?.shared_list_code || "").trim().toLowerCase();
    const sharedListOptions = sharedListRows()
        .map((row) => ({
            code: String(row?.code || "").trim().toLowerCase(),
            label: String(row?.label || row?.code || "").trim(),
        }))
        .filter((row) => row.code && row.label)
        .map((row) => `<option value="${escapeHtml(row.code)}" ${row.code === sharedCode ? "selected" : ""}>${escapeHtml(row.label)}</option>`)
        .join("");
    return `
        <div class="type-schema-field-editor">
            <div class="type-schema-field-editor-title">${escapeHtml(draft?.mode === "edit" ? "Modifier le champ" : "Nouveau champ")}</div>
            <div class="type-schema-field-grid">
                <label class="field">
                    <span>Libelle</span>
                    <input id="service-field-label" type="text" value="${escapeHtml(String(draft?.label || ""))}">
                </label>
                <label class="field">
                    <span>Nature</span>
                    <select id="service-field-kind">
                        ${NO_CODE_FIELD_KINDS.map((kind) => `<option value="${escapeHtml(kind)}" ${kind === fieldKind ? "selected" : ""}>${escapeHtml(noCodeKindLabel(kind))}</option>`).join("")}
                    </select>
                </label>
                <label class="field" id="service-field-list-source-wrap" ${fieldKind === "list" ? "" : "hidden"}>
                    <span>Source des valeurs</span>
                    <select id="service-field-list-source">
                        <option value="local" ${sourceKind === "local" ? "selected" : ""}>Liste du service</option>
                        <option value="shared" ${sourceKind === "shared" ? "selected" : ""}>Liste partagee</option>
                    </select>
                </label>
                <label class="field wide" id="service-field-shared-wrap" ${fieldKind === "list" && sourceKind === "shared" ? "" : "hidden"}>
                    <span>Choisir une liste partagee</span>
                    <select id="service-field-shared-list">
                        <option value="">Selectionner une liste partagee</option>
                        ${sharedListOptions}
                    </select>
                </label>
                <label class="field">
                    <span>Valeur par defaut</span>
                    <input id="service-field-default" type="text" value="${escapeHtml(String(draft?.default_value || ""))}">
                </label>
                <label class="field wide" id="service-field-options-wrap" ${fieldKind === "list" && sourceKind === "local" ? "" : "hidden"}>
                    <span>Options (liste, separees par des virgules)</span>
                    <input id="service-field-options" type="text" value="${escapeHtml(String(draft?.options || ""))}">
                </label>
            </div>
            <p class="muted">Liste du service: valeurs stockees dans le service. Liste partagee: valeurs reutilisables dans plusieurs services.</p>
            ${state.noCodeSharedListsWarning ? `<p class="error-text">${escapeHtml(state.noCodeSharedListsWarning)}</p>` : ""}
            ${sharedListOptions ? "" : '<p class="muted">Aucune liste partagee disponible. Creez une liste partagee dans le menu Services.</p>'}
            <label class="check-field">
                <input id="service-field-required" type="checkbox" ${draft?.required ? "checked" : ""}>
                <span>Champ obligatoire</span>
            </label>
            <label class="check-field">
                <input id="service-field-track-history" type="checkbox" ${draft?.track_history ? "checked" : ""}>
                <span>Historiser les changements</span>
            </label>
            <label class="check-field">
                <input id="service-field-inline-editable" type="checkbox" ${draft?.inline_editable ? "checked" : ""}>
                <span>Modifiable directement dans le tableau</span>
            </label>
            <label id="service-field-batch-editable-wrap" class="check-field" ${fieldKind === "list" ? "" : "hidden"}>
                <input id="service-field-batch-editable" type="checkbox" ${draft?.batch_editable ? "checked" : ""}>
                <span>Modifiable par lot</span>
            </label>
            <label class="check-field">
                <input id="service-field-quick-filter" type="checkbox" ${draft?.quick_filter ? "checked" : ""}>
                <span>Filtre rapide dans la vue du module</span>
            </label>
            <div class="type-schema-field-actions">
                ${createActionButtonMarkup({ preset: "cancel", action: "service:field:cancel" })}
                ${createActionButtonMarkup({ preset: "save", type: "button", action: "service:field:save", label: "Enregistrer le champ" })}
            </div>
        </div>
    `;
}

function normalizeNoCodeServiceWizardStep(value) {
    const step = Number(value || 1);
    if (!Number.isFinite(step)) {
        return 1;
    }
    return Math.min(4, Math.max(1, Math.round(step)));
}

function currentNoCodeServiceWizardStep() {
    return normalizeNoCodeServiceWizardStep(state.noCodeServiceEditor?.wizardStep || 1);
}

function syncNoCodeServiceEditorFromForm(form = document.getElementById("modal-service-form")) {
    const editor = state.noCodeServiceEditor;
    if (!editor || !(form instanceof HTMLFormElement)) {
        return;
    }
    const labelInput = form.querySelector('[name="service_label"]');
    if (labelInput instanceof HTMLInputElement) {
        editor.label = normalizeNoCodeText(labelInput.value);
    }
    const childEnabledInput = form.querySelector('[name="service_child_enabled"]');
    if (childEnabledInput instanceof HTMLInputElement) {
        editor.child_enabled = childEnabledInput.checked;
    }
    const childLabelInput = form.querySelector('[name="service_child_label"]');
    if (childLabelInput instanceof HTMLInputElement) {
        editor.child_label = normalizeNoCodeText(childLabelInput.value) || "Elements lies";
    }
    const activeInput = form.querySelector('[name="service_is_active"]');
    if (activeInput instanceof HTMLInputElement) {
        editor.is_active = activeInput.checked;
    }
    const technicalInput = form.querySelector('[name="service_is_technical"]');
    if (technicalInput instanceof HTMLInputElement) {
        editor.is_technical = technicalInput.checked;
    }
    if (editor.is_technical) {
        editor.is_active = true;
    }
    const credentialsInput = form.querySelector('[name="service_credentials_enabled"]');
    if (credentialsInput instanceof HTMLInputElement) {
        editor.credentials_enabled = credentialsInput.checked;
    }
    const iconInput = form.querySelector('[name="service_icon"]');
    if (iconInput instanceof HTMLInputElement) {
        editor.icon = String(iconInput.value || "").trim().toLowerCase();
    }
    const colorInput = form.querySelector('[name="service_color"]');
    if (colorInput instanceof HTMLInputElement) {
        editor.color = sanitizeServiceIconColor(colorInput.value);
    }
    const tileShowCountInput = form.querySelector('[name="service_tile_show_count"]');
    if (tileShowCountInput instanceof HTMLInputElement) {
        editor.tile_config = {
            ...(editor.tile_config || {}),
            show_count: tileShowCountInput.checked,
        };
    }
    const remoteEnabledInput = form.querySelector('[name="service_remote_enabled"]');
    const remoteFieldInput = form.querySelector('[name="service_remote_field"]');
    const remoteSchemeInput = form.querySelector('[name="service_remote_scheme"]');
    const remoteLabelInput = form.querySelector('[name="service_remote_label"]');
    if (remoteEnabledInput instanceof HTMLInputElement) {
        editor.tile_config = {
            ...(editor.tile_config || {}),
            remote_access: {
                enabled: remoteEnabledInput.checked,
                field_key: String(remoteFieldInput?.value || "").trim(),
                scheme: ["http", "https", "url"].includes(String(remoteSchemeInput?.value || "")) ? String(remoteSchemeInput.value) : "url",
                label: normalizeNoCodeText(remoteLabelInput?.value || "") || "Ouvrir l'interface",
            },
        };
    }
}

function noCodeServiceTechnicalCodeDisplay(editor) {
    if (!editor) {
        return "Genere depuis le nom";
    }
    const hasLabel = Boolean(normalizeNoCodeText(editor.label));
    const hasCode = Boolean(String(editor.code || "").trim());
    if (!hasLabel && !hasCode) {
        return "Genere depuis le nom";
    }
    return String(editor.code || slugifyNoCodeIdentifier(editor.label || "", "service")).trim().toLowerCase();
}

function updateNoCodeServiceTechnicalCodeDisplay() {
    const editor = state.noCodeServiceEditor;
    if (!editor) {
        return;
    }
    const display = noCodeServiceTechnicalCodeDisplay(editor);
    const input = document.getElementById("service-technical-code-display");
    if (input instanceof HTMLInputElement) {
        input.value = display;
    }
    const badge = document.getElementById("service-technical-code-badge");
    if (badge instanceof HTMLElement) {
        badge.textContent = display;
    }
}

function renderNoCodeServiceEditorShell() {
    const form = document.getElementById("modal-service-form");
    if (!(form instanceof HTMLFormElement) || !state.noCodeServiceEditor) {
        return;
    }
    const modalBody = form.parentElement;
    if (!(modalBody instanceof HTMLElement)) {
        return;
    }
    modalBody.innerHTML = buildNoCodeServiceEditorMarkup();
    renderNoCodeServiceEditor();
}

function setNoCodeServiceWizardStep(step) {
    const editor = state.noCodeServiceEditor;
    if (!editor) {
        return;
    }
    syncNoCodeServiceEditorFromForm();
    editor.wizardStep = normalizeNoCodeServiceWizardStep(step);
    renderNoCodeServiceEditorShell();
}

function buildNoCodeServiceWizardStepsMarkup(activeStep) {
    return `
        <nav class="no-code-service-wizard-steps" aria-label="Etapes du service">
            ${NO_CODE_SERVICE_WIZARD_STEPS.map((step) => {
                const isActive = step.value === activeStep;
                const isDone = step.value < activeStep;
                return `
                    <button
                        class="no-code-service-wizard-step ${isActive ? "is-active" : ""} ${isDone ? "is-done" : ""}"
                        type="button"
                        data-action="service:wizard:step"
                        data-step="${step.value}"
                        aria-current="${isActive ? "step" : "false"}"
                    >
                        <span>${step.value}</span>
                        <strong>${escapeHtml(step.label)}</strong>
                    </button>
                `;
            }).join("")}
        </nav>
    `;
}

function buildNoCodeServiceIconGalleryMarkup(editor) {
    const selectedIcon = String(editor?.icon || "").trim().toLowerCase();
    const customColor = sanitizeServiceIconColor(editor?.color || "");
    const buttons = SERVICE_ICON_LIBRARY.map((icon) => {
        const isSelected = String(icon.code || "") === selectedIcon;
        const iconMarkup = icon.code ? renderServiceIconSvg(icon.code) : '<span class="no-code-service-icon-none">-</span>';
        return `
            <button class="service-icon-choice ${isSelected ? "is-selected" : ""}" type="button"
                data-action="service:icon:select"
                data-service-icon="${escapeHtml(String(icon.code || ""))}"
                aria-pressed="${isSelected ? "true" : "false"}"
                title="${escapeHtml(icon.label)}">
                ${iconMarkup}
                <span>${escapeHtml(icon.label)}</span>
            </button>
        `;
    }).join("");
    return `
        <section class="no-code-service-icon-section">
            <div class="type-schema-fields-head">
                <div>
                    <h3>Icone de tuile</h3>
                    <p class="muted">Optionnel, utilise pour harmoniser les tuiles du portail.</p>
                </div>
                <div class="service-icon-preview" style="${customColor ? `--service-card-icon-color: ${escapeHtml(customColor)}` : ""}" aria-hidden="true">
                    ${renderServiceIconSvg(selectedIcon) || '<span class="no-code-service-icon-none">-</span>'}
                </div>
            </div>
            <input name="service_icon" type="hidden" value="${escapeHtml(selectedIcon)}">
            <input name="service_color" type="hidden" value="${escapeHtml(customColor)}">
            <div class="service-icon-gallery">
                ${buttons}
            </div>
        </section>
    `;
}

function buildNoCodeServiceIdentityStepMarkup(editor) {
    const serviceCodeDisplay = noCodeServiceTechnicalCodeDisplay(editor);
    const isReservedCode = isReservedSystemEntityCode(editor?.code || serviceCodeDisplay);
    const remoteAccess = editor?.tile_config?.remote_access && typeof editor.tile_config.remote_access === "object" ? editor.tile_config.remote_access : {};
    const remoteEnabled = Boolean(remoteAccess.enabled);
    const remoteFieldKey = String(remoteAccess.field_key || "").trim();
    const remoteScheme = ["http", "https", "url"].includes(String(remoteAccess.scheme || "")) ? String(remoteAccess.scheme) : "url";
    const remoteLabel = String(remoteAccess.label || "Ouvrir l'interface").trim();
    const remoteFieldOptions = (editor?.fields || []).map((field) => {
        const key = String(field?.field_key || "").trim();
        const label = String(field?.label || key).trim();
        return key ? `<option value="${escapeHtml(key)}" ${key === remoteFieldKey ? "selected" : ""}>${escapeHtml(label)}</option>` : "";
    }).join("");
    return `
        <section class="no-code-service-wizard-panel no-code-service-identity-panel">
            <div class="no-code-service-panel-head">
                <div>
                    <h3>Identite du service</h3>
                    <p class="muted">Nom, visibilite et options de base.</p>
                </div>
                <span id="service-technical-code-badge" class="no-code-service-code">${escapeHtml(serviceCodeDisplay)}</span>
            </div>
            <div class="modal-settings-grid">
                ${createFieldMarkup("service_label", "Nom du service", editor.label || "")}
                <label class="field">
                    <span>Code technique</span>
                    <input id="service-technical-code-display" type="text" value="${escapeHtml(serviceCodeDisplay)}" disabled>
                </label>
            </div>
            <details class="no-code-service-advanced-options">
                <summary>Parametres supplementaires</summary>
                <div class="no-code-service-option-grid">
                    <label class="check-field">
                        <input name="service_is_technical" type="checkbox" ${editor.is_technical ? "checked" : ""}>
                        <span>Module technique</span>
                        <small>Actif pour les relations, mais masque par defaut sur le dashboard. Il peut etre affiche manuellement depuis la personnalisation du dashboard.</small>
                    </label>
                    <label class="check-field">
                        <input name="service_is_active" type="checkbox" ${(editor.is_technical || editor.is_active) ? "checked" : ""} ${editor.is_technical ? "disabled" : ""}>
                        <span>${editor.is_technical ? "Service actif (requis pour un module technique)" : "Service actif dans le portail"}</span>
                    </label>
                    ${isReservedCode ? `<p class="muted no-code-service-system-note">Nom reserve : ce referentiel existe comme module systeme, pas comme service personnalise.</p>` : ""}
                    <label class="check-field">
                        <input name="service_credentials_enabled" type="checkbox" ${editor.credentials_enabled ? "checked" : ""}>
                        <span>Identifiants login et mot de passe</span>
                    </label>
                    <label class="check-field">
                        <input name="service_tile_show_count" type="checkbox" ${editor.tile_config?.show_count !== false ? "checked" : ""}>
                        <span>Afficher le nombre de fiches sur la tuile</span>
                    </label>
                    <label class="check-field">
                        <input name="service_remote_enabled" type="checkbox" ${remoteEnabled ? "checked" : ""}>
                        <span>Acces distant depuis la fiche</span>
                        <small>Affiche un lien uniquement lorsque le champ choisi est renseigne.</small>
                    </label>
                    <div id="service-remote-options" class="no-code-service-option-grid" ${remoteEnabled ? "" : "hidden"}>
                        <label class="field">
                            <span>Champ de destination</span>
                            <select name="service_remote_field"><option value="">Choisir un champ</option>${remoteFieldOptions}</select>
                        </label>
                        <label class="field">
                            <span>Type de lien</span>
                            <select name="service_remote_scheme">
                                <option value="url" ${remoteScheme === "url" ? "selected" : ""}>URL complete (http:// ou https://)</option>
                                <option value="http" ${remoteScheme === "http" ? "selected" : ""}>Adresse IP / hote en HTTP</option>
                                <option value="https" ${remoteScheme === "https" ? "selected" : ""}>Adresse IP / hote en HTTPS</option>
                            </select>
                        </label>
                        <label class="field"><span>Libelle du bouton</span><input name="service_remote_label" value="${escapeHtml(remoteLabel)}"></label>
                    </div>
                </div>
            </details>
            ${isReservedCode ? "" : buildNoCodeServiceIconGalleryMarkup(editor)}
        </section>
    `;
}

function buildNoCodeServiceFieldsStepMarkup(editor) {
    const exportActionMarkup = editor.mode === "edit" && editor.code
        ? createActionButtonMarkup({
            preset: "export",
            action: "service:field:export",
            label: "Exporter CSV",
            title: "Exporter les champs au format CSV",
        })
        : "";
    const addFieldButtonMarkup = createActionButtonMarkup({
        className: "toolbar-btn",
        action: "service:field:add",
        label: "Ajouter un champ",
        title: "Ajouter un champ",
        iconHtml: "+",
    });
    return `
        <section class="no-code-service-wizard-panel type-schema-fields-section">
            <div class="type-schema-fields-head">
                <div>
                    <h3>Champs de la fiche</h3>
                    <p class="muted">Structure des donnees du service.</p>
                </div>
                <div class="inventory-row-actions">
                    ${exportActionMarkup}
                    ${createActionButtonMarkup({
                        preset: "import",
                        className: "toolbar-btn",
                        action: "service:field:import",
                        label: "Importer fichier",
                        title: "Importer un fichier CSV ou XLSX",
                    })}
                    ${createActionButtonMarkup({
                        className: "toolbar-btn",
                        action: "service:field:ad-source",
                        label: "Source AD",
                        title: "Utiliser Active Directory comme source de champs",
                    })}
                    ${addFieldButtonMarkup}
                </div>
            </div>
            <div id="service-import-preview-wrap" hidden></div>
            <div id="service-field-list" class="type-schema-custom-fields-list"></div>
            <div class="inventory-row-actions type-schema-field-bottom-actions">
                ${addFieldButtonMarkup}
            </div>
        </section>
    `;
}

function buildServiceFieldImportPreviewTreeMarkup(fields = []) {
    const rows = (Array.isArray(fields) ? fields : []).map((field, index) => {
        const label = String(field?.label || field?.field_key || `Champ ${index + 1}`).trim();
        const fieldKey = String(field?.field_key || "").trim();
        const kind = noCodeKindLabel(String(field?.field_kind || "text"));
        const options = parseNoCodeOptions(field?.options || "");
        const optionsLabel = options.length
            ? options.slice(0, 8).join(", ") + (options.length > 8 ? ` (+${options.length - 8})` : "")
            : "-";
        return `
            <tr>
                <td class="muted">${index + 1}</td>
                <td>
                    <strong>${escapeHtml(label)}</strong>
                    <span class="muted">${escapeHtml(fieldKey || "-")}</span>
                </td>
                <td>${escapeHtml(kind)}</td>
                <td>${field?.required ? "Oui" : "Non"}</td>
                <td>${escapeHtml(optionsLabel)}</td>
            </tr>
        `;
    }).join("");
    return `
        <div class="table-wrap shared-treeview-table-wrap service-import-preview-tree">
            <table class="device-table shared-treeview-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Champ</th>
                        <th>Type</th>
                        <th>Obligatoire</th>
                        <th>Options</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows || '<tr class="shared-treeview-empty"><td colspan="5">Aucun champ propose.</td></tr>'}
                </tbody>
            </table>
        </div>
    `;
}

function noCodePreviewValueForKind(fieldKind) {
    const kind = normalizeNoCodeKind(fieldKind || "text");
    if (kind === "date") {
        return "2026-06-24";
    }
    if (kind === "ip") {
        return "192.168.1.10";
    }
    if (kind === "url") {
        return "https://...";
    }
    if (kind === "list") {
        return "Valeur";
    }
    return "Texte";
}

function noCodeRelationDrafts(editor) {
    return Array.isArray(editor?.relationDrafts) ? editor.relationDrafts : [];
}

function noCodeRelationCurrentServiceCode(editor) {
    return String(editor?.code || noCodeServiceTechnicalCodeDisplay(editor) || "").trim().toLowerCase();
}

function noCodeRelationAvailableServices(editor) {
    const currentCode = noCodeRelationCurrentServiceCode(editor);
    return [...NO_CODE_RELATION_SYSTEM_ENTITIES, ...noCodeServiceRows()]
        .filter((service) => {
            const code = String(service?.code || "").trim().toLowerCase();
            return code && code !== "monitoring" && code !== currentCode;
        })
        .sort((left, right) => String(left?.label || left?.code || "").localeCompare(String(right?.label || right?.code || ""), undefined, { sensitivity: "base" }));
}

function noCodeRelationNodeCodes(editor) {
    const currentCode = noCodeRelationCurrentServiceCode(editor);
    const codes = new Set(currentCode ? [currentCode] : []);
    const canvasState = editor?.relationCanvas && typeof editor.relationCanvas === "object" ? editor.relationCanvas : {};
    const nodePositions = canvasState.nodes && typeof canvasState.nodes === "object" ? canvasState.nodes : {};
    Object.keys(nodePositions).forEach((code) => {
        const normalized = String(code || "").trim().toLowerCase();
        if (normalized) {
            codes.add(normalized);
        }
    });
    noCodeRelationDrafts(editor).forEach((relation) => {
        const source = String(relation?.source_service_code || "").trim().toLowerCase();
        const target = normalizeNoCodeRelationEntityCode(relation?.target_service_code || relation?.service_code || "");
        if (source) {
            codes.add(source);
        }
        if (target) {
            codes.add(target);
        }
    });
    return [...codes].filter(Boolean);
}

function noCodeRelationNodePosition(editor, serviceCode, index = 0) {
    const code = normalizeNoCodeRelationEntityCode(serviceCode);
    const canvasState = editor?.relationCanvas && typeof editor.relationCanvas === "object" ? editor.relationCanvas : {};
    if (code === noCodeRelationCurrentServiceCode(editor)) {
        return {
            x: Number.isFinite(Number(canvasState.currentX)) ? Number(canvasState.currentX) : 36,
            y: Number.isFinite(Number(canvasState.currentY)) ? Number(canvasState.currentY) : 176,
        };
    }
    const nodePositions = canvasState.nodes && typeof canvasState.nodes === "object" ? canvasState.nodes : {};
    const saved = nodePositions[code] && typeof nodePositions[code] === "object" ? nodePositions[code] : {};
    const relation = noCodeRelationDrafts(editor).find((item) => normalizeNoCodeRelationEntityCode(item?.target_service_code || item?.service_code || "") === code);
    return {
        x: Number.isFinite(Number(saved.x)) ? Number(saved.x) : (Number.isFinite(Number(relation?.x ?? relation?.target_x)) ? Number(relation.x ?? relation.target_x) : 430),
        y: Number.isFinite(Number(saved.y)) ? Number(saved.y) : (Number.isFinite(Number(relation?.y ?? relation?.target_y)) ? Number(relation.y ?? relation.target_y) : 34 + (Math.max(0, index - 1) * 152)),
    };
}

function setNoCodeRelationNodePosition(editor, serviceCode, x, y) {
    const code = normalizeNoCodeRelationEntityCode(serviceCode);
    if (!editor || !code) {
        return;
    }
    editor.relationCanvas = editor.relationCanvas && typeof editor.relationCanvas === "object" ? editor.relationCanvas : {};
    if (code === noCodeRelationCurrentServiceCode(editor)) {
        editor.relationCanvas.currentX = x;
        editor.relationCanvas.currentY = y;
        noCodeRelationDrafts(editor).forEach((relation) => {
            if (String(relation?.source_service_code || "").trim().toLowerCase() === code) {
                relation.source_x = x;
                relation.source_y = y;
            }
        });
        return;
    }
    editor.relationCanvas.nodes = editor.relationCanvas.nodes && typeof editor.relationCanvas.nodes === "object" ? editor.relationCanvas.nodes : {};
    editor.relationCanvas.nodes[code] = { x, y };
    noCodeRelationDrafts(editor).forEach((relation) => {
        if (normalizeNoCodeRelationEntityCode(relation?.target_service_code || relation?.service_code || "") === code) {
            relation.target_x = x;
            relation.target_y = y;
            relation.x = x;
            relation.y = y;
        }
    });
}

function removeNoCodeRelationCanvasNode(editor, serviceCode) {
    const code = normalizeNoCodeRelationEntityCode(serviceCode);
    const currentCode = noCodeRelationCurrentServiceCode(editor);
    if (!editor || !code || code === currentCode) {
        return 0;
    }
    const beforeCount = noCodeRelationDrafts(editor).length;
    editor.relationDrafts = noCodeRelationDrafts(editor).filter((relation) => {
        const sourceCode = String(relation?.source_service_code || "").trim().toLowerCase();
        const targetCode = normalizeNoCodeRelationEntityCode(relation?.target_service_code || relation?.service_code || "");
        return sourceCode !== code && targetCode !== code;
    });
    editor.relationCanvas = editor.relationCanvas && typeof editor.relationCanvas === "object" ? editor.relationCanvas : {};
    if (editor.relationCanvas.nodes && typeof editor.relationCanvas.nodes === "object") {
        delete editor.relationCanvas.nodes[code];
    }
    if (String(editor.selectedRelationServiceCode || "").trim().toLowerCase() === code) {
        editor.selectedRelationServiceCode = "";
    }
    const selectedRelation = selectedNoCodeRelationDraft(editor);
    if (!selectedRelation) {
        editor.selectedRelationId = "";
    }
    return beforeCount - noCodeRelationDrafts(editor).length;
}

function noCodeRelationId(relation, index = 0) {
    const explicit = String(relation?.relation_id || relation?.client_id || relation?.id || "").trim();
    if (explicit) {
        return explicit;
    }
    const source = String(relation?.source_service_code || "").trim().toLowerCase();
    const target = normalizeNoCodeRelationEntityCode(relation?.target_service_code || relation?.service_code || "");
    const cardinality = normalizeNoCodeRelationCardinality(relation?.cardinality || relation?.relation_type || "many_to_one");
    const direction = normalizeNoCodeRelationDirection(relation?.direction || "out");
    return `${source || "source"}:${target || "target"}:${cardinality}:${direction}:${index}`;
}

function findNoCodeRelationDraftById(editor, relationId) {
    const wanted = String(relationId || "").trim();
    if (!wanted) {
        return null;
    }
    return noCodeRelationDrafts(editor).find((relation, index) => noCodeRelationId(relation, index) === wanted) || null;
}

function findNoCodeRelationDraft(editor, serviceCode) {
    const wanted = normalizeNoCodeRelationEntityCode(serviceCode);
    if (!wanted) {
        return null;
    }
    return noCodeRelationDrafts(editor).find((relation) => {
        const source = String(relation?.source_service_code || "").trim().toLowerCase();
        const target = normalizeNoCodeRelationEntityCode(relation?.target_service_code || relation?.service_code || "");
        return source === wanted || target === wanted;
    }) || null;
}

function selectedNoCodeRelationDraft(editor) {
    const selectedId = String(editor?.selectedRelationId || "").trim();
    if (selectedId) {
        const byId = findNoCodeRelationDraftById(editor, selectedId);
        if (byId) {
            return byId;
        }
    }
    return findNoCodeRelationDraft(editor, editor?.selectedRelationServiceCode || "");
}

function noCodeRelationIsReadonly(editor, relation) {
    const currentCode = noCodeRelationCurrentServiceCode(editor);
    const sourceCode = String(relation?.source_service_code || currentCode).trim().toLowerCase();
    return Boolean(relation?.is_readonly_relation) || (sourceCode && sourceCode !== currentCode);
}

function normalizeNoCodeRelationCardinality(value) {
    const raw = String(value || "").trim().toLowerCase().replaceAll("-", "_");
    if (["reference", "many_one", "many_to_one", "n_1"].includes(raw)) {
        return "many_to_one";
    }
    if (["one_one", "one_to_one", "1_1"].includes(raw)) {
        return "one_to_one";
    }
    if (["one_many", "one_to_many", "1_n"].includes(raw)) {
        return "one_to_many";
    }
    if (["many_many", "many_to_many", "n_n"].includes(raw)) {
        return "many_to_many";
    }
    return "many_to_one";
}

function normalizeNoCodeRelationDirection(value) {
    return String(value || "").trim().toLowerCase() === "in" ? "in" : "out";
}

function createNoCodeRelationDraft(service, index = 0, sourceServiceCode = "") {
    const code = normalizeNoCodeRelationEntityCode(service?.code || "");
    const label = String(service?.label || code || "Service lie").trim();
    const source = String(sourceServiceCode || state.noCodeServiceEditor?.code || noCodeServiceTechnicalCodeDisplay(state.noCodeServiceEditor)).trim().toLowerCase();
    const x = 430;
    const y = 34 + (Math.max(0, Number(index || 0)) * 152);
    return {
        client_id: `rel_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
        source_service_code: source,
        target_service_code: code,
        service_code: code,
        label,
        display_label: label,
        verb: "est lie a",
        cardinality: "many_to_one",
        relation_type: "many_to_one",
        direction: "out",
        required: false,
        is_active: true,
        source_x: 36,
        source_y: 176,
        target_x: x,
        target_y: y,
        x,
        y,
        sort_order: (Number(index || 0) + 1) * 10,
    };
}

function noCodeRelationTypeLabel(type) {
    const value = normalizeNoCodeRelationCardinality(type);
    if (value === "one_to_one") {
        return "Un seul de chaque cote";
    }
    if (value === "one_to_many") {
        return "Un vers plusieurs";
    }
    if (value === "many_to_many") {
        return "Plusieurs vers plusieurs";
    }
    return "Un vers un autre";
}

function pluralizeNoCodeRelationLabel(label) {
    const value = String(label || "").trim();
    if (!value) {
        return "elements";
    }
    if (/[sxz]$/i.test(value)) {
        return value;
    }
    return `${value}s`;
}

function noCodeRelationServiceLabels(editor, relation) {
    const sourceCode = String(relation?.source_service_code || noCodeRelationCurrentServiceCode(editor)).trim().toLowerCase();
    const targetCode = normalizeNoCodeRelationEntityCode(relation?.target_service_code || relation?.service_code || "");
    const sourceService = findNoCodeRelationEntity(sourceCode) || { label: editor?.label || sourceCode || "Service source" };
    const targetService = findNoCodeRelationEntity(targetCode) || relation || { label: targetCode || "service cible" };
    const labels = {
        source: String(sourceService?.label || sourceCode || "Service source").trim(),
        target: String(targetService?.label || targetCode || "service cible").trim(),
    };
    if (normalizeNoCodeRelationDirection(relation?.direction || "out") === "in") {
        return {
            source: labels.target,
            target: labels.source,
        };
    }
    return labels;
}

function noCodeRelationAbilityVerb(verb) {
    const raw = String(verb || "").trim();
    const normalized = raw.toLowerCase();
    const aliases = {
        "est lie a": "etre lie a",
        "appartient a": "appartenir a",
        "contient": "contenir",
        "est gere par": "etre gere par",
        "est localise sur": "etre localise sur",
        "utilise": "utiliser",
        "concerne": "concerner",
    };
    return aliases[normalized] || raw;
}

function noCodeRelationCardinalityTitle(editor, relation, type) {
    const labels = noCodeRelationServiceLabels(editor, relation);
    const verb = noCodeRelationAbilityVerb(relation?.verb || "est lie a");
    const value = normalizeNoCodeRelationCardinality(type);
    if (value === "one_to_one") {
        return `Un ${labels.source} peut ${verb} un seul ${labels.target}.`;
    }
    if (value === "one_to_many") {
        return `Un ${labels.source} peut ${verb} plusieurs ${pluralizeNoCodeRelationLabel(labels.target)}.`;
    }
    if (value === "many_to_many") {
        return `Un ${labels.source} peut ${verb} plusieurs ${pluralizeNoCodeRelationLabel(labels.target)}, et inversement.`;
    }
    return `Un ${labels.source} peut ${verb} un ${labels.target}.`;
}

function noCodeRelationNaturalPhrase(editor, relation) {
    if (!relation) {
        return "Selectionne un lien pour afficher son explication.";
    }
    const verb = noCodeRelationAbilityVerb(relation.verb || "est lie a");
    const labels = noCodeRelationServiceLabels(editor, relation);
    const cardinality = normalizeNoCodeRelationCardinality(relation.cardinality || relation.relation_type);
    if (cardinality === "one_to_one") {
        return `Un ${labels.source} peut ${verb} un seul ${labels.target}. Un ${labels.target} ne sera relie qu'a un seul ${labels.source}.`;
    }
    if (cardinality === "one_to_many") {
        return `Un ${labels.source} peut ${verb} plusieurs ${pluralizeNoCodeRelationLabel(labels.target)}. Chaque ${labels.target} reste rattache a ce ${labels.source}.`;
    }
    if (cardinality === "many_to_many") {
        return `Un ${labels.source} peut ${verb} plusieurs ${pluralizeNoCodeRelationLabel(labels.target)}, et un ${labels.target} peut aussi etre relie a plusieurs ${pluralizeNoCodeRelationLabel(labels.source)}.`;
    }
    return `Un ${labels.source} peut ${verb} un ${labels.target}. Plusieurs ${pluralizeNoCodeRelationLabel(labels.source)} peuvent etre relies a des ${pluralizeNoCodeRelationLabel(labels.target)} differents.`;
}

function updateNoCodeRelationNaturalPhrasePreview(relation) {
    const editor = state.noCodeServiceEditor;
    const node = document.querySelector(".no-code-relation-natural");
    if (!editor || !(node instanceof HTMLElement)) {
        return;
    }
    node.textContent = noCodeRelationNaturalPhrase(editor, relation || selectedNoCodeRelationDraft(editor));
}

function noCodeRelationApiPayload(relation, {
    index = 0,
    sourceX,
    sourceY,
    targetX,
    targetY,
} = {}) {
    const targetCode = normalizeNoCodeRelationEntityCode(relation?.target_service_code || relation?.service_code || "");
    const resolvedTargetX = Math.round(Number(targetX ?? relation?.target_x ?? relation?.x ?? 0));
    const resolvedTargetY = Math.round(Number(targetY ?? relation?.target_y ?? relation?.y ?? 0));
    const recordDisplayMode = String(relation?.record_display_mode || "").trim().toLowerCase();
    return {
        target_service_code: targetCode,
        service_code: targetCode,
        verb: String(relation?.verb || "est lie a").trim() || "est lie a",
        cardinality: normalizeNoCodeRelationCardinality(relation?.cardinality || relation?.relation_type || "many_to_one"),
        relation_type: normalizeNoCodeRelationCardinality(relation?.cardinality || relation?.relation_type || "many_to_one"),
        direction: normalizeNoCodeRelationDirection(relation?.direction || "out"),
        display_label: String(relation?.display_label || relation?.label || "").trim(),
        label: String(relation?.display_label || relation?.label || "").trim(),
        required: Boolean(relation?.required),
        is_active: relation?.is_active !== false,
        filter_candidates_by_shared_relation: Boolean(relation?.filter_candidates_by_shared_relation),
        show_indirect_relations: Boolean(relation?.show_indirect_relations),
        record_display_mode: ["standard", "hidden", "assignment"].includes(recordDisplayMode) ? recordDisplayMode : "standard",
        assignment_resource_service_code: normalizeNoCodeRelationEntityCode(relation?.assignment_resource_service_code || ""),
        unique_value_field_key: String(relation?.unique_value_field_key || "").trim().toLowerCase(),
        source_x: Math.round(Number(sourceX ?? relation?.source_x ?? 0)),
        source_y: Math.round(Number(sourceY ?? relation?.source_y ?? 0)),
        target_x: resolvedTargetX,
        target_y: resolvedTargetY,
        x: resolvedTargetX,
        y: resolvedTargetY,
        sort_order: Number(relation?.sort_order || ((index + 1) * 10)),
    };
}

function noCodeRelationApiPayloads(editor) {
    const currentCode = noCodeRelationCurrentServiceCode(editor);
    const nodeCodes = noCodeRelationNodeCodes(editor);
    return noCodeRelationDrafts(editor)
        .filter((relation) => String(relation?.source_service_code || currentCode).trim().toLowerCase() === currentCode)
        .map((relation, index) => {
            const sourceCode = String(relation?.source_service_code || currentCode).trim().toLowerCase();
            const targetCode = normalizeNoCodeRelationEntityCode(relation?.target_service_code || relation?.service_code || "");
            const sourcePos = noCodeRelationNodePosition(editor, sourceCode, nodeCodes.indexOf(sourceCode));
            const targetPos = noCodeRelationNodePosition(editor, targetCode, nodeCodes.indexOf(targetCode));
            return noCodeRelationApiPayload(relation, {
                index,
                sourceX: sourcePos.x,
                sourceY: sourcePos.y,
                targetX: targetPos.x || relation?.target_x || relation?.x || 0,
                targetY: targetPos.y || relation?.target_y || relation?.y || 0,
            });
        })
        .filter((relation) => relation.target_service_code && relation.target_service_code !== currentCode);
}

function buildNoCodeRelationFieldsMarkup(fields = []) {
    const rows = (Array.isArray(fields) ? fields : []).slice(0, 5);
    if (!rows.length) {
        return '<li class="muted">Aucun champ</li>';
    }
    return rows.map((field) => {
        const label = String(field?.label || field?.field_key || "").trim();
        const kind = noCodeKindLabel(field?.field_kind || "text");
        return `<li><span>${escapeHtml(label || "Champ")}</span><em>${escapeHtml(kind)}</em></li>`;
    }).join("");
}

function normalizeNoCodeRelationZoom(value) {
    const parsed = Number(value || 1);
    if (!Number.isFinite(parsed)) {
        return 1;
    }
    return Math.max(0.5, Math.min(1.6, Math.round(parsed * 100) / 100));
}

function buildNoCodeRelationCanvasBlockMarkup({ service, fields, current = false, selected = false, top = 0, left = 0 }) {
    const code = String(service?.code || "").trim().toLowerCase();
    const label = String(service?.label || code || "Service").trim();
    const style = `left:${Math.round(left)}px;top:${Math.round(top)}px;`;
    return `
        <button
            type="button"
            class="no-code-relation-node ${current ? "is-current" : ""} ${selected ? "is-selected" : ""}"
            style="${style}"
            data-relation-node="${escapeHtml(code)}"
            data-action="service:relation:node-select"
            data-service-code="${escapeHtml(code)}"
        >
            <span class="no-code-relation-port no-code-relation-port-left" data-relation-port="left" data-service-code="${escapeHtml(code)}" aria-hidden="true"></span>
            <span class="no-code-relation-port no-code-relation-port-right" data-relation-port="right" data-service-code="${escapeHtml(code)}" aria-hidden="true"></span>
            <strong>${escapeHtml(label)}</strong>
            <small>${current ? "Service courant" : escapeHtml(code)}</small>
            <ul>${buildNoCodeRelationFieldsMarkup(fields)}</ul>
        </button>
    `;
}

function buildNoCodeRelationCanvasMarkup(editor) {
    const canvasState = editor?.relationCanvas && typeof editor.relationCanvas === "object" ? editor.relationCanvas : {};
    const zoom = normalizeNoCodeRelationZoom(canvasState.zoom || 1);
    const currentCode = noCodeRelationCurrentServiceCode(editor);
    const currentService = {
        code: currentCode,
        label: editor?.label || "Service en creation",
    };
    const relations = noCodeRelationDrafts(editor);
    const selectedRelation = selectedNoCodeRelationDraft(editor);
    const selectedRelationId = selectedRelation ? noCodeRelationId(selectedRelation, relations.indexOf(selectedRelation)) : "";
    const selectedCode = String(editor?.selectedRelationServiceCode || "").trim().toLowerCase();
    const nodeCodes = noCodeRelationNodeCodes(editor);
    const relationNodes = nodeCodes.map((code, index) => {
        const service = code === currentCode ? currentService : (findNoCodeRelationEntity(code) || { code, label: code });
        const position = noCodeRelationNodePosition(editor, code, index);
        return buildNoCodeRelationCanvasBlockMarkup({
            service,
            fields: code === currentCode ? editor?.fields || [] : noCodeRelationEntityFields(service),
            current: code === currentCode,
            selected: code === selectedCode,
            top: position.y,
            left: position.x,
        });
    }).join("");
    const paths = relations.map((relation, index) => {
        const sourceCode = String(relation.source_service_code || currentCode).trim().toLowerCase();
        const targetCode = normalizeNoCodeRelationEntityCode(relation.target_service_code || relation.service_code || "");
        const sourcePos = noCodeRelationNodePosition(editor, sourceCode, nodeCodes.indexOf(sourceCode));
        const targetPos = noCodeRelationNodePosition(editor, targetCode, nodeCodes.indexOf(targetCode));
        const sourceX = sourcePos.x + 250;
        const sourceY = sourcePos.y + 70;
        const targetX = targetPos.x;
        const targetY = targetPos.y + 70;
        const midX = Math.round((sourceX + targetX) / 2);
        const pathD = `M ${sourceX} ${sourceY} C ${midX} ${sourceY} ${midX} ${targetY} ${targetX} ${targetY}`;
        const relationId = noCodeRelationId(relation, index);
        const isSelected = relationId === selectedRelationId;
        const labelX = Math.round((sourceX + targetX) / 2);
        const labelY = Math.round((sourceY + targetY) / 2) - 8;
        const label = String(relation.verb || "est lie a").trim();
        return `
            <g class="no-code-relation-link ${isSelected ? "is-selected" : ""}" data-action="service:relation:select-link" data-relation-id="${escapeHtml(relationId)}">
                <path class="no-code-relation-hit" d="${pathD}"></path>
                <path class="no-code-relation-path" d="${pathD}"></path>
                <text class="no-code-relation-label" x="${labelX}" y="${labelY}">${escapeHtml(label)}</text>
            </g>
        `;
    }).join("");
    const connect = state.noCodeRelationConnect;
    const tempLine = connect?.active
        ? `<line class="no-code-relation-temp-line" x1="${Number(connect.x1 || 0)}" y1="${Number(connect.y1 || 0)}" x2="${Number(connect.x2 || connect.x1 || 0)}" y2="${Number(connect.y2 || connect.y1 || 0)}"></line>`
        : "";
    return `
        <div class="no-code-relations-canvas" role="img" aria-label="Apercu des relations du service">
            <div class="no-code-relations-canvas-tools" aria-label="Outils canvas">
                ${createActionButtonMarkup({ className: "toolbar-btn", action: "service:relation:zoom-out", label: "-", title: "Dezoomer" })}
                <span>${Math.round(zoom * 100)}%</span>
                ${createActionButtonMarkup({ className: "toolbar-btn", action: "service:relation:zoom-in", label: "+", title: "Zoomer" })}
                ${createActionButtonMarkup({ className: "toolbar-btn", action: "service:relation:center", label: "Recentrer" })}
            </div>
            <div class="no-code-relations-stage" data-relation-stage="1" style="transform:scale(${zoom});">
                <svg class="no-code-relation-lines" viewBox="0 0 920 620" aria-hidden="true">
                    <defs>
                        <marker id="no-code-relation-arrow" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                            <path d="M 0 1.5 L 10 5 L 0 8.5 z"></path>
                        </marker>
                    </defs>
                    ${paths}
                    ${tempLine}
                </svg>
                ${relationNodes}
                ${relations.length ? "" : '<div class="no-code-relations-empty-canvas">Ajoute un service depuis la liste puis relie deux pastilles pour creer une relation.</div>'}
            </div>
        </div>
    `;
}

function buildNoCodeRelationPaletteMarkup(editor) {
    const nodes = new Set(noCodeRelationNodeCodes(editor));
    const services = noCodeRelationAvailableServices(editor);
    const rows = services.map((service) => {
        const code = normalizeNoCodeRelationEntityCode(service?.code || "");
        const label = String(service?.label || code).trim();
        const fieldsCount = noCodeRelationEntityFields(service).length;
        const alreadyLinked = nodes.has(code);
        return `
            <button
                type="button"
                class="no-code-relation-service-option ${alreadyLinked ? "is-linked" : ""}"
                data-action="${alreadyLinked ? "service:relation:select" : "service:relation:add"}"
                data-service-code="${escapeHtml(code)}"
                draggable="true"
            >
                <strong>${escapeHtml(label)}</strong>
                <span>${escapeHtml(service?.relation_kind === "system" ? "Entite systeme" : `${fieldsCount} champ(s)`)}</span>
            </button>
        `;
    }).join("");
    return `
        <aside class="no-code-relations-palette">
            <h4>Services</h4>
            <div class="no-code-relations-service-list">
                ${rows || '<p class="muted">Aucun autre service disponible.</p>'}
            </div>
        </aside>
    `;
}

async function prepareNoCodeRelationAssignment(editor, relation, {
    uniqueFieldKey = "",
    resourceOwnerCardinality = "many_to_one",
    resourceBeneficiaryCardinality = "many_to_one",
} = {}) {
    const relationId = noCodeRelationId(relation, noCodeRelationDrafts(editor).indexOf(relation));
    const sourceCode = String(relation?.source_service_code || noCodeRelationCurrentServiceCode(editor)).trim().toLowerCase();
    const targetCode = normalizeNoCodeRelationEntityCode(relation?.target_service_code || relation?.service_code || "");
    const resourceCode = normalizeNoCodeRelationEntityCode(relation?.assignment_resource_service_code || "");
    if (!sourceCode || !targetCode || !resourceCode) {
        setNoCodeRelationAssignmentFeedback(editor, relationId, "Choisissez d'abord l'element attribue.");
        renderNoCodeServiceEditorShell();
        return;
    }
    const resourceRelations = await fetchNoCodeServiceRelations(resourceCode);
    const sourceService = findNoCodeRelationEntity(sourceCode) || { label: sourceCode };
    const targetService = findNoCodeRelationEntity(targetCode) || { label: targetCode };
    const requiredRelations = [
        {
            target_service_code: sourceCode,
            verb: "est lie a",
            cardinality: normalizeNoCodeRelationCardinality(resourceOwnerCardinality),
            relation_type: normalizeNoCodeRelationCardinality(resourceOwnerCardinality),
            direction: "out",
            display_label: String(sourceService.label || sourceCode),
            required: true,
            unique_value_field_key: String(uniqueFieldKey || "").trim().toLowerCase(),
        },
        {
            target_service_code: targetCode,
            verb: "est attribue a",
            cardinality: normalizeNoCodeRelationCardinality(resourceBeneficiaryCardinality),
            relation_type: normalizeNoCodeRelationCardinality(resourceBeneficiaryCardinality),
            direction: "out",
            display_label: String(targetService.label || targetCode),
            required: false,
            filter_candidates_by_shared_relation: true,
        },
    ];
    const expectedByTarget = new Map(requiredRelations.map((expected) => [expected.target_service_code, expected]));
    const existingOutgoingRelations = resourceRelations.filter((existing) =>
        String(existing?.source_service_code || "").trim().toLowerCase() === resourceCode,
    );
    const unchangedRelations = existingOutgoingRelations.filter((existing) =>
        !expectedByTarget.has(String(existing?.target_service_code || "").trim().toLowerCase()),
    );
    const alignedRelations = requiredRelations.map((expected, index) => {
        const existing = existingOutgoingRelations.find((item) =>
            String(item?.target_service_code || "").trim().toLowerCase() === expected.target_service_code,
        );
        return {
            ...(existing || {}),
            ...expected,
            source_service_code: resourceCode,
            sort_order: Number(existing?.sort_order || ((index + 1) * 10)),
        };
    });
    const relationPayloads = [...unchangedRelations, ...alignedRelations]
        .map((item, index) => noCodeRelationApiPayload(item, { index }));
    try {
        await replaceNoCodeServiceRelations(resourceCode, relationPayloads);
    } catch (error) {
        const confirmed = await confirmNoCodeLinkedRelationsDeletion(resourceCode, error);
        if (!confirmed) {
            throw error;
        }
        await replaceNoCodeServiceRelations(resourceCode, relationPayloads, {
            allowLinkedRelationDeletion: true,
        });
    }
    setNoCodeRelationAssignmentFeedback(editor, relationId,
        "Les relations techniques ont ete alignees avec les reponses de l'assistant. Enregistrez maintenant ce module.");
    renderNoCodeServiceEditorShell();
}

function linkedNoCodeRelationIdsFromReplaceError(error) {
    const message = String(error?.message || error || "");
    return Array.from(message.matchAll(/#(\d+)\s*:\s*\d+\s+lien\(s\)/gi))
        .map((match) => Number(match[1] || 0))
        .filter((relationId, index, values) => relationId > 0 && values.indexOf(relationId) === index);
}

async function confirmNoCodeLinkedRelationsDeletion(serviceCode, error) {
    const relationIds = linkedNoCodeRelationIdsFromReplaceError(error);
    if (!relationIds.length) {
        return false;
    }
    const impacts = await Promise.all(relationIds.map((relationId) =>
        fetchNoCodeRelationImpact(serviceCode, relationId).catch(() => null),
    ));
    const details = impacts.filter(Boolean).map((impact) => {
        const source = findNoCodeRelationEntity(impact.source_service_code)?.label || impact.source_service_code;
        const target = findNoCodeRelationEntity(impact.target_service_code)?.label || impact.target_service_code;
        return `${source} → ${target} : ${Number(impact.link_count || 0)} lien(s) seront supprimes.`;
    });
    if (!details.length) {
        return false;
    }
    return showItopsConfirm({
        title: "Relations deja utilisees",
        message: "La nouvelle configuration remplace des relations qui contiennent encore des liens entre fiches.",
        details: [
            ...details,
            "Cette action supprime uniquement les liens listes ci-dessus, pas les fiches elles-memes.",
        ],
        confirmLabel: "Appliquer et supprimer les liens",
        cancelLabel: "Conserver les liens",
        danger: true,
    });
}

function setNoCodeRelationAssignmentFeedback(editor, relationId, message) {
    const feedbacks = editor?.assignmentAssistantFeedbacks && typeof editor.assignmentAssistantFeedbacks === "object"
        ? editor.assignmentAssistantFeedbacks
        : {};
    editor.assignmentAssistantFeedbacks = { ...feedbacks, [String(relationId || "")]: String(message || "") };
}

function buildNoCodeRelationPropertiesMarkup(editor) {
    const selectedRelation = selectedNoCodeRelationDraft(editor);
    const sourceCode = String(selectedRelation?.source_service_code || noCodeRelationCurrentServiceCode(editor)).trim().toLowerCase();
    const targetCode = normalizeNoCodeRelationEntityCode(selectedRelation?.target_service_code || selectedRelation?.service_code || "");
    const sourceService = findNoCodeRelationEntity(sourceCode) || { code: sourceCode, label: editor?.label || sourceCode };
    const targetService = findNoCodeRelationEntity(targetCode) || selectedRelation || { code: targetCode, label: targetCode };
    const selectedRelationId = selectedRelation ? noCodeRelationId(selectedRelation, noCodeRelationDrafts(editor).indexOf(selectedRelation)) : "";
    const relationVerb = String(selectedRelation?.verb || "est lie a").trim();
    const cardinality = normalizeNoCodeRelationCardinality(selectedRelation?.cardinality || selectedRelation?.relation_type);
    const readonly = noCodeRelationIsReadonly(editor, selectedRelation);
    const sourceFields = (sourceCode === noCodeRelationCurrentServiceCode(editor)
        ? (Array.isArray(editor?.fields) ? editor.fields : [])
        : noCodeRelationEntityFields(sourceService))
        .filter((field) => String(field?.field_key || "").trim());
    const uniqueValueFieldKey = String(selectedRelation?.unique_value_field_key || "").trim().toLowerCase();
    const recordDisplayMode = ["standard", "hidden", "assignment"].includes(String(selectedRelation?.record_display_mode || "").trim().toLowerCase())
        ? String(selectedRelation.record_display_mode).trim().toLowerCase()
        : "standard";
    const assignmentResourceCode = normalizeNoCodeRelationEntityCode(selectedRelation?.assignment_resource_service_code || "");
    const assignmentAssistantFeedback = String(editor?.assignmentAssistantFeedbacks?.[selectedRelationId] || "").trim();
    const assignmentResources = noCodeRelationAvailableServices(editor)
        .filter((service) => {
            const code = normalizeNoCodeRelationEntityCode(service?.code || "");
            return code && code !== sourceCode && code !== targetCode && Boolean(findNoCodeService(code));
        });
    const verbOptions = ["est lie a", "appartient a", "contient", "est gere par", "est localise sur", "utilise", "concerne"];
    return `
        <aside class="no-code-relations-properties">
            <h4>Proprietes</h4>
            ${selectedRelation ? `
                ${readonly ? `<p class="muted">Relation configuree depuis ${escapeHtml(sourceService.label || sourceCode)}. Elle est visible ici pour la reciprocite.</p>` : ""}
                <label class="field no-code-relation-direction-field">
                    <span>Relation :</span>
                    <select name="service_relation_direction" data-relation-id="${escapeHtml(selectedRelationId)}" ${readonly ? "disabled" : ""}>
                        <option value="out" ${selectedRelation.direction !== "in" ? "selected" : ""}>${escapeHtml(sourceService.label || sourceCode)} vers ${escapeHtml(targetService.label || targetCode)}</option>
                        <option value="in" ${selectedRelation.direction === "in" ? "selected" : ""}>${escapeHtml(targetService.label || targetCode)} vers ${escapeHtml(sourceService.label || sourceCode)}</option>
                    </select>
                </label>
                <div class="no-code-relations-property-group">
                    <p class="no-code-relation-natural">${escapeHtml(noCodeRelationNaturalPhrase(editor, selectedRelation))}</p>
                </div>
                <div class="no-code-relations-property-group">
                    <strong>Nommer le lien</strong>
                    <div class="no-code-relation-chip-grid">
                        ${verbOptions.map((verb) => `
                            <button type="button" class="no-code-relation-chip ${verb === relationVerb ? "is-active" : ""}" data-action="service:relation:verb" data-relation-id="${escapeHtml(selectedRelationId)}" data-verb="${escapeHtml(verb)}" ${readonly ? "disabled" : ""}>${escapeHtml(verb)}</button>
                        `).join("")}
                    </div>
                    <label class="field">
                        <span>Verbe personnalise</span>
                        <input name="service_relation_verb" data-relation-id="${escapeHtml(selectedRelationId)}" type="text" value="${escapeHtml(relationVerb)}" ${readonly ? "disabled" : ""}>
                    </label>
                </div>
                <div class="no-code-relations-property-group">
                    <strong>Combien d'elements ?</strong>
                    ${["many_to_one", "one_to_one", "one_to_many", "many_to_many"].map((type) => `
                        <button type="button" class="no-code-relation-qty ${cardinality === type ? "is-active" : ""}" data-action="service:relation:cardinality" data-relation-id="${escapeHtml(selectedRelationId)}" data-cardinality="${type}" ${readonly ? "disabled" : ""}>
                            <strong>${escapeHtml(noCodeRelationTypeLabel(type))}</strong>
                            <span>${escapeHtml(noCodeRelationCardinalityTitle(editor, selectedRelation, type))}</span>
                        </button>
                    `).join("")}
                    <label class="check-field">
                        <input name="service_relation_required" data-relation-id="${escapeHtml(selectedRelationId)}" type="checkbox" ${selectedRelation.required ? "checked" : ""} ${readonly ? "disabled" : ""}>
                        <span>Relation obligatoire</span>
                    </label>
                    <div class="inventory-row-actions" ${readonly ? "hidden" : ""}>
                        ${createActionButtonMarkup({
                            className: "toolbar-btn danger-btn",
                            action: "service:relation:remove",
                            label: "Retirer",
                            data: { relation_id: selectedRelationId },
                        })}
                    </div>
                </div>
                <div class="no-code-relations-property-group">
                    <strong>Règles de choix</strong>
                    <p class="muted">À utiliser lorsque les éléments doivent correspondre à une autre relation déjà renseignée, par exemple un code lié au même copieur que l’agent.</p>
                    <label class="check-field">
                        <input name="service_relation_filter_candidates_by_shared_relation" data-relation-id="${escapeHtml(selectedRelationId)}" type="checkbox" ${selectedRelation.filter_candidates_by_shared_relation ? "checked" : ""} ${readonly ? "disabled" : ""}>
                        <span>Ne proposer que les éléments compatibles avec les relations déjà choisies</span>
                    </label>
                </div>
                <div class="no-code-relations-property-group">
                    <strong>Affichage des relations</strong>
                    <p class="muted">Par défaut, seules les relations directes sont affichées. Activez cette option uniquement si les éléments liés au second niveau sont utiles dans la fiche.</p>
                    <label class="check-field" ${recordDisplayMode === "assignment" ? "hidden" : ""}>
                        <input name="service_relation_show_indirect_relations" data-relation-id="${escapeHtml(selectedRelationId)}" type="checkbox" ${selectedRelation.show_indirect_relations ? "checked" : ""} ${readonly ? "disabled" : ""}>
                        <span>Afficher les relations indirectes via cet élément lié</span>
                    </label>
                    ${recordDisplayMode === "assignment" ? '<p class="muted">Le mode Attribution affiche deja une synthese des liens directs. Les relations indirectes ne sont donc pas utilisees ici.</p>' : ""}
                </div>
                <div class="no-code-relations-property-group">
                    <strong>Presentation dans la fiche</strong>
                    <p class="muted">Standard affiche le lien brut. Attribution regroupe ce lien avec un element technique, par exemple un code d'acces ou une licence. Masquee conserve la relation sans la dupliquer dans la fiche.</p>
                    ${recordDisplayMode === "standard" ? createActionButtonMarkup({
                        className: "toolbar-btn",
                        type: "button",
                        action: "service:relation:assignment:start",
                        label: "Configurer une attribution guidee",
                        data: { relation_id: selectedRelationId },
                        disabled: readonly,
                    }) : ""}
                    <label class="field">
                        <span>Mode d'affichage</span>
                        <select name="service_relation_record_display_mode" data-relation-id="${escapeHtml(selectedRelationId)}" ${readonly ? "disabled" : ""}>
                            <option value="standard" ${recordDisplayMode === "standard" ? "selected" : ""}>Standard</option>
                            <option value="assignment" ${recordDisplayMode === "assignment" ? "selected" : ""}>Attribution d'un element lie</option>
                            <option value="hidden" ${recordDisplayMode === "hidden" ? "selected" : ""}>Masquee dans la fiche</option>
                        </select>
                    </label>
                    <label class="field" ${recordDisplayMode === "assignment" ? "" : "hidden"}>
                        <span>Element attribue</span>
                        <select name="service_relation_assignment_resource" data-relation-id="${escapeHtml(selectedRelationId)}" ${readonly ? "disabled" : ""}>
                            <option value="">Choisir un module</option>
                            ${assignmentResources.map((service) => {
                                const code = normalizeNoCodeRelationEntityCode(service?.code || "");
                                return `<option value="${escapeHtml(code)}" ${code === assignmentResourceCode ? "selected" : ""}>${escapeHtml(String(service?.label || code))}</option>`;
                            }).join("")}
                        </select>
                    </label>
                    ${recordDisplayMode === "assignment" ? `
                        <div class="no-code-assignment-assistant">
                            <strong>Assistant d'attribution</strong>
                            <p class="muted">1. Choisissez l'element attribue. 2. Preparez ses liens techniques. 3. Enregistrez le module.</p>
                            ${createActionButtonMarkup({
                                className: "toolbar-btn",
                                type: "button",
                                action: "service:relation:assignment:prepare",
                                label: "Preparer les liens necessaires",
                                data: { relation_id: selectedRelationId },
                                disabled: readonly || !assignmentResourceCode,
                            })}
                            <p class="muted">L'assistant cree seulement les relations absentes : ${escapeHtml(String(sourceService.label || sourceCode))} et ${escapeHtml(String(targetService.label || targetCode))}. Les relations existantes ne sont pas modifiees.</p>
                            ${assignmentAssistantFeedback ? `<p class="inventory-feedback">${escapeHtml(assignmentAssistantFeedback)}</p>` : ""}
                        </div>
                    ` : ""}
                </div>
                <div class="no-code-relations-property-group">
                    <strong>Valeur unique par élément lié</strong>
                    <p class="muted">Évite d’utiliser deux fois la même valeur pour un même élément lié. Exemple : le code « 0101 » peut exister sur plusieurs copieurs, mais une seule fois par copieur.</p>
                    <label class="check-field">
                        <input name="service_relation_unique_value_enabled" data-relation-id="${escapeHtml(selectedRelationId)}" type="checkbox" ${uniqueValueFieldKey ? "checked" : ""} ${readonly || !sourceFields.length ? "disabled" : ""}>
                        <span>Empêcher les doublons sur l’élément lié</span>
                    </label>
                    <label class="field" ${uniqueValueFieldKey ? "" : "hidden"}>
                        <span>Valeur à contrôler</span>
                        <select name="service_relation_unique_value_field_key" data-relation-id="${escapeHtml(selectedRelationId)}" ${readonly || !uniqueValueFieldKey ? "disabled" : ""}>
                            ${sourceFields.map((field) => {
                                const key = String(field.field_key || "").trim().toLowerCase();
                                const label = String(field.label || key).trim();
                                return `<option value="${escapeHtml(key)}" ${key === uniqueValueFieldKey ? "selected" : ""}>${escapeHtml(label)}</option>`;
                            }).join("") || '<option value="">Aucun champ disponible</option>'}
                        </select>
                    </label>
                </div>
            ` : '<p class="muted">Selectionne une fleche du schema ou relie deux services pour regler leurs options.</p>'}
        </aside>
    `;
}

function noCodeRelationGuideCardinality(ownerCanHaveSeveral, relatedCanHaveSeveral) {
    if (ownerCanHaveSeveral && relatedCanHaveSeveral) return "many_to_many";
    if (ownerCanHaveSeveral) return "one_to_many";
    if (relatedCanHaveSeveral) return "many_to_one";
    return "one_to_one";
}

function noCodeRelationGuideAllowsOwnerSeveral(cardinality) {
    return ["one_to_many", "many_to_many"].includes(normalizeNoCodeRelationCardinality(cardinality));
}

function noCodeRelationGuideAllowsRelatedSeveral(cardinality) {
    return ["many_to_one", "many_to_many"].includes(normalizeNoCodeRelationCardinality(cardinality));
}

function buildNoCodeRelationGuideMarkup() {
    const editor = state.noCodeServiceEditor;
    const wizard = state.noCodeRelationGuide || {};
    const ownerService = { code: editor?.code || "", label: editor?.label || "Module" };
    const ownerLabel = noCodeRecordEditorEntityLabel(ownerService);
    const relatedCode = normalizeNoCodeRelationEntityCode(wizard.relatedCode || "");
    const relatedService = findNoCodeRelationEntity(relatedCode);
    const relatedLabel = noCodeRecordEditorEntityLabel(relatedService || { label: "element lie" });
    const relationshipKind = wizard.relationshipKind === "assignment" ? "assignment" : "simple";
    const resourceCode = normalizeNoCodeRelationEntityCode(wizard.resourceCode || "");
    const resourceService = findNoCodeService(resourceCode);
    const resourceLabel = noCodeRecordEditorEntityLabel(resourceService || { label: "element attribue" });
    const resourceFields = noCodeCustomServiceFields(resourceService);
    const uniqueFieldKey = String(wizard.uniqueFieldKey || "").trim().toLowerCase();
    const relatedOptions = noCodeRelationAvailableServices(editor)
        .filter((service) => normalizeNoCodeRelationEntityCode(service?.code || ""))
        .map((service) => {
            const code = normalizeNoCodeRelationEntityCode(service?.code || "");
            return `<option value="${escapeHtml(code)}" ${code === relatedCode ? "selected" : ""}>${escapeHtml(String(service?.label || code))}</option>`;
        }).join("");
    const resourceOptions = noCodeServiceRows()
        .filter((service) => {
            const code = normalizeNoCodeRelationEntityCode(service?.code || "");
            return code && code !== normalizeNoCodeRelationEntityCode(ownerService.code) && code !== relatedCode;
        })
        .map((service) => {
            const code = normalizeNoCodeRelationEntityCode(service?.code || "");
            return `<option value="${escapeHtml(code)}" ${code === resourceCode ? "selected" : ""}>${escapeHtml(String(service?.label || code))}</option>`;
        }).join("");
    const yesNoOptions = (value) => `
        <option value="yes" ${value === "yes" ? "selected" : ""}>Oui</option>
        <option value="no" ${value === "no" ? "selected" : ""}>Non</option>
    `;
    return `
        <form id="modal-relation-guide-form" class="modal-form">
            <section class="modal-section">
                <p class="muted">Decrivez le fonctionnement de ${escapeHtml(ownerLabel)} avec des mots simples. L'application creera les liens et l'affichage adaptes.</p>
                ${wizard.existingConfiguration ? '<p class="inventory-feedback">Les reponses ont ete pre-remplies a partir de la configuration actuelle. Vous pouvez les verifier ou les modifier.</p>' : ""}
                <div class="modal-settings-grid">
                    <label class="field">
                        <span>1. Les fiches « <strong>${escapeHtml(ownerLabel)}</strong> » sont-elles liees a un autre type d'element ?</span>
                        <select name="relationship_guide_has_relation">${yesNoOptions(wizard.hasRelation || "yes")}</select>
                    </label>
                    <label class="field" ${wizard.hasRelation === "no" ? "hidden" : ""}>
                        <span>2. A quel type d'element sont-ils lies ?</span>
                        <select name="relationship_guide_related" required>
                            <option value="">Choisir un type d'element</option>
                            ${relatedOptions}
                        </select>
                    </label>
                    <label class="field" ${wizard.hasRelation === "no" ? "hidden" : ""}>
                        <span>3. Que represente ce lien ?</span>
                        <select name="relationship_guide_kind">
                            <option value="simple" ${relationshipKind === "simple" ? "selected" : ""}>Un lien direct entre les deux fiches</option>
                            <option value="assignment" ${relationshipKind === "assignment" ? "selected" : ""}>L'attribution d'un code, d'une licence, d'un badge ou d'un autre element</option>
                        </select>
                    </label>
                    <label class="field" ${wizard.hasRelation === "no" ? "hidden" : ""}>
                        <span>4. Chaque fiche « <strong>${escapeHtml(ownerLabel)}</strong> » peut-elle etre liee a plusieurs fiches « <strong>${escapeHtml(relatedLabel)}</strong> » ?</span>
                        <select name="relationship_guide_owner_many">${yesNoOptions(wizard.ownerMany || "yes")}</select>
                    </label>
                    <label class="field" ${wizard.hasRelation === "no" ? "hidden" : ""}>
                        <span>5. Chaque fiche « <strong>${escapeHtml(relatedLabel)}</strong> » peut-elle etre liee a plusieurs fiches « <strong>${escapeHtml(ownerLabel)}</strong> » ?</span>
                        <select name="relationship_guide_related_many">${yesNoOptions(wizard.relatedMany || "yes")}</select>
                    </label>
                    <label class="field" ${wizard.hasRelation === "no" ? "hidden" : ""}>
                        <span>6. Une fiche « <strong>${escapeHtml(ownerLabel)}</strong> » peut-elle exister sans fiche « <strong>${escapeHtml(relatedLabel)}</strong> » liee ?</span>
                        <select name="relationship_guide_owner_without_related">${yesNoOptions(wizard.ownerWithoutRelated || "yes")}</select>
                    </label>
                    <label class="field" ${wizard.hasRelation === "no" ? "hidden" : ""}>
                        <span>Titre visible dans la fiche</span>
                        <input name="relationship_guide_label" type="text" value="${escapeHtml(String(wizard.label || ""))}" placeholder="Exemple : Utilisateurs et codes d'acces">
                    </label>
                    ${relationshipKind === "assignment" && wizard.hasRelation !== "no" ? `
                        <label class="field">
                            <span>7. Quel element est attribue ?</span>
                            <select name="relationship_guide_resource" required>
                                <option value="">Choisir un module existant</option>
                                ${resourceOptions}
                            </select>
                        </label>
                        <label class="field">
                            <span>8. Chaque element « <strong>${escapeHtml(resourceLabel)}</strong> » reste-t-il rattache a une seule fiche « <strong>${escapeHtml(ownerLabel)}</strong> » ?</span>
                            <select name="relationship_guide_resource_owner_single">${yesNoOptions(wizard.resourceOwnerSingle || "yes")}</select>
                        </label>
                        <label class="field">
                            <span>9. Chaque element « <strong>${escapeHtml(resourceLabel)}</strong> » peut-il etre attribue a plusieurs fiches « <strong>${escapeHtml(relatedLabel)}</strong> » ?</span>
                            <select name="relationship_guide_resource_related_many">${yesNoOptions(wizard.resourceRelatedMany || "no")}</select>
                        </label>
                        <label class="field">
                            <span>10. Faut-il empecher de reutiliser la meme valeur sur une meme fiche « <strong>${escapeHtml(ownerLabel)}</strong> » ?</span>
                            <select name="relationship_guide_unique_value">${yesNoOptions(wizard.uniqueValueEnabled || "no")}</select>
                        </label>
                        <label class="field" ${wizard.uniqueValueEnabled === "yes" && resourceFields.length ? "" : "hidden"}>
                            <span>Quelle information ne doit pas etre dupliquee ?</span>
                            <select name="relationship_guide_unique_field">
                                <option value="">Choisir une information</option>
                                ${resourceFields.map((field) => {
                                    const key = String(field?.field_key || "").trim().toLowerCase();
                                    return `<option value="${escapeHtml(key)}" ${key === uniqueFieldKey ? "selected" : ""}>${escapeHtml(String(field?.label || key))}</option>`;
                                }).join("")}
                            </select>
                        </label>
                    ` : ""}
                </div>
            </section>
            <p id="modal-relation-guide-feedback" class="muted inventory-feedback"></p>
            ${createModalActionsMarkup({ buttons: [{ preset: "back", type: "button", action: "service:relation-guide:back", label: "Retour" }, { preset: "save", label: wizard.hasRelation === "no" ? "Terminer" : "Creer cette relation" }] })}
        </form>
    `;
}

function noCodeExistingGuidedRelation(editor) {
    const ownerCode = noCodeRelationCurrentServiceCode(editor);
    const directRelations = noCodeRelationDrafts(editor).filter((relation) =>
        String(relation?.source_service_code || "").trim().toLowerCase() === ownerCode,
    );
    return directRelations.find((relation) =>
        String(relation?.record_display_mode || "").trim().toLowerCase() === "assignment"
        && normalizeNoCodeRelationEntityCode(relation?.assignment_resource_service_code || ""),
    ) || directRelations[0] || null;
}

function openNoCodeRelationGuide() {
    const editor = state.noCodeServiceEditor;
    if (!editor?.code || editor.mode !== "edit") {
        throw new Error("Enregistrez d'abord le module.");
    }
    const ownerCode = noCodeRelationCurrentServiceCode(editor);
    const existingRelation = noCodeExistingGuidedRelation(editor);
    const beneficiaryCode = normalizeNoCodeRelationEntityCode(
        existingRelation?.target_service_code || existingRelation?.service_code || "",
    );
    const resourceCode = normalizeNoCodeRelationEntityCode(
        existingRelation?.assignment_resource_service_code || "",
    );
    const baseCardinality = normalizeNoCodeRelationCardinality(
        existingRelation?.cardinality || existingRelation?.relation_type || "many_to_many",
    );
    state.noCodeRelationGuide = {
        hasRelation: "yes",
        relatedCode: existingRelation ? beneficiaryCode : "",
        relationshipKind: String(existingRelation?.record_display_mode || "").trim().toLowerCase() === "assignment" ? "assignment" : "simple",
        ownerMany: noCodeRelationGuideAllowsOwnerSeveral(baseCardinality) ? "yes" : "no",
        relatedMany: noCodeRelationGuideAllowsRelatedSeveral(baseCardinality) ? "yes" : "no",
        ownerWithoutRelated: existingRelation?.required ? "no" : "yes",
        resourceCode,
        label: String(existingRelation?.display_label || existingRelation?.label || "").trim(),
        uniqueFieldKey: "",
        resourceOwnerSingle: "yes",
        resourceRelatedMany: "no",
        uniqueValueEnabled: "no",
        existingConfiguration: Boolean(existingRelation),
    };
    openModal(
        "Assistant de relations",
        buildNoCodeRelationGuideMarkup(),
        noCodeInlineOptions("min(760px, calc(100vw - 40px))", { inline: true }),
    );
    if (!resourceCode) {
        return;
    }
    fetchNoCodeServiceRelations(resourceCode)
        .then((resourceRelations) => {
            const ownerRelation = resourceRelations.find((relation) =>
                String(relation?.source_service_code || "").trim().toLowerCase() === resourceCode
                && normalizeNoCodeRelationEntityCode(relation?.target_service_code || relation?.service_code || "") === ownerCode,
            );
            const beneficiaryRelation = resourceRelations.find((relation) =>
                String(relation?.source_service_code || "").trim().toLowerCase() === resourceCode
                && normalizeNoCodeRelationEntityCode(relation?.target_service_code || relation?.service_code || "") === beneficiaryCode,
            );
            const uniqueFieldKey = String(ownerRelation?.unique_value_field_key || "").trim().toLowerCase();
            const wizard = state.noCodeRelationGuide;
            if (!wizard || normalizeNoCodeRelationEntityCode(wizard.resourceCode || "") !== resourceCode) {
                return;
            }
            wizard.uniqueFieldKey = uniqueFieldKey;
            wizard.uniqueValueEnabled = uniqueFieldKey ? "yes" : "no";
            wizard.resourceOwnerSingle = normalizeNoCodeRelationCardinality(ownerRelation?.cardinality || ownerRelation?.relation_type) === "many_to_many" ? "no" : "yes";
            wizard.resourceRelatedMany = normalizeNoCodeRelationCardinality(beneficiaryRelation?.cardinality || beneficiaryRelation?.relation_type) === "many_to_many" ? "yes" : "no";
            const wizardForm = document.getElementById("modal-relation-guide-form");
            if (wizardForm instanceof HTMLFormElement) {
                openModal(
                    "Assistant de relations",
                    buildNoCodeRelationGuideMarkup(),
                    noCodeInlineOptions("min(760px, calc(100vw - 40px))", { inline: true }),
                );
            }
        })
        .catch(() => {
            // Le scenario reste utilisable si la regle technique ne peut pas etre chargee.
        });
}

function returnToNoCodeServiceRelationsEditor() {
    const editor = state.noCodeServiceEditor;
    state.noCodeRelationGuide = null;
    if (!editor) {
        closeModal();
        return;
    }
    openModal("Service - Edition", buildNoCodeServiceEditorMarkup(), noCodeInlineOptions("min(1180px, calc(100vw - 32px))", { inline: true }));
}

function buildNoCodeServiceRelationsStepMarkup(editor) {
    const relations = noCodeRelationDrafts(editor);
    const relationSummary = relations.length
        ? relations.map((relation) => {
            const sourceCode = String(relation?.source_service_code || "").trim().toLowerCase();
            const targetCode = normalizeNoCodeRelationEntityCode(relation?.target_service_code || relation?.service_code || "");
            const source = findNoCodeRelationEntity(sourceCode) || { label: sourceCode };
            const target = findNoCodeRelationEntity(targetCode) || { label: targetCode };
            const direction = noCodeRelationIsReadonly(editor, relation) ? "entrante" : "sortante";
            return `${source.label || sourceCode} -> ${target.label || targetCode} (${direction}, ${noCodeRelationTypeLabel(relation.cardinality || relation.relation_type)})`;
        }).join(" | ")
        : "Aucune relation configuree.";
    return `
        <section class="no-code-service-wizard-panel no-code-relations-panel">
            <div class="no-code-service-panel-head">
                <div>
                    <h3>Relations</h3>
                    <p class="muted">Commencez par un scenario guide. Le schema reste disponible pour les reglages avances.</p>
                </div>
                ${editor.mode === "edit" && editor.code ? createActionButtonMarkup({
                    preset: "add",
                    action: "service:relation-guide:start",
                    label: "Configurer les relations avec l'assistant",
                }) : ""}
            </div>
            ${editor.mode === "edit" && editor.code ? "" : '<p class="muted">Enregistrez d\'abord le module pour pouvoir creer un scenario guide.</p>'}
            ${editor.relationScenarioFeedback ? `<p class="inventory-feedback">${escapeHtml(editor.relationScenarioFeedback)}</p>` : ""}
            <details class="no-code-relations-advanced">
                <summary>Reglages avances des relations</summary>
                <div class="no-code-relations-builder">
                    ${buildNoCodeRelationPaletteMarkup(editor)}
                    ${buildNoCodeRelationCanvasMarkup(editor)}
                    ${buildNoCodeRelationPropertiesMarkup(editor)}
                </div>
            </details>
            ${editor.relationLoadError ? `<p class="error-text">${escapeHtml(editor.relationLoadError)}</p>` : ""}
            <p class="muted">${escapeHtml(relationSummary)}</p>
        </section>
    `;
}

function beginNoCodeRelationNodeDrag(event) {
    const target = event.target;
    if (!(target instanceof Element)) {
        return;
    }
    if (target.closest("[data-relation-port]")) {
        beginNoCodeRelationConnect(event);
        return;
    }
    const node = target.closest("[data-relation-node]");
    if (!(node instanceof HTMLElement)) {
        return;
    }
    const editor = state.noCodeServiceEditor;
    if (!editor) {
        return;
    }
    const nodeCode = String(node.dataset.relationNode || "").trim().toLowerCase();
    if (!nodeCode) {
        return;
    }
    const canvasState = editor.relationCanvas && typeof editor.relationCanvas === "object" ? editor.relationCanvas : {};
    const zoom = normalizeNoCodeRelationZoom(canvasState.zoom || 1);
    const startX = Number(event.clientX || 0);
    const startY = Number(event.clientY || 0);
    const nodeCodes = noCodeRelationNodeCodes(editor);
    const position = noCodeRelationNodePosition(editor, nodeCode, nodeCodes.indexOf(nodeCode));
    const initialX = Number(position.x || 0);
    const initialY = Number(position.y || 0);
    state.noCodeRelationDrag = {
        nodeCode,
        startX,
        startY,
        initialX,
        initialY,
        zoom,
        moved: false,
    };
    try {
        node.setPointerCapture(event.pointerId);
    } catch (_error) {
    }
}

function updateNoCodeRelationNodeDrag(event) {
    const drag = state.noCodeRelationDrag;
    const editor = state.noCodeServiceEditor;
    if (!drag || !editor) {
        return;
    }
    const dx = (Number(event.clientX || 0) - Number(drag.startX || 0)) / Math.max(0.5, Number(drag.zoom || 1));
    const dy = (Number(event.clientY || 0) - Number(drag.startY || 0)) / Math.max(0.5, Number(drag.zoom || 1));
    if (Math.abs(dx) + Math.abs(dy) > 3) {
        drag.moved = true;
    }
    const nextX = Math.max(0, Math.min(650, Math.round(Number(drag.initialX || 0) + dx)));
    const nextY = Math.max(0, Math.min(460, Math.round(Number(drag.initialY || 0) + dy)));
    setNoCodeRelationNodePosition(editor, drag.nodeCode, nextX, nextY);
    editor.selectedRelationServiceCode = drag.nodeCode;
    renderNoCodeServiceEditorShell();
}

function endNoCodeRelationNodeDrag() {
    if (state.noCodeRelationDrag?.moved) {
        state.noCodeRelationSuppressClickUntil = Date.now() + 350;
    }
    state.noCodeRelationDrag = null;
}

function noCodeRelationPortCoordinates(editor, serviceCode, side) {
    const nodeCodes = noCodeRelationNodeCodes(editor);
    const position = noCodeRelationNodePosition(editor, serviceCode, nodeCodes.indexOf(serviceCode));
    return {
        x: String(side || "right") === "left" ? position.x : position.x + 250,
        y: position.y + 70,
    };
}

function beginNoCodeRelationConnect(event) {
    const port = event.target instanceof Element ? event.target.closest("[data-relation-port]") : null;
    const editor = state.noCodeServiceEditor;
    if (!(port instanceof HTMLElement) || !editor) {
        return;
    }
    event.stopPropagation();
    event.preventDefault();
    const serviceCode = normalizeNoCodeRelationEntityCode(port.dataset.serviceCode || "");
    const side = String(port.dataset.relationPort || "right").trim().toLowerCase();
    const coords = noCodeRelationPortCoordinates(editor, serviceCode, side);
    state.noCodeRelationConnect = {
        active: true,
        sourceServiceCode: serviceCode,
        sourceSide: side,
        x1: coords.x,
        y1: coords.y,
        x2: coords.x,
        y2: coords.y,
    };
    renderNoCodeServiceEditorShell();
}

function updateNoCodeRelationConnect(event) {
    const connect = state.noCodeRelationConnect;
    const editor = state.noCodeServiceEditor;
    if (!connect?.active || !editor) {
        return;
    }
    const stage = document.querySelector("[data-relation-stage]");
    const canvasState = editor.relationCanvas && typeof editor.relationCanvas === "object" ? editor.relationCanvas : {};
    const zoom = normalizeNoCodeRelationZoom(canvasState.zoom || 1);
    if (stage instanceof HTMLElement) {
        const rect = stage.getBoundingClientRect();
        connect.x2 = Math.round((Number(event.clientX || 0) - rect.left) / zoom);
        connect.y2 = Math.round((Number(event.clientY || 0) - rect.top) / zoom);
    }
    renderNoCodeServiceEditorShell();
}

function endNoCodeRelationConnect(event) {
    const connect = state.noCodeRelationConnect;
    const editor = state.noCodeServiceEditor;
    if (!connect?.active || !editor) {
        state.noCodeRelationConnect = null;
        return;
    }
    const elementAtPointer = event
        ? document.elementFromPoint(Number(event.clientX || 0), Number(event.clientY || 0))
        : null;
    const target = elementAtPointer instanceof Element ? elementAtPointer.closest("[data-relation-port]") : null;
    const sourceCode = normalizeNoCodeRelationEntityCode(connect.sourceServiceCode || "");
    const targetCode = target instanceof HTMLElement ? normalizeNoCodeRelationEntityCode(target.dataset.serviceCode || "") : "";
    state.noCodeRelationConnect = null;
    if (!sourceCode || !targetCode || sourceCode === targetCode) {
        renderNoCodeServiceEditorShell();
        return;
    }
    const currentCode = noCodeRelationCurrentServiceCode(editor);
    if (sourceCode !== currentCode && targetCode !== currentCode) {
        renderNoCodeServiceEditorShell();
        return;
    }
    const storedSourceCode = currentCode;
    const storedTargetCode = sourceCode === currentCode ? targetCode : sourceCode;
    const storedDirection = sourceCode === currentCode ? "out" : "in";
    const exists = noCodeRelationDrafts(editor).some((relation) => (
        String(relation?.source_service_code || "").trim().toLowerCase() === storedSourceCode
        && normalizeNoCodeRelationEntityCode(relation?.target_service_code || relation?.service_code || "") === storedTargetCode
    ));
    if (!exists) {
        const targetService = findNoCodeRelationEntity(storedTargetCode) || { code: storedTargetCode, label: storedTargetCode };
        const relation = createNoCodeRelationDraft(targetService, noCodeRelationDrafts(editor).length, storedSourceCode);
        relation.direction = storedDirection;
        const sourcePos = noCodeRelationNodePosition(editor, storedSourceCode, noCodeRelationNodeCodes(editor).indexOf(storedSourceCode));
        const targetPos = noCodeRelationNodePosition(editor, storedTargetCode, noCodeRelationNodeCodes(editor).indexOf(storedTargetCode));
        relation.source_x = sourcePos.x;
        relation.source_y = sourcePos.y;
        relation.target_x = targetPos.x;
        relation.target_y = targetPos.y;
        relation.x = targetPos.x;
        relation.y = targetPos.y;
        editor.relationDrafts = [...noCodeRelationDrafts(editor), relation];
        editor.selectedRelationId = noCodeRelationId(relation, editor.relationDrafts.length - 1);
        editor.selectedRelationServiceCode = storedTargetCode;
    }
    renderNoCodeServiceEditorShell();
}

function addNoCodeRelationCanvasNodeAt(serviceCode, clientX, clientY) {
    const editor = state.noCodeServiceEditor;
    const code = normalizeNoCodeRelationEntityCode(serviceCode);
    const service = findNoCodeRelationEntity(code);
    if (!editor || !code || !service || code === noCodeRelationCurrentServiceCode(editor)) {
        return false;
    }
    const stage = document.querySelector("[data-relation-stage]");
    const canvasState = editor.relationCanvas && typeof editor.relationCanvas === "object" ? editor.relationCanvas : {};
    const zoom = normalizeNoCodeRelationZoom(canvasState.zoom || 1);
    let x = 430;
    let y = 34;
    if (stage instanceof HTMLElement) {
        const rect = stage.getBoundingClientRect();
        x = Math.round((Number(clientX || 0) - rect.left) / zoom - 125);
        y = Math.round((Number(clientY || 0) - rect.top) / zoom - 70);
    }
    editor.relationCanvas = editor.relationCanvas && typeof editor.relationCanvas === "object" ? editor.relationCanvas : {};
    editor.relationCanvas.nodes = editor.relationCanvas.nodes && typeof editor.relationCanvas.nodes === "object" ? editor.relationCanvas.nodes : {};
    editor.relationCanvas.nodes[code] = {
        x: Math.max(0, Math.min(650, x)),
        y: Math.max(0, Math.min(460, y)),
    };
    if (!noCodeRelationDrafts(editor).length) {
        const currentCode = noCodeRelationCurrentServiceCode(editor);
        const relation = createNoCodeRelationDraft(service, 0, currentCode);
        const sourcePos = noCodeRelationNodePosition(editor, currentCode, 0);
        const targetPos = noCodeRelationNodePosition(editor, code, noCodeRelationNodeCodes(editor).indexOf(code));
        relation.source_x = sourcePos.x;
        relation.source_y = sourcePos.y;
        relation.target_x = targetPos.x;
        relation.target_y = targetPos.y;
        relation.x = targetPos.x;
        relation.y = targetPos.y;
        editor.relationDrafts = [relation];
        editor.selectedRelationId = noCodeRelationId(relation, 0);
    } else {
        editor.selectedRelationId = "";
    }
    editor.selectedRelationServiceCode = code;
    renderNoCodeServiceEditorShell();
    return true;
}

function buildNoCodeServiceRecapStepMarkup(editor) {
    const fields = Array.isArray(editor.fields) ? editor.fields : [];
    const code = noCodeServiceTechnicalCodeDisplay(editor);
    const visibleFields = fields.slice(0, 8);
    const hiddenFieldsCount = Math.max(0, fields.length - visibleFields.length);
    const headCells = visibleFields
        .map((field) => `<th>${escapeHtml(String(field.label || field.field_key || "").trim())}</th>`)
        .join("");
    const sampleCells = visibleFields
        .map((field) => `<td>${escapeHtml(noCodePreviewValueForKind(field.field_kind))}</td>`)
        .join("");
    const emptyColspan = Math.max(2, visibleFields.length + 2);
    return `
        <section class="no-code-service-wizard-panel">
            <div class="no-code-service-panel-head">
                <div>
                    <h3>${escapeHtml(editor.label || "Service sans nom")}</h3>
                    <p class="muted">Apercu de l'inventaire qui sera cree.</p>
                </div>
                <span class="no-code-service-code">${escapeHtml(code)}</span>
            </div>
            <div class="inventory-row-actions">
                ${createActionButtonMarkup({
                    className: "toolbar-btn",
                    type: "button",
                    label: "Exporter CSV",
                    disabled: true,
                })}
                ${createActionButtonMarkup({
                    className: "toolbar-btn",
                    type: "button",
                    label: "Importer",
                    disabled: true,
                })}
                ${createActionButtonMarkup({
                    className: "toolbar-btn",
                    type: "button",
                    label: "Ajouter fiche",
                    disabled: true,
                })}
            </div>
            <div class="table-wrap shared-treeview-table-wrap no-code-service-recap-tree">
                <table class="device-table shared-treeview-table">
                    <thead>
                        <tr>
                            <th>Fiche</th>
                            ${headCells}
                            ${editor.credentials_enabled ? "<th>Identifiants</th>" : ""}
                            ${editor.child_enabled ? `<th>${escapeHtml(editor.child_label || "Elements lies")}</th>` : ""}
                        </tr>
                    </thead>
                    <tbody>
                        ${visibleFields.length ? `
                            <tr>
                                <td><strong>Creation — ${escapeHtml(String(editor.label || "Service"))}</strong><span class="muted">exemple</span></td>
                                ${sampleCells}
                                ${editor.credentials_enabled ? "<td>login / mot de passe</td>" : ""}
                                ${editor.child_enabled ? "<td>0 element</td>" : ""}
                            </tr>
                        ` : `<tr class="shared-treeview-empty"><td colspan="${emptyColspan}">Aucun champ defini.</td></tr>`}
                    </tbody>
                </table>
            </div>
            <p class="muted">${escapeHtml([
                editor.is_technical ? "Module technique (tuile masquee par defaut)" : (editor.is_active ? "Service actif" : "Service inactif"),
                `${fields.length} champ(s)`,
                hiddenFieldsCount ? `${hiddenFieldsCount} champ(s) supplementaire(s) masque(s) dans l'apercu` : "",
                editor.child_enabled ? `Sous-liste: ${editor.child_label || "Elements lies"}` : "",
            ].filter(Boolean).join(" | "))}</p>
        </section>
    `;
}

function buildNoCodeServiceWizardContentMarkup(editor, activeStep) {
    if (activeStep === 2) {
        return buildNoCodeServiceFieldsStepMarkup(editor);
    }
    if (activeStep === 3) {
        return buildNoCodeServiceRelationsStepMarkup(editor);
    }
    if (activeStep === 4) {
        return buildNoCodeServiceRecapStepMarkup(editor);
    }
    return buildNoCodeServiceIdentityStepMarkup(editor);
}

function buildNoCodeServiceWizardFooterMarkup(editor, activeStep) {
    const saveLabel = editor.mode === "edit" ? "Enregistrer" : "Creer le service";
    return `
        <div class="no-code-service-wizard-footer">
            ${createActionButtonMarkup({ preset: "back", action: "service:back", label: "Quitter" })}
            <span class="muted">Etape ${activeStep} sur ${NO_CODE_SERVICE_WIZARD_STEPS.length}</span>
            <div class="inventory-row-actions">
                ${createActionButtonMarkup({
                    className: "toolbar-btn",
                    type: "button",
                    action: "service:wizard:previous",
                    label: "Precedent",
                    disabled: activeStep <= 1,
                })}
                ${activeStep < NO_CODE_SERVICE_WIZARD_STEPS.length
                    ? createActionButtonMarkup({
                        className: "primary-btn",
                        type: "button",
                        action: "service:wizard:next",
                        label: "Suivant",
                    })
                    : createActionButtonMarkup({
                        className: "primary-btn",
                        type: "submit",
                        label: saveLabel,
                    })}
            </div>
        </div>
    `;
}

function renderNoCodeServiceEditor() {
    const editor = state.noCodeServiceEditor;
    if (!editor) {
        return;
    }
    const listWrap = document.getElementById("service-field-list");
    if (listWrap instanceof HTMLElement) {
        const rows = editor.fields || [];
        const draft = editor.fieldEditor;
        const editorMarkup = draft ? buildNoCodeFieldEditorAccordionMarkup(draft) : "";
        if (!rows.length && !draft) {
            listWrap.innerHTML = `<div class="muted">Aucun champ defini.</div>`;
        } else {
            const rowsMarkup = rows.map((field) => {
                const fieldKey = String(field.field_key || "").trim();
                const label = String(field.label || fieldKey).trim() || fieldKey;
                const kindLabel = noCodeKindLabel(field.field_kind);
                const sourceKind = normalizeListSourceKind(field.list_source_kind || "local");
                const sharedListCode = String(field.shared_list_code || "").trim().toLowerCase();
                const sharedList = findSharedList(sharedListCode);
                const sourceLabel = normalizeNoCodeKind(field.field_kind) === "list"
                    ? (sourceKind === "shared"
                        ? ` | Liste commune: ${sharedList ? sharedList.label : (sharedListCode || "non definie")}`
                        : " | Liste locale")
                    : "";
                return `
                    <div class="type-schema-custom-field-row">
                        <div class="type-schema-custom-field-meta">
                            <strong>${escapeHtml(label)}</strong>
                            <span>${escapeHtml(kindLabel)}${field.required ? " | obligatoire" : ""}${field.track_history ? " | historique" : ""}${field.inline_editable ? " | edition directe" : ""}${field.batch_editable ? " | modification par lot" : ""}${field.quick_filter ? " | filtre" : ""}${escapeHtml(sourceLabel)}</span>
                        </div>
                        ${createIconActionButtonMarkup({
                            icon: "settings",
                            action: "service:field:edit",
                            title: "Modifier",
                            data: { field_key: fieldKey },
                        })}
                        ${createIconActionButtonMarkup({
                            icon: "delete",
                            danger: true,
                            action: "service:field:delete",
                            title: "Supprimer",
                            data: { field_key: fieldKey },
                        })}
                    </div>
                    ${draft && draft.mode === "edit" && String(draft.originalKey || "").trim() === fieldKey ? editorMarkup : ""}
                `;
            }).join("");
            if (draft && draft.mode === "create") {
                listWrap.innerHTML = `${editorMarkup}${rowsMarkup}`;
            } else if (!rows.length && draft) {
                listWrap.innerHTML = editorMarkup;
            } else {
                listWrap.innerHTML = rowsMarkup;
            }
        }
    }
    const previewWrap = document.getElementById("service-import-preview-wrap");
    if (previewWrap instanceof HTMLElement) {
        const preview = editor.importPreview;
        const hasAdSource = Boolean(editor.adImportDraft);
        const hasPreview = Boolean(preview && Array.isArray(preview.fields) && preview.fields.length > 0);
        previewWrap.hidden = !hasPreview && !hasAdSource;
        if (hasAdSource) {
            previewWrap.innerHTML = buildServiceActiveDirectorySourceMarkup(editor);
        } else if (hasPreview) {
            const sourceHeaders = Array.isArray(preview.sourceHeaders) ? preview.sourceHeaders : [];
            const sourceRowsPreview = Array.isArray(preview.sourceRowsPreview) ? preview.sourceRowsPreview : [];
            const availableSheets = Array.isArray(preview.availableSheets) ? preview.availableSheets : [];
            const selectedSheetName = String(preview.selectedSheetName || "").trim();
            const headerMode = normalizeTabularHeaderMode(editor.importHeaderMode || preview.effectiveHeaderMode || "auto");
            const headerRowNumber = normalizeTabularHeaderRowNumber(editor.importHeaderRowNumber || preview.detectedHeaderRowNumber || 1);
            const importUntilRowNumber = normalizeTabularUntilRowNumber(editor.importUntilRowNumber || 0);
            const detectedHeaderRow = normalizeTabularHeaderRowNumber(preview.detectedHeaderRowNumber || headerRowNumber);
            const effectiveHeaderMode = normalizeTabularHeaderMode(preview.effectiveHeaderMode || headerMode);
            const advancedEnabled = Boolean(editor.importAdvancedEnabled);
            const sheetSelectorMarkup = availableSheets.length > 1
                ? `
                    <div class="modal-settings-grid">
                        <label class="field">
                            <span>Feuille Excel</span>
                            <select name="service_field_import_sheet">
                                ${availableSheets.map((sheet) => {
                                    const label = String(sheet || "").trim();
                                    const selected = label && label === selectedSheetName;
                                    return `<option value="${escapeHtml(label)}" ${selected ? "selected" : ""}>${escapeHtml(label)}</option>`;
                                }).join("")}
                            </select>
                        </label>
                    </div>
                `
                : "";
            const headerModeOptions = TABULAR_HEADER_MODES
                .map((option) => (
                    `<option value="${escapeHtml(option.value)}" ${headerMode === option.value ? "selected" : ""}>${escapeHtml(option.label)}</option>`
                ))
                .join("");
            const importActionsMarkup = `
                <div class="inventory-row-actions no-code-import-actions">
                    ${createActionButtonMarkup({
                        className: "toolbar-btn",
                        type: "button",
                        action: "service:field:import:clear",
                        label: "Ignorer",
                        iconHtml: "&#10005;",
                    })}
                    ${createActionButtonMarkup({
                        className: "primary-btn",
                        type: "button",
                        action: "service:field:import:apply",
                        label: "Appliquer l'import",
                        iconHtml: "&#10003;",
                    })}
                </div>
            `;
            previewWrap.innerHTML = `
                <section class="type-schema-field-editor">
                    <div class="type-schema-fields-head">
                        <h3>Apercu de l'import</h3>
                        ${importActionsMarkup}
                    </div>
                    <p class="muted">${escapeHtml(String(preview.filename || "Fichier"))} | ${Number(preview.detectedColumns || 0)} colonne(s) detectee(s) | ${Number(preview.detectedRows || 0)} ligne(s) analysee(s)</p>
                    <label class="check-field">
                        <input name="service_field_import_records_enabled" type="checkbox" ${editor.importRecordsEnabled !== false ? "checked" : ""}>
                        <span>Importer les donnees du fichier apres creation du service</span>
                    </label>
                    <label class="check-field">
                        <input name="service_field_import_advanced" type="checkbox" ${advancedEnabled ? "checked" : ""}>
                        <span>Reglages avances</span>
                    </label>
                    <div id="service-field-import-advanced-wrap" ${advancedEnabled ? "" : "hidden"}>
                        ${sheetSelectorMarkup}
                        <div class="modal-settings-grid">
                            <label class="field">
                                <span>Detection entete</span>
                                <select name="service_field_import_header_mode">
                                    ${headerModeOptions}
                                </select>
                            </label>
                            <label class="field">
                                <span>Ligne entete</span>
                                <input name="service_field_import_header_row" type="number" min="1" step="1" value="${escapeHtml(String(headerRowNumber))}" ${headerMode === "manual" ? "" : "disabled"}>
                            </label>
                            <label class="field">
                                <span>Importer jusqu'a la ligne</span>
                                <input name="service_field_import_until_row" type="number" min="0" step="1" placeholder="Toutes les lignes" value="${importUntilRowNumber > 0 ? escapeHtml(String(importUntilRowNumber)) : ""}">
                            </label>
                        </div>
                    </div>
                    <p class="muted">Entete active: ligne ${detectedHeaderRow} (${effectiveHeaderMode}).</p>
                    <h4>Import avec mappage integre</h4>
                    ${buildServiceFieldImportMappingMarkup(editor, sourceHeaders, sourceRowsPreview)}
                    <h4>Apercu de la structure creee</h4>
                    ${buildServiceFieldImportPreviewTreeMarkup(preview.fields || [])}
                    <div class="inventory-row-actions type-schema-field-bottom-actions">
                        ${createActionButtonMarkup({
                            className: "toolbar-btn",
                            action: "service:field:add",
                            label: "Ajouter un champ",
                            title: "Ajouter un champ",
                            iconHtml: "+",
                        })}
                    </div>
                    ${importActionsMarkup}
                </section>
            `;
        } else {
            previewWrap.innerHTML = "";
        }
    }

}

function buildNoCodeServiceEditorMarkup() {
    const editor = state.noCodeServiceEditor;
    if (!editor) {
        return "";
    }
    const activeStep = currentNoCodeServiceWizardStep();
    return `
        <form id="modal-service-form" class="modal-form no-code-service-wizard" data-edit-code="${escapeHtml(editor.code)}" data-current-step="${activeStep}">
            <div class="no-code-service-wizard-shell">
                ${buildNoCodeServiceWizardStepsMarkup(activeStep)}
                <div class="no-code-service-wizard-content">
                    ${buildNoCodeServiceWizardContentMarkup(editor, activeStep)}
                </div>
            </div>
            <p id="modal-service-form-feedback" class="muted inventory-feedback"></p>
            ${buildNoCodeServiceWizardFooterMarkup(editor, activeStep)}
        </form>
    `;
}

function startNoCodeFieldEditor(fieldKey = "") {
    const editor = state.noCodeServiceEditor;
    if (!editor) {
        return;
    }
    if (!fieldKey) {
        editor.fieldEditor = noCodeFieldEditorSeed(null);
        renderNoCodeServiceEditor();
        return;
    }
    const found = (editor.fields || []).find((row) => String(row.field_key || "").trim() === String(fieldKey || "").trim());
    if (!found) {
        return;
    }
    editor.fieldEditor = noCodeFieldEditorSeed(found);
    renderNoCodeServiceEditor();
}

function removeNoCodeField(fieldKey) {
    const editor = state.noCodeServiceEditor;
    if (!editor) {
        return;
    }
    const wanted = String(fieldKey || "").trim();
    editor.fields = (editor.fields || []).filter((row) => String(row.field_key || "").trim() !== wanted);
    editor.fieldEditor = null;
    renderNoCodeServiceEditor();
}

function saveNoCodeFieldDraft() {
    const editor = state.noCodeServiceEditor;
    if (!editor || !editor.fieldEditor) {
        return { ok: false, message: "Editeur de champ indisponible." };
    }
    const labelInput = document.getElementById("service-field-label");
    const kindSelect = document.getElementById("service-field-kind");
    const requiredCheckbox = document.getElementById("service-field-required");
    const trackHistoryCheckbox = document.getElementById("service-field-track-history");
    const inlineEditableCheckbox = document.getElementById("service-field-inline-editable");
    const batchEditableCheckbox = document.getElementById("service-field-batch-editable");
    const quickFilterCheckbox = document.getElementById("service-field-quick-filter");
    const listSourceSelect = document.getElementById("service-field-list-source");
    const sharedListSelect = document.getElementById("service-field-shared-list");
    const optionsInput = document.getElementById("service-field-options");
    const defaultInput = document.getElementById("service-field-default");
    if (
        !(labelInput instanceof HTMLInputElement)
        || !(kindSelect instanceof HTMLSelectElement)
        || !(requiredCheckbox instanceof HTMLInputElement)
        || !(trackHistoryCheckbox instanceof HTMLInputElement)
        || !(inlineEditableCheckbox instanceof HTMLInputElement)
        || !(batchEditableCheckbox instanceof HTMLInputElement)
        || !(quickFilterCheckbox instanceof HTMLInputElement)
        || !(listSourceSelect instanceof HTMLSelectElement)
        || !(sharedListSelect instanceof HTMLSelectElement)
        || !(optionsInput instanceof HTMLInputElement)
        || !(defaultInput instanceof HTMLInputElement)
    ) {
        return { ok: false, message: "Champs editeur introuvables." };
    }
    const label = normalizeNoCodeText(labelInput.value);
    if (!label) {
        return { ok: false, message: "Libelle du champ requis." };
    }
    const fieldKind = normalizeNoCodeKind(kindSelect.value);
    const listSourceKind = fieldKind === "list"
        ? normalizeListSourceKind(listSourceSelect.value)
        : "local";
    const sharedListCode = fieldKind === "list" && listSourceKind === "shared"
        ? String(sharedListSelect.value || "").trim().toLowerCase()
        : "";
    const optionsValues = parseNoCodeOptions(optionsInput.value);
    if (fieldKind === "list" && listSourceKind === "local" && !optionsValues.length) {
        return { ok: false, message: "Ajoute au moins une option pour une liste." };
    }
    if (fieldKind === "list" && listSourceKind === "shared" && !sharedListCode) {
        return { ok: false, message: "Selectionne une liste partagee pour cette liste." };
    }
    let fieldKey = slugifyNoCodeIdentifier(label, "field");
    if (editor.fieldEditor.mode === "edit" && editor.fieldEditor.originalKey) {
        fieldKey = String(editor.fieldEditor.originalKey || "").trim();
    }
    const duplicate = (editor.fields || []).some((row) => {
        const key = String(row.field_key || "").trim();
        if (editor.fieldEditor.mode === "edit" && key === String(editor.fieldEditor.originalKey || "").trim()) {
            return false;
        }
        return key === fieldKey;
    });
    if (duplicate) {
        return { ok: false, message: "Un champ avec cette cle existe deja." };
    }
    const row = {
        field_key: fieldKey,
        label,
        field_kind: fieldKind,
        required: requiredCheckbox.checked,
        options: listSourceKind === "local" ? optionsValues.join(",") : "",
        default_value: normalizeNoCodeText(defaultInput.value),
        sort_order: 0,
        list_source_kind: listSourceKind,
        shared_list_code: sharedListCode,
        track_history: trackHistoryCheckbox.checked,
        inline_editable: inlineEditableCheckbox.checked,
        batch_editable: fieldKind === "list" && batchEditableCheckbox.checked,
        quick_filter: quickFilterCheckbox.checked,
    };
    if (editor.fieldEditor.mode === "edit") {
        editor.fields = (editor.fields || []).map((item) => (
            String(item.field_key || "").trim() === String(editor.fieldEditor.originalKey || "").trim()
                ? row
                : item
        ));
    } else {
        editor.fields = [...(editor.fields || []), row];
    }
    editor.fields = (editor.fields || []).map((item, index) => ({ ...item, sort_order: (index + 1) * 10 }));
    editor.fieldEditor = null;
    renderNoCodeServiceEditor();
    return { ok: true };
}

function noCodeRecordColumns(service) {
    const systemEntity = findNoCodeRelationSystemEntity(service?.code || "");
    if (systemEntity) {
        return noCodeRelationEntityFields(systemEntity).map((field) => ({
            key: `field:${String(field?.field_key || "").trim()}`,
            label: String(field?.label || field?.field_key || "").trim() || String(field?.field_key || ""),
            kind: normalizeNoCodeKind(field?.field_kind || "text"),
            field_key: String(field?.field_key || "").trim(),
        }));
    }
    const fields = noCodeCustomServiceFields(service);
    const columns = [
        ...fields.map((field) => ({
            key: `field:${String(field?.field_key || "").trim()}`,
            label: String(field?.label || field?.field_key || "").trim() || String(field?.field_key || ""),
            kind: normalizeNoCodeKind(field?.field_kind || "text"),
            field_key: String(field?.field_key || "").trim(),
            track_history: Boolean(field?.track_history),
            inline_editable: Boolean(field?.inline_editable),
            batch_editable: Boolean(field?.batch_editable),
            quick_filter: Boolean(field?.quick_filter),
            options: String(field?.options || ""),
            default_value: String(field?.default_value || ""),
            required: Boolean(field?.required),
        })),
    ];
    if (String(service?.code || "").trim().toLowerCase() === "emails") {
        columns.push(
            { key: "field:agents_lies", label: "Agents lies", kind: "text" },
            { key: "field:services_deduits", label: "Services deduits", kind: "text" },
        );
    }
    if (Boolean(service?.credentials_enabled)) {
        if (String(service?.code || "").trim().toLowerCase() !== "emails") {
            columns.push({ key: "credential:login", label: "Login", kind: "text" });
        }
    }
    if (Boolean(service?.child_enabled)) {
        columns.push({
            key: "child_count",
            label: String(service?.child_label || "Elements lies").trim() || "Elements lies",
            kind: "number",
        });
    }
    return columns;
}

function noCodeRecordColumnAllowsInlineEdit(service, column) {
    if (String(service?.code || "").trim().toLowerCase() === "emails") {
        return false;
    }
    return Boolean(column?.inline_editable);
}

function normalizeNoCodeRecordSortState(service, sortState = null) {
    const columns = noCodeRecordColumns(service);
    const validKeys = new Set(columns.map((column) => String(column?.key || "").trim()).filter(Boolean));
    const fallbackColumn = String(columns[0]?.key || "").trim();
    const requestedColumn = String(sortState?.column || "").trim();
    const column = validKeys.has(requestedColumn) ? requestedColumn : fallbackColumn;
    const direction = String(sortState?.direction || "").trim().toLowerCase() === "desc" ? "desc" : "asc";
    return { column, direction };
}

function noCodeRecordColumnValue(row, column) {
    const key = String(column?.key || "");
    if (key === "record_id") {
        return String(row?.id || "");
    }
    if (key === "credential:login") {
        return noCodeCredentialValueFromMap(row?.values || {}, "login");
    }
    if (key === "child_count") {
        return Number(Array.isArray(row?.children) ? row.children.length : 0);
    }
    if (key === "updated_at") {
        return String(row?.updated_at || "");
    }
    if (key.startsWith("field:")) {
        const fieldKey = key.slice("field:".length);
        return String(row?.values?.[fieldKey] || "");
    }
    if (key.startsWith("linked:")) {
        return String(row?.linked_column_values?.[key] || "");
    }
    return "";
}

function linkedColumnValuesForRow(row, column) {
    const key = String(column?.key || "").trim();
    const stored = row?.linked_column_items?.[key];
    if (Array.isArray(stored)) {
        return stored.map((value) => String(value || "").trim()).filter(Boolean);
    }
    const fallback = String(row?.linked_column_values?.[key] || "").trim();
    return fallback ? [fallback] : [];
}

function linkedColumnPreferredValue(row, column, values) {
    const candidates = Array.isArray(column?.preferred_value_keys) ? column.preferred_value_keys : [];
    for (const key of candidates) {
        const expected = String(row?.[key] ?? row?.values?.[key] ?? "").trim();
        if (!expected) {
            continue;
        }
        const match = values.find((value) => String(value || "").trim().toLowerCase() === expected.toLowerCase());
        if (match) {
            return match;
        }
    }
    return values[0] || "";
}

function renderLinkedColumnCell(row, column) {
    const values = linkedColumnValuesForRow(row, column);
    if (values.length <= 1) {
        return escapeHtml(values[0] || "");
    }
    const label = String(column?.label || "Informations liées").trim();
    const preferredValue = linkedColumnPreferredValue(row, column, values);
    const orderedValues = [
        preferredValue,
        ...values.filter((value) => value !== preferredValue),
    ].filter(Boolean);
    return `
        <select class="linked-column-values-select" aria-label="${escapeHtml(label)}" title="${escapeHtml(values.join("\n"))}">
            ${orderedValues.map((value, index) => `<option value="${escapeHtml(value)}" ${index === 0 ? "selected" : ""}>${escapeHtml(value)}</option>`).join("")}
        </select>
    `;
}

function relationColumnSource(context) {
    const isDirectory = Boolean(context?.kind && Array.isArray(context?.rows));
    if (isDirectory) {
        const serviceCode = directoryServiceCode(context.kind);
        return {
            service: findNoCodeRelationSystemEntity(serviceCode) || { code: serviceCode, label: context.kind === "services" ? "Services" : "Agents" },
            relations: Array.isArray(context.relations) ? context.relations : [],
            rows: Array.isArray(context.rows) ? context.rows : [],
        };
    }
    return {
        service: context?.service || context?.currentService || null,
        relations: Array.isArray(context?.relations) ? context.relations : [],
        rows: Array.isArray(context?.records) ? context.records : [],
    };
}

function linkedColumnsForContext(context) {
    return Array.isArray(context?.linkedColumns) ? context.linkedColumns : [];
}

function recordColumnsForContext(context) {
    return [
        ...noCodeRecordColumns(context?.service || context?.currentService || null),
        ...linkedColumnsForContext(context),
    ];
}

function availableLinkedColumnsForContext(context) {
    const source = relationColumnSource(context);
    const relationContext = {
        service: source.service,
        relations: source.relations,
    };
    return noCodeRecordRelationsForContext(relationContext)
        .filter((relation) => Boolean(relation?.is_active !== false && Number(relation?.id || 0) > 0))
        .flatMap((relation) => {
            const linkedServiceCode = noCodeRelationLinkedServiceCodeForContext(relationContext, relation);
            const linkedService = findNoCodeRelationEntity(linkedServiceCode);
            if (!linkedService) {
                return [];
            }
            const serviceLabel = String(linkedService.label || linkedService.code || linkedServiceCode).trim() || linkedServiceCode;
            return noCodeRecordColumns(linkedService)
                .filter((column) => String(column?.field_key || "").trim())
                .map((column) => {
                    const fieldKey = String(column.field_key || "").trim();
                    const fieldLabel = String(column.label || fieldKey).trim() || fieldKey;
                    return {
                        key: `linked:${Number(relation.id)}:${fieldKey}`,
                        label: fieldLabel,
                        relation_id: Number(relation.id),
                        service_code: linkedServiceCode,
                        service_label: serviceLabel,
                        field_key: fieldKey,
                        field_label: fieldLabel,
                        preferred_value_keys: linkedServiceCode === "emails" && fieldKey.toLowerCase() === "address"
                            ? ["mail"]
                            : [],
                    };
                });
        });
}

function linkedColumnMenuMarkup(context) {
    const selectedKeys = new Set(linkedColumnsForContext(context).map((column) => String(column?.key || "").trim()));
    const columns = availableLinkedColumnsForContext(context);
    if (!columns.length) {
        return "";
    }
    return `
        <div class="context-menu-group">
            <div class="context-menu-label">Informations liées</div>
            <button class="context-menu-item" type="button" data-tree-column-extra-action="linked:manage">
                <span>Ajouter des informations liées</span>
                <small>${selectedKeys.size ? `${selectedKeys.size} sélectionnée(s)` : "Choisir"}</small>
            </button>
            ${selectedKeys.size ? `
                <button class="context-menu-item" type="button" data-tree-column-extra-action="linked:clear">
                    <span>Retirer les colonnes liées</span>
                </button>
            ` : ""}
        </div>
    `;
}

function buildLinkedColumnsPickerMarkup(picker) {
    const selectedKeys = new Set(Array.isArray(picker?.selectedKeys) ? picker.selectedKeys : []);
    const groups = new Map();
    (Array.isArray(picker?.columns) ? picker.columns : []).forEach((column) => {
        const key = `${Number(column?.relation_id || 0)}:${String(column?.service_label || column?.service_code || "").trim()}`;
        const group = groups.get(key) || {
            label: String(column?.service_label || column?.service_code || "Information liée").trim(),
            columns: [],
        };
        group.columns.push(column);
        groups.set(key, group);
    });
    return `
        <form id="modal-linked-columns-picker-form" class="modal-form linked-columns-picker-form">
            <p class="muted">Choisissez une ou plusieurs informations à afficher dans le tableau. Elles sont lues depuis les fiches liées, sans modifier les données.</p>
            <div class="linked-columns-picker-list">
                ${Array.from(groups.values()).map((group) => `
                    <section class="linked-columns-picker-group">
                        <h4>${escapeHtml(group.label)}</h4>
                        ${group.columns.map((column) => `
                            <label class="check-field linked-columns-picker-option">
                                <input type="checkbox" name="linked_column_keys" value="${escapeHtml(column.key)}" ${selectedKeys.has(String(column.key || "")) ? "checked" : ""}>
                                <span>${escapeHtml(column.field_label || column.label || "Information")}</span>
                            </label>
                        `).join("")}
                    </section>
                `).join("") || '<p class="muted">Aucune information liée disponible.</p>'}
            </div>
            <div class="modal-actions">
                <button type="button" class="toolbar-btn" data-action="linked-columns-picker:back">Annuler</button>
                <button type="submit" class="primary-btn">Ajouter les informations sélectionnées</button>
            </div>
        </form>
    `;
}

function linkedColumnsContextFromSnapshot(snapshot) {
    if (snapshot?.type === "directory-list") {
        return snapshot.directoryContext || null;
    }
    if (snapshot?.type === "service-records") {
        return snapshot.noCodeServiceRecordContext || null;
    }
    return null;
}

function currentLinkedColumnsContext(origin) {
    return origin === "directory" ? state.directoryContext : state.noCodeServiceRecordContext;
}

function renderLinkedColumnsOrigin(origin) {
    if (origin === "directory") {
        renderDirectoryTreeView();
    } else {
        renderNoCodeServiceRecordsModal({ inline: true });
    }
}

function openLinkedColumnsPicker(context) {
    const columns = availableLinkedColumnsForContext(context);
    if (!columns.length) {
        return;
    }
    const origin = context === state.directoryContext ? "directory" : "service-records";
    pushModalBackSnapshot();
    state.linkedColumnsPicker = {
        origin,
        columns,
        selectedKeys: linkedColumnsForContext(context).map((column) => String(column?.key || "").trim()).filter(Boolean),
    };
    openModal("Ajouter des informations liées", buildLinkedColumnsPickerMarkup(state.linkedColumnsPicker), {
        width: "min(680px, calc(100vw - 40px))",
    });
}

async function submitLinkedColumnsPicker(form) {
    const picker = state.linkedColumnsPicker;
    if (!picker) {
        return;
    }
    const selectedKeys = new Set(
        Array.from(new FormData(form).getAll("linked_column_keys"))
            .map((value) => String(value || "").trim())
            .filter(Boolean),
    );
    const selectedColumns = (picker.columns || []).filter((column) => selectedKeys.has(String(column?.key || "")));
    const restored = await restoreNextModalBackSnapshot((snapshot) => {
        const context = linkedColumnsContextFromSnapshot(snapshot);
        if (!context) {
            return;
        }
        context.linkedColumns = selectedColumns;
        relationColumnSource(context).rows.forEach((row) => {
            delete row.linked_column_values;
            delete row.linked_column_items;
        });
    });
    state.linkedColumnsPicker = null;
    if (!restored) {
        return;
    }
    const context = currentLinkedColumnsContext(picker.origin);
    if (!context) {
        return;
    }
    await Promise.all(selectedColumns.map((column) => hydrateLinkedColumn(context, column)));
    renderLinkedColumnsOrigin(picker.origin);
}

async function hydrateLinkedColumn(context, column) {
    const source = relationColumnSource(context);
    const serviceCode = String(source.service?.code || "").trim().toLowerCase();
    const relationId = Number(column?.relation_id || 0);
    const rows = source.rows;
    if (!serviceCode || relationId <= 0 || !rows.length) {
        return;
    }
    const linksByRecord = await fetchNoCodeServiceRecordRelationLinksBatch(
        serviceCode,
        rows.map((row) => String(row?.id || "").trim()),
        relationId,
    );
    rows.forEach((row) => {
        const recordId = String(row?.id || "").trim();
        const links = Array.isArray(linksByRecord?.[recordId]) ? linksByRecord[recordId] : [];
        const values = links
            .map((link) => noCodeRecordColumnValue(link?.linked_record || {}, { key: `field:${String(column.field_key || "").trim()}` }))
            .map((value) => String(value || "").trim())
            .filter(Boolean);
        row.linked_column_values = row.linked_column_values && typeof row.linked_column_values === "object"
            ? row.linked_column_values
            : {};
        row.linked_column_items = row.linked_column_items && typeof row.linked_column_items === "object"
            ? row.linked_column_items
            : {};
        const uniqueValues = Array.from(new Set(values));
        row.linked_column_items[String(column.key || "")] = uniqueValues;
        row.linked_column_values[String(column.key || "")] = uniqueValues.join(", ");
    });
}

async function handleLinkedColumnMenuAction(context, action, trigger, render) {
    if (action === "linked:clear") {
        context.linkedColumns = [];
        relationColumnSource(context).rows.forEach((row) => {
            delete row.linked_column_values;
            delete row.linked_column_items;
        });
        render();
        return;
    }
    if (action === "linked:manage") {
        openLinkedColumnsPicker(context);
        return;
    }
    if (action !== "linked:add") {
        return;
    }
    const key = String(trigger?.dataset?.linkedColumnKey || "").trim();
    const column = availableLinkedColumnsForContext(context).find((item) => String(item.key || "") === key);
    if (!column) {
        return;
    }
    context.linkedColumns = [...linkedColumnsForContext(context), column];
    await hydrateLinkedColumn(context, column);
    render();
}

function noCodeRecordQuickFilterColumns(service) {
    return noCodeRecordColumns(service)
        .filter((column) => Boolean(column?.quick_filter) && String(column?.field_key || "").trim());
}

function noCodeRecordQuickFilterValueMap(context) {
    const source = context?.quickFilters && typeof context.quickFilters === "object" ? context.quickFilters : {};
    const output = {};
    for (const [key, value] of Object.entries(source)) {
        const normalizedKey = String(key || "").trim();
        const normalizedValue = String(value || "").trim();
        if (normalizedKey && normalizedValue) {
            output[normalizedKey] = normalizedValue;
        }
    }
    return output;
}

function defaultNoCodeRecordQuickFilters(service) {
    const defaults = {};
    noCodeRecordQuickFilterColumns(service).forEach((column) => {
        const fieldKey = String(column?.field_key || "").trim();
        const defaultValue = String(column?.default_value || "").trim();
        if (fieldKey && String(column?.kind || "") === "list" && defaultValue) {
            defaults[fieldKey] = defaultValue;
        }
    });
    if (String(service?.code || "").trim().toLowerCase() === "emails" && !defaults.status) {
        defaults.status = "Actif";
    }
    return defaults;
}

function noCodeServiceRecordsHasActiveFilters(context) {
    return Boolean(
        Object.keys(noCodeRecordQuickFilterValueMap(context)).length
        || String(context?.searchQuery || "").trim()
    );
}

function clearNoCodeServiceRecordsFilters(context) {
    if (!context) {
        return;
    }
    context.quickFilters = defaultNoCodeRecordQuickFilters(context.service || null);
    context.searchQuery = "";
    context.selectedRecordKeys = [];
    const searchInput = document.getElementById("service-records-search");
    if (searchInput instanceof HTMLInputElement) {
        searchInput.value = "";
    }
    Array.from(document.querySelectorAll("[data-no-code-quick-filter]")).forEach((control) => {
        if (control instanceof HTMLInputElement || control instanceof HTMLSelectElement) {
            const fieldKey = String(control.getAttribute("data-no-code-quick-filter") || "").trim();
            control.value = String(context.quickFilters?.[fieldKey] || "");
        }
    });
    const tree = context._recordsTreeView || null;
    if (tree) {
        tree.selectedRowKeys = new Set();
    }
}

function noCodeRecordRowsForContext(context) {
    const rows = Array.isArray(context?.records) ? context.records : [];
    const filters = noCodeRecordQuickFilterValueMap(context);
    const filterEntries = Object.entries(filters);
    if (!filterEntries.length) {
        return rows;
    }
    const columnsByFieldKey = new Map(
        noCodeRecordQuickFilterColumns(context?.service || null)
            .map((column) => [String(column?.field_key || "").trim(), column]),
    );
    return rows.filter((row) => filterEntries.every(([fieldKey, expected]) => {
        const column = columnsByFieldKey.get(fieldKey);
        if (!column) {
            return true;
        }
        const current = String(noCodeRecordColumnValue(row, column) || "").trim();
        if (String(column.kind || "text") === "list") {
            return current.toLowerCase() === String(expected || "").trim().toLowerCase();
        }
        return current.toLowerCase().includes(String(expected || "").trim().toLowerCase());
    }));
}

function noCodeRecordRelationsForContext(context) {
    const serviceCode = String(context?.service?.code || "").trim().toLowerCase();
    const relations = Array.isArray(context?.relations) ? context.relations : [];
    return relations.filter((relation) => {
        const source = String(relation?.source_service_code || "").trim().toLowerCase();
        const target = String(relation?.target_service_code || relation?.service_code || "").trim().toLowerCase();
        return serviceCode
            && Number(relation?.id || 0) > 0
            && relation?.is_active !== false
            && (source === serviceCode || target === serviceCode);
    });
}

function noCodeRelationLinkedServiceCodeForContext(context, relation) {
    const serviceCode = String(context?.service?.code || "").trim().toLowerCase();
    const source = String(relation?.source_service_code || "").trim().toLowerCase();
    const target = String(relation?.target_service_code || relation?.service_code || "").trim().toLowerCase();
    return serviceCode === source ? target : source;
}

function noCodeRelationLabelForContext(context, relation) {
    const serviceCode = String(context?.service?.code || "").trim().toLowerCase();
    const source = String(relation?.source_service_code || "").trim().toLowerCase();
    const linkedServiceCode = noCodeRelationLinkedServiceCodeForContext(context, relation);
    const linkedService = findNoCodeRelationEntity(linkedServiceCode) || { label: linkedServiceCode };
    // The configured label describes the target from the source service.  On the
    // reciprocal side it would name the current table, so use the actual linked
    // service instead (e.g. "Copieurs" when viewing an "Agents" record).
    if (serviceCode && serviceCode !== source) {
        return String(linkedService?.label || linkedServiceCode || "Fiches liees").trim();
    }
    return String(relation?.display_label || relation?.label || linkedService?.label || linkedServiceCode || "Fiches liees").trim();
}

function noCodeRelationMenuLabel(context, relation) {
    const label = noCodeRelationLabelForContext(context, relation);
    return `${label} lie(s)`;
}

function noCodeRelationAllowsMultipleLinkedFromCurrent(context, relation) {
    const serviceCode = String(context?.service?.code || "").trim().toLowerCase();
    const source = String(relation?.source_service_code || "").trim().toLowerCase();
    const cardinality = normalizeNoCodeRelationCardinality(relation?.cardinality || relation?.relation_type || "many_to_one");
    const currentIsSource = serviceCode === source;
    if (cardinality === "many_to_many") {
        return true;
    }
    if (cardinality === "one_to_many") {
        return currentIsSource;
    }
    return !currentIsSource;
}

function noCodeRelationAllowsMultipleCurrentFromLinked(context, relation) {
    const serviceCode = String(context?.service?.code || context?.currentService?.code || "").trim().toLowerCase();
    const source = String(relation?.source_service_code || "").trim().toLowerCase();
    const cardinality = normalizeNoCodeRelationCardinality(relation?.cardinality || relation?.relation_type || "many_to_one");
    const currentIsSource = serviceCode === source;
    if (cardinality === "many_to_many") {
        return true;
    }
    if (cardinality === "many_to_one") {
        return currentIsSource;
    }
    if (cardinality === "one_to_many") {
        return !currentIsSource;
    }
    return false;
}

function buildRelationAssignmentCandidatePickerMarkup({
    name = "linked_record_ids",
    linkedService = null,
    relationContext = null,
    relation = null,
    candidates = [],
    selectedIds = [],
} = {}) {
    const rows = Array.isArray(candidates) ? candidates : [];
    const selected = new Set((Array.isArray(selectedIds) ? selectedIds : []).map((value) => String(value || "").trim()).filter(Boolean));
    const allowsMany = noCodeRelationAllowsMultipleLinkedFromCurrent(relationContext, relation);
    const listMarkup = rows.map((row) => {
        const rowId = String(row?.id || row?.record_id || "").trim();
        if (!rowId) {
            return "";
        }
        const label = noCodeRecordPrimaryLabel(linkedService, row) || rowId;
        const values = row?.values && typeof row.values === "object" ? Object.values(row.values) : Object.values(row || {});
        const searchText = [rowId, label, ...values.map((value) => String(value || ""))]
            .join(" ")
            .toLowerCase();
        return `
            <label class="relation-assignment-option" data-relation-assignment-option data-search-text="${escapeHtml(searchText)}">
                <input type="checkbox" name="${escapeHtml(name)}" value="${escapeHtml(rowId)}" ${allowsMany ? "" : "data-relation-assignment-single"} ${selected.has(rowId) ? "checked" : ""}>
                <span>${escapeHtml(label)}</span>
            </label>
        `;
    }).join("");
    return `
        <section class="relation-assignment-picker" data-relation-assignment-picker>
            <div class="type-schema-fields-head">
                <h3>${escapeHtml(linkedService?.label || linkedService?.code || "Elements disponibles")}</h3>
                <span class="meta-badge">${rows.length} element(s)</span>
            </div>
            <label class="field full">
                <span>Recherche</span>
                <input type="search" data-relation-assignment-search placeholder="Filtrer les elements a assigner">
            </label>
            <div class="relation-assignment-options" data-relation-assignment-options>
                ${listMarkup || '<p class="muted">Aucune fiche disponible pour cette relation.</p>'}
            </div>
            <p class="muted">${allowsMany ? "Plusieurs elements peuvent etre coches." : "Cette relation accepte un seul element lie par fiche."}</p>
        </section>
    `;
}

function readRelationAssignmentSelectedIds(form) {
    if (!(form instanceof HTMLFormElement)) {
        return [];
    }
    return Array.from(form.querySelectorAll('input[name="linked_record_ids"]:checked'))
        .map((input) => String(input instanceof HTMLInputElement ? input.value : "").trim())
        .filter(Boolean);
}

function filterRelationAssignmentPicker(searchInput) {
    if (!(searchInput instanceof HTMLInputElement)) {
        return;
    }
    const picker = searchInput.closest("[data-relation-assignment-picker]");
    const query = String(searchInput.value || "").trim().toLowerCase();
    Array.from(picker?.querySelectorAll?.("[data-relation-assignment-option]") || []).forEach((option) => {
        if (!(option instanceof HTMLElement)) {
            return;
        }
        const haystack = String(option.dataset.searchText || "").toLowerCase();
        option.hidden = Boolean(query) && !haystack.includes(query);
    });
}

function relationPickerFromElement(element) {
    return element instanceof Element ? element.closest("[data-relation-dual-picker]") : null;
}

function relationPickerSelectForPicker(picker) {
    const select = picker?.querySelector?.("[data-record-relation-select]");
    return select instanceof HTMLSelectElement ? select : null;
}

function relationPickerSelectedItem(picker, listSelector) {
    const item = picker?.querySelector?.(`${listSelector} .relation-picker-item.is-selected`);
    return item instanceof HTMLElement ? item : null;
}

function relationPickerOptionLabel(option) {
    return String(option?.textContent || "").trim();
}

function relationPickerButtonMarkupFromOption(option, linked = false) {
    const value = String(option?.value || "").trim();
    const label = relationPickerOptionLabel(option) || value;
    return `
        <button class="relation-picker-item ${linked ? "is-linked" : ""}" type="button"
            data-relation-picker-item="${escapeHtml(value)}"
            data-search-text="${escapeHtml(`${value} ${label}`.toLowerCase())}">
            <span>${escapeHtml(label)}</span>
        </button>
    `;
}

function relationPickerRefreshEmptyStates(picker) {
    if (!(picker instanceof HTMLElement)) {
        return;
    }
    [
        ["[data-relation-picker-available]", "Aucun element disponible."],
        ["[data-relation-picker-linked]", "Aucun objet lie."],
    ].forEach(([selector, message]) => {
        const list = picker.querySelector(selector);
        if (!(list instanceof HTMLElement)) {
            return;
        }
        const hasItems = Boolean(list.querySelector(".relation-picker-item"));
        const existingEmpty = list.querySelector("[data-relation-picker-empty]");
        if (hasItems && existingEmpty instanceof HTMLElement) {
            existingEmpty.remove();
        } else if (!hasItems && !(existingEmpty instanceof HTMLElement)) {
            list.insertAdjacentHTML("beforeend", `<p class="muted" data-relation-picker-empty>${escapeHtml(message)}</p>`);
        }
    });
}

function relationPickerSetSelectedItem(item) {
    if (!(item instanceof HTMLElement)) {
        return;
    }
    const list = item.parentElement;
    Array.from(list?.querySelectorAll?.(".relation-picker-item.is-selected") || []).forEach((row) => {
        row.classList.remove("is-selected");
    });
    item.classList.add("is-selected");
}

function relationPickerMoveItem(item) {
    if (!(item instanceof HTMLElement)) {
        return;
    }
    const picker = relationPickerFromElement(item);
    if (!(picker instanceof HTMLElement)) {
        return;
    }
    relationPickerSetSelectedItem(item);
    const inLinkedList = Boolean(item.closest("[data-relation-picker-linked]"));
    relationPickerMoveSelected(picker, inLinkedList ? "remove" : "add");
}

function relationPickerCurrentSelectedCount(select) {
    return Array.from(select?.options || []).filter((option) => option.selected && String(option.value || "").trim()).length;
}

function relationPickerMoveSelected(picker, direction) {
    if (!(picker instanceof HTMLElement)) {
        return;
    }
    const select = relationPickerSelectForPicker(picker);
    if (!(select instanceof HTMLSelectElement) || select.disabled) {
        return;
    }
    const fromSelector = direction === "add" ? "[data-relation-picker-available]" : "[data-relation-picker-linked]";
    const toSelector = direction === "add" ? "[data-relation-picker-linked]" : "[data-relation-picker-available]";
    const item = relationPickerSelectedItem(picker, fromSelector);
    if (!(item instanceof HTMLElement)) {
        return;
    }
    const value = String(item.dataset.relationPickerItem || "").trim();
    const option = Array.from(select.options).find((row) => String(row.value || "").trim() === value);
    if (!(option instanceof HTMLOptionElement)) {
        return;
    }
    if (direction === "add") {
        const maxSelected = Number(select.dataset.maxSelected || 0);
        if (maxSelected > 0 && relationPickerCurrentSelectedCount(select) >= maxSelected) {
            const feedback = document.getElementById("modal-directory-record-feedback") || document.getElementById("modal-service-record-feedback");
            if (feedback instanceof HTMLElement) {
                feedback.textContent = `Selection limitee a ${maxSelected} element(s) pour cette relation.`;
            }
            return;
        }
        if (!select.multiple) {
            Array.from(select.options).forEach((row) => {
                row.selected = false;
            });
            const linkedList = picker.querySelector("[data-relation-picker-linked]");
            const availableList = picker.querySelector("[data-relation-picker-available]");
            Array.from(linkedList?.querySelectorAll?.(".relation-picker-item") || []).forEach((button) => {
                if (availableList instanceof HTMLElement) {
                    button.classList.remove("is-linked", "is-selected");
                    availableList.appendChild(button);
                }
            });
        }
        option.selected = true;
        item.classList.add("is-linked");
    } else {
        option.selected = false;
        item.classList.remove("is-linked");
    }
    item.classList.remove("is-selected");
    const targetList = picker.querySelector(toSelector);
    if (targetList instanceof HTMLElement) {
        targetList.appendChild(item);
    }
    relationPickerRefreshEmptyStates(picker);
}

function relationPickerAddBatchSelection(picker) {
    if (!(picker instanceof HTMLElement)) {
        return;
    }
    const checkedItems = Array.from(picker.querySelectorAll("[data-relation-picker-batch-check]:checked"))
        .map((input) => input.closest("[data-relation-picker-item]"))
        .filter((item) => item instanceof HTMLElement);
    if (!checkedItems.length) {
        const feedback = document.getElementById("modal-directory-record-feedback") || document.getElementById("modal-service-record-feedback");
        if (feedback instanceof HTMLElement) {
            feedback.textContent = "Cochez au moins un element a lier.";
        }
        return;
    }
    checkedItems.forEach((item) => {
        relationPickerSetSelectedItem(item);
        relationPickerMoveSelected(picker, "add");
    });
}

function filterRelationDualPicker(searchInput) {
    const picker = relationPickerFromElement(searchInput);
    const query = String(searchInput?.value || "").trim().toLowerCase();
    Array.from(picker?.querySelectorAll?.("[data-relation-picker-available] .relation-picker-item") || []).forEach((option) => {
        if (!(option instanceof HTMLElement)) {
            return;
        }
        const haystack = String(option.dataset.searchText || "").toLowerCase();
        option.hidden = Boolean(query) && !haystack.includes(query);
    });
}

function noCodeRecordPrimaryLabel(service, record) {
    const columns = noCodeRecordColumns(service || null);
    const preferred = columns.find((column) => ["label", "name", "nom", "title"].includes(String(column?.field_key || column?.key || "").toLowerCase()))
        || columns[0]
        || null;
    const value = preferred ? String(noCodeRecordColumnValue(record, preferred) || "").trim() : "";
    return value || String(record?.label || record?.name || record?.id || record?.record_id || "").trim();
}

function noCodeRecordSearchText(service, record) {
    const values = record?.values && typeof record.values === "object"
        ? Object.values(record.values)
        : Object.values(record || {});
    return [
        String(record?.id || record?.record_id || ""),
        noCodeRecordPrimaryLabel(service, record),
        ...values.map((value) => String(value || "")),
    ].join(" ").toLowerCase();
}

function noCodeRelationCandidateRows(context) {
    const links = Array.isArray(context?.links) ? context.links : [];
    const linkedIds = new Set(
        links.map((link) => String(link?.linked_record?.id || "").trim()).filter(Boolean),
    );
    return (Array.isArray(context?.candidates) ? context.candidates : [])
        .filter((row) => !linkedIds.has(String(row?.id || row?.record_id || "").trim()));
}

function noCodeRecordRelationState(editor, relationId) {
    const states = editor?.relationStates && typeof editor.relationStates === "object" ? editor.relationStates : {};
    return states[String(relationId || "")] || {};
}

function noCodeRecordEditableRelationsForContext(context) {
    return noCodeRecordRelationsForContext(context).filter((relation) => {
        if (!relation || Number(relation.id || 0) <= 0) {
            return false;
        }
        const linkedServiceCode = noCodeRelationLinkedServiceCodeForContext(context, relation);
        return relation.is_active !== false && Boolean(findNoCodeRelationEntity(linkedServiceCode));
    });
}

function isDirectoryAgentServiceRelation(context, relation) {
    const serviceCode = String(context?.service?.code || "").trim().toLowerCase();
    const linkedCode = noCodeRelationLinkedServiceCodeForContext(context, relation);
    return Boolean(state.directoryRecordEditor)
        && serviceCode === "utilisateurs"
        && linkedCode === "services";
}

function isDirectoryAgentEmailRelation(context, relation) {
    const serviceCode = String(context?.service?.code || "").trim().toLowerCase();
    const linkedCode = noCodeRelationLinkedServiceCodeForContext(context, relation);
    return Boolean(state.directoryRecordEditor)
        && serviceCode === "utilisateurs"
        && linkedCode === "emails";
}

function directoryPrincipalServiceIds() {
    const row = state.directoryRecordEditor?.row || {};
    return new Set(
        (Array.isArray(row?.ad_service_ids) ? row.ad_service_ids : [])
            .map((value) => String(value || "").trim())
            .filter(Boolean),
    );
}

function directoryPrincipalEmailIds() {
    const row = state.directoryRecordEditor?.row || {};
    const protectedIds = (Array.isArray(row?.ad_email_ids) ? row.ad_email_ids : [])
        .map((value) => String(value || "").trim())
        .filter(Boolean);
    if (protectedIds.length) {
        return new Set(protectedIds);
    }
    const mail = String(row?.mail || "").trim().toLowerCase();
    if (!mail) {
        return new Set();
    }
    const linkedLabels = String(row?.linked_emails || "")
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean);
    const linkedIds = Array.isArray(row?.linked_email_ids)
        ? row.linked_email_ids.map((value) => String(value || "").trim())
        : [];
    const exactIndex = linkedLabels.findIndex((label) => label.toLowerCase() === mail);
    const fallbackIndex = linkedLabels.length === 1 || (!linkedLabels.length && linkedIds.length === 1) ? 0 : -1;
    const linkedId = linkedIds[exactIndex >= 0 ? exactIndex : fallbackIndex] || "";
    return new Set(linkedId ? [linkedId] : []);
}

function directoryComplementaryServiceLimit() {
    const principalCount = directoryPrincipalServiceIds().size;
    return Math.max(0, 3 - principalCount);
}

function protectedRelationLinkedRecordIds(context, relation) {
    if (isDirectoryAgentServiceRelation(context, relation)) {
        return directoryPrincipalServiceIds();
    }
    if (isDirectoryAgentEmailRelation(context, relation)) {
        return directoryPrincipalEmailIds();
    }
    return new Set();
}

function relationEditorRowsForState(context, relation, rows) {
    const source = Array.isArray(rows) ? rows : [];
    const protectedIds = protectedRelationLinkedRecordIds(context, relation);
    if (!protectedIds.size) {
        return source;
    }
    return source.filter((row) => {
        const record = row?.linked_record && typeof row.linked_record === "object" ? row.linked_record : row;
        return !protectedIds.has(String(record?.id || record?.record_id || "").trim());
    });
}

function mergeRelationSummaryItemsPreferLinked(items = []) {
    const merged = new Map();
    (Array.isArray(items) ? items : []).forEach((item) => {
        const label = String(item?.label || item?.id || "").trim();
        if (!label) {
            return;
        }
        const key = label.toLowerCase();
        const current = merged.get(key);
        const currentClickable = Boolean(current?.linkedServiceCode && current?.recordId);
        const nextClickable = Boolean(item?.linkedServiceCode && item?.recordId);
        if (!current || (nextClickable && !currentClickable)) {
            merged.set(key, {
                ...item,
                id: String(item?.id || key).trim() || key,
                label,
            });
        }
    });
    return Array.from(merged.values());
}

function directoryAgentAdEmailSummaryItems(row) {
    const mail = String(row?.mail || "").trim();
    if (!mail) {
        return [];
    }
    const linkedLabels = String(row?.linked_emails || "")
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean);
    const linkedIds = Array.isArray(row?.linked_email_ids)
        ? row.linked_email_ids.map((value) => String(value || "").trim())
        : [];
    const adLinkedIds = Array.isArray(row?.ad_email_ids)
        ? row.ad_email_ids.map((value) => String(value || "").trim()).filter(Boolean)
        : [];
    const exactIndex = linkedLabels.findIndex((label) => label.toLowerCase() === mail.toLowerCase());
    const fallbackIndex = linkedLabels.length === 1 || (!linkedLabels.length && linkedIds.length === 1) ? 0 : -1;
    const linkedId = adLinkedIds[0] || linkedIds[exactIndex >= 0 ? exactIndex : fallbackIndex] || "";
    return [{
        id: linkedId || mail.toLowerCase(),
        label: mail,
        linkedServiceCode: "emails",
        recordId: linkedId,
    }];
}

function directoryAgentAdServiceSummaryItems(row) {
    const labels = String(row?.ad_services || row?.service || "")
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean);
    const ids = Array.isArray(row?.ad_service_ids)
        ? row.ad_service_ids.map((value) => String(value || "").trim())
        : [];
    return labels.map((label, index) => ({
        id: ids[index] || label.toLowerCase(),
        label,
        linkedServiceCode: "services",
        recordId: ids[index] || "",
    }));
}

function buildNoCodeRecordDirectRelationControl(context, editor, relation) {
    const relationId = String(relation?.id || "");
    const linkedServiceCode = noCodeRelationLinkedServiceCodeForContext(context, relation);
    const linkedService = findNoCodeService(linkedServiceCode) || { code: linkedServiceCode, label: linkedServiceCode };
    const stateForRelation = noCodeRecordRelationState(editor, relationId);
    const links = relationEditorRowsForState(context, relation, Array.isArray(stateForRelation.links) ? stateForRelation.links : []);
    const candidates = relationEditorRowsForState(context, relation, Array.isArray(stateForRelation.candidates) ? stateForRelation.candidates : []);
    const candidatesLoading = Boolean(stateForRelation.candidatesLoading);
    const candidatesLoaded = Boolean(stateForRelation.candidatesLoaded);
    const selectedIds = new Set(links.map((link) => String(link?.linked_record?.id || "").trim()).filter(Boolean));
    const allowsMany = noCodeRelationAllowsMultipleLinkedFromCurrent(context, relation);
    const batchSelectionMode = allowsMany && Boolean(stateForRelation.batchSelectionMode);
    const allRows = [
        ...links.map((link) => link.linked_record).filter(Boolean),
        ...candidates,
    ];
    const seen = new Set();
    const optionRows = allRows.filter((row) => {
        const id = String(row?.id || row?.record_id || "").trim();
        if (!id || seen.has(id)) {
            return false;
        }
        seen.add(id);
        return true;
    });
    const hiddenOptions = optionRows.map((row) => {
        const rowId = String(row?.id || row?.record_id || "").trim();
        const label = noCodeRecordPrimaryLabel(linkedService, row) || rowId;
        return `<option value="${escapeHtml(rowId)}" ${selectedIds.has(rowId) ? "selected" : ""}>${escapeHtml(label)}</option>`;
    }).join("");
    const availableRows = optionRows.filter((row) => !selectedIds.has(String(row?.id || row?.record_id || "").trim()));
    const linkedRows = optionRows.filter((row) => selectedIds.has(String(row?.id || row?.record_id || "").trim()));
    const optionButtonMarkup = (row, selected = false) => {
        const rowId = String(row?.id || row?.record_id || "").trim();
        const rowLabel = noCodeRecordPrimaryLabel(linkedService, row) || rowId;
        const values = row?.values && typeof row.values === "object" ? Object.values(row.values) : Object.values(row || {});
        const searchText = [rowId, rowLabel, ...values.map((value) => String(value || ""))]
            .join(" ")
            .toLowerCase();
        if (batchSelectionMode && !selected) {
            return `
                <label class="relation-picker-item" data-relation-picker-item="${escapeHtml(rowId)}" data-search-text="${escapeHtml(searchText)}">
                    <input type="checkbox" data-relation-picker-batch-check value="${escapeHtml(rowId)}">
                    <span>${escapeHtml(rowLabel)}</span>
                </label>
            `;
        }
        return `
            <button class="relation-picker-item ${selected ? "is-linked" : ""}" type="button"
                data-relation-picker-item="${escapeHtml(rowId)}"
                data-search-text="${escapeHtml(searchText)}">
                <span>${escapeHtml(rowLabel)}</span>
            </button>
        `;
    };
    const serviceComplementLimit = isDirectoryAgentServiceRelation(context, relation)
        ? directoryComplementaryServiceLimit()
        : 0;
    const serviceComplementLimitReached = isDirectoryAgentServiceRelation(context, relation) && serviceComplementLimit === 0;
    const label = isDirectoryAgentServiceRelation(context, relation)
        ? "Services complementaires"
        : noCodeRelationLabelForContext(context, relation);
    const loading = stateForRelation.loading;
    const helper = isDirectoryAgentServiceRelation(context, relation)
        ? `Le service AD principal reste gere par la synchronisation. Maximum ${3} services au total, donc ${serviceComplementLimit} complementaire(s) possible(s).`
        : "";
    const candidateConstraintMessage = String(stateForRelation.candidateConstraintMessage || "").trim();
    return `
        <section class="relation-dual-picker ${allowsMany ? "full" : ""}" data-relation-dual-picker data-relation-id="${escapeHtml(relationId)}">
            <div class="type-schema-fields-head">
                <h3>${escapeHtml(label || linkedService.label || "Relation")}</h3>
                <span class="meta-badge">${escapeHtml(String(linkedRows.length))} lie(s)</span>
                ${allowsMany ? createActionButtonMarkup({
                    preset: "secondary",
                    type: "button",
                    action: "relation-picker:batch-toggle",
                    label: batchSelectionMode ? "Selection individuelle" : "Selection par lot",
                    data: { relation_id: relationId },
                    disabled: loading || candidatesLoading || !candidatesLoaded || serviceComplementLimitReached,
                }) : ""}
            </div>
            <select name="record_relation_${escapeHtml(relationId)}" data-record-relation-select data-relation-id="${escapeHtml(relationId)}" ${serviceComplementLimit ? `data-max-selected="${escapeHtml(String(serviceComplementLimit))}"` : ""} ${allowsMany ? "multiple" : ""} hidden ${loading || serviceComplementLimitReached ? "disabled" : ""}>
                ${allowsMany ? "" : '<option value="">Aucun</option>'}
                ${hiddenOptions}
            </select>
            <div class="relation-dual-picker-grid">
                <div class="relation-dual-picker-pane">
                    <label class="field full">
                        <span>Recherche</span>
                        <input type="search" data-relation-picker-search placeholder="Filtrer les elements disponibles" ${loading || serviceComplementLimitReached ? "disabled" : ""}>
                    </label>
                    <div class="relation-picker-list" data-relation-picker-available>
                        ${candidatesLoading
                            ? '<p class="muted" data-relation-picker-empty>Chargement des elements disponibles...</p>'
                            : (availableRows.map((row) => optionButtonMarkup(row, false)).join("")
                                || `<p class="muted" data-relation-picker-empty>${candidatesLoaded ? "Aucun element disponible." : "Ouvre ce panneau pour charger les elements disponibles."}</p>`)}
                    </div>
                    ${batchSelectionMode
                        ? createActionButtonMarkup({
                            preset: "add",
                            type: "button",
                            action: "relation-picker:batch-add",
                            label: "Ajouter la selection",
                            disabled: loading || candidatesLoading || !candidatesLoaded || serviceComplementLimitReached,
                        })
                        : createIconActionButtonMarkup({
                            icon: "add",
                            action: "relation-picker:add",
                            title: "Ajouter la selection",
                            disabled: loading || candidatesLoading || !candidatesLoaded || serviceComplementLimitReached,
                        })}
                </div>
                <div class="relation-dual-picker-pane">
                    <div class="relation-picker-pane-title">
                        <span>Objets lies</span>
                        <span class="meta-badge">${escapeHtml(String(linkedRows.length))}</span>
                    </div>
                    <div class="relation-picker-list" data-relation-picker-linked>
                        ${linkedRows.map((row) => optionButtonMarkup(row, true)).join("") || '<p class="muted" data-relation-picker-empty>Aucun objet lie.</p>'}
                    </div>
                    ${createIconActionButtonMarkup({
                        icon: "delete",
                        action: "relation-picker:remove",
                        title: "Retirer la selection",
                        danger: true,
                        disabled: loading || !linkedRows.length,
                    })}
                </div>
            </div>
            ${[helper, candidateConstraintMessage, batchSelectionMode ? "Cochez les fiches voulues, puis ajoutez-les en une seule fois." : ""].filter(Boolean).map((message) => `<p class="muted">${escapeHtml(message)}</p>`).join("")}
        </section>
    `;
}

function noCodeRelationSummaryItems(context, editor, relation) {
    const relationId = String(relation?.id || "");
    const stateForRelation = noCodeRecordRelationState(editor, relationId);
    const linkedCode = noCodeRelationLinkedServiceCodeForContext(context, relation);
    const links = Array.isArray(stateForRelation.links) ? stateForRelation.links : [];
    const rows = links
        .map((link) => link?.linked_record || null)
        .filter(Boolean)
        .map((record) => ({
            id: String(record?.id || record?.record_id || "").trim(),
            label: noCodeRecordPrimaryLabel(
                findNoCodeRelationEntity(linkedCode) || null,
                record,
            ),
            linkedServiceCode: linkedCode,
            recordId: String(record?.id || record?.record_id || "").trim(),
            record,
        }))
        .filter((row) => row.id || row.label);
    rows.forEach((row) => rememberLinkedRecordViewCache(row.linkedServiceCode, row.record));
    if (String(context?.service?.code || "").trim().toLowerCase() === "utilisateurs" && linkedCode === "emails") {
        return mergeRelationSummaryItemsPreferLinked([
            ...rows,
            ...directoryAgentAdEmailSummaryItems(state.directoryRecordEditor?.row || {}),
        ]);
    }
    if (isDirectoryAgentServiceRelation(context, relation)) {
        return mergeRelationSummaryItemsPreferLinked([
            ...directoryAgentAdServiceSummaryItems(state.directoryRecordEditor?.row || {}),
            ...rows,
        ]);
    }
    return rows;
}

function noCodeRelationSummaryChipMarkup(item) {
    const linkedServiceCode = String(item?.linkedServiceCode || "").trim().toLowerCase();
    const recordId = String(item?.recordId || "").trim();
    const label = String(item?.label || item?.id || "").trim();
    if (linkedServiceCode && recordId) {
        return `
            <button class="relation-summary-chip is-clickable" type="button"
                data-relation-summary-record
                data-linked-service-code="${escapeHtml(linkedServiceCode)}"
                data-record-id="${escapeHtml(recordId)}"
                title="Consulter la fiche liee">
                ${escapeHtml(label)}
            </button>
        `;
    }
    return `<span class="relation-summary-chip">${escapeHtml(label)}</span>`;
}

function linkedRecordViewCacheKey(serviceCode, recordId) {
    const normalizedCode = normalizeNoCodeText(serviceCode).toLowerCase();
    const normalizedRecordId = String(recordId || "").trim();
    return normalizedCode && normalizedRecordId ? `${normalizedCode}:${normalizedRecordId}` : "";
}

function rememberLinkedRecordViewCache(serviceCode, record) {
    const recordId = String(record?.id || record?.record_id || "").trim();
    const key = linkedRecordViewCacheKey(serviceCode, recordId);
    if (!key) {
        return;
    }
    state.linkedRecordViewCache = state.linkedRecordViewCache && typeof state.linkedRecordViewCache === "object"
        ? state.linkedRecordViewCache
        : {};
    state.linkedRecordViewCache[key] = record;
    const keys = Object.keys(state.linkedRecordViewCache);
    if (keys.length > LINKED_RECORD_VIEW_CACHE_LIMIT) {
        keys.slice(0, keys.length - LINKED_RECORD_VIEW_CACHE_LIMIT).forEach((oldKey) => {
            delete state.linkedRecordViewCache[oldKey];
        });
    }
}

function cachedLinkedRecordView(serviceCode, recordId) {
    const key = linkedRecordViewCacheKey(serviceCode, recordId);
    return key ? (state.linkedRecordViewCache?.[key] || null) : null;
}

function createLinkedRecordViewContext(service, record) {
    return {
        service,
        records: [record],
        relations: [],
        recordsPage: {
            total: 1,
            limit: 1,
            offset: 0,
            source: "linked",
        },
        isLinkedRecordViewContext: true,
        importPreview: null,
        importFile: null,
        importSheetName: "",
        importAvailableSheets: [],
        importHeaderMode: "auto",
        importHeaderRowNumber: 1,
        quickFilters: defaultNoCodeRecordQuickFilters(service),
        importCredentialMode: "preserve_on_blank",
        importColumnPage: 0,
        _recordsTreeView: null,
        searchQuery: "",
        selectedRecordKeys: [],
        sort: normalizeNoCodeRecordSortState(service),
    };
}

function findNoCodeRecordById(rows, recordId) {
    const wanted = String(recordId || "").trim();
    if (!wanted) {
        return null;
    }
    return (Array.isArray(rows) ? rows : [])
        .find((row) => String(row?.id || row?.record_id || "").trim() === wanted) || null;
}

async function fetchLinkedNoCodeRecord(serviceCode, recordId) {
    const normalizedCode = normalizeNoCodeText(serviceCode).toLowerCase();
    const normalizedRecordId = String(recordId || "").trim();
    const cached = cachedLinkedRecordView(normalizedCode, normalizedRecordId);
    if (cached) {
        return cached;
    }
    const searchedPage = await fetchNoCodeServiceRecordsPage(normalizedCode, {
        search: normalizedRecordId,
        limit: 50,
        offset: 0,
        sort: "label",
        direction: "asc",
    });
    let record = findNoCodeRecordById(searchedPage?.items, normalizedRecordId);
    if (!record) {
        const firstPage = await fetchNoCodeServiceRecordsPage(normalizedCode, {
            search: "",
            limit: 500,
            offset: 0,
            sort: "label",
            direction: "asc",
        });
        record = findNoCodeRecordById(firstPage?.items, normalizedRecordId);
    }
    rememberLinkedRecordViewCache(normalizedCode, record);
    return record;
}

async function resolveNoCodeRelationEntity(serviceCode) {
    const normalizedCode = normalizeNoCodeText(serviceCode).toLowerCase();
    if (!normalizedCode) {
        return null;
    }
    let service = findNoCodeRelationEntity(normalizedCode);
    if (!service) {
        await loadAdministrationData({
            includeModules: false,
            includeRoles: false,
            includeUsers: false,
            includeServices: true,
            includeSharedLists: false,
        });
        service = findNoCodeRelationEntity(normalizedCode);
    }
    return service || null;
}

function noCodeRelationReadableLabel(context, relation) {
    const serviceCode = String(context?.service?.code || "").trim().toLowerCase();
    const linkedCode = noCodeRelationLinkedServiceCodeForContext(context, relation);
    if (serviceCode === "emails") {
        if (linkedCode === "utilisateurs") {
            return "Agent";
        }
        if (linkedCode === "services") {
            return "Services";
        }
    }
    if (serviceCode === "utilisateurs") {
        if (linkedCode === "emails") {
            return "Mail";
        }
        if (linkedCode === "services") {
            return "Services";
        }
        const linkedEntity = findNoCodeRelationEntity(linkedCode);
        return String(linkedEntity?.label || linkedCode || "Relation").trim();
    }
    return noCodeRelationLabelForContext(context, relation);
}

function noCodeRelationManageObjectLabel(serviceCode, label = "") {
    const normalizedCode = String(serviceCode || "").trim().toLowerCase();
    if (normalizedCode === "emails") {
        return "mails";
    }
    if (normalizedCode === "services") {
        return "services";
    }
    if (normalizedCode === "utilisateurs") {
        return "agents";
    }
    const rawLabel = String(label || normalizedCode || "relations").trim().toLowerCase();
    if (!rawLabel) {
        return "relations";
    }
    return /[sx]$/i.test(rawLabel) ? rawLabel : `${rawLabel}s`;
}

function noCodeRelationManageActionLabel(context, relation) {
    const serviceCode = String(context?.service?.code || "").trim().toLowerCase();
    const linkedCode = noCodeRelationLinkedServiceCodeForContext(context, relation);
    const currentEntityLabel = noCodeRelationManageObjectLabel(serviceCode, context?.service?.label || "");
    if (serviceCode === "utilisateurs") {
        if (linkedCode === "emails") {
            return "Gerer les mails de l'agent";
        }
        if (linkedCode === "services") {
            return "Gerer les services de l'agent";
        }
        const linkedLabel = noCodeRelationManageObjectLabel(
            linkedCode,
            findNoCodeRelationEntity(linkedCode)?.label || noCodeRelationReadableLabel(context, relation),
        );
        return `Gerer les ${linkedLabel} de l'agent`;
    }
    if (serviceCode === "emails") {
        if (linkedCode === "utilisateurs") {
            return "Gerer les agents du mail";
        }
        if (linkedCode === "services") {
            return "Gerer les services du mail";
        }
    }
    if (serviceCode === "services") {
        if (linkedCode === "utilisateurs") {
            return "Gerer les agents du service";
        }
        if (linkedCode === "emails") {
            return "Gerer les mails du service";
        }
    }
    const label = noCodeRelationManageObjectLabel(linkedCode, noCodeRelationReadableLabel(context, relation));
    const suffix = currentEntityLabel ? ` pour ${currentEntityLabel}` : "";
    return `Gerer les ${label}${suffix}`;
}

function buildNoCodeReadonlyRelationSummaryCard(section) {
    const label = String(section?.label || "Relation").trim();
    const rows = Array.isArray(section?.rows) ? section.rows : [];
    rows.forEach((row) => rememberLinkedRecordViewCache(row.linkedServiceCode, row.record));
    return `
        <div class="relation-summary-card relation-summary-card-readonly">
            <div class="relation-summary-toggle">
                <div class="relation-summary-row">
                    <strong>${escapeHtml(label || "Relation")}</strong>
                    <div class="relation-summary-values">
                        ${rows.length
                            ? rows.map((item) => noCodeRelationSummaryChipMarkup(item)).join("")
                            : '<span class="muted">Aucun objet lie.</span>'}
                    </div>
                </div>
            </div>
        </div>
    `;
}

function mergeNoCodeReadonlyRelationSummarySections(sections = []) {
    const merged = new Map();
    (Array.isArray(sections) ? sections : []).forEach((section) => {
        const label = String(section?.label || "Relation").trim() || "Relation";
        const labelKey = label.toLowerCase();
        if (!merged.has(labelKey)) {
            merged.set(labelKey, {
                label,
                rows: [],
                rowKeys: new Set(),
            });
        }
        const target = merged.get(labelKey);
        (Array.isArray(section?.rows) ? section.rows : []).forEach((row) => {
            const rowKey = [
                String(row?.linkedServiceCode || "").trim().toLowerCase(),
                String(row?.recordId || row?.id || "").trim().toLowerCase(),
                String(row?.label || "").trim().toLowerCase(),
            ].filter(Boolean).join(":");
            if (!rowKey || target.rowKeys.has(rowKey)) {
                return;
            }
            target.rowKeys.add(rowKey);
            target.rows.push(row);
        });
    });
    return Array.from(merged.values()).map((section) => ({
        label: section.label,
        rows: section.rows,
    }));
}

function buildNoCodeRecordRelationsSummaryMarkup(context, editor, relations) {
    const openRelationIds = new Set(
        (Array.isArray(editor?.openRelationEditorIds) ? editor.openRelationEditorIds : [])
            .map((value) => String(value || "").trim())
            .filter(Boolean),
    );
    const editableRows = (Array.isArray(relations) ? relations : []).map((relation) => {
        const relationId = String(relation?.id || "").trim();
        const label = noCodeRelationReadableLabel(context, relation);
        const actionLabel = noCodeRelationManageActionLabel(context, relation);
        const items = noCodeRelationSummaryItems(context, editor, relation);
        const loading = Boolean(noCodeRecordRelationState(editor, relationId).loading);
        return `
            <details class="relation-summary-card relation-editor-accordion" data-relation-editor-accordion data-relation-id="${escapeHtml(relationId)}" ${openRelationIds.has(relationId) ? "open" : ""}>
                <summary class="relation-summary-toggle">
                    <div class="relation-summary-row">
                        <strong>${escapeHtml(label || "Relation")}</strong>
                        <div class="relation-summary-values">
                            ${loading
                                ? '<span class="muted">Chargement...</span>'
                                : (items.length
                                    ? items.map((item) => noCodeRelationSummaryChipMarkup(item)).join("")
                                    : '<span class="muted">Aucun objet lie.</span>')}
                        </div>
                    </div>
                    <span class="relation-summary-action">${escapeHtml(actionLabel)}</span>
                </summary>
                <div class="relation-editor-panel">
                    ${buildNoCodeRecordDirectRelationControl(context, editor, relation)}
                </div>
            </details>
        `;
    }).join("");
    const indirectRows = mergeNoCodeReadonlyRelationSummarySections(editor?.indirectRelationSections)
        .map((section) => buildNoCodeReadonlyRelationSummaryCard(section))
        .join("");
    return `
        <div class="relation-summary-list">
            ${editableRows}
            ${indirectRows}
        </div>
    `;
}

function buildNoCodeRecordRelationExperienceMarkup(context, editor) {
    if (editor?.mode !== "edit") {
        const currentServiceCode = String(context?.service?.code || "").trim().toLowerCase();
        const requiredRelations = noCodeRecordEditableRelationsForContext(context)
            .filter((relation) => (
                String(relation?.source_service_code || "").trim().toLowerCase() === currentServiceCode
                && Boolean(relation?.required)
            ));
        return `
            <section class="modal-section no-code-record-direct-relations">
                <h3>Relations</h3>
                ${requiredRelations.length
                    ? `<p class="muted">Les relations ci-dessous sont obligatoires pour creer cette fiche.</p>${requiredRelations.map((relation) => buildNoCodeRecordDirectRelationControl(context, editor, relation)).join("")}`
                    : '<p class="muted">Les relations complementaires pourront etre ajoutees apres la creation.</p>'}
            </section>
        `;
    }
    const assignment = editor?.recordAssignment;
    const assignmentRelationIds = new Set([
        String(assignment?.definition?.id || "").trim(),
        String(assignment?.ownerRelationId || "").trim(),
    ].filter(Boolean));
    const relations = noCodeRecordEditableRelationsForContext(context)
        .filter((relation) => !assignmentRelationIds.has(String(relation?.id || "").trim()));
    const hasIndirectRelations = Array.isArray(editor?.indirectRelationSections) && editor.indirectRelationSections.length > 0;
    if (!relations.length && !hasIndirectRelations) {
        return "";
    }
    const summaryMarkup = buildNoCodeRecordRelationsSummaryMarkup(context, editor, relations);
    return `
        <section class="modal-section no-code-record-direct-relations">
            <h3>Relations</h3>
            ${summaryMarkup}
        </section>
    `;
}

function buildNoCodeRelationLinkPickerMarkup(context) {
    const candidates = noCodeRelationCandidateRows(context);
    const canAddMore = noCodeRelationAllowsMultipleLinkedFromCurrent(
        { service: context?.currentService },
        context?.relation,
    ) || !Array.isArray(context?.links) || context.links.length <= 0;
    const optionsMarkup = candidates.map((row) => {
        const rowId = String(row?.id || row?.record_id || "").trim();
        const label = noCodeRecordPrimaryLabel(context?.linkedService || null, row) || rowId;
        return `<option value="${escapeHtml(rowId)}">${escapeHtml(label)}</option>`;
    }).join("");
    const disabled = !canAddMore || !candidates.length;
    const helper = !canAddMore
        ? "Cette relation accepte deja une fiche liee depuis cette fiche."
        : (!candidates.length ? "Aucune fiche disponible a ajouter." : "");
    return `
        <section class="modal-section">
            <div class="inventory-row-actions no-code-relation-link-picker">
                <label class="field inline-field">
                    <span>Ajouter une fiche liee</span>
                    <select id="service-relation-link-candidate" ${disabled ? "disabled" : ""}>
                        <option value="">Choisir une fiche</option>
                        ${optionsMarkup}
                    </select>
                </label>
                ${createActionButtonMarkup({
                    preset: "add",
                    action: "service:relation-link:add",
                    label: "Ajouter le lien",
                    disabled,
                })}
            </div>
            ${helper ? `<p class="muted">${escapeHtml(helper)}</p>` : ""}
            <p id="service-relation-links-feedback" class="muted inventory-feedback"></p>
        </section>
    `;
}

function buildNoCodeRelationLinksModalMarkup(context) {
    const currentRecord = context?.record || {};
    const linkedService = context?.linkedService || {};
    const relationLabel = noCodeRelationLabelForContext({ service: context?.currentService }, context?.relation);
    const currentLabel = noCodeRecordPrimaryLabel(context?.currentService || null, currentRecord) || String(currentRecord?.id || "");
    return `
        <div class="modal-stack">
            <p class="muted">
                ${escapeHtml(relationLabel)} pour ${escapeHtml(currentLabel || "la fiche selectionnee")}
            </p>
            ${buildNoCodeRelationLinkPickerMarkup(context)}
            ${buildTreeSectionMarkup({
                title: linkedService.label || linkedService.code || "Fiches liees",
                searchId: "service-relation-links-search",
                searchLabel: "Recherche",
                searchPlaceholder: "Filtrer les fiches liees",
                searchValue: String(context?.searchQuery || ""),
                headId: "service-relation-links-head",
                bodyId: "service-relation-links-body",
                tableClassName: "device-table inventory-table",
            })}
        </div>
    `;
}

function renderNoCodeRelationLinksModal() {
    const context = state.noCodeRelationLinksContext;
    if (!context) {
        return;
    }
    const tree = ensureNoCodeRelationLinksTreeView(context);
    if (tree) {
        tree.render();
    }
}

function refreshOpenNoCodeRecordEditorMarkup() {
    const form = document.getElementById("modal-service-record-form");
    const directoryForm = document.getElementById("modal-directory-record-form");
    if (directoryForm instanceof HTMLFormElement && state.directoryRecordEditor) {
        const parent = directoryForm.parentElement;
        if (parent instanceof HTMLElement) {
            parent.innerHTML = buildDirectoryRecordEditorMarkup();
        }
        return;
    }
    if (!(form instanceof HTMLFormElement) || !state.noCodeRecordEditor) {
        return;
    }
    const parent = form.parentElement;
    if (parent instanceof HTMLElement) {
        parent.innerHTML = buildNoCodeRecordEditorMarkup();
    }
}

async function loadNoCodeRecordRelationExperience() {
    const context = state.noCodeServiceRecordContext;
    const editor = state.noCodeRecordEditor;
    if (!context?.service || !editor) {
        return;
    }
    const currentServiceCode = String(context.service.code || "").trim().toLowerCase();
    const isCreate = editor.mode !== "edit" || !editor.recordId;
    const relations = noCodeRecordEditableRelationsForContext(context)
        .filter((relation) => !isCreate || (
            String(relation?.source_service_code || "").trim().toLowerCase() === currentServiceCode
            && Boolean(relation?.required)
        ));
    editor.relationStates = editor.relationStates && typeof editor.relationStates === "object" ? editor.relationStates : {};
    relations.forEach((relation) => {
        editor.relationStates[String(relation.id || "")] = {
            ...(editor.relationStates[String(relation.id || "")] || {}),
            loading: true,
        };
    });
    refreshOpenNoCodeRecordEditorMarkup();
    const relationEntries = await Promise.all(relations.map(async (relation) => {
        const relationId = Number(relation.id || 0);
        if (isCreate) {
            const linkedServiceCode = noCodeRelationLinkedServiceCodeForContext(context, relation);
            const candidatePage = await fetchNoCodeServiceRecordsPage(linkedServiceCode, {
                search: "",
                activeOnly: true,
                limit: 500,
                offset: 0,
                sort: "label",
                direction: "asc",
            }).catch(() => ({ items: [] }));
            return [String(relationId), {
                loading: false,
                links: [],
                candidates: Array.isArray(candidatePage?.items) ? candidatePage.items : [],
                candidatesLoaded: true,
                candidatesLoading: false,
            }];
        }
        const links = await fetchNoCodeServiceRecordRelationLinks(
            String(context.service.code || ""),
            String(editor.recordId || ""),
            relationId,
        );
        return [String(relationId), {
            loading: false,
            links,
            candidates: [],
            candidatesLoaded: false,
            candidatesLoading: false,
        }];
    }));
    editor.relationStates = Object.fromEntries(relationEntries);
    editor.indirectRelationSections = isCreate ? [] : await buildNoCodeRecordIndirectRelationSections(context, editor);
    editor.recordAssignment = isCreate ? null : await buildRecordAssignment(context, editor);
    refreshOpenNoCodeRecordEditorMarkup();
}

async function loadNoCodeRecordRelationCandidates(relationId) {
    const context = state.noCodeServiceRecordContext;
    const editor = state.noCodeRecordEditor;
    const normalizedRelationId = String(relationId || "").trim();
    if (!context?.service || !editor || !normalizedRelationId) {
        return;
    }
    const relation = noCodeRecordEditableRelationsForContext(context)
        .find((row) => String(row?.id || "") === normalizedRelationId);
    if (!relation) {
        return;
    }
    const existingState = noCodeRecordRelationState(editor, normalizedRelationId);
    if (existingState.candidatesLoaded || existingState.candidatesLoading) {
        return;
    }
    editor.relationStates = editor.relationStates && typeof editor.relationStates === "object" ? editor.relationStates : {};
    editor.relationStates[normalizedRelationId] = {
        ...existingState,
        candidatesLoading: true,
    };
    refreshOpenNoCodeRecordEditorMarkup();
    const linkedServiceCode = noCodeRelationLinkedServiceCodeForContext(context, relation);
    try {
        const candidatePage = await fetchNoCodeServiceRecordsPage(linkedServiceCode, {
            search: "",
            activeOnly: true,
            limit: 500,
            offset: 0,
            sort: "label",
            direction: "asc",
        }).catch(() => ({ items: [] }));
        const candidates = Array.isArray(candidatePage?.items) ? candidatePage.items : [];
        const constrained = relation?.filter_candidates_by_shared_relation
            ? await filterRelationCandidatesBySharedLinks(context, editor, relation, candidates)
            : { rows: candidates, message: "" };
        editor.relationStates[normalizedRelationId] = {
            ...noCodeRecordRelationState(editor, normalizedRelationId),
            candidates: constrained.rows,
            candidateConstraintMessage: constrained.message,
            candidatesLoaded: true,
            candidatesLoading: false,
        };
    } catch (error) {
        editor.relationStates[normalizedRelationId] = {
            ...noCodeRecordRelationState(editor, normalizedRelationId),
            candidates: [],
            candidatesLoaded: true,
            candidatesLoading: false,
            candidatesError: normalizeErrorMessage(error.message),
        };
    }
    refreshOpenNoCodeRecordEditorMarkup();
}

async function filterRelationCandidatesBySharedLinks(context, editor, relation, candidates) {
    const rows = Array.isArray(candidates) ? candidates : [];
    const currentServiceCode = String(context?.service?.code || "").trim().toLowerCase();
    const candidateServiceCode = noCodeRelationLinkedServiceCodeForContext(context, relation);
    if (!currentServiceCode || !candidateServiceCode || !rows.length) {
        return { rows, message: "" };
    }
    const anchorIdsByService = new Map();
    noCodeRecordEditableRelationsForContext(context).forEach((currentRelation) => {
        if (Number(currentRelation?.id || 0) === Number(relation?.id || 0)) {
            return;
        }
        const serviceCode = noCodeRelationLinkedServiceCodeForContext(context, currentRelation);
        const linkedIds = new Set(
            (noCodeRecordRelationState(editor, currentRelation.id)?.links || [])
                .map((link) => String(link?.linked_record?.id || "").trim())
                .filter(Boolean),
        );
        if (serviceCode && linkedIds.size) {
            anchorIdsByService.set(serviceCode, linkedIds);
        }
    });
    const candidateRelations = await fetchNoCodeServiceRelations(candidateServiceCode).catch(() => []);
    const sharedRelations = candidateRelations
        .filter((candidateRelation) => Boolean(candidateRelation?.is_active !== false && Number(candidateRelation?.id || 0) > 0))
        .map((candidateRelation) => ({
            relation: candidateRelation,
            pivotServiceCode: noCodeRelationLinkedServiceCodeForContext(
                { service: { code: candidateServiceCode } },
                candidateRelation,
            ),
        }))
        .filter(({ pivotServiceCode }) => pivotServiceCode && pivotServiceCode !== currentServiceCode && anchorIdsByService.has(pivotServiceCode));
    if (!sharedRelations.length) {
        return { rows, message: "" };
    }
    const candidateIds = rows.map((row) => String(row?.id || row?.record_id || "").trim()).filter(Boolean);
    const allowedIds = new Set();
    for (const { relation: candidateRelation, pivotServiceCode } of sharedRelations) {
        const linksByCandidate = await fetchNoCodeServiceRecordRelationLinksBatch(
            candidateServiceCode,
            candidateIds,
            Number(candidateRelation.id || 0),
        );
        const allowedPivotIds = anchorIdsByService.get(pivotServiceCode) || new Set();
        candidateIds.forEach((candidateId) => {
            const matches = Array.isArray(linksByCandidate?.[candidateId]) ? linksByCandidate[candidateId] : [];
            if (matches.some((link) => allowedPivotIds.has(String(link?.linked_record?.id || "").trim()))) {
                allowedIds.add(candidateId);
            }
        });
    }
    const pivotLabels = Array.from(new Set(sharedRelations.map(({ pivotServiceCode }) => {
        const service = findNoCodeRelationEntity(pivotServiceCode);
        return String(service?.label || pivotServiceCode).trim();
    }).filter(Boolean)));
    const pivotLabel = pivotLabels.join(", ");
    return {
        rows: rows.filter((row) => allowedIds.has(String(row?.id || row?.record_id || "").trim())),
        message: pivotLabel
            ? `Liste filtrée selon le ou les ${pivotLabel.toLowerCase()} liés à cette fiche.`
            : "Liste filtrée selon les objets liés à cette fiche.",
    };
}

async function buildNoCodeRecordIndirectRelationSections(context, editor) {
    const directRelations = noCodeRecordEditableRelationsForContext(context)
        .filter((relation) => Boolean(relation?.show_indirect_relations));
    const sections = [];
    for (const directRelation of directRelations) {
        const relationId = String(directRelation.id || "");
        const directState = noCodeRecordRelationState(editor, relationId);
        const intermediateLinks = Array.isArray(directState.links) ? directState.links : [];
        const intermediateServiceCode = noCodeRelationLinkedServiceCodeForContext(context, directRelation);
        if (!intermediateLinks.length || !intermediateServiceCode) {
            continue;
        }
        const intermediateService = findNoCodeRelationEntity(intermediateServiceCode) || { code: intermediateServiceCode, label: intermediateServiceCode };
        const intermediateRelations = await fetchNoCodeServiceRelations(intermediateServiceCode).catch(() => []);
        const usefulRelations = intermediateRelations.filter((relation) => {
            const linkedCode = noCodeRelationLinkedServiceCodeForContext({ service: intermediateService }, relation);
            return linkedCode && linkedCode !== String(context.service.code || "").trim().toLowerCase();
        });
        for (const intermediateLink of intermediateLinks) {
            const intermediateRecord = intermediateLink?.linked_record || {};
            const intermediateRecordId = String(intermediateRecord?.id || "").trim();
            if (!intermediateRecordId) {
                continue;
            }
            for (const relation of usefulRelations) {
                const linkedCode = noCodeRelationLinkedServiceCodeForContext({ service: intermediateService }, relation);
                const linkedService = findNoCodeRelationEntity(linkedCode) || { code: linkedCode, label: linkedCode };
                const links = await fetchNoCodeServiceRecordRelationLinks(
                    intermediateServiceCode,
                    intermediateRecordId,
                    Number(relation.id || 0),
                ).catch(() => []);
                const rows = links.map((link) => {
                    const record = link?.linked_record || {};
                    const recordId = String(record.id || record.record_id || "").trim();
                    rememberLinkedRecordViewCache(linkedCode, record);
                    return {
                        id: recordId,
                        label: noCodeRecordPrimaryLabel(linkedService, record) || recordId,
                        linkedServiceCode: linkedCode,
                        recordId,
                        record,
                    };
                }).filter((row) => row.id);
                if (rows.length) {
                    sections.push({
                        label: `${linkedService.label || linkedCode}`,
                        via: `via ${intermediateService.label || intermediateServiceCode}: ${noCodeRecordPrimaryLabel(intermediateService, intermediateRecord) || intermediateRecordId}`,
                        rows,
                    });
                }
            }
        }
    }
    return sections;
}

async function openNoCodeRecordRelationLinksModal({ serviceCode, recordId, relationId } = {}) {
    const currentContext = state.noCodeServiceRecordContext;
    const normalizedServiceCode = String(serviceCode || currentContext?.service?.code || "").trim().toLowerCase();
    const normalizedRecordId = String(recordId || "").trim();
    const normalizedRelationId = Number(relationId || 0);
    if (!currentContext?.service || !normalizedServiceCode || !normalizedRecordId || normalizedRelationId <= 0) {
        throw new Error("Relation introuvable.");
    }
    const relation = noCodeRecordRelationsForContext(currentContext)
        .find((row) => Number(row?.id || 0) === normalizedRelationId);
    if (!relation) {
        throw new Error("Relation introuvable.");
    }
    const linkedServiceCode = noCodeRelationLinkedServiceCodeForContext(currentContext, relation);
    let linkedService = findNoCodeService(linkedServiceCode);
    if (!linkedService) {
        await loadAdministrationData({
            includeModules: false,
            includeRoles: false,
            includeUsers: false,
            includeServices: true,
            includeSharedLists: false,
        });
        linkedService = findNoCodeService(linkedServiceCode);
    }
    const record = findNoCodeServiceRecordInContext(currentContext, normalizedRecordId) || { id: normalizedRecordId };
    const [links, candidatePage] = await Promise.all([
        fetchNoCodeServiceRecordRelationLinks(
            normalizedServiceCode,
            normalizedRecordId,
            normalizedRelationId,
        ),
        fetchNoCodeServiceRecordsPage(linkedServiceCode, {
            search: "",
            activeOnly: true,
            limit: 500,
            offset: 0,
            sort: "label",
            direction: "asc",
        }).catch(() => ({ items: [] })),
    ]);
    state.noCodeRelationLinksContext = {
        serviceCode: normalizedServiceCode,
        recordId: normalizedRecordId,
        relationId: normalizedRelationId,
        currentService: currentContext.service,
        linkedService: linkedService || { code: linkedServiceCode, label: linkedServiceCode },
        relation,
        record,
        links,
        candidates: Array.isArray(candidatePage?.items) ? candidatePage.items : [],
        searchQuery: "",
        sort: { column: "", direction: "asc" },
        _treeView: null,
    };
    openModal(
        "Fiches liees",
        buildNoCodeRelationLinksModalMarkup(state.noCodeRelationLinksContext),
        { width: "min(1180px, calc(100vw - 32px))" },
    );
    renderNoCodeRelationLinksModal();
}

async function refreshNoCodeRelationLinksModal() {
    const context = state.noCodeRelationLinksContext;
    if (!context) {
        return;
    }
    const [links, candidatePage] = await Promise.all([
        fetchNoCodeServiceRecordRelationLinks(context.serviceCode, context.recordId, context.relationId),
        fetchNoCodeServiceRecordsPage(context.linkedService?.code || "", {
            search: "",
            activeOnly: true,
            limit: 500,
            offset: 0,
            sort: "label",
            direction: "asc",
        }).catch(() => ({ items: [] })),
    ]);
    context.links = links;
    context.candidates = Array.isArray(candidatePage?.items) ? candidatePage.items : [];
    context._treeView = null;
    openModal(
        "Fiches liees",
        buildNoCodeRelationLinksModalMarkup(context),
        { width: "min(1180px, calc(100vw - 32px))" },
    );
    renderNoCodeRelationLinksModal();
}

function buildNoCodeInlineRecordControl(row, column, value) {
    const fieldKey = String(column?.field_key || "").trim();
    if (!fieldKey) {
        return escapeHtml(String(value || ""));
    }
    const commonAttrs = [
        `data-no-code-inline-field="${escapeHtml(fieldKey)}"`,
        `data-original-value="${escapeHtml(String(value || ""))}"`,
        `aria-label="${escapeHtml(`Modifier ${String(column?.label || fieldKey)}`)}"`,
    ].join(" ");
    const kind = normalizeNoCodeKind(column?.kind || "text");
    if (kind === "list") {
        const currentValue = String(value || "").trim();
        const options = parseNoCodeOptions(column?.options || "");
        if (currentValue && !options.some((option) => option.toLowerCase() === currentValue.toLowerCase())) {
            options.unshift(currentValue);
        }
        const optionsMarkup = options.map((option) => {
            const selected = currentValue.toLowerCase() === option.toLowerCase();
            return `<option value="${escapeHtml(option)}" ${selected ? "selected" : ""}>${escapeHtml(option)}</option>`;
        }).join("");
        return `
            <select class="no-code-inline-edit-control" ${commonAttrs}>
                <option value="" ${currentValue ? "" : "selected"}></option>
                ${optionsMarkup}
            </select>
        `;
    }
    return `<input class="no-code-inline-edit-control" ${commonAttrs} type="${escapeHtml(noCodeRecordInputType(kind))}" value="${escapeHtml(String(value || ""))}">`;
}

function buildNoCodeRecordsQuickFiltersMarkup(context) {
    const columns = noCodeRecordQuickFilterColumns(context?.service || null);
    if (!columns.length) {
        return "";
    }
    const filters = noCodeRecordQuickFilterValueMap(context);
    const fieldsMarkup = columns.map((column) => {
        const fieldKey = String(column?.field_key || "").trim();
        const label = String(column?.label || fieldKey).trim() || fieldKey;
        const currentValue = String(filters[fieldKey] || "");
        if (String(column.kind || "text") === "list") {
            const optionsMarkup = parseNoCodeOptions(column?.options || "").map((option) => {
                const selected = currentValue.toLowerCase() === option.toLowerCase();
                return `<option value="${escapeHtml(option)}" ${selected ? "selected" : ""}>${escapeHtml(option)}</option>`;
            }).join("");
            return `
                <label class="field no-code-quick-filter-field">
                    <span>${escapeHtml(label)}</span>
                    <select data-no-code-quick-filter="${escapeHtml(fieldKey)}">
                        <option value="">Tous</option>
                        ${optionsMarkup}
                    </select>
                </label>
            `;
        }
        return `
            <label class="field no-code-quick-filter-field">
                <span>${escapeHtml(label)}</span>
                <input data-no-code-quick-filter="${escapeHtml(fieldKey)}" type="${escapeHtml(noCodeRecordInputType(column.kind))}" value="${escapeHtml(currentValue)}" placeholder="Tous">
            </label>
        `;
    }).join("");
    const hasActiveFilter = Object.keys(filters).length > 0;
    return `
        <section class="shared-treeview-filter-section no-code-quick-filters">
            <div class="type-schema-fields-head">
                <h3>Filtres rapides</h3>
                ${createActionButtonMarkup({
                    className: "toolbar-btn",
                    type: "button",
                    action: "service:records:filters:clear",
                    label: "Reinitialiser",
                    disabled: !hasActiveFilter,
                })}
            </div>
            <div class="no-code-quick-filter-line">
                <div class="content-filter-grid no-code-quick-filter-grid">
                    ${fieldsMarkup}
                </div>
                <div class="shared-treeview-control-right no-code-quick-filter-pagination">
                    <div id="service-records-page-size-top" data-tree-page-size-control></div>
                    <div id="service-records-pagination-top">${buildNoCodeRecordsPaginationMarkup(context)}</div>
                </div>
            </div>
        </section>
    `;
}

function buildNoCodeRecordsBatchToolbarMarkup(context) {
    const selectedCount = noCodeSelectedRecordRows(context).length;
    const hasEditableRelations = noCodeRecordEditableRelationsForContext(context).length > 0;
    const batchEditableFields = noCodeRecordColumns(context?.service || null)
        .filter((column) => String(column?.kind || "") === "list" && Boolean(column?.batch_editable));
    return `
        <section id="service-records-batch-toolbar" class="modal-section no-code-record-batch-toolbar" ${selectedCount <= 0 ? "hidden" : ""}>
            <div class="inventory-row-actions no-code-record-batch-actions">
                <span id="service-records-batch-count" class="muted">
                    ${selectedCount > 0
                        ? `${selectedCount} fiche${selectedCount > 1 ? "s" : ""} selectionnee${selectedCount > 1 ? "s" : ""}`
                        : "Aucune fiche selectionnee"}
                </span>
                <label class="field no-code-record-batch-field">
                    <span>Actions sur la selection</span>
                    <select id="service-records-batch-action" ${selectedCount <= 0 ? "disabled" : ""}>
                        <option value="">Choisir une action</option>
                        ${batchEditableFields.map((column) => `<option value="field:${escapeHtml(String(column.field_key || ""))}">Modifier ${escapeHtml(String(column.label || column.field_key || ""))}</option>`).join("")}
                        ${hasEditableRelations ? '<option value="relation">Assigner un element lie</option>' : ""}
                        <option value="delete">Supprimer les fiches selectionnees</option>
                    </select>
                </label>
            </div>
        </section>
    `;
}

function noCodeRecordCompareByColumn(columnsByKey, column, direction, left, right) {
    const dir = direction === "desc" ? -1 : 1;
    const col = columnsByKey.get(String(column || "")) || Array.from(columnsByKey.values())[0] || { kind: "text", key: "" };
    if (!String(col?.key || "").trim()) {
        return 0;
    }
    const kind = String(col.kind || "text");
    const leftValue = noCodeRecordColumnValue(left, col);
    const rightValue = noCodeRecordColumnValue(right, col);
    if (kind === "number") {
        const lv = Number(leftValue || 0);
        const rv = Number(rightValue || 0);
        if (lv === rv) {
            return 0;
        }
        return (lv - rv) * dir;
    }
    if (kind === "date") {
        const lv = Date.parse(String(leftValue || ""));
        const rv = Date.parse(String(rightValue || ""));
        if (Number.isFinite(lv) && Number.isFinite(rv)) {
            if (lv === rv) {
                return 0;
            }
            return (lv - rv) * dir;
        }
    }
    if (kind === "ip") {
        const parseIp = (value) => String(value || "").split(".").map((chunk) => Number.parseInt(chunk, 10));
        const leftIp = parseIp(leftValue);
        const rightIp = parseIp(rightValue);
        const size = Math.max(leftIp.length, rightIp.length);
        for (let index = 0; index < size; index += 1) {
            const li = Number.isFinite(leftIp[index]) ? leftIp[index] : -1;
            const ri = Number.isFinite(rightIp[index]) ? rightIp[index] : -1;
            if (li !== ri) {
                return (li - ri) * dir;
            }
        }
        return 0;
    }
    return String(leftValue || "").localeCompare(String(rightValue || ""), undefined, { sensitivity: "base" }) * dir;
}

function noCodeVisibleRecordRows(context) {
    const tree = ensureServiceRecordsTreeView(context);
    if (tree) {
        return tree.getVisibleRows();
    }
    return tableFilterAndSortRows(Array.isArray(context?.records) ? context.records : [], {});
}

function noCodeSelectedRecordRows(context) {
    const tree = context?._recordsTreeView || null;
    if (tree && typeof tree.getSelectedRows === "function") {
        return tree.getSelectedRows();
    }
    const selected = new Set(
        Array.isArray(context?.selectedRecordKeys)
            ? context.selectedRecordKeys.map((key) => String(key || "").trim()).filter(Boolean)
            : [],
    );
    if (!selected.size) {
        return [];
    }
    return (Array.isArray(context?.records) ? context.records : []).filter((row) => (
        selected.has(String(row?.id || row?.record_id || "").trim())
    ));
}

function updateNoCodeServiceRecordsBatchActions(context) {
    const toolbar = document.getElementById("service-records-batch-toolbar");
    const button = document.getElementById("service-records-batch-delete");
    const select = document.getElementById("service-records-batch-action");
    const countLabel = document.getElementById("service-records-batch-count");
    if (!(button instanceof HTMLButtonElement)) {
        // The compact toolbar may be present even when the title button is not rendered.
    }
    const count = noCodeSelectedRecordRows(context).length;
    if (toolbar instanceof HTMLElement) {
        toolbar.hidden = count <= 0;
    }
    if (button instanceof HTMLButtonElement) {
        button.disabled = count <= 0;
        const label = button.querySelector(".ui-action-btn-label") || button;
        label.textContent = count > 0 ? `Supprimer selection (${count})` : "Supprimer selection";
    }
    if (select instanceof HTMLSelectElement) {
        select.disabled = count <= 0;
        if (count <= 0 || ["delete", "relation"].includes(select.value) || String(select.value || "").startsWith("field:")) {
            select.value = "";
        }
    }
    if (countLabel instanceof HTMLElement) {
        countLabel.textContent = count > 0
            ? `${count} fiche${count > 1 ? "s" : ""} selectionnee${count > 1 ? "s" : ""}`
            : "Aucune fiche selectionnee";
    }
}

function updateNoCodeServiceRecordsFilterActions(context) {
    Array.from(document.querySelectorAll('[data-action="service:records:filters:clear"]')).forEach((button) => {
        if (button instanceof HTMLButtonElement) {
            button.disabled = !noCodeServiceRecordsHasActiveFilters(context);
        }
    });
}

function reconcileNoCodeSelectedRecordKeys(context) {
    if (!context) {
        return;
    }
    const existing = new Set(
        (Array.isArray(context.records) ? context.records : [])
            .map((row) => String(row?.id || row?.record_id || "").trim())
            .filter(Boolean),
    );
    context.selectedRecordKeys = (
        Array.isArray(context.selectedRecordKeys) ? context.selectedRecordKeys : []
    ).map((key) => String(key || "").trim()).filter((key) => key && existing.has(key));
}

let noCodeServiceRecordsReloadTimer = 0;

function buildNoCodeRecordsPaginationMarkup(context) {
    const page = context?.recordsPage && typeof context.recordsPage === "object" ? context.recordsPage : {};
    const total = Math.max(0, Number(page.total || 0));
    const limit = Math.max(1, Number(page.limit || 50));
    const offset = Math.max(0, Number(page.offset || 0));
    const count = Array.isArray(context?.records) ? context.records.length : 0;
    const start = total && count ? offset + 1 : 0;
    const end = total && count ? Math.min(offset + count, total) : 0;
    const previousOffset = Math.max(0, offset - limit);
    const nextOffset = offset + limit;
    return `
        <div class="inventory-row-actions no-code-records-pagination">
            <span class="muted">${escapeHtml(String(start))}-${escapeHtml(String(end))} / ${escapeHtml(String(total))}</span>
            ${createActionButtonMarkup({
                className: "toolbar-btn",
                action: "service:records:page",
                label: "Precedent",
                disabled: offset <= 0,
                data: { offset: previousOffset },
            })}
            ${createActionButtonMarkup({
                className: "toolbar-btn",
                action: "service:records:page",
                label: "Suivant",
                disabled: nextOffset >= total,
                data: { offset: nextOffset },
            })}
        </div>
    `;
}

function buildNoCodeRecordsTopControlsMarkup(context, searchMarkup = "") {
    return `
        <div class="no-code-records-toolbar-top shared-treeview-control-bar">
            <div class="shared-treeview-control-left">
                ${searchMarkup}
            </div>
        </div>
    `;
}

function buildNoCodeRecordsBottomControlsMarkup(context) {
    return `
        <div class="no-code-records-toolbar-bottom shared-treeview-control-bar">
            <div class="shared-treeview-control-left"></div>
            <div class="shared-treeview-control-right">
                <div id="service-records-page-size-bottom" data-tree-page-size-control></div>
                <div id="service-records-pagination-bottom">${buildNoCodeRecordsPaginationMarkup(context)}</div>
            </div>
        </div>
    `;
}

function normalizeServiceRecordImportMappings(mappings) {
    return (Array.isArray(mappings) ? mappings : [])
        .map((row) => ({
            source_column: String(row?.source_column || "").trim(),
            target_field: String(row?.target_field || "").trim(),
            custom_key: String(row?.custom_key || "").trim(),
        }))
        .filter((row) => row.source_column && row.target_field);
}

function summarizeImportIssues(issues, limit = 5) {
    const rows = (Array.isArray(issues) ? issues : [])
        .map((item) => String(item || "").trim())
        .filter(Boolean);
    if (!rows.length) {
        return "";
    }
    const shown = rows.slice(0, Math.max(1, Number(limit || 5)));
    const suffix = rows.length > shown.length ? ` | +${rows.length - shown.length} autre(s)` : "";
    return ` Alertes: ${shown.join(" | ")}${suffix}`;
}

function formatServiceRecordsImportResult(applied, { relaxed = false } = {}) {
    const issueCount = Array.isArray(applied?.issues) ? applied.issues.length : 0;
    const prefix = relaxed ? "Import force termine" : "Import termine";
    return `${prefix}: ${Number(applied?.created || 0)} creee(s), ${Number(applied?.updated || 0)} mise(s) a jour, ${Number(applied?.skipped || 0)} ignoree(s).${issueCount ? ` (${issueCount} alerte(s)).` : ""}${summarizeImportIssues(applied?.issues)}`;
}

async function applyServiceRecordsImportWithRelaxedFallback({
    file,
    serviceCode,
    credentialMode = "preserve_on_blank",
    sheetName = "",
    headerMode = "auto",
    headerRowNumber = 1,
    columnMappings = [],
    importUntilRowNumber = 0,
    duplicatePolicy = "skip",
    duplicateFieldKey = "",
    feedback = null,
    setProgress = null,
} = {}) {
    const progress = typeof setProgress === "function" ? setProgress : () => {};
    progress(65, "Import en cours...", true);
    if (feedback instanceof HTMLElement) {
        feedback.textContent = "Import en cours...";
    }
    let applied = await applyServiceRecordsImportFromFile(
        file,
        serviceCode,
        credentialMode,
        sheetName,
        headerMode,
        headerRowNumber,
        columnMappings,
        importUntilRowNumber,
        duplicatePolicy === "skip",
        duplicatePolicy,
        duplicateFieldKey,
    );
    let relaxed = false;
    if (duplicatePolicy !== "skip" && applied.skipped > 0 && Array.isArray(applied.issues) && applied.issues.length) {
        const decision = await showItopsChoice({
            title: "Importer avec alertes",
            message: `${applied.skipped} ligne(s) n'ont pas ete importee(s). Voulez-vous importer quand meme les valeurs non conformes ?`,
            details: applied.issues.slice(0, 8),
            choices: [
                { value: "cancel", label: "Ne pas importer", className: "toolbar-btn" },
                { value: "force", label: "Importer quand meme", className: "primary-btn" },
            ],
        });
        if (decision !== "force") {
            progress(0, "", false);
            if (feedback instanceof HTMLElement) {
                feedback.textContent = formatServiceRecordsImportResult(applied);
            }
            return { applied, relaxed, cancelled: true };
        }
        progress(72, "Import force en cours...", true);
        if (feedback instanceof HTMLElement) {
            feedback.textContent = "Import force en cours...";
        }
        applied = await applyServiceRecordsImportFromFile(
            file,
            serviceCode,
            credentialMode,
            sheetName,
            headerMode,
            headerRowNumber,
            columnMappings,
            importUntilRowNumber,
            true,
            duplicatePolicy,
            duplicateFieldKey,
        );
        relaxed = true;
    }
    return { applied, relaxed, cancelled: false };
}

function mergeServiceRecordImportMappings(baseMappings, changedMappings) {
    const merged = new Map();
    normalizeServiceRecordImportMappings(baseMappings).forEach((row) => {
        merged.set(row.source_column, row);
    });
    normalizeServiceRecordImportMappings(changedMappings).forEach((row) => {
        merged.set(row.source_column, row);
    });
    return Array.from(merged.values());
}

function buildDefaultServiceRecordImportMappings(service, sourceHeaders) {
    const fields = noCodeCustomServiceFields(service);
    const headers = (Array.isArray(sourceHeaders) ? sourceHeaders : [])
        .map((header) => String(header || "").trim())
        .filter(Boolean);
    const mappings = [];
    const usedHeaders = new Set();
    fields.forEach((field, index) => {
        const fieldKey = String(field?.field_key || "").trim();
        if (!fieldKey) {
            return;
        }
        const label = String(field?.label || fieldKey).trim();
        const normalizedAliases = new Set([
            slugifyNoCodeIdentifier(fieldKey, "field"),
            slugifyNoCodeIdentifier(label, "field"),
        ]);
        let source = headers.find((header) => !usedHeaders.has(header) && normalizedAliases.has(slugifyNoCodeIdentifier(header, "field"))) || "";
        if (!source) {
            source = headers.filter((header) => !["record_id", "id"].includes(slugifyNoCodeIdentifier(header, "field")))[index] || "";
        }
        if (source) {
            usedHeaders.add(source);
            mappings.push({ source_column: source, target_field: fieldKey });
        }
    });
    return mappings;
}

function buildServiceRecordImportMappingsFromEffectiveMapping(effectiveMapping) {
    return (Array.isArray(effectiveMapping) ? effectiveMapping : [])
        .map((row) => ({
            source_column: String(row?.source_column || "").trim(),
            target_field: String(row?.target_field || "").trim(),
        }))
        .filter((row) => row.source_column && row.target_field && !["__ignore__", "ignore", "none"].includes(row.target_field));
}

function readServiceRecordImportMappingsFromDom() {
    const sharedImport = window.NMPSharedImport;
    if (sharedImport && typeof sharedImport.collectColumnMappings === "function") {
        return sharedImport.collectColumnMappings(document, {
            rowSelector: "th[data-source-column]",
            targetName: "service_records_import_target",
        });
    }
    return Array.from(document.querySelectorAll('select[name="service_records_import_target"]'))
        .map((select) => ({
            source_column: String(select.closest("[data-source-column]")?.getAttribute("data-source-column") || "").trim(),
            target_field: String(select.value || "__ignore__").trim() || "__ignore__",
            custom_key: String(select.closest("[data-source-column]")?.querySelector?.('input[name="service_records_import_custom"]')?.value || "").trim(),
        }))
        .filter((row) => row.source_column);
}

function buildServiceRecordImportTargetOptions(service) {
    const fields = noCodeCustomServiceFields(service);
    const credentialTargets = service?.credentials_enabled ? [
        { value: "device_login", label: "Identifiant securise (technique)" },
        { value: "device_password", label: "Mot de passe securise (technique)" },
    ] : [];
    return [
        { value: "__create_field__", label: "Ajouter" },
        { value: "__ignore__", label: "Ignorer" },
        ...credentialTargets,
        ...fields.map((field) => ({
            value: String(field?.field_key || "").trim(),
            label: String(field?.label || field?.field_key || "").trim(),
            required: Boolean(field?.required),
        })).filter((option) => option.value),
    ];
}

function buildServiceRecordImportMappingMarkup(context, sourceHeaders, sourceRowsPreview) {
    const service = context?.service || null;
    const headers = (Array.isArray(sourceHeaders) ? sourceHeaders : [])
        .map((header) => String(header || "").trim())
        .filter(Boolean);
    if (!service || !headers.length) {
        return "";
    }
    const sharedImport = window.NMPSharedImport;
    const targetOptions = buildServiceRecordImportTargetOptions(service);
    const detectedHeaderRowNumber = Number(context?.importPreview?.detectedHeaderRowNumber || 1);
    const sampleRows = Array.isArray(sourceRowsPreview)
        ? sourceRowsPreview.slice(Math.max(0, detectedHeaderRowNumber - 1), Math.max(0, detectedHeaderRowNumber))
        : [];
    if (sharedImport && typeof sharedImport.buildIntegratedMappingPreviewTable === "function") {
        return sharedImport.buildIntegratedMappingPreviewTable({
            headers,
            rows: Array.isArray(sourceRowsPreview) ? sourceRowsPreview : [],
            sampleRows,
            targetOptions,
            effectiveMapping: context?.importPreview?.effectiveMapping || [],
            draftMapping: context?.importColumnMappings || [],
            selectName: "service_records_import_target",
            customName: "service_records_import_custom",
            showCustomKey: true,
            customTargetValue: "__create_field__",
            customTargetValues: ["__create_field__"],
            customPlaceholder: "Nom de la nouvelle colonne",
            tableClassName: "device-table import-mapping-table",
            wrapClassName: "table-wrap import-mapping-table-wrap",
            ignoreValue: "__ignore__",
            validateRequiredTargets: false,
            columnsPerPage: 6,
            columnPage: Number(context?.importColumnPage || 0),
        });
    }
    return buildTabularSourcePreviewTable(headers, sourceRowsPreview);
}

function renderNoCodeServiceRecordsPagination() {
    const markup = buildNoCodeRecordsPaginationMarkup(state.noCodeServiceRecordContext);
    ["service-records-pagination-top", "service-records-pagination-bottom"].forEach((id) => {
        const target = document.getElementById(id);
        if (target instanceof HTMLElement) {
            target.innerHTML = markup;
        }
    });
}

function renderNoCodeServiceRecordsTable() {
    const context = state.noCodeServiceRecordContext;
    if (!context?.service) {
        return;
    }
    const tree = ensureServiceRecordsTreeView(context);
    if (tree) {
        tree.render();
        updateNoCodeServiceRecordsBatchActions(context);
        return;
    }
    const body = document.getElementById("service-records-body");
    if (body instanceof HTMLElement) {
        body.innerHTML = `<tr><td>Aucune fiche</td></tr>`;
    }
    updateNoCodeServiceRecordsBatchActions(context);
}

function bindNoCodeServiceRecordsDoubleClick(context) {
    const body = document.getElementById("service-records-body");
    if (!(body instanceof HTMLElement) || body.dataset.recordDblclickBound === "1") {
        return;
    }
    body.dataset.recordDblclickBound = "1";
    body.addEventListener("dblclick", (event) => {
        const target = event.target;
        if (!(target instanceof Element)) {
            return;
        }
        if (target.closest("button, a, input, select, textarea")) {
            return;
        }
        const rowElement = target.closest("tr[data-tree-row-key]");
        if (!(rowElement instanceof HTMLElement)) {
            return;
        }
        const recordId = String(rowElement.dataset.treeRowKey || "").trim();
        if (!recordId) {
            return;
        }
        const activeContext = context || state.noCodeServiceRecordContext;
        const rows = Array.isArray(activeContext?.records) ? activeContext.records : [];
        const row = rows.find((item) => String(item?.id || item?.record_id || "").trim() === recordId) || null;
        if (row) {
            openNoCodeRecordEditor(row);
        }
    });
}

function bindNoCodeServiceRecordsQuickFilters(context) {
    const controls = Array.from(document.querySelectorAll("[data-no-code-quick-filter]"));
    if (!controls.length || !context) {
        return;
    }
    let filterTimer = 0;
    const applyFilters = (target) => {
        if (!(target instanceof HTMLInputElement) && !(target instanceof HTMLSelectElement)) {
            return;
        }
        const fieldKey = String(target.dataset.noCodeQuickFilter || "").trim();
        if (!fieldKey) {
            return;
        }
        const filters = noCodeRecordQuickFilterValueMap(context);
        const value = String(target.value || "").trim();
        if (value) {
            filters[fieldKey] = value;
        } else {
            delete filters[fieldKey];
        }
        context.quickFilters = filters;
        updateNoCodeServiceRecordsFilterActions(context);
        renderNoCodeServiceRecordsTable();
    };
    controls.forEach((control) => {
        if (!(control instanceof HTMLInputElement) && !(control instanceof HTMLSelectElement)) {
            return;
        }
        if (control.dataset.quickFilterBound === "1") {
            return;
        }
        control.dataset.quickFilterBound = "1";
        const eventName = control instanceof HTMLSelectElement ? "change" : "input";
        control.addEventListener(eventName, (event) => {
            const target = event.target;
            if (filterTimer) {
                window.clearTimeout(filterTimer);
            }
            filterTimer = window.setTimeout(() => {
                filterTimer = 0;
                applyFilters(target);
            }, control instanceof HTMLSelectElement ? 0 : 180);
        });
    });
}

function findNoCodeServiceRecordInContext(context, recordId) {
    const wanted = String(recordId || "").trim();
    if (!wanted) {
        return null;
    }
    const rows = Array.isArray(context?.records) ? context.records : [];
    return rows.find((item) => String(item?.id || item?.record_id || "").trim() === wanted) || null;
}

function replaceNoCodeServiceRecordInContext(context, record) {
    if (!context || !record) {
        return;
    }
    const recordId = String(record?.id || record?.record_id || "").trim();
    if (!recordId) {
        return;
    }
    context.records = (Array.isArray(context.records) ? context.records : []).map((row) => (
        String(row?.id || row?.record_id || "").trim() === recordId ? record : row
    ));
}

function mergeNoCodeInlineHistorySummary(updatedRecord, previousRecord, fieldKey, trackedChanges, historyDecision) {
    const merged = {
        ...(previousRecord?.history_summary && typeof previousRecord.history_summary === "object"
            ? previousRecord.history_summary
            : {}),
        ...(updatedRecord?.history_summary && typeof updatedRecord.history_summary === "object"
            ? updatedRecord.history_summary
            : {}),
    };
    const trackedChange = (Array.isArray(trackedChanges) ? trackedChanges : [])
        .find((row) => String(row?.key || "").trim() === String(fieldKey || "").trim());
    if (noCodeHistoryDecisionKind(historyDecision) === "history" && trackedChange) {
        merged[String(fieldKey || "").trim()] = {
            old_value: String(trackedChange.oldValue || ""),
            new_value: String(trackedChange.newValue || ""),
            changed_at: noCodeHistoryDecisionChangedAt(historyDecision) || String(updatedRecord?.updated_at || new Date().toISOString()),
            changed_by: "",
            change_source: "manual",
        };
    }
    return {
        ...updatedRecord,
        history_summary: merged,
    };
}

function isEmailDeleteReminderTrigger(service, fieldKey, value) {
    return String(service?.code || "").trim().toLowerCase() === "emails"
        && String(fieldKey || "").trim().toLowerCase() === "status"
        && String(value || "").trim().toLowerCase() === "a supprimer";
}

async function resolveEmailDeleteReminderDueDate(service, fieldKey, nextValue, previousValue = "") {
    if (!isEmailDeleteReminderTrigger(service, fieldKey, nextValue)) {
        return "";
    }
    if (String(previousValue || "").trim().toLowerCase() === "a supprimer") {
        return "";
    }
    return requestNotificationReminderDate({
        title: "Rappel de suppression Email",
        message: "Le statut A supprimer doit etre associe a une date de rappel.",
    });
}

async function applyNoCodeInlineRecordValue(control) {
    if (!(control instanceof HTMLInputElement) && !(control instanceof HTMLSelectElement)) {
        return;
    }
    const context = state.noCodeServiceRecordContext;
    const service = context?.service || null;
    const serviceCode = String(service?.code || "").trim();
    const fieldKey = String(control.dataset.noCodeInlineField || "").trim();
    const rowElement = control.closest("tr[data-tree-row-key]");
    const recordId = String(rowElement?.getAttribute("data-tree-row-key") || "").trim();
    const feedback = document.getElementById("modal-service-records-feedback");
    if (!context || !serviceCode || !fieldKey || !recordId) {
        return;
    }
    const record = findNoCodeServiceRecordInContext(context, recordId);
    if (!record) {
        return;
    }
    const originalValue = String(control.dataset.originalValue || "");
    const nextValue = String(control.value || "").trim();
    if (nextValue === originalValue) {
        return;
    }
    const reminderDueAt = await resolveEmailDeleteReminderDueDate(service, fieldKey, nextValue, originalValue);
    if (isEmailDeleteReminderTrigger(service, fieldKey, nextValue) && String(originalValue || "").trim().toLowerCase() !== "a supprimer" && !reminderDueAt) {
        control.value = originalValue;
        if (feedback) {
            feedback.textContent = "Date de rappel requise pour passer un Email a supprimer.";
        }
        return;
    }
    const values = {
        ...(record?.values && typeof record.values === "object" ? record.values : {}),
        [fieldKey]: nextValue,
    };
    const trackedChanges = noCodeTrackedRecordChanges(service, recordId, values)
        .filter((row) => String(row?.key || "").trim() === fieldKey);
    let historyDecision = { decision: "none", changedAt: "" };
    if (trackedChanges.length) {
        historyDecision = await confirmNoCodeTrackedRecordChanges(trackedChanges);
        if (noCodeHistoryDecisionKind(historyDecision) === "cancel") {
            control.value = originalValue;
            if (feedback) {
                feedback.textContent = "Modification annulee.";
            }
            return;
        }
    }
    const children = (Array.isArray(record?.children) ? record.children : []).map((row, index) => ({
        name: normalizeNoCodeText(row?.name),
        code: normalizeNoCodeText(row?.code),
        sort_order: Number(row?.sort_order || ((index + 1) * 10)),
    }));
    const buildPayloadForRecord = (sourceRecord) => ({
        values: {
            ...(sourceRecord?.values && typeof sourceRecord.values === "object" ? sourceRecord.values : {}),
            [fieldKey]: nextValue,
        },
        children: (Array.isArray(sourceRecord?.children) ? sourceRecord.children : []).map((row, index) => ({
            name: normalizeNoCodeText(row?.name),
            code: normalizeNoCodeText(row?.code),
            sort_order: Number(row?.sort_order || ((index + 1) * 10)),
        })),
        confirm_history_changes: trackedChanges.length > 0 && noCodeHistoryDecisionKind(historyDecision) === "history",
        skip_history_changes: trackedChanges.length > 0 && noCodeHistoryDecisionKind(historyDecision) === "skip",
        history_changed_at: noCodeHistoryDecisionChangedAt(historyDecision),
        reminder_due_at: reminderDueAt,
        version_token: String(sourceRecord?.version_token || ""),
    });
    const saveRecord = (sourceRecord) => requestJson(
        `/admin/custom-services/${encodeURIComponent(serviceCode)}/records/${encodeURIComponent(recordId)}`,
        {
            method: "PUT",
            body: JSON.stringify(buildPayloadForRecord(sourceRecord)),
        },
    );
    control.disabled = true;
    try {
        const updated = await saveRecord({ ...record, values, children });
        const hadActiveFilters = noCodeServiceRecordsHasActiveFilters(context);
        const enriched = mergeNoCodeInlineHistorySummary(updated, record, fieldKey, trackedChanges, historyDecision);
        replaceNoCodeServiceRecordInContext(context, enriched);
        if (hadActiveFilters) {
            clearNoCodeServiceRecordsFilters(context);
            await reloadNoCodeServiceRecordsPage(context, { offset: 0 });
        } else {
            renderNoCodeServiceRecordsTable();
        }
        if (feedback) {
            feedback.textContent = hadActiveFilters
                ? "Fiche mise a jour. Filtres reinitialises pour afficher toutes les fiches."
                : "Fiche mise a jour.";
        }
    } catch (error) {
        control.disabled = false;
        control.value = originalValue;
        if (feedback) {
            const message = normalizeErrorMessage(error.message);
            if (Number(error?.status || 0) === 409 && message.toLowerCase().includes("conflit de modification")) {
                await reloadNoCodeServiceRecordsPage(context);
                const freshRecord = findNoCodeServiceRecordInContext(context, recordId);
                const freshValue = String((freshRecord?.values || {})[fieldKey] || "").trim();
                if (freshRecord && freshValue === originalValue) {
                    const updated = await saveRecord(freshRecord);
                    replaceNoCodeServiceRecordInContext(context, mergeNoCodeInlineHistorySummary(updated, freshRecord, fieldKey, trackedChanges, historyDecision));
                    renderNoCodeServiceRecordsTable();
                    feedback.textContent = "Fiche mise a jour apres rechargement de la version serveur.";
                    return;
                }
                feedback.textContent = "La fiche a ete modifiee depuis le chargement de la liste. Vue rechargee: verifie la valeur puis recommence si necessaire.";
                return;
            }
            feedback.textContent = message;
        }
    }
}

async function deleteSelectedNoCodeServiceRecords() {
    const context = state.noCodeServiceRecordContext;
    const serviceCode = String(context?.service?.code || "").trim();
    const selectedRows = noCodeSelectedRecordRows(context);
    const feedback = document.getElementById("modal-service-records-feedback");
    if (!context || !serviceCode || !selectedRows.length) {
        if (feedback) {
            feedback.textContent = "Aucune fiche selectionnee.";
        }
        return;
    }
    const confirmed = await confirmBatchAction({
        title: "Supprimer la selection",
        count: selectedRows.length,
        itemLabel: "fiche",
        itemPluralLabel: "fiches",
        details: [
            "Cette action supprime uniquement les fiches selectionnees dans la vue actuelle.",
        ],
        danger: true,
    });
    if (!confirmed) {
        return;
    }
    let deleted = 0;
    const deletedIds = new Set();
    const errors = [];
    if (feedback) {
        feedback.textContent = "Suppression en cours...";
    }
    for (const row of selectedRows) {
        const recordId = String(row?.id || row?.record_id || "").trim();
        if (!recordId) {
            continue;
        }
        const versionToken = String(row?.version_token || "").trim();
        const path = versionToken
            ? `/admin/custom-services/${encodeURIComponent(serviceCode)}/records/${encodeURIComponent(recordId)}?version_token=${encodeURIComponent(versionToken)}`
            : `/admin/custom-services/${encodeURIComponent(serviceCode)}/records/${encodeURIComponent(recordId)}`;
        try {
            await requestJson(path, { method: "DELETE" });
            deleted += 1;
            deletedIds.add(recordId);
        } catch (error) {
            errors.push(`${recordId}: ${normalizeErrorMessage(error.message)}`);
        }
    }
    context.records = (Array.isArray(context.records) ? context.records : []).filter((row) => (
        !deletedIds.has(String(row?.id || row?.record_id || "").trim())
    ));
    context.selectedRecordKeys = [];
    if (context.recordsPage && typeof context.recordsPage === "object") {
        context.recordsPage.total = Math.max(0, Number(context.recordsPage.total || 0) - deleted);
    }
    const tree = ensureServiceRecordsTreeView(context);
    if (tree && typeof tree.clearSelection === "function") {
        tree.clearSelection();
    }
    renderNoCodeServiceRecordsTable();
    renderNoCodeServiceRecordsPagination();
    if (feedback) {
        const suffix = errors.length ? ` ${errors.length} erreur(s): ${errors.slice(0, 3).join(" | ")}${errors.length > 3 ? " | ..." : ""}` : "";
        feedback.textContent = `Suppression terminee: ${deleted} fiche(s) supprimee(s).${suffix}`;
    }
}

function buildNoCodeBatchFieldUpdateMarkup(batchContext) {
    const column = batchContext?.column || {};
    const selectedRows = Array.isArray(batchContext?.selectedRows) ? batchContext.selectedRows : [];
    const options = parseNoCodeOptions(column?.options || "");
    return `
        <form id="modal-service-records-batch-field-form" class="modal-form">
            <div class="modal-stack">
                <p class="muted">${escapeHtml(`${selectedRows.length} fiche${selectedRows.length > 1 ? "s" : ""} selectionnee${selectedRows.length > 1 ? "s" : ""}.`)}</p>
                <label class="field">
                    <span>${escapeHtml(String(column?.label || "Valeur"))}</span>
                    <select name="batch_field_value" required>
                        <option value="" selected disabled>Choisir une valeur</option>
                        ${options.map((option) => `<option value="${escapeHtml(option)}">${escapeHtml(option)}</option>`).join("")}
                    </select>
                </label>
                <p class="muted">La valeur choisie remplacera la valeur actuelle de ce champ pour toutes les fiches selectionnees.</p>
                <p id="modal-service-records-batch-field-feedback" class="muted inventory-feedback"></p>
                <div class="modal-actions">
                    ${createActionButtonMarkup({ preset: "cancel", type: "button", action: "service:records:batch-field:cancel", label: "Annuler" })}
                    ${createActionButtonMarkup({ preset: "save", type: "submit", label: "Appliquer" })}
                </div>
            </div>
        </form>
    `;
}

async function openNoCodeBatchFieldUpdateModal(fieldKey) {
    const context = state.noCodeServiceRecordContext;
    const normalizedFieldKey = String(fieldKey || "").trim();
    const column = noCodeRecordColumns(context?.service || null).find((candidate) => (
        String(candidate?.field_key || "").trim() === normalizedFieldKey
        && String(candidate?.kind || "") === "list"
        && Boolean(candidate?.batch_editable)
    ));
    const selectedRows = noCodeSelectedRecordRows(context);
    if (!context || !column || !selectedRows.length) {
        throw new Error("Selection ou champ modifiable par lot introuvable.");
    }
    state.noCodeBatchFieldUpdate = { context, column, selectedRows };
    openModal(
        `Modifier ${String(column.label || column.field_key || "")}`,
        buildNoCodeBatchFieldUpdateMarkup(state.noCodeBatchFieldUpdate),
        { width: "min(560px, calc(100vw - 32px))" },
    );
}

async function submitNoCodeBatchFieldUpdateForm(form) {
    const batchContext = state.noCodeBatchFieldUpdate;
    const context = batchContext?.context;
    const column = batchContext?.column;
    const feedback = document.getElementById("modal-service-records-batch-field-feedback");
    const serviceCode = String(context?.service?.code || "").trim();
    const fieldKey = String(column?.field_key || "").trim();
    const value = String(new window.FormData(form).get("batch_field_value") || "").trim();
    const selectedRows = Array.isArray(batchContext?.selectedRows) ? batchContext.selectedRows : [];
    const allowedValues = parseNoCodeOptions(column?.options || "");
    if (!context || !serviceCode || !fieldKey || !selectedRows.length || !value || !allowedValues.includes(value)) {
        if (feedback) {
            feedback.textContent = "Choisis une valeur valide de la liste.";
        }
        return;
    }
    const changedRows = selectedRows.filter((row) => String(row?.values?.[fieldKey] || "").trim() !== value);
    if (!changedRows.length) {
        if (feedback) {
            feedback.textContent = "Les fiches selectionnees ont deja cette valeur.";
        }
        return;
    }
    if (!(await showItopsConfirm({
        title: `Modifier ${changedRows.length} fiche${changedRows.length > 1 ? "s" : ""}`,
        message: `Appliquer « ${value} » au champ « ${String(column.label || fieldKey)} » ?`,
        confirmLabel: "Appliquer",
    }))) {
        return;
    }
    let historyDecision = { decision: "none", changedAt: "" };
    if (column.track_history) {
        historyDecision = await confirmNoCodeTrackedRecordChanges([{
            label: String(column.label || fieldKey),
            oldValue: "valeurs actuelles",
            newValue: value,
        }]);
        if (noCodeHistoryDecisionKind(historyDecision) === "cancel") {
            return;
        }
    }
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton instanceof HTMLButtonElement) {
        submitButton.disabled = true;
    }
    if (feedback) {
        feedback.textContent = "Mise a jour en cours...";
    }
    const errors = [];
    let updatedCount = 0;
    for (const row of changedRows) {
        const recordId = String(row?.id || row?.record_id || "").trim();
        if (!recordId) {
            continue;
        }
        const children = (Array.isArray(row?.children) ? row.children : []).map((child, index) => ({
            name: normalizeNoCodeText(child?.name),
            code: normalizeNoCodeText(child?.code),
            sort_order: Number(child?.sort_order || ((index + 1) * 10)),
        }));
        try {
            const updated = await requestJson(
                `/admin/custom-services/${encodeURIComponent(serviceCode)}/records/${encodeURIComponent(recordId)}`,
                {
                    method: "PUT",
                    body: JSON.stringify({
                        values: { ...(row?.values || {}), [fieldKey]: value },
                        children,
                        confirm_history_changes: Boolean(column.track_history) && noCodeHistoryDecisionKind(historyDecision) === "history",
                        skip_history_changes: Boolean(column.track_history) && noCodeHistoryDecisionKind(historyDecision) === "skip",
                        history_changed_at: noCodeHistoryDecisionChangedAt(historyDecision),
                        version_token: String(row?.version_token || ""),
                    }),
                },
            );
            replaceNoCodeServiceRecordInContext(context, updated);
            updatedCount += 1;
        } catch (error) {
            errors.push(`${recordId}: ${normalizeErrorMessage(error.message)}`);
        }
    }
    state.noCodeBatchFieldUpdate = null;
    context.selectedRecordKeys = [];
    const tree = ensureServiceRecordsTreeView(context);
    if (tree && typeof tree.clearSelection === "function") {
        tree.clearSelection();
    }
    renderNoCodeServiceRecordsTable();
    const suffix = errors.length ? ` ${errors.length} erreur(s): ${errors.slice(0, 3).join(" | ")}${errors.length > 3 ? " | ..." : ""}` : "";
    if (errors.length) {
        if (feedback) {
            feedback.textContent = `Mise a jour terminee: ${updatedCount} fiche(s) modifiee(s).${suffix}`;
        }
        return;
    }
    closeModal();
    const listFeedback = document.getElementById("modal-service-records-feedback");
    if (listFeedback) {
        listFeedback.textContent = `Mise a jour terminee: ${updatedCount} fiche(s) modifiee(s).`;
    }
}

function buildNoCodeServiceRecordsBatchContextMenuMarkup(rows) {
    const count = Array.isArray(rows) ? rows.length : 0;
    const context = state.noCodeServiceRecordContext;
    const singleRecord = count === 1 ? rows[0] : null;
    const relations = singleRecord ? noCodeRecordRelationsForContext(context) : [];
    const batchRelations = count > 0 ? noCodeRecordEditableRelationsForContext(context) : [];
    const recordId = String(singleRecord?.id || singleRecord?.record_id || "");
    const batchRelationMarkup = batchRelations.length
        ? createPortalContextMenuButton({
            label: "Assigner un element lie",
            action: "service:records:batch-relation-assign",
            disabled: count <= 0,
        })
        : "";
    const relationsMarkup = relations.length
        ? `
            <div class="context-menu-sep"></div>
            <div class="context-menu-label">Relations</div>
            ${relations.map((relation) => `
                <button class="context-menu-item" type="button"
                    data-action="service:records:relation-open"
                    data-relation-id="${escapeHtml(String(relation?.id || ""))}"
                    data-record-id="${escapeHtml(recordId)}">
                    <span>${escapeHtml(noCodeRelationMenuLabel(context, relation))}</span>
                </button>
            `).join("")}
        `
        : "";
    return `
        <div class="context-menu-group">
            <div class="context-menu-title">${escapeHtml(`${count} fiche${count > 1 ? "s" : ""} selectionnee${count > 1 ? "s" : ""}`)}</div>
            ${batchRelationMarkup}
            ${relationsMarkup}
            ${(batchRelationMarkup || relationsMarkup) ? '<div class="context-menu-sep"></div>' : ""}
            ${createPortalContextMenuButton({
                label: "Supprimer la selection",
                action: "service:records:batch-delete",
                hint: count > 0 ? "" : "Aucune selection",
                disabled: count <= 0,
            })}
        </div>
    `;
}

function buildNoCodeBatchRelationAssignMarkup(context) {
    const selectedRows = Array.isArray(context?.selectedRows) ? context.selectedRows : [];
    const relations = Array.isArray(context?.relations) ? context.relations : [];
    const selectedRelationId = String(context?.relation?.id || "");
    const candidates = Array.isArray(context?.candidates) ? context.candidates : [];
    const linkedService = context?.linkedService || {};
    const selectedIds = Array.isArray(context?.selectedLinkedRecordIds) ? context.selectedLinkedRecordIds : [];
    const relationOptions = relations.map((relation) => `
        <option value="${escapeHtml(String(relation?.id || ""))}" ${String(relation?.id || "") === selectedRelationId ? "selected" : ""}>
            ${escapeHtml(noCodeRelationLabelForContext(context?.relationContext, relation))}
        </option>
    `).join("");
    const candidatePicker = buildRelationAssignmentCandidatePickerMarkup({
        linkedService,
        relationContext: context?.relationContext,
        relation: context?.relation,
        candidates,
        selectedIds,
    });
    return `
        <form id="modal-service-records-batch-relation-form" class="modal-form" data-relation-id="${escapeHtml(selectedRelationId)}">
            <div class="modal-stack">
                <p class="muted">${escapeHtml(`${selectedRows.length} fiche${selectedRows.length > 1 ? "s" : ""} selectionnee${selectedRows.length > 1 ? "s" : ""}.`)}</p>
                <div class="modal-settings-grid">
                    <label class="field">
                        <span>Relation</span>
                        <select name="relation_id" data-service-records-batch-relation-select>
                            ${relationOptions}
                        </select>
                    </label>
                </div>
                ${candidatePicker}
                <p id="modal-service-records-batch-relation-feedback" class="muted inventory-feedback"></p>
                <div class="modal-actions">
                    <button type="button" class="ghost-button" data-action="modal:close">Annuler</button>
                    <button type="submit" class="primary-button" ${candidates.length ? "" : "disabled"}>Assigner</button>
                </div>
            </div>
        </form>
    `;
}

async function loadNoCodeBatchRelationAssignContext(relationId = "") {
    const relationContext = state.noCodeServiceRecordContext;
    const selectedRows = noCodeSelectedRecordRows(relationContext);
    if (!relationContext?.service || !selectedRows.length) {
        throw new Error("Selectionnez au moins une fiche.");
    }
    const relations = noCodeRecordEditableRelationsForContext(relationContext);
    if (!relations.length) {
        throw new Error("Aucune relation editable n'est disponible pour ce module.");
    }
    const wantedRelationId = Number(relationId || 0);
    const relation = relations.find((row) => Number(row?.id || 0) === wantedRelationId) || relations[0];
    const linkedServiceCode = noCodeRelationLinkedServiceCodeForContext(relationContext, relation);
    let linkedService = findNoCodeRelationEntity(linkedServiceCode);
    if (!linkedService) {
        await loadAdministrationData({
            includeModules: false,
            includeRoles: false,
            includeUsers: false,
            includeServices: true,
            includeSharedLists: false,
        });
        linkedService = findNoCodeRelationEntity(linkedServiceCode);
    }
    const candidatePage = await fetchNoCodeServiceRecordsPage(linkedServiceCode, {
        search: "",
        activeOnly: true,
        limit: 500,
        offset: 0,
        sort: "label",
        direction: "asc",
    }).catch(() => ({ items: [] }));
    return {
        relationContext,
        selectedRows,
        relations,
        relation,
        linkedService: linkedService || { code: linkedServiceCode, label: linkedServiceCode },
        candidates: Array.isArray(candidatePage?.items) ? candidatePage.items : [],
    };
}

async function openNoCodeBatchRelationAssignModal(relationId = "") {
    const context = await loadNoCodeBatchRelationAssignContext(relationId);
    state.noCodeBatchRelationContext = context;
    openModal(
        "Assigner un element lie",
        buildNoCodeBatchRelationAssignMarkup(context),
        { width: "min(720px, calc(100vw - 32px))" },
    );
}

async function reloadNoCodeBatchRelationAssignModal(relationId) {
    const feedback = document.getElementById("modal-service-records-batch-relation-feedback");
    try {
        const context = await loadNoCodeBatchRelationAssignContext(relationId);
        state.noCodeBatchRelationContext = context;
        const form = document.getElementById("modal-service-records-batch-relation-form");
        const parent = form?.parentElement;
        if (parent instanceof HTMLElement) {
            parent.innerHTML = buildNoCodeBatchRelationAssignMarkup(context);
        }
    } catch (error) {
        if (feedback instanceof HTMLElement) {
            feedback.textContent = normalizeErrorMessage(error.message);
        }
    }
}

async function submitNoCodeBatchRelationAssignForm(form) {
    const feedback = document.getElementById("modal-service-records-batch-relation-feedback");
    if (feedback instanceof HTMLElement) {
        feedback.textContent = "";
    }
    const data = new window.FormData(form);
    const relationId = Number(data.get("relation_id") || 0);
    const linkedRecordIds = readRelationAssignmentSelectedIds(form);
    const context = state.noCodeBatchRelationContext || await loadNoCodeBatchRelationAssignContext(relationId);
    const relation = noCodeRecordEditableRelationsForContext(context.relationContext)
        .find((row) => Number(row?.id || 0) === relationId);
    if (!relation || !linkedRecordIds.length) {
        if (feedback instanceof HTMLElement) {
            feedback.textContent = "Selectionnez une relation et au moins un element a lier.";
        }
        return;
    }
    if (!noCodeRelationAllowsMultipleLinkedFromCurrent(context.relationContext, relation) && linkedRecordIds.length > 1) {
        if (feedback instanceof HTMLElement) {
            feedback.textContent = "Cette relation accepte un seul element lie par fiche.";
        }
        return;
    }
    try {
        const totals = { created: 0, replaced: 0, skipped: 0, errors: [] };
        for (const linkedRecordId of linkedRecordIds) {
            const result = await assignNoCodeRelationLinkToRecords({
                context: context.relationContext,
                records: context.selectedRows,
                relation,
                linkedRecordId,
            });
            totals.created += Number(result.created || 0);
            totals.replaced += Number(result.replaced || 0);
            totals.skipped += Number(result.skipped || 0);
            totals.errors.push(...(Array.isArray(result.errors) ? result.errors : []));
        }
        if (feedback instanceof HTMLElement) {
            const skippedSuffix = totals.skipped ? ` ${totals.skipped} deja lie(s) ou ignore(s).` : "";
            const replacedSuffix = totals.replaced ? ` ${totals.replaced} ancien(s) lien(s) remplace(s).` : "";
            feedback.textContent = totals.errors.length
                ? `Lien applique a ${totals.created} fiche(s).${replacedSuffix}${skippedSuffix} Erreurs: ${totals.errors.slice(0, 3).join(" | ")}`
                : `Lien applique a ${totals.created} fiche(s).${replacedSuffix}${skippedSuffix}`;
        }
    } catch (error) {
        if (feedback instanceof HTMLElement) {
            feedback.textContent = normalizeErrorMessage(error.message);
        }
    }
}

function openNoCodeServiceRecordsBatchContextMenu(x, y, rows = noCodeSelectedRecordRows(state.noCodeServiceRecordContext)) {
    const selectedRows = Array.isArray(rows) ? rows : [];
    if (!selectedRows.length || !(cardsContextMenu instanceof HTMLElement)) {
        return false;
    }
    state.portalContextModuleCode = "";
    cardsContextMenu.innerHTML = buildNoCodeServiceRecordsBatchContextMenuMarkup(selectedRows);
    cardsContextMenu.hidden = false;
    const maxX = window.innerWidth - cardsContextMenu.offsetWidth - 12;
    const maxY = window.innerHeight - cardsContextMenu.offsetHeight - 12;
    cardsContextMenu.style.left = `${Math.max(8, Math.min(x, maxX))}px`;
    cardsContextMenu.style.top = `${Math.max(8, Math.min(y, maxY))}px`;
    return true;
}

function bindNoCodeServiceRecordsInlineEdit(context) {
    const body = document.getElementById("service-records-body");
    if (!(body instanceof HTMLElement) || body.dataset.inlineEditBound === "1") {
        return;
    }
    body.dataset.inlineEditBound = "1";
    body.addEventListener("change", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLInputElement) && !(target instanceof HTMLSelectElement)) {
            return;
        }
        if (!target.matches("[data-no-code-inline-field]")) {
            return;
        }
        const activeContext = context || state.noCodeServiceRecordContext;
        if (String(activeContext?.service?.code || "").trim().toLowerCase() === "emails") {
            return;
        }
        applyNoCodeInlineRecordValue(target).catch((error) => {
            const feedback = document.getElementById("modal-service-records-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        });
    });
}

function bindNoCodeServiceRecordsContextMenu(context) {
    const body = document.getElementById("service-records-body");
    if (!(body instanceof HTMLElement) || body.dataset.batchContextMenuBound === "1") {
        return;
    }
    body.dataset.batchContextMenuBound = "1";
    body.addEventListener("contextmenu", (event) => {
        const target = event.target;
        if (!(target instanceof Element)) {
            return;
        }
        if (target.closest("button, a, input, select, textarea")) {
            return;
        }
        const rowElement = target.closest("tr[data-tree-row-key]");
        if (!(rowElement instanceof HTMLElement)) {
            return;
        }
        const recordId = String(rowElement.dataset.treeRowKey || "").trim();
        if (!recordId) {
            return;
        }
        const activeContext = context || state.noCodeServiceRecordContext;
        if (!activeContext) {
            return;
        }
        const selectedKeys = new Set(
            Array.isArray(activeContext.selectedRecordKeys)
                ? activeContext.selectedRecordKeys.map((key) => String(key || "").trim()).filter(Boolean)
                : [],
        );
        const tree = activeContext._recordsTreeView || null;
        if (!selectedKeys.has(recordId)) {
            activeContext.selectedRecordKeys = [recordId];
            if (tree) {
                tree.selectedRowKeys = new Set([recordId]);
                tree.render();
            } else {
                renderNoCodeServiceRecordsTable();
            }
        }
        const selectedRows = noCodeSelectedRecordRows(activeContext);
        if (!selectedRows.length) {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        openNoCodeServiceRecordsBatchContextMenu(event.clientX, event.clientY, selectedRows);
    });
}

function bindNoCodeServiceRecordsBatchToolbar(context) {
    const selector = document.getElementById("service-records-batch-action");
    if (!(selector instanceof HTMLSelectElement) || selector.dataset.batchActionBound === "1") {
        return;
    }
    selector.dataset.batchActionBound = "1";
    selector.addEventListener("change", () => {
        const action = String(selector.value || "").trim();
        if (action === "delete") {
            selector.value = "";
            deleteSelectedNoCodeServiceRecords().finally(() => {
                updateNoCodeServiceRecordsBatchActions(context || state.noCodeServiceRecordContext);
            });
            return;
        }
        if (action === "relation") {
            selector.value = "";
            openNoCodeBatchRelationAssignModal().catch((error) => {
                const feedback = document.getElementById("modal-service-records-feedback");
                if (feedback) {
                    feedback.textContent = normalizeErrorMessage(error.message);
                }
            }).finally(() => {
                updateNoCodeServiceRecordsBatchActions(context || state.noCodeServiceRecordContext);
            });
            return;
        }
        if (action.startsWith("field:")) {
            selector.value = "";
            openNoCodeBatchFieldUpdateModal(action.slice("field:".length)).catch((error) => {
                const feedback = document.getElementById("modal-service-records-feedback");
                if (feedback) {
                    feedback.textContent = normalizeErrorMessage(error.message);
                }
            }).finally(() => {
                updateNoCodeServiceRecordsBatchActions(context || state.noCodeServiceRecordContext);
            });
            return;
        }
        updateNoCodeServiceRecordsBatchActions(context || state.noCodeServiceRecordContext);
    });
}

function bindNoCodeServiceRecordsInteractions() {
    const context = state.noCodeServiceRecordContext;
    ensureServiceRecordsTreeView(context);
    bindNoCodeServiceRecordsDoubleClick(context);
    bindNoCodeServiceRecordsQuickFilters(context);
    bindNoCodeServiceRecordsInlineEdit(context);
    bindNoCodeServiceRecordsContextMenu(context);
    bindNoCodeServiceRecordsBatchToolbar(context);
    updateNoCodeServiceRecordsFilterActions(context);
    renderNoCodeServiceRecordsPagination();
}

function buildNoCodeDuplicateAnalysisMarkup(context, result = null) {
    const service = context?.service || {};
    const fields = noCodeCustomServiceFields(service).filter((field) => String(field?.field_key || "").trim());
    const fieldKey = String(result?.field_key || "").trim();
    const groups = Array.isArray(result?.groups) ? result.groups : [];
    const rows = groups.map((group) => `
        <tr><td>${escapeHtml(String(group?.value || ""))}</td><td>${escapeHtml(String((group?.records || []).length))}</td><td>${escapeHtml((group?.records || []).map((record) => String(record?.id || "")).join(", "))}</td></tr>
    `).join("");
    return `
        <section class="modal-section">
            <h3>Nettoyage des doublons — ${escapeHtml(String(service?.label || "Module"))}</h3>
            <p class="muted">Choisissez l'identifiant stable. Les modules synchronises depuis l'AD seront analyses mais restent proteges contre la fusion automatique.</p>
            <div class="modal-settings-grid"><label class="field"><span>Identifiant stable</span><select id="duplicate-analysis-field"><option value="">Choisir un champ</option>${fields.map((field) => `<option value="${escapeHtml(String(field.field_key))}" ${String(field.field_key) === fieldKey ? "selected" : ""}>${escapeHtml(String(field.label || field.field_key))}</option>`).join("")}</select></label></div>
            ${result ? `<p class="muted">${Number(result.group_count || 0)} groupe(s), ${Number(result.record_count || 0)} fiche(s) concernees.</p><div class="table-scroll"><table class="device-table"><thead><tr><th>Valeur</th><th>Fiches</th><th>Identifiants</th></tr></thead><tbody>${rows || '<tr><td colspan="3" class="muted">Aucun doublon detecte.</td></tr>'}</tbody></table></div>` : ""}
            <p id="duplicate-analysis-feedback" class="muted inventory-feedback"></p>
            ${createModalActionsMarkup({ buttons: [{ preset: "back", type: "button", action: "duplicates:back", label: "Retour" }, { preset: "search", type: "button", action: "duplicates:analyze", label: "Analyser" }] })}
        </section>`;
}

function buildNoCodeRecordsModalMarkup(context) {
    const service = context?.service || null;
    const serviceLabel = String(service?.label || service?.code || "").trim();
    const actionLabels = noCodeServiceActionLabels(service);
    const importPreview = buildNoCodeRecordsImportPreviewMarkup(context);
    const quickFilters = buildNoCodeRecordsQuickFiltersMarkup(context);
    const batchToolbar = buildNoCodeRecordsBatchToolbarMarkup(context);
    const selectedCount = noCodeSelectedRecordRows(context).length;
    const isEmailService = String(service?.code || "").trim().toLowerCase() === "emails";
    const serviceDefinitionActionMarkup = isSystemNoCodeService(service)
        ? ""
        : createActionButtonMarkup({
            className: "toolbar-btn",
            type: "button",
            action: "service:definition:edit",
            label: actionLabels.edit,
            title: "Modifier la definition du service",
            data: { service_code: String(service?.code || "") },
        });
    return buildTreeSectionMarkup({
        title: `Inventaire ${serviceLabel || "Service"}`,
        titleActionsMarkup: `
            ${serviceDefinitionActionMarkup}
            ${createActionButtonMarkup({
                preset: "export",
                action: "service:records:export",
                label: actionLabels.export,
            })}
            ${createActionButtonMarkup({
                preset: "import",
                className: "toolbar-btn",
                action: "service:records:import",
                label: actionLabels.import,
                title: "Importer un fichier CSV ou XLSX (detection automatique)",
            })}
            ${createActionButtonMarkup({
                className: "toolbar-btn",
                type: "button",
                action: "service:records:duplicates",
                label: actionLabels.duplicates,
                title: "Analyser les doublons selon un identifiant stable",
            })}
            ${createActionButtonMarkup({
                className: "toolbar-btn",
                type: "button",
                action: "service:records:filters:clear",
                label: "Reinitialiser filtres",
                title: "Vider la recherche et les filtres rapides",
                disabled: !noCodeServiceRecordsHasActiveFilters(context),
            })}
            ${createActionButtonMarkup({
                preset: "add",
                className: "toolbar-btn",
                type: "button",
                action: "service:record:add",
                label: actionLabels.add,
            })}
            ${createActionButtonMarkup({
                id: "service-records-batch-delete",
                className: "toolbar-btn danger",
                type: "button",
                action: "service:records:batch-delete",
                label: selectedCount > 0 ? `Supprimer selection (${selectedCount})` : "Supprimer selection",
                title: "Supprimer les fiches selectionnees",
                disabled: selectedCount <= 0,
            })}
        `,
        searchId: "service-records-search",
        searchLabel: "Filtre",
        searchPlaceholder: isEmailService ? "Adresse mail, alias, service..." : "ID, valeurs, elements lies...",
        searchInTitleRow: false,
        extraToolsMarkup: (searchMarkup) => buildNoCodeRecordsTopControlsMarkup(context, searchMarkup),
        filtersMarkup: quickFilters,
        beforeTableMarkup: `${importPreview}${batchToolbar}`,
        headId: "service-records-head",
        bodyId: "service-records-body",
        afterTableMarkup: `
            ${buildNoCodeRecordsBottomControlsMarkup(context)}
            <div id="service-records-import-progress-wrap" class="modal-scan-progress modal-scan-progress-top" hidden>
                <progress id="service-records-import-progress" value="0" max="100"></progress>
                <span id="service-records-import-progress-status" class="muted">Pret.</span>
            </div>
        `,
        feedbackId: "modal-service-records-feedback",
        footerActionsMarkup: createModalActionsMarkup({
            buttons: [{ preset: "back", action: "service:records:back-services", label: "Retour services" }],
        }),
    });
}

function buildNoCodeRecordsImportPreviewMarkup(context) {
    const preview = context?.importPreview;
    const service = context?.service || null;
    if (!preview || !Array.isArray(preview.rows) || !preview.rows.length || !service) {
        return "";
    }
    const fields = Array.isArray(preview.fields) && preview.fields.length
        ? preview.fields
        : noCodeCustomServiceFields(service);
    const visibleFields = fields.slice(0, 5);
    const headCells = visibleFields.map((field) => `<th>${escapeHtml(String(field.label || field.field_key || ""))}</th>`).join("");
    const rowsMarkup = preview.rows.slice(0, 12).map((row) => {
        const values = row?.values || {};
        const valueCells = visibleFields.map((field) => {
            const key = String(field.field_key || "");
            return `<td>${escapeHtml(formatNoCodeRecordDisplayValue(values[key] || "", { kind: field.field_kind }))}</td>`;
        }).join("");
        const recordId = String(row?.record_id || "").trim();
        const childCount = Array.isArray(row?.children) ? row.children.length : 0;
        return `
            <tr>
                <td>${escapeHtml(recordId || "(nouvelle)")}</td>
                ${valueCells}
                <td>${service?.child_enabled ? childCount : "-"}</td>
            </tr>
        `;
    }).join("");
    const rowsCount = Number(preview.detectedRows || 0);
    const colsCount = Number(preview.detectedColumns || 0);
    const sourceHeaders = Array.isArray(preview.sourceHeaders) ? preview.sourceHeaders : [];
    const sourceRowsPreview = Array.isArray(preview.sourceRowsPreview) ? preview.sourceRowsPreview : [];
    if (!Array.isArray(context.importColumnMappings) || !context.importColumnMappings.length) {
        context.importColumnMappings = buildServiceRecordImportMappingsFromEffectiveMapping(preview.effectiveMapping);
        if (!context.importColumnMappings.length) {
            context.importColumnMappings = buildDefaultServiceRecordImportMappings(service, sourceHeaders);
        }
    }
    const availableSheets = Array.isArray(preview.availableSheets) ? preview.availableSheets : [];
    const selectedSheetName = String(preview.selectedSheetName || context?.importSheetName || "").trim();
    const headerMode = normalizeTabularHeaderMode(context?.importHeaderMode || preview.effectiveHeaderMode || "auto");
    const headerRowNumber = normalizeTabularHeaderRowNumber(context?.importHeaderRowNumber || preview.detectedHeaderRowNumber || 1);
    const detectedHeaderRow = normalizeTabularHeaderRowNumber(preview.detectedHeaderRowNumber || headerRowNumber);
    const effectiveHeaderMode = normalizeTabularHeaderMode(preview.effectiveHeaderMode || headerMode);
    const issues = Array.isArray(preview.issues) ? preview.issues.filter((item) => String(item || "").trim()) : [];
    const credentialMode = normalizeRecordsImportCredentialMode(context?.importCredentialMode);
    const duplicatePolicy = ["skip", "update", "create"].includes(String(context?.importDuplicatePolicy || "")) ? context.importDuplicatePolicy : "skip";
    const stableIdentifierField = fields.find((field) => Boolean(field?.unique_value))
        || fields.find((field) => /serial|serie|inventaire|asset|mac|adresse_ip|ip/.test(String(field?.field_key || "").toLowerCase()))
        || null;
    const duplicateFieldKey = String(
        context?.importDuplicateFieldKey
        || (String(service?.code || "").toLowerCase() === "emails" ? "address" : stableIdentifierField?.field_key || ""),
    ).trim();
    const duplicateFieldOptions = fields.map((field) => {
        const key = String(field?.field_key || "").trim();
        return key ? `<option value="${escapeHtml(key)}" ${key === duplicateFieldKey ? "selected" : ""}>${escapeHtml(String(field?.label || key))}</option>` : "";
    }).join("");
    const credentialModeOptions = RECORD_IMPORT_CREDENTIAL_MODES
        .map((option) => (
            `<option value="${escapeHtml(option.value)}" ${credentialMode === option.value ? "selected" : ""}>${escapeHtml(option.label)}</option>`
        ))
        .join("");
    const sheetSelectorMarkup = availableSheets.length > 1
        ? `
            <div class="modal-settings-grid">
                <label class="field">
                    <span>Feuille Excel</span>
                    <select name="service_records_import_sheet">
                        ${availableSheets.map((sheet) => {
                            const label = String(sheet || "").trim();
                            const selected = label && label === selectedSheetName;
                            return `<option value="${escapeHtml(label)}" ${selected ? "selected" : ""}>${escapeHtml(label)}</option>`;
                        }).join("")}
                    </select>
                </label>
            </div>
        `
        : "";
    const headerModeOptions = TABULAR_HEADER_MODES
        .map((option) => (
            `<option value="${escapeHtml(option.value)}" ${headerMode === option.value ? "selected" : ""}>${escapeHtml(option.label)}</option>`
        ))
        .join("");
    const issuesMarkup = issues.length
        ? `<p class="muted">Alertes detectees: ${issues.length} (${escapeHtml(String(issues[0] || ""))}${issues.length > 1 ? "..." : ""})</p>`
        : "";
    const importActionsMarkup = `
        <div class="inventory-row-actions no-code-import-actions">
            ${createActionButtonMarkup({
                className: "toolbar-btn",
                type: "button",
                action: "service:records:import:clear",
                label: "Ignorer",
                iconHtml: "&#10005;",
            })}
            ${createActionButtonMarkup({
                className: "primary-btn",
                type: "button",
                action: "service:records:import:apply",
                label: "Appliquer l'import",
                iconHtml: "&#10003;",
            })}
        </div>
    `;
    return `
        <section class="modal-section type-schema-fields-section">
            <div class="type-schema-fields-head">
                <h3>Apercu de l'import</h3>
                ${importActionsMarkup}
            </div>
            <p class="muted">${escapeHtml(String(preview.filename || "Fichier"))} | ${rowsCount} ligne(s) detectee(s) | ${colsCount} colonne(s)</p>
            ${sheetSelectorMarkup}
            <div class="modal-settings-grid">
                <label class="field">
                    <span>Detection entete</span>
                    <select name="service_records_import_header_mode">
                        ${headerModeOptions}
                    </select>
                </label>
                <label class="field">
                    <span>Ligne entete</span>
                    <input name="service_records_import_header_row" type="number" min="1" step="1" value="${escapeHtml(String(headerRowNumber))}" ${headerMode === "manual" ? "" : "disabled"}>
                </label>
            </div>
            <p class="muted">Entete active: ligne ${detectedHeaderRow} (${effectiveHeaderMode}).</p>
            <h4>Association colonnes</h4>
            ${buildServiceRecordImportMappingMarkup(context, sourceHeaders, sourceRowsPreview)}
            ${service?.credentials_enabled ? `
                <div class="modal-settings-grid">
                    <label class="field">
                        <span>Identifiants existants</span>
                        <select name="service_records_import_credential_mode">
                            ${credentialModeOptions}
                        </select>
                    </label>
                </div>
                <p class="muted">Dans l'association des colonnes, vous pouvez mapper un identifiant et/ou un mot de passe vers les champs securises. Pour les e-mails, l'identifiant est facultatif : l'adresse e-mail reste l'identifiant naturel de la fiche.</p>
            ` : ""}
            <div class="modal-settings-grid">
                <label class="field"><span>En cas de doublon</span><select name="service_records_import_duplicate_policy"><option value="skip" ${duplicatePolicy === "skip" ? "selected" : ""}>Ignorer la ligne du fichier</option><option value="update" ${duplicatePolicy === "update" ? "selected" : ""}>Mettre a jour la fiche existante</option><option value="create" ${duplicatePolicy === "create" ? "selected" : ""}>Creer quand meme</option></select></label>
                <label class="field"><span>Identifiant stable pour detecter les doublons</span><select name="service_records_import_duplicate_field"><option value="">Identifiant de fiche uniquement</option>${duplicateFieldOptions}</select><small>Conseil : numero de serie, code inventaire ou adresse MAC. L'adresse IP peut changer.</small></label>
            </div>
            ${issuesMarkup}
            <h4>Apercu mappe</h4>
            <div class="table-wrap">
                <table class="device-table">
                    <thead>
                        <tr>
                            <th>record_id</th>
                            ${headCells || "<th>Valeur</th>"}
                            <th>Elements lies</th>
                        </tr>
                    </thead>
                    <tbody>${rowsMarkup}</tbody>
                </table>
            </div>
            ${importActionsMarkup}
        </section>
    `;
}

function noCodeRecordInputType(fieldKind) {
    const kind = normalizeNoCodeKind(fieldKind);
    if (kind === "date") {
        return "date";
    }
    if (kind === "url") {
        return "url";
    }
    return "text";
}

function noCodeRecordEditorEntityLabel(service) {
    const label = String(service?.label || service?.code || "").trim();
    if (!label) {
        return "Element";
    }
    const normalized = label.toLowerCase();
    if (["utilisateurs", "users", "agents"].includes(normalized)) {
        return "Agent";
    }
    if (["emails", "e-mails", "mails"].includes(normalized)) {
        return "Adresse e-mail";
    }
    return label;
}

function noCodeRecordEditorModalTitle(service, mode) {
    const label = noCodeRecordEditorEntityLabel(service);
    return String(mode || "").toLowerCase() === "edit"
        ? `Edition — ${label}`
        : `Creation — ${label}`;
}

function recordAssignmentDefinition(context, editor) {
    const ownerCode = String(context?.service?.code || "").trim().toLowerCase();
    return editor?.mode === "edit" && String(editor?.recordId || "").trim()
        ? noCodeRecordRelationsForContext(context).find((relation) =>
            [
                String(relation?.source_service_code || "").trim().toLowerCase(),
                normalizeNoCodeRelationEntityCode(relation?.target_service_code || relation?.service_code || ""),
            ].includes(ownerCode)
            && String(relation?.record_display_mode || "standard").trim().toLowerCase() === "assignment"
            && String(relation?.assignment_resource_service_code || "").trim(),
        ) || null
        : null;
}

async function buildRecordAssignment(context, editor) {
    const definition = recordAssignmentDefinition(context, editor);
    if (!definition) return null;
    const ownerCode = String(context.service.code || "").trim().toLowerCase();
    const ownerId = String(editor.recordId || "").trim();
    const definitionSourceCode = String(definition?.source_service_code || "").trim().toLowerCase();
    const isSourcePerspective = definitionSourceCode === ownerCode;
    const beneficiaryCode = noCodeRelationLinkedServiceCodeForContext(context, definition);
    const resourceCode = normalizeNoCodeRelationEntityCode(definition.assignment_resource_service_code || "");
    const resourceService = findNoCodeService(resourceCode);
    const beneficiaryService = findNoCodeRelationEntity(beneficiaryCode) || { code: beneficiaryCode, label: beneficiaryCode };
    const resourceRelations = await fetchNoCodeServiceRelations(resourceCode).catch(() => []);
    const ownerRelation = resourceRelations.find((relation) => String(relation?.source_service_code || "").toLowerCase() === resourceCode && String(relation?.target_service_code || "").toLowerCase() === ownerCode);
    const beneficiaryRelation = resourceRelations.find((relation) => String(relation?.source_service_code || "").toLowerCase() === resourceCode && String(relation?.target_service_code || "").toLowerCase() === beneficiaryCode);
    if (!ownerRelation || !beneficiaryRelation || !resourceService) return null;
    const [beneficiaryLinks, resourceLinks] = await Promise.all([
        fetchNoCodeServiceRecordRelationLinks(ownerCode, ownerId, Number(definition.id || 0)),
        fetchNoCodeServiceRecordRelationLinks(ownerCode, ownerId, Number(ownerRelation.id || 0)),
    ]);
    const beneficiaries = (beneficiaryLinks || []).map((link) => link?.linked_record || {}).filter((row) => row?.id);
    const resources = (resourceLinks || []).map((link) => link?.linked_record || {}).filter((row) => row?.id);
    const resourceLinksById = resources.length ? await fetchNoCodeServiceRecordRelationLinksBatch(resourceCode, resources.map((row) => String(row.id)), Number(beneficiaryRelation.id || 0)) : {};
    const resourceByBeneficiaryId = new Map();
    resources.forEach((resource) => {
        const beneficiary = (resourceLinksById?.[String(resource.id)] || [])[0]?.linked_record;
        if (beneficiary?.id && !resourceByBeneficiaryId.has(String(beneficiary.id))) {
            resourceByBeneficiaryId.set(String(beneficiary.id), {
                id: String(resource.id),
                label: noCodeRecordPrimaryLabel(resourceService, resource),
            });
        }
    });
    return {
        ownerCode, ownerId, definition, resourceCode, resourceService, beneficiaryCode, beneficiaryService,
        title: isSourcePerspective ? String(definition.display_label || definition.label || "").trim() : "",
        beneficiaries: beneficiaries.map((row) => ({
            id: String(row.id),
            label: noCodeRecordPrimaryLabel(beneficiaryService, row),
            resource: resourceByBeneficiaryId.get(String(row.id)) || null,
        })),
        ownerRelationId: Number(ownerRelation.id || 0), beneficiaryRelationId: Number(beneficiaryRelation.id || 0),
    };
}

function buildRecordAssignmentMarkup(context, editor) {
    const assignments = editor?.recordAssignment;
    if (!assignments || !Array.isArray(assignments.beneficiaries)) {
        return "";
    }
    const rows = assignments.beneficiaries.map((beneficiary) => {
        const beneficiaryChip = noCodeRelationSummaryChipMarkup({
            linkedServiceCode: assignments.beneficiaryCode,
            recordId: beneficiary.id,
            label: beneficiary.label,
        });
        const resourceChip = beneficiary.resource?.id
            ? noCodeRelationSummaryChipMarkup({
                linkedServiceCode: assignments.resourceCode,
                recordId: beneficiary.resource.id,
                label: beneficiary.resource.label,
            })
            : '<span class="muted">Non attribue</span>';
        return `
            <tr>
                <td>${beneficiaryChip}</td>
                <td>${resourceChip}</td>
                <td class="inventory-row-actions">
                    ${createIconActionButtonMarkup({
                        icon: "delete",
                        danger: true,
                        action: "assignment:beneficiary:unlink",
                        title: `Delier ${beneficiary.label || "cet element"}`,
                        data: {
                            beneficiary_id: beneficiary.id,
                            resource_id: beneficiary.resource?.id || "",
                        },
                    })}
                </td>
            </tr>
        `;
    }).join("");
    const beneficiaryLabel = noCodeRecordEditorEntityLabel(assignments.beneficiaryService);
    const resourceLabel = noCodeRecordEditorEntityLabel(assignments.resourceService);
    const allowsSeveralBeneficiaries = noCodeRelationAllowsMultipleLinkedFromCurrent(context, assignments.definition);
    return `
        <section class="modal-section">
            <div class="type-schema-fields-head">
                <div>
                    <h3>${escapeHtml(assignments.title || `${beneficiaryLabel} et ${resourceLabel}`)}</h3>
                    <p class="muted">Creez un ${escapeHtml(resourceLabel.toLowerCase())} et attribuez-le a ${escapeHtml(beneficiaryLabel.toLowerCase())} de votre choix.</p>
                    ${createActionButtonMarkup({ preset: "add", action: "assignment:resource:add", label: `Ajouter ${resourceLabel.toLowerCase()}` })}
                    ${allowsSeveralBeneficiaries ? createActionButtonMarkup({ preset: "secondary", action: "assignment:beneficiary:add", label: `Ajouter ${pluralizeNoCodeRelationLabel(beneficiaryLabel)}` }) : ""}
                </div>
            </div>
            ${assignments.beneficiaries.length ? `
                <div class="table-scroll">
                    <table class="device-table inventory-table">
                        <thead><tr><th>${escapeHtml(beneficiaryLabel)}</th><th>${escapeHtml(resourceLabel)}</th><th>Actions</th></tr></thead>
                        <tbody>${rows}</tbody>
                    </table>
                </div>
            ` : `
                <p class="muted">Aucun ${escapeHtml(beneficiaryLabel.toLowerCase())} n'est encore lie. Cliquez sur « Ajouter ${escapeHtml(resourceLabel.toLowerCase())} » puis choisissez « Ajouter un element lie... » dans la liste.</p>
            `}
        </section>
    `;
}

function buildRecordAssignmentCreateMarkup(context) {
    const createContext = state.relationAssignmentCreate || {};
    const assignments = createContext.assignments || { beneficiaries: [] };
    const selectedBeneficiaryId = String(createContext.selectedBeneficiaryId || "").trim();
    const resourceService = assignments.resourceService || { label: "Element", fields: [] };
    const beneficiaryService = assignments.beneficiaryService || { label: "Element lie" };
    const fields = noCodeCustomServiceFields(resourceService);
    const primaryField = fields[0] || { label: "Valeur", field_key: "value" };
    const additionalFields = fields
        .filter((field) => String(field?.field_key || "").trim().toLowerCase() !== String(primaryField.field_key || "").trim().toLowerCase());
    const additionalFieldsMarkup = additionalFields
        .filter((field) => String(field?.field_key || "").trim().toLowerCase() !== "status")
        .map((field) => {
            const key = String(field?.field_key || "").trim();
            const label = String(field?.label || key).trim() || key;
            const defaultValue = String(field?.default_value || "");
            if (normalizeNoCodeKind(field?.field_kind || "text") === "list") {
                return `
                    <label class="field">
                        <span>${escapeHtml(label)}${field?.required ? " *" : ""}</span>
                        <select name="assignment_field_${escapeHtml(key)}" ${field?.required ? "required" : ""}>
                            ${parseNoCodeOptions(field?.options || "").map((option) => `<option value="${escapeHtml(option)}" ${option === defaultValue ? "selected" : ""}>${escapeHtml(option)}</option>`).join("")}
                        </select>
                    </label>
                `;
            }
            return `
                <label class="field">
                    <span>${escapeHtml(label)}${field?.required ? " *" : ""}</span>
                    <input name="assignment_field_${escapeHtml(key)}" type="${escapeHtml(noCodeRecordInputType(field?.field_kind || "text"))}" value="${escapeHtml(defaultValue)}" ${field?.required ? "required" : ""}>
                </label>
            `;
        }).join("");
    const statusField = additionalFields.find((field) => String(field?.field_key || "").trim().toLowerCase() === "status");
    const fixedStatus = String(statusField?.default_value || "Actif").trim() || "Actif";
    return `
        <form id="modal-relation-assignment-form" class="modal-form">
            <section class="modal-section">
                <h3>Ajouter ${escapeHtml(noCodeRecordEditorEntityLabel(resourceService).toLowerCase())}</h3>
                <p class="muted">L'element sera automatiquement lie a la fiche ouverte et a l'element choisi.</p>
                <div class="modal-settings-grid">
                    <label class="field">
                        <span>${escapeHtml(String(primaryField.label || "Valeur"))} *</span>
                        <input name="assignment_primary_value" type="text" required autofocus>
                    </label>
                    <label class="field">
                        <span>${escapeHtml(noCodeRecordEditorEntityLabel(beneficiaryService))} *</span>
                        <select name="assignment_beneficiary" required>
                            <option value="">Choisir un element</option>
                            ${(assignments.beneficiaries || []).map((row) => `<option value="${escapeHtml(row.id)}" ${row.id === selectedBeneficiaryId ? "selected" : ""}>${escapeHtml(row.label)}</option>`).join("")}
                            <option value="__add_beneficiary__">Ajouter un element lie...</option>
                        </select>
                    </label>
                    ${additionalFieldsMarkup}
                </div>
                ${statusField ? `<p class="muted">Statut applique automatiquement : <strong>${escapeHtml(fixedStatus)}</strong></p>` : ""}
                ${(assignments.beneficiaries || []).length ? "" : `<p class="muted">Aucun ${escapeHtml(noCodeRecordEditorEntityLabel(beneficiaryService).toLowerCase())} n'est encore lie a cette fiche : choisissez « Ajouter un element lie... » dans la liste.</p>`}
            </section>
            <p id="modal-relation-assignment-feedback" class="muted inventory-feedback"></p>
            ${createModalActionsMarkup({ buttons: [{ preset: "back", type: "button", action: "assignment:resource:back", label: "Retour a la fiche" }, { preset: "add", label: "Creer et attribuer" }] })}
        </form>
    `;
}

async function openRecordAssignmentCreateForm() {
    const context = state.noCodeServiceRecordContext;
    const editor = state.noCodeRecordEditor;
    const assignments = context && editor ? await buildRecordAssignment(context, editor) : null;
    if (!assignments?.ownerRelationId || !assignments?.beneficiaryRelationId) {
        throw new Error("Les relations d'attribution ne sont pas disponibles.");
    }
    editor.recordAssignment = assignments;
    state.relationAssignmentCreate = {
        ownerId: String(editor.recordId || "").trim(),
        assignments,
    };
    openModal(`Ajouter ${noCodeRecordEditorEntityLabel(assignments.resourceService).toLowerCase()}`, buildRecordAssignmentCreateMarkup(context), { width: "min(720px, calc(100vw - 40px))" });
}

async function returnToRecordAssignmentEditor() {
    const context = state.noCodeServiceRecordContext;
    const editor = state.noCodeRecordEditor;
    state.relationAssignmentCreate = null;
    if (!recordAssignmentDefinition(context, editor)) {
        closeModal();
        return;
    }
    editor.recordAssignment = null;
    await reopenRecordAssignmentOwnerEditor(context, editor);
}

async function openRecordAssignmentBeneficiaryPicker() {
    const context = state.noCodeServiceRecordContext;
    const editor = state.noCodeRecordEditor;
    const assignments = context && editor ? await buildRecordAssignment(context, editor) : null;
    if (!assignments?.definition?.id || !assignments?.ownerId) {
        throw new Error("La relation a utiliser est indisponible.");
    }
    state.relationAssignmentCreate = {
        ownerId: String(editor.recordId || "").trim(),
        assignments,
        linkOnly: true,
    };
    await openRecordAssignmentPicker();
}

async function reopenRecordAssignmentOwnerEditor(context, editor) {
    if (!context?.service || !editor) {
        closeModal();
        return;
    }
    const isDirectoryRecord = Boolean(state.directoryRecordEditor)
        && Boolean(findNoCodeRelationSystemEntity(context?.service?.code || ""));
    openModal(
        noCodeRecordEditorModalTitle(context.service, "edit"),
        isDirectoryRecord ? buildDirectoryRecordEditorMarkup() : buildNoCodeRecordEditorMarkup(),
        noCodeInlineOptions("min(980px, calc(100vw - 40px))", { inline: true }),
    );
    await loadNoCodeRecordRelationExperience();
}

function buildRecordAssignmentPickerMarkup() {
    const picker = state.relationAssignmentPicker || { query: "", rows: [] };
    const createContext = state.relationAssignmentCreate || {};
    const assignments = createContext.assignments || {};
    const label = noCodeRecordEditorEntityLabel(assignments.beneficiaryService);
    const allowsBatch = Boolean(createContext.linkOnly)
        && noCodeRelationAllowsMultipleLinkedFromCurrent(state.noCodeServiceRecordContext, assignments.definition);
    const batchMode = allowsBatch && Boolean(picker.batchMode);
    const rowsMarkup = (picker.rows || []).map((row) => `
        <tr data-assignment-beneficiary-row data-record-id="${escapeHtml(String(row.id || ""))}" data-search-text="${escapeHtml(noCodeRecordSearchText(assignments.beneficiaryService, row))}" title="${escapeHtml(batchMode ? "Cochez pour selectionner" : "Double-cliquer pour lier cet element")}">
            ${batchMode ? `<td><input type="checkbox" data-assignment-beneficiary-check value="${escapeHtml(String(row.id || ""))}"></td>` : ""}
            <td>${escapeHtml(noCodeRecordPrimaryLabel(assignments.beneficiaryService, row) || String(row.id || ""))}</td>
        </tr>
    `).join("") || `<tr><td class="muted" colspan="${batchMode ? "2" : "1"}">Aucun element trouve.</td></tr>`;
    return `
        <section class="modal-section">
            <h3>Ajouter ${escapeHtml(label.toLowerCase())}</h3>
            <p class="muted">${escapeHtml(batchMode ? "Cochez les elements a lier, puis validez la selection." : "Recherchez puis double-cliquez sur un element pour le lier a la fiche.")}</p>
            <div class="inventory-row-actions">
                <label class="field inline-field">
                    <span>Recherche</span>
                    <input id="relation-assignment-search" type="search" value="${escapeHtml(String(picker.query || ""))}">
                </label>
                ${allowsBatch ? createActionButtonMarkup({ preset: "secondary", type: "button", action: "assignment:beneficiary:batch-toggle", label: batchMode ? "Selection individuelle" : "Selection par lot" }) : ""}
                ${batchMode ? createActionButtonMarkup({ preset: "add", type: "button", action: "assignment:beneficiary:batch-add", label: "Lier la selection" }) : ""}
                ${createActionButtonMarkup({ preset: "back", type: "button", action: "assignment:beneficiary:back", label: "Retour" })}
            </div>
            <div class="table-scroll">
                <table class="device-table inventory-table">
                    <thead><tr>${batchMode ? "<th></th>" : ""}<th>${escapeHtml(label)}</th></tr></thead>
                    <tbody>${rowsMarkup}</tbody>
                </table>
            </div>
            <p id="modal-relation-assignment-picker-feedback" class="muted inventory-feedback"></p>
        </section>
    `;
}

async function openRecordAssignmentPicker(query = "") {
    const createContext = state.relationAssignmentCreate;
    const assignments = createContext?.assignments;
    if (!createContext?.ownerId || !assignments?.definition?.id) {
        throw new Error("La liaison d'attribution est indisponible.");
    }
    const normalizedQuery = String(query || "").trim().toLowerCase();
    const previousPicker = state.relationAssignmentPicker || {};
    let allRows = Array.isArray(previousPicker.allRows) ? previousPicker.allRows : null;
    if (!allRows) {
        const page = await fetchNoCodeServiceRecordsPage(assignments.beneficiaryCode, {
            search: "",
            activeOnly: true,
            limit: 500,
            offset: 0,
            sort: "label",
            direction: "asc",
        });
        allRows = Array.isArray(page?.items) ? page.items : [];
    }
    const linkedIds = new Set((assignments.beneficiaries || []).map((row) => String(row.id || "")));
    state.relationAssignmentPicker = {
        query: String(query || "").trim(),
        batchMode: Boolean(previousPicker.batchMode),
        allRows,
        rows: allRows.filter((row) => (
            !linkedIds.has(String(row?.id || ""))
            && (!normalizedQuery || noCodeRecordSearchText(assignments.beneficiaryService, row).includes(normalizedQuery))
        )),
    };
    openModal("Ajouter un element lie", buildRecordAssignmentPickerMarkup(), { width: "min(980px, calc(100vw - 40px))" });
}

function filterRecordAssignmentPickerRows(searchInput) {
    if (!(searchInput instanceof HTMLInputElement)) {
        return;
    }
    const query = String(searchInput.value || "").trim().toLowerCase();
    Array.from(appModalBody.querySelectorAll("[data-assignment-beneficiary-row]")).forEach((row) => {
        if (!(row instanceof HTMLElement)) {
            return;
        }
        if (action.startsWith("field:")) {
            selector.value = "";
            openNoCodeBatchFieldUpdateModal(action.slice("field:".length)).catch((error) => {
                const feedback = document.getElementById("modal-service-records-feedback");
                if (feedback) {
                    feedback.textContent = normalizeErrorMessage(error.message);
                }
            }).finally(() => {
                updateNoCodeServiceRecordsBatchActions(context || state.noCodeServiceRecordContext);
            });
            return;
        }
        row.hidden = Boolean(query) && !String(row.dataset.searchText || "").includes(query);
    });
}

async function linkRecordAssignmentBeneficiary(recordId) {
    const createContext = state.relationAssignmentCreate;
    const assignments = createContext?.assignments;
    const id = String(recordId || "").trim();
    if (!createContext?.ownerId || !assignments?.definition?.id || !id) {
        throw new Error("Element introuvable.");
    }
    await requestJson(
        `/admin/custom-services/${encodeURIComponent(assignments.ownerCode)}/records/${encodeURIComponent(createContext.ownerId)}/relations/${encodeURIComponent(assignments.definition.id)}/links`,
        { method: "POST", body: JSON.stringify({ linked_record_id: id }) },
    );
    const context = state.noCodeServiceRecordContext;
    const editor = state.noCodeRecordEditor;
    const refreshed = await buildRecordAssignment(context, editor);
    if (createContext.linkOnly) {
        state.relationAssignmentCreate = null;
        state.relationAssignmentPicker = null;
        if (editor) {
            editor.recordAssignment = null;
        }
        await reopenRecordAssignmentOwnerEditor(context, editor);
        return;
    }
    state.relationAssignmentCreate = {
        ...createContext,
        assignments: refreshed,
        selectedBeneficiaryId: id,
    };
    state.relationAssignmentPicker = null;
    openModal(`Ajouter ${noCodeRecordEditorEntityLabel(refreshed.resourceService).toLowerCase()}`, buildRecordAssignmentCreateMarkup(context), { width: "min(720px, calc(100vw - 40px))" });
}

async function linkRecordAssignmentBeneficiaries(recordIds) {
    const createContext = state.relationAssignmentCreate;
    const assignments = createContext?.assignments;
    const ids = Array.from(new Set((Array.isArray(recordIds) ? recordIds : [])
        .map((value) => String(value || "").trim())
        .filter(Boolean)));
    if (!createContext?.linkOnly || !createContext?.ownerId || !assignments?.definition?.id || !ids.length) {
        throw new Error("Selection invalide.");
    }
    await Promise.all(ids.map((id) => requestJson(
        `/admin/custom-services/${encodeURIComponent(assignments.ownerCode)}/records/${encodeURIComponent(createContext.ownerId)}/relations/${encodeURIComponent(assignments.definition.id)}/links`,
        { method: "POST", body: JSON.stringify({ linked_record_id: id }) },
    )));
    const context = state.noCodeServiceRecordContext;
    const editor = state.noCodeRecordEditor;
    state.relationAssignmentCreate = null;
    state.relationAssignmentPicker = null;
    if (editor) {
        editor.recordAssignment = null;
    }
    await reopenRecordAssignmentOwnerEditor(context, editor);
}

async function unlinkRecordAssignmentBeneficiary(beneficiaryId, resourceId = "") {
    const context = state.noCodeServiceRecordContext;
    const editor = state.noCodeRecordEditor;
    const assignments = context && editor ? await buildRecordAssignment(context, editor) : null;
    const beneficiary = String(beneficiaryId || "").trim();
    const resource = String(resourceId || "").trim();
    if (!assignments?.definition?.id || !assignments?.ownerCode || !assignments?.ownerId || !beneficiary) {
        throw new Error("Le lien a retirer est introuvable.");
    }
    await deleteNoCodeServiceRecordRelationLink(
        assignments.ownerCode,
        assignments.ownerId,
        Number(assignments.definition.id || 0),
        beneficiary,
    );
    if (resource && assignments.beneficiaryRelationId > 0) {
        await deleteNoCodeServiceRecordRelationLink(
            assignments.resourceCode,
            resource,
            assignments.beneficiaryRelationId,
            beneficiary,
        );
    }
    editor.recordAssignment = null;
    await reopenRecordAssignmentOwnerEditor(context, editor);
}

function noCodeRecordRemoteAccessUrl(service, values) {
    const config = service?.tile_config?.remote_access;
    if (!config || !config.enabled) return "";
    const value = String(values?.[String(config.field_key || "").trim()] || "").trim();
    if (!value) return "";
    const scheme = String(config.scheme || "url").toLowerCase();
    const rawUrl = scheme === "url" ? value : `${scheme}://${value.replace(/^https?:\/\//i, "")}`;
    try {
        const parsed = new URL(rawUrl);
        return ["http:", "https:"].includes(parsed.protocol) ? parsed.href : "";
    } catch (_error) {
        return "";
    }
}

function buildNoCodeRecordEditorMarkup() {
    const context = state.noCodeServiceRecordContext;
    const editor = state.noCodeRecordEditor;
    if (!context || !editor) {
        return "";
    }
    const service = context.service;
    const fields = noCodeCustomServiceFields(service);
    const credentialsEnabled = Boolean(service?.credentials_enabled);
    const isEmailService = String(service?.code || "").trim().toLowerCase() === "emails";
    const credentialLogin = String(editor?.credentials?.login || "");
    const credentialPassword = String(editor?.credentials?.password || "");
    const credentialPasswordMask = String(editor?.credentialPasswordMask || "").trim();
    const hasCredentialPassword = Boolean(editor?.hasCredentialPassword || credentialPasswordMask);
    const remoteAccessUrl = noCodeRecordRemoteAccessUrl(service, editor.values || {});
    const remoteAccessLabel = String(service?.tile_config?.remote_access?.label || "Ouvrir l'interface").trim() || "Ouvrir l'interface";
    const revealCredentialButton = createIconActionButtonMarkup({
        iconHtml: "&#128065;",
        iconClass: "reveal-password",
        title: hasCredentialPassword ? "Afficher le mot de passe stocke" : "Aucun mot de passe stocke",
        ariaLabel: hasCredentialPassword ? "Afficher le mot de passe stocke" : "Aucun mot de passe stocke",
        action: "service:record:credential-reveal",
        data: {
            service_code: String(service?.code || ""),
            record_id: String(editor?.recordId || ""),
        },
        disabled: !hasCredentialPassword || !String(editor?.recordId || "").trim(),
    });
    const fieldMarkup = fields.map((field) => {
        const fieldKey = String(field.field_key || "").trim();
        const label = String(field.label || fieldKey).trim() || fieldKey;
        const kind = normalizeNoCodeKind(field.field_kind || "text");
        const currentValue = String((editor.values || {})[fieldKey] || "");
        if (kind === "list") {
            const options = parseNoCodeOptions(field.options || "");
            const optionsMarkup = options.map((option) => {
                const selected = currentValue.toLowerCase() === option.toLowerCase();
                return `<option value="${escapeHtml(option)}" ${selected ? "selected" : ""}>${escapeHtml(option)}</option>`;
            }).join("");
            return `
                <label class="field">
                    <span>${escapeHtml(label)}${field.required ? " *" : ""}</span>
                    <select name="record_field_${escapeHtml(fieldKey)}">
                        <option value=""></option>
                        ${optionsMarkup}
                    </select>
                </label>
            `;
        }
        return `
            <label class="field">
                <span>${escapeHtml(label)}${field.required ? " *" : ""}</span>
                <input name="record_field_${escapeHtml(fieldKey)}" type="${escapeHtml(noCodeRecordInputType(kind))}" value="${escapeHtml(currentValue)}">
            </label>
        `;
    }).join("");
    const childEnabled = Boolean(service?.child_enabled);
    const children = Array.isArray(editor.children) ? editor.children : [];
    const childRows = children.map((row, index) => `
        <div class="no-code-child-row">
            <input type="text" name="record_child_name" placeholder="Nom" value="${escapeHtml(String(row?.name || ""))}">
            <input type="text" name="record_child_code" placeholder="Code" value="${escapeHtml(String(row?.code || ""))}">
            ${createIconActionButtonMarkup({
                icon: "delete",
                danger: true,
                action: "service:child:remove",
                title: "Supprimer",
                data: { child_index: index },
            })}
        </div>
    `).join("");
    const relationExperienceMarkup = buildNoCodeRecordRelationExperienceMarkup(context, editor);
    const recordAssignmentMarkup = buildRecordAssignmentMarkup(context, editor);
    const assignmentResourceCode = String(editor?.recordAssignment?.resourceCode || "").trim().toLowerCase();
    const recordRelations = editor.mode === "edit"
        ? noCodeRecordRelationsForContext(context).filter((relation) => (
            String(relation?.record_display_mode || "standard").toLowerCase() === "standard"
            && String(relation?.source_service_code || "").trim().toLowerCase() !== assignmentResourceCode
        ))
        : [];
    const relationsMarkup = recordRelations.length
        ? `
            <section class="modal-section">
                <h3>Relations</h3>
                <div class="inventory-row-actions no-code-record-relations-actions">
                    ${recordRelations.map((relation) => createActionButtonMarkup({
                        className: "toolbar-btn",
                        type: "button",
                        action: "service:record:relation-open",
                        label: noCodeRelationMenuLabel(context, relation),
                        data: {
                            relation_id: String(relation?.id || ""),
                            record_id: String(editor.recordId || ""),
                        },
                    })).join("")}
                </div>
            </section>
        `
        : "";
    return `
        <form id="modal-service-record-form" class="modal-form" data-record-id="${escapeHtml(String(editor.recordId || ""))}">
            <section class="modal-section">
                <h3>${escapeHtml(editor.mode === "edit" ? `Modifier — ${noCodeRecordEditorEntityLabel(service)}` : `Creer — ${noCodeRecordEditorEntityLabel(service)}`)}</h3>
                <div class="modal-settings-grid">
                    ${fieldMarkup}
                </div>
                ${remoteAccessUrl ? `<p><a class="toolbar-btn" href="${escapeHtml(remoteAccessUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(remoteAccessLabel)}</a></p>` : ""}
            </section>
            ${credentialsEnabled ? `
                <section class="modal-section">
                    <h3>${isEmailService ? "Mot de passe" : "Identifiants"}</h3>
                    <div class="modal-settings-grid">
                        ${isEmailService ? "" : `<label class="field">
                            <span>Login</span>
                            <input name="record_credential_login" type="text" value="${escapeHtml(credentialLogin)}" autocomplete="off">
                        </label>`}
                        <label class="field">
                            <span>Mot de passe</span>
                            <span class="password-reveal-field no-code-credential-password-field">
                                <input name="record_credential_password" type="password" value="${escapeHtml(credentialPassword)}" autocomplete="new-password" placeholder="${escapeHtml(credentialPasswordMask)}">
                                ${revealCredentialButton}
                            </span>
                            ${hasCredentialPassword ? `<span class="device-password-edit-status">Mot de passe stocke: ${escapeHtml(credentialPasswordMask)}</span>` : ""}
                        </label>
                    </div>
                </section>
            ` : ""}
            ${childEnabled ? `
                <section class="modal-section type-schema-fields-section">
                    <div class="type-schema-fields-head">
                        <h3>${escapeHtml(String(service?.child_label || "Elements lies"))}</h3>
                        ${createIconActionButtonMarkup({
                            icon: "add",
                            action: "service:child:add",
                            title: "Ajouter un element",
                        })}
                    </div>
                    <div id="no-code-child-list" class="no-code-child-list">
                        ${childRows || '<div class="muted">Aucun element lie.</div>'}
                    </div>
                </section>
            ` : ""}
            ${relationExperienceMarkup || relationsMarkup}
            ${recordAssignmentMarkup}
            <p id="modal-service-record-feedback" class="muted inventory-feedback"></p>
            ${createModalActionsMarkup({
                buttons: [
                    { preset: "back", action: "service:records:back" },
                    {
                        preset: editor.mode === "edit" ? "save" : "add",
                        label: editor.mode === "edit" ? "Enregistrer" : "Ajouter",
                    },
                ],
            })}
        </form>
    `;
}

function renderNoCodeRecordEditor() {
    if (!state.noCodeRecordEditor || !(appModalBody instanceof HTMLElement)) {
        return;
    }
    appModalBody.innerHTML = buildNoCodeRecordEditorMarkup();
}

async function openNoCodeServicesModal(options = {}) {
    setPortalServiceEditorFocusMode(false);
    await loadAdministrationData({
        includeModules: true,
        includeRoles: false,
        includeUsers: false,
        includeServices: true,
        includeSharedLists: true,
    });
    state.noCodeServiceEditor = null;
    state.noCodeServiceEditorContext = null;
    state.noCodeServiceRecordContext = null;
    state.noCodeRecordEditor = null;
    state.noCodeSharedListEditor = null;
    state.noCodeSharedListItemsContext = null;
    state.noCodeSharedListItemEditor = null;
    openModal("Administration - Ajout de service", buildNoCodeServicesModalMarkup(), noCodeInlineOptions("min(1120px, calc(100vw - 40px))", options));
    renderNoCodeServicesTreeView();
}

function modalBodyContains(selector) {
    return (
        appModal instanceof HTMLElement
        && !appModal.hidden
        && appModalBody instanceof HTMLElement
        && Boolean(appModalBody.querySelector(selector))
    );
}

function setNoCodeModalFeedback(feedbackId, message) {
    if (!message) {
        return;
    }
    const feedback = document.getElementById(feedbackId);
    if (feedback) {
        feedback.textContent = message;
    }
}

function captureNoCodeServiceEditorContext(options = {}) {
    if (options?.context && typeof options.context === "object") {
        return {
            source: String(options.context.source || "standalone").trim().toLowerCase() || "standalone",
            serviceCode: String(options.context.serviceCode || "").trim().toLowerCase(),
            inline: options.context.inline !== undefined ? Boolean(options.context.inline) : Boolean(state.noCodeInlineMode),
        };
    }
    const inline = Boolean(state.noCodeInlineMode);
    const recordContextCode = normalizeNoCodeText(state.noCodeServiceRecordContext?.service?.code).toLowerCase();
    if (recordContextCode && modalBodyContains("#service-records-body")) {
        return { source: "records", serviceCode: recordContextCode, inline };
    }
    if (modalBodyContains("#no-code-services-body")) {
        return { source: "services", serviceCode: "", inline };
    }
    return { source: "standalone", serviceCode: "", inline };
}

async function returnToNoCodeServiceEditorCaller(message = "") {
    const context = state.noCodeServiceEditorContext && typeof state.noCodeServiceEditorContext === "object"
        ? state.noCodeServiceEditorContext
        : { source: "services", serviceCode: "", inline: true };
    const source = String(context.source || "services").trim().toLowerCase() || "services";
    const serviceCode = String(context.serviceCode || "").trim().toLowerCase();
    const inline = context.inline !== undefined ? Boolean(context.inline) : true;

    state.noCodeServiceEditor = null;
    state.noCodeServiceEditorContext = null;

    if (source === "records" && serviceCode) {
        try {
            await openNoCodeServiceRecords(serviceCode, { inline, forceRefresh: true });
            setNoCodeModalFeedback("modal-service-records-feedback", message);
            return;
        } catch (_error) {
            await openNoCodeServicesModal({ inline });
            setNoCodeModalFeedback("modal-service-feedback", message);
            return;
        }
    }

    if (source === "services") {
        await openNoCodeServicesModal({ inline });
        setNoCodeModalFeedback("modal-service-feedback", message);
        return;
    }

    closeModal();
}

async function openNoCodeServiceEditor(service = null, options = {}) {
    setPortalServiceEditorFocusMode(true);
    state.noCodeSharedListEditor = null;
    state.noCodeSharedListItemsContext = null;
    state.noCodeSharedListItemEditor = null;
    state.noCodeServiceEditorContext = captureNoCodeServiceEditorContext(options);
    const editor = createNoCodeServiceEditor(service);
    if (service?.code) {
        try {
            const relations = await fetchNoCodeServiceRelations(service.code);
            const currentServiceCode = String(service.code || "").trim().toLowerCase();
            editor.relationDrafts = relations
                .map((relation, index) => {
                    const targetCode = normalizeNoCodeRelationEntityCode(relation?.target_service_code || relation?.service_code || "");
                    const sourceCode = String(relation?.source_service_code || service.code || "").trim().toLowerCase();
                    const isIncoming = sourceCode !== currentServiceCode && targetCode === currentServiceCode;
                    const displayTargetCode = isIncoming ? sourceCode : targetCode;
                    const label = String(relation?.display_label || relation?.label || findNoCodeRelationEntity(displayTargetCode)?.label || displayTargetCode).trim();
                    return {
                        ...relation,
                        client_id: `rel_${relation?.id || index}`,
                        source_service_code: sourceCode,
                        target_service_code: targetCode,
                        service_code: displayTargetCode,
                        label,
                        display_label: label,
                        is_incoming: isIncoming,
                        is_readonly_relation: isIncoming,
                        verb: String(relation?.verb || "est lie a").trim() || "est lie a",
                        cardinality: normalizeNoCodeRelationCardinality(relation?.cardinality || relation?.relation_type || "many_to_one"),
                        relation_type: normalizeNoCodeRelationCardinality(relation?.cardinality || relation?.relation_type || "many_to_one"),
                        direction: normalizeNoCodeRelationDirection(relation?.direction || "out"),
                        filter_candidates_by_shared_relation: Boolean(relation?.filter_candidates_by_shared_relation),
                        show_indirect_relations: Boolean(relation?.show_indirect_relations),
                        record_display_mode: ["standard", "hidden", "assignment"].includes(String(relation?.record_display_mode || "").trim().toLowerCase())
                            ? String(relation.record_display_mode).trim().toLowerCase()
                            : "standard",
                        assignment_resource_service_code: normalizeNoCodeRelationEntityCode(relation?.assignment_resource_service_code || ""),
                        unique_value_field_key: String(relation?.unique_value_field_key || "").trim().toLowerCase(),
                        x: Number.isFinite(Number(relation?.x ?? relation?.target_x)) ? Number(relation.x ?? relation.target_x) : 430,
                        y: Number.isFinite(Number(relation?.y ?? relation?.target_y)) ? Number(relation.y ?? relation.target_y) : 34 + (index * 152),
                    };
                });
            const first = editor.relationDrafts[0] || null;
            editor.selectedRelationId = first ? noCodeRelationId(first, 0) : "";
            editor.selectedRelationServiceCode = noCodeRelationIsReadonly(editor, first)
                ? String(first?.source_service_code || "").trim().toLowerCase()
                : normalizeNoCodeRelationEntityCode(first?.target_service_code || first?.service_code || "");
        } catch (error) {
            editor.relationLoadError = normalizeErrorMessage(error.message);
        }
    }
    state.noCodeServiceEditor = editor;
    openModal(
        service ? "Service - Edition" : "Service - Creation",
        buildNoCodeServiceEditorMarkup(),
        noCodeInlineOptions("min(1520px, calc(100vw - 24px))", options),
    );
    renderNoCodeServiceEditor();
}

async function fetchDirectoryRelationEntityRecordsPage(systemEntity, options = {}) {
    const limit = Math.max(1, Math.min(500, Number(options.limit || 50)));
    const endpoint = systemEntity.code === "utilisateurs" ? "/directory/agents" : "/directory/services";
    const search = normalizeNoCodeText(options.search || "").toLowerCase();
    const requestLimit = search ? 500 : limit;
    const payload = await requestJson(`${endpoint}?limit=${encodeURIComponent(String(requestLimit))}`);
    const isActiveAgent = (row) => {
        if (systemEntity.code !== "utilisateurs") {
            return true;
        }
        if (row?.is_active === false || row?.enabled === false || row?.account_enabled === false) {
            return false;
        }
        const status = normalizeNoCodeText(row?.status || row?.account_status || "").toLowerCase();
        return !["desactive", "désactivé", "desactivee", "désactivée", "inactive", "inactif", "disabled"].includes(status);
    };
    const rows = listFromMaybeArray(payload?.items).filter(isActiveAgent).map((row) => ({
        id: String(row?.id || ""),
        service_code: systemEntity.code,
        values: systemEntity.code === "utilisateurs"
            ? {
                display_name: String(row?.identity || row?.label || ""),
                login: String(row?.login || ""),
                mail: String(row?.mail || ""),
                service: String(row?.linked_services || row?.service || ""),
                distinguished_name: String(row?.distinguished_name || ""),
            }
            : {
                name: String(row?.label || row?.code || ""),
                code: String(row?.code || ""),
                description: String(row?.description || ""),
                manager: String(row?.manager || ""),
                distinguished_name: String(row?.distinguished_name || ""),
            },
        updated_at: String(row?.synced_at || ""),
    })).filter((row) => row.id);
    const filteredRows = search
        ? rows.filter((row) => Object.values(row?.values || {}).some((value) =>
            String(value || "").toLowerCase().includes(search),
        ))
        : rows;
    return {
        items: filteredRows,
        total: search ? filteredRows.length : Number(payload?.total || rows.length),
        limit: search ? filteredRows.length || limit : limit,
        offset: 0,
        source: "directory",
    };
}

async function fetchCustomServiceRecordsPage(serviceCode, options = {}) {
    const normalizedCode = normalizeNoCodeText(serviceCode).toLowerCase();
    const limit = Math.max(1, Math.min(500, Number(options.limit || 50)));
    const offset = Math.max(0, Number(options.offset || 0));
    const params = new URLSearchParams({
        search: String(options.search || ""),
        limit: String(limit),
        offset: String(offset),
        sort: String(options.sort || "label"),
        direction: String(options.direction || "asc"),
    });
    try {
        const page = await requestJson(`/admin/custom-services/${encodeURIComponent(normalizedCode)}/records/query?${params.toString()}`);
        if (page && Array.isArray(page.items)) {
            if (!page.items.length && Number(page.total || 0) > 0 && offset > 0) {
                return fetchNoCodeServiceRecordsPage(normalizedCode, {
                    ...options,
                    offset: 0,
                });
            }
            return {
                items: page.items,
                total: Number(page.total || 0),
                limit: Number(page.limit || limit),
                offset: Number(page.offset || offset),
                source: "query",
            };
        }
    } catch (_error) {
    }
    const records = await requestJson(`/admin/custom-services/${encodeURIComponent(normalizedCode)}/records`);
    const rows = Array.isArray(records) ? records : [];
    return {
        items: rows,
        total: rows.length,
        limit: rows.length || limit,
        offset: 0,
        source: "list",
    };
}

async function fetchNoCodeServiceRecordsPage(serviceCode, options = {}) {
    const normalizedCode = normalizeNoCodeText(serviceCode).toLowerCase();
    const systemEntity = findNoCodeRelationSystemEntity(normalizedCode);
    const page = systemEntity
        ? fetchDirectoryRelationEntityRecordsPage(systemEntity, options)
        : fetchCustomServiceRecordsPage(normalizedCode, options);
    const resolved = await page;
    if (!options.activeOnly) {
        return resolved;
    }
    const activeItems = (resolved?.items || []).filter((row) => {
        const values = row?.values && typeof row.values === "object" ? row.values : {};
        const statusEntry = Object.entries(values).find(([key]) => ["status", "statut", "etat", "state"].includes(normalizeNoCodeText(key).toLowerCase()));
        if (!statusEntry) return true;
        return ["actif", "active", "enabled"].includes(normalizeNoCodeText(statusEntry[1]).toLowerCase());
    });
    return { ...resolved, items: activeItems, total: activeItems.length, offset: 0 };
}

async function reloadNoCodeServiceRecordsPage(context, options = {}) {
    const activeContext = context || state.noCodeServiceRecordContext;
    const serviceCode = normalizeNoCodeText(activeContext?.service?.code).toLowerCase();
    if (!activeContext || !serviceCode) {
        return;
    }
    const currentPage = activeContext.recordsPage || {};
    const nextOffset = Math.max(0, Number(options.offset ?? currentPage.offset ?? 0));
    const nextLimit = Math.max(1, Math.min(500, Number(options.limit ?? currentPage.limit ?? 50)));
    const page = await fetchNoCodeServiceRecordsPage(serviceCode, {
        search: String(activeContext.searchQuery || ""),
        limit: nextLimit,
        offset: nextOffset,
        sort: "label",
        direction: "asc",
    });
    activeContext.records = Array.isArray(page.items) ? page.items : [];
    activeContext.recordsPage = {
        total: Number(page.total || 0),
        limit: Number(page.limit || nextLimit),
        offset: Number(page.offset || 0),
        source: String(page.source || "query"),
    };
    for (const column of linkedColumnsForContext(activeContext)) {
        await hydrateLinkedColumn(activeContext, column).catch(() => {});
    }
    reconcileNoCodeSelectedRecordKeys(activeContext);
    renderNoCodeServiceRecordsTable();
    renderNoCodeServiceRecordsPagination();
}

async function openLinkedNoCodeRecordFromSummary(serviceCode, recordId) {
    const normalizedCode = normalizeNoCodeText(serviceCode).toLowerCase();
    const normalizedRecordId = String(recordId || "").trim();
    if (!normalizedCode || !normalizedRecordId) {
        return;
    }
    pushModalBackSnapshot();
    let service = findNoCodeRelationEntity(normalizedCode);
    if (!service) {
        await loadAdministrationData({
            includeModules: false,
            includeRoles: false,
            includeUsers: false,
            includeServices: true,
            includeSharedLists: false,
        });
        service = findNoCodeRelationEntity(normalizedCode);
    }
    if (!service) {
        throw new Error("Module introuvable.");
    }
    const record = await fetchLinkedNoCodeRecord(normalizedCode, normalizedRecordId);
    if (!record) {
        throw new Error("Fiche introuvable.");
    }
    state.directoryRecordEditor = null;
    state.noCodeServiceRecordContext = createLinkedRecordViewContext(service, record);
    state.noCodeRecordEditor = null;
    state.noCodeRecordViewer = { record };
    renderLinkedNoCodeRecordViewModal();
}

async function openLinkedSystemDirectoryRecordEditor(systemCode, recordId) {
    const normalizedCode = normalizeNoCodeRelationEntityCode(systemCode);
    const normalizedRecordId = String(recordId || "").trim();
    const kind = normalizedCode === "services" ? "services" : "agents";
    if (!normalizedRecordId) {
        throw new Error("Fiche introuvable.");
    }
    state.directoryContext = await fetchDirectoryContext(kind, {
        selectedRecordKeys: [],
        statusFilter: kind === "agents" ? "Actif" : "",
    });
    const row = directoryRowById(normalizedRecordId);
    if (!row) {
        throw new Error("Fiche introuvable.");
    }
    await openDirectoryRecordEditor(normalizedRecordId, { pushBack: false, inline: false });
}

async function openLinkedRecordEditorFromViewer(recordId) {
    const normalizedRecordId = String(recordId || "").trim();
    const context = state.noCodeServiceRecordContext;
    const serviceCode = String(context?.service?.code || "").trim().toLowerCase();
    const rows = Array.isArray(context?.records) ? context.records : [];
    const row = findNoCodeRecordById(rows, normalizedRecordId) || state.noCodeRecordViewer?.record || null;
    if (!row || !serviceCode) {
        return;
    }
    pushModalBackSnapshot();
    if (findNoCodeRelationSystemEntity(serviceCode)) {
        state.noCodeRecordViewer = null;
        await openLinkedSystemDirectoryRecordEditor(serviceCode, normalizedRecordId);
        return;
    }
    context.relations = await fetchNoCodeServiceRelations(serviceCode).catch(() => []);
    state.noCodeRecordViewer = null;
    openNoCodeRecordEditor(row, { inline: false });
}

function scheduleNoCodeServiceRecordsPageReload(context, options = {}) {
    if (noCodeServiceRecordsReloadTimer) {
        window.clearTimeout(noCodeServiceRecordsReloadTimer);
    }
    noCodeServiceRecordsReloadTimer = window.setTimeout(() => {
        noCodeServiceRecordsReloadTimer = 0;
        reloadNoCodeServiceRecordsPage(context, options).catch((error) => {
            const feedback = document.getElementById("modal-service-records-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        });
    }, 250);
}

function createNoCodeServiceRecordContext(service, previousContext = null, options = {}) {
    const effectiveServiceCode = normalizeNoCodeText(service?.code || "").toLowerCase();
    const sameService = String(previousContext?.service?.code || "").trim().toLowerCase() === effectiveServiceCode;
    const previousPage = previousContext?.recordsPage && typeof previousContext.recordsPage === "object"
        ? previousContext.recordsPage
        : {};
    const recordsPage = options.recordsPage && typeof options.recordsPage === "object" ? options.recordsPage : null;
    const records = recordsPage
        ? (Array.isArray(recordsPage.items) ? recordsPage.items : [])
        : (Array.isArray(options.records) ? options.records : []);
    return {
        service,
        records,
        relations: Array.isArray(options.relations)
            ? options.relations
            : (sameService && Array.isArray(previousContext?.relations) ? previousContext.relations : []),
        recordsPage: {
            total: Number(recordsPage?.total || 0),
            limit: Number(recordsPage?.limit || previousPage.limit || 50),
            offset: Number(recordsPage?.offset || previousPage.offset || 0),
            source: String(recordsPage?.source || options.source || "query"),
        },
        importPreview: null,
        importFile: null,
        importSheetName: sameService ? String(previousContext?.importSheetName || "").trim() : "",
        importAvailableSheets: sameService && Array.isArray(previousContext?.importAvailableSheets)
            ? previousContext.importAvailableSheets.map((item) => String(item || ""))
            : [],
        importHeaderMode: sameService
            ? normalizeTabularHeaderMode(previousContext?.importHeaderMode)
            : "auto",
        importHeaderRowNumber: sameService
            ? normalizeTabularHeaderRowNumber(previousContext?.importHeaderRowNumber)
            : 1,
        quickFilters: sameService
            ? noCodeRecordQuickFilterValueMap(previousContext)
            : defaultNoCodeRecordQuickFilters(service),
        importCredentialMode: sameService
            ? normalizeRecordsImportCredentialMode(previousContext?.importCredentialMode)
            : "preserve_on_blank",
        importColumnPage: sameService ? Number(previousContext?.importColumnPage || 0) : 0,
        linkedColumns: sameService && Array.isArray(previousContext?.linkedColumns) ? previousContext.linkedColumns : [],
        _recordsTreeView: null,
        searchQuery: sameService ? String(previousContext?.searchQuery || "") : "",
        selectedRecordKeys: [],
        sort: normalizeNoCodeRecordSortState(
            service,
            sameService && previousContext?.sort
                ? { column: String(previousContext.sort.column || ""), direction: String(previousContext.sort.direction || "asc") }
                : null,
        ),
    };
}

async function openNoCodeServiceRecords(serviceCode, options = {}) {
    setPortalServiceEditorFocusMode(false);
    const normalizedCode = normalizeNoCodeText(serviceCode).toLowerCase();
    if (!normalizedCode) {
        throw new Error("Service introuvable.");
    }
    let service = findNoCodeService(normalizedCode);
    if (Boolean(options.forceRefresh) || !service) {
        if (Boolean(options.forceRefresh)) {
            invalidateAdminData(["services"]);
        }
        await loadAdministrationData({
            includeModules: false,
            includeRoles: false,
            includeUsers: false,
            includeServices: true,
            includeSharedLists: false,
        });
        service = findNoCodeService(normalizedCode);
    }
    if (!service) {
        throw new Error("Service introuvable.");
    }
    const effectiveServiceCode = normalizeNoCodeText(service?.code || normalizedCode).toLowerCase();
    const previousContext = state.noCodeServiceRecordContext;
    const sameService = String(previousContext?.service?.code || "").trim().toLowerCase() === effectiveServiceCode;
    const searchQuery = sameService ? String(previousContext?.searchQuery || "") : "";
    const previousPage = previousContext?.recordsPage && typeof previousContext.recordsPage === "object"
        ? previousContext.recordsPage
        : {};
    state.noCodeServiceRecordContext = createNoCodeServiceRecordContext(service, previousContext, {
        recordsPage: {
            items: [],
            total: 0,
            limit: Number(previousPage.limit || 50),
            offset: Number(previousPage.offset || 0),
            source: "loading",
        },
        relations: sameService && Array.isArray(previousContext?.relations) ? previousContext.relations : [],
        source: "loading",
    });
    state.noCodeRecordEditor = null;
    state.noCodeRecordViewer = null;
    renderNoCodeServiceRecordsModal(options);
    let recordsPage;
    let serviceRelations = [];
    try {
        [recordsPage, serviceRelations] = await Promise.all([
            fetchNoCodeServiceRecordsPage(effectiveServiceCode, {
                search: searchQuery,
                limit: Number(previousPage.limit || 50),
                offset: Number(previousPage.offset || 0),
                sort: "label",
                direction: "asc",
            }),
            fetchNoCodeServiceRelations(effectiveServiceCode).catch(() => []),
        ]);
    } catch (error) {
        throw error;
    }
    state.noCodeServiceRecordContext = createNoCodeServiceRecordContext(service, previousContext, {
        recordsPage,
        relations: serviceRelations,
    });
    for (const column of linkedColumnsForContext(state.noCodeServiceRecordContext)) {
        await hydrateLinkedColumn(state.noCodeServiceRecordContext, column).catch(() => {});
    }
    state.noCodeRecordEditor = null;
    state.noCodeRecordViewer = null;
    renderNoCodeServiceRecordsModal(options);
}

function renderNoCodeServiceRecordsModal(options = {}) {
    const context = state.noCodeServiceRecordContext;
    if (!context?.service) {
        return;
    }
    const service = context.service;
    openModal(
        `Vue detaillee - ${service.label || service.code}`,
        buildNoCodeRecordsModalMarkup(context),
        noCodeInlineOptions("min(1180px, calc(100vw - 40px))", options),
    );
    bindNoCodeServiceRecordsInteractions();
    renderNoCodeServiceRecordsTable();
}

function noCodeRecordValueByKeys(record, keys = []) {
    const values = record?.values && typeof record.values === "object" ? record.values : {};
    const normalizedKeys = (Array.isArray(keys) ? keys : [])
        .map((key) => String(key || "").trim().toLowerCase())
        .filter(Boolean);
    for (const [key, value] of Object.entries(values)) {
        if (normalizedKeys.includes(String(key || "").trim().toLowerCase())) {
            const text = String(value || "").trim();
            if (text) {
                return text;
            }
        }
    }
    return "";
}

function noCodeRecordViewField(label, value) {
    return {
        label: String(label || "Champ").trim() || "Champ",
        value: String(value || "").trim(),
    };
}

function noCodeRecordViewFieldRows(service, record) {
    const serviceCode = String(service?.code || "").trim().toLowerCase();
    if (serviceCode === "emails") {
        return [
            noCodeRecordViewField(
                "Mail",
                noCodeRecordValueByKeys(record, ["address", "adresse", "email", "mail"])
                    || noCodeRecordPrimaryLabel(service, record),
            ),
            noCodeRecordViewField("Alias", noCodeRecordValueByKeys(record, ["alias", "aliases", "alias_mail", "alias_email"])),
        ];
    }
    if (serviceCode === "utilisateurs") {
        return [
            noCodeRecordViewField("Identite", noCodeRecordValueByKeys(record, ["display_name", "identity", "label", "name"]) || noCodeRecordPrimaryLabel(service, record)),
            noCodeRecordViewField("Identifiant", noCodeRecordValueByKeys(record, ["login", "samaccountname", "username"])),
            noCodeRecordViewField("Mail", noCodeRecordValueByKeys(record, ["mail", "email", "address"])),
            noCodeRecordViewField("Service", noCodeRecordValueByKeys(record, ["service", "linked_services", "ad_services"])),
        ];
    }
    if (serviceCode === "services") {
        return [
            noCodeRecordViewField("Service", noCodeRecordValueByKeys(record, ["name", "label", "code"]) || noCodeRecordPrimaryLabel(service, record)),
            noCodeRecordViewField("Code", noCodeRecordValueByKeys(record, ["code"])),
            noCodeRecordViewField("Description", noCodeRecordValueByKeys(record, ["description"])),
            noCodeRecordViewField("Responsable", noCodeRecordValueByKeys(record, ["manager", "responsable"])),
        ];
    }
    return noCodeCustomServiceFields(service)
        .map((field) => {
            const fieldKey = String(field?.field_key || "").trim();
            return noCodeRecordViewField(field?.label || fieldKey, record?.values?.[fieldKey]);
        })
        .filter((row) => row.label);
}

function noCodeRecordViewEditLabel(service, record) {
    const serviceCode = String(service?.code || "").trim().toLowerCase();
    if (serviceCode === "emails") {
        return "Modifier mail";
    }
    const recordLabel = noCodeRecordPrimaryLabel(service, record);
    if (recordLabel) {
        return `Modifier ${recordLabel}`;
    }
    const serviceLabel = String(service?.label || service?.code || "fiche").trim().toLowerCase();
    return `Modifier ${serviceLabel}`;
}

function noCodeRecordViewCredentialRows(service, record) {
    if (!Boolean(service?.credentials_enabled)) {
        return "";
    }
    const serviceCode = String(service?.code || "").trim().toLowerCase();
    const recordId = String(record?.id || record?.record_id || "").trim();
    const login = noCodeCredentialValueFromMap(record?.values || {}, "login");
    const revealedPassword = revealedNoCodeRecordPassword(serviceCode, recordId);
    const passwordMask = revealedPassword || noCodeRecordCredentialPasswordMask(record);
    const hasPassword = Boolean(revealedPassword || noCodeRecordHasStoredCredentialPassword(record));
    const revealButton = createIconActionButtonMarkup({
        iconHtml: "&#128065;",
        iconClass: "reveal-password",
        title: hasPassword ? "Afficher le mot de passe stocke" : "Aucun mot de passe stocke",
        ariaLabel: hasPassword ? "Afficher le mot de passe stocke" : "Aucun mot de passe stocke",
        action: "service:record:view-credential-reveal",
        data: {
            service_code: serviceCode,
            record_id: recordId,
        },
        disabled: !hasPassword || !recordId,
    });
    return `
        ${serviceCode === "emails" ? "" : `
            <dt>Login</dt>
            <dd>${escapeHtml(login || "-")}</dd>
        `}
        <dt>Mot de passe</dt>
        <dd>
            <span class="linked-record-password">
                <span class="inventory-password-mask ${revealedPassword ? "is-clear" : ""}">${escapeHtml(passwordMask || "-")}</span>
                ${revealButton}
            </span>
        </dd>
    `;
}

function buildLinkedNoCodeRecordViewMarkup() {
    const context = state.noCodeServiceRecordContext;
    const viewer = state.noCodeRecordViewer;
    const service = context?.service || null;
    const record = viewer?.record || null;
    if (!service || !record) {
        return '<p class="muted">Fiche introuvable.</p>';
    }
    const serviceCode = String(service?.code || "").trim().toLowerCase();
    const recordId = String(record?.id || record?.record_id || "").trim();
    const isEmailService = serviceCode === "emails";
    const fieldRows = noCodeRecordViewFieldRows(service, record);
    const credentialRows = noCodeRecordViewCredentialRows(service, record);
    return `
        <section class="modal-section linked-record-view">
            <h3>${escapeHtml(isEmailService ? "Compte mail" : noCodeRecordPrimaryLabel(service, record))}</h3>
            <dl class="detail-list linked-record-detail-list">
                ${fieldRows.length
                    ? fieldRows.map((row) => `
                        <dt>${escapeHtml(row.label)}</dt>
                        <dd>${escapeHtml(row.value || "-")}</dd>
                    `).join("")
                    : `
                        <dt>Element</dt>
                        <dd>${escapeHtml(noCodeRecordPrimaryLabel(service, record) || "-")}</dd>
                    `}
                ${credentialRows}
            </dl>
            <p id="modal-service-record-feedback" class="muted inventory-feedback"></p>
            ${createModalActionsMarkup({
                buttons: [
                    { className: "toolbar-btn", type: "button", action: "modal:close", label: "Fermer" },
                    {
                        className: "primary-btn",
                        type: "button",
                        action: "service:record:view-edit",
                        label: noCodeRecordViewEditLabel(service, record),
                        data: {
                            record_id: recordId,
                        },
                    },
                ],
            })}
        </section>
    `;
}

function renderLinkedNoCodeRecordViewModal() {
    const context = state.noCodeServiceRecordContext;
    const record = state.noCodeRecordViewer?.record || null;
    const service = context?.service || null;
    const title = String(service?.code || "").trim().toLowerCase() === "emails"
        ? "Consultation mail"
        : `Consultation - ${noCodeRecordPrimaryLabel(service, record)}`;
    openModal(
        title,
        buildLinkedNoCodeRecordViewMarkup(),
        noCodeInlineOptions("min(720px, calc(100vw - 40px))", { inline: false }),
    );
}

function setServiceRecordsImportProgress(value, label, visible = true) {
    const wrap = document.getElementById("service-records-import-progress-wrap");
    const bar = document.getElementById("service-records-import-progress");
    const status = document.getElementById("service-records-import-progress-status");
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

async function refreshNoCodeServiceFieldImportPreviewFromSheet(
    sheetName = "",
    headerMode = "auto",
    headerRowNumber = 1,
    importUntilRowNumber = null,
) {
    const editor = state.noCodeServiceEditor;
    const importFile = editor?.importFile || null;
    if (!editor || !importFile) {
        throw new Error("Aucun fichier d'import en attente.");
    }
    const normalizedHeaderMode = normalizeTabularHeaderMode(headerMode);
    const normalizedHeaderRow = normalizeTabularHeaderRowNumber(headerRowNumber);
    const normalizedUntilRow = normalizeTabularUntilRowNumber(
        importUntilRowNumber === null ? editor.importUntilRowNumber : importUntilRowNumber,
    );
    const columnMappings = normalizeServiceFieldImportMappings(editor.importColumnMappings);
    const imported = await importServiceFieldsFromFile(
        importFile,
        sheetName,
        normalizedHeaderMode,
        normalizedHeaderRow,
        columnMappings,
        normalizedUntilRow,
    );
    editor.importPreview = {
        filename: String(importFile?.name || ""),
        fields: imported.fields,
        detectedRows: imported.detectedRows,
        detectedColumns: imported.detectedColumns,
        sourceHeaders: Array.isArray(imported.sourceHeaders) ? imported.sourceHeaders : [],
        sourceRowsPreview: Array.isArray(imported.sourceRowsPreview) ? imported.sourceRowsPreview : [],
        availableSheets: Array.isArray(imported.availableSheets) ? imported.availableSheets : [],
        selectedSheetName: String(imported.selectedSheetName || sheetName || "").trim(),
        detectedHeaderRowNumber: Number(imported.detectedHeaderRowNumber || normalizedHeaderRow || 1),
        effectiveHeaderMode: normalizeTabularHeaderMode(imported.effectiveHeaderMode || normalizedHeaderMode),
        effectiveMapping: Array.isArray(imported.effectiveMapping) ? imported.effectiveMapping : [],
    };
    editor.importHeaderMode = normalizeTabularHeaderMode(imported.effectiveHeaderMode || normalizedHeaderMode);
    editor.importHeaderRowNumber = normalizeTabularHeaderRowNumber(imported.detectedHeaderRowNumber || normalizedHeaderRow || 1);
    editor.importUntilRowNumber = normalizedUntilRow;
    editor.importColumnMappings = columnMappings.length
        ? columnMappings
        : normalizeServiceFieldImportMappings(imported.effectiveMapping);
    renderNoCodeServiceEditor();
}

async function refreshNoCodeServiceRecordsImportPreviewFromSheet(sheetName = "", headerMode = "auto", headerRowNumber = 1) {
    const context = state.noCodeServiceRecordContext;
    const serviceCode = String(context?.service?.code || "").trim().toLowerCase();
    const importFile = context?.importFile || null;
    if (!context || !serviceCode || !importFile) {
        throw new Error("Aucun fichier d'import en attente.");
    }
    const normalizedHeaderMode = normalizeTabularHeaderMode(headerMode);
    const normalizedHeaderRow = normalizeTabularHeaderRowNumber(headerRowNumber);
    const credentialMode = normalizeRecordsImportCredentialMode(context?.importCredentialMode);
    const columnMappings = normalizeServiceRecordImportMappings(context?.importColumnMappings);
    const preview = await previewServiceRecordsFromFile(
        importFile,
        serviceCode,
        credentialMode,
        sheetName,
        normalizedHeaderMode,
        normalizedHeaderRow,
        columnMappings,
    );
    context.importPreview = {
        ...preview,
        filename: String(importFile?.name || ""),
    };
    context.importSheetName = String(preview.selectedSheetName || sheetName || "").trim();
    context.importAvailableSheets = Array.isArray(preview.availableSheets)
        ? preview.availableSheets.map((item) => String(item || ""))
        : [];
    context.importHeaderMode = normalizeTabularHeaderMode(preview.effectiveHeaderMode || normalizedHeaderMode);
    context.importHeaderRowNumber = normalizeTabularHeaderRowNumber(preview.detectedHeaderRowNumber || normalizedHeaderRow || 1);
    context.importColumnMappings = columnMappings.length
        ? columnMappings
        : (
            buildServiceRecordImportMappingsFromEffectiveMapping(preview.effectiveMapping).length
                ? buildServiceRecordImportMappingsFromEffectiveMapping(preview.effectiveMapping)
                : buildDefaultServiceRecordImportMappings(context.service, preview.sourceHeaders)
        );
    renderNoCodeServiceRecordsModal();
}

function openNoCodeRecordEditor(record = null, options = {}) {
    const context = state.noCodeServiceRecordContext;
    if (!context || !context.service) {
        return;
    }
    state.directoryRecordEditor = null;
    const service = context.service;
    const fields = noCodeCustomServiceFields(service);
    const values = {};
    for (const field of fields) {
        const key = String(field.field_key || "").trim();
        values[key] = record
            ? String(record?.values?.[key] || "")
            : String(field?.default_value || "");
    }
    state.noCodeRecordEditor = {
        mode: record ? "edit" : "create",
        recordId: String(record?.id || ""),
        versionToken: String(record?.version_token || ""),
        values,
        credentials: {
            login: noCodeCredentialValueFromMap(record?.values || {}, "login"),
            password: record
                ? revealedNoCodeRecordPassword(service?.code || "", record?.id || "")
                : "",
        },
        hasCredentialPassword: record ? noCodeRecordHasStoredCredentialPassword(record) : false,
        credentialPasswordMask: record ? noCodeRecordCredentialPasswordMask(record) : "",
        children: Array.isArray(record?.children)
            ? record.children.map((row) => ({ name: String(row?.name || ""), code: String(row?.code || "") }))
            : [],
        recordAssignment: null,
        openRelationEditorIds: [],
    };
    openModal(
        noCodeRecordEditorModalTitle(service, record ? "edit" : "create"),
        buildNoCodeRecordEditorMarkup(),
        noCodeInlineOptions("min(980px, calc(100vw - 40px))", options),
    );
    window.setTimeout(() => {
        loadNoCodeRecordRelationExperience().catch((error) => {
            const feedback = document.getElementById("modal-service-record-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        });
    }, 0);
}

async function revealNoCodeRecordCredentialPassword({ serviceCode = "", recordId = "" } = {}) {
    const normalizedServiceCode = normalizeNoCodeText(serviceCode).toLowerCase();
    const normalizedRecordId = String(recordId || "").trim();
    const feedback = document.getElementById("modal-service-record-feedback");
    if (!normalizedServiceCode || !normalizedRecordId) {
        if (feedback) {
            feedback.textContent = "Fiche introuvable.";
        }
        return null;
    }
    let sessionPassword = isCredentialRevealSessionUnlocked() ? String(state.credentialRevealSessionPassword || "") : "";
    if (!sessionPassword) {
        const prompted = await promptCredentialRevealSessionPassword();
        if (prompted === null) {
            if (feedback) {
                feedback.textContent = "Affichage du mot de passe annule.";
            }
            return null;
        }
        sessionPassword = String(prompted || "");
    }
    if (!sessionPassword) {
        if (feedback) {
            feedback.textContent = "Mot de passe de session requis.";
        }
        return null;
    }
    if (feedback) {
        feedback.textContent = "Verification en cours...";
    }
    try {
        const payload = await requestJson(
            `/admin/custom-services/${encodeURIComponent(normalizedServiceCode)}/records/${encodeURIComponent(normalizedRecordId)}/credentials/reveal`,
            {
                method: "POST",
                body: JSON.stringify({ session_password: sessionPassword }),
            },
        );
        applyCredentialRevealSessionPassword(sessionPassword);
        const password = String(payload?.device_password || "");
        state.revealedNoCodeRecordPasswords[noCodeRecordCredentialKey(normalizedServiceCode, normalizedRecordId)] = password;
        if (state.noCodeRecordEditor && String(state.noCodeRecordEditor.recordId || "") === normalizedRecordId) {
            state.noCodeRecordEditor.credentials = {
                ...(state.noCodeRecordEditor.credentials || {}),
                password,
            };
            renderNoCodeRecordEditor();
        }
        const refreshedFeedback = document.getElementById("modal-service-record-feedback") || feedback;
        if (refreshedFeedback) {
            refreshedFeedback.textContent = "Mot de passe affiche.";
        }
        return payload;
    } catch (error) {
        const message = normalizeErrorMessage(error.message);
        if (message.toLowerCase().includes("mot de passe de session invalide")) {
            clearCredentialRevealState();
            await showItopsAlert({
                title: "Authentification refusee",
                message: "Le mot de passe de session ITOPS est incorrect. Le mot de passe enregistre n'a pas ete affiche.",
                confirmLabel: "Reessayer",
            });
        }
        if (feedback) {
            feedback.textContent = message;
        }
        return null;
    }
}

function updateNoCodeRecordChildRows() {
    const editor = state.noCodeRecordEditor;
    const context = state.noCodeServiceRecordContext;
    const listNode = document.getElementById("no-code-child-list");
    if (!(listNode instanceof HTMLElement) || !editor || !context) {
        return;
    }
    const rows = Array.isArray(editor.children) ? editor.children : [];
    listNode.innerHTML = rows.length
        ? rows.map((row, index) => `
            <div class="no-code-child-row">
                <input type="text" name="record_child_name" placeholder="Nom" value="${escapeHtml(String(row?.name || ""))}">
                <input type="text" name="record_child_code" placeholder="Code" value="${escapeHtml(String(row?.code || ""))}">
                ${createIconActionButtonMarkup({
                    icon: "delete",
                    danger: true,
                    action: "service:child:remove",
                    title: "Supprimer",
                    data: { child_index: index },
                })}
            </div>
        `).join("")
        : `<div class="muted">Aucun element lie.</div>`;
}

function syncNoCodeRecordChildrenFromDom() {
    const editor = state.noCodeRecordEditor;
    if (!editor) {
        return;
    }
    const listNode = document.getElementById("no-code-child-list");
    if (!(listNode instanceof HTMLElement)) {
        return;
    }
    const rows = Array.from(listNode.querySelectorAll(".no-code-child-row"));
    editor.children = rows.map((row) => {
        const nameInput = row.querySelector('input[name="record_child_name"]');
        const codeInput = row.querySelector('input[name="record_child_code"]');
        return {
            name: nameInput instanceof HTMLInputElement ? String(nameInput.value || "") : "",
            code: codeInput instanceof HTMLInputElement ? String(codeInput.value || "") : "",
        };
    });
}

function readNoCodeRecordRelationSelectionsFromDom() {
    const selections = {};
    Array.from(document.querySelectorAll("[data-record-relation-select]")).forEach((select) => {
        if (!(select instanceof HTMLSelectElement)) {
            return;
        }
        const relationId = String(select.dataset.relationId || "").trim();
        if (!relationId) {
            return;
        }
        selections[relationId] = select.multiple
            ? Array.from(select.selectedOptions).map((option) => String(option.value || "").trim()).filter(Boolean)
            : [String(select.value || "").trim()].filter(Boolean);
    });
    return selections;
}

function validateRecordRelationSelectionLimits(feedback = null) {
    for (const select of Array.from(document.querySelectorAll("[data-record-relation-select][data-max-selected]"))) {
        if (!(select instanceof HTMLSelectElement)) {
            continue;
        }
        const maxSelected = Number(select.dataset.maxSelected || 0);
        if (maxSelected <= 0) {
            continue;
        }
        const selectedCount = Array.from(select.selectedOptions).filter((option) => String(option.value || "").trim()).length;
        if (selectedCount > maxSelected) {
            if (feedback instanceof HTMLElement) {
                feedback.textContent = `Selection limitee a ${maxSelected} element(s) pour cette relation.`;
            }
            return false;
        }
    }
    return true;
}

function validateRequiredRecordRelationSelections(context, editor, selections, feedback = null) {
    if (editor?.mode === "edit") {
        return true;
    }
    const currentServiceCode = String(context?.service?.code || "").trim().toLowerCase();
    const missingRelation = noCodeRecordEditableRelationsForContext(context).find((relation) => {
        if (
            String(relation?.source_service_code || "").trim().toLowerCase() !== currentServiceCode
            || !Boolean(relation?.required)
        ) {
            return false;
        }
        const selected = selections?.[String(relation?.id || "")] || [];
        return !Array.isArray(selected) || selected.length <= 0;
    });
    if (!missingRelation) {
        return true;
    }
    if (feedback instanceof HTMLElement) {
        const label = String(missingRelation?.display_label || missingRelation?.target_service_code || "element lie").trim();
        feedback.textContent = `La relation obligatoire « ${label} » doit etre renseignee.`;
    }
    return false;
}

async function syncNoCodeRecordRelationSelections({ serviceCode, recordId, selections, editor, context = null }) {
    const code = String(serviceCode || "").trim().toLowerCase();
    const rid = String(recordId || "").trim();
    if (!code || !rid || !selections || typeof selections !== "object") {
        return { created: 0, deleted: 0 };
    }
    const relationContext = context && typeof context === "object" ? context : state.noCodeServiceRecordContext;
    const totals = { created: 0, deleted: 0 };
    for (const [relationId, selectedValues] of Object.entries(selections)) {
        const relId = Number(relationId || 0);
        if (relId <= 0) {
            continue;
        }
        const relation = noCodeRecordRelationsForContext(relationContext)
            .find((item) => Number(item?.id || 0) === relId) || null;
        const protectedIds = protectedRelationLinkedRecordIds(relationContext, relation);
        const selected = new Set((Array.isArray(selectedValues) ? selectedValues : []).map((value) => String(value || "").trim()).filter(Boolean));
        const stateForRelation = noCodeRecordRelationState(editor, relationId);
        const existingLinks = Array.isArray(stateForRelation.links) ? stateForRelation.links : await fetchNoCodeServiceRecordRelationLinks(code, rid, relId);
        const existing = new Set(existingLinks.map((link) => String(link?.linked_record?.id || "").trim()).filter(Boolean));
        for (const linkedId of existing) {
            if (protectedIds.has(linkedId)) {
                continue;
            }
            if (!selected.has(linkedId)) {
                await deleteNoCodeServiceRecordRelationLink(code, rid, relId, linkedId);
                totals.deleted += 1;
            }
        }
        for (const linkedId of selected) {
            if (!existing.has(linkedId)) {
                await createNoCodeServiceRecordRelationLink(code, rid, relId, linkedId);
                totals.created += 1;
            }
        }
    }
    return totals;
}

function noCodeTrackedRecordChanges(service, recordId, nextValues) {
    const fields = noCodeCustomServiceFields(service).filter((field) => Boolean(field?.track_history));
    if (!fields.length || !recordId) {
        return [];
    }
    const records = Array.isArray(state.noCodeServiceRecordContext?.records) ? state.noCodeServiceRecordContext.records : [];
    const existing = records.find((row) => String(row?.id || "") === String(recordId || "")) || null;
    const oldValues = existing?.values && typeof existing.values === "object" ? existing.values : {};
    const source = nextValues && typeof nextValues === "object" ? nextValues : {};
    return fields
        .map((field) => {
            const key = String(field?.field_key || "").trim();
            if (!key) {
                return null;
            }
            const oldValue = String(oldValues?.[key] || "");
            const newValue = String(source?.[key] || "");
            if (oldValue === newValue) {
                return null;
            }
            return {
                key,
                label: String(field?.label || key).trim(),
                oldValue,
                newValue,
            };
        })
        .filter(Boolean);
}

async function confirmNoCodeTrackedRecordChanges(changes) {
    const rows = (Array.isArray(changes) ? changes : []).slice(0, 8);
    if (!rows.length) {
        return { decision: "none", changedAt: "" };
    }
    const suffix = changes.length > rows.length ? `\n... +${changes.length - rows.length} autre(s) champ(s)` : "";
    const details = rows.map((row) => `${row.label}: "${row.oldValue || "(vide)"}" -> "${row.newValue || "(vide)"}"`);
    if (suffix) {
        details.push(suffix.trim());
    }
    return new Promise((resolve) => {
        const dialog = document.createElement("div");
        dialog.className = "itops-confirm-overlay";
        dialog.innerHTML = `
            <div class="app-modal-panel itops-confirm-panel" role="dialog" aria-modal="true" aria-labelledby="no-code-history-confirm-title">
                <div class="app-modal-head">
                    <h2 id="no-code-history-confirm-title">Historiser le changement</h2>
                    <button class="app-modal-close" type="button" data-history-decision="cancel" aria-label="Fermer">x</button>
                </div>
                <div class="app-modal-body itops-confirm-body">
                    <p class="muted">Ce champ est configure avec un historique. Choisissez comment enregistrer ce changement.</p>
                    <div class="itops-confirm-details">
                        ${details.map((item) => `<div>${escapeHtml(item)}</div>`).join("")}
                    </div>
                    <label class="check-field itops-dialog-check">
                        <input type="checkbox" data-history-advanced>
                        <span>Parametre avance</span>
                    </label>
                    <div class="modal-settings-grid" data-history-advanced-panel hidden>
                        <label class="field">
                            <span>Date du changement</span>
                            <input type="datetime-local" data-history-changed-at value="${escapeHtml(formatNoCodeDateTimeLocalValue())}">
                        </label>
                    </div>
                    <div class="modal-actions">
                        ${createActionButtonMarkup({
                            className: "toolbar-btn",
                            type: "button",
                            label: "Annuler",
                            attrs: { "data-history-decision": "cancel" },
                        })}
                        ${createActionButtonMarkup({
                            className: "toolbar-btn",
                            type: "button",
                            label: "Changer uniquement",
                            attrs: { "data-history-decision": "skip", "data-history-advanced-action": "1" },
                        })}
                        ${createActionButtonMarkup({
                            className: "primary-btn",
                            type: "button",
                            label: "Valider",
                            attrs: { "data-history-decision": "history" },
                        })}
                    </div>
                </div>
            </div>
        `;
        const cleanup = (decision) => {
            const changedAtInput = dialog.querySelector("[data-history-changed-at]");
            const advancedInput = dialog.querySelector("[data-history-advanced]");
            const changedAt = advancedInput instanceof HTMLInputElement
                && advancedInput.checked
                && changedAtInput instanceof HTMLInputElement
                ? String(changedAtInput.value || "").trim()
                : "";
            dialog.remove();
            resolve({ decision, changedAt: decision === "history" ? changedAt : "" });
        };
        const syncAdvanced = () => {
            const advancedInput = dialog.querySelector("[data-history-advanced]");
            const enabled = advancedInput instanceof HTMLInputElement && advancedInput.checked;
            const panel = dialog.querySelector("[data-history-advanced-panel]");
            if (panel instanceof HTMLElement) {
                panel.hidden = !enabled;
            }
            Array.from(dialog.querySelectorAll("[data-history-advanced-action]")).forEach((button) => {
                if (button instanceof HTMLElement) {
                    button.hidden = !enabled;
                }
            });
        };
        dialog.addEventListener("change", (event) => {
            const target = event.target;
            if (target instanceof HTMLInputElement && target.matches("[data-history-advanced]")) {
                syncAdvanced();
            }
        });
        dialog.addEventListener("click", (event) => {
            const target = event.target;
            if (!(target instanceof Element)) {
                return;
            }
            const button = target.closest("[data-history-decision]");
            if (!(button instanceof HTMLElement)) {
                return;
            }
            cleanup(String(button.getAttribute("data-history-decision") || "cancel"));
        });
        document.body.appendChild(dialog);
        syncAdvanced();
        const primary = dialog.querySelector(".primary-btn");
        if (primary instanceof HTMLElement) {
            primary.focus();
        }
    });
}

async function closeModalWithContextBack() {
    if (state.linkedColumnsPicker) {
        state.linkedColumnsPicker = null;
    }
    if (await restoreNextModalBackSnapshot()) {
        return;
    }
    if (state.noCodeSharedListItemEditor && state.noCodeSharedListItemsContext?.list?.code) {
        state.noCodeSharedListItemEditor = null;
        await openSharedListItemsModal(String(state.noCodeSharedListItemsContext.list.code || ""));
        return;
    }
    if (state.noCodeSharedListEditor) {
        await openSharedListsModal();
        return;
    }
    if (state.noCodeSharedListItemsContext) {
        await openSharedListsModal();
        return;
    }
    if (state.directoryRecordEditor && state.directoryContext) {
        const kind = String(state.directoryContext.kind || state.directoryRecordEditor.kind || "agents").trim().toLowerCase();
        if (consumeModalDirectoryDirty()) {
            await refreshDirectoryContextRows(kind).catch(() => null);
        }
        const rows = Array.isArray(state.directoryContext.rows) ? state.directoryContext.rows : [];
        state.directoryRecordEditor = null;
        state.noCodeRecordEditor = null;
        state.noCodeServiceRecordContext = null;
        directoryTreeView = null;
        openModal(
            kind === "services" ? "Services" : "Agents",
            buildDirectoryModuleMarkup(kind === "services" ? "services" : "agents", rows),
            noCodeInlineOptions("min(1180px, calc(100vw - 40px))", { inline: true }),
        );
        renderDirectoryTreeView();
        return;
    }
    if (state.noCodeRecordEditor && state.noCodeServiceRecordContext?.service?.code) {
        const serviceCode = String(state.noCodeServiceRecordContext.service.code || "");
        state.noCodeRecordEditor = null;
        if (consumeModalServiceDirty(serviceCode)) {
            await openNoCodeServiceRecords(serviceCode);
        } else {
            renderNoCodeServiceRecordsModal();
        }
        return;
    }
    if (state.noCodeServiceEditor) {
        const confirmed = await confirmAbortNoCodeServiceEditor();
        if (!confirmed) {
            return;
        }
        await returnToNoCodeServiceEditorCaller();
        return;
    }
    if (state.noCodeServiceRecordContext) {
        await openNoCodeServicesModal();
        return;
    }
    closeModal();
}

async function handleSharedListModalClick(actionButton) {
    const action = String(actionButton?.dataset?.action || "");
    if (!action.startsWith("shared-list:") && !action.startsWith("shared-list-item:")) {
        return false;
    }
    if (action === "shared-list:add") {
        openSharedListEditor(null);
        return true;
    }
    if (action === "shared-list:edit") {
        const listCode = String(actionButton.dataset.listCode || "").trim().toLowerCase();
        const row = findSharedList(listCode);
        if (!row) {
            const feedback = document.getElementById("modal-shared-list-feedback");
            if (feedback) {
                feedback.textContent = "Liste partagee introuvable.";
            }
            return true;
        }
        openSharedListEditor(row);
        return true;
    }
    if (action === "shared-list:delete") {
        const listCode = String(actionButton.dataset.listCode || "").trim().toLowerCase();
        const versionToken = String(actionButton.dataset.listVersionToken || "").trim();
        if (!listCode) {
            return true;
        }
        if (!(await showItopsConfirm({
            title: "Supprimer la liste partagee",
            message: `Supprimer la liste partagee '${listCode}' ?`,
            confirmLabel: "Supprimer",
            danger: true,
        }))) {
            return true;
        }
        try {
            const path = versionToken
                ? `/admin/shared-lists/${encodeURIComponent(listCode)}?version_token=${encodeURIComponent(versionToken)}`
                : `/admin/shared-lists/${encodeURIComponent(listCode)}`;
            await requestJson(path, { method: "DELETE" });
            invalidateAdminData(["sharedLists", "services"]);
            await openSharedListsModal();
        } catch (error) {
            const feedback = document.getElementById("modal-shared-list-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return true;
    }
    if (action === "shared-list:items") {
        const listCode = String(actionButton.dataset.listCode || "").trim().toLowerCase();
        try {
            await openSharedListItemsModal(listCode);
        } catch (error) {
            const feedback = document.getElementById("modal-shared-list-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return true;
    }
    if (action === "shared-list:back") {
        await openSharedListsModal();
        return true;
    }
    if (action === "shared-list:back-services") {
        await openNoCodeServicesModal();
        return true;
    }
    if (action === "shared-list-item:add") {
        openSharedListItemEditor(null);
        return true;
    }
    if (action === "shared-list-item:export") {
        const context = state.noCodeSharedListItemsContext;
        const listCode = String(context?.list?.code || "").trim().toLowerCase();
        const feedback = document.getElementById("modal-shared-list-items-feedback");
        if (!listCode) {
            if (feedback) {
                feedback.textContent = "Liste partagee introuvable.";
            }
            return true;
        }
        try {
            if (feedback) {
                feedback.textContent = "Preparation de l'export...";
            }
            const outcome = await exportSharedListItemsToFile(listCode);
            if (feedback) {
                feedback.textContent = `Export termine (${outcome.filename}).`;
            }
        } catch (error) {
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return true;
    }
    if (action === "shared-list-item:import") {
        await runSharedListItemsImportFlow();
        return true;
    }
    if (action === "shared-list-item:edit") {
        const context = state.noCodeSharedListItemsContext;
        const code = String(actionButton.dataset.itemCode || "").trim().toLowerCase();
        const rows = Array.isArray(context?.items) ? context.items : [];
        const row = rows.find((item) => String(item?.code || "").trim().toLowerCase() === code) || null;
        if (!row) {
            const feedback = document.getElementById("modal-shared-list-items-feedback");
            if (feedback) {
                feedback.textContent = "Valeur introuvable.";
            }
            return true;
        }
        openSharedListItemEditor(row);
        return true;
    }
    if (action === "shared-list-item:delete") {
        const context = state.noCodeSharedListItemsContext;
        const listCode = String(context?.list?.code || "").trim().toLowerCase();
        const itemCode = String(actionButton.dataset.itemCode || "").trim().toLowerCase();
        const versionToken = String(actionButton.dataset.itemVersionToken || "").trim();
        if (!listCode || !itemCode) {
            return true;
        }
        if (!(await showItopsConfirm({
            title: "Supprimer la valeur",
            message: `Supprimer la valeur '${itemCode}' ?`,
            confirmLabel: "Supprimer",
            danger: true,
        }))) {
            return true;
        }
        try {
            const path = versionToken
                ? `/admin/shared-lists/${encodeURIComponent(listCode)}/items/${encodeURIComponent(itemCode)}?version_token=${encodeURIComponent(versionToken)}`
                : `/admin/shared-lists/${encodeURIComponent(listCode)}/items/${encodeURIComponent(itemCode)}`;
            await requestJson(path, { method: "DELETE" });
            invalidateAdminData(["sharedLists", "services"]);
            await openSharedListItemsModal(listCode);
        } catch (error) {
            const feedback = document.getElementById("modal-shared-list-items-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return true;
    }
    if (action === "shared-list-item:back") {
        const context = state.noCodeSharedListItemsContext;
        const listCode = String(context?.list?.code || "").trim().toLowerCase();
        if (listCode) {
            await openSharedListItemsModal(listCode);
            return true;
        }
        await openSharedListsModal();
        return true;
    }
    return false;
}

async function handleSharedListModalSubmit(form) {
    if (!(form instanceof HTMLFormElement)) {
        return false;
    }
    if (form.id === "modal-shared-list-form") {
        const feedback = document.getElementById("modal-shared-list-form-feedback");
        if (feedback) {
            feedback.textContent = "";
        }
        const formData = new window.FormData(form);
        const editCode = String(form.dataset.editCode || "").trim().toLowerCase();
        const label = normalizeNoCodeText(formData.get("shared_list_label"));
        if (!label) {
            if (feedback) {
                feedback.textContent = "Libelle requis.";
            }
            return true;
        }
        const sourceCode = normalizeNoCodeText(formData.get("shared_list_code"));
        const code = editCode || (sourceCode ? slugifyNoCodeIdentifier(sourceCode, "list") : "");
        const payload = {
            code,
            label,
            is_system: form.querySelector('[name="shared_list_is_system"]')?.checked ?? false,
            sort_order: Number(formData.get("shared_list_sort_order") || 100),
            version_token: String(form.dataset.versionToken || "").trim(),
        };
        try {
            await requestJson(
                editCode
                    ? `/admin/shared-lists/${encodeURIComponent(editCode)}`
                    : "/admin/shared-lists",
                {
                    method: editCode ? "PUT" : "POST",
                    body: JSON.stringify(payload),
                },
            );
            invalidateAdminData(["sharedLists", "services"]);
            await openSharedListsModal();
        } catch (error) {
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return true;
    }
    if (form.id === "modal-shared-list-item-form") {
        const feedback = document.getElementById("modal-shared-list-item-form-feedback");
        if (feedback) {
            feedback.textContent = "";
        }
        const context = state.noCodeSharedListItemsContext;
        const listCode = String(context?.list?.code || "").trim().toLowerCase();
        if (!listCode) {
            if (feedback) {
                feedback.textContent = "Liste partagee introuvable.";
            }
            return true;
        }
        const formData = new window.FormData(form);
        const editCode = String(form.dataset.editCode || "").trim().toLowerCase();
        const label = normalizeNoCodeText(formData.get("shared_list_item_label"));
        if (!label) {
            if (feedback) {
                feedback.textContent = "Libelle requis.";
            }
            return true;
        }
        const rawCode = normalizeNoCodeText(formData.get("shared_list_item_code"));
        const itemCode = editCode || (rawCode ? slugifyNoCodeIdentifier(rawCode, "item") : "");
        const payload = {
            code: itemCode,
            label,
            is_active: form.querySelector('[name="shared_list_item_is_active"]')?.checked ?? true,
            sort_order: Number(formData.get("shared_list_item_sort_order") || 100),
            version_token: String(form.dataset.versionToken || "").trim(),
        };
        try {
            await requestJson(
                editCode
                    ? `/admin/shared-lists/${encodeURIComponent(listCode)}/items/${encodeURIComponent(editCode)}`
                    : `/admin/shared-lists/${encodeURIComponent(listCode)}/items`,
                {
                    method: editCode ? "PUT" : "POST",
                    body: JSON.stringify(payload),
                },
            );
            invalidateAdminData(["sharedLists", "services"]);
            await openSharedListItemsModal(listCode);
        } catch (error) {
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return true;
    }
    return false;
}

async function handleNoCodeModalClick(actionButton) {
    const action = String(actionButton?.dataset?.action || "");
    if (!action.startsWith("service:") && !action.startsWith("duplicates:")) {
        return false;
    }
    if (action === "service:module:toggle-active") {
        const moduleCode = String(actionButton.dataset.moduleCode || "").trim().toLowerCase();
        const moduleRow = findAdminModuleRow(moduleCode);
        if (!moduleRow) {
            return true;
        }
        try {
            await setPortalModuleActivation(moduleRow, !Boolean(moduleRow?.is_active));
            await openNoCodeServicesModal();
        } catch (error) {
            const feedback = document.getElementById("modal-service-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return true;
    }
    if (action === "service:monitoring:toggle-active") {
        const monitoringModule = findAdminModuleRow("monitoring");
        if (!monitoringModule) {
            return true;
        }
        try {
            await requestJson("/admin/modules/monitoring/activation", {
                method: "PUT",
                body: JSON.stringify({ is_active: !Boolean(monitoringModule?.is_active) }),
            });
            state.moduleAccessLoaded = false;
            invalidateAdminData(["services", "modules"]);
            await Promise.all([
                openNoCodeServicesModal(),
                loadPortalModules({ forceRefresh: true }),
            ]);
        } catch (error) {
            const feedback = document.getElementById("modal-service-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return true;
    }
    if (action === "service:definition:add") {
        await openNoCodeServiceEditor(null);
        return true;
    }
    if (action === "service:definition:edit") {
        const serviceCode = String(actionButton.dataset.serviceCode || "");
        if (normalizeNoCodeText(serviceCode).toLowerCase() === "monitoring") {
            return true;
        }
        const service = findNoCodeService(serviceCode);
        if (!service) {
            return true;
        }
        if (isSystemNoCodeService(service)) {
            const feedback = document.getElementById("modal-service-feedback");
            if (feedback) {
                feedback.textContent = "Module socle protege: la definition n'est pas modifiable.";
            }
            return true;
        }
        await openNoCodeServiceEditor(service);
        return true;
    }
    if (action === "service:definition:toggle-active") {
        const code = String(actionButton.dataset.serviceCode || "").trim();
        if (normalizeNoCodeText(code).toLowerCase() === "monitoring") {
            return true;
        }
        const versionToken = String(actionButton.dataset.serviceVersionToken || "").trim();
        const service = findNoCodeService(code);
        if (!code || !service) {
            return true;
        }
        const nextActive = !Boolean(service?.is_active);
        const payload = {
            code: String(service.code || "").trim(),
            label: String(service.label || "").trim(),
            is_active: nextActive,
            credentials_enabled: Boolean(service.credentials_enabled),
            child_enabled: Boolean(service.child_enabled),
            child_label: String(service.child_label || "Elements lies").trim() || "Elements lies",
            sort_order: Number(service.sort_order || 100),
            version_token: versionToken || String(service.version_token || ""),
            fields: noCodeCustomServiceFields(service),
        };
        try {
            await requestJson(`/admin/custom-services/${encodeURIComponent(code)}`, {
                method: "PUT",
                body: JSON.stringify(payload),
            });
            state.moduleAccessLoaded = false;
            invalidateAdminData(["services", "modules"]);
            await Promise.all([
                openNoCodeServicesModal(),
                loadPortalModules({ forceRefresh: true }),
            ]);
        } catch (error) {
            const feedback = document.getElementById("modal-service-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return true;
    }
    if (action === "service:definition:delete") {
        const code = String(actionButton.dataset.serviceCode || "").trim();
        if (normalizeNoCodeText(code).toLowerCase() === "monitoring") {
            return true;
        }
        const versionToken = String(actionButton.dataset.serviceVersionToken || "").trim();
        if (!code) {
            return true;
        }
        if (isReservedSystemEntityCode(code) || isSystemNoCodeService(code)) {
            const feedback = document.getElementById("modal-service-feedback");
            if (feedback) {
                feedback.textContent = "Ce module systeme n'est pas un service personnalise.";
            }
            return true;
        }
        let impact = null;
        try {
            impact = await fetchNoCodeServiceDeleteImpact(code);
        } catch (_error) {
            impact = null;
        }
        const impactDetails = impact
            ? [
                `${Number(impact.record_count || 0)} fiche(s) du service seront supprimees.`,
                `${Number(impact.relation_count || 0)} relation(s) entrante(s)/sortante(s) seront supprimees.`,
                `${Number(impact.relation_link_count || 0)} lien(s) entre fiches seront supprimes.`,
                ...(Array.isArray(impact.warnings) ? impact.warnings : []),
            ].filter(Boolean)
            : ["Analyse d'impact indisponible: verifie manuellement les fiches et relations liees avant suppression."];
        if (!(await showItopsConfirm({
            title: "Supprimer le service",
            message: `Supprimer le service '${code}' ?`,
            details: impactDetails,
            confirmLabel: "Supprimer",
            danger: true,
        }))) {
            return true;
        }
        try {
            const path = versionToken
                ? `/admin/custom-services/${encodeURIComponent(code)}?version_token=${encodeURIComponent(versionToken)}`
                : `/admin/custom-services/${encodeURIComponent(code)}`;
            await requestJson(path, { method: "DELETE" });
            state.moduleAccessLoaded = false;
            invalidateAdminData(["services", "modules"]);
            await Promise.all([
                openNoCodeServicesModal(),
                loadPortalModules({ forceRefresh: true }),
            ]);
        } catch (error) {
            const feedback = document.getElementById("modal-service-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return true;
    }
    if (action === "service:records:open") {
        const code = String(actionButton.dataset.serviceCode || "").trim();
        if (!code) {
            return true;
        }
        try {
            await openNoCodeServiceRecords(code);
        } catch (error) {
            const feedback = document.getElementById("modal-service-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return true;
    }
    if (action === "service:records:page") {
        const context = state.noCodeServiceRecordContext;
        const offset = Math.max(0, Number(actionButton.dataset.offset || 0));
        const feedback = document.getElementById("modal-service-records-feedback");
        try {
            await reloadNoCodeServiceRecordsPage(context, { offset });
        } catch (error) {
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return true;
    }
    if (action === "service:back") {
        try {
            const confirmed = await confirmAbortNoCodeServiceEditor();
            if (confirmed) {
                await returnToNoCodeServiceEditorCaller();
            }
        } catch (error) {
            const feedback = document.getElementById("modal-service-form-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return true;
    }
    if (action === "service:wizard:step") {
        const editor = state.noCodeServiceEditor;
        if (!editor) {
            return true;
        }
        setNoCodeServiceWizardStep(actionButton.dataset.step || 1);
        return true;
    }
    if (action === "service:wizard:previous") {
        const editor = state.noCodeServiceEditor;
        if (!editor) {
            return true;
        }
        setNoCodeServiceWizardStep(currentNoCodeServiceWizardStep() - 1);
        return true;
    }
    if (action === "service:icon:select") {
        const editor = state.noCodeServiceEditor;
        if (!editor) {
            return true;
        }
        syncNoCodeServiceEditorFromForm();
        const iconCode = String(actionButton.dataset.serviceIcon || "").trim().toLowerCase();
        editor.icon = serviceIconDefinition(iconCode)?.code || "";
        renderNoCodeServiceEditorShell();
        return true;
    }
    if (action === "service:wizard:next") {
        const editor = state.noCodeServiceEditor;
        const feedback = document.getElementById("modal-service-form-feedback");
        if (!editor) {
            return true;
        }
        syncNoCodeServiceEditorFromForm();
        if (currentNoCodeServiceWizardStep() === 1 && !normalizeNoCodeText(editor.label)) {
            if (feedback) {
                feedback.textContent = "Nom du service requis.";
            }
            return true;
        }
        if (feedback) {
            feedback.textContent = "";
        }
        setNoCodeServiceWizardStep(currentNoCodeServiceWizardStep() + 1);
        return true;
    }
    if (action === "service:relation-guide:start") {
        openNoCodeRelationGuide();
        return true;
    }
    if (action === "service:relation-guide:back") {
        returnToNoCodeServiceRelationsEditor();
        return true;
    }
    if (action === "service:relation:add") {
        const editor = state.noCodeServiceEditor;
        const serviceCode = normalizeNoCodeRelationEntityCode(actionButton.dataset.serviceCode || "");
        const service = findNoCodeRelationEntity(serviceCode);
        if (!editor || !serviceCode || !service) {
            return true;
        }
        if (!Array.isArray(editor.relationDrafts)) {
            editor.relationDrafts = [];
        }
        const currentCode = noCodeRelationCurrentServiceCode(editor);
        if (!noCodeRelationNodeCodes(editor).includes(serviceCode)) {
            editor.relationCanvas = editor.relationCanvas && typeof editor.relationCanvas === "object" ? editor.relationCanvas : {};
            editor.relationCanvas.nodes = editor.relationCanvas.nodes && typeof editor.relationCanvas.nodes === "object" ? editor.relationCanvas.nodes : {};
            editor.relationCanvas.nodes[serviceCode] = {
                x: 430,
                y: 34 + (Math.max(0, Object.keys(editor.relationCanvas.nodes).length) * 152),
            };
            if (!noCodeRelationDrafts(editor).length) {
                const relation = createNoCodeRelationDraft(service, 0, currentCode);
                const sourcePos = noCodeRelationNodePosition(editor, currentCode, 0);
                const targetPos = noCodeRelationNodePosition(editor, serviceCode, noCodeRelationNodeCodes(editor).indexOf(serviceCode));
                relation.source_x = sourcePos.x;
                relation.source_y = sourcePos.y;
                relation.target_x = targetPos.x;
                relation.target_y = targetPos.y;
                relation.x = targetPos.x;
                relation.y = targetPos.y;
                editor.relationDrafts = [relation];
                editor.selectedRelationId = noCodeRelationId(relation, 0);
            } else {
                editor.selectedRelationId = "";
            }
        } else if (!findNoCodeRelationDraft(editor, serviceCode)) {
            editor.selectedRelationId = "";
        }
        editor.selectedRelationServiceCode = serviceCode;
        renderNoCodeServiceEditorShell();
        return true;
    }
    if (action === "service:relation:zoom-in" || action === "service:relation:zoom-out") {
        const editor = state.noCodeServiceEditor;
        if (editor) {
            editor.relationCanvas = editor.relationCanvas && typeof editor.relationCanvas === "object" ? editor.relationCanvas : {};
            const currentZoom = normalizeNoCodeRelationZoom(editor.relationCanvas.zoom || 1);
            editor.relationCanvas.zoom = normalizeNoCodeRelationZoom(currentZoom + (action === "service:relation:zoom-in" ? 0.1 : -0.1));
            renderNoCodeServiceEditorShell();
        }
        return true;
    }
    if (action === "service:relation:center") {
        const editor = state.noCodeServiceEditor;
        if (editor) {
            editor.relationCanvas = { zoom: 1, currentX: 36, currentY: 176, nodes: {} };
            editor.relationDrafts = noCodeRelationDrafts(editor).map((relation, index) => ({
                ...relation,
                source_x: 36,
                source_y: 176,
                target_x: 430,
                target_y: 34 + (index * 152),
                x: 430,
                y: 34 + (index * 152),
            }));
            renderNoCodeServiceEditorShell();
        }
        return true;
    }
    if (action === "service:relation:node-select") {
        const editor = state.noCodeServiceEditor;
        if (editor && Date.now() >= Number(state.noCodeRelationSuppressClickUntil || 0)) {
            editor.selectedRelationServiceCode = normalizeNoCodeRelationEntityCode(actionButton.dataset.serviceCode || "");
            renderNoCodeServiceEditorShell();
        }
        return true;
    }
    if (action === "service:relation:select-link") {
        const editor = state.noCodeServiceEditor;
        if (editor) {
            const relationId = String(actionButton.dataset.relationId || "").trim();
            const relation = findNoCodeRelationDraftById(editor, relationId);
            editor.selectedRelationId = relationId;
            editor.selectedRelationServiceCode = normalizeNoCodeRelationEntityCode(relation?.target_service_code || relation?.service_code || "");
            renderNoCodeServiceEditorShell();
        }
        return true;
    }
    if (action === "service:relation:select") {
        const editor = state.noCodeServiceEditor;
        if (editor) {
            editor.selectedRelationServiceCode = normalizeNoCodeRelationEntityCode(actionButton.dataset.serviceCode || "");
            renderNoCodeServiceEditorShell();
        }
        return true;
    }
    if (action === "service:relation:verb" || action === "service:relation:cardinality") {
        const editor = state.noCodeServiceEditor;
        const relationId = String(actionButton.dataset.relationId || "").trim();
        const relation = findNoCodeRelationDraftById(editor, relationId);
        if (editor && relation) {
            if (action === "service:relation:verb") {
                relation.verb = String(actionButton.dataset.verb || "est lie a").trim() || "est lie a";
            } else {
                relation.cardinality = normalizeNoCodeRelationCardinality(actionButton.dataset.cardinality || "many_to_one");
                relation.relation_type = relation.cardinality;
            }
            editor.selectedRelationId = relationId;
            renderNoCodeServiceEditorShell();
        }
        return true;
    }
    if (action === "service:relation:assignment:prepare") {
        const editor = state.noCodeServiceEditor;
        const relationId = String(actionButton.dataset.relationId || "").trim();
        const relation = findNoCodeRelationDraftById(editor, relationId);
        if (editor && relation) {
            try {
                await prepareNoCodeRelationAssignment(editor, relation);
            } catch (error) {
                setNoCodeRelationAssignmentFeedback(editor, relationId, normalizeErrorMessage(error.message));
                renderNoCodeServiceEditorShell();
            }
        }
        return true;
    }
    if (action === "service:relation:assignment:start") {
        const editor = state.noCodeServiceEditor;
        const relationId = String(actionButton.dataset.relationId || "").trim();
        const relation = findNoCodeRelationDraftById(editor, relationId);
        if (editor && relation) {
            relation.record_display_mode = "assignment";
            editor.selectedRelationId = relationId;
            renderNoCodeServiceEditorShell();
        }
        return true;
    }
    if (action === "service:relation:remove") {
        const editor = state.noCodeServiceEditor;
        const relationId = String(actionButton.dataset.relationId || "").trim();
        const relation = findNoCodeRelationDraftById(editor, relationId);
        const storedRelationId = Number(relation?.id || relation?.relation_id || 0);
        const currentCode = noCodeRelationCurrentServiceCode(editor);
        if (editor && relation && storedRelationId > 0) {
            try {
                const impact = await fetchNoCodeRelationImpact(currentCode, storedRelationId);
                const linkCount = Number(impact?.link_count || 0);
                if (linkCount > 0) {
                    await showItopsAlert({
                        title: "Suppression bloquee",
                        message: "Cette relation contient deja des liens entre fiches.",
                        details: [
                            `${linkCount} lien(s) seraient supprimes.`,
                            "Pour garantir la coherence, supprime d'abord les liens entre fiches ou conserve cette relation.",
                        ],
                    });
                    return true;
                }
            } catch (error) {
                await showItopsAlert({
                    title: "Analyse d'impact impossible",
                    message: normalizeErrorMessage(error.message),
                });
                return true;
            }
        }
        if (editor && relationId && await showItopsConfirm({
            title: "Supprimer la relation",
            message: "Retirer cette relation du schema ?",
            details: [
                "Aucun lien existant n'a ete detecte pour cette relation.",
                "La relation ne sera plus proposee pour relier les fiches.",
            ],
            confirmLabel: "Retirer",
            danger: true,
        })) {
            editor.relationDrafts = noCodeRelationDrafts(editor)
                .filter((relation, index) => noCodeRelationId(relation, index) !== relationId);
            const firstRelation = editor.relationDrafts?.[0] || null;
            editor.selectedRelationId = firstRelation ? noCodeRelationId(firstRelation, 0) : "";
            editor.selectedRelationServiceCode = normalizeNoCodeRelationEntityCode(firstRelation?.target_service_code || firstRelation?.service_code || "");
            renderNoCodeServiceEditorShell();
        }
        return true;
    }
    if (action === "service:field:add") {
        const editor = state.noCodeServiceEditor;
        if (editor?.fieldEditor?.mode === "create") {
            editor.fieldEditor = null;
            renderNoCodeServiceEditor();
            return true;
        }
        startNoCodeFieldEditor("");
        return true;
    }
    if (action === "service:field:export") {
        const feedback = document.getElementById("modal-service-form-feedback");
        const editor = state.noCodeServiceEditor;
        const serviceCode = String(editor?.code || "").trim().toLowerCase();
        if (!serviceCode) {
            if (feedback) {
                feedback.textContent = "Enregistre le service avant d'exporter ses champs.";
            }
            return true;
        }
        try {
            if (feedback) {
                feedback.textContent = "Preparation de l'export...";
            }
            const outcome = await exportServiceFieldsToFile(serviceCode);
            if (feedback) {
                feedback.textContent = `Export termine (${outcome.filename}).`;
            }
        } catch (error) {
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return true;
    }
    if (action === "service:field:import") {
        const feedback = document.getElementById("modal-service-form-feedback");
        const editor = state.noCodeServiceEditor;
        if (!editor) {
            return true;
        }
        const pickedFile = await pickServiceDefinitionImportFile();
        if (!pickedFile) {
            return true;
        }
        try {
            if (feedback) {
                feedback.textContent = "Analyse du fichier en cours...";
            }
            const headerMode = normalizeTabularHeaderMode(editor.importHeaderMode);
            const headerRowNumber = normalizeTabularHeaderRowNumber(editor.importHeaderRowNumber);
            const imported = await importServiceFieldsFromFile(
                pickedFile,
                "",
                headerMode,
                headerRowNumber,
                [],
                normalizeTabularUntilRowNumber(editor.importUntilRowNumber),
            );
            if (!imported.fields.length) {
                if (feedback) {
                    feedback.textContent = "Aucune colonne exploitable n'a ete detectee.";
                }
                return true;
            }
            editor.importFile = pickedFile;
            editor.adImportDraft = null;
            editor.appliedActiveDirectoryImportForRecords = null;
            editor.importPreview = {
                filename: String(pickedFile?.name || ""),
                fields: imported.fields,
                detectedRows: imported.detectedRows,
                detectedColumns: imported.detectedColumns,
                sourceHeaders: Array.isArray(imported.sourceHeaders) ? imported.sourceHeaders : [],
                sourceRowsPreview: Array.isArray(imported.sourceRowsPreview) ? imported.sourceRowsPreview : [],
                availableSheets: Array.isArray(imported.availableSheets) ? imported.availableSheets : [],
                selectedSheetName: String(imported.selectedSheetName || "").trim(),
                detectedHeaderRowNumber: Number(imported.detectedHeaderRowNumber || headerRowNumber || 1),
                effectiveHeaderMode: normalizeTabularHeaderMode(imported.effectiveHeaderMode || headerMode),
                effectiveMapping: Array.isArray(imported.effectiveMapping) ? imported.effectiveMapping : [],
            };
            editor.importHeaderMode = normalizeTabularHeaderMode(imported.effectiveHeaderMode || headerMode);
            editor.importHeaderRowNumber = normalizeTabularHeaderRowNumber(imported.detectedHeaderRowNumber || headerRowNumber || 1);
            editor.importColumnMappings = normalizeServiceFieldImportMappings(imported.effectiveMapping);
            editor.importColumnPage = 0;
            renderNoCodeServiceEditor();
            if (feedback) {
                feedback.textContent = `Apercu pret: ${imported.detectedColumns} colonne(s) detectee(s), ${imported.fields.length} champ(s) proposes.`;
            }
        } catch (error) {
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return true;
    }
    if (action === "service:field:ad-source") {
        const feedback = document.getElementById("modal-service-form-feedback");
        const editor = state.noCodeServiceEditor;
        if (!editor) {
            return true;
        }
        try {
            if (feedback) feedback.textContent = "Chargement des profils Active Directory...";
            const payload = await requestJson("/sync/active-directory/profiles");
            editor.adImportPayload = payload;
            editor.importFile = null;
            editor.importPreview = null;
            editor.appliedImportForRecords = null;
            editor.appliedActiveDirectoryImportForRecords = null;
            const defaultTarget = "organizational_units";
            editor.adImportDraft = {
                profile_id: "",
                target_kind: defaultTarget,
                label: editor.label || "Services mairie",
                code: "",
                search_base: "",
                search_filter: activeDirectoryProfileDefaultFilter(defaultTarget),
                selected_attributes: listFromMaybeArray(payload.available_attributes?.[defaultTarget]).slice(0, 5),
                options: {},
            };
            renderNoCodeServiceEditor();
            window.setTimeout(() => loadServiceActiveDirectoryExamples({ silent: true }), 0);
            if (feedback) feedback.textContent = "Source Active Directory prete.";
        } catch (error) {
            if (feedback) feedback.textContent = normalizeErrorMessage(error.message);
        }
        return true;
    }
    if (action === "service:field:ad-source:clear") {
        const editor = state.noCodeServiceEditor;
        if (editor) {
            editor.adImportDraft = null;
            editor.appliedActiveDirectoryImportForRecords = null;
            renderNoCodeServiceEditor();
        }
        return true;
    }
    if (action === "service:field:ad-source:preview") {
        await loadServiceActiveDirectoryExamples();
        return true;
    }
    if (action === "service:field:ad-source:apply") {
        const feedback = document.getElementById("modal-service-form-feedback");
        const editor = state.noCodeServiceEditor;
        if (!editor) {
            return true;
        }
        syncServiceActiveDirectoryDraftFromDom();
        const draft = editor.adImportDraft || {};
        const attributes = listFromMaybeArray(draft.selected_attributes);
        const mappings = listFromMaybeArray(draft.field_mappings);
        if (!attributes.length) {
            if (feedback) feedback.textContent = "Selectionne au moins un champ AD.";
            return true;
        }
        if ((editor.fields || []).length > 0) {
            const confirmReplace = await showItopsConfirm({
                title: "Remplacer les champs",
                message: "Les champs actuels seront remplaces par les champs issus de la source AD. Confirmer ?",
                confirmLabel: "Remplacer",
                danger: true,
            });
            if (!confirmReplace) {
                if (feedback) feedback.textContent = "Application de la source AD annulee.";
                return true;
            }
        }
        try {
            if (feedback) feedback.textContent = "Enregistrement du profil AD...";
            const saved = await requestJson("/sync/active-directory/profiles", {
                method: "POST",
                body: JSON.stringify({
                    id: String(draft.profile_id || draft.id || ""),
                    code: String(draft.code || ""),
                    label: String(draft.label || editor.label || "Source AD"),
                    target_kind: normalizeActiveDirectoryProfileTargetKind(draft.target_kind),
                    search_base: String(draft.search_base || ""),
                    search_filter: String(draft.search_filter || activeDirectoryProfileDefaultFilter(draft.target_kind)),
                    selected_attributes: attributes,
                    options: {
                        ...(draft.options || {}),
                        consumer_kind: "custom_service",
                        service_code: noCodeServiceTechnicalCodeDisplay(editor),
                        field_mappings: mappings,
                    },
                    is_active: true,
                }),
            });
            const existingByKey = new Map((editor.fields || []).map((field) => [String(field.field_key || "").trim(), field]));
            const nextFields = [];
            const effectiveFieldMappings = [];
            attributes.forEach((attribute, index) => {
                const mapping = mappings.find((item) => String(item.attribute || "") === String(attribute || ""));
                if (mapping?.target === "ignore") {
                    return;
                }
                if (mapping?.target === "existing" && String(mapping.field_key || "").trim()) {
                    const existing = existingByKey.get(String(mapping.field_key || "").trim());
                    if (existing && !nextFields.some((field) => String(field.field_key || "") === String(existing.field_key || ""))) {
                        nextFields.push(existing);
                        effectiveFieldMappings.push({
                            attribute: String(attribute || "").trim(),
                            target: "existing",
                            field_key: String(existing.field_key || "").trim(),
                        });
                    }
                    return;
                }
                const generated = activeDirectoryAttributeToServiceField(attribute, index);
                if (mapping?.label) generated.label = String(mapping.label || generated.label).trim();
                if (mapping?.field_kind) generated.field_kind = normalizeNoCodeKind(mapping.field_kind);
                const generatedKey = String(generated.field_key || "").trim();
                const generatedLabelKey = slugifyNoCodeIdentifier(generated.label || generatedKey, "");
                const existingMatch = findExistingServiceFieldForActiveDirectoryAttribute(editor, attribute, index)
                    || Array.from(existingByKey.values()).find((field) => {
                        const fieldKey = String(field?.field_key || "").trim();
                        const fieldLabelKey = slugifyNoCodeIdentifier(field?.label || fieldKey, "");
                        return fieldKey === generatedKey || (generatedLabelKey && fieldLabelKey === generatedLabelKey);
                    });
                if (existingMatch) {
                    if (!nextFields.some((field) => String(field.field_key || "") === String(existingMatch.field_key || ""))) {
                        nextFields.push(existingMatch);
                    }
                    effectiveFieldMappings.push({
                        attribute: String(attribute || "").trim(),
                        target: "existing",
                        field_key: String(existingMatch.field_key || "").trim(),
                    });
                    return;
                }
                nextFields.push(generated);
                effectiveFieldMappings.push({
                    attribute: String(attribute || "").trim(),
                    target: "existing",
                    field_key: String(generated.field_key || "").trim(),
                });
            });
            editor.fields = nextFields;
            editor.appliedActiveDirectoryImportForRecords = {
                targetKind: normalizeActiveDirectoryProfileTargetKind(draft.target_kind),
                profileId: String(saved.id || draft.profile_id || draft.id || ""),
                fieldMappings: effectiveFieldMappings,
            };
            editor.adImportDraft = null;
            editor.adImportPayload = null;
            editor.fieldEditor = null;
            renderNoCodeServiceEditor();
            if (feedback) feedback.textContent = `Source AD appliquee (${saved.label || "profil"}): ${editor.fields.length} champ(s). Enregistre le service pour importer les donnees AD.`;
        } catch (error) {
            if (feedback) feedback.textContent = normalizeErrorMessage(error.message);
        }
        return true;
    }
    if (action === "service:field:ad-source:add-field") {
        return true;
    }
    if (action === "service:field:import:apply") {
        const feedback = document.getElementById("modal-service-form-feedback");
        const editor = state.noCodeServiceEditor;
        const preview = editor?.importPreview;
        if (!editor || !preview || !Array.isArray(preview.fields) || !preview.fields.length) {
            return true;
        }
        if ((editor.fields || []).length > 0) {
            const confirmReplace = await showItopsConfirm({
                title: "Remplacer les champs",
                message: "Les champs actuels seront remplaces par les champs issus de l'import. Confirmer ?",
                confirmLabel: "Remplacer",
                danger: true,
            });
            if (!confirmReplace) {
                if (feedback) {
                    feedback.textContent = "Application de l'import annulee.";
                }
                return true;
            }
        }
        const columnMappings = mergeServiceFieldImportMappings(
            editor.importColumnMappings,
            readServiceFieldImportMappingsFromDom(),
        );
        editor.fields = preview.fields;
        editor.appliedImportForRecords = editor.importRecordsEnabled !== false
            ? {
                file: editor.importFile,
                fields: preview.fields,
                sourceHeaders: Array.isArray(preview.sourceHeaders) ? preview.sourceHeaders : [],
                columnMappings,
                sheetName: String(preview.selectedSheetName || "").trim(),
                headerMode: normalizeTabularHeaderMode(editor.importHeaderMode || preview.effectiveHeaderMode || "auto"),
                headerRowNumber: normalizeTabularHeaderRowNumber(editor.importHeaderRowNumber || preview.detectedHeaderRowNumber || 1),
                importUntilRowNumber: normalizeTabularUntilRowNumber(editor.importUntilRowNumber || 0),
            }
            : null;
        editor.fieldEditor = null;
        editor.importFile = null;
        editor.importPreview = null;
        editor.importHeaderMode = "auto";
        editor.importHeaderRowNumber = 1;
        editor.importAdvancedEnabled = false;
        editor.importUntilRowNumber = 0;
        editor.importColumnMappings = [];
        editor.importColumnPage = 0;
        renderNoCodeServiceEditor();
        if (feedback) {
            feedback.textContent = `Importation appliquee: ${editor.fields.length} champ(s) mis a jour.`;
        }
        return true;
    }
    if (action === "service:field:import:clear") {
        const feedback = document.getElementById("modal-service-form-feedback");
        const editor = state.noCodeServiceEditor;
        if (!editor) {
            return true;
        }
        editor.importFile = null;
        editor.importPreview = null;
        editor.appliedImportForRecords = null;
        editor.importHeaderMode = "auto";
        editor.importHeaderRowNumber = 1;
        editor.importAdvancedEnabled = false;
        editor.importUntilRowNumber = 0;
        editor.importColumnMappings = [];
        editor.importColumnPage = 0;
        renderNoCodeServiceEditor();
        if (feedback) {
            feedback.textContent = "Apercu d'import retire.";
        }
        return true;
    }
    if (action === "service:field:edit") {
        const editor = state.noCodeServiceEditor;
        const fieldKey = String(actionButton.dataset.fieldKey || "");
        const openedKey = String(editor?.fieldEditor?.originalKey || "").trim();
        const openedMode = String(editor?.fieldEditor?.mode || "");
        if (openedMode === "edit" && openedKey === String(fieldKey || "").trim()) {
            if (editor) {
                editor.fieldEditor = null;
                renderNoCodeServiceEditor();
            }
            return true;
        }
        startNoCodeFieldEditor(fieldKey);
        return true;
    }
    if (action === "service:field:delete") {
        removeNoCodeField(String(actionButton.dataset.fieldKey || ""));
        return true;
    }
    if (action === "service:field:cancel") {
        if (state.noCodeServiceEditor) {
            state.noCodeServiceEditor.fieldEditor = null;
            renderNoCodeServiceEditor();
        }
        return true;
    }
    if (action === "service:field:save") {
        const feedback = document.getElementById("modal-service-form-feedback");
        const outcome = saveNoCodeFieldDraft();
        if (!outcome.ok && feedback) {
            feedback.textContent = outcome.message || "Enregistrement du champ impossible.";
        } else if (feedback) {
            feedback.textContent = "";
        }
        return true;
    }
    if (action === "service:records:duplicates") {
        const context = state.noCodeServiceRecordContext;
        openModal("Nettoyage des doublons", buildNoCodeDuplicateAnalysisMarkup(context), { width: "min(900px, calc(100vw - 40px))" });
        return true;
    }
    if (action === "duplicates:back") {
        renderNoCodeServiceRecordsModal({ inline: true });
        return true;
    }
    if (action === "duplicates:analyze") {
        const context = state.noCodeServiceRecordContext;
        const serviceCode = String(context?.service?.code || "").trim().toLowerCase();
        const field = document.getElementById("duplicate-analysis-field");
        const fieldKey = String(field instanceof HTMLSelectElement ? field.value : "").trim();
        const feedback = document.getElementById("duplicate-analysis-feedback");
        if (!serviceCode || !fieldKey) {
            if (feedback instanceof HTMLElement) feedback.textContent = "Choisissez un identifiant stable.";
            return true;
        }
        try {
            const result = await requestJson(`/admin/custom-services/${encodeURIComponent(serviceCode)}/records/duplicates?field_key=${encodeURIComponent(fieldKey)}`);
            openModal("Nettoyage des doublons", buildNoCodeDuplicateAnalysisMarkup(context, result), { width: "min(900px, calc(100vw - 40px))" });
        } catch (error) {
            if (feedback instanceof HTMLElement) feedback.textContent = normalizeErrorMessage(error.message);
        }
        return true;
    }
    if (action === "service:records:export") {
        const context = state.noCodeServiceRecordContext;
        const serviceCode = String(context?.service?.code || "").trim().toLowerCase();
        const feedback = document.getElementById("modal-service-records-feedback");
        if (!serviceCode) {
            if (feedback) {
                feedback.textContent = "Service introuvable.";
            }
            return true;
        }
        try {
            setServiceRecordsImportProgress(0, "", false);
            if (feedback) {
                feedback.textContent = "Preparation de l'export...";
            }
            const outcome = await exportServiceRecordsToFile(serviceCode);
            if (feedback) {
                feedback.textContent = `Export termine (${outcome.filename}).`;
            }
        } catch (error) {
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return true;
    }
    if (action === "service:records:import") {
        const context = state.noCodeServiceRecordContext;
        const serviceCode = String(context?.service?.code || "").trim().toLowerCase();
        const feedback = document.getElementById("modal-service-records-feedback");
        if (!serviceCode) {
            if (feedback) {
                feedback.textContent = "Service introuvable.";
            }
            return true;
        }
        try {
            invalidateAdminData(["services"]);
            await loadAdministrationData({
                includeModules: false,
                includeRoles: false,
                includeUsers: false,
                includeServices: true,
                includeSharedLists: true,
            });
            const freshService = findNoCodeService(serviceCode);
            if (freshService && context) {
                context.service = freshService;
            }
        } catch (error) {
            if (feedback) {
                feedback.textContent = `Rechargement du schema service impossible: ${normalizeErrorMessage(error.message)}`;
            }
            return true;
        }
        const pickedFile = await pickServiceDefinitionImportFile();
        if (!pickedFile) {
            return true;
        }
        try {
            setServiceRecordsImportProgress(10, "Analyse du fichier...", true);
            if (feedback) {
                feedback.textContent = "Analyse du fichier en cours...";
            }
            const credentialMode = normalizeRecordsImportCredentialMode(context?.importCredentialMode);
            const selectedSheetName = String(context?.importSheetName || "").trim();
            const headerMode = normalizeTabularHeaderMode(context?.importHeaderMode);
            const headerRowNumber = normalizeTabularHeaderRowNumber(context?.importHeaderRowNumber);
            const initialMappings = [];
            const preview = await previewServiceRecordsFromFile(
                pickedFile,
                serviceCode,
                credentialMode,
                selectedSheetName,
                headerMode,
                headerRowNumber,
                initialMappings,
            );
            setServiceRecordsImportProgress(55, "Apercu pret", true);
            if (!Array.isArray(preview.rows) || !preview.rows.length) {
                if (feedback) {
                    feedback.textContent = "Aucune fiche exploitable detectee.";
                }
                setServiceRecordsImportProgress(0, "", false);
                return true;
            }
            context.importPreview = {
                ...preview,
                filename: String(pickedFile?.name || ""),
            };
            context.importFile = pickedFile;
            context.importCredentialMode = credentialMode;
            context.importSheetName = String(preview.selectedSheetName || selectedSheetName || "").trim();
            context.importAvailableSheets = Array.isArray(preview.availableSheets) ? preview.availableSheets.map((item) => String(item || "")) : [];
            context.importHeaderMode = normalizeTabularHeaderMode(preview.effectiveHeaderMode || headerMode);
            context.importHeaderRowNumber = normalizeTabularHeaderRowNumber(preview.detectedHeaderRowNumber || headerRowNumber || 1);
            context.importColumnMappings = buildServiceRecordImportMappingsFromEffectiveMapping(preview.effectiveMapping);
            context.importColumnPage = 0;
            if (!context.importColumnMappings.length) {
                context.importColumnMappings = buildDefaultServiceRecordImportMappings(context.service, preview.sourceHeaders);
            }
            renderNoCodeServiceRecordsModal();
            setServiceRecordsImportProgress(55, "Apercu pret", true);
            const refreshedFeedback = document.getElementById("modal-service-records-feedback");
            if (refreshedFeedback) {
                refreshedFeedback.textContent = `Apercu charge: ${preview.rows.length} fiche(s) detectee(s). Verifie puis clique 'Appliquer l'import'.`;
            }
        } catch (error) {
            setServiceRecordsImportProgress(0, "", false);
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return true;
    }
    if (action === "service:records:import:clear") {
        const context = state.noCodeServiceRecordContext;
        if (context) {
            context.importPreview = null;
            context.importFile = null;
            context.importSheetName = "";
            context.importAvailableSheets = [];
            context.importHeaderMode = "auto";
            context.importHeaderRowNumber = 1;
            context.importColumnMappings = [];
            context.importColumnPage = 0;
            renderNoCodeServiceRecordsModal();
            const refreshedFeedback = document.getElementById("modal-service-records-feedback");
            if (refreshedFeedback) {
                refreshedFeedback.textContent = "Apercu d'import retire.";
            }
            setServiceRecordsImportProgress(0, "", false);
        }
        return true;
    }
    if (action === "service:records:import:apply") {
        const context = state.noCodeServiceRecordContext;
        const serviceCode = String(context?.service?.code || "").trim().toLowerCase();
        const feedback = document.getElementById("modal-service-records-feedback");
        const importFile = context?.importFile || null;
        if (!serviceCode || !importFile) {
            if (feedback) {
                feedback.textContent = "Aucun apercu d'import a appliquer.";
            }
            return true;
        }
        try {
            const credentialSelector = document.querySelector('select[name="service_records_import_credential_mode"]');
            const sheetSelector = document.querySelector('select[name="service_records_import_sheet"]');
            const headerModeSelector = document.querySelector('select[name="service_records_import_header_mode"]');
            const headerRowInput = document.querySelector('input[name="service_records_import_header_row"]');
            const duplicatePolicySelector = document.querySelector('select[name="service_records_import_duplicate_policy"]');
            const duplicateFieldSelector = document.querySelector('select[name="service_records_import_duplicate_field"]');
            const credentialMode = normalizeRecordsImportCredentialMode(
                credentialSelector?.value || context?.importCredentialMode,
            );
            const selectedSheetName = String(sheetSelector?.value || context?.importSheetName || "").trim();
            const headerMode = normalizeTabularHeaderMode(headerModeSelector?.value || context?.importHeaderMode);
            const headerRowNumber = normalizeTabularHeaderRowNumber(headerRowInput?.value || context?.importHeaderRowNumber);
            const duplicatePolicy = ["skip", "update", "create"].includes(String(duplicatePolicySelector?.value || "")) ? String(duplicatePolicySelector.value) : "skip";
            const duplicateFieldKey = String(duplicateFieldSelector?.value || context?.importDuplicateFieldKey || "").trim();
            const columnMappings = mergeServiceRecordImportMappings(
                context?.importColumnMappings,
                readServiceRecordImportMappingsFromDom(),
            );
            context.importCredentialMode = credentialMode;
            context.importSheetName = selectedSheetName;
            context.importHeaderMode = headerMode;
            context.importHeaderRowNumber = headerRowNumber;
            context.importColumnMappings = columnMappings;
            context.importDuplicatePolicy = duplicatePolicy;
            context.importDuplicateFieldKey = duplicateFieldKey;
            const importOutcome = await applyServiceRecordsImportWithRelaxedFallback({
                file: importFile,
                serviceCode,
                credentialMode,
                sheetName: selectedSheetName,
                headerMode,
                headerRowNumber,
                columnMappings,
                duplicatePolicy,
                duplicateFieldKey,
                feedback,
                setProgress: setServiceRecordsImportProgress,
            });
            if (importOutcome.cancelled) {
                return true;
            }
            const applied = importOutcome.applied;
            const relaxedImport = importOutcome.relaxed;
            setServiceRecordsImportProgress(85, "Rechargement des fiches...", true);
            invalidateAdminData(["services"]);
            await openNoCodeServiceRecords(serviceCode, { forceRefresh: true });
            setServiceRecordsImportProgress(100, "Import termine", true);
            const refreshedFeedback = document.getElementById("modal-service-records-feedback");
            if (refreshedFeedback) {
                refreshedFeedback.textContent = formatServiceRecordsImportResult(applied, { relaxed: relaxedImport });
            }
        } catch (error) {
            setServiceRecordsImportProgress(0, "", false);
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return true;
    }
    if (action === "service:record:add") {
        openNoCodeRecordEditor(null);
        return true;
    }
    if (action === "service:record:edit") {
        const recordId = String(actionButton.dataset.recordId || "").trim();
        const rows = Array.isArray(state.noCodeServiceRecordContext?.records) ? state.noCodeServiceRecordContext.records : [];
        const row = rows.find((item) => String(item?.id || "") === recordId) || null;
        if (row) {
            openNoCodeRecordEditor(row);
        }
        return true;
    }
    if (action === "service:record:view-edit") {
        await openLinkedRecordEditorFromViewer(actionButton.dataset.recordId || "");
        return true;
    }
    if (action === "service:record:delete") {
        const context = state.noCodeServiceRecordContext;
        const serviceCode = String(context?.service?.code || "").trim();
        const recordId = String(actionButton.dataset.recordId || "").trim();
        const recordVersionToken = String(actionButton.dataset.recordVersionToken || "").trim();
        if (!serviceCode || !recordId) {
            return true;
        }
        if (!(await showItopsConfirm({
            title: "Supprimer la fiche",
            message: "Supprimer cette fiche ?",
            confirmLabel: "Supprimer",
            danger: true,
        }))) {
            return true;
        }
        try {
            const path = recordVersionToken
                ? `/admin/custom-services/${encodeURIComponent(serviceCode)}/records/${encodeURIComponent(recordId)}?version_token=${encodeURIComponent(recordVersionToken)}`
                : `/admin/custom-services/${encodeURIComponent(serviceCode)}/records/${encodeURIComponent(recordId)}`;
            await requestJson(path, { method: "DELETE" });
            markModalImpactedViewsDirty(serviceCode);
            await openNoCodeServiceRecords(serviceCode);
            consumeModalServiceDirty(serviceCode);
        } catch (error) {
            const feedback = document.getElementById("modal-service-records-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return true;
    }
    if (action === "service:record:relation-open") {
        await openNoCodeRecordRelationLinksModal({
            serviceCode: state.noCodeServiceRecordContext?.service?.code,
            recordId: String(actionButton.dataset.recordId || state.noCodeRecordEditor?.recordId || ""),
            relationId: Number(actionButton.dataset.relationId || 0),
        });
        return true;
    }
    if (action === "service:record:credential-reveal") {
        const payload = await revealNoCodeRecordCredentialPassword({
            serviceCode: actionButton.dataset.serviceCode || state.noCodeServiceRecordContext?.service?.code,
            recordId: actionButton.dataset.recordId || state.noCodeRecordEditor?.recordId,
        });
        if (payload && !state.noCodeRecordEditor) {
            await showRevealedCredentialPassword(payload.device_password);
        }
        return true;
    }
    if (action === "service:record:view-credential-reveal") {
        await revealNoCodeRecordCredentialPassword({
            serviceCode: actionButton.dataset.serviceCode || state.noCodeServiceRecordContext?.service?.code,
            recordId: actionButton.dataset.recordId || state.noCodeRecordViewer?.record?.id,
        });
        renderLinkedNoCodeRecordViewModal();
        return true;
    }
    if (action === "service:relation-link:add") {
        const context = state.noCodeRelationLinksContext;
        const select = document.getElementById("service-relation-link-candidate");
        const feedback = document.getElementById("service-relation-links-feedback");
        const linkedRecordId = select instanceof HTMLSelectElement ? String(select.value || "").trim() : "";
        if (!context || !linkedRecordId) {
            if (feedback) {
                feedback.textContent = "Selectionnez une fiche a lier.";
            }
            return true;
        }
        try {
            await createNoCodeServiceRecordRelationLink(
                context.serviceCode,
                context.recordId,
                context.relationId,
                linkedRecordId,
            );
            markModalImpactedViewsDirty(context.serviceCode);
            await refreshNoCodeRelationLinksModal();
        } catch (error) {
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return true;
    }
    if (action === "service:relation-link:delete") {
        const context = state.noCodeRelationLinksContext;
        const linkedRecordId = String(actionButton.dataset.linkedRecordId || "").trim();
        if (!context || !linkedRecordId) {
            return true;
        }
        if (!(await showItopsConfirm({
            title: "Delier la fiche",
            message: "Retirer ce lien entre les deux fiches ?",
            confirmLabel: "Delier",
            danger: true,
        }))) {
            return true;
        }
        const feedback = document.getElementById("service-relation-links-feedback");
        try {
            await deleteNoCodeServiceRecordRelationLink(
                context.serviceCode,
                context.recordId,
                context.relationId,
                linkedRecordId,
            );
            markModalImpactedViewsDirty(context.serviceCode);
            await refreshNoCodeRelationLinksModal();
        } catch (error) {
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return true;
    }
    if (action === "service:relation-link:open") {
        const context = state.noCodeRelationLinksContext;
        const linkedRecordId = String(actionButton.dataset.linkedRecordId || "").trim();
        if (!context || !linkedRecordId) {
            return true;
        }
        const linkedServiceCode = String(context.linkedService?.code || "").trim().toLowerCase();
        await openNoCodeServiceRecords(linkedServiceCode);
        const row = findNoCodeServiceRecordInContext(state.noCodeServiceRecordContext, linkedRecordId);
        if (row) {
            openNoCodeRecordEditor(row);
        }
        return true;
    }
    if (action === "service:records:batch-delete") {
        await deleteSelectedNoCodeServiceRecords();
        return true;
    }
    if (action === "service:records:batch-relation-assign") {
        await openNoCodeBatchRelationAssignModal();
        return true;
    }
    if (action === "service:records:batch-field:cancel") {
        state.noCodeBatchFieldUpdate = null;
        closeModal();
        return true;
    }
    if (action === "service:records:back-services") {
        await openNoCodeServicesModal();
        return true;
    }
    if (action === "service:records:back") {
        if (await restoreNextModalBackSnapshot()) {
            return true;
        }
        const context = state.noCodeServiceRecordContext;
        if (context?.service?.code) {
            const systemEntity = findNoCodeRelationSystemEntity(context.service.code);
            if (systemEntity) {
                await openDirectoryModuleFromPortal(systemEntity.code === "services" ? "services" : "agents");
                return true;
            }
            if (context.isLinkedRecordViewContext) {
                context.recordsPage = {};
                context.records = [];
                context.searchQuery = "";
            }
            await openNoCodeServiceRecords(String(context.service.code || ""));
        } else {
            await openNoCodeServicesModal();
        }
        return true;
    }
    if (action === "service:records:filters:clear") {
        const context = state.noCodeServiceRecordContext;
        if (context) {
            clearNoCodeServiceRecordsFilters(context);
            await reloadNoCodeServiceRecordsPage(context, { offset: 0 });
            renderNoCodeServiceRecordsModal();
        }
        return true;
    }
    if (action === "service:child:add") {
        syncNoCodeRecordChildrenFromDom();
        if (!state.noCodeRecordEditor) {
            return true;
        }
        state.noCodeRecordEditor.children = [...(state.noCodeRecordEditor.children || []), { name: "", code: "" }];
        updateNoCodeRecordChildRows();
        return true;
    }
    if (action === "service:child:remove") {
        syncNoCodeRecordChildrenFromDom();
        if (!state.noCodeRecordEditor) {
            return true;
        }
        const index = Number(actionButton.dataset.childIndex || -1);
        if (Number.isInteger(index) && index >= 0) {
            state.noCodeRecordEditor.children = (state.noCodeRecordEditor.children || []).filter((_, rowIndex) => rowIndex !== index);
            updateNoCodeRecordChildRows();
        }
        return true;
    }
    return false;
}

async function handleNoCodeModalSubmit(form) {
    if (!(form instanceof HTMLFormElement)) {
        return false;
    }
    if (form.id === "modal-relation-assignment-form") {
        const feedback = document.getElementById("modal-relation-assignment-feedback");
        const createContext = state.relationAssignmentCreate;
        const originalContext = state.noCodeServiceRecordContext;
        const originalEditor = state.noCodeRecordEditor;
        const formData = new window.FormData(form);
        const primaryValue = normalizeNoCodeText(formData.get("assignment_primary_value"));
        const beneficiaryId = String(formData.get("assignment_beneficiary") || "").trim();
        if (!primaryValue || !beneficiaryId || !createContext?.ownerId) {
            if (feedback) {
                feedback.textContent = "Valeur et element lie requis.";
            }
            return true;
        }
        try {
            const freshAssignments = originalContext && originalEditor
                ? await buildRecordAssignment(originalContext, originalEditor)
                : null;
            if (!freshAssignments?.ownerRelationId || !freshAssignments?.beneficiaryRelationId) {
                throw new Error("La configuration de l'attribution a change. Fermez puis rouvrez la fiche.");
            }
            createContext.assignments = freshAssignments;
            const resourceService = freshAssignments.resourceService || { fields: [] };
            const primaryField = noCodeCustomServiceFields(resourceService)[0] || { field_key: "value" };
            const values = { [String(primaryField.field_key || "value")]: primaryValue };
            noCodeCustomServiceFields(resourceService).forEach((field) => {
                const key = String(field?.field_key || "").trim();
                if (!key || key.toLowerCase() === String(primaryField.field_key || "").toLowerCase()) {
                    return;
                }
                values[key] = normalizeNoCodeText(formData.get(`assignment_field_${key}`) ?? field?.default_value ?? "");
            });
            await requestJson(`/admin/custom-services/${encodeURIComponent(freshAssignments.resourceCode)}/records`, {
                method: "POST",
                body: JSON.stringify({
                    values,
                    relation_links: {
                        [String(freshAssignments.ownerRelationId)]: [String(createContext.ownerId)],
                        [String(freshAssignments.beneficiaryRelationId)]: [beneficiaryId],
                    },
                }),
            });
            state.relationAssignmentCreate = null;
            if (originalContext?.service && originalEditor) {
                originalEditor.recordAssignment = null;
                await reopenRecordAssignmentOwnerEditor(originalContext, originalEditor);
            }
        } catch (error) {
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return true;
    }
    if (form.id === "modal-relation-guide-form") {
        const feedback = document.getElementById("modal-relation-guide-feedback");
        const editor = state.noCodeServiceEditor;
        const formData = new window.FormData(form);
        const hasRelation = String(formData.get("relationship_guide_has_relation") || "yes") !== "no";
        const beneficiaryCode = normalizeNoCodeRelationEntityCode(formData.get("relationship_guide_related") || "");
        const relationshipKind = String(formData.get("relationship_guide_kind") || "simple") === "assignment" ? "assignment" : "simple";
        const resourceCode = normalizeNoCodeRelationEntityCode(formData.get("relationship_guide_resource") || "");
        const label = normalizeNoCodeText(formData.get("relationship_guide_label"));
        const uniqueFieldKey = String(formData.get("relationship_guide_unique_value") || "no") === "yes"
            ? normalizeNoCodeText(formData.get("relationship_guide_unique_field")).toLowerCase()
            : "";
        const ownerCode = noCodeRelationCurrentServiceCode(editor);
        const beneficiaryService = findNoCodeRelationEntity(beneficiaryCode);
        const resourceService = findNoCodeService(resourceCode);
        if (!editor || !ownerCode) {
            return true;
        }
        if (!hasRelation) {
            state.noCodeRelationGuide = null;
            editor.relationScenarioFeedback = "Aucune relation n'a ete ajoutee. Vous pourrez relancer l'assistant plus tard.";
            returnToNoCodeServiceRelationsEditor();
            return true;
        }
        if (!beneficiaryService || beneficiaryCode === ownerCode || (relationshipKind === "assignment" && !resourceService)) {
            if (feedback) {
                feedback.textContent = relationshipKind === "assignment"
                    ? "Choisissez le type d'element lie et l'element a attribuer."
                    : "Choisissez le type d'element lie.";
            }
            return true;
        }
        editor.relationDrafts = Array.isArray(editor.relationDrafts) ? editor.relationDrafts : [];
        let relation = editor.relationDrafts.find((item) =>
            String(item?.source_service_code || "").trim().toLowerCase() === ownerCode
            && normalizeNoCodeRelationEntityCode(item?.target_service_code || item?.service_code || "") === beneficiaryCode,
        );
        if (!relation) {
            relation = createNoCodeRelationDraft(beneficiaryService, editor.relationDrafts.length, ownerCode);
            editor.relationDrafts.push(relation);
        }
        const cardinality = noCodeRelationGuideCardinality(
            String(formData.get("relationship_guide_owner_many") || "yes") === "yes",
            String(formData.get("relationship_guide_related_many") || "yes") === "yes",
        );
        relation.cardinality = cardinality;
        relation.relation_type = cardinality;
        relation.direction = "out";
        relation.display_label = label || String(beneficiaryService.label || beneficiaryCode);
        relation.label = relation.display_label;
        relation.required = String(formData.get("relationship_guide_owner_without_related") || "yes") === "no";
        relation.record_display_mode = relationshipKind === "assignment" ? "assignment" : "standard";
        relation.assignment_resource_service_code = relationshipKind === "assignment" ? resourceCode : "";
        try {
            if (relationshipKind === "assignment") {
                await prepareNoCodeRelationAssignment(editor, relation, {
                    uniqueFieldKey,
                    resourceOwnerCardinality: String(formData.get("relationship_guide_resource_owner_single") || "yes") === "yes" ? "many_to_one" : "many_to_many",
                    resourceBeneficiaryCardinality: String(formData.get("relationship_guide_resource_related_many") || "no") === "yes" ? "many_to_many" : "many_to_one",
                });
            }
            editor.selectedRelationId = noCodeRelationId(relation, editor.relationDrafts.indexOf(relation));
            editor.selectedRelationServiceCode = beneficiaryCode;
            editor.relationScenarioFeedback = relationshipKind === "assignment"
                ? "Attribution preparee. Enregistrez le module pour terminer la configuration."
                : "Relation preparee. Enregistrez le module pour terminer la configuration.";
            state.noCodeRelationGuide = null;
            openModal("Service - Edition", buildNoCodeServiceEditorMarkup(), noCodeInlineOptions("min(1180px, calc(100vw - 32px))", { inline: true }));
        } catch (error) {
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return true;
    }
    if (form.id === "modal-service-form") {
        const feedback = document.getElementById("modal-service-form-feedback");
        if (feedback) {
            feedback.textContent = "";
        }
        const editor = state.noCodeServiceEditor;
        if (!editor) {
            return true;
        }
        const wasCreatingService = editor.mode !== "edit";
        const editorReturnContext = state.noCodeServiceEditorContext;
        syncNoCodeServiceEditorFromForm(form);
        if (editor.importPreview && Array.isArray(editor.importPreview.fields) && editor.importPreview.fields.length) {
            if (feedback) {
                feedback.textContent = "Un apercu d'import est en attente. Appliquez ou ignorez l'import avant d'enregistrer.";
            }
            return true;
        }
        const label = normalizeNoCodeText(editor.label);
        if (!label) {
            if (feedback) {
                feedback.textContent = "Nom du service requis.";
            }
            editor.wizardStep = 1;
            renderNoCodeServiceEditorShell();
            const refreshedFeedback = document.getElementById("modal-service-form-feedback");
            if (refreshedFeedback) {
                refreshedFeedback.textContent = "Nom du service requis.";
            }
            return true;
        }
        const childEnabled = Boolean(editor.child_enabled);
        const childLabel = childEnabled
            ? (normalizeNoCodeText(editor.child_label) || "Elements lies")
            : "Elements lies";
        const normalizedServiceCode = String(editor.code || slugifyNoCodeIdentifier(label, "service")).trim().toLowerCase();
        if (isReservedSystemEntityCode(normalizedServiceCode)) {
            if (feedback) {
                feedback.textContent = "Nom reserve: utilisez le module systeme dedie, pas un service personnalise.";
            }
            editor.wizardStep = 1;
            renderNoCodeServiceEditorShell();
            const refreshedFeedback = document.getElementById("modal-service-form-feedback");
            if (refreshedFeedback) {
                refreshedFeedback.textContent = "Nom reserve: utilisez le module systeme dedie, pas un service personnalise.";
            }
            return true;
        }
        const credentialsWasEnabled = Boolean(editor.initial_credentials_enabled);
        const credentialsWillBeEnabled = Boolean(editor.credentials_enabled);
        let purgeStoredCredentials = false;
        if (editor.mode === "edit" && credentialsWasEnabled && !credentialsWillBeEnabled && normalizedServiceCode) {
            try {
                const rows = await requestJson(`/admin/custom-services/${encodeURIComponent(normalizedServiceCode)}/records`);
                const hasStoredCredentials = (Array.isArray(rows) ? rows : []).some((row) => noCodeRecordHasCredentialValues(row));
                if (hasStoredCredentials) {
                    purgeStoredCredentials = await showItopsConfirm({
                        title: "Identifiants enregistres",
                        message: "Des identifiants sont deja enregistres pour ce service.",
                        details: ["Confirmer: supprimer definitivement ces identifiants.", "Annuler: conserver les identifiants masques tant que la gestion est desactivee."],
                        confirmLabel: "Supprimer les identifiants",
                        cancelLabel: "Conserver",
                        danger: true,
                    });
                }
            } catch (_error) {
                // Si le controle echoue, on continue la sauvegarde sans purge.
            }
        }
        const payload = {
            code: normalizedServiceCode,
            label,
            is_active: Boolean(editor.is_technical || editor.is_active),
            is_technical: Boolean(editor.is_technical),
            credentials_enabled: Boolean(editor.credentials_enabled),
            child_enabled: childEnabled,
            child_label: childLabel,
            sort_order: Number(editor.sort_order || 100),
            icon: String(editor.icon || "").trim().toLowerCase(),
            color: sanitizeServiceIconColor(editor.color || ""),
            tile_config: {
                show_count: editor.tile_config?.show_count !== false,
                remote_access: editor.tile_config?.remote_access && typeof editor.tile_config.remote_access === "object"
                    ? { ...editor.tile_config.remote_access }
                    : {},
            },
            version_token: String(editor.version_token || ""),
            fields: (editor.fields || [])
                .filter((row) => !isNoCodeCredentialFieldKey(row?.field_key))
                .map((row, index) => ({
                ...row,
                sort_order: (index + 1) * 10,
                list_source_kind: normalizeListSourceKind(row?.list_source_kind || "local"),
                shared_list_code: String(row?.shared_list_code || "").trim().toLowerCase(),
            })),
        };
        try {
            await requestJson(
                editor.mode === "edit"
                    ? `/admin/custom-services/${encodeURIComponent(String(editor.code || payload.code))}`
                    : "/admin/custom-services",
                {
                    method: editor.mode === "edit" ? "PUT" : "POST",
                    body: JSON.stringify(payload),
                },
            );
            let relationsMessage = "";
            const relationPayloads = noCodeRelationApiPayloads(editor);
            try {
                let savedRelations;
                try {
                    savedRelations = await replaceNoCodeServiceRelations(payload.code, relationPayloads);
                } catch (relationError) {
                    const confirmed = await confirmNoCodeLinkedRelationsDeletion(payload.code, relationError);
                    if (!confirmed) {
                        throw relationError;
                    }
                    savedRelations = await replaceNoCodeServiceRelations(payload.code, relationPayloads, {
                        allowLinkedRelationDeletion: true,
                    });
                }
                if (relationPayloads.length || savedRelations.length) {
                    relationsMessage = ` Relations: ${savedRelations.length} enregistree(s).`;
                }
            } catch (relationError) {
                throw new Error(`Service enregistre, mais relations non enregistrees: ${normalizeErrorMessage(relationError.message)}`);
            }
            let recordsImportMessage = "";
            const appliedImport = editor.appliedImportForRecords;
            if (appliedImport?.file && editor.importRecordsEnabled !== false) {
                const recordMappings = buildRecordMappingsFromAppliedServiceFieldImport(appliedImport);
                if (recordMappings.length) {
                    const importOutcome = await applyServiceRecordsImportWithRelaxedFallback({
                        file: appliedImport.file,
                        serviceCode: payload.code,
                        credentialMode: "preserve_on_blank",
                        sheetName: appliedImport.sheetName || "",
                        headerMode: appliedImport.headerMode || "auto",
                        headerRowNumber: appliedImport.headerRowNumber || 1,
                        columnMappings: recordMappings,
                        importUntilRowNumber: appliedImport.importUntilRowNumber || 0,
                        feedback,
                    });
                    const importedRecords = importOutcome.applied;
                    recordsImportMessage = ` Donnees importees: ${importedRecords.created} creee(s), ${importedRecords.updated} mise(s) a jour.${importedRecords.skipped ? ` ${importedRecords.skipped} ignoree(s).` : ""}${importOutcome.relaxed ? " Import force applique." : ""}`;
                    if (importOutcome.cancelled) {
                        recordsImportMessage = ` Donnees non importees: ${importedRecords.skipped} ligne(s) ignoree(s).`;
                    }
                }
            }
            const appliedActiveDirectoryImport = editor.appliedActiveDirectoryImportForRecords;
            if (appliedActiveDirectoryImport && editor.importRecordsEnabled !== false) {
                try {
                    const importOutcome = await applyServiceRecordsImportFromActiveDirectoryWithRelaxedFallback(payload.code, appliedActiveDirectoryImport);
                    const importedRecords = importOutcome.applied || {};
                    recordsImportMessage += ` Donnees AD importees: ${Number(importedRecords.created || 0)} creee(s), ${Number(importedRecords.updated || 0)} mise(s) a jour.${Number(importedRecords.skipped || 0) ? ` ${Number(importedRecords.skipped || 0)} ignoree(s).` : ""}${importOutcome.relaxed ? " Import force applique." : ""}`;
                    if (Array.isArray(importedRecords.issues) && importedRecords.issues.length) {
                        recordsImportMessage += ` A verifier: ${importedRecords.issues.slice(0, 2).map((item) => String(item || "").trim()).filter(Boolean).join(" ")}`;
                    }
                    editor.appliedActiveDirectoryImportForRecords = null;
                } catch (adImportError) {
                    recordsImportMessage += ` Donnees AD non importees: ${normalizeErrorMessage(adImportError.message)}`;
                }
            }
            if (editor.mode === "edit" && purgeStoredCredentials && normalizedServiceCode) {
                await requestJson(`/admin/custom-services/${encodeURIComponent(normalizedServiceCode)}/credentials/purge`, {
                    method: "POST",
                });
            }
            state.moduleAccessLoaded = false;
            invalidateAdminData(["services", "modules"]);
            let portalRefreshWarning = "";
            try {
                await loadPortalModules({ forceRefresh: true });
            } catch (refreshError) {
                portalRefreshWarning = normalizeErrorMessage(refreshError.message);
            }
            if (wasCreatingService && await showItopsConfirm({
                title: "Module cree",
                message: `Le module ${payload.label || payload.code} est pret. Voulez-vous decrire maintenant ses relations avec l'assistant ?`,
                details: ["Vous repondrez a des questions metier. Les reglages techniques resteront disponibles plus tard si besoin."],
                confirmLabel: "Configurer les relations",
                cancelLabel: "Plus tard",
            })) {
                await openNoCodeServiceEditor({ ...payload, code: payload.code }, { context: editorReturnContext });
                state.noCodeServiceEditor.wizardStep = 3;
                openNoCodeRelationGuide();
                return true;
            }
            await returnToNoCodeServiceEditorCaller(
                `Service ${payload.label || payload.code} enregistre.${relationsMessage}${recordsImportMessage}${portalRefreshWarning ? ` Rafraichissement portail: ${portalRefreshWarning}` : ""}`,
            );
        } catch (error) {
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return true;
    }
    if (form.id === "modal-service-record-form") {
        const feedback = document.getElementById("modal-service-record-feedback");
        if (feedback) {
            feedback.textContent = "";
        }
        const context = state.noCodeServiceRecordContext;
        const editor = state.noCodeRecordEditor;
        if (!context || !editor || !context.service) {
            return true;
        }
        let service = context.service;
        const fields = noCodeCustomServiceFields(service);
        const formData = new window.FormData(form);
        const values = {};
        const relationSelections = readNoCodeRecordRelationSelectionsFromDom();
        if (!validateRecordRelationSelectionLimits(feedback) || !validateRequiredRecordRelationSelections(context, editor, relationSelections, feedback)) {
            return true;
        }
        for (const field of fields) {
            const key = String(field.field_key || "").trim();
            values[key] = normalizeNoCodeText(formData.get(`record_field_${key}`));
        }
        if (Boolean(service?.credentials_enabled)) {
            if (String(service?.code || "").trim().toLowerCase() !== "emails") {
                values[NO_CODE_CREDENTIAL_LOGIN_KEY] = normalizeNoCodeText(formData.get("record_credential_login"));
            }
            const credentialPassword = String(formData.get("record_credential_password") ?? "");
            if (credentialPassword) {
                values[NO_CODE_CREDENTIAL_PASSWORD_KEY] = credentialPassword;
            }
        }
        const previousStatus = editor.mode === "edit" ? String(editor.values?.status || "") : "";
        const reminderDueAt = await resolveEmailDeleteReminderDueDate(service, "status", values.status, previousStatus);
        if (isEmailDeleteReminderTrigger(service, "status", values.status) && String(previousStatus || "").trim().toLowerCase() !== "a supprimer" && !reminderDueAt) {
            if (feedback) {
                feedback.textContent = "Date de rappel requise pour passer un Email a supprimer.";
            }
            return true;
        }
        syncNoCodeRecordChildrenFromDom();
        const children = Array.isArray(editor.children) ? editor.children : [];
        const trackedChanges = editor.mode === "edit"
            ? noCodeTrackedRecordChanges(service, editor.recordId, values)
            : [];
        let historyDecision = { decision: "none", changedAt: "" };
        if (trackedChanges.length) {
            historyDecision = await confirmNoCodeTrackedRecordChanges(trackedChanges);
            if (noCodeHistoryDecisionKind(historyDecision) === "cancel") {
                if (feedback) {
                    feedback.textContent = "Enregistrement annule.";
                }
                return true;
            }
        }
        const payload = {
            values,
            children: children.map((row, index) => ({
                name: normalizeNoCodeText(row.name),
                code: normalizeNoCodeText(row.code),
                sort_order: (index + 1) * 10,
            })),
            confirm_history_changes: trackedChanges.length > 0 && noCodeHistoryDecisionKind(historyDecision) === "history",
            skip_history_changes: trackedChanges.length > 0 && noCodeHistoryDecisionKind(historyDecision) === "skip",
            history_changed_at: noCodeHistoryDecisionChangedAt(historyDecision),
            reminder_due_at: reminderDueAt,
            relation_links: editor.mode === "edit" ? {} : relationSelections,
            version_token: String(editor.versionToken || ""),
        };
        try {
            const saveRecord = () => requestJson(
                editor.mode === "edit"
                    ? `/admin/custom-services/${encodeURIComponent(String(service.code || ""))}/records/${encodeURIComponent(String(editor.recordId || ""))}`
                    : `/admin/custom-services/${encodeURIComponent(String(service.code || ""))}/records`,
                {
                    method: editor.mode === "edit" ? "PUT" : "POST",
                    body: JSON.stringify(payload),
                },
            );
            let savedRecord;
            try {
                savedRecord = await saveRecord();
            } catch (error) {
                if (!isNoCodeServiceNotFoundError(error)) {
                    throw error;
                }
                service = await refreshNoCodeServiceForRecordSave(service);
                context.service = service;
                savedRecord = await saveRecord();
            }
            const savedRecordId = String(savedRecord?.id || editor.recordId || "").trim();
            let relationResult = { created: 0, deleted: 0 };
            if (savedRecordId) {
                relationResult = await syncNoCodeRecordRelationSelections({
                    serviceCode: String(service.code || ""),
                    recordId: savedRecordId,
                    selections: relationSelections,
                    editor,
                    context: state.noCodeServiceRecordContext,
                });
            }
            if (savedRecord && savedRecordId) {
                rememberLinkedRecordViewCache(String(service.code || ""), savedRecord);
            }
            if (savedRecordId || Number(relationResult?.created || 0) || Number(relationResult?.deleted || 0)) {
                markModalImpactedViewsDirty(String(service.code || ""));
            }
            const restoredCaller = await restoreNextModalBackSnapshot((snapshot) => {
                if (snapshot?.type === "service-record-view" && savedRecord) {
                    snapshot.noCodeRecordViewer = {
                        ...(snapshot.noCodeRecordViewer || {}),
                        record: savedRecord,
                    };
                }
            });
            if (!restoredCaller) {
                await openNoCodeServiceRecords(String(service.code || ""));
                consumeModalServiceDirty(String(service.code || ""));
            }
            const relationChanges = Number(relationResult?.created || 0) + Number(relationResult?.deleted || 0);
            showAppSaveFeedback({
                feedbackId: restoredCaller ? "modal-service-record-feedback" : "modal-service-records-feedback",
                message: editor.mode === "edit"
                    ? `Fiche mise a jour${relationChanges ? `, relations: ${Number(relationResult.created || 0)} ajoutee(s), ${Number(relationResult.deleted || 0)} retiree(s)` : ""}.`
                    : "Fiche creee.",
            });
        } catch (error) {
            showAppSaveFeedback({
                feedback,
                kind: "error",
                message: normalizeErrorMessage(error.message),
                durationMs: 4200,
            });
        }
        return true;
    }
    return false;
}

async function openRolesModal(options = {}) {
    await loadAdministrationData({ includeModules: true, includeRoles: true, includeUsers: false });
    openModal("Administration - Roles", buildRolesModalMarkup(), adminInlineOptions("min(1120px, calc(100vw - 40px))", options));
    renderRolesTreeView();
}

async function openUsersModal(options = {}) {
    await loadAdministrationData({ includeModules: false, includeRoles: true, includeUsers: true });
    openModal("Administration - Comptes applicatifs", buildUsersModalMarkup(), adminInlineOptions("min(1120px, calc(100vw - 40px))", options));
    renderUsersTreeView();
}

async function boot() {
    if (state.token) {
        authScreen.hidden = true;
        authScreen.style.display = "none";
        const sessionOk = await restoreSession();
        if (sessionOk) {
            showPortal();
            Promise.all([
                loadPrivateUiConfig(),
                loadPortalModules(),
            ])
                .then(() => consumeServiceHashNavigation())
                .catch(() => {
                });
            return;
        }
    }

    const mode = await loadAuthMode();
    if (mode?.mustChangePassword) {
        persistToken("");
        clearSessionState();
        showAuth();
        return;
    }
    const sessionOk = await restoreSession();
    if (!sessionOk) {
        showAuth();
        return;
    }
    showPortal();
    Promise.all([
        loadPrivateUiConfig(),
        loadPortalModules(),
    ])
        .then(() => consumeServiceHashNavigation())
        .catch(() => {
        });
}

authForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    setError("");
    authSubmit.disabled = true;
    try {
        const mode = String(authForm.dataset.mode || "login");
        if (mode === "bootstrap") {
            if (!String(newPasswordInput.value || "").trim()) {
                setError("Nouveau mot de passe requis.");
                return;
            }
            if (!String(confirmPasswordInput.value || "").trim()) {
                setError("Confirmation du mot de passe requise.");
                return;
            }
            if (String(newPasswordInput.value || "") !== String(confirmPasswordInput.value || "")) {
                setError("La confirmation du nouveau mot de passe ne correspond pas.");
                return;
            }
            await bootstrapAndLogin(newPasswordInput.value);
        } else {
            if (!String(usernameInput.value || "").trim()) {
                setError("Identifiant requis.");
                return;
            }
            if (!String(passwordInput.value || "").trim()) {
                setError("Mot de passe requis.");
                return;
            }
            if (String(authForm.dataset.forcePasswordChange || "") === "1") {
                if (!String(newPasswordInput.value || "").trim()) {
                    setError("Nouveau mot de passe requis.");
                    return;
                }
                if (!String(confirmPasswordInput.value || "").trim()) {
                    setError("Confirmation du mot de passe requise.");
                    return;
                }
                if (String(newPasswordInput.value || "") !== String(confirmPasswordInput.value || "")) {
                    setError("La confirmation du nouveau mot de passe ne correspond pas.");
                    return;
                }
            }
            await authenticate(usernameInput.value, passwordInput.value, newPasswordInput.value);
        }
        passwordInput.value = "";
        newPasswordInput.value = "";
        confirmPasswordInput.value = "";
        const sessionOk = await restoreSession();
        if (!sessionOk) {
            throw new Error("Session invalide ou expiree.");
        }
        state.moduleAccessLoaded = false;
        invalidateAdminData();
        showPortal();
        Promise.all([
            loadPrivateUiConfig(),
            loadPortalModules({ forceRefresh: true }),
        ])
            .then(() => consumeServiceHashNavigation())
            .catch(() => {
            });
    } catch (error) {
        persistToken("");
        clearSessionState();
        invalidateAdminData();
        const message = normalizeErrorMessage(error.message);
        if (String(message).toLowerCase().includes("changement du mot de passe requis")) {
            enablePasswordChangeMode();
            setError("Premiere connexion: renseigne un nouveau mot de passe.");
        } else {
            setError(message);
        }
        if (String(authForm.dataset.forcePasswordChange || "") !== "1") {
            await loadAuthMode();
        }
        showAuth();
    } finally {
        authSubmit.disabled = false;
    }
});

initProfileMenu();
refreshButton?.addEventListener("click", async () => {
    await loadPortalModules({ forceRefresh: true });
});
portalSyncBadge?.addEventListener("click", async () => {
    if (portalSyncBadge instanceof HTMLButtonElement && !portalSyncBadge.disabled) {
        await runActiveDirectoryManualSync({ trigger: portalSyncBadge });
    }
});

portalMenuButtons.forEach((button) => {
    button.addEventListener("click", () => {
        const menuKey = String(button.dataset.menuKey || "").trim();
        if (menuKey) {
            openTopMenu(button, menuKey);
        }
    });
});
cardsGrid.addEventListener("click", handleModuleCardsClick);
cardsGrid.addEventListener("contextmenu", async (event) => {
    const target = event.target;
    if (!(target instanceof Element)) {
        return;
    }
    const card = target.closest("[data-module-code]");
    if (!(card instanceof HTMLElement)) {
        return;
    }
    const moduleCode = String(card.dataset.moduleCode || "").trim().toLowerCase();
    const moduleRow = findPortalModuleByCode(moduleCode);
    if (!moduleRow) {
        return;
    }
    event.preventDefault();
    closeTopMenu();
    closeCardsContextMenu();
    const isMonitoring = isMonitoringPortalModule(moduleRow);
    if (isMonitoring) {
        state.monitoringSummaryLoaded = false;
        await loadPortalMonitoringSummary({ forceRefresh: true });
    }
    openPortalCardsContextMenu(event.clientX, event.clientY, moduleRow);
});

if (cardsContextMenu instanceof HTMLElement) {
    cardsContextMenu.addEventListener("click", async (event) => {
        const target = event.target;
        if (!(target instanceof Element)) {
            return;
        }
        const button = target.closest("[data-action]");
        if (!(button instanceof HTMLButtonElement) || button.disabled) {
            return;
        }
        const action = String(button.dataset.action || "");
        const relationContextNodeCode = String(state.noCodeRelationContextNodeCode || "").trim().toLowerCase();
        const contextModuleRow = findPortalModuleByCode(state.portalContextModuleCode);
        closeCardsContextMenu();
        try {
            if (action === "service:relation-node:delete") {
                state.noCodeRelationContextNodeCode = relationContextNodeCode;
                await deleteNoCodeRelationContextNode();
                state.noCodeRelationContextNodeCode = "";
                return;
            }
            if (action === "service:records:batch-delete") {
                await deleteSelectedNoCodeServiceRecords();
                return;
            }
            if (action === "service:records:batch-relation-assign") {
                await openNoCodeBatchRelationAssignModal();
                return;
            }
            if (action === "service:records:relation-open") {
                await openNoCodeRecordRelationLinksModal({
                    serviceCode: state.noCodeServiceRecordContext?.service?.code,
                    recordId: String(button.dataset.recordId || ""),
                    relationId: Number(button.dataset.relationId || 0),
                });
                return;
            }
            if (action === "directory:record:relation-open") {
                await openDirectoryRecordRelationLinks(
                    String(button.dataset.recordId || ""),
                    Number(button.dataset.relationId || 0),
                );
                return;
            }
            if (action === "directory:record:edit") {
                await openDirectoryRecordEditor(String(button.dataset.recordId || ""));
                return;
            }
            if (action === "directory:batch:relation-assign") {
                await openDirectoryBatchRelationAssignModal();
                return;
            }
            await handlePortalCardsContextMenuAction(action, contextModuleRow);
        } catch (error) {
            openModal("Action indisponible", `<p class="muted">${escapeHtml(normalizeErrorMessage(error.message))}</p>`);
        }
    });
}

topMenuPanel.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action]");
    if (!button || button.disabled) {
        return;
    }
    const action = String(button.dataset.action || "");
    closeTopMenu();
    try {
        const commonMenuActions = window.NMPSharedMenu?.buildCommonActions?.({
            navigatePortal: () => window.location.assign("/"),
            openWebServerSettingsModal,
            downloadHttpsRootCertificate,
            openModal,
            escapeHtml,
            normalizeErrorMessage,
            applySettingsPatch,
            getAppVersionText: () => String(document.getElementById("app-version").textContent || "-"),
            aboutText: "Portail mutualise des modules IT.",
        }) || {};
        const handler = commonMenuActions[action];
        if (handler) {
            await handler();
            return;
        }
        if (action === "menu:active-module:portal") {
            closeModal();
            return;
        }
        if (action === "menu:active-module:refresh") {
            await refreshActiveModuleData();
            return;
        }
        if (action.startsWith("menu:active-module:data:")) {
            if (!await runActiveModuleDataAction(action)) {
                throw new Error("Cette action n'est pas disponible pour ce module.");
            }
            return;
        }
        if (action.startsWith("menu:active-module:open:")) {
            const moduleCode = decodeURIComponent(action.slice("menu:active-module:open:".length) || "").trim().toLowerCase();
            const moduleRow = findPortalModuleByCode(moduleCode);
            if (!moduleRow) {
                throw new Error("Module introuvable.");
            }
            await openPortalModuleCard(moduleRow);
            return;
        }
        if (action === "menu:admin:roles") {
            await openRolesModal({ inline: true });
            return;
        }
        if (action === "menu:admin:users") {
            await openUsersModal({ inline: true });
            return;
        }
        if (action === "menu:services:manage") {
            await openNoCodeServicesModal({ inline: true });
            return;
        }
        if (action === "menu:services:add") {
            await loadAdministrationData({
                includeModules: false,
                includeRoles: false,
                includeUsers: false,
                includeServices: true,
                includeSharedLists: true,
            });
            await openNoCodeServiceEditor(null, { inline: true });
            return;
        }
        if (action === "menu:services:shared-lists") {
            await openSharedListsModal({ inline: true });
            return;
        }
        if (action === "menu:notifications" || action === "menu:notifications:settings") {
            await openNotificationSettingsModal();
            return;
        }
        if (action === "menu:notifications:tasks") {
            await openNotificationTasksModal();
            return;
        }
        if (action === "menu:notifications:templates") {
            await openNotificationTemplatesModal();
            return;
        }
        if (action === "menu:sync:active-directory") {
            await openActiveDirectorySettingsModal();
            return;
        }
        if (action === "menu:watermark:import") {
            await openWatermarkEditorModal({ forceImport: true });
            return;
        }
        if (action === "menu:watermark:edit") {
            await openWatermarkEditorModal({ forceImport: false });
            return;
        }
        if (action === "menu:storage:files") {
            await openStorageFilesModal();
            return;
        }
        if (action === "menu:database:backup") {
            await downloadDatabaseBackup();
            return;
        }
        if (action === "menu:database:import") {
            openDatabaseImportModal();
            return;
        }
    } catch (error) {
        openModal(
            "Action indisponible",
            `<p class="error-text">${escapeHtml(normalizeErrorMessage(error.message))}</p>`,
            { width: "min(560px, calc(100vw - 40px))" },
        );
    }
});

appModalBody.addEventListener("pointerdown", (event) => {
    beginNoCodeRelationNodeDrag(event);
});

appModalBody.addEventListener("contextmenu", async (event) => {
    const node = event.target instanceof Element ? event.target.closest("[data-relation-node]") : null;
    if (!(node instanceof HTMLElement)) {
        return;
    }
    const editor = state.noCodeServiceEditor;
    const serviceCode = normalizeNoCodeRelationEntityCode(node.dataset.relationNode || node.dataset.serviceCode || "");
    if (!editor || !serviceCode || serviceCode === noCodeRelationCurrentServiceCode(editor)) {
        return;
    }
    event.preventDefault();
    openNoCodeRelationNodeContextMenu(event.clientX, event.clientY, serviceCode);
});

appModalBody.addEventListener("dragstart", (event) => {
    const target = event.target instanceof Element ? event.target.closest(".no-code-relation-service-option") : null;
    if (!(target instanceof HTMLElement) || !event.dataTransfer) {
        return;
    }
    event.dataTransfer.setData("text/no-code-service", normalizeNoCodeRelationEntityCode(target.dataset.serviceCode || ""));
    event.dataTransfer.effectAllowed = "copy";
});

appModalBody.addEventListener("dragover", (event) => {
    const target = event.target instanceof Element ? event.target.closest(".no-code-relations-canvas") : null;
    if (!(target instanceof HTMLElement) || !event.dataTransfer) {
        return;
    }
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
});

appModalBody.addEventListener("drop", (event) => {
    const target = event.target instanceof Element ? event.target.closest(".no-code-relations-canvas") : null;
    if (!(target instanceof HTMLElement) || !event.dataTransfer) {
        return;
    }
    const serviceCode = event.dataTransfer.getData("text/no-code-service");
    if (!serviceCode) {
        return;
    }
    event.preventDefault();
    addNoCodeRelationCanvasNodeAt(serviceCode, event.clientX, event.clientY);
});

appModalBody.addEventListener("dblclick", async (event) => {
    const row = event.target instanceof Element ? event.target.closest("[data-assignment-beneficiary-row]") : null;
    if (!(row instanceof HTMLElement)) {
        return;
    }
    if (state.relationAssignmentPicker?.batchMode) {
        return;
    }
    event.preventDefault();
    const feedback = document.getElementById("modal-relation-assignment-picker-feedback");
    try {
        await linkRecordAssignmentBeneficiary(String(row.dataset.recordId || ""));
    } catch (error) {
        if (feedback instanceof HTMLElement) {
            feedback.textContent = normalizeErrorMessage(error.message);
        }
    }
});

appModalBody.addEventListener("change", async (event) => {
    const select = event.target;
    if (select instanceof HTMLSelectElement && select.name.startsWith("relationship_guide_")) {
        const wizard = state.noCodeRelationGuide || {};
        const form = select.closest("form");
        const formData = form instanceof HTMLFormElement ? new window.FormData(form) : new window.FormData();
        state.noCodeRelationGuide = {
            ...wizard,
            hasRelation: String(formData.get("relationship_guide_has_relation") || wizard.hasRelation || "yes"),
            relatedCode: String(formData.get("relationship_guide_related") || wizard.relatedCode || ""),
            relationshipKind: String(formData.get("relationship_guide_kind") || wizard.relationshipKind || "simple"),
            ownerMany: String(formData.get("relationship_guide_owner_many") || wizard.ownerMany || "yes"),
            relatedMany: String(formData.get("relationship_guide_related_many") || wizard.relatedMany || "yes"),
            ownerWithoutRelated: String(formData.get("relationship_guide_owner_without_related") || wizard.ownerWithoutRelated || "yes"),
            resourceCode: String(formData.get("relationship_guide_resource") || wizard.resourceCode || ""),
            resourceOwnerSingle: String(formData.get("relationship_guide_resource_owner_single") || wizard.resourceOwnerSingle || "yes"),
            resourceRelatedMany: String(formData.get("relationship_guide_resource_related_many") || wizard.resourceRelatedMany || "no"),
            uniqueValueEnabled: String(formData.get("relationship_guide_unique_value") || wizard.uniqueValueEnabled || "no"),
            uniqueFieldKey: String(formData.get("relationship_guide_unique_field") || wizard.uniqueFieldKey || ""),
            label: String(formData.get("relationship_guide_label") || wizard.label || ""),
        };
        openModal(
            "Assistant de relations",
            buildNoCodeRelationGuideMarkup(),
            noCodeInlineOptions("min(760px, calc(100vw - 40px))", { inline: true }),
        );
        return;
    }
    if (!(select instanceof HTMLSelectElement) || select.name !== "assignment_beneficiary" || select.value !== "__add_beneficiary__") {
        return;
    }
    select.value = "";
    try {
        await openRecordAssignmentPicker();
    } catch (error) {
        const feedback = document.getElementById("modal-relation-assignment-feedback");
        if (feedback instanceof HTMLElement) {
            feedback.textContent = normalizeErrorMessage(error.message);
        }
    }
});

document.addEventListener("pointermove", (event) => {
    updateNoCodeRelationConnect(event);
    updateNoCodeRelationNodeDrag(event);
});

document.addEventListener("pointerup", (event) => {
    endNoCodeRelationConnect(event);
    endNoCodeRelationNodeDrag();
});

appModalBody.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof Element)) {
        return;
    }
    if (Number(state.noCodeRelationSuppressClickUntil || 0) > Date.now()) {
        event.preventDefault();
        event.stopPropagation();
        return;
    }
    const assignmentResourceButton = target.closest('[data-action="assignment:resource:add"]');
    if (assignmentResourceButton instanceof HTMLButtonElement) {
        event.preventDefault();
        await openRecordAssignmentCreateForm();
        return;
    }
    const assignmentBeneficiaryAddButton = target.closest('[data-action="assignment:beneficiary:add"]');
    if (assignmentBeneficiaryAddButton instanceof HTMLButtonElement) {
        event.preventDefault();
        await openRecordAssignmentBeneficiaryPicker();
        return;
    }
    const assignmentBeneficiaryUnlinkButton = target.closest('[data-action="assignment:beneficiary:unlink"]');
    if (assignmentBeneficiaryUnlinkButton instanceof HTMLButtonElement) {
        event.preventDefault();
        const beneficiaryId = String(assignmentBeneficiaryUnlinkButton.dataset.beneficiaryId || "").trim();
        const resourceId = String(assignmentBeneficiaryUnlinkButton.dataset.resourceId || "").trim();
        const confirmed = await showItopsConfirm({
            title: "Retirer le lien",
            message: "Retirer cet element de la fiche ouverte ?",
            details: resourceId
                ? ["Le code restera lie a la fiche ouverte, mais ne sera plus attribue a cet element."]
                : ["Seul le lien entre les deux fiches sera retire."],
            confirmLabel: "Delier",
            danger: true,
        });
        if (!confirmed) {
            return;
        }
        try {
            await unlinkRecordAssignmentBeneficiary(beneficiaryId, resourceId);
        } catch (error) {
            const feedback = document.getElementById("modal-service-record-feedback") || document.getElementById("modal-directory-record-feedback");
            if (feedback instanceof HTMLElement) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return;
    }
    const assignmentBeneficiaryBatchToggleButton = target.closest('[data-action="assignment:beneficiary:batch-toggle"]');
    if (assignmentBeneficiaryBatchToggleButton instanceof HTMLButtonElement) {
        event.preventDefault();
        state.relationAssignmentPicker = {
            ...(state.relationAssignmentPicker || {}),
            batchMode: !state.relationAssignmentPicker?.batchMode,
        };
        openModal("Ajouter un element lie", buildRecordAssignmentPickerMarkup(), { width: "min(980px, calc(100vw - 40px))" });
        return;
    }
    const assignmentBeneficiaryBatchAddButton = target.closest('[data-action="assignment:beneficiary:batch-add"]');
    if (assignmentBeneficiaryBatchAddButton instanceof HTMLButtonElement) {
        event.preventDefault();
        const ids = Array.from(appModalBody.querySelectorAll("[data-assignment-beneficiary-check]:checked"))
            .map((input) => String(input instanceof HTMLInputElement ? input.value : "").trim())
            .filter(Boolean);
        const feedback = document.getElementById("modal-relation-assignment-picker-feedback");
        if (!ids.length) {
            if (feedback instanceof HTMLElement) {
                feedback.textContent = "Cochez au moins un agent a lier.";
            }
            return;
        }
        try {
            await linkRecordAssignmentBeneficiaries(ids);
        } catch (error) {
            if (feedback instanceof HTMLElement) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return;
    }
    const assignmentResourceBackButton = target.closest('[data-action="assignment:resource:back"]');
    if (assignmentResourceBackButton instanceof HTMLButtonElement) {
        event.preventDefault();
        await returnToRecordAssignmentEditor();
        return;
    }
    const assignmentBeneficiaryBackButton = target.closest('[data-action="assignment:beneficiary:back"]');
    if (assignmentBeneficiaryBackButton instanceof HTMLButtonElement) {
        event.preventDefault();
        state.relationAssignmentPicker = null;
        const assignments = state.relationAssignmentCreate?.assignments;
        openModal(`Ajouter ${noCodeRecordEditorEntityLabel(assignments?.resourceService).toLowerCase()}`, buildRecordAssignmentCreateMarkup(state.noCodeServiceRecordContext), { width: "min(720px, calc(100vw - 40px))" });
        return;
    }
    const relationSummaryRecord = target.closest("[data-relation-summary-record]");
    if (relationSummaryRecord instanceof HTMLElement) {
        event.preventDefault();
        event.stopPropagation();
        const serviceCode = String(relationSummaryRecord.dataset.linkedServiceCode || "").trim().toLowerCase();
        const recordId = String(relationSummaryRecord.dataset.recordId || "").trim();
        if (serviceCode && recordId) {
            try {
                await openLinkedNoCodeRecordFromSummary(serviceCode, recordId);
            } catch (error) {
                const feedback = document.getElementById("modal-directory-record-feedback") || document.getElementById("modal-service-record-feedback");
                if (feedback instanceof HTMLElement) {
                    feedback.textContent = normalizeErrorMessage(error.message);
                }
            }
        }
        return;
    }
    const relationSummaryToggle = target.closest(".relation-summary-toggle");
    if (relationSummaryToggle instanceof HTMLElement && !target.closest(".relation-summary-action")) {
        event.preventDefault();
        event.stopPropagation();
        return;
    }
    const notificationTestButton = target.closest('[data-action="notification:test"]');
    if (notificationTestButton instanceof HTMLButtonElement) {
        const form = notificationTestButton.closest("form");
        if (form instanceof HTMLFormElement && form.id === "modal-notification-form") {
            await runNotificationSettingsTest(form);
        }
        return;
    }
    const notificationTaskButton = target.closest('[data-action^="notification:task"]');
    if (notificationTaskButton instanceof HTMLButtonElement) {
        const action = String(notificationTaskButton.dataset.action || "");
        if (action === "notification:tasks:refresh") {
            await openNotificationTasksModal();
            return;
        }
        if (action === "notification:task:done" || action === "notification:task:cancel") {
            await updateNotificationTaskStatus(
                notificationTaskButton.dataset.taskId || "",
                action === "notification:task:done" ? "done" : "cancelled",
            );
            return;
        }
    }
    const notificationTemplateButton = target.closest('[data-action^="notification:template"]');
    if (notificationTemplateButton instanceof HTMLButtonElement) {
        const action = String(notificationTemplateButton.dataset.action || "");
        if (action === "notification:templates:refresh") {
            await openNotificationTemplatesModal();
            return;
        }
        if (action === "notification:template:create") {
            openNotificationTemplateEditor(null);
            return;
        }
        if (action === "notification:template:edit") {
            const code = String(notificationTemplateButton.dataset.templateCode || "").trim().toLowerCase();
            const template = (state.notificationTemplates || []).find((row) => String(row?.code || "").trim().toLowerCase() === code);
            openNotificationTemplateEditor(template || null);
            return;
        }
        if (action === "notification:template:delete") {
            await deleteNotificationTemplate(notificationTemplateButton.dataset.templateCode || "");
            return;
        }
        if (action === "notification:template:insert-variable") {
            insertNotificationTemplateVariable(notificationTemplateButton.dataset.templateVariable || "");
            return;
        }
    }
    const directoryRelationButton = target.closest('[data-action="directory:record:relation-open"]');
    if (directoryRelationButton instanceof HTMLButtonElement) {
        await openDirectoryRecordRelationLinks(
            String(directoryRelationButton.dataset.recordId || ""),
            Number(directoryRelationButton.dataset.relationId || 0),
        );
        return;
    }
    const directoryEditButton = target.closest('[data-action="directory:record:edit"]');
    if (directoryEditButton instanceof HTMLButtonElement) {
        await openDirectoryRecordEditor(String(directoryEditButton.dataset.recordId || ""));
        return;
    }
    if (target.matches("[data-relation-picker-batch-check]")) {
        return;
    }
    const relationPickerItem = target.closest("[data-relation-picker-item]");
    if (relationPickerItem instanceof HTMLElement) {
        relationPickerSetSelectedItem(relationPickerItem);
        return;
    }
    const relationPickerBatchToggleButton = target.closest('[data-action="relation-picker:batch-toggle"]');
    if (relationPickerBatchToggleButton instanceof HTMLButtonElement) {
        const editor = state.noCodeRecordEditor;
        const relationId = String(relationPickerBatchToggleButton.dataset.relationId || "").trim();
        if (editor && relationId) {
            editor.relationStates = editor.relationStates && typeof editor.relationStates === "object" ? editor.relationStates : {};
            const current = noCodeRecordRelationState(editor, relationId);
            editor.relationStates[relationId] = {
                ...current,
                batchSelectionMode: !current.batchSelectionMode,
            };
            refreshOpenNoCodeRecordEditorMarkup();
        }
        return;
    }
    const relationPickerBatchAddButton = target.closest('[data-action="relation-picker:batch-add"]');
    if (relationPickerBatchAddButton instanceof HTMLButtonElement) {
        relationPickerAddBatchSelection(relationPickerFromElement(relationPickerBatchAddButton));
        return;
    }
    const relationPickerAddButton = target.closest('[data-action="relation-picker:add"]');
    if (relationPickerAddButton instanceof HTMLButtonElement) {
        relationPickerMoveSelected(relationPickerFromElement(relationPickerAddButton), "add");
        return;
    }
    const relationPickerRemoveButton = target.closest('[data-action="relation-picker:remove"]');
    if (relationPickerRemoveButton instanceof HTMLButtonElement) {
        relationPickerMoveSelected(relationPickerFromElement(relationPickerRemoveButton), "remove");
        return;
    }
    const directoryBatchRelationButton = target.closest('[data-action="directory:batch:relation-assign"]');
    if (directoryBatchRelationButton instanceof HTMLButtonElement) {
        await openDirectoryBatchRelationAssignModal();
        return;
    }
    const rolesHeader = target.closest("th[data-admin-roles-col]");
    if (rolesHeader instanceof HTMLElement) {
        const col = String(rolesHeader.getAttribute("data-admin-roles-col") || "").trim();
        if (col) {
            if (state.adminRolesSort.column === col) {
                state.adminRolesSort.direction = state.adminRolesSort.direction === "asc" ? "desc" : "asc";
            } else {
                state.adminRolesSort.column = col;
                state.adminRolesSort.direction = "asc";
            }
            renderRolesTreeView();
        }
        return;
    }
    const usersHeader = target.closest("th[data-admin-users-col]");
    if (usersHeader instanceof HTMLElement) {
        const col = String(usersHeader.getAttribute("data-admin-users-col") || "").trim();
        if (col) {
            if (state.adminUsersSort.column === col) {
                state.adminUsersSort.direction = state.adminUsersSort.direction === "asc" ? "desc" : "asc";
            } else {
                state.adminUsersSort.column = col;
                state.adminUsersSort.direction = "asc";
            }
            renderUsersTreeView();
        }
        return;
    }
    if (target.closest('[data-action="modal:close"]')) {
        await closeModalWithContextBack();
        return;
    }
    const activeDirectoryTestButton = target.closest('[data-action="active-directory:test"]');
    if (activeDirectoryTestButton instanceof HTMLButtonElement) {
        const form = activeDirectoryTestButton.closest("form");
        if (form instanceof HTMLFormElement && form.id === "modal-active-directory-form") {
            await submitActiveDirectorySettings(form, { test: true });
            event.stopPropagation();
            return;
        }
    }
    const activeDirectorySyncButton = target.closest('[data-action="active-directory:sync-now"]');
    if (activeDirectorySyncButton instanceof HTMLButtonElement) {
        const form = activeDirectorySyncButton.closest("form");
        if (form instanceof HTMLFormElement && form.id === "modal-active-directory-form") {
            await submitActiveDirectorySettings(form, {
                syncNow: true,
                syncMode: String(activeDirectorySyncButton.dataset.syncMode || "normal"),
            });
            event.stopPropagation();
            return;
        }
    }
    const activeDirectoryToggleButton = target.closest('[data-action="active-directory:toggle-auto-sync"]');
    if (activeDirectoryToggleButton instanceof HTMLButtonElement) {
        const form = activeDirectoryToggleButton.closest("form");
        const checkbox = form?.querySelector('[name="active_directory_enabled"]');
        if (form instanceof HTMLFormElement && checkbox instanceof HTMLInputElement) {
            checkbox.checked = !checkbox.checked;
            updateActiveDirectoryAutoSyncToggle(form);
            event.stopPropagation();
            return;
        }
    }
    const activeDirectoryImportButton = target.closest('[data-action="active-directory:certificate-import"]');
    if (activeDirectoryImportButton instanceof HTMLButtonElement) {
        document.getElementById("active-directory-certificate-file")?.click();
        return;
    }
    const activeDirectoryProfileButton = target.closest('[data-action^="active-directory-profile:"]');
    if (activeDirectoryProfileButton instanceof HTMLButtonElement) {
        const form = activeDirectoryProfileButton.closest("form");
        if (form instanceof HTMLFormElement && (form.id === "modal-active-directory-profile-form" || form.id === "modal-service-form")) {
            const action = String(activeDirectoryProfileButton.dataset.action || "");
            if (action === "active-directory-profile:add-field") {
                moveActiveDirectoryProfileField(form, "add");
            } else if (action === "active-directory-profile:remove-field") {
                moveActiveDirectoryProfileField(form, "remove");
            } else if (action === "active-directory-profile:move-up") {
                reorderActiveDirectorySelectedField(form, -1);
            } else if (action === "active-directory-profile:move-down") {
                reorderActiveDirectorySelectedField(form, 1);
            } else if (form.id === "modal-service-form") {
                syncServiceActiveDirectoryDraftFromDom();
            } else if (action === "active-directory-profile:new") {
                await openActiveDirectoryProfilesModal("");
            } else if (action === "active-directory-profile:preview") {
                await submitActiveDirectoryProfileForm(form, { preview: true });
            } else if (action === "active-directory-profile:delete") {
                const profileId = String(form.dataset.profileId || "").trim();
                if (!profileId) {
                    const feedback = document.getElementById("modal-active-directory-profile-feedback");
                    if (feedback instanceof HTMLElement) feedback.textContent = "Aucun profil existant a supprimer.";
                } else if (await showItopsConfirm({ title: "Supprimer le profil AD", message: "Supprimer ce profil de synchronisation ?", confirmLabel: "Supprimer", danger: true })) {
                    await requestJson(`/sync/active-directory/profiles/${encodeURIComponent(profileId)}`, { method: "DELETE" });
                    await openActiveDirectoryProfilesModal("");
                }
            }
            event.stopPropagation();
            return;
        }
    }
    const adMappingRow = target.closest("[data-ad-mapping-row]");
    if (adMappingRow instanceof HTMLElement) {
        const table = adMappingRow.closest("table");
        table?.querySelectorAll("[data-ad-mapping-row].is-selected").forEach((row) => row.classList.remove("is-selected"));
        adMappingRow.classList.add("is-selected");
        return;
    }
    const passwordRevealButton = target.closest('[data-action="password:toggle-visibility"]');
    if (passwordRevealButton instanceof HTMLButtonElement) {
        const field = passwordRevealButton.closest(".password-reveal-field");
        const input = field?.querySelector("input");
        if (input instanceof HTMLInputElement) {
            const reveal = input.type === "password";
            input.type = reveal ? "text" : "password";
            passwordRevealButton.innerHTML = passwordVisibilityIconMarkup(reveal);
            passwordRevealButton.title = reveal ? "Masquer le mot de passe" : "Afficher le mot de passe";
            passwordRevealButton.setAttribute("aria-label", reveal ? "Masquer le mot de passe" : "Afficher le mot de passe");
            event.stopPropagation();
            return;
        }
    }
    const sharedImport = window.NMPSharedImport;
    if (sharedImport && typeof sharedImport.handleIntegratedMappingPaginationClick === "function") {
        const handledMappingPage = sharedImport.handleIntegratedMappingPaginationClick(target);
        if (handledMappingPage) {
            const widget = target.closest("[data-import-mapping-widget]");
            if (state.noCodeServiceEditor?.importPreview && widget instanceof HTMLElement) {
                state.noCodeServiceEditor.importColumnPage = Number(widget.getAttribute("data-import-mapping-current-page") || 0);
            }
            if (state.noCodeServiceRecordContext?.importPreview && widget instanceof HTMLElement) {
                state.noCodeServiceRecordContext.importColumnPage = Number(widget.getAttribute("data-import-mapping-current-page") || 0);
            }
            return;
        }
    }
    const actionButton = target.closest("[data-action]");
    if (!(actionButton instanceof Element)) {
        return;
    }
    if (actionButton instanceof HTMLButtonElement && actionButton.disabled) {
        return;
    }
    const action = String(actionButton.dataset.action || "");
    // Les actions de l'editeur sont executees de maniere asynchrone. Sans
    // stopper le clic ici, il continue vers le tableau de bord pendant l'attente
    // et rouvre la tuile du module sous-jacent.
    if (action.startsWith("service:")) {
        event.preventDefault();
        event.stopPropagation();
    }
    if (action === "linked-columns-picker:back") {
        state.linkedColumnsPicker = null;
        await restoreNextModalBackSnapshot();
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
    if (action === "storage-files:refresh") {
        try {
            await refreshStorageFilesModal();
        } catch (error) {
            const feedback = document.getElementById("modal-storage-files-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return;
    }
    if (action === "storage-files:download") {
        try {
            await downloadStorageFile(actionButton.dataset.fileId, actionButton.dataset.fileName);
        } catch (error) {
            const feedback = document.getElementById("modal-storage-files-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return;
    }
    if (action === "storage-explorer:open") {
        try {
            await openStorageExplorerModal(actionButton.dataset.rootId || "");
        } catch (error) {
            const feedback = document.getElementById("modal-storage-files-feedback") || document.getElementById("modal-storage-remote-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return;
    }
    if (action === "storage-explorer:back") {
        await openStorageFilesModal();
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
        try {
            await createStorageExplorerFolder();
        } catch (error) {
            const feedback = document.getElementById("storage-explorer-feedback");
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
    if (action === "storage-target:add") {
        openStorageTargetForm(null);
        return;
    }
    if (action === "storage-target:edit") {
        const target = storageTargetById(actionButton.dataset.targetId);
        const feedback = document.getElementById("modal-storage-remote-feedback");
        if (!target) {
            if (feedback) {
                feedback.textContent = "Emplacement de stockage introuvable.";
            }
            return;
        }
        openStorageTargetForm(target);
        return;
    }
    if (action === "storage-target:cancel") {
        const form = document.getElementById("modal-storage-target-form");
        if (form instanceof HTMLFormElement) {
            resetStorageTargetForm(form);
        }
        return;
    }
    if (action === "storage-target:test") {
        const feedback = document.getElementById("modal-storage-remote-feedback");
        try {
            if (feedback) {
                feedback.textContent = "Test de l'emplacement...";
            }
            const result = await requestJson(`/storage/targets/${encodeURIComponent(String(actionButton.dataset.targetId || ""))}/test`, {
                method: "POST",
            });
            await refreshStorageFilesModal();
            if (feedback) {
                feedback.textContent = String(result?.message || "").trim() || "Test termine.";
            }
        } catch (error) {
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return;
    }
    if (action === "storage-target:delete") {
        const targetId = String(actionButton.dataset.targetId || "").trim();
        if (!targetId || !(await showItopsConfirm({
            title: "Supprimer l'emplacement",
            message: "Supprimer cet emplacement de stockage ?",
            confirmLabel: "Supprimer",
            danger: true,
        }))) {
            return;
        }
        const feedback = document.getElementById("modal-storage-remote-feedback");
        try {
            await requestJson(`/storage/targets/${encodeURIComponent(targetId)}`, {
                method: "DELETE",
            });
            await refreshStorageFilesModal();
        } catch (error) {
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return;
    }
    const handledSharedList = await handleSharedListModalClick(actionButton);
    if (handledSharedList) {
        return;
    }
    const handledNoCode = await handleNoCodeModalClick(actionButton);
    if (handledNoCode) {
        return;
    }
    const sharedAdminController = window.NMPSharedAdminController;
    if (!sharedAdminController || typeof sharedAdminController.handleModalClick !== "function") {
        const feedback = document.getElementById("modal-admin-feedback");
        if (feedback) {
            feedback.textContent = "Controleur admin indisponible.";
        }
        return;
    }
    await sharedAdminController.handleModalClick(actionButton, {
        documentRef: document,
        adminData: state.adminData,
        openModal: (title, bodyMarkup, modalOptions = {}) => {
            const merged = { ...modalOptions };
            if (state.adminInlineMode) {
                merged.inlineHost = "portal";
            }
            openModal(title, bodyMarkup, merged);
        },
        resolveModalOptions: () => (state.adminInlineMode ? { inlineHost: "portal" } : {}),
        roleFormMarkup,
        userFormMarkup,
        requestJson,
        normalizeErrorMessage,
        invalidateAdminData,
        openRolesModal,
        openUsersModal,
        confirmFn: (message) => showItopsConfirm({
            title: "Confirmation",
            message,
            confirmLabel: "Confirmer",
            danger: true,
        }),
    });
});

appModalBody.addEventListener("change", async (event) => {
    const input = event.target;
    if (!(input instanceof HTMLInputElement) || input.id !== "active-directory-certificate-file") {
        return;
    }
    const file = input.files?.[0];
    const feedback = document.getElementById("modal-active-directory-feedback");
    if (!file) return;
    try {
        if (feedback instanceof HTMLElement) feedback.textContent = "Import du certificat...";
        const dataUrl = await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(String(reader.result || ""));
            reader.onerror = () => reject(new Error("Lecture du certificat impossible."));
            reader.readAsDataURL(file);
        });
        const contentBase64 = String(dataUrl).split(",", 2)[1] || "";
        await requestJson("/settings/active-directory/certificate", { method: "POST", body: JSON.stringify({ filename: file.name, content_base64: contentBase64 }) });
        if (feedback instanceof HTMLElement) feedback.textContent = "Certificat importe. Le test utilisera immediatement ce certificat.";
    } catch (error) {
        if (feedback instanceof HTMLElement) feedback.textContent = normalizeErrorMessage(error.message);
    } finally {
        input.value = "";
    }
});

appModalBody.addEventListener("dblclick", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) {
        return;
    }
    if (target.matches("[data-relation-picker-batch-check]")) {
        return;
    }
    const relationPickerItem = target.closest("[data-relation-picker-item]");
    if (relationPickerItem instanceof HTMLElement) {
        event.preventDefault();
        event.stopPropagation();
        relationPickerMoveItem(relationPickerItem);
    }
});

appModalBody.addEventListener("toggle", (event) => {
    const details = event.target;
    if (!(details instanceof HTMLDetailsElement) || !details.matches("[data-relation-editor-accordion]")) {
        return;
    }
    const relationId = String(details.dataset.relationId || "").trim();
    if (!relationId || !state.noCodeRecordEditor) {
        return;
    }
    const current = new Set(
        (Array.isArray(state.noCodeRecordEditor.openRelationEditorIds) ? state.noCodeRecordEditor.openRelationEditorIds : [])
            .map((value) => String(value || "").trim())
            .filter(Boolean),
    );
    if (details.open) {
        current.add(relationId);
        state.noCodeRecordEditor.openRelationEditorIds = Array.from(current);
        loadNoCodeRecordRelationCandidates(relationId).catch((error) => {
            const feedback = document.getElementById("modal-directory-record-feedback") || document.getElementById("modal-service-record-feedback");
            if (feedback instanceof HTMLElement) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        });
    } else {
        current.delete(relationId);
        state.noCodeRecordEditor.openRelationEditorIds = Array.from(current);
    }
}, true);

appModalBody.addEventListener("change", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLSelectElement)) {
        return;
    }
    const form = target.closest("form");
    if (!(form instanceof HTMLFormElement) || form.id !== "modal-active-directory-profile-form") {
        return;
    }
    if (target.matches("[data-ad-profile-selector]")) {
        await openActiveDirectoryProfilesModal(String(target.value || ""));
        return;
    }
    if (target.matches("[data-ad-profile-target-kind]")) {
        const payload = await requestJson("/sync/active-directory/profiles");
        const targetKind = normalizeActiveDirectoryProfileTargetKind(target.value);
        openModal("Profils d'import Active Directory", buildActiveDirectoryProfilesMarkup({
            ...payload,
            profiles: [{
                id: String(form.dataset.profileId || ""),
                code: String(new window.FormData(form).get("code") || ""),
                label: String(new window.FormData(form).get("label") || ""),
                target_kind: targetKind,
                search_base: String(new window.FormData(form).get("search_base") || ""),
                search_filter: activeDirectoryProfileDefaultFilter(targetKind),
                selected_attributes: listFromMaybeArray(payload.available_attributes?.[targetKind]).slice(0, 6),
                options: activeDirectoryReadOuScopeOptions(form, "profile", targetKind, {}),
                is_active: form.querySelector('[name="is_active"]')?.checked ?? true,
            }],
        }), String(form.dataset.profileId || ""));
    }
});

appModalBody.addEventListener("change", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLSelectElement)) {
        return;
    }
    const form = target.closest("form");
    if (!(form instanceof HTMLFormElement) || form.id !== "modal-service-form") {
        return;
    }
    const editor = state.noCodeServiceEditor;
    if (!editor?.adImportDraft) {
        return;
    }
    if (target.name === "service_ad_import_target_kind") {
        const targetKind = normalizeActiveDirectoryProfileTargetKind(target.value);
        editor.adImportDraft = {
            ...editor.adImportDraft,
            profile_id: "",
            target_kind: targetKind,
            search_filter: activeDirectoryProfileDefaultFilter(targetKind),
            selected_attributes: listFromMaybeArray(editor.adImportPayload?.available_attributes?.[targetKind]).slice(0, 6),
            options: {},
        };
        renderNoCodeServiceEditor();
        window.setTimeout(() => loadServiceActiveDirectoryExamples({ silent: true }), 0);
        return;
    }
    if (target.name === "service_ad_import_profile") {
        const profileId = String(target.value || "").trim();
        const profile = listFromMaybeArray(editor.adImportPayload?.profiles)
            .find((row) => String(row.id || "") === profileId);
        if (profile) {
            editor.adImportDraft = {
                profile_id: String(profile.id || ""),
                id: String(profile.id || ""),
                target_kind: normalizeActiveDirectoryProfileTargetKind(profile.target_kind),
                label: String(profile.label || ""),
                code: String(profile.code || ""),
                search_base: String(profile.search_base || ""),
                search_filter: String(profile.search_filter || activeDirectoryProfileDefaultFilter(profile.target_kind)),
                selected_attributes: listFromMaybeArray(profile.selected_attributes),
                options: profile.options || {},
            };
            renderNoCodeServiceEditor();
            window.setTimeout(() => loadServiceActiveDirectoryExamples({ silent: true }), 0);
        }
        return;
    }
    if (target.name === "service_ad_mapping_target") {
        const row = target.closest("[data-ad-mapping-row]");
        if (row instanceof HTMLElement) {
            const ignored = target.value === "__ignore__";
            const newField = target.value === "__new__";
            const labelInput = row.querySelector('input[name="service_ad_mapping_label"]');
            const kindSelect = row.querySelector('select[name="service_ad_mapping_kind"]');
            target.classList.toggle("is-ignored", ignored);
            target.classList.toggle("is-mapped", !ignored);
            row.classList.toggle("is-ignored", ignored);
            if (labelInput instanceof HTMLInputElement) labelInput.disabled = !newField;
            if (kindSelect instanceof HTMLSelectElement) kindSelect.disabled = !newField;
        }
        syncServiceActiveDirectoryDraftFromDom();
        return;
    }
    if (target.name === "service_ad_mapping_kind") {
        syncServiceActiveDirectoryDraftFromDom();
    }
});

appModalBody.addEventListener("change", async (event) => {
    const target = event.target;
    if (target instanceof HTMLInputElement && target.matches('[data-relation-assignment-single]') && target.checked) {
        const picker = target.closest("[data-relation-assignment-picker]");
        Array.from(picker?.querySelectorAll?.('input[name="linked_record_ids"]') || []).forEach((input) => {
            if (input instanceof HTMLInputElement && input !== target) {
                input.checked = false;
            }
        });
        return;
    }
    if (!(target instanceof HTMLSelectElement) || !target.matches("[data-directory-batch-relation-select]")) {
        return;
    }
    await reloadDirectoryBatchRelationAssignModal(String(target.value || ""));
});

appModalBody.addEventListener("change", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLSelectElement) || !target.matches("[data-service-records-batch-relation-select]")) {
        return;
    }
    await reloadNoCodeBatchRelationAssignModal(String(target.value || ""));
});

appModalBody.addEventListener("submit", async (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) {
        return;
    }
    event.preventDefault();
    if (form.id === "modal-linked-columns-picker-form") {
        await submitLinkedColumnsPicker(form);
        return;
    }
    if (form.id === "modal-webserver-form") {
        await submitWebServerSettings(form);
        return;
    }
    if (form.id === "modal-notification-form") {
        await submitNotificationSettings(form);
        return;
    }
    if (form.id === "modal-notification-template-form") {
        await submitNotificationTemplate(form);
        return;
    }
    if (form.id === "modal-active-directory-form") {
        await submitActiveDirectorySettings(form);
        return;
    }
    if (form.id === "modal-active-directory-profile-form") {
        await submitActiveDirectoryProfileForm(form);
        return;
    }
    if (form.id === "modal-monitoring-notification-form") {
        await submitMonitoringNotificationSettings(form);
        return;
    }
    if (form.id === "modal-watermark-form") {
        await submitWatermarkEditorForm(form);
        return;
    }
    if (form.id === "modal-database-import-form") {
        const feedback = document.getElementById("modal-database-import-feedback");
        try {
            await submitDatabaseImportForm(form);
        } catch (error) {
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return;
    }
    if (form.id === "modal-storage-target-form") {
        const feedback = document.getElementById("modal-storage-target-feedback");
        try {
            await submitStorageTargetForm(form);
        } catch (error) {
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return;
    }
    if (form.id === "modal-directory-batch-relation-form") {
        await submitDirectoryBatchRelationAssignForm(form);
        return;
    }
    if (form.id === "modal-directory-record-form") {
        await submitDirectoryRecordEditorForm();
        return;
    }
    if (form.id === "modal-service-records-batch-relation-form") {
        await submitNoCodeBatchRelationAssignForm(form);
        return;
    }
    if (form.id === "modal-service-records-batch-field-form") {
        await submitNoCodeBatchFieldUpdateForm(form);
        return;
    }
    const handledSharedList = await handleSharedListModalSubmit(form);
    if (handledSharedList) {
        return;
    }
    const handledNoCode = await handleNoCodeModalSubmit(form);
    if (handledNoCode) {
        return;
    }
    const sharedAdminController = window.NMPSharedAdminController;
    if (!sharedAdminController || typeof sharedAdminController.handleModalSubmit !== "function") {
        if (form.id === "modal-role-form" || form.id === "modal-user-form") {
            const feedbackId = form.id === "modal-role-form" ? "modal-role-feedback" : "modal-user-feedback";
            const feedback = document.getElementById(feedbackId);
            if (feedback) {
                feedback.textContent = "Controleur admin indisponible.";
            }
        }
        return;
    }
    await sharedAdminController.handleModalSubmit(form, {
        documentRef: document,
        requestJson,
        normalizeErrorMessage,
        invalidateAdminData,
        openRolesModal,
        openUsersModal,
        parseRoleForm: window.NMPSharedAdminUi?.parseRoleForm,
        parseUserForm: window.NMPSharedAdminUi?.parseUserForm,
    });
});

appModalBody.addEventListener("input", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLInputElement)) {
        return;
    }
    if (target.matches("[data-relation-assignment-search]")) {
        filterRelationAssignmentPicker(target);
        return;
    }
    if (target.id === "relation-assignment-search") {
        filterRecordAssignmentPickerRows(target);
        return;
    }
    if (target.matches("[data-relation-picker-search]")) {
        filterRelationDualPicker(target);
        return;
    }
    if (target.id === "modal-admin-roles-search") {
        renderRolesTreeView();
        return;
    }
    if (target.id === "modal-admin-users-search") {
        renderUsersTreeView();
        return;
    }
    if (target.name === "active_directory_host" || target.name === "active_directory_bind_username") {
        const form = target.closest("form");
        if (form instanceof HTMLFormElement && form.id === "modal-active-directory-form") {
            updateActiveDirectoryDomainSuffix(form);
        }
        return;
    }
    if (target.name === "service_ad_mapping_label") {
        syncServiceActiveDirectoryDraftFromDom();
        return;
    }
    if (target.name === "service_label") {
        const editor = state.noCodeServiceEditor;
        if (editor) {
            editor.label = normalizeNoCodeText(target.value);
            updateNoCodeServiceTechnicalCodeDisplay();
        }
        return;
    }
    if (target.name === "service_child_label") {
        const editor = state.noCodeServiceEditor;
        if (editor) {
            editor.child_label = normalizeNoCodeText(target.value) || "Elements lies";
        }
        return;
    }
    if (target.name === "service_relation_verb") {
        const editor = state.noCodeServiceEditor;
        const relationId = String(target.dataset.relationId || "").trim();
        const relation = relationId ? findNoCodeRelationDraftById(editor, relationId) : null;
        if (relation) {
            relation.verb = normalizeNoCodeText(target.value) || "est lie a";
            updateNoCodeRelationNaturalPhrasePreview(relation);
        }
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
    if (target instanceof HTMLSelectElement && target.name === "storage_target_type") {
        const form = target.closest("#modal-storage-target-form");
        if (form instanceof HTMLFormElement) {
            syncStorageTargetFormType(form);
        }
        return;
    }
    if (target instanceof HTMLInputElement && target.name === "service_field_import_advanced") {
        const editor = state.noCodeServiceEditor;
        if (editor) {
            editor.importAdvancedEnabled = Boolean(target.checked);
            renderNoCodeServiceEditor();
        }
        return;
    }
    if (target instanceof HTMLInputElement && target.name === "service_field_import_records_enabled") {
        const editor = state.noCodeServiceEditor;
        if (editor) {
            editor.importRecordsEnabled = Boolean(target.checked);
            if (!editor.importRecordsEnabled) {
                editor.appliedImportForRecords = null;
            }
        }
        return;
    }
    if (target instanceof HTMLInputElement && target.name === "service_field_import_until_row") {
        const editor = state.noCodeServiceEditor;
        const form = target.closest("form");
        const sheetSelector = form?.querySelector?.('select[name="service_field_import_sheet"]');
        const headerModeSelector = form?.querySelector?.('select[name="service_field_import_header_mode"]');
        const headerRowInput = form?.querySelector?.('input[name="service_field_import_header_row"]');
        const selectedSheet = String(sheetSelector?.value || editor?.importPreview?.selectedSheetName || "").trim();
        const headerMode = normalizeTabularHeaderMode(headerModeSelector?.value || editor?.importHeaderMode);
        const headerRowNumber = normalizeTabularHeaderRowNumber(headerRowInput?.value || editor?.importHeaderRowNumber);
        const importUntilRowNumber = normalizeTabularUntilRowNumber(target.value || 0);
        if (editor) {
            editor.importUntilRowNumber = importUntilRowNumber;
        }
        const feedback = document.getElementById("modal-service-form-feedback");
        if (feedback) {
            feedback.textContent = "Recalcul de l'apercu...";
        }
        refreshNoCodeServiceFieldImportPreviewFromSheet(selectedSheet, headerMode, headerRowNumber, importUntilRowNumber)
            .then(() => {
                const refreshed = document.getElementById("modal-service-form-feedback");
                if (refreshed) {
                    refreshed.textContent = "Apercu mis a jour.";
                }
            })
            .catch((error) => {
                const refreshed = document.getElementById("modal-service-form-feedback");
                if (refreshed) {
                    refreshed.textContent = normalizeErrorMessage(error.message);
                }
            });
        return;
    }
    if (target instanceof HTMLSelectElement && target.name === "service_field_import_sheet") {
        const selectedSheet = String(target.value || "").trim();
        const form = target.closest("form");
        const headerModeSelector = form?.querySelector?.('select[name="service_field_import_header_mode"]');
        const headerRowInput = form?.querySelector?.('input[name="service_field_import_header_row"]');
        const headerMode = normalizeTabularHeaderMode(headerModeSelector?.value || state.noCodeServiceEditor?.importHeaderMode);
        const headerRowNumber = normalizeTabularHeaderRowNumber(headerRowInput?.value || state.noCodeServiceEditor?.importHeaderRowNumber);
        const importUntilRowNumber = readServiceFieldImportUntilRowFromForm(form);
        if (state.noCodeServiceEditor) {
            state.noCodeServiceEditor.importColumnMappings = [];
            state.noCodeServiceEditor.importColumnPage = 0;
            state.noCodeServiceEditor.importUntilRowNumber = importUntilRowNumber;
        }
        const feedback = document.getElementById("modal-service-form-feedback");
        if (feedback) {
            feedback.textContent = "Recalcul de l'apercu...";
        }
        refreshNoCodeServiceFieldImportPreviewFromSheet(selectedSheet, headerMode, headerRowNumber)
            .then(() => {
                const refreshed = document.getElementById("modal-service-form-feedback");
                if (refreshed) {
                    refreshed.textContent = "Apercu mis a jour.";
                }
            })
            .catch((error) => {
                const refreshed = document.getElementById("modal-service-form-feedback");
                if (refreshed) {
                    refreshed.textContent = normalizeErrorMessage(error.message);
                }
            });
        return;
    }
    if (target instanceof HTMLSelectElement && target.name === "service_field_import_header_mode") {
        const selectedMode = normalizeTabularHeaderMode(target.value);
        const form = target.closest("form");
        const sheetSelector = form?.querySelector?.('select[name="service_field_import_sheet"]');
        const headerRowInput = form?.querySelector?.('input[name="service_field_import_header_row"]');
        if (headerRowInput instanceof HTMLInputElement) {
            headerRowInput.disabled = selectedMode !== "manual";
            if (selectedMode !== "manual") {
                headerRowInput.value = String(normalizeTabularHeaderRowNumber(state.noCodeServiceEditor?.importHeaderRowNumber || 1));
            }
        }
        const selectedSheet = String(sheetSelector?.value || state.noCodeServiceEditor?.importPreview?.selectedSheetName || "").trim();
        const headerRowNumber = normalizeTabularHeaderRowNumber(headerRowInput?.value || state.noCodeServiceEditor?.importHeaderRowNumber);
        const importUntilRowNumber = readServiceFieldImportUntilRowFromForm(form);
        if (state.noCodeServiceEditor) {
            state.noCodeServiceEditor.importColumnMappings = [];
            state.noCodeServiceEditor.importColumnPage = 0;
            state.noCodeServiceEditor.importUntilRowNumber = importUntilRowNumber;
        }
        const feedback = document.getElementById("modal-service-form-feedback");
        if (feedback) {
            feedback.textContent = "Recalcul de l'apercu...";
        }
        refreshNoCodeServiceFieldImportPreviewFromSheet(selectedSheet, selectedMode, headerRowNumber, importUntilRowNumber)
            .then(() => {
                const refreshed = document.getElementById("modal-service-form-feedback");
                if (refreshed) {
                    refreshed.textContent = "Apercu mis a jour.";
                }
            })
            .catch((error) => {
                const refreshed = document.getElementById("modal-service-form-feedback");
                if (refreshed) {
                    refreshed.textContent = normalizeErrorMessage(error.message);
                }
            });
        return;
    }
    if (target instanceof HTMLInputElement && target.name === "service_field_import_header_row") {
        const form = target.closest("form");
        const headerModeSelector = form?.querySelector?.('select[name="service_field_import_header_mode"]');
        const headerMode = normalizeTabularHeaderMode(headerModeSelector?.value || state.noCodeServiceEditor?.importHeaderMode);
        if (headerMode !== "manual") {
            return;
        }
        const sheetSelector = form?.querySelector?.('select[name="service_field_import_sheet"]');
        const selectedSheet = String(sheetSelector?.value || state.noCodeServiceEditor?.importPreview?.selectedSheetName || "").trim();
        const headerRowNumber = normalizeTabularHeaderRowNumber(target.value || state.noCodeServiceEditor?.importHeaderRowNumber);
        const importUntilRowNumber = readServiceFieldImportUntilRowFromForm(form);
        if (state.noCodeServiceEditor) {
            state.noCodeServiceEditor.importColumnMappings = [];
            state.noCodeServiceEditor.importColumnPage = 0;
            state.noCodeServiceEditor.importUntilRowNumber = importUntilRowNumber;
        }
        const feedback = document.getElementById("modal-service-form-feedback");
        if (feedback) {
            feedback.textContent = "Recalcul de l'apercu...";
        }
        refreshNoCodeServiceFieldImportPreviewFromSheet(selectedSheet, headerMode, headerRowNumber)
            .then(() => {
                const refreshed = document.getElementById("modal-service-form-feedback");
                if (refreshed) {
                    refreshed.textContent = "Apercu mis a jour.";
                }
            })
            .catch((error) => {
                const refreshed = document.getElementById("modal-service-form-feedback");
                if (refreshed) {
                    refreshed.textContent = normalizeErrorMessage(error.message);
                }
            });
        return;
    }
    if (
        target instanceof HTMLSelectElement
        && (target.name === "service_field_import_target" || target.name === "service_field_import_kind")
    ) {
        if (target.name === "service_field_import_target") {
            window.NMPSharedImport?.updateMappingSelectClass?.(target);
        }
        const row = target.closest("[data-source-column]");
        const customInput = row?.querySelector?.('input[name="service_field_import_custom"]');
        if (target.name === "service_field_import_target" && customInput instanceof HTMLInputElement) {
            const shouldShow = String(target.value || "").trim() === "__create_field__";
            customInput.disabled = !shouldShow;
            customInput.style.display = shouldShow ? "" : "none";
            if (!shouldShow) {
                customInput.value = "";
            }
        }
        const editor = state.noCodeServiceEditor;
        const form = target.closest("form");
        const sheetSelector = form?.querySelector?.('select[name="service_field_import_sheet"]');
        const headerModeSelector = form?.querySelector?.('select[name="service_field_import_header_mode"]');
        const headerRowInput = form?.querySelector?.('input[name="service_field_import_header_row"]');
        const selectedSheet = String(sheetSelector?.value || editor?.importPreview?.selectedSheetName || "").trim();
        const headerMode = normalizeTabularHeaderMode(headerModeSelector?.value || editor?.importHeaderMode);
        const headerRowNumber = normalizeTabularHeaderRowNumber(headerRowInput?.value || editor?.importHeaderRowNumber);
        const importUntilRowNumber = readServiceFieldImportUntilRowFromForm(form);
        if (editor) {
            editor.importColumnMappings = mergeServiceFieldImportMappings(
                editor.importColumnMappings,
                readServiceFieldImportMappingsFromDom(),
            );
            editor.importUntilRowNumber = importUntilRowNumber;
        }
        const feedback = document.getElementById("modal-service-form-feedback");
        if (feedback) {
            feedback.textContent = "Recalcul de l'apercu...";
        }
        refreshNoCodeServiceFieldImportPreviewFromSheet(selectedSheet, headerMode, headerRowNumber, importUntilRowNumber)
            .then(() => {
                const refreshed = document.getElementById("modal-service-form-feedback");
                if (refreshed) {
                    refreshed.textContent = "Mapping mis a jour.";
                }
            })
            .catch((error) => {
                const refreshed = document.getElementById("modal-service-form-feedback");
                if (refreshed) {
                    refreshed.textContent = normalizeErrorMessage(error.message);
                }
            });
        return;
    }
    if (target instanceof HTMLInputElement && target.name === "service_field_import_custom") {
        const editor = state.noCodeServiceEditor;
        const form = target.closest("form");
        const sheetSelector = form?.querySelector?.('select[name="service_field_import_sheet"]');
        const headerModeSelector = form?.querySelector?.('select[name="service_field_import_header_mode"]');
        const headerRowInput = form?.querySelector?.('input[name="service_field_import_header_row"]');
        const selectedSheet = String(sheetSelector?.value || editor?.importPreview?.selectedSheetName || "").trim();
        const headerMode = normalizeTabularHeaderMode(headerModeSelector?.value || editor?.importHeaderMode);
        const headerRowNumber = normalizeTabularHeaderRowNumber(headerRowInput?.value || editor?.importHeaderRowNumber);
        const importUntilRowNumber = readServiceFieldImportUntilRowFromForm(form);
        if (editor) {
            editor.importColumnMappings = mergeServiceFieldImportMappings(
                editor.importColumnMappings,
                readServiceFieldImportMappingsFromDom(),
            );
            editor.importUntilRowNumber = importUntilRowNumber;
        }
        const feedback = document.getElementById("modal-service-form-feedback");
        if (feedback) {
            feedback.textContent = "Recalcul de l'apercu...";
        }
        refreshNoCodeServiceFieldImportPreviewFromSheet(selectedSheet, headerMode, headerRowNumber, importUntilRowNumber)
            .then(() => {
                const refreshed = document.getElementById("modal-service-form-feedback");
                if (refreshed) {
                    refreshed.textContent = "Nom du champ mis a jour.";
                }
            })
            .catch((error) => {
                const refreshed = document.getElementById("modal-service-form-feedback");
                if (refreshed) {
                    refreshed.textContent = normalizeErrorMessage(error.message);
                }
            });
        return;
    }
    if (target instanceof HTMLSelectElement && target.name === "service_records_import_sheet") {
        const selectedSheet = String(target.value || "").trim();
        const credentialSelector = document.querySelector('select[name="service_records_import_credential_mode"]');
        const headerModeSelector = document.querySelector('select[name="service_records_import_header_mode"]');
        const headerRowInput = document.querySelector('input[name="service_records_import_header_row"]');
        const headerMode = normalizeTabularHeaderMode(headerModeSelector?.value || state.noCodeServiceRecordContext?.importHeaderMode);
        const headerRowNumber = normalizeTabularHeaderRowNumber(headerRowInput?.value || state.noCodeServiceRecordContext?.importHeaderRowNumber);
        if (state.noCodeServiceRecordContext) {
            state.noCodeServiceRecordContext.importCredentialMode = normalizeRecordsImportCredentialMode(
                credentialSelector?.value || state.noCodeServiceRecordContext.importCredentialMode,
            );
            state.noCodeServiceRecordContext.importHeaderMode = headerMode;
            state.noCodeServiceRecordContext.importHeaderRowNumber = headerRowNumber;
            state.noCodeServiceRecordContext.importColumnMappings = [];
        }
        const feedback = document.getElementById("modal-service-records-feedback");
        if (feedback) {
            feedback.textContent = "Recalcul de l'apercu...";
        }
        setServiceRecordsImportProgress(40, "Recalcul de l'apercu...", true);
        refreshNoCodeServiceRecordsImportPreviewFromSheet(selectedSheet, headerMode, headerRowNumber)
            .then(() => {
                setServiceRecordsImportProgress(55, "Apercu pret", true);
                const refreshed = document.getElementById("modal-service-records-feedback");
                if (refreshed) {
                    refreshed.textContent = "Apercu mis a jour.";
                }
            })
            .catch((error) => {
                setServiceRecordsImportProgress(0, "", false);
                const refreshed = document.getElementById("modal-service-records-feedback");
                if (refreshed) {
                    refreshed.textContent = normalizeErrorMessage(error.message);
                }
            });
        return;
    }
    if (target instanceof HTMLSelectElement && target.name === "service_records_import_header_mode") {
        const selectedMode = normalizeTabularHeaderMode(target.value);
        const headerRowInput = document.querySelector('input[name="service_records_import_header_row"]');
        if (headerRowInput instanceof HTMLInputElement) {
            headerRowInput.disabled = selectedMode !== "manual";
            if (selectedMode !== "manual") {
                headerRowInput.value = String(normalizeTabularHeaderRowNumber(state.noCodeServiceRecordContext?.importHeaderRowNumber || 1));
            }
        }
        const sheetSelector = document.querySelector('select[name="service_records_import_sheet"]');
        const selectedSheet = String(sheetSelector?.value || state.noCodeServiceRecordContext?.importSheetName || "").trim();
        const headerRowNumber = normalizeTabularHeaderRowNumber(headerRowInput?.value || state.noCodeServiceRecordContext?.importHeaderRowNumber);
        if (state.noCodeServiceRecordContext) {
            state.noCodeServiceRecordContext.importHeaderMode = selectedMode;
            state.noCodeServiceRecordContext.importHeaderRowNumber = headerRowNumber;
            state.noCodeServiceRecordContext.importColumnMappings = [];
        }
        const feedback = document.getElementById("modal-service-records-feedback");
        if (feedback) {
            feedback.textContent = "Recalcul de l'apercu...";
        }
        setServiceRecordsImportProgress(40, "Recalcul de l'apercu...", true);
        refreshNoCodeServiceRecordsImportPreviewFromSheet(selectedSheet, selectedMode, headerRowNumber)
            .then(() => {
                setServiceRecordsImportProgress(55, "Apercu pret", true);
                const refreshed = document.getElementById("modal-service-records-feedback");
                if (refreshed) {
                    refreshed.textContent = "Apercu mis a jour.";
                }
            })
            .catch((error) => {
                setServiceRecordsImportProgress(0, "", false);
                const refreshed = document.getElementById("modal-service-records-feedback");
                if (refreshed) {
                    refreshed.textContent = normalizeErrorMessage(error.message);
                }
            });
        return;
    }
    if (target instanceof HTMLSelectElement && target.name === "service_records_import_target") {
        window.NMPSharedImport?.updateMappingSelectClass?.(target);
        const row = target.closest("[data-source-column]");
        const customInput = row?.querySelector?.('input[name="service_records_import_custom"]');
        if (customInput instanceof HTMLInputElement) {
            const shouldShow = String(target.value || "").trim() === "__create_field__";
            customInput.disabled = !shouldShow;
            customInput.style.display = shouldShow ? "" : "none";
            if (!shouldShow) {
                customInput.value = "";
            }
        }
        const context = state.noCodeServiceRecordContext;
        const sheetSelector = document.querySelector('select[name="service_records_import_sheet"]');
        const headerModeSelector = document.querySelector('select[name="service_records_import_header_mode"]');
        const headerRowInput = document.querySelector('input[name="service_records_import_header_row"]');
        const selectedSheet = String(sheetSelector?.value || context?.importSheetName || "").trim();
        const headerMode = normalizeTabularHeaderMode(headerModeSelector?.value || context?.importHeaderMode);
        const headerRowNumber = normalizeTabularHeaderRowNumber(headerRowInput?.value || context?.importHeaderRowNumber);
        if (context) {
            context.importColumnMappings = mergeServiceRecordImportMappings(
                context.importColumnMappings,
                readServiceRecordImportMappingsFromDom(),
            );
        }
        const feedback = document.getElementById("modal-service-records-feedback");
        if (feedback) {
            feedback.textContent = "Recalcul de l'apercu...";
        }
        setServiceRecordsImportProgress(40, "Recalcul de l'apercu...", true);
        refreshNoCodeServiceRecordsImportPreviewFromSheet(selectedSheet, headerMode, headerRowNumber)
            .then(() => {
                setServiceRecordsImportProgress(55, "Apercu pret", true);
                const refreshed = document.getElementById("modal-service-records-feedback");
                if (refreshed) {
                    refreshed.textContent = "Mapping mis a jour.";
                }
            })
            .catch((error) => {
                setServiceRecordsImportProgress(0, "", false);
                const refreshed = document.getElementById("modal-service-records-feedback");
                if (refreshed) {
                    refreshed.textContent = normalizeErrorMessage(error.message);
                }
            });
        return;
    }
    if (target instanceof HTMLInputElement && target.name === "service_records_import_custom") {
        const context = state.noCodeServiceRecordContext;
        const sheetSelector = document.querySelector('select[name="service_records_import_sheet"]');
        const headerModeSelector = document.querySelector('select[name="service_records_import_header_mode"]');
        const headerRowInput = document.querySelector('input[name="service_records_import_header_row"]');
        const selectedSheet = String(sheetSelector?.value || context?.importSheetName || "").trim();
        const headerMode = normalizeTabularHeaderMode(headerModeSelector?.value || context?.importHeaderMode);
        const headerRowNumber = normalizeTabularHeaderRowNumber(headerRowInput?.value || context?.importHeaderRowNumber);
        if (context) {
            context.importColumnMappings = mergeServiceRecordImportMappings(
                context.importColumnMappings,
                readServiceRecordImportMappingsFromDom(),
            );
        }
        const feedback = document.getElementById("modal-service-records-feedback");
        if (feedback) {
            feedback.textContent = "Recalcul de l'apercu...";
        }
        setServiceRecordsImportProgress(40, "Recalcul de l'apercu...", true);
        refreshNoCodeServiceRecordsImportPreviewFromSheet(selectedSheet, headerMode, headerRowNumber)
            .then(() => {
                setServiceRecordsImportProgress(55, "Apercu pret", true);
                const refreshed = document.getElementById("modal-service-records-feedback");
                if (refreshed) {
                    refreshed.textContent = "Nom de colonne mis a jour.";
                }
            })
            .catch((error) => {
                setServiceRecordsImportProgress(0, "", false);
                const refreshed = document.getElementById("modal-service-records-feedback");
                if (refreshed) {
                    refreshed.textContent = normalizeErrorMessage(error.message);
                }
            });
        return;
    }
    if (target instanceof HTMLInputElement && target.name === "service_records_import_header_row") {
        const headerModeSelector = document.querySelector('select[name="service_records_import_header_mode"]');
        const headerMode = normalizeTabularHeaderMode(headerModeSelector?.value || state.noCodeServiceRecordContext?.importHeaderMode);
        if (headerMode !== "manual") {
            return;
        }
        const sheetSelector = document.querySelector('select[name="service_records_import_sheet"]');
        const selectedSheet = String(sheetSelector?.value || state.noCodeServiceRecordContext?.importSheetName || "").trim();
        const headerRowNumber = normalizeTabularHeaderRowNumber(target.value || state.noCodeServiceRecordContext?.importHeaderRowNumber);
        if (state.noCodeServiceRecordContext) {
            state.noCodeServiceRecordContext.importHeaderMode = headerMode;
            state.noCodeServiceRecordContext.importHeaderRowNumber = headerRowNumber;
            state.noCodeServiceRecordContext.importColumnMappings = [];
        }
        const feedback = document.getElementById("modal-service-records-feedback");
        if (feedback) {
            feedback.textContent = "Recalcul de l'apercu...";
        }
        setServiceRecordsImportProgress(40, "Recalcul de l'apercu...", true);
        refreshNoCodeServiceRecordsImportPreviewFromSheet(selectedSheet, headerMode, headerRowNumber)
            .then(() => {
                setServiceRecordsImportProgress(55, "Apercu pret", true);
                const refreshed = document.getElementById("modal-service-records-feedback");
                if (refreshed) {
                    refreshed.textContent = "Apercu mis a jour.";
                }
            })
            .catch((error) => {
                setServiceRecordsImportProgress(0, "", false);
                const refreshed = document.getElementById("modal-service-records-feedback");
                if (refreshed) {
                    refreshed.textContent = normalizeErrorMessage(error.message);
                }
            });
        return;
    }
    if (target instanceof HTMLInputElement && target.name === "service_child_enabled") {
        const editor = state.noCodeServiceEditor;
        const childEnabled = Boolean(target.checked);
        if (editor) {
            editor.child_enabled = childEnabled;
        }
        const childLabelWrap = document.getElementById("service-child-label-wrap");
        if (childLabelWrap instanceof HTMLElement) {
            childLabelWrap.hidden = !childEnabled;
        }
        return;
    }
    if (
        target instanceof HTMLSelectElement
        && (target.name === "service_relation_type" || target.name === "service_relation_direction")
    ) {
        const editor = state.noCodeServiceEditor;
        const relationId = String(target.dataset.relationId || "").trim();
        const serviceCode = normalizeNoCodeRelationEntityCode(target.dataset.serviceCode || "");
        const relation = relationId ? findNoCodeRelationDraftById(editor, relationId) : findNoCodeRelationDraft(editor, serviceCode);
        if (relation) {
            if (target.name === "service_relation_type") {
                relation.cardinality = normalizeNoCodeRelationCardinality(target.value || "many_to_one");
                relation.relation_type = relation.cardinality;
            } else {
                relation.direction = normalizeNoCodeRelationDirection(target.value || "out");
            }
            renderNoCodeServiceEditorShell();
        }
        return;
    }
    if (
        target instanceof HTMLInputElement
        && [
            "service_relation_required",
            "service_relation_filter_candidates_by_shared_relation",
            "service_relation_show_indirect_relations",
            "service_relation_unique_value_enabled",
        ].includes(target.name)
    ) {
        const editor = state.noCodeServiceEditor;
        const relationId = String(target.dataset.relationId || "").trim();
        const serviceCode = normalizeNoCodeRelationEntityCode(target.dataset.serviceCode || "");
        const relation = relationId ? findNoCodeRelationDraftById(editor, relationId) : findNoCodeRelationDraft(editor, serviceCode);
        if (relation) {
            if (target.name === "service_relation_required") {
                relation.required = Boolean(target.checked);
            } else if (target.name === "service_relation_filter_candidates_by_shared_relation") {
                relation.filter_candidates_by_shared_relation = Boolean(target.checked);
            } else if (target.name === "service_relation_show_indirect_relations") {
                relation.show_indirect_relations = Boolean(target.checked);
            } else if (target.name === "service_relation_unique_value_enabled") {
                const sourceCode = String(relation.source_service_code || noCodeRelationCurrentServiceCode(editor)).trim().toLowerCase();
                const sourceService = findNoCodeRelationEntity(sourceCode) || { code: sourceCode };
                const fields = (sourceCode === noCodeRelationCurrentServiceCode(editor)
                    ? (Array.isArray(editor?.fields) ? editor.fields : [])
                    : noCodeRelationEntityFields(sourceService))
                    .filter((field) => String(field?.field_key || "").trim());
                relation.unique_value_field_key = target.checked
                    ? String(fields[0]?.field_key || "").trim().toLowerCase()
                    : "";
            }
            renderNoCodeServiceEditorShell();
        }
        return;
    }
    if (target instanceof HTMLInputElement && target.name === "service_remote_enabled") {
        const options = document.getElementById("service-remote-options");
        if (options instanceof HTMLElement) {
            options.hidden = !target.checked;
        }
        return;
    }
    if (target instanceof HTMLSelectElement && target.name === "service_relation_unique_value_field_key") {
        const editor = state.noCodeServiceEditor;
        const relationId = String(target.dataset.relationId || "").trim();
        const relation = relationId ? findNoCodeRelationDraftById(editor, relationId) : null;
        if (relation) {
            relation.unique_value_field_key = String(target.value || "").trim().toLowerCase();
            renderNoCodeServiceEditorShell();
        }
        return;
    }
    if (target instanceof HTMLSelectElement && ["service_relation_record_display_mode", "service_relation_assignment_resource"].includes(target.name)) {
        const editor = state.noCodeServiceEditor;
        const relationId = String(target.dataset.relationId || "").trim();
        const relation = relationId ? findNoCodeRelationDraftById(editor, relationId) : null;
        if (relation) {
            if (target.name === "service_relation_record_display_mode") {
                relation.record_display_mode = ["standard", "hidden", "assignment"].includes(String(target.value || "")) ? String(target.value) : "standard";
                if (relation.record_display_mode !== "assignment") {
                    relation.assignment_resource_service_code = "";
                }
            } else {
                relation.assignment_resource_service_code = normalizeNoCodeRelationEntityCode(target.value || "");
            }
            renderNoCodeServiceEditorShell();
        }
        return;
    }
    if (target instanceof HTMLInputElement && target.name === "service_is_active") {
        const editor = state.noCodeServiceEditor;
        if (editor) {
            editor.is_active = Boolean(target.checked);
        }
        return;
    }
    if (target instanceof HTMLInputElement && target.name === "service_is_technical") {
        const editor = state.noCodeServiceEditor;
        if (editor) {
            syncNoCodeServiceEditorFromForm();
            editor.is_technical = Boolean(target.checked);
            if (editor.is_technical) {
                editor.is_active = true;
            }
            renderNoCodeServiceEditorShell();
        }
        return;
    }
    if (target instanceof HTMLInputElement && target.name === "service_credentials_enabled") {
        const editor = state.noCodeServiceEditor;
        if (editor) {
            editor.credentials_enabled = Boolean(target.checked);
        }
        return;
    }
    if (target.id === "service-field-kind" && target instanceof HTMLSelectElement) {
        const editor = state.noCodeServiceEditor;
        const normalizedKind = normalizeNoCodeKind(target.value);
        if (editor?.fieldEditor) {
            editor.fieldEditor.field_kind = normalizedKind;
            if (normalizedKind !== "list") {
                editor.fieldEditor.list_source_kind = "local";
                editor.fieldEditor.shared_list_code = "";
                editor.fieldEditor.batch_editable = false;
            }
        }
        const listSourceWrap = document.getElementById("service-field-list-source-wrap");
        if (listSourceWrap instanceof HTMLElement) {
            listSourceWrap.hidden = normalizedKind !== "list";
        }
        const listSourceSelect = document.getElementById("service-field-list-source");
        const sourceKind = listSourceSelect instanceof HTMLSelectElement
            ? normalizeListSourceKind(listSourceSelect.value)
            : "local";
        const optionsWrap = document.getElementById("service-field-options-wrap");
        if (optionsWrap instanceof HTMLElement) {
            optionsWrap.hidden = normalizedKind !== "list" || sourceKind !== "local";
        }
        const sharedWrap = document.getElementById("service-field-shared-wrap");
        if (sharedWrap instanceof HTMLElement) {
            sharedWrap.hidden = normalizedKind !== "list" || sourceKind !== "shared";
        }
        const batchEditableWrap = document.getElementById("service-field-batch-editable-wrap");
        if (batchEditableWrap instanceof HTMLElement) {
            batchEditableWrap.hidden = normalizedKind !== "list";
        }
        return;
    }
    if (target.id === "service-field-list-source" && target instanceof HTMLSelectElement) {
        const editor = state.noCodeServiceEditor;
        const sourceKind = normalizeListSourceKind(target.value);
        if (editor?.fieldEditor) {
            editor.fieldEditor.list_source_kind = sourceKind;
            if (sourceKind !== "shared") {
                editor.fieldEditor.shared_list_code = "";
            }
        }
        const kindSelect = document.getElementById("service-field-kind");
        const fieldKind = kindSelect instanceof HTMLSelectElement
            ? normalizeNoCodeKind(kindSelect.value)
            : "text";
        const optionsWrap = document.getElementById("service-field-options-wrap");
        if (optionsWrap instanceof HTMLElement) {
            optionsWrap.hidden = fieldKind !== "list" || sourceKind !== "local";
        }
        const sharedWrap = document.getElementById("service-field-shared-wrap");
        if (sharedWrap instanceof HTMLElement) {
            sharedWrap.hidden = fieldKind !== "list" || sourceKind !== "shared";
        }
        return;
    }
    if (target.id === "service-field-shared-list" && target instanceof HTMLSelectElement) {
        const editor = state.noCodeServiceEditor;
        if (editor?.fieldEditor) {
            editor.fieldEditor.shared_list_code = String(target.value || "").trim().toLowerCase();
        }
    }
});

appModalBackdrop.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    focusFirstModalElement();
});
appModalClose.addEventListener("click", async () => {
    await closeModalWithContextBack();
});

document.addEventListener("click", (event) => {
    if (!topMenuPanel.hidden && !topMenuPanel.contains(event.target) && !event.target.closest(".menu-btn")) {
        closeTopMenu();
    }
    if (profileMenuController?.isOpen?.() && !profileMenuController.contains?.(event.target)) {
        closeProfileMenu();
    }
    if (
        cardsContextMenu instanceof HTMLElement
        && !cardsContextMenu.hidden
        && !cardsContextMenu.contains(event.target)
    ) {
        closeCardsContextMenu();
    }
});

document.addEventListener("focusin", (event) => {
    if (
        isAppModalOpen()
        && appModalPanel instanceof HTMLElement
        && event.target instanceof Node
        && !appModalPanel.contains(event.target)
        && !portalMenuBar?.contains(event.target)
        && !topMenuPanel?.contains(event.target)
        && !isPortalOverlayDialogTarget(event.target)
    ) {
        focusFirstModalElement();
    }
});

document.addEventListener("keydown", async (event) => {
    keepModalFocusInside(event);
    if (event.key === "Escape") {
        if (isPortalOverlayDialogTarget(event.target)) {
            return;
        }
        if (isAppModalOpen()) {
            event.preventDefault();
            await closeModalWithContextBack();
            return;
        }
        closeTopMenu();
        closeProfileMenu();
        closeCardsContextMenu();
    }
});

document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
        stopPortalMonitoringSummaryRefresh();
        return;
    }
    if (portalMonitoringModuleVisible()) {
        startPortalMonitoringSummaryRefresh();
        reloadPortalMonitoringSummaryForTile().catch(() => {});
    }
});

boot().catch((error) => {
    setError(normalizeErrorMessage(error.message));
    showAuth();
});
