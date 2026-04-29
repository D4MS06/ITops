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
    noCodeServiceRecordContext: null,
    noCodeRecordEditor: null,
    noCodeSharedListEditor: null,
    noCodeSharedListItemsContext: null,
    noCodeSharedListItemEditor: null,
    noCodeSharedListsWarning: "",
    monitoringPrewarmStarted: false,
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
const logoutButton = document.getElementById("logout-button");
const cardsGrid = document.getElementById("cards-grid");
const menuSupervision = document.getElementById("menu-supervision");
const menuDisplay = document.getElementById("menu-display");
const menuHelp = document.getElementById("menu-help");
const topMenuPanel = document.getElementById("top-menu-panel");
const appModal = document.getElementById("app-modal");
const appModalBackdrop = document.getElementById("app-modal-backdrop");
const appModalPanel = document.getElementById("app-modal-panel");
const appModalTitle = document.getElementById("app-modal-title");
const appModalBody = document.getElementById("app-modal-body");
const appModalClose = document.getElementById("app-modal-close");
const accessStatusLabel = document.getElementById("access-status-label");
const sessionProfileLabel = document.getElementById("session-profile-label");
const modalController = window.NMPSharedUi?.shell?.createModalController?.({
    modal: appModal,
    titleNode: appModalTitle,
    bodyNode: appModalBody,
    panelNode: appModalPanel,
    defaultWidth: "min(860px, calc(100vw - 40px))",
}) || null;
const topMenuController = window.NMPSharedUi?.shell?.createTopMenuController?.({
    state,
    panel: topMenuPanel,
    buttons: [menuSupervision, menuDisplay, menuHelp],
    buildMarkup: (menuKey) => topMenuMarkup(menuKey),
    onBeforeOpen: () => closeModal(),
}) || null;

const MODULE_META = {
    monitoring: {
        title: "Monitoring reseau",
        subtitle: "Supervision, inventaire, actions reseau",
    },
    interventions: {
        title: "Interventions",
        subtitle: "Fiches, historique et suivi d'action",
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
    const label = String(state.sessionLabel || state.sessionSubject || "-").trim() || "-";
    const roleLabel = String(state.sessionRoleLabel || state.sessionRoleCode || "").trim();
    const icon = roleIcon(state.sessionRoleCode);
    sessionProfileLabel.textContent = roleLabel ? `${icon} ${label} (${roleLabel})` : `${icon} ${label}`;
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
        return;
    }
    state.sessionSubject = "";
    state.sessionLabel = "";
    state.sessionRoleCode = "";
    state.sessionRoleLabel = "";
    state.moduleAccess = [];
    state.moduleAccessLoaded = false;
    state.monitoringPrewarmStarted = false;
}

function invalidateAdminData(parts = []) {
    adminStore.invalidate(parts);
}

function showPortal() {
    authScreen.hidden = true;
    portalPanel.hidden = false;
    authScreen.style.display = "none";
    portalPanel.style.display = "";
    document.body.dataset.screen = "dashboard";
    document.documentElement.classList.remove("auth-mode");
    accessStatusLabel.textContent = "Reussi";
}

function showAuth() {
    closeTopMenu();
    closeModal();
    portalPanel.hidden = true;
    authScreen.hidden = false;
    portalPanel.style.display = "none";
    authScreen.style.display = "";
    document.body.dataset.screen = "auth";
    document.documentElement.classList.add("auth-mode");
    accessStatusLabel.textContent = "Hors ligne";
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
        ? "Premiere connexion: cree ton mot de passe administrateur."
        : "Connecte-toi avec ton compte pour ouvrir le portail des modules.";
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

function openModal(title, bodyMarkup, options = {}) {
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
        return;
    }
    appModal.hidden = true;
    appModalBody.innerHTML = "";
}

function closeTopMenu() {
    if (topMenuController) {
        topMenuController.close();
        return;
    }
    const sharedCloseTopMenu = window.NMPSharedUi?.closeTopMenu;
    if (typeof sharedCloseTopMenu === "function") {
        sharedCloseTopMenu(state, topMenuPanel, [menuSupervision, menuDisplay, menuHelp]);
    }
}

function topMenuDefinitions() {
    const sharedDefs = window.NMPSharedMenu?.commonDefinitions?.() || {};
    const hasUsersAdminAccess = (state.moduleAccess || []).some((row) => {
        const code = String(row?.code || "").trim().toLowerCase();
        return Boolean(row?.granted) && (code === "users_admin" || code === "admin");
    });
    const hasAdminModule = (state.moduleAccess || []).some((row) => String(row?.code || "").trim().toLowerCase() === "admin" && Boolean(row?.granted));
    const canManageRoles = state.sessionRoleCode === "admin" || hasAdminModule || ["sa", "admin"].includes(state.sessionSubject);
    const canManageServices = canManageRoles;
    return {
        supervision: [
            ...(sharedDefs.supervision || []),
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
        display: [...(sharedDefs.display || [])],
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
    if (topMenuController) {
        topMenuController.open(button, menuKey, {
            buildMarkup: topMenuMarkup,
            onBeforeOpen: () => closeModal(),
        });
        return;
    }
    const sharedOpenTopMenu = window.NMPSharedUi?.openTopMenu;
    if (typeof sharedOpenTopMenu === "function") {
        sharedOpenTopMenu({
            state,
            panel: topMenuPanel,
            buttons: [menuSupervision, menuDisplay, menuHelp],
            button,
            menuKey,
            buildMarkup: topMenuMarkup,
            onBeforeOpen: () => closeModal(),
        });
        return;
    }
    if (state.openTopMenu === menuKey && !topMenuPanel.hidden) {
        closeTopMenu();
        return;
    }
    closeModal();
    state.openTopMenu = menuKey;
    topMenuPanel.innerHTML = topMenuMarkup(menuKey);
    topMenuPanel.hidden = false;
    [menuSupervision, menuDisplay, menuHelp].forEach((entry) => {
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
        const sortState = context?.sort && String(context.sort.column || "").trim()
            ? context.sort
            : { column: "updated_at", direction: "desc" };
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

function buildWebServerSettingsMarkup(settings) {
    const sharedBuilder = window.NMPSharedUi?.webServer?.buildSettingsMarkup;
    if (typeof sharedBuilder === "function") {
        return sharedBuilder({
            settings,
            field: (key, label, value, wide = false) => createFieldMarkup(key, label, value, wide),
        });
    }
    return `
    <form id="modal-webserver-form" class="modal-form">
        <div class="modal-settings-grid">
            ${createFieldMarkup("web_server_host", "Host", settings.web_server_host || "127.0.0.1")}
            ${createFieldMarkup("web_server_port", "Port", settings.web_server_port || 8000)}
            ${createFieldMarkup("web_server_public_url", "URL publique", settings.web_server_public_url || "", true)}
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
    await loadPrivateUiConfig();
    if (feedback) {
        feedback.textContent = "Parametres enregistres.";
    }
}

async function openWebServerSettingsModal() {
    const settings = await requestJson("/settings");
    openModal("Parametres serveur web", buildWebServerSettingsMarkup(settings), {
        width: "min(860px, calc(100vw - 40px))",
    });
}

async function submitWebServerSettings(form) {
    const sharedParser = window.NMPSharedUi?.webServer?.parseSettingsForm;
    const payload = typeof sharedParser === "function"
        ? sharedParser(form)
        : (() => {
            const formData = new window.FormData(form);
            const parsedPort = Number(formData.get("web_server_port") || 8000);
            const port = Number.isFinite(parsedPort) ? Math.max(1, Math.min(65535, Math.trunc(parsedPort))) : 8000;
            return {
                web_server_host: String(formData.get("web_server_host") || "127.0.0.1").trim() || "127.0.0.1",
                web_server_port: port,
                web_server_autostart: form.querySelector('[name="web_server_autostart"]')?.checked ?? false,
                web_server_public_url: String(formData.get("web_server_public_url") || "").trim(),
                web_server_use_public_url: form.querySelector('[name="web_server_use_public_url"]')?.checked ?? false,
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
    await openNoCodeServiceRecords(normalizedCode);
}

async function handleModuleCardsClick(event) {
    const target = event.target;
    if (!(target instanceof Element)) {
        return;
    }
    const actionable = target.closest("[data-module-link], [data-module-service], [data-module-blocked]");
    if (!(actionable instanceof HTMLElement)) {
        return;
    }
    const serviceCode = String(actionable.getAttribute("data-module-service") || "").trim().toLowerCase();
    if (serviceCode) {
        try {
            await openServiceModuleFromPortal(serviceCode);
        } catch (error) {
            openModal("Module non disponible", `<p class="muted">${escapeHtml(normalizeErrorMessage(error.message))}</p>`);
        }
        return;
    }
    const link = String(actionable.getAttribute("data-module-link") || "").trim();
    if (link) {
        window.location.assign(link);
        return;
    }
    const reason = String(actionable.getAttribute("data-module-blocked") || "Acces refuse.");
    openModal("Module non disponible", `<p class="muted">${escapeHtml(reason)}</p>`);
}

function scheduleMonitoringPrewarm(rows) {
    if (state.monitoringPrewarmStarted) {
        return;
    }
    const monitoringModule = (Array.isArray(rows) ? rows : []).find((row) => {
        const code = String(row?.code || "").trim().toLowerCase();
        const routePath = String(row?.route_path || "").trim();
        return code === "monitoring" && Boolean(row?.granted) && Boolean(row?.is_active) && Boolean(routePath);
    });
    if (!monitoringModule) {
        return;
    }
    state.monitoringPrewarmStarted = true;
    const routePath = String(monitoringModule.route_path || "/monitoring").trim() || "/monitoring";
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
        return { badgeClass: "stat-online", text: "Disponible", value: "Live" };
    }
    if (!isActive) {
        return { badgeClass: "stat-offline", text: "Module non dispo", value: "Bientot" };
    }
    if (!granted) {
        return { badgeClass: "stat-offline", text: "Acces refuse", value: "Verrouille" };
    }
    return { badgeClass: "stat-offline", text: "Module non dispo", value: "Bientot" };
}

function renderModuleCard(moduleRow) {
    const code = String(moduleRow.code || "").trim().toLowerCase();
    const routePath = String(moduleRow.route_path || "").trim();
    const serviceCode = extractServiceCodeFromRoutePath(routePath);
    const isActive = Boolean(moduleRow.is_active);
    const granted = Boolean(moduleRow.granted);
    const canOpen = Boolean(isActive && granted && routePath);
    const known = MODULE_META[code] || {};
    const status = moduleStatusMeta({ is_active: isActive, granted, route_path: routePath });
    const title = String(moduleRow.label || known.title || code || "Module");
    const subtitle = String(known.subtitle || (serviceCode ? "Service personnalise" : "Module de service IT"));
    const hint = serviceCode ? `service:${serviceCode}` : (routePath || code || "-");
    const moduleLink = canOpen && !serviceCode ? routePath : "";
    const behaviorAttr = canOpen
        ? (serviceCode
            ? `data-module-service="${escapeHtml(serviceCode)}"`
            : `data-module-link="${escapeHtml(moduleLink)}"`)
        : `data-module-blocked="${escapeHtml(granted ? "Module indisponible pour le moment." : "Vous n'avez pas les droits sur ce module.")}"`;

    return `
        <article class="dash-card panel ${canOpen ? "clickable" : ""}" ${behaviorAttr}>
            <div class="dash-card-title">${escapeHtml(title)}</div>
            <div class="dash-card-value">${escapeHtml(status.value)}</div>
            <div class="dash-card-sub">${escapeHtml(subtitle)}</div>
            <div class="dash-card-stats">
                <span class="${escapeHtml(status.badgeClass)}">${escapeHtml(status.text)}</span>
                <span>${escapeHtml(hint)}</span>
            </div>
        </article>
    `;
}

function renderModuleCards(rows) {
    const modules = (Array.isArray(rows) ? rows : [])
        .filter((row) => Boolean(row?.granted))
        .filter((row) => !["admin", "users_admin", "imprimantes", "comptes"].includes(String(row?.code || "").trim().toLowerCase()))
        .filter((row) => {
            const serviceCode = extractServiceCodeFromRoutePath(String(row?.route_path || ""));
            if (serviceCode && !Boolean(row?.is_active)) {
                return false;
            }
            return true;
        });
    if (!modules.length) {
        cardsGrid.innerHTML = `
            <article class="dash-card panel">
                <div class="dash-card-title">Modules</div>
                <div class="dash-card-value">0</div>
                <div class="dash-card-sub">Aucun module visible pour cet utilisateur.</div>
                <div class="dash-card-stats">
                    <span class="stat-offline">Aucun acces</span>
                    <span></span>
                </div>
            </article>
        `;
        return;
    }
    cardsGrid.innerHTML = modules.map((moduleRow) => renderModuleCard(moduleRow)).join("");
}

async function loadPortalModules(options = {}) {
    const forceRefresh = Boolean(options.forceRefresh);
    if (!forceRefresh && state.moduleAccessLoaded) {
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
        renderModuleCards(state.moduleAccess);
        scheduleMonitoringPrewarm(state.moduleAccess);
        return state.moduleAccess;
    } catch (_error) {
        state.moduleAccess = [];
        state.moduleAccessLoaded = true;
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
    const rows = sharedListRows();
    const listMarkup = rows.length
        ? rows.map((row) => {
            const code = String(row?.code || "").trim().toLowerCase();
            const label = String(row?.label || code || "").trim() || code;
            const itemCount = Number(row?.item_count || 0);
            const isSystem = Boolean(row?.is_system);
            const versionToken = String(row?.version_token || "").trim();
            return `
                <div class="type-schema-custom-field-row">
                    <div class="type-schema-custom-field-meta">
                        <strong>${escapeHtml(label)}</strong>
                        <span>${escapeHtml(code)} | ${itemCount} valeur(s)${isSystem ? " | systeme" : ""}</span>
                    </div>
                    <div class="inventory-row-actions">
                        ${createIconActionButtonMarkup({
                            icon: "list",
                            action: "shared-list:items",
                            title: "Valeurs",
                            data: { list_code: code },
                        })}
                        ${createIconActionButtonMarkup({
                            icon: "settings",
                            action: "shared-list:edit",
                            title: "Modifier",
                            data: { list_code: code },
                        })}
                        ${createIconActionButtonMarkup({
                            icon: "delete",
                            danger: true,
                            action: "shared-list:delete",
                            title: "Supprimer",
                            data: {
                                list_code: code,
                                list_version_token: versionToken,
                            },
                            disabled: isSystem,
                        })}
                    </div>
                </div>
            `;
        }).join("")
        : `<div class="muted">Aucune liste partagee definie.</div>`;
    return `
        <section class="modal-section type-schema-fields-section">
            <div class="type-schema-fields-head">
                <h3>Listes partagees</h3>
                ${createIconActionButtonMarkup({
                    icon: "add",
                    action: "shared-list:add",
                    title: "Ajouter une liste partagee",
                })}
            </div>
            <p class="muted">Une liste partagee permet de reutiliser la meme liste de valeurs dans plusieurs services.</p>
            <div class="type-schema-custom-fields-list">${listMarkup}</div>
            <p id="modal-shared-list-feedback" class="muted inventory-feedback"></p>
            ${createModalActionsMarkup({
                buttons: [{ preset: "back", action: "shared-list:back-services", label: "Retour services" }],
            })}
        </section>
    `;
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
    const rows = Array.isArray(context.items) ? context.items : [];
    const code = String(list.code || "").trim().toLowerCase();
    const label = String(list.label || code).trim() || code;
    const rowsMarkup = rows.length
        ? rows.map((item) => {
            const itemCode = String(item?.code || "").trim().toLowerCase();
            const itemLabel = String(item?.label || itemCode).trim() || itemCode;
            const active = Boolean(item?.is_active);
            const versionToken = String(item?.version_token || "").trim();
            return `
                <div class="type-schema-custom-field-row">
                    <div class="type-schema-custom-field-meta">
                        <strong>${escapeHtml(itemLabel)}</strong>
                        <span>${escapeHtml(itemCode)} | ${active ? "active" : "inactive"}</span>
                    </div>
                    <div class="inventory-row-actions">
                        ${createIconActionButtonMarkup({
                            icon: "settings",
                            action: "shared-list-item:edit",
                            title: "Modifier",
                            data: { item_code: itemCode },
                        })}
                        ${createIconActionButtonMarkup({
                            icon: "delete",
                            danger: true,
                            action: "shared-list-item:delete",
                            title: "Supprimer",
                            data: {
                                item_code: itemCode,
                                item_version_token: versionToken,
                            },
                        })}
                    </div>
                </div>
            `;
        }).join("")
        : `<div class="muted">Aucune valeur.</div>`;
    return `
        <section class="modal-section type-schema-fields-section">
            <div class="type-schema-fields-head">
                <h3>${escapeHtml(label)}</h3>
                <div class="inventory-row-actions">
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
                </div>
            </div>
            <p class="muted">${escapeHtml(code)} | Valeurs disponibles pour les champs lies a cette liste partagee.</p>
            <div class="type-schema-custom-fields-list">${rowsMarkup}</div>
            <p id="modal-shared-list-items-feedback" class="muted inventory-feedback"></p>
            ${createModalActionsMarkup({
                buttons: [{ preset: "back", action: "shared-list-item:back" }],
            })}
        </section>
    `;
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

async function openSharedListsModal() {
    await loadAdministrationData({
        includeModules: false,
        includeRoles: false,
        includeUsers: false,
        includeServices: false,
        includeSharedLists: true,
    });
    state.noCodeServiceEditor = null;
    state.noCodeServiceRecordContext = null;
    state.noCodeRecordEditor = null;
    state.noCodeSharedListEditor = null;
    state.noCodeSharedListItemsContext = null;
    state.noCodeSharedListItemEditor = null;
    openModal("Services - Listes partagees", buildSharedListsModalMarkup(), {
        width: "min(1080px, calc(100vw - 40px))",
    });
}

function openSharedListEditor(list = null) {
    state.noCodeSharedListEditor = createSharedListEditor(list);
    state.noCodeSharedListItemsContext = null;
    state.noCodeSharedListItemEditor = null;
    openModal(
        list ? "Liste partagee - Edition" : "Liste partagee - Creation",
        buildSharedListEditorMarkup(),
        { width: "min(860px, calc(100vw - 40px))" },
    );
}

async function openSharedListItemsModal(listCode) {
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
        { width: "min(1080px, calc(100vw - 40px))" },
    );
}

function openSharedListItemEditor(item = null) {
    if (!state.noCodeSharedListItemsContext?.list) {
        return;
    }
    state.noCodeSharedListEditor = null;
    state.noCodeSharedListItemEditor = createSharedListItemEditor(item);
    openModal(
        item ? "Valeur - Edition" : "Valeur - Creation",
        buildSharedListItemEditorMarkup(),
        { width: "min(860px, calc(100vw - 40px))" },
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

async function importServiceFieldsFromFile(file) {
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
            responseMapper: (payload) => {
                const fields = normalizeImportedServiceFields(payload?.fields || []);
                return {
                    fields,
                    detectedRows: Number(payload?.detected_rows || 0),
                    detectedColumns: Number(payload?.detected_columns || fields.length),
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

async function importSharedListItemsFromFile(file, listCode) {
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
        responseMapper: (payload) => {
            const items = normalizeImportedSharedListItems(payload?.items || []);
            return {
                items,
                detectedRows: Number(payload?.detected_rows || 0),
                detectedColumns: Number(payload?.detected_columns || 0),
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

async function previewServiceRecordsFromFile(file, serviceCode) {
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
        responseMapper: (payload) => ({
            rows: Array.isArray(payload?.rows) ? payload.rows : [],
            detectedRows: Number(payload?.detected_rows || 0),
            detectedColumns: Number(payload?.detected_columns || 0),
            issues: Array.isArray(payload?.issues) ? payload.issues : [],
        }),
    });
}

async function applyServiceRecordsImportFromFile(file, serviceCode) {
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
        const imported = await importSharedListItemsFromFile(file, listCode);
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

function createNoCodeServiceEditor(service = null) {
    const fields = Array.isArray(service?.fields)
        ? service.fields.map((row, index) => ({
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
        child_enabled: Boolean(service?.child_enabled),
        child_label: String(service?.child_label || "Elements lies").trim() || "Elements lies",
        sort_order: Number(service?.sort_order || 100),
        version_token: String(service?.version_token || "").trim(),
        fields,
        fieldEditor: null,
        importPreview: null,
    };
}

function noCodeServiceRows() {
    return Array.isArray(state.adminData.services) ? state.adminData.services : [];
}

function findNoCodeService(serviceCode) {
    const wanted = normalizeNoCodeText(serviceCode).toLowerCase();
    if (!wanted) {
        return null;
    }
    return noCodeServiceRows().find((row) => String(row?.code || "").trim().toLowerCase() === wanted) || null;
}

function buildNoCodeServicesModalMarkup() {
    const rows = noCodeServiceRows();
    const content = rows.length
        ? rows.map((service) => {
            const code = String(service.code || "").trim();
            const label = String(service.label || code || "").trim() || code;
            const isActive = Boolean(service?.is_active);
            const fieldsCount = Array.isArray(service.fields) ? service.fields.length : 0;
            const childEnabled = Boolean(service.child_enabled);
            const childLabel = String(service.child_label || "Elements lies").trim() || "Elements lies";
            return `
                <div class="type-schema-custom-field-row">
                    <div class="type-schema-custom-field-meta">
                        <strong>${escapeHtml(label)}</strong>
                        <span>${escapeHtml(code)} | ${isActive ? "actif" : "desactive"} | ${fieldsCount} champ(s)${childEnabled ? ` | ${escapeHtml(childLabel)} actifs` : ""}</span>
                    </div>
                    <div class="inventory-row-actions">
                        ${createActionButtonMarkup({
                            className: "inventory-action-btn",
                            type: "button",
                            action: "service:definition:toggle-active",
                            label: isActive ? "OFF" : "ON",
                            title: isActive ? "Desactiver" : "Activer",
                            data: {
                                service_code: code,
                                service_version_token: String(service.version_token || ""),
                            },
                        })}
                        ${createIconActionButtonMarkup({
                            icon: "list",
                            action: "service:records:open",
                            title: "Donnees",
                            data: {
                                service_code: code,
                                service_version_token: String(service.version_token || ""),
                            },
                        })}
                        ${createIconActionButtonMarkup({
                            icon: "settings",
                            action: "service:definition:edit",
                            title: "Modifier",
                            data: {
                                service_code: code,
                                service_version_token: String(service.version_token || ""),
                            },
                        })}
                        ${createIconActionButtonMarkup({
                            icon: "delete",
                            danger: true,
                            action: "service:definition:delete",
                            title: "Supprimer",
                            data: {
                                service_code: code,
                                service_version_token: String(service.version_token || ""),
                            },
                        })}
                    </div>
                </div>
            `;
        }).join("")
        : `<div class="muted">Aucun service.</div>`;
    return `
        <section class="modal-section type-schema-fields-section">
            <div class="type-schema-fields-head">
                <h3>Services</h3>
                ${createIconActionButtonMarkup({
                    icon: "add",
                    action: "service:definition:add",
                    title: "Ajouter un service",
                })}
            </div>
            <p class="muted">Creer des services et gerer leurs fiches.</p>
            <div class="type-schema-custom-fields-list">${content}</div>
            <p id="modal-service-feedback" class="muted inventory-feedback"></p>
        </section>
    `;
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
    const fields = Array.isArray(service?.fields) ? service.fields : [];
    const columns = [
        { key: "record_id", label: "ID fiche", kind: "text" },
        ...fields.map((field) => ({
            key: `field:${String(field?.field_key || "").trim()}`,
            label: String(field?.label || field?.field_key || "").trim() || String(field?.field_key || ""),
            kind: normalizeNoCodeKind(field?.field_kind || "text"),
            field_key: String(field?.field_key || "").trim(),
        })),
    ];
    if (Boolean(service?.child_enabled)) {
        columns.push({
            key: "child_count",
            label: String(service?.child_label || "Elements lies").trim() || "Elements lies",
            kind: "number",
        });
    }
    columns.push({ key: "updated_at", label: "Derniere mise a jour", kind: "date" });
    return columns;
}

function noCodeRecordColumnValue(row, column) {
    const key = String(column?.key || "");
    if (key === "record_id") {
        return String(row?.id || "");
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
    const col = columnsByKey.get(String(column || "")) || { kind: "text", key: "record_id" };
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
    return `
        <section class="modal-section">
            <div class="section-head">
                <h3>${escapeHtml(serviceLabel || "Service")}</h3>
                <div class="inventory-row-actions">
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
                </div>
            </div>
            <div class="inventory-controls">
                <label class="modal-inline-search">
                    <span>Recherche</span>
                    <input id="service-records-search" type="search" placeholder="ID, valeurs, elements lies...">
                </label>
            </div>
            ${importPreview}
            <div class="table-wrap">
                <table class="device-table inventory-table">
                    <thead id="service-records-head"></thead>
                    <tbody id="service-records-body"></tbody>
                </table>
            </div>
            <div id="service-records-import-progress-wrap" class="modal-scan-progress modal-scan-progress-top" hidden>
                <progress id="service-records-import-progress" value="0" max="100"></progress>
                <span id="service-records-import-progress-status" class="muted">Pret.</span>
            </div>
            <p id="modal-service-records-feedback" class="muted inventory-feedback"></p>
            ${createModalActionsMarkup({
                buttons: [{ preset: "back", action: "service:records:back-services", label: "Retour services" }],
            })}
        </section>
    `;
}

function buildNoCodeRecordsImportPreviewMarkup(context) {
    const preview = context?.importPreview;
    const service = context?.service || null;
    if (!preview || !Array.isArray(preview.rows) || !preview.rows.length || !service) {
        return "";
    }
    const fields = Array.isArray(service.fields) ? service.fields : [];
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
    const issues = Array.isArray(preview.issues) ? preview.issues.filter((item) => String(item || "").trim()) : [];
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
            ${issuesMarkup}
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
    const fields = Array.isArray(service?.fields) ? service.fields : [];
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

async function openNoCodeServicesModal() {
    await loadAdministrationData({
        includeModules: false,
        includeRoles: false,
        includeUsers: false,
        includeServices: true,
        includeSharedLists: true,
    });
    state.noCodeServiceEditor = null;
    state.noCodeServiceRecordContext = null;
    state.noCodeRecordEditor = null;
    state.noCodeSharedListEditor = null;
    state.noCodeSharedListItemsContext = null;
    state.noCodeSharedListItemEditor = null;
    openModal("Administration - Ajout de service", buildNoCodeServicesModalMarkup(), {
        width: "min(1120px, calc(100vw - 40px))",
    });
}

function openNoCodeServiceEditor(service = null) {
    state.noCodeSharedListEditor = null;
    state.noCodeSharedListItemsContext = null;
    state.noCodeSharedListItemEditor = null;
    state.noCodeServiceEditor = createNoCodeServiceEditor(service);
    openModal(
        service ? "Service - Edition" : "Service - Creation",
        buildNoCodeServiceEditorMarkup(),
        { width: "min(1120px, calc(100vw - 40px))" },
    );
    renderNoCodeServiceEditor();
}

async function openNoCodeServiceRecords(serviceCode) {
    const service = findNoCodeService(serviceCode);
    if (!service) {
        throw new Error("Service introuvable.");
    }
    const previousContext = state.noCodeServiceRecordContext;
    const sameService = String(previousContext?.service?.code || "").trim().toLowerCase() === String(service.code || "").trim().toLowerCase();
    const records = await requestJson(`/admin/custom-services/${encodeURIComponent(String(service.code || ""))}/records`);
    state.noCodeServiceRecordContext = {
        service,
        records: Array.isArray(records) ? records : [],
        importPreview: null,
        importFile: null,
        _recordsTreeView: null,
        searchQuery: sameService ? String(previousContext?.searchQuery || "") : "",
        sort: sameService && previousContext?.sort
            ? { column: String(previousContext.sort.column || "updated_at"), direction: String(previousContext.sort.direction || "desc") }
            : { column: "updated_at", direction: "desc" },
    };
    state.noCodeRecordEditor = null;
    renderNoCodeServiceRecordsModal();
}

function renderNoCodeServiceRecordsModal() {
    const context = state.noCodeServiceRecordContext;
    if (!context?.service) {
        return;
    }
    const service = context.service;
    openModal(
        `Donnees - ${service.label || service.code}`,
        buildNoCodeRecordsModalMarkup(context),
        { width: "min(1180px, calc(100vw - 40px))" },
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

function openNoCodeRecordEditor(record = null) {
    const context = state.noCodeServiceRecordContext;
    if (!context || !context.service) {
        return;
    }
    const service = context.service;
    const fields = Array.isArray(service.fields) ? service.fields : [];
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
        children: Array.isArray(record?.children)
            ? record.children.map((row) => ({ name: String(row?.name || ""), code: String(row?.code || "") }))
            : [],
    };
    openModal(
        record ? "Edition fiche" : "Nouvelle fiche",
        buildNoCodeRecordEditorMarkup(),
        { width: "min(980px, calc(100vw - 40px))" },
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
        await openNoCodeServicesModal();
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
    if (action === "service:definition:add") {
        openNoCodeServiceEditor(null);
        return true;
    }
    if (action === "service:definition:edit") {
        const service = findNoCodeService(String(actionButton.dataset.serviceCode || ""));
        if (!service) {
            return true;
        }
        openNoCodeServiceEditor(service);
        return true;
    }
    if (action === "service:definition:toggle-active") {
        const code = String(actionButton.dataset.serviceCode || "").trim();
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
            child_enabled: Boolean(service.child_enabled),
            child_label: String(service.child_label || "Elements lies").trim() || "Elements lies",
            sort_order: Number(service.sort_order || 100),
            version_token: versionToken || String(service.version_token || ""),
            fields: Array.isArray(service.fields) ? service.fields : [],
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
            await openNoCodeServicesModal();
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
            const imported = await importServiceFieldsFromFile(pickedFile);
            if (!imported.fields.length) {
                if (feedback) {
                    feedback.textContent = "Aucune colonne exploitable n'a ete detectee.";
                }
                return true;
            }
            editor.importPreview = {
                filename: String(pickedFile?.name || ""),
                fields: imported.fields,
                detectedRows: imported.detectedRows,
                detectedColumns: imported.detectedColumns,
            };
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
        editor.importPreview = null;
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
        editor.importPreview = null;
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
            const preview = await previewServiceRecordsFromFile(pickedFile, serviceCode);
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
            setServiceRecordsImportProgress(65, "Import en cours...", true);
            if (feedback) {
                feedback.textContent = "Import en cours...";
            }
            const applied = await applyServiceRecordsImportFromFile(importFile, serviceCode);
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
        const payload = {
            code: editor.code || slugifyNoCodeIdentifier(label, "service"),
            label,
            is_active: Boolean(editor.is_active),
            child_enabled: childEnabled,
            child_label: childLabel,
            sort_order: Number(editor.sort_order || 100),
            version_token: String(editor.version_token || ""),
            fields: (editor.fields || []).map((row, index) => ({
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
            state.moduleAccessLoaded = false;
            invalidateAdminData(["services", "modules"]);
            await Promise.all([
                openNoCodeServicesModal(),
                loadPortalModules({ forceRefresh: true }),
            ]);
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
        const fields = Array.isArray(service.fields) ? service.fields : [];
        const formData = new window.FormData(form);
        const values = {};
        for (const field of fields) {
            const key = String(field.field_key || "").trim();
            values[key] = normalizeNoCodeText(formData.get(`record_field_${key}`));
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

async function openRolesModal() {
    await loadAdministrationData({ includeModules: true, includeRoles: true, includeUsers: false });
    openModal("Administration - Roles", buildRolesModalMarkup(), { width: "min(1120px, calc(100vw - 40px))" });
}

async function openUsersModal() {
    await loadAdministrationData({ includeModules: false, includeRoles: true, includeUsers: true });
    openModal("Administration - Utilisateurs", buildUsersModalMarkup(), { width: "min(1120px, calc(100vw - 40px))" });
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

logoutButton.addEventListener("click", async () => {
    await logout();
});

menuSupervision.addEventListener("click", () => openTopMenu(menuSupervision, "supervision"));
menuDisplay.addEventListener("click", () => openTopMenu(menuDisplay, "display"));
menuHelp.addEventListener("click", () => openTopMenu(menuHelp, "help"));
cardsGrid.addEventListener("click", handleModuleCardsClick);

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
            await openRolesModal();
            return;
        }
        if (action === "menu:admin:users") {
            await openUsersModal();
            return;
        }
        if (action === "menu:services:manage") {
            await openNoCodeServicesModal();
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
            openNoCodeServiceEditor(null);
            return;
        }
        if (action === "menu:services:shared-lists") {
            await openSharedListsModal();
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
    if (target.closest('[data-action="modal:close"]')) {
        await closeModalWithContextBack();
        return;
    }
    const actionButton = target.closest("[data-action]");
    if (!(actionButton instanceof HTMLElement)) {
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
        openModal,
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

appModalBody.addEventListener("change", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) {
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
});

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
        closeTopMenu();
        closeModalWithContextBack().catch(() => {
            closeModal();
        });
    }
});

boot().catch((error) => {
    setError(normalizeErrorMessage(error.message));
    showAuth();
});
