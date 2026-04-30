(function () {
    const form = document.getElementById("setup-form");
    const errorNode = document.getElementById("setup-error");
    const infoNode = document.getElementById("setup-info");
    const submitButton = document.getElementById("setup-submit");
    const tokenInput = document.getElementById("setup-token");
    const adminPasswordInput = document.getElementById("admin-password");
    const adminPasswordConfirmInput = document.getElementById("admin-password-confirm");
    const dbPasswordInput = document.getElementById("db-password");
    const dbRootPasswordInput = document.getElementById("db-root-password");
    const dbRootPasswordConfirmInput = document.getElementById("db-root-password-confirm");
    const showPasswordsInput = document.getElementById("show-passwords");
    const reverseProxyInput = document.getElementById("reverse-proxy");
    const publicUrlInput = document.getElementById("public-url");
    const reverseProxyNote = document.getElementById("reverse-proxy-note");
    const proxyNoteHostDns = document.getElementById("proxy-note-host-dns");
    const proxyNoteIpDns = document.getElementById("proxy-note-ip-dns");
    const proxyNoteIpHosts = document.getElementById("proxy-note-ip-hosts");
    const proxyNoteHostHosts = document.getElementById("proxy-note-host-hosts");
    let setupStatusCache = {};

    function setError(message) {
        const text = String(message || "").trim();
        if (!text) {
            errorNode.hidden = true;
            errorNode.textContent = "";
            return;
        }
        errorNode.hidden = false;
        errorNode.textContent = text;
    }

    function setInfo(message) {
        infoNode.textContent = String(message || "").trim();
    }

    async function requestJson(path, options) {
        const response = await fetch(path, options || {});
        let payload = null;
        try {
            payload = await response.json();
        } catch (_err) {
            payload = null;
        }
        if (!response.ok) {
            const detail = payload && payload.detail ? payload.detail : `Erreur HTTP ${response.status}`;
            throw new Error(String(detail || "Erreur API"));
        }
        return payload || {};
    }

    async function loadStatus() {
        setError("");
        const status = await requestJson("/setup/status");
        setupStatusCache = status || {};
        if (!status.setup_required) {
            window.location.href = "/portal";
            return;
        }
        if (status.has_setup_token) {
            tokenInput.required = true;
            setInfo("Token d'installation requis (fourni par le script bootstrap).");
        } else {
            tokenInput.required = false;
            setInfo("Aucun token requis. Configuration locale autorisee.");
        }
        renderReverseProxyNote();
    }

    function extractHostname(rawUrl) {
        const value = String(rawUrl || "").trim();
        if (!value) {
            return "";
        }
        try {
            return String(new URL(value).hostname || "").trim().toLowerCase();
        } catch (_err) {
            return "";
        }
    }

    function renderReverseProxyNote() {
        if (!reverseProxyNote) {
            return;
        }
        const proxyType = String(reverseProxyInput?.value || "aucun").trim().toLowerCase();
        const publicHost = extractHostname(publicUrlInput?.value || "");
        const targetHost = publicHost || "itops.mvl";
        const targetIp = String(setupStatusCache?.server_hint_ip || "").trim() || "<IP_SERVEUR>";
        if (proxyType === "aucun") {
            reverseProxyNote.hidden = true;
            return;
        }
        reverseProxyNote.hidden = false;
        if (proxyNoteHostDns) {
            proxyNoteHostDns.textContent = targetHost;
        }
        if (proxyNoteIpDns) {
            proxyNoteIpDns.textContent = targetIp;
        }
        if (proxyNoteIpHosts) {
            proxyNoteIpHosts.textContent = targetIp;
        }
        if (proxyNoteHostHosts) {
            proxyNoteHostHosts.textContent = targetHost;
        }
    }

    async function onSubmit(event) {
        event.preventDefault();
        setError("");
        const adminPassword = String(form.admin_password.value || "");
        const adminPasswordConfirm = String(form.admin_password_confirm.value || "");
        if (adminPassword !== adminPasswordConfirm) {
            setError("La confirmation du mot de passe admin ne correspond pas.");
            return;
        }
        const rootPassword = String(form.mariadb_root_password.value || "");
        const rootPasswordConfirm = String(form.mariadb_root_password_confirm.value || "");
        if (rootPassword || rootPasswordConfirm) {
            if (rootPassword !== rootPasswordConfirm) {
                setError("La confirmation du mot de passe root MariaDB ne correspond pas.");
                return;
            }
            if (rootPassword.length < 8) {
                setError("Le mot de passe root MariaDB doit contenir au moins 8 caracteres.");
                return;
            }
        }
        submitButton.disabled = true;
        submitButton.textContent = "Finalisation en cours...";
        try {
            const payload = {
                setup_token: String(form.setup_token.value || ""),
                admin_password: adminPassword,
                hote_ecoute: String(form.hote_ecoute.value || "0.0.0.0"),
                port_ecoute: Number(form.port_ecoute.value || 8080),
                reverse_proxy_type: String(form.reverse_proxy_type.value || "aucun"),
                url_publique: String(form.url_publique.value || ""),
                db_host: String(form.db_host.value || "127.0.0.1"),
                db_port: Number(form.db_port.value || 3306),
                db_user: String(form.db_user.value || "itops"),
                db_password: String(form.db_password.value || ""),
                db_name: String(form.db_name.value || "itops"),
                mariadb_root_password: rootPassword,
            };
            const out = await requestJson("/setup/finalize", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const redirectUrl = String(out.redirect_url || "/portal").trim() || "/portal";
            setInfo(`${String(out.message || "Installation finalisee.")} Redirection vers ${redirectUrl}...`);
            setTimeout(() => {
                window.location.href = redirectUrl;
            }, 1400);
        } catch (error) {
            setError(error.message || "Impossible de finaliser l'installation.");
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = "Finaliser l'installation";
        }
    }

    function applyPasswordsVisibility() {
        const visible = Boolean(showPasswordsInput && showPasswordsInput.checked);
        const nextType = visible ? "text" : "password";
        if (adminPasswordInput) {
            adminPasswordInput.type = nextType;
        }
        if (adminPasswordConfirmInput) {
            adminPasswordConfirmInput.type = nextType;
        }
        if (dbPasswordInput) {
            dbPasswordInput.type = nextType;
        }
        if (dbRootPasswordInput) {
            dbRootPasswordInput.type = nextType;
        }
        if (dbRootPasswordConfirmInput) {
            dbRootPasswordConfirmInput.type = nextType;
        }
    }

    if (form) {
        form.addEventListener("submit", onSubmit);
    }
    if (showPasswordsInput) {
        showPasswordsInput.addEventListener("change", applyPasswordsVisibility);
    }
    if (reverseProxyInput) {
        reverseProxyInput.addEventListener("change", renderReverseProxyNote);
    }
    if (publicUrlInput) {
        publicUrlInput.addEventListener("input", renderReverseProxyNote);
    }
    applyPasswordsVisibility();
    renderReverseProxyNote();
    loadStatus().catch((error) => {
        setError(error.message || "Impossible de charger le statut d'installation.");
    });
})();
