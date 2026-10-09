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
        };
    }

    async function fetchSessionContext(requestJson) {
        try {
            const context = await requestJson("/auth/me/context");
            return {
                ...normalizeSessionContext(context),
                modules_loaded: true,
            };
        } catch (contextError) {
            let me;
            try {
                me = await requestJson("/auth/me");
            } catch (_meError) {
                throw contextError;
            }
            const fallback = normalizeSessionContext({
                subject: normalizeText(me?.subject).toLowerCase(),
                label: normalizeText(me?.subject).toLowerCase(),
                role_code: ["sa", "admin"].includes(normalizeText(me?.subject).toLowerCase()) ? "admin" : "",
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
        return normalized;
    }

    function clearSessionContext(state) {
        state.sessionSubject = "";
        state.sessionLabel = "";
        state.sessionRoleCode = "";
        state.sessionRoleLabel = "";
        state.moduleAccess = [];
        state.moduleAccessLoaded = false;
    }

    window.NMPSharedAuth = {
        roleIcon,
        normalizeSessionContext,
        fetchSessionContext,
        applySessionContext,
        clearSessionContext,
    };
})();
