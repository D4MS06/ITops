(function () {
    function normalizeText(value) {
        return String(value || "").trim();
    }

    function escapeHtml(value) {
        return String(value || "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");
    }

    function authHeaders(token) {
        const normalizedToken = normalizeText(token);
        return normalizedToken ? { Authorization: `Bearer ${normalizedToken}` } : {};
    }

    function normalizeErrorMessage(message) {
        const normalized = normalizeText(message);
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
        if (lowered.includes("missing bearer token")) {
            return "Jeton Bearer manquant.";
        }
        if (lowered.includes("empty bearer token")) {
            return "Jeton Bearer vide.";
        }
        return normalized;
    }

    function persistToken(state, token, storageKey = "nmp_token") {
        const normalizedToken = normalizeText(token);
        if (state && typeof state === "object") {
            state.token = normalizedToken;
        }
        if (normalizedToken) {
            window.localStorage.setItem(storageKey, normalizedToken);
        } else {
            window.localStorage.removeItem(storageKey);
        }
        return normalizedToken;
    }

    async function requestJson(path, options = {}, context = {}) {
        const normalizeMessage = typeof context.normalizeErrorMessage === "function"
            ? context.normalizeErrorMessage
            : normalizeErrorMessage;
        const mergedHeaders = {
            "Content-Type": "application/json",
            ...authHeaders(context.token),
            ...(options.headers || {}),
        };
        const response = await fetch(path, {
            ...options,
            headers: mergedHeaders,
        });
        if (!response.ok) {
            let detail = `${response.status} ${response.statusText}`;
            try {
                const body = await response.json();
                detail = body.detail || body.message || detail;
            } catch (_error) {
            }
            throw new Error(normalizeMessage(detail));
        }
        if (response.status === 204) {
            return null;
        }
        return response.json();
    }

    window.NMPSharedApi = {
        escapeHtml,
        authHeaders,
        normalizeErrorMessage,
        persistToken,
        requestJson,
    };
})();
