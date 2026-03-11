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
};

const authScreen = document.getElementById("auth-screen");
const authPanel = document.getElementById("auth-panel");
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
    const runningTypes = (state.snapshot?.summary?.running_types || []);
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
            applyCurrentView();
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
                state.currentView = card.clickView;
                applyCurrentView();
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
    globalButton.id = "start-all-button";
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
            state.currentView = item.type_code;
            applyCurrentView();
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
        .sort((left, right) => `${left.device_type}:${left.name}`.localeCompare(`${right.device_type}:${right.name}`))
        .forEach((item) => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${escapeHtml(item.device_type || "")}</td>
                <td>${escapeHtml(item.name || "")}</td>
                <td>${escapeHtml(item.ip || "")}</td>
                <td><span class="status-badge ${statusClass(item.status)}">${escapeHtml(localizeStatus(item.status || "idle"))}</span></td>
                <td>${escapeHtml(item.description || "")}</td>
            `;
            tbody.appendChild(tr);
        });
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

function applyCurrentView() {
    if (!state.snapshot) {
        return;
    }
    const summary = state.snapshot.summary || {};
    const runningTypes = summary.running_types || [];
    const runningAny = Boolean(summary.running_any);

    renderNavigation(state.snapshot.types || []);

    if (state.currentView === "dashboard") {
        if (!runningAny) {
            detailPanel.hidden = true;
            placeholderPanel.hidden = false;
            return;
        }
        placeholderPanel.hidden = true;
        detailPanel.hidden = false;
        if (runningTypes.length === 1) {
            state.currentView = runningTypes[0];
            applyCurrentView();
            return;
        }
        detailTitle.textContent = "Globale";
        inventoryTitle.textContent = "Inventaire global";
        renderDevices(state.snapshot);
        return;
    }

    placeholderPanel.hidden = true;
    detailPanel.hidden = false;
    detailTitle.textContent = displayLabelForView(state.currentView);
    inventoryTitle.textContent = state.currentView === "global"
        ? "Inventaire global"
        : `Inventaire ${displayLabelForView(state.currentView)}`;
    renderDevices(state.snapshot);
}

function renderSnapshot(snapshot) {
    state.snapshot = snapshot;
    const summary = snapshot.summary || {};
    document.getElementById("runtime-running").textContent = summary.running_any ? "Oui" : "Non";
    document.getElementById("runtime-types").textContent = String((summary.running_types || []).length);
    renderCards(snapshot);
    renderMonitoringToolbar(snapshot.types || [], summary);
    renderTypes(snapshot.types || []);
    devicesSection.hidden = !summary.running_any;
    if (!summary.running_any) {
        state.currentView = "dashboard";
    }
    applyCurrentView();
}

async function refreshSnapshot() {
    const snapshot = await requestJson("/monitoring/snapshot");
    renderSnapshot(snapshot);
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
    await refreshSnapshot();
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
        await refreshSnapshot();
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
    await refreshSnapshot();
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
    state.currentView = "dashboard";
    applyUiConfig(null);
    await loadAuthMode();
    showAuth();
});

deviceFilter.addEventListener("input", () => {
    if (state.snapshot) {
        renderDevices(state.snapshot);
    }
});

boot().catch((error) => {
    setError(error.message || "Initialisation web impossible.");
    showAuth();
});
