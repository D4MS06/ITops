(function () {
    function createMenuButton(label, action, hint, disabled) {
        return `
        <button
            class="context-menu-item"
            type="button"
            data-action="${String(action || "").replaceAll('"', "&quot;")}"
            ${disabled ? "disabled" : ""}
        >
            <span>${String(label || "")}</span>
            <span class="context-menu-hint">${String(hint || "")}</span>
        </button>
    `;
    }

    function createSubmenu(label, itemsMarkup, disabled) {
        return `
        <div class="context-menu-submenu">
            <button class="context-menu-summary" type="button" ${disabled ? "disabled" : ""}>
                <span>${String(label || "")}</span>
                <span class="context-menu-hint">${disabled ? "Indisponible" : ">"}</span>
            </button>
            ${disabled ? "" : `<div class="context-menu-submenu-panel">${itemsMarkup}</div>`}
        </div>
    `;
    }

    function renderTopMenuEntry(entry) {
        if (Array.isArray(entry?.items) && entry.items.length) {
            const itemsMarkup = entry.items
                .map((item) => createMenuButton(item.label, item.action, "", Boolean(item.disabled)))
                .join("");
            return createSubmenu(entry.label, itemsMarkup, Boolean(entry.disabled));
        }
        return createMenuButton(entry?.label || "", entry?.action || "", "", Boolean(entry?.disabled));
    }

    function renderTopMenuGroup(entries) {
        return `
        <div class="context-menu-group">
            ${(entries || []).map((entry) => renderTopMenuEntry(entry)).join("")}
        </div>
    `;
    }

    function commonDefinitions() {
        return {
            supervision: [
                {
                    label: "Serveur web",
                    items: [
                        { label: "Portail modules", action: "menu:portal" },
                        { label: "Parametres...", action: "menu:web" },
                        { label: "Export certificat HTTPS...", action: "menu:cert" },
                    ],
                },
            ],
            display: [
                {
                    label: "Theme",
                    items: [
                        { label: "Clair", action: "menu:theme-light" },
                        { label: "Sombre", action: "menu:theme-dark" },
                    ],
                },
            ],
            help: [
                { label: "A propos...", action: "menu:about" },
            ],
        };
    }

    function buildCommonActions(ctx) {
        return {
            "menu:portal": () => ctx.navigatePortal(),
            "menu:web": () => ctx.openWebServerSettingsModal(),
            "menu:cert": async () => {
                try {
                    await ctx.downloadHttpsRootCertificate();
                    ctx.openModal(
                        "Certificat HTTPS",
                        `
                        <section class="modal-section">
                            <p>Certificat racine telecharge.</p>
                            <p class="muted">Importe ce certificat uniquement sur les postes autorises (Trusted Root).</p>
                        </section>
                    `,
                        { width: "min(560px, calc(100vw - 40px))" },
                    );
                } catch (error) {
                    ctx.openModal(
                        "Certificat HTTPS",
                        `
                        <section class="modal-section">
                            <p class="error-text">${ctx.escapeHtml(ctx.normalizeErrorMessage(error.message))}</p>
                        </section>
                    `,
                        { width: "min(560px, calc(100vw - 40px))" },
                    );
                }
            },
            "menu:theme-light": () => ctx.applySettingsPatch({ ui_theme: "light" }),
            "menu:theme-dark": () => ctx.applySettingsPatch({ ui_theme: "dark" }),
            "menu:about": () => ctx.openModal(
                "A propos",
                `
                <section class="modal-section">
                    <h3>ITops</h3>
                    <p class="muted">Version web: ${ctx.escapeHtml(ctx.getAppVersionText())}</p>
                    <p class="muted">${ctx.aboutText || "Interface web alignee au runtime desktop."}</p>
                </section>
            `,
                { width: "min(560px, calc(100vw - 40px))" },
            ),
        };
    }

    window.NMPSharedMenu = {
        createMenuButton,
        createSubmenu,
        renderTopMenuGroup,
        commonDefinitions,
        buildCommonActions,
    };
})();
