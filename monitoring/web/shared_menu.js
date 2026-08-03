(function () {
    const TOP_MENU_LAYOUTS = Object.freeze({
        monitoring: Object.freeze([
            Object.freeze({ key: "modules", label: "Services" }),
            Object.freeze({ key: "supervision", label: "Supervision" }),
            Object.freeze({ key: "equipments", label: "Equipements" }),
            Object.freeze({ key: "tools", label: "Outils" }),
            Object.freeze({ key: "help", label: "Aide" }),
        ]),
        portal: Object.freeze([
            Object.freeze({ key: "supervision", label: "Gestion" }),
            Object.freeze({ key: "configuration", label: "Configuration" }),
            Object.freeze({ key: "help", label: "Aide" }),
        ]),
        module: Object.freeze([
            Object.freeze({ key: "services", label: "Services" }),
            Object.freeze({ key: "data", label: "Données" }),
            Object.freeze({ key: "help", label: "Aide" }),
        ]),
    });

    function topMenuLayout(name = "portal") {
        const normalizedName = String(name || "").trim().toLowerCase();
        const layout = TOP_MENU_LAYOUTS[normalizedName] || TOP_MENU_LAYOUTS.portal;
        return layout.map((entry) => ({ ...entry }));
    }

    function applyTopMenuLayout(menuBar, name = "portal") {
        if (!(menuBar instanceof HTMLElement)) {
            return [];
        }
        const layout = topMenuLayout(name);
        const buttons = Array.from(menuBar.querySelectorAll("[data-top-menu-button]"));
        buttons.forEach((button, index) => {
            const entry = layout[index];
            button.hidden = !entry;
            if (!entry) {
                button.dataset.menuKey = "";
                return;
            }
            button.dataset.menuKey = entry.key;
            button.textContent = entry.label;
        });
        return layout;
    }

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

    function renderMenuEntry(entry) {
        if (Array.isArray(entry?.items) && entry.items.length) {
            const itemsMarkup = entry.items
                .map((item) => renderMenuEntry(item))
                .join("");
            return createSubmenu(entry.label, itemsMarkup, Boolean(entry.disabled));
        }
        return createMenuButton(entry?.label || "", entry?.action || "", "", Boolean(entry?.disabled));
    }

    function renderTopMenuEntry(entry) {
        return renderMenuEntry(entry);
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
                        { label: "Parametres...", action: "menu:web" },
                        { label: "Export certificat HTTPS...", action: "menu:cert" },
                    ],
                },
            ],
            display: [],
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
        topMenuLayout,
        applyTopMenuLayout,
        createMenuButton,
        createSubmenu,
        renderTopMenuGroup,
        commonDefinitions,
        buildCommonActions,
    };
})();
