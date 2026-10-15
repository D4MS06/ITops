(function () {
    "use strict";

    const DEFAULT_PLATFORM_KEYS = new Set(["windows", "linux", "firmware", "autre"]);
    const ACTION_LABELS = Object.freeze({
        ssh: "SSH",
        web: "Web (URL)",
        teamviewer: "TeamViewer",
        remote_desktop: "Remote Desktop",
    });

    function platformLabel(device) {
        return String(device?.device_subtype || device?.type || "Autre").trim() || "Autre";
    }

    function normalizePlatform(value) {
        const normalized = String(value || "")
            .replaceAll(",", " ")
            .replace(/\s+/g, " ")
            .trim()
            .toLocaleLowerCase();
        return normalized || "autre";
    }

    function allowsOs(rawScope, devicePlatform) {
        const scope = Array.from(new Set(String(rawScope || "")
            .split(",")
            .map((item) => normalizePlatform(item))
            .filter(Boolean)));
        if (!scope.length) return true;
        const platform = normalizePlatform(devicePlatform);
        return scope.includes(platform) || (!DEFAULT_PLATFORM_KEYS.has(platform) && scope.includes("autre"));
    }

    function actionLabel(actionKey) {
        const key = String(actionKey || "").trim().toLowerCase();
        return ACTION_LABELS[key] || key.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
    }

    function actionsForDevice(schema, device) {
        const platform = platformLabel(device);
        return (schema?.actions || [])
            .filter((row) => allowsOs(row?.os_scope, platform))
            .map((row) => ({
                ...row,
                action_key: String(row?.action_key || "").trim().toLowerCase(),
                target_kind: String(row?.target_kind || "").trim().toLowerCase(),
                target_value: String(row?.target_value || row?.action_key || "").trim().toLowerCase(),
                sort_order: Number(row?.sort_order || 0),
            }))
            .filter((row) => Boolean(row.action_key))
            .sort((left, right) => Number(left.sort_order || 0) - Number(right.sort_order || 0)
                || String(left.label || left.action_key).localeCompare(String(right.label || right.action_key), undefined, { sensitivity: "base" }));
    }

    function resolveForDevice(device, schema, preferredActionKey = "", defaultActionKey = "") {
        const actions = actionsForDevice(schema, device);
        const normalize = (value) => String(value || "").trim().toLowerCase();
        const matches = (row, key) => Boolean(key) && (normalize(row?.action_key) === key || normalize(row?.target_value) === key);
        const selected = actions.find((row) => matches(row, normalize(preferredActionKey)))
            || actions.find((row) => matches(row, normalize(device?.action_double_click)))
            || actions.find((row) => matches(row, normalize(defaultActionKey)))
            || actions[0]
            || null;
        return { actions, selected };
    }

    function defaultActionForDevice(schema, device) {
        const actions = actionsForDevice(schema, device);
        const platform = normalizePlatform(platformLabel(device));
        const definition = (schema?.fields || []).find((item) => String(item?.field_key || "").trim().toLowerCase() === "action_default_by_os");
        try {
            const configured = String(JSON.parse(String(definition?.default_value || "{}"))?.[platform] || "").trim().toLowerCase();
            if (configured && actions.some((item) => item.action_key === configured || item.target_value === configured)) {
                return configured;
            }
        } catch (_) {
        }
        return actions.find((item) => item.is_default)?.action_key || actions[0]?.action_key || "";
    }

    function canRunBuiltinAction(device, builtin) {
        const ip = String(device?.ip || "").trim();
        if (builtin === "teamviewer") return Boolean(String(device?.id_Teamviewer || "").trim());
        if (builtin === "web") return Boolean(String(device?.web_url || "").trim() || ip);
        if (builtin === "remote_desktop") return Boolean(ip);
        return false;
    }

    function webStatus(device, action) {
        const actionKey = String(action?.action_key || "").trim().toLowerCase();
        if (!actionKey) return { ok: false, builtin: "", hint: "Indisponible", message: "Action distante introuvable." };
        if (String(action?.target_kind || "").trim().toLowerCase() !== "builtin") {
            return { ok: false, builtin: "", hint: "Non supporté web", message: `Action ${actionKey} non supportée sur l'interface web.` };
        }
        const builtin = String(action?.target_value || actionKey).trim().toLowerCase();
        if (builtin === "ssh") {
            return { ok: false, builtin, hint: "Bientôt web", message: `${actionLabel(builtin)} n'est pas encore disponible depuis le navigateur.` };
        }
        if (!canRunBuiltinAction(device, builtin)) {
            return { ok: false, builtin, hint: "Informations manquantes", message: `Informations manquantes pour lancer ${actionLabel(builtin)}.` };
        }
        return { ok: true, builtin, hint: "", message: "" };
    }

    function resolveWebUrl({ ip, subtype, webUrl }) {
        const normalizedIp = String(ip || "").trim();
        const raw = String(webUrl || "").trim();
        if (!raw) return String(subtype || "").trim().toLowerCase() === "dsm" && normalizedIp ? `http://${normalizedIp}:5000` : (normalizedIp ? `http://${normalizedIp}` : "");
        const numeric = raw.match(/^:?(?<port>\d{1,5})$/);
        if (numeric?.groups?.port) {
            const port = Number(numeric.groups.port);
            return normalizedIp && port >= 1 && port <= 65535 ? `http://${normalizedIp}:${port}` : "";
        }
        if (/^[a-z][a-z0-9+.-]*:\/\//i.test(raw)) return raw;
        if (/^[^/\s:]+:\d{1,5}(?:[/?#]|$)/.test(raw)) return `http://${raw}`;
        if (raw.startsWith(":")) {
            const port = Number(raw.slice(1));
            return normalizedIp && port >= 1 && port <= 65535 ? `http://${normalizedIp}:${port}` : "";
        }
        if (raw.startsWith("/") && normalizedIp) return `http://${normalizedIp}${raw}`;
        return /^[^\s/]+(?:[/?#].*)?$/.test(raw) ? `http://${raw}` : raw;
    }

    function builtinActionUrl(device, builtin) {
        if (builtin === "teamviewer") {
            const id = String(device?.id_Teamviewer || "").trim();
            return id ? `https://start.teamviewer.com/${encodeURIComponent(id)}` : "";
        }
        return builtin === "web" ? resolveWebUrl({ ip: device?.ip, subtype: device?.device_subtype || device?.type, webUrl: device?.web_url }) : "";
    }

    function usesDirectSwitchWebAccess(device) {
        return ["1", "true", "yes", "oui", "on"].includes(String(device?.custom_data?.web_direct_no_proxy ?? "").trim().toLowerCase());
    }

    function shouldUseSwitchWebProxy(device) {
        return String(device?.device_type || "").trim().toLowerCase() === "switch" && !usesDirectSwitchWebAccess(device);
    }

    function switchWebProxyUrl(device, token) {
        const normalize = (value) => String(value || "").trim().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/\s+/g, "_").replace(/[^A-Za-z0-9_-]+/g, "_").replace(/_+/g, "_").replace(/^_+|_+$/g, "");
        const typeCode = String(device?.device_type || "").trim();
        const locator = normalize(device?.name) || normalize(device?.id);
        const sessionToken = String(token || "").trim();
        if (!typeCode || !locator || !sessionToken) return "";
        return `/devices/${encodeURIComponent(typeCode)}/${encodeURIComponent(locator)}/web-ui?token=${encodeURIComponent(sessionToken)}`;
    }

    window.NMPRemoteActions = Object.freeze({ platformLabel, normalizePlatform, allowsOs, actionLabel, actionsForDevice, resolveForDevice, defaultActionForDevice, canRunBuiltinAction, webStatus, resolveWebUrl, builtinActionUrl, usesDirectSwitchWebAccess, shouldUseSwitchWebProxy, switchWebProxyUrl });
}());
