(function () {
    function normalizeText(value) {
        return String(value || "").trim();
    }

    function roleIcon(roleCode) {
        const normalized = normalizeText(roleCode).toLowerCase();
        if (normalized === "admin") {
            return "\uD83D\uDEE1";
        }
        if (normalized === "technician") {
            return "\uD83D\uDEE0";
        }
        return "\uD83D\uDC64";
    }

    function normalizeModules(rows) {
        if (!Array.isArray(rows)) {
            return [];
        }
        return rows.map((row) => ({
            code: normalizeText(row?.code).toLowerCase(),
            label: normalizeText(row?.label),
            route_path: normalizeText(row?.route_path),
            is_active: Boolean(row?.is_active),
            granted: Boolean(row?.granted),
            last_sync_at: normalizeText(row?.last_sync_at),
            // Keep the complete shared portal-module contract.  Session
            // restoration is also the first tile render after a Ctrl+F5;
            // dropping these properties here made the portal display empty
            // icons and zero counters until its manual refresh button ran.
            is_technical: Boolean(row?.is_technical),
            icon: normalizeText(row?.icon),
            color: normalizeText(row?.color),
            item_count: Number.isFinite(Number(row?.item_count))
                ? Math.max(0, Math.trunc(Number(row.item_count)))
                : 0,
            permissions: Array.isArray(row?.permissions)
                ? row.permissions.map((permission) => normalizeText(permission)).filter(Boolean)
                : [],
            tile_config: row?.tile_config && typeof row.tile_config === "object" && !Array.isArray(row.tile_config)
                ? { ...row.tile_config }
                : {},
        }));
    }

    function normalizeSessionContext(raw) {
        const payload = raw || {};
        const subject = normalizeText(payload.subject).toLowerCase();
        const modules = normalizeModules(payload.modules);
        let roleCode = normalizeText(payload.role_code).toLowerCase();
        let roleLabel = normalizeText(payload.role_label);
        const hasAdminModule = modules.some((row) => row.code === "admin" && row.granted);
        if (!roleCode) {
            if (hasAdminModule || subject === "sa" || subject === "admin") {
                roleCode = "admin";
            } else if (subject) {
                roleCode = "user";
            }
        }
        if (!roleLabel && roleCode) {
            roleLabel = roleCode === "admin" ? "Administrateur" : `${roleCode.charAt(0).toUpperCase()}${roleCode.slice(1)}`;
        }
        const label = normalizeText(payload.label) || subject || "-";
        return {
            subject,
            label,
            role_code: roleCode,
            role_label: roleLabel,
            modules,
            expires_at: normalizeText(payload.expires_at),
        };
    }

    async function fetchSessionContext(requestJson) {
        try {
            const context = await requestJson("/auth/me/context", { cache: "no-store" });
            return {
                ...normalizeSessionContext(context),
                modules_loaded: true,
            };
        } catch (contextError) {
            let me;
            try {
                me = await requestJson("/auth/me", { cache: "no-store" });
            } catch (meError) {
                throw meError?.isAuthFailure ? meError : contextError;
            }
            const fallback = normalizeSessionContext({
                subject: normalizeText(me?.subject).toLowerCase(),
                label: normalizeText(me?.subject).toLowerCase(),
                role_code: ["sa", "admin"].includes(normalizeText(me?.subject).toLowerCase()) ? "admin" : "",
                expires_at: normalizeText(me?.expires_at),
            });
            let modulesLoaded = false;
            try {
                const profile = await requestJson("/auth/me/profile");
                const merged = {
                    ...fallback,
                    subject: normalizeText(profile?.subject) || fallback.subject,
                    label: normalizeText(profile?.label) || fallback.label,
                    role_code: normalizeText(profile?.role_code) || fallback.role_code,
                    role_label: normalizeText(profile?.role_label) || fallback.role_label,
                };
                Object.assign(fallback, normalizeSessionContext(merged));
            } catch (_profileError) {
            }
            try {
                const modules = await requestJson("/auth/me/modules");
                fallback.modules = normalizeModules(modules);
                modulesLoaded = true;
            } catch (_moduleError) {
            }
            return {
                ...normalizeSessionContext(fallback),
                modules_loaded: modulesLoaded,
            };
        }
    }

    function applySessionContext(state, context) {
        const normalized = normalizeSessionContext(context);
        state.sessionSubject = normalized.subject;
        state.sessionLabel = normalized.label;
        state.sessionRoleCode = normalized.role_code;
        state.sessionRoleLabel = normalized.role_label;
        state.moduleAccess = normalized.modules;
        const hasExplicitModulesLoaded = context && typeof context === "object" && typeof context.modules_loaded === "boolean";
        state.moduleAccessLoaded = hasExplicitModulesLoaded
            ? Boolean(context.modules_loaded)
            : Array.isArray(context?.modules);
        state.sessionExpiresAt = normalized.expires_at;
        return normalized;
    }

    function clearSessionContext(state) {
        state.sessionSubject = "";
        state.sessionLabel = "";
        state.sessionRoleCode = "";
        state.sessionRoleLabel = "";
        state.moduleAccess = [];
        state.moduleAccessLoaded = false;
        state.sessionExpiresAt = "";
    }

    const SESSION_ACTIVITY_KEY = "nmp_session_last_activity";

    function clearSessionExpiryTimer(state) {
        if (state?.sessionExpiryTimer != null) {
            window.clearTimeout(state.sessionExpiryTimer);
            state.sessionExpiryTimer = null;
        }
        state?._sessionActivityCleanup?.();
        if (state) state._sessionActivityCleanup = null;
    }

    function scheduleSessionExpiry(state, onExpired, options = {}) {
        clearSessionExpiryTimer(state);
        const expiresAtMs = Date.parse(String(state?.sessionExpiresAt || ""));
        if (!Number.isFinite(expiresAtMs) || typeof onExpired !== "function") return;
        const verifySession = options.verifySession;
        if (typeof verifySession !== "function") {
            state.sessionExpiryTimer = window.setTimeout(onExpired, Math.max(0, expiresAtMs - Date.now()));
            return;
        }

        const token = String(state.token || "");
        let tokenHash = 2166136261;
        for (const character of token) {
            tokenHash = Math.imul(tokenHash ^ character.charCodeAt(0), 16777619);
        }
        const activityScope = (tokenHash >>> 0).toString(16);
        let active = true;
        let refreshing = false;
        let idleTimeoutMs = Math.max(1000, expiresAtMs - Date.now());
        let lastActivityMs = Date.now();
        let lastWrittenMs = 0;
        let lastRefreshAttemptMs = Date.now();
        const activityEvents = ["pointerdown", "pointermove", "keydown", "wheel", "touchstart"];

        const sharedActivityMs = () => {
            try {
                const entry = JSON.parse(window.localStorage.getItem(SESSION_ACTIVITY_KEY) || "null");
                const value = entry?.scope === activityScope ? Number(entry.at || 0) : 0;
                return Number.isFinite(value) && value <= Date.now() ? value : 0;
            } catch (_error) {
                return 0;
            }
        };
        const activityDeadline = () => Math.max(lastActivityMs, sharedActivityMs()) + idleTimeoutMs;
        const clearTimer = () => {
            if (state.sessionExpiryTimer != null) window.clearTimeout(state.sessionExpiryTimer);
            state.sessionExpiryTimer = null;
        };
        const scheduleCheck = (delayMs = null) => {
            if (!active) return;
            clearTimer();
            const deadline = Math.min(Date.parse(String(state.sessionExpiresAt || "")), activityDeadline());
            const delay = delayMs == null ? Math.max(0, deadline - Date.now()) : delayMs;
            state.sessionExpiryTimer = window.setTimeout(checkSession, delay);
        };
        const refreshSession = async () => {
            if (!active || refreshing || state.token !== token) return;
            refreshing = true;
            lastRefreshAttemptMs = Date.now();
            try {
                const session = await verifySession();
                if (!active || state.token !== token) return;
                const nextExpiryMs = Date.parse(String(session?.expires_at || ""));
                if (!Number.isFinite(nextExpiryMs) || nextExpiryMs <= Date.now()) throw new Error("Expiration de session invalide.");
                state.sessionExpiresAt = session.expires_at;
                idleTimeoutMs = Math.max(1000, nextExpiryMs - Date.now());
                scheduleCheck();
            } catch (error) {
                if (!active || state.token !== token) return;
                if (error?.isAuthFailure) {
                    clearSessionExpiryTimer(state);
                    onExpired();
                } else {
                    scheduleCheck(60_000);
                }
            } finally {
                refreshing = false;
            }
        };
        const checkSession = () => {
            if (!active || state.token !== token) return;
            if (Date.now() >= activityDeadline()) {
                clearSessionExpiryTimer(state);
                (typeof options.onIdle === "function" ? options.onIdle : onExpired)();
                return;
            }
            if (refreshing) {
                scheduleCheck(Math.max(1000, activityDeadline() - Date.now()));
                return;
            }
            refreshSession();
        };
        const recordActivity = () => {
            if (!active || state.token !== token) return;
            const now = Date.now();
            if (now - lastActivityMs < 1000) return;
            lastActivityMs = now;
            if (now - lastWrittenMs >= 1000) {
                try { window.localStorage.setItem(SESSION_ACTIVITY_KEY, JSON.stringify({ scope: activityScope, at: now })); } catch (_error) {}
                lastWrittenMs = now;
            }
            const retryDelay = 60_000 - (now - lastRefreshAttemptMs);
            if (retryDelay <= 0) refreshSession();
            else {
                const expiryDelay = Date.parse(String(state.sessionExpiresAt || "")) - now;
                scheduleCheck(Math.min(
                    retryDelay,
                    expiryDelay > 0 ? expiryDelay : retryDelay,
                    Math.max(0, activityDeadline() - now),
                ));
            }
        };
        const onStorage = (event) => {
            if (event.key === SESSION_ACTIVITY_KEY) scheduleCheck();
        };
        const onVisibility = () => {
            if (document.visibilityState === "visible") recordActivity();
        };
        activityEvents.forEach((name) => document.addEventListener(name, recordActivity, { passive: true }));
        document.addEventListener("visibilitychange", onVisibility);
        window.addEventListener("storage", onStorage);
        state._sessionActivityCleanup = () => {
            active = false;
            activityEvents.forEach((name) => document.removeEventListener(name, recordActivity));
            document.removeEventListener("visibilitychange", onVisibility);
            window.removeEventListener("storage", onStorage);
        };
        try { window.localStorage.setItem(SESSION_ACTIVITY_KEY, JSON.stringify({ scope: activityScope, at: lastActivityMs })); } catch (_error) {}
        scheduleCheck();
    }

    window.NMPSharedAuth = {
        roleIcon,
        normalizeSessionContext,
        fetchSessionContext,
        applySessionContext,
        clearSessionContext,
        clearSessionExpiryTimer,
        scheduleSessionExpiry,
    };
})();
