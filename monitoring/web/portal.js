const state = {
    token: window.localStorage.getItem("nmp_token") || "",
    uiConfig: null,
};

const authScreen = document.getElementById("auth-screen");
const portalPanel = document.getElementById("portal-panel");
const authTitle = document.getElementById("auth-title");
const authHelp = document.getElementById("auth-help");
const authForm = document.getElementById("auth-form");
const authSubmit = document.getElementById("auth-submit");
const passwordInput = document.getElementById("password-input");
const authError = document.getElementById("auth-error");
const logoutButton = document.getElementById("logout-button");

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
}

function showAuth() {
    portalPanel.hidden = true;
    authScreen.hidden = false;
    portalPanel.style.display = "none";
    authScreen.style.display = "";
    document.body.dataset.screen = "auth";
    document.documentElement.classList.add("auth-mode");
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
    const bootstrapMode = !status.has_admin_password;
    authTitle.textContent = bootstrapMode ? "Initialiser l'acces" : "Connexion";
    authHelp.textContent = bootstrapMode
        ? "Aucun mot de passe admin n'est defini. Cree le mot de passe initial pour activer l'acces web."
        : "Connecte-toi avec le mot de passe administrateur pour ouvrir le portail des modules.";
    authSubmit.textContent = bootstrapMode ? "Initialiser" : "Se connecter";
    passwordInput.autocomplete = bootstrapMode ? "new-password" : "current-password";
    authForm.dataset.mode = bootstrapMode ? "bootstrap" : "login";
    await loadPublicUiConfig();
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

function bindModuleCards() {
    document.querySelectorAll("[data-module-link]").forEach((node) => {
        node.addEventListener("click", () => {
            const url = String(node.getAttribute("data-module-link") || "").trim();
            if (url) {
                window.location.href = url;
            }
        });
    });
    document.querySelectorAll("[data-module-name]").forEach((node) => {
        node.addEventListener("click", () => {
            window.alert("Module en preparation.");
        });
    });
}

async function boot() {
    bindModuleCards();
    await loadAuthMode();
    const sessionOk = await restoreSession();
    if (!sessionOk) {
        showAuth();
        return;
    }
    await loadPrivateUiConfig();
    showPortal();
}

authForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    setError("");
    authSubmit.disabled = true;
    try {
        await authenticate(passwordInput.value);
        passwordInput.value = "";
        await loadPrivateUiConfig();
        showPortal();
    } catch (error) {
        persistToken("");
        setError(normalizeErrorMessage(error.message));
        await loadAuthMode();
        showAuth();
    } finally {
        authSubmit.disabled = false;
    }
});

logoutButton.addEventListener("click", async () => {
    await logout();
});

boot().catch((error) => {
    setError(normalizeErrorMessage(error.message));
    showAuth();
});
