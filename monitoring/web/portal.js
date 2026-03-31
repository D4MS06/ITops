const state = {
    token: window.localStorage.getItem("nmp_token") || "",
    uiConfig: null,
    openTopMenu: "",
};

const authScreen = document.getElementById("auth-screen");
const portalPanel = document.getElementById("portal-panel");
const authTitle = document.getElementById("auth-title");
const authHelp = document.getElementById("auth-help");
const authForm = document.getElementById("auth-form");
const authSubmit = document.getElementById("auth-submit");
const usernameInput = document.getElementById("username-input");
const passwordInput = document.getElementById("password-input");
const newPasswordField = document.getElementById("new-password-field");
const newPasswordInput = document.getElementById("new-password-input");
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

const MODULE_META = {
    monitoring: {
        title: "Monitoring reseau",
        subtitle: "Supervision, inventaire, actions reseau",
    },
    interventions: {
        title: "Interventions",
        subtitle: "Fiches, historique et suivi d'action",
    },
    imprimantes: {
        title: "Imprimantes",
        subtitle: "Codes, modeles et maintenance",
    },
    comptes: {
        title: "Comptes techniques",
        subtitle: "Comptes de service et acces internes",
    },
    admin: {
        title: "Administration",
        subtitle: "Gestion utilisateurs, roles et habilitations",
    },
};
const IMPLEMENTED_MODULES = new Set(["monitoring"]);

function escapeHtml(value) {
    return String(value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function setError(message = "") {
    authError.hidden = !message;
    authError.textContent = message;
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
    if (lowered.includes("invalid credentials")) {
        return "Identifiants invalides.";
    }
    if (lowered.includes("invalid or expired session")) {
        return "Session invalide ou expiree.";
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
        ? "Premiere connexion: utilise le compte sa puis definis un nouveau mot de passe."
        : "Connecte-toi avec ton compte pour ouvrir le portail des modules.";
    authSubmit.textContent = mustChangePassword ? "Se connecter et changer le mot de passe" : "Se connecter";
    passwordInput.autocomplete = "current-password";
    usernameInput.autocomplete = "username";
    if (!String(usernameInput.value || "").trim()) {
        usernameInput.value = "sa";
    }
    newPasswordField.hidden = !mustChangePassword;
    newPasswordInput.required = mustChangePassword;
    authForm.dataset.forcePasswordChange = mustChangePassword ? "1" : "0";
    await loadPublicUiConfig();
    return { mustChangePassword };
}

function enablePasswordChangeMode() {
    authForm.dataset.forcePasswordChange = "1";
    authSubmit.textContent = "Se connecter et changer le mot de passe";
    newPasswordField.hidden = false;
    newPasswordInput.required = true;
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
        await requestJson("/auth/me");
        return true;
    } catch (_error) {
        persistToken("");
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
    await loadAuthMode();
    showAuth();
}

function openModal(title, bodyMarkup, options = {}) {
    appModalTitle.textContent = title;
    appModalBody.innerHTML = bodyMarkup;
    appModalPanel.style.width = options.width || "min(860px, calc(100vw - 40px))";
    appModal.hidden = false;
}

function closeModal() {
    appModal.hidden = true;
    appModalBody.innerHTML = "";
}

function closeTopMenu() {
    topMenuPanel.hidden = true;
    topMenuPanel.innerHTML = "";
    state.openTopMenu = "";
    [menuSupervision, menuDisplay, menuHelp].forEach((button) => button.classList.remove("active"));
}

function topMenuDefinitions() {
    const sharedDefs = window.NMPSharedMenu?.commonDefinitions?.() || {};
    return {
        supervision: [...(sharedDefs.supervision || [])],
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
    return `
    <label class="field ${wide ? "wide" : ""}">
        <span>${escapeHtml(label)}</span>
        <input name="${escapeHtml(key)}" value="${escapeHtml(value)}">
    </label>
    `;
}

function buildWebServerSettingsMarkup(settings) {
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

async function downloadHttpsRootCertificate() {
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

function bindModuleCards() {
    document.querySelectorAll("[data-module-link]").forEach((node) => {
        node.addEventListener("click", () => {
            const url = String(node.getAttribute("data-module-link") || "").trim();
            if (url) {
                window.location.href = url;
            }
        });
    });
    document.querySelectorAll("[data-module-blocked]").forEach((node) => {
        node.addEventListener("click", () => {
            const reason = String(node.getAttribute("data-module-blocked") || "Acces refuse.");
            openModal("Module non disponible", `<p class="muted">${escapeHtml(reason)}</p>`);
        });
    });
}

function moduleStatusMeta(moduleRow) {
    const code = String(moduleRow.code || "").trim().toLowerCase();
    const implemented = IMPLEMENTED_MODULES.has(code);
    if (!moduleRow.is_active) {
        return { badgeClass: "stat-offline", text: "Module non dispo", value: "Bientot" };
    }
    if (!moduleRow.granted) {
        return { badgeClass: "stat-offline", text: "Acces refuse", value: "Verrouille" };
    }
    if (moduleRow.route_path && implemented) {
        return { badgeClass: "stat-online", text: "Disponible", value: "Live" };
    }
    return { badgeClass: "stat-offline", text: "Module non dispo", value: "Bientot" };
}

function renderModuleCard(moduleRow) {
    const code = String(moduleRow.code || "").trim().toLowerCase();
    const routePath = String(moduleRow.route_path || "").trim();
    const isActive = Boolean(moduleRow.is_active);
    const granted = Boolean(moduleRow.granted);
    const implemented = IMPLEMENTED_MODULES.has(code);
    const canOpen = Boolean(isActive && granted && routePath && implemented);
    const known = MODULE_META[code] || {};
    const status = moduleStatusMeta({ is_active: isActive, granted, route_path: routePath });
    const title = String(moduleRow.label || known.title || code || "Module");
    const subtitle = String(known.subtitle || "Module de service IT");
    const hint = routePath || code || "-";
    const moduleLink = canOpen ? routePath : "";
    const behaviorAttr = canOpen
        ? `data-module-link="${escapeHtml(moduleLink)}"`
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
    const modules = Array.isArray(rows) ? rows : [];
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
        bindModuleCards();
        return;
    }
    cardsGrid.innerHTML = modules.map((moduleRow) => renderModuleCard(moduleRow)).join("");
    bindModuleCards();
}

async function loadPortalModules() {
    try {
        const modules = await requestJson("/auth/me/modules");
        renderModuleCards(modules);
    } catch (_error) {
        renderModuleCards([
            {
                code: "monitoring",
                label: "Monitoring",
                route_path: "/monitoring",
                is_active: true,
                granted: true,
            },
        ]);
    }
}

async function boot() {
    const mode = await loadAuthMode();
    if (mode?.mustChangePassword) {
        persistToken("");
        showAuth();
        return;
    }
    const sessionOk = await restoreSession();
    if (!sessionOk) {
        showAuth();
        return;
    }
    await loadPrivateUiConfig();
    await loadPortalModules();
    showPortal();
}

authForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    setError("");
    authSubmit.disabled = true;
    try {
        await authenticate(usernameInput.value, passwordInput.value, newPasswordInput.value);
        passwordInput.value = "";
        newPasswordInput.value = "";
        await loadPrivateUiConfig();
        await loadPortalModules();
        showPortal();
    } catch (error) {
        persistToken("");
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

topMenuPanel.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action]");
    if (!button || button.disabled) {
        return;
    }
    const action = String(button.dataset.action || "");
    closeTopMenu();
    const commonMenuActions = window.NMPSharedMenu?.buildCommonActions?.({
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
    }
});

appModalBody.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) {
        return;
    }
    if (target.closest('[data-action="modal:close"]')) {
        closeModal();
    }
});

appModalBody.addEventListener("submit", async (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) {
        return;
    }
    event.preventDefault();
    if (form.id === "modal-webserver-form") {
        await submitWebServerSettings(form);
    }
});

appModalBackdrop.addEventListener("click", () => closeModal());
appModalClose.addEventListener("click", () => closeModal());

document.addEventListener("click", (event) => {
    if (!topMenuPanel.hidden && !topMenuPanel.contains(event.target) && !event.target.closest(".menu-btn")) {
        closeTopMenu();
    }
});

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
        closeTopMenu();
        closeModal();
    }
});

boot().catch((error) => {
    setError(normalizeErrorMessage(error.message));
    showAuth();
});
