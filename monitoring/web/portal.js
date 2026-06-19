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
    noCodeServiceEditorContext: null,
    noCodeServiceRecordContext: null,
    noCodeRecordEditor: null,
    noCodeSharedListEditor: null,
    noCodeSharedListItemsContext: null,
    noCodeSharedListItemEditor: null,
    noCodeSharedListsWarning: "",
    monitoringPrewarmStarted: false,
    monitoringSummary: null,
    monitoringSummaryLoaded: false,
    portalModules: [],
    portalContextModuleCode: "",
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
const profileMenuButton = document.getElementById("profile-menu-button");
const dashboardEditButton = document.getElementById("dashboard-edit-button");
const cardsGrid = document.getElementById("cards-grid");
const menuSupervision = document.getElementById("menu-supervision");
const menuConfiguration = document.getElementById("menu-configuration");
const menuHelp = document.getElementById("menu-help");
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
        closeModal();
    },
}) || null;
let adminRolesTreeView = null;
let adminUsersTreeView = null;
let noCodeServicesTreeView = null;
let sharedListsTreeView = null;
let sharedListItemsTreeView = null;
let storageRemoteTreeView = null;
let storageLocalTreeView = null;
let portalDashboardEditor = null;
let profileMenuController = null;
let authFailureHandling = false;

const MODULE_META = {
    monitoring: {
        title: "Monitoring reseau",
        subtitle: "Supervision, inventaire, actions reseau",
    },
    admin: {
        title: "Administration",
        subtitle: "Gestion utilisateurs, roles et habilitations",
    },
};
const NO_CODE_FIELD_KINDS = ["text", "ip", "url", "date", "list"];
const NO_CODE_FIELD_KIND_LABELS = {
    text: "Texte",
    ip: "IP",
    url: "URL",
    date: "Date",
    list: "Liste",
};
const NO_CODE_CREDENTIAL_LOGIN_KEY = "device_login";
const NO_CODE_CREDENTIAL_PASSWORD_KEY = "device_password";
const NO_CODE_CREDENTIAL_FIELD_KEYS = new Set([
    NO_CODE_CREDENTIAL_LOGIN_KEY,
    NO_CODE_CREDENTIAL_PASSWORD_KEY,
]);
const NO_CODE_CREDENTIAL_LEGACY_LOGIN_KEYS = [NO_CODE_CREDENTIAL_LOGIN_KEY, "login"];
const NO_CODE_CREDENTIAL_LEGACY_PASSWORD_KEYS = [NO_CODE_CREDENTIAL_PASSWORD_KEY, "password"];
const RECORD_IMPORT_CREDENTIAL_MODES = [
    { value: "preserve_on_blank", label: "Conserver si vide (recommande)" },
    { value: "overwrite", label: "Ecraser avec le fichier" },
    { value: "ignore", label: "Ignorer les identifiants du fichier" },
];
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
        ? "Premiere connexion: creer un mot de passe administrateur."
        : "Connexion requise avec un compte pour ouvrir le portail des modules.";
    authSubmit.textContent = mustChangePassword ? "Creer le mot de passe" : "Se connecter";
    passwordInput.autocomplete = "current-password";
    usernameInput.autocomplete = "username";
    if (!String(usernameInput.value || "").trim()) {
        usernameInput.value = "sa";
    }
    if (usernameField) {
        usernameField.hidden = mustChangePassword;
    }
    if (passwordField) {
        passwordField.hidden = mustChangePassword;
    }
    usernameInput.required = !mustChangePassword;
    passwordInput.required = !mustChangePassword;
    newPasswordField.hidden = !mustChangePassword;
    newPasswordInput.required = mustChangePassword;
    confirmPasswordField.hidden = !mustChangePassword;
    confirmPasswordInput.required = mustChangePassword;
    authForm.dataset.mode = mustChangePassword ? "bootstrap" : "login";
    await loadPublicUiConfig();
    return { mustChangePassword };
}

function enablePasswordChangeMode() {
    authForm.dataset.mode = "bootstrap";
    authSubmit.textContent = "Creer le mot de passe";
    if (usernameField) {
        usernameField.hidden = true;
    }
    if (passwordField) {
        passwordField.hidden = true;
    }
    usernameInput.required = false;
    passwordInput.required = false;
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
    if (modalController) {
        modalController.open(title, bodyMarkup, options);
        return;
    }
    appModalTitle.textContent = title;
    appModalBody.innerHTML = bodyMarkup;
    appModalPanel.style.width = options.width || "min(860px, calc(100vw - 40px))";
    appModal.hidden = false;
}

function closeModal() {
    if (modalController) {
        modalController.close("manual");
        exitInlineModalMode();
        return;
    }
    appModal.hidden = true;
    appModalBody.innerHTML = "";
    exitInlineModalMode();
    clearWatermarkEditorDraft();
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
}

function topMenuDefinitions() {
    const sharedDefs = window.NMPSharedMenu?.commonDefinitions?.() || {};
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
            label: "Notification...",
            action: "menu:notifications",
            disabled: !canManageRoles,
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
                            ...(hasUsersAdminAccess || canManageRoles ? [{ label: "Utilisateurs...", action: "menu:admin:users" }] : []),
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
                closeModal();
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
                closeModal();
            },
        });
        return;
    }
    if (state.openTopMenu === menuKey && !topMenuPanel.hidden) {
        closeTopMenu();
        return;
    }
    closeCardsContextMenu();
    closeModal();
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
    const extraToolsMarkup = String(options.extraToolsMarkup || "");
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
    const toolsMarkup = ((!searchInTitleRow && searchMarkup) || extraToolsMarkup)
        ? `
            <div class="inventory-controls shared-treeview-tools">
                ${searchInTitleRow ? "" : searchMarkup}
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

function tableBindHeaderSort(headElement, options = {}) {
    const shared = window.NMPSharedUi?.tableTools?.bindHeaderSort;
    if (typeof shared !== "function") {
        return;
    }
    shared(headElement, options);
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
            getRows: () => (Array.isArray(context?.records) ? context.records : []),
            getColumns: () => {
                const dynamicCols = noCodeRecordColumns(context?.service || null)
                    .map((column) => ({
                        key: String(column?.key || ""),
                        label: String(column?.label || ""),
                        sortable: true,
                    }));
                return [...dynamicCols, { key: "", label: "Actions", sortable: false }];
            },
            searchText: (row) => {
                const columns = noCodeRecordColumns(context?.service || null);
                const values = [
                    String(row?.id || ""),
                    String(row?.updated_at || ""),
                    ...columns.map((column) => String(noCodeRecordColumnValue(row, column) || "")),
                    ...(Array.isArray(row?.children) ? row.children.map((child) => `${child?.name || ""} ${child?.code || ""}`) : []),
                ];
                return values.join(" ").toLowerCase();
            },
            compareRows: (column, direction, left, right) => {
                const columns = noCodeRecordColumns(context?.service || null);
                const columnsByKey = new Map(columns.map((entry) => [String(entry.key || ""), entry]));
                return noCodeRecordCompareByColumn(columnsByKey, column, direction, left, right);
            },
            getRowKey: (row) => String(row?.id || row?.record_id || ""),
            renderRowCells: (row) => {
                const columns = noCodeRecordColumns(context?.service || null);
                const valueCells = columns
                    .map((column) => `<td>${escapeHtml(String(noCodeRecordColumnValue(row, column) || ""))}</td>`)
                    .join("");
                return `
                    ${valueCells}
                    <td class="inventory-row-actions">
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
            },
        });
        this._context = context;
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
            emptyMessage: "Aucun utilisateur",
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
        tbody.innerHTML = "<tr><td colspan='4'>Aucun utilisateur</td></tr>";
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
    const monitoringModule = findAdminModuleRow("monitoring");
    const baseRows = monitoringModule
        ? [{
            row_kind: "monitoring",
            code: "monitoring",
            label: String(monitoringModule?.label || "Monitoring").trim() || "Monitoring",
            is_active: Boolean(monitoringModule?.is_active),
            credentials_enabled: true,
            fields_count: 0,
            child_label: "",
            version_token: "",
        }]
        : [];
    const dynamicRows = noCodeServiceRows().map((service) => ({
        row_kind: "service",
        code: String(service?.code || "").trim(),
        label: String(service?.label || service?.code || "").trim() || String(service?.code || ""),
        is_active: Boolean(service?.is_active),
        credentials_enabled: Boolean(service?.credentials_enabled),
        fields_count: noCodeCustomServiceFields(service).length,
        child_label: Boolean(service?.child_enabled) ? String(service?.child_label || "Elements lies").trim() || "Elements lies" : "",
        version_token: String(service?.version_token || ""),
    }));
    return [...baseRows, ...dynamicRows];
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
                const isMonitoring = String(row?.row_kind || "") === "monitoring";
                const active = Boolean(row?.is_active);
                const credentials = Boolean(row?.credentials_enabled);
                const code = String(row?.code || "");
                const token = String(row?.version_token || "");
                return `
                    <td>${escapeHtml(code)}</td>
                    <td>${escapeHtml(String(row?.label || code))}</td>
                    <td>${active ? "actif" : "desactive"}</td>
                    <td>${credentials ? "actifs" : "inactifs"}</td>
                    <td>${isMonitoring ? "-" : escapeHtml(String(row?.fields_count || 0))}</td>
                    <td class="inventory-row-actions">
                        ${isMonitoring
        ? createActionButtonMarkup({
            className: "inventory-action-btn",
            type: "button",
            action: "service:monitoring:toggle-active",
            label: active ? "OFF" : "ON",
            title: active ? "Desactiver" : "Activer",
        })
        : [
            createActionButtonMarkup({
                className: "inventory-action-btn",
                type: "button",
                action: "service:definition:toggle-active",
                label: active ? "OFF" : "ON",
                title: active ? "Desactiver" : "Activer",
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
                title: "Modifier",
                data: { service_code: code, service_version_token: token },
            }),
            createIconActionButtonMarkup({
                icon: "delete",
                danger: true,
                action: "service:definition:delete",
                title: "Supprimer",
                data: { service_code: code, service_version_token: token },
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

function renderStorageTreeViews() {
    if (storageRemoteTreeView instanceof StorageRemoteTreeView) {
        storageRemoteTreeView.render();
    }
    if (storageLocalTreeView instanceof StorageLocalTreeView) {
        storageLocalTreeView.render();
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

async function openServiceModuleFromPortal(serviceCode) {
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
    await openNoCodeServiceRecords(normalizedCode, { inline: true });
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
    openNoCodeServiceEditor(service, { inline: true, context: { source: "standalone" } });
}

function normalizeMonitoringSummary(summary) {
    if (!summary || typeof summary !== "object") {
        return null;
    }
    return {
        running_any: Boolean(summary.running_any),
        running_all: Boolean(summary.running_all),
        total_running: Math.max(0, Number(summary.total_running || 0)),
        total_types: Math.max(0, Number(summary.total_types || 0)),
    };
}

async function loadPortalMonitoringSummary(options = {}) {
    const forceRefresh = Boolean(options.forceRefresh);
    if (!forceRefresh && state.monitoringSummaryLoaded) {
        return state.monitoringSummary;
    }
    try {
        const summary = await requestJson("/monitoring/summary");
        state.monitoringSummary = normalizeMonitoringSummary(summary);
    } catch (_error) {
        state.monitoringSummary = null;
    } finally {
        state.monitoringSummaryLoaded = true;
    }
    return state.monitoringSummary;
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
    const canOpen = Boolean(isActive && granted && routePath);
    if (!canOpen) {
        openModal("Module non disponible", `<p class="muted">${escapeHtml(buildModuleBlockedReason(moduleRow))}</p>`);
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
    const isActive = Boolean(moduleRow?.is_active);
    const granted = Boolean(moduleRow?.granted);
    const canOpen = Boolean(isActive && granted && routePath);
    const canEditDynamicService = Boolean(serviceCode) && serviceCode !== "monitoring";
    const monitoringMeta = monitoringRuntimeStatusMeta(moduleRow);
    const monitoringControlDisabled = !Boolean(isActive && granted);
    const serviceItems = [
        '<div class="context-menu-label">Service</div>',
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

async function handleModuleCardsClick(event) {
    if (ensurePortalDashboardEditor().isEditing()) {
        return;
    }
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

    return `
        <article class="dash-card panel ${canOpen ? "clickable" : ""} ${status.ghost ? "module-ghost" : ""}" data-module-code="${escapeHtml(code)}" data-dashboard-card-id="${escapeHtml(code)}" data-dashboard-card-active="${isActive ? "true" : "false"}">
            <div class="dash-card-title">${escapeHtml(title)}</div>
            <div class="dash-card-sub">${escapeHtml(subtitle)}</div>
            <div class="dash-card-stats">
                <span class="${escapeHtml(status.badgeClass)}">${escapeHtml(status.text)}</span>
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
    if (!modules.length) {
        state.portalModules = [];
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
    ensurePortalDashboardEditor().refresh().catch(() => {
        ensurePortalDashboardEditor().decorateCards();
    });
}

async function loadPortalModules(options = {}) {
    const forceRefresh = Boolean(options.forceRefresh);
    if (!forceRefresh && state.moduleAccessLoaded) {
        await loadPortalMonitoringSummary({ forceRefresh: false });
        renderModuleCards(state.moduleAccess);
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
        await loadPortalMonitoringSummary({ forceRefresh: true });
        renderModuleCards(state.moduleAccess);
        scheduleMonitoringPrewarm(state.moduleAccess);
        return state.moduleAccess;
    } catch (_error) {
        state.moduleAccess = [];
        state.moduleAccessLoaded = true;
        state.monitoringSummaryLoaded = false;
        await loadPortalMonitoringSummary({ forceRefresh: true });
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
    return `<section class="modal-section"><p class="error-text">Interface utilisateurs indisponible.</p></section>`;
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
    return `<section class="modal-section"><p class="error-text">Formulaire utilisateur indisponible.</p></section>`;
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
    }));
}

async function importServiceFieldsFromFile(file, sheetName = "", headerMode = "auto", headerRowNumber = 1) {
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
            effectiveHeaderMode: normalizeTabularHeaderMode(payload?.effective_header_mode || "auto"),
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

function promptSharedListImportSheetSelection(availableSheets = [], selectedSheetName = "") {
    const sheets = Array.isArray(availableSheets)
        ? availableSheets.map((item) => String(item || "").trim()).filter(Boolean)
        : [];
    if (sheets.length <= 1) {
        return sheets[0] || "";
    }
    const defaultSheet = String(selectedSheetName || sheets[0] || "").trim();
    const promptLabel = sheets.map((name, index) => `${index + 1}. ${name}`).join("\n");
    const rawInput = window.prompt(
        `Plusieurs feuilles detectees.\n\n${promptLabel}\n\nSaisir le numero ou le nom de la feuille a importer:`,
        defaultSheet,
    );
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

function promptTabularHeaderSelection(defaultMode = "auto", defaultRow = 1) {
    const initialMode = normalizeTabularHeaderMode(defaultMode);
    const rawMode = window.prompt(
        "Entete du tableau : saisir 'auto', 'manual' ou 'first'.",
        initialMode,
    );
    if (rawMode == null) {
        return null;
    }
    const mode = normalizeTabularHeaderMode(rawMode);
    if (mode !== "manual") {
        return { mode, rowNumber: 1 };
    }
    const rawRow = window.prompt(
        "Numero de ligne pour l'entete (a partir de 1).",
        String(normalizeTabularHeaderRowNumber(defaultRow)),
    );
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
        const selectedSheet = promptSharedListImportSheetSelection(imported.availableSheets, imported.selectedSheetName);
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
        const headerChoice = promptTabularHeaderSelection(imported.effectiveHeaderMode, imported.detectedHeaderRowNumber);
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
        const confirmed = window.confirm(
            `Importer ${imported.items.length} valeur(s) dans la liste partagee '${listCode}' ?\n\nApercu: ${preview}`,
        );
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

function noCodeRecordHasCredentialValues(record) {
    const values = record?.values && typeof record.values === "object" ? record.values : {};
    return Boolean(
        noCodeCredentialValueFromMap(values, "login")
        || noCodeCredentialValueFromMap(values, "password"),
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
        }))
        : [];
    return {
        mode: service ? "edit" : "create",
        code: String(service?.code || "").trim(),
        label: String(service?.label || "").trim(),
        is_active: service ? Boolean(service?.is_active) : true,
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
        importHeaderMode: "auto",
        importHeaderRowNumber: 1,
    };
}

function noCodeServiceRows() {
    return Array.isArray(state.adminData.services) ? state.adminData.services : [];
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
            <div class="type-schema-field-actions">
                ${createActionButtonMarkup({ preset: "cancel", action: "service:field:cancel" })}
                ${createActionButtonMarkup({ preset: "save", type: "button", action: "service:field:save", label: "Enregistrer le champ" })}
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
                            <span>${escapeHtml(kindLabel)}${field.required ? " | obligatoire" : ""}${escapeHtml(sourceLabel)}</span>
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
        const hasPreview = Boolean(preview && Array.isArray(preview.fields) && preview.fields.length > 0);
        previewWrap.hidden = !hasPreview;
        if (hasPreview) {
            const optionsLimit = 6;
            const sourceHeaders = Array.isArray(preview.sourceHeaders) ? preview.sourceHeaders : [];
            const sourceRowsPreview = Array.isArray(preview.sourceRowsPreview) ? preview.sourceRowsPreview : [];
            const availableSheets = Array.isArray(preview.availableSheets) ? preview.availableSheets : [];
            const selectedSheetName = String(preview.selectedSheetName || "").trim();
            const headerMode = normalizeTabularHeaderMode(editor.importHeaderMode || preview.effectiveHeaderMode || "auto");
            const headerRowNumber = normalizeTabularHeaderRowNumber(editor.importHeaderRowNumber || preview.detectedHeaderRowNumber || 1);
            const detectedHeaderRow = normalizeTabularHeaderRowNumber(preview.detectedHeaderRowNumber || headerRowNumber);
            const effectiveHeaderMode = normalizeTabularHeaderMode(preview.effectiveHeaderMode || headerMode);
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
            const previewRows = (preview.fields || []).map((field, index) => {
                const label = String(field?.label || field?.field_key || `Champ ${index + 1}`).trim();
                const kind = noCodeKindLabel(String(field?.field_kind || "text"));
                const options = parseNoCodeOptions(field?.options || "");
                const optionsLabel = options.length
                    ? options.slice(0, optionsLimit).join(", ") + (options.length > optionsLimit ? ` (+${options.length - optionsLimit})` : "")
                    : "-";
                return `
                    <div class="type-schema-custom-field-row">
                        <div class="type-schema-custom-field-meta">
                            <strong>${escapeHtml(label)}</strong>
                            <span>${escapeHtml(kind)} | Options: ${escapeHtml(optionsLabel)}</span>
                        </div>
                    </div>
                `;
            }).join("");
            previewWrap.innerHTML = `
                <section class="type-schema-field-editor">
                    <div class="type-schema-fields-head">
                        <h3>Apercu de l'import</h3>
                        <div class="inventory-row-actions">
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
                    </div>
                    <p class="muted">${escapeHtml(String(preview.filename || "Fichier"))} | ${Number(preview.detectedColumns || 0)} colonne(s) detectee(s) | ${Number(preview.detectedRows || 0)} ligne(s) analysee(s)</p>
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
                    </div>
                    <p class="muted">Entete active: ligne ${detectedHeaderRow} (${effectiveHeaderMode}).</p>
                    <h4>Apercu source</h4>
                    ${buildTabularSourcePreviewTable(sourceHeaders, sourceRowsPreview)}
                    <h4>Champs proposes</h4>
                    <div class="type-schema-custom-fields-list">${previewRows}</div>
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
    const title = editor.mode === "edit" ? "Modifier le service" : "Nouveau service";
    return `
        <form id="modal-service-form" class="modal-form" data-edit-code="${escapeHtml(editor.code)}">
            <section class="modal-section">
                <h3>${escapeHtml(title)}</h3>
                <div class="modal-settings-grid">
                    ${createFieldMarkup("service_label", "Nom du service", editor.label || "")}
                    <div id="service-child-label-wrap" ${editor.child_enabled ? "" : "hidden"}>
                        ${createFieldMarkup("service_child_label", "Nom de la sous-liste", editor.child_label || "Elements lies")}
                    </div>
                </div>
                <label class="check-field">
                    <input name="service_child_enabled" type="checkbox" ${editor.child_enabled ? "checked" : ""}>
                    <span>Ajouter une sous-liste par fiche (ex: Utilisateurs)</span>
                </label>
                <label class="check-field">
                    <input name="service_is_active" type="checkbox" ${editor.is_active ? "checked" : ""}>
                    <span>Service actif (tuile visible dans le portail)</span>
                </label>
                <label class="check-field">
                    <input name="service_credentials_enabled" type="checkbox" ${editor.credentials_enabled ? "checked" : ""}>
                    <span>Gestion des identifiants (login + mot de passe)</span>
                </label>
            </section>
            <section class="modal-section type-schema-fields-section">
                <div class="type-schema-fields-head">
                    <h3>Champs de la fiche</h3>
                    <div class="inventory-row-actions">
                        ${createActionButtonMarkup({
                            preset: "export",
                            action: "service:field:export",
                            label: "Exporter CSV",
                            title: "Exporter les champs au format CSV",
                            disabled: !editor.code,
                        })}
                        ${createActionButtonMarkup({
                            preset: "import",
                            className: "toolbar-btn",
                            action: "service:field:import",
                            label: "Importer",
                            title: "Importer un fichier CSV ou XLSX (detection automatique)",
                        })}
                        ${createIconActionButtonMarkup({
                            icon: "add",
                            action: "service:field:add",
                            title: "Ajouter un champ",
                        })}
                    </div>
                </div>
                <p class="muted">Import CSV/XLSX: analyse automatique du fichier, apercu des champs detectes, puis application.</p>
                <div id="service-import-preview-wrap" hidden></div>
                <div id="service-field-list" class="type-schema-custom-fields-list"></div>
            </section>
            <p id="modal-service-form-feedback" class="muted inventory-feedback"></p>
            ${createModalActionsMarkup({
                buttons: [
                    { preset: "back", action: "service:back" },
                    {
                        preset: editor.mode === "edit" ? "save" : "add",
                        label: editor.mode === "edit" ? "Enregistrer" : "Ajouter le service",
                    },
                ],
            })}
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
    const listSourceSelect = document.getElementById("service-field-list-source");
    const sharedListSelect = document.getElementById("service-field-shared-list");
    const optionsInput = document.getElementById("service-field-options");
    const defaultInput = document.getElementById("service-field-default");
    if (
        !(labelInput instanceof HTMLInputElement)
        || !(kindSelect instanceof HTMLSelectElement)
        || !(requiredCheckbox instanceof HTMLInputElement)
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
    const fields = noCodeCustomServiceFields(service);
    const columns = [
        ...fields.map((field) => ({
            key: `field:${String(field?.field_key || "").trim()}`,
            label: String(field?.label || field?.field_key || "").trim() || String(field?.field_key || ""),
            kind: normalizeNoCodeKind(field?.field_kind || "text"),
            field_key: String(field?.field_key || "").trim(),
        })),
    ];
    if (Boolean(service?.credentials_enabled)) {
        columns.push(
            { key: "credential:login", label: "Login", kind: "text" },
            { key: "credential:password", label: "Mot de passe", kind: "text" },
        );
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
    if (key === "credential:password") {
        return noCodeCredentialValueFromMap(row?.values || {}, "password");
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
    return "";
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

function renderNoCodeServiceRecordsTable() {
    const context = state.noCodeServiceRecordContext;
    if (!context?.service) {
        return;
    }
    const tree = ensureServiceRecordsTreeView(context);
    if (tree) {
        tree.render();
        return;
    }
    const body = document.getElementById("service-records-body");
    if (body instanceof HTMLElement) {
        body.innerHTML = `<tr><td>Aucune fiche</td></tr>`;
    }
}

function bindNoCodeServiceRecordsInteractions() {
    const context = state.noCodeServiceRecordContext;
    ensureServiceRecordsTreeView(context);
}

function buildNoCodeRecordsModalMarkup(context) {
    const service = context?.service || null;
    const serviceLabel = String(service?.label || service?.code || "").trim();
    const importPreview = buildNoCodeRecordsImportPreviewMarkup(context);
    return buildTreeSectionMarkup({
        title: `Inventaire ${serviceLabel || "Service"}`,
        titleActionsMarkup: `
            ${createActionButtonMarkup({
                className: "toolbar-btn",
                type: "button",
                action: "service:definition:edit",
                label: `Modifier Service ${serviceLabel || "Service"}`,
                title: "Modifier la definition du service",
                data: { service_code: String(service?.code || "") },
            })}
            ${createActionButtonMarkup({
                preset: "export",
                action: "service:records:export",
                label: "Exporter CSV",
            })}
            ${createActionButtonMarkup({
                preset: "import",
                className: "toolbar-btn",
                action: "service:records:import",
                label: "Importer",
                title: "Importer un fichier CSV ou XLSX (detection automatique)",
            })}
            ${createActionButtonMarkup({
                preset: "add",
                className: "toolbar-btn",
                type: "button",
                action: "service:record:add",
                label: "Ajouter fiche",
            })}
        `,
        searchId: "service-records-search",
        searchLabel: "Filtre",
        searchPlaceholder: "ID, valeurs, elements lies...",
        searchInTitleRow: true,
        beforeTableMarkup: importPreview,
        headId: "service-records-head",
        bodyId: "service-records-body",
        afterTableMarkup: `
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
    const fields = noCodeCustomServiceFields(service);
    const visibleFields = fields.slice(0, 5);
    const headCells = visibleFields.map((field) => `<th>${escapeHtml(String(field.label || field.field_key || ""))}</th>`).join("");
    const rowsMarkup = preview.rows.slice(0, 12).map((row) => {
        const values = row?.values || {};
        const valueCells = visibleFields.map((field) => {
            const key = String(field.field_key || "");
            return `<td>${escapeHtml(String(values[key] || ""))}</td>`;
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
    const availableSheets = Array.isArray(preview.availableSheets) ? preview.availableSheets : [];
    const selectedSheetName = String(preview.selectedSheetName || context?.importSheetName || "").trim();
    const headerMode = normalizeTabularHeaderMode(context?.importHeaderMode || preview.effectiveHeaderMode || "auto");
    const headerRowNumber = normalizeTabularHeaderRowNumber(context?.importHeaderRowNumber || preview.detectedHeaderRowNumber || 1);
    const detectedHeaderRow = normalizeTabularHeaderRowNumber(preview.detectedHeaderRowNumber || headerRowNumber);
    const effectiveHeaderMode = normalizeTabularHeaderMode(preview.effectiveHeaderMode || headerMode);
    const issues = Array.isArray(preview.issues) ? preview.issues.filter((item) => String(item || "").trim()) : [];
    const credentialMode = normalizeRecordsImportCredentialMode(context?.importCredentialMode);
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
    return `
        <section class="modal-section type-schema-fields-section">
            <div class="type-schema-fields-head">
                <h3>Apercu de l'import</h3>
                <div class="inventory-row-actions">
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
            ${service?.credentials_enabled ? `
                <div class="modal-settings-grid">
                    <label class="field">
                        <span>Identifiants existants</span>
                        <select name="service_records_import_credential_mode">
                            ${credentialModeOptions}
                        </select>
                    </label>
                </div>
            ` : ""}
            ${issuesMarkup}
            <h4>Apercu source</h4>
            ${buildTabularSourcePreviewTable(sourceHeaders, sourceRowsPreview)}
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

function buildNoCodeRecordEditorMarkup() {
    const context = state.noCodeServiceRecordContext;
    const editor = state.noCodeRecordEditor;
    if (!context || !editor) {
        return "";
    }
    const service = context.service;
    const fields = noCodeCustomServiceFields(service);
    const credentialsEnabled = Boolean(service?.credentials_enabled);
    const credentialLogin = String(editor?.credentials?.login || "");
    const credentialPassword = String(editor?.credentials?.password || "");
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
    return `
        <form id="modal-service-record-form" class="modal-form" data-record-id="${escapeHtml(String(editor.recordId || ""))}">
            <section class="modal-section">
                <h3>${escapeHtml(editor.mode === "edit" ? "Modifier la fiche" : "Nouvelle fiche")}</h3>
                <div class="modal-settings-grid">
                    ${fieldMarkup}
                </div>
            </section>
            ${credentialsEnabled ? `
                <section class="modal-section">
                    <h3>Identifiants</h3>
                    <div class="modal-settings-grid">
                        <label class="field">
                            <span>Login</span>
                            <input name="record_credential_login" type="text" value="${escapeHtml(credentialLogin)}" autocomplete="off">
                        </label>
                        <label class="field">
                            <span>Mot de passe</span>
                            <input name="record_credential_password" type="text" value="${escapeHtml(credentialPassword)}" autocomplete="off">
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

async function openNoCodeServicesModal(options = {}) {
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
            await openNoCodeServiceRecords(serviceCode, { inline });
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

function openNoCodeServiceEditor(service = null, options = {}) {
    state.noCodeSharedListEditor = null;
    state.noCodeSharedListItemsContext = null;
    state.noCodeSharedListItemEditor = null;
    state.noCodeServiceEditorContext = captureNoCodeServiceEditorContext(options);
    state.noCodeServiceEditor = createNoCodeServiceEditor(service);
    openModal(
        service ? "Service - Edition" : "Service - Creation",
        buildNoCodeServiceEditorMarkup(),
        noCodeInlineOptions("min(1120px, calc(100vw - 40px))", options),
    );
    renderNoCodeServiceEditor();
}

async function openNoCodeServiceRecords(serviceCode, options = {}) {
    const normalizedCode = normalizeNoCodeText(serviceCode).toLowerCase();
    if (!normalizedCode) {
        throw new Error("Service introuvable.");
    }
    let service = findNoCodeService(normalizedCode);
    if (!service) {
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
    const records = await requestJson(`/admin/custom-services/${encodeURIComponent(effectiveServiceCode)}/records`);
    state.noCodeServiceRecordContext = {
        service,
        records: Array.isArray(records) ? records : [],
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
        importCredentialMode: sameService
            ? normalizeRecordsImportCredentialMode(previousContext?.importCredentialMode)
            : "preserve_on_blank",
        _recordsTreeView: null,
        searchQuery: sameService ? String(previousContext?.searchQuery || "") : "",
        sort: normalizeNoCodeRecordSortState(
            service,
            sameService && previousContext?.sort
                ? { column: String(previousContext.sort.column || ""), direction: String(previousContext.sort.direction || "asc") }
                : null,
        ),
    };
    state.noCodeRecordEditor = null;
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

async function refreshNoCodeServiceFieldImportPreviewFromSheet(sheetName = "", headerMode = "auto", headerRowNumber = 1) {
    const editor = state.noCodeServiceEditor;
    const importFile = editor?.importFile || null;
    if (!editor || !importFile) {
        throw new Error("Aucun fichier d'import en attente.");
    }
    const normalizedHeaderMode = normalizeTabularHeaderMode(headerMode);
    const normalizedHeaderRow = normalizeTabularHeaderRowNumber(headerRowNumber);
    const imported = await importServiceFieldsFromFile(importFile, sheetName, normalizedHeaderMode, normalizedHeaderRow);
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
    };
    editor.importHeaderMode = normalizeTabularHeaderMode(imported.effectiveHeaderMode || normalizedHeaderMode);
    editor.importHeaderRowNumber = normalizeTabularHeaderRowNumber(imported.detectedHeaderRowNumber || normalizedHeaderRow || 1);
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
    const preview = await previewServiceRecordsFromFile(
        importFile,
        serviceCode,
        credentialMode,
        sheetName,
        normalizedHeaderMode,
        normalizedHeaderRow,
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
    renderNoCodeServiceRecordsModal();
}

function openNoCodeRecordEditor(record = null, options = {}) {
    const context = state.noCodeServiceRecordContext;
    if (!context || !context.service) {
        return;
    }
    const service = context.service;
    const fields = noCodeCustomServiceFields(service);
    const values = {};
    for (const field of fields) {
        const key = String(field.field_key || "").trim();
        values[key] = String(record?.values?.[key] || "");
    }
    state.noCodeRecordEditor = {
        mode: record ? "edit" : "create",
        recordId: String(record?.id || ""),
        versionToken: String(record?.version_token || ""),
        values,
        credentials: {
            login: noCodeCredentialValueFromMap(record?.values || {}, "login"),
            password: noCodeCredentialValueFromMap(record?.values || {}, "password"),
        },
        children: Array.isArray(record?.children)
            ? record.children.map((row) => ({ name: String(row?.name || ""), code: String(row?.code || "") }))
            : [],
    };
    openModal(
        record ? "Edition fiche" : "Nouvelle fiche",
        buildNoCodeRecordEditorMarkup(),
        noCodeInlineOptions("min(980px, calc(100vw - 40px))", options),
    );
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

async function closeModalWithContextBack() {
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
    if (state.noCodeRecordEditor && state.noCodeServiceRecordContext?.service?.code) {
        state.noCodeRecordEditor = null;
        await openNoCodeServiceRecords(String(state.noCodeServiceRecordContext.service.code || ""));
        return;
    }
    if (state.noCodeServiceEditor) {
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
        if (!window.confirm(`Supprimer la liste partagee '${listCode}' ?`)) {
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
        if (!window.confirm(`Supprimer la valeur '${itemCode}' ?`)) {
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
    if (!action.startsWith("service:")) {
        return false;
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
        openNoCodeServiceEditor(null);
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
        openNoCodeServiceEditor(service);
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
        if (!window.confirm(`Supprimer le service '${code}' ?`)) {
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
    if (action === "service:back") {
        try {
            await returnToNoCodeServiceEditorCaller();
        } catch (error) {
            const feedback = document.getElementById("modal-service-form-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
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
            const imported = await importServiceFieldsFromFile(pickedFile, "", headerMode, headerRowNumber);
            if (!imported.fields.length) {
                if (feedback) {
                    feedback.textContent = "Aucune colonne exploitable n'a ete detectee.";
                }
                return true;
            }
            editor.importFile = pickedFile;
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
            };
            editor.importHeaderMode = normalizeTabularHeaderMode(imported.effectiveHeaderMode || headerMode);
            editor.importHeaderRowNumber = normalizeTabularHeaderRowNumber(imported.detectedHeaderRowNumber || headerRowNumber || 1);
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
    if (action === "service:field:import:apply") {
        const feedback = document.getElementById("modal-service-form-feedback");
        const editor = state.noCodeServiceEditor;
        const preview = editor?.importPreview;
        if (!editor || !preview || !Array.isArray(preview.fields) || !preview.fields.length) {
            return true;
        }
        if ((editor.fields || []).length > 0) {
            const confirmReplace = window.confirm(
                "Les champs actuels seront remplaces par les champs issus de l'import. Confirmer ?",
            );
            if (!confirmReplace) {
                if (feedback) {
                    feedback.textContent = "Application de l'import annulee.";
                }
                return true;
            }
        }
        editor.fields = preview.fields;
        editor.fieldEditor = null;
        editor.importFile = null;
        editor.importPreview = null;
        editor.importHeaderMode = "auto";
        editor.importHeaderRowNumber = 1;
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
        editor.importHeaderMode = "auto";
        editor.importHeaderRowNumber = 1;
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
            const preview = await previewServiceRecordsFromFile(
                pickedFile,
                serviceCode,
                credentialMode,
                selectedSheetName,
                headerMode,
                headerRowNumber,
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
            const credentialMode = normalizeRecordsImportCredentialMode(
                credentialSelector?.value || context?.importCredentialMode,
            );
            const selectedSheetName = String(sheetSelector?.value || context?.importSheetName || "").trim();
            const headerMode = normalizeTabularHeaderMode(headerModeSelector?.value || context?.importHeaderMode);
            const headerRowNumber = normalizeTabularHeaderRowNumber(headerRowInput?.value || context?.importHeaderRowNumber);
            context.importCredentialMode = credentialMode;
            context.importSheetName = selectedSheetName;
            context.importHeaderMode = headerMode;
            context.importHeaderRowNumber = headerRowNumber;
            setServiceRecordsImportProgress(65, "Import en cours...", true);
            if (feedback) {
                feedback.textContent = "Import en cours...";
            }
            const applied = await applyServiceRecordsImportFromFile(
                importFile,
                serviceCode,
                credentialMode,
                selectedSheetName,
                headerMode,
                headerRowNumber,
            );
            setServiceRecordsImportProgress(85, "Rechargement des fiches...", true);
            await openNoCodeServiceRecords(serviceCode);
            setServiceRecordsImportProgress(100, "Import termine", true);
            const issueCount = Array.isArray(applied.issues) ? applied.issues.length : 0;
            const refreshedFeedback = document.getElementById("modal-service-records-feedback");
            if (refreshedFeedback) {
                refreshedFeedback.textContent = `Import termine: ${applied.created} creee(s), ${applied.updated} mise(s) a jour, ${applied.skipped} ignoree(s).${issueCount ? ` (${issueCount} alerte(s))` : ""}`;
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
    if (action === "service:record:delete") {
        const context = state.noCodeServiceRecordContext;
        const serviceCode = String(context?.service?.code || "").trim();
        const recordId = String(actionButton.dataset.recordId || "").trim();
        const recordVersionToken = String(actionButton.dataset.recordVersionToken || "").trim();
        if (!serviceCode || !recordId) {
            return true;
        }
        if (!window.confirm("Supprimer cette fiche ?")) {
            return true;
        }
        try {
            const path = recordVersionToken
                ? `/admin/custom-services/${encodeURIComponent(serviceCode)}/records/${encodeURIComponent(recordId)}?version_token=${encodeURIComponent(recordVersionToken)}`
                : `/admin/custom-services/${encodeURIComponent(serviceCode)}/records/${encodeURIComponent(recordId)}`;
            await requestJson(path, { method: "DELETE" });
            await openNoCodeServiceRecords(serviceCode);
        } catch (error) {
            const feedback = document.getElementById("modal-service-records-feedback");
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
        }
        return true;
    }
    if (action === "service:records:back-services") {
        await openNoCodeServicesModal();
        return true;
    }
    if (action === "service:records:back") {
        const context = state.noCodeServiceRecordContext;
        if (context?.service?.code) {
            await openNoCodeServiceRecords(String(context.service.code || ""));
        } else {
            await openNoCodeServicesModal();
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
    if (form.id === "modal-service-form") {
        const feedback = document.getElementById("modal-service-form-feedback");
        if (feedback) {
            feedback.textContent = "";
        }
        const editor = state.noCodeServiceEditor;
        if (!editor) {
            return true;
        }
        if (editor.importPreview && Array.isArray(editor.importPreview.fields) && editor.importPreview.fields.length) {
            if (feedback) {
                feedback.textContent = "Un apercu d'import est en attente. Appliquez ou ignorez l'import avant d'enregistrer.";
            }
            return true;
        }
        const formData = new window.FormData(form);
        const label = normalizeNoCodeText(formData.get("service_label"));
        if (!label) {
            if (feedback) {
                feedback.textContent = "Nom du service requis.";
            }
            return true;
        }
        const childEnabled = form.querySelector('[name="service_child_enabled"]')?.checked ?? false;
        const childLabel = childEnabled
            ? (normalizeNoCodeText(formData.get("service_child_label")) || "Elements lies")
            : "Elements lies";
        const normalizedServiceCode = String(editor.code || slugifyNoCodeIdentifier(label, "service")).trim().toLowerCase();
        const credentialsWasEnabled = Boolean(editor.initial_credentials_enabled);
        const credentialsWillBeEnabled = Boolean(editor.credentials_enabled);
        let purgeStoredCredentials = false;
        if (editor.mode === "edit" && credentialsWasEnabled && !credentialsWillBeEnabled && normalizedServiceCode) {
            try {
                const rows = await requestJson(`/admin/custom-services/${encodeURIComponent(normalizedServiceCode)}/records`);
                const hasStoredCredentials = (Array.isArray(rows) ? rows : []).some((row) => noCodeRecordHasCredentialValues(row));
                if (hasStoredCredentials) {
                    purgeStoredCredentials = window.confirm(
                        "Des identifiants sont deja enregistres pour ce service.\n\nOK: supprimer definitivement ces identifiants.\nAnnuler: conserver les identifiants (masques tant que la gestion est desactivee).",
                    );
                }
            } catch (_error) {
                // Si le controle echoue, on continue la sauvegarde sans purge.
            }
        }
        const payload = {
            code: normalizedServiceCode,
            label,
            is_active: Boolean(editor.is_active),
            credentials_enabled: Boolean(editor.credentials_enabled),
            child_enabled: childEnabled,
            child_label: childLabel,
            sort_order: Number(editor.sort_order || 100),
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
            await returnToNoCodeServiceEditorCaller(
                `Service ${payload.label || payload.code} enregistre.${portalRefreshWarning ? ` Rafraichissement portail: ${portalRefreshWarning}` : ""}`,
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
        const service = context.service;
        const fields = noCodeCustomServiceFields(service);
        const formData = new window.FormData(form);
        const values = {};
        for (const field of fields) {
            const key = String(field.field_key || "").trim();
            values[key] = normalizeNoCodeText(formData.get(`record_field_${key}`));
        }
        if (Boolean(service?.credentials_enabled)) {
            values[NO_CODE_CREDENTIAL_LOGIN_KEY] = normalizeNoCodeText(formData.get("record_credential_login"));
            values[NO_CODE_CREDENTIAL_PASSWORD_KEY] = normalizeNoCodeText(formData.get("record_credential_password"));
        }
        syncNoCodeRecordChildrenFromDom();
        const children = Array.isArray(editor.children) ? editor.children : [];
        const payload = {
            values,
            children: children.map((row, index) => ({
                name: normalizeNoCodeText(row.name),
                code: normalizeNoCodeText(row.code),
                sort_order: (index + 1) * 10,
            })),
            version_token: String(editor.versionToken || ""),
        };
        try {
            await requestJson(
                editor.mode === "edit"
                    ? `/admin/custom-services/${encodeURIComponent(String(service.code || ""))}/records/${encodeURIComponent(String(editor.recordId || ""))}`
                    : `/admin/custom-services/${encodeURIComponent(String(service.code || ""))}/records`,
                {
                    method: editor.mode === "edit" ? "PUT" : "POST",
                    body: JSON.stringify(payload),
                },
            );
            await openNoCodeServiceRecords(String(service.code || ""));
        } catch (error) {
            if (feedback) {
                feedback.textContent = normalizeErrorMessage(error.message);
            }
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
    openModal("Administration - Utilisateurs", buildUsersModalMarkup(), adminInlineOptions("min(1120px, calc(100vw - 40px))", options));
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
        await loadAuthMode();
        showAuth();
    } finally {
        authSubmit.disabled = false;
    }
});

initProfileMenu();
refreshButton?.addEventListener("click", async () => {
    await loadPortalModules({ forceRefresh: true });
});

menuSupervision.addEventListener("click", () => openTopMenu(menuSupervision, "supervision"));
menuConfiguration.addEventListener("click", () => openTopMenu(menuConfiguration, "configuration"));
menuHelp.addEventListener("click", () => openTopMenu(menuHelp, "help"));
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
        const moduleRow = findPortalModuleByCode(state.portalContextModuleCode);
        closeCardsContextMenu();
        try {
            await handlePortalCardsContextMenuAction(action, moduleRow);
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
            openNoCodeServiceEditor(null, { inline: true });
            return;
        }
        if (action === "menu:services:shared-lists") {
            await openSharedListsModal({ inline: true });
            return;
        }
        if (action === "menu:notifications") {
            await openNotificationSettingsModal();
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

appModalBody.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof Element)) {
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
    const actionButton = target.closest("[data-action]");
    if (!(actionButton instanceof HTMLElement)) {
        return;
    }
    const action = String(actionButton.dataset.action || "");
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
        if (!targetId || !window.confirm("Supprimer cet emplacement de stockage ?")) {
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
        confirmFn: (message) => window.confirm(message),
    });
});

appModalBody.addEventListener("submit", async (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) {
        return;
    }
    event.preventDefault();
    if (form.id === "modal-webserver-form") {
        await submitWebServerSettings(form);
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
    if (target.id === "modal-admin-roles-search") {
        renderRolesTreeView();
        return;
    }
    if (target.id === "modal-admin-users-search") {
        renderUsersTreeView();
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
    if (target instanceof HTMLSelectElement && target.name === "service_field_import_sheet") {
        const selectedSheet = String(target.value || "").trim();
        const form = target.closest("form");
        const headerModeSelector = form?.querySelector?.('select[name="service_field_import_header_mode"]');
        const headerRowInput = form?.querySelector?.('input[name="service_field_import_header_row"]');
        const headerMode = normalizeTabularHeaderMode(headerModeSelector?.value || state.noCodeServiceEditor?.importHeaderMode);
        const headerRowNumber = normalizeTabularHeaderRowNumber(headerRowInput?.value || state.noCodeServiceEditor?.importHeaderRowNumber);
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
        const feedback = document.getElementById("modal-service-form-feedback");
        if (feedback) {
            feedback.textContent = "Recalcul de l'apercu...";
        }
        refreshNoCodeServiceFieldImportPreviewFromSheet(selectedSheet, selectedMode, headerRowNumber)
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
    if (target instanceof HTMLInputElement && target.name === "service_is_active") {
        const editor = state.noCodeServiceEditor;
        if (editor) {
            editor.is_active = Boolean(target.checked);
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

appModalBackdrop.addEventListener("click", async () => {
    await closeModalWithContextBack();
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

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
        closeTopMenu();
        closeProfileMenu();
        closeCardsContextMenu();
        closeModalWithContextBack().catch(() => {
            closeModal();
        });
    }
});

boot().catch((error) => {
    setError(normalizeErrorMessage(error.message));
    showAuth();
});
