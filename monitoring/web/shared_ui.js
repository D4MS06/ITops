(function () {
    function resolveSearchContainer(input) {
        if (!(input instanceof HTMLElement)) {
            return null;
        }
        return input.closest("label") || input.closest(".modal-inline-search") || input.parentElement;
    }

    function updateSearchVisibility(input, rowCount, threshold = 5) {
        if (!(input instanceof HTMLInputElement)) {
            return;
        }
        const container = resolveSearchContainer(input);
        if (!(container instanceof HTMLElement)) {
            return;
        }
        const show = Number(rowCount) >= Number(threshold);
        if (!show && input.value) {
            input.value = "";
        }
        container.hidden = !show;
    }

    function filterAndSortRows(rows, options = {}) {
        const source = Array.isArray(rows) ? rows.slice() : [];
        const query = String(options.query || "").trim().toLowerCase();
        const searchText = typeof options.searchText === "function" ? options.searchText : () => "";
        const sortColumn = String(options.sortColumn || "").trim();
        const sortDirection = String(options.sortDirection || "asc").trim();
        const compare = typeof options.compare === "function" ? options.compare : null;

        const filtered = query
            ? source.filter((item) => String(searchText(item) || "").toLowerCase().includes(query))
            : source;
        if (compare) {
            filtered.sort((left, right) => compare(sortColumn, sortDirection, left, right));
        }
        return filtered;
    }

    function bindHeaderSort(headElement, options = {}) {
        if (!(headElement instanceof HTMLElement)) {
            return;
        }
        const sortState = options.sortState || { column: "", direction: "asc" };
        const columnAttr = String(options.columnAttr || "col");
        const onChanged = typeof options.onChanged === "function" ? options.onChanged : () => {};
        headElement.addEventListener("click", (event) => {
            const target = event.target;
            if (!(target instanceof Element)) {
                return;
            }
            const th = target.closest(`th[data-${columnAttr}]`);
            if (!th) {
                return;
            }
            const col = String(th.getAttribute(`data-${columnAttr}`) || "").trim();
            if (!col) {
                return;
            }
            if (sortState.column === col) {
                sortState.direction = sortState.direction === "asc" ? "desc" : "asc";
            } else {
                sortState.column = col;
                sortState.direction = "asc";
            }
            onChanged();
        });
    }

    function defaultEscape(value) {
        return String(value || "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");
    }

    class SharedTreeView {
        constructor(options = {}) {
            this.headElement = options.headElement instanceof HTMLElement ? options.headElement : null;
            this.bodyElement = options.bodyElement instanceof HTMLElement ? options.bodyElement : null;
            this.searchInput = options.searchInput instanceof HTMLInputElement ? options.searchInput : null;
            this.sortState = options.sortState || { column: "", direction: "asc" };
            this.columnAttr = String(options.columnAttr || "col").trim() || "col";
            this.searchThreshold = Number(options.searchThreshold || 5);
            this.emptyMessage = String(options.emptyMessage || "Aucune donnee.").trim() || "Aucune donnee.";
            this.manageSortBinding = options.manageSortBinding !== false;
            this.manageSearchBinding = options.manageSearchBinding !== false;
            this.renderHeadEnabled = options.renderHead !== false;
            this.getRows = typeof options.getRows === "function" ? options.getRows : () => [];
            this.getColumns = typeof options.getColumns === "function" ? options.getColumns : () => [];
            this.searchText = typeof options.searchText === "function" ? options.searchText : () => "";
            this.compareRows = typeof options.compareRows === "function" ? options.compareRows : null;
            this.getRowKey = typeof options.getRowKey === "function" ? options.getRowKey : (_row, index) => String(index);
            this.getRowClassName = typeof options.getRowClassName === "function" ? options.getRowClassName : () => "";
            this.getRowAttributes = typeof options.getRowAttributes === "function" ? options.getRowAttributes : () => ({});
            this.renderRowCells = typeof options.renderRowCells === "function" ? options.renderRowCells : () => "";
            this.onSearchChanged = typeof options.onSearchChanged === "function" ? options.onSearchChanged : null;
            this.onRowsRendered = typeof options.onRowsRendered === "function" ? options.onRowsRendered : null;
            this.escapeHtml = typeof options.escapeHtml === "function" ? options.escapeHtml : defaultEscape;
            this.escapeAttribute = typeof options.escapeAttribute === "function" ? options.escapeAttribute : this.escapeHtml;
            this._visibleRows = [];
            this._bindInteractions();
        }

        _bindInteractions() {
            if (this.manageSortBinding && this.headElement) {
                bindHeaderSort(this.headElement, {
                    sortState: this.sortState,
                    columnAttr: this.columnAttr,
                    onChanged: () => this.render(),
                });
            }
            if (this.manageSearchBinding && this.searchInput && !this.searchInput.dataset.treeBound) {
                this.searchInput.dataset.treeBound = "1";
                this.searchInput.addEventListener("input", () => {
                    if (typeof this.onSearchChanged === "function") {
                        this.onSearchChanged(String(this.searchInput?.value || ""));
                    }
                    this.render();
                });
            }
        }

        _resolveQuery() {
            return String(this.searchInput?.value || "").trim().toLowerCase();
        }

        _resolveRawRows() {
            const rows = this.getRows();
            return Array.isArray(rows) ? rows : [];
        }

        _renderHead(columns) {
            if (!this.renderHeadEnabled || !(this.headElement instanceof HTMLElement)) {
                return;
            }
            const safeColumns = Array.isArray(columns) ? columns : [];
            const caret = (column) => {
                const key = String(column?.key || "").trim();
                const sortable = column?.sortable !== false && key;
                if (!sortable || String(this.sortState.column || "") !== key) {
                    return "";
                }
                return this.sortState.direction === "desc" ? " v" : " ^";
            };
            const headerMarkup = safeColumns
                .map((column) => {
                    const label = String(column?.label || "").trim();
                    const key = String(column?.key || "").trim();
                    const sortable = column?.sortable !== false && key;
                    const attrs = [];
                    if (sortable) {
                        attrs.push(`data-${this.columnAttr}="${this.escapeAttribute(key)}"`);
                    }
                    const className = String(column?.className || "").trim();
                    if (className) {
                        attrs.push(`class="${this.escapeAttribute(className)}"`);
                    }
                    return `<th ${attrs.join(" ")}>${this.escapeHtml(label)}${this.escapeHtml(caret(column))}</th>`;
                })
                .join("");
            this.headElement.innerHTML = `<tr>${headerMarkup}</tr>`;
        }

        getVisibleRows() {
            const rows = this._resolveRawRows();
            updateSearchVisibility(this.searchInput, rows.length, this.searchThreshold);
            const visibleRows = filterAndSortRows(rows, {
                query: this._resolveQuery(),
                searchText: this.searchText,
                sortColumn: String(this.sortState.column || "").trim(),
                sortDirection: String(this.sortState.direction || "asc").trim(),
                compare: this.compareRows,
            });
            this._visibleRows = visibleRows;
            return visibleRows.slice();
        }

        render() {
            const columns = Array.isArray(this.getColumns()) ? this.getColumns() : [];
            const rows = this.getVisibleRows();
            this._renderHead(columns);
            if (!(this.bodyElement instanceof HTMLElement)) {
                return rows;
            }
            if (!rows.length) {
                const colspan = Math.max(1, columns.length || 1);
                this.bodyElement.innerHTML = `<tr><td colspan="${colspan}">${this.escapeHtml(this.emptyMessage)}</td></tr>`;
                return rows;
            }
            this.bodyElement.innerHTML = rows
                .map((row, index) => {
                    const rowKey = String(this.getRowKey(row, index) || `${index}`);
                    const rowClassName = String(this.getRowClassName(row, index) || "").trim();
                    const attrs = [
                        `data-tree-row-key="${this.escapeAttribute(rowKey)}"`,
                    ];
                    if (rowClassName) {
                        attrs.push(`class="${this.escapeAttribute(rowClassName)}"`);
                    }
                    const extraAttrs = this.getRowAttributes(row, index);
                    if (extraAttrs && typeof extraAttrs === "object") {
                        Object.entries(extraAttrs).forEach(([name, value]) => {
                            const normalizedName = String(name || "").trim();
                            if (!normalizedName) {
                                return;
                            }
                            attrs.push(`${normalizedName}="${this.escapeAttribute(String(value ?? ""))}"`);
                        });
                    }
                    return `<tr ${attrs.join(" ")}>${String(this.renderRowCells(row, index) || "")}</tr>`;
                })
                .join("");
            if (typeof this.onRowsRendered === "function") {
                this.onRowsRendered(rows, columns);
            }
            return rows;
        }
    }

    function closeTopMenu(state, panel, buttons = []) {
        if (panel) {
            panel.hidden = true;
            panel.innerHTML = "";
        }
        if (state && typeof state === "object") {
            state.openTopMenu = "";
        }
        for (const button of Array.isArray(buttons) ? buttons : []) {
            if (button && button.classList) {
                button.classList.remove("active");
            }
        }
    }

    function openTopMenu(options = {}) {
        const state = options.state;
        const panel = options.panel;
        const buttons = Array.isArray(options.buttons) ? options.buttons : [];
        const button = options.button || null;
        const menuKey = String(options.menuKey || "").trim();
        const buildMarkup = typeof options.buildMarkup === "function" ? options.buildMarkup : (() => "");
        const onBeforeOpen = typeof options.onBeforeOpen === "function" ? options.onBeforeOpen : null;
        const onAfterOpen = typeof options.onAfterOpen === "function" ? options.onAfterOpen : null;
        if (!state || !panel || !menuKey || !(button instanceof Element)) {
            return false;
        }
        if (state.openTopMenu === menuKey && !panel.hidden) {
            closeTopMenu(state, panel, buttons);
            return false;
        }
        if (onBeforeOpen) {
            onBeforeOpen();
        }
        state.openTopMenu = menuKey;
        panel.innerHTML = String(buildMarkup(menuKey) || "");
        panel.hidden = false;
        for (const entry of buttons) {
            if (entry && entry.classList) {
                entry.classList.toggle("active", entry === button);
            }
        }
        const rect = button.getBoundingClientRect();
        panel.style.left = `${Math.max(8, rect.left)}px`;
        panel.style.top = `${rect.bottom + 4}px`;
        if (onAfterOpen) {
            onAfterOpen(menuKey, panel);
        }
        return true;
    }

    class SharedModalController {
        constructor(options = {}) {
            this.modal = options.modal instanceof HTMLElement ? options.modal : null;
            this.titleNode = options.titleNode instanceof HTMLElement ? options.titleNode : null;
            this.bodyNode = options.bodyNode instanceof HTMLElement ? options.bodyNode : null;
            this.panelNode = options.panelNode instanceof HTMLElement ? options.panelNode : null;
            this.defaultWidth = String(options.defaultWidth || "min(980px, calc(100vw - 40px))");
            this.onBeforeClose = typeof options.onBeforeClose === "function" ? options.onBeforeClose : null;
            this.onAfterClose = typeof options.onAfterClose === "function" ? options.onAfterClose : null;
            this.onAfterOpen = typeof options.onAfterOpen === "function" ? options.onAfterOpen : null;
        }

        open(title, bodyMarkup, options = {}) {
            if (this.titleNode) {
                this.titleNode.textContent = String(title || "");
            }
            if (this.bodyNode) {
                this.bodyNode.innerHTML = String(bodyMarkup || "");
            }
            if (this.panelNode) {
                this.panelNode.style.width = String(options.width || this.defaultWidth);
            }
            if (this.modal) {
                this.modal.hidden = false;
            }
            if (this.onAfterOpen) {
                this.onAfterOpen({ title, bodyMarkup, options });
            }
        }

        close(reason = "manual") {
            if (this.onBeforeClose) {
                this.onBeforeClose(reason);
            }
            if (this.modal) {
                this.modal.hidden = true;
            }
            if (this.bodyNode) {
                this.bodyNode.innerHTML = "";
            }
            if (this.onAfterClose) {
                this.onAfterClose(reason);
            }
        }
    }

    class SharedTopMenuController {
        constructor(options = {}) {
            this.state = options.state;
            this.panel = options.panel instanceof HTMLElement ? options.panel : null;
            this.buttons = Array.isArray(options.buttons) ? options.buttons : [];
            this.buildMarkup = typeof options.buildMarkup === "function" ? options.buildMarkup : (() => "");
            this.onBeforeOpen = typeof options.onBeforeOpen === "function" ? options.onBeforeOpen : null;
            this.onAfterOpen = typeof options.onAfterOpen === "function" ? options.onAfterOpen : null;
        }

        close() {
            closeTopMenu(this.state, this.panel, this.buttons);
        }

        open(button, menuKey, overrides = {}) {
            const activeButtons = Array.isArray(overrides.buttons) ? overrides.buttons : this.buttons;
            return openTopMenu({
                state: this.state,
                panel: this.panel,
                buttons: activeButtons,
                button,
                menuKey,
                buildMarkup: typeof overrides.buildMarkup === "function" ? overrides.buildMarkup : this.buildMarkup,
                onBeforeOpen: typeof overrides.onBeforeOpen === "function" ? overrides.onBeforeOpen : this.onBeforeOpen,
                onAfterOpen: typeof overrides.onAfterOpen === "function" ? overrides.onAfterOpen : this.onAfterOpen,
            });
        }
    }

    function createModalController(options = {}) {
        return new SharedModalController(options);
    }

    function createTopMenuController(options = {}) {
        return new SharedTopMenuController(options);
    }

    function createFieldMarkup({ key, label, value, wide = false, multiline = false, inputType = "text", escapeHtml }) {
        const escape = typeof escapeHtml === "function" ? escapeHtml : (raw) => String(raw || "");
        if (multiline) {
            return `
        <label class="field ${wide ? "wide" : ""}">
            <span>${escape(label)}</span>
            <textarea name="${escape(key)}">${escape(value)}</textarea>
        </label>
    `;
        }
        return `
    <label class="field ${wide ? "wide" : ""}">
        <span>${escape(label)}</span>
        <input name="${escape(key)}" type="${escape(inputType || "text")}" value="${escape(value)}">
    </label>
    `;
    }

    const ACTION_BUTTON_PRESETS = Object.freeze({
        cancel: {
            className: "toolbar-btn",
            type: "button",
            action: "modal:close",
            label: "Annuler",
            iconHtml: "&#10005;",
            iconClass: "cancel",
        },
        close: {
            className: "toolbar-btn",
            type: "button",
            action: "modal:close",
            label: "Fermer",
            iconHtml: "&#10005;",
            iconClass: "close",
        },
        back: {
            className: "toolbar-btn",
            type: "button",
            label: "Retour",
            iconHtml: "&#8592;",
            iconClass: "back",
        },
        save: {
            className: "primary-btn",
            type: "submit",
            label: "Enregistrer",
            iconHtml: "&#10003;",
            iconClass: "save",
        },
        add: {
            className: "primary-btn",
            type: "submit",
            label: "Ajouter",
            iconHtml: "&#43;",
            iconClass: "add",
        },
        settings: {
            className: "toolbar-btn",
            type: "button",
            label: "Parametres",
            iconHtml: "&#9881;",
            iconClass: "settings",
        },
        refresh: {
            className: "toolbar-btn",
            type: "button",
            label: "Actualiser",
            iconHtml: "&#8635;",
            iconClass: "refresh",
        },
        download: {
            className: "toolbar-btn",
            type: "button",
            label: "Telecharger",
            iconHtml: "&#8681;",
            iconClass: "download",
        },
        import: {
            className: "primary-btn",
            type: "button",
            label: "Importer",
            iconHtml: "&#8682;",
            iconClass: "import",
        },
        export: {
            className: "toolbar-btn",
            type: "button",
            label: "Exporter",
            iconHtml: "&#8681;",
            iconClass: "export",
        },
        stop: {
            className: "toolbar-btn",
            type: "button",
            label: "Arreter",
            iconHtml: "&#9632;",
            iconClass: "stop",
        },
        run: {
            className: "primary-btn",
            type: "submit",
            label: "Lancer",
            iconHtml: "&#9654;",
            iconClass: "run",
        },
    });

    const ACTION_ICON_HTML = Object.freeze({
        add: "&#43;",
        edit: "&#9998;",
        settings: "&#9881;",
        delete: "&#128465;",
        list: "&#128203;",
        check: "&#10003;",
        close: "&#10005;",
        refresh: "&#8635;",
        download: "&#8681;",
        upload: "&#8682;",
        stop: "&#9632;",
        run: "&#9654;",
    });

    function normalizeActionButtonSpec(rawSpec) {
        if (typeof rawSpec === "string") {
            return { preset: rawSpec };
        }
        if (rawSpec && typeof rawSpec === "object" && !Array.isArray(rawSpec)) {
            return rawSpec;
        }
        return {};
    }

    function createActionButtonMarkup(spec = {}, options = {}) {
        const escape = typeof options.escapeHtml === "function" ? options.escapeHtml : defaultEscape;
        const escapeAttr = typeof options.escapeAttribute === "function" ? options.escapeAttribute : escape;
        const normalized = normalizeActionButtonSpec(spec);
        const presetKey = String(normalized.preset || "").trim().toLowerCase();
        const preset = ACTION_BUTTON_PRESETS[presetKey] || {};
        const buttonClass = String(normalized.className || preset.className || "toolbar-btn").trim() || "toolbar-btn";
        const buttonType = String(normalized.type || preset.type || "button").trim().toLowerCase() || "button";
        const buttonAction = String(normalized.action || preset.action || "").trim();
        const buttonLabel = String(normalized.label ?? preset.label ?? "").trim();
        const buttonTitle = String(normalized.title || "").trim();
        const buttonId = String(normalized.id || "").trim();
        const buttonName = String(normalized.name || "").trim();
        const buttonValue = String(normalized.value || "").trim();
        const iconClass = String(normalized.iconClass || preset.iconClass || "").trim();
        const iconHtml = String(normalized.iconHtml || preset.iconHtml || "").trim();
        const iconText = String(normalized.iconText || "").trim();
        const showIcon = normalized.showIcon !== false && Boolean(iconHtml || iconText);
        const attrs = [
            `class="${escapeAttr(buttonClass)}"`,
            `type="${escapeAttr(buttonType)}"`,
        ];
        if (buttonAction) {
            attrs.push(`data-action="${escapeAttr(buttonAction)}"`);
        }
        const dataAttrs = normalized.data && typeof normalized.data === "object" ? normalized.data : {};
        Object.entries(dataAttrs).forEach(([name, value]) => {
            const rawName = String(name || "").trim();
            if (!rawName || value === undefined || value === null || value === false) {
                return;
            }
            const dataName = rawName
                .replaceAll("_", "-")
                .replaceAll(" ", "-")
                .replace(/[A-Z]/g, (match) => `-${match.toLowerCase()}`);
            if (value === true) {
                attrs.push(`data-${dataName}`);
                return;
            }
            attrs.push(`data-${dataName}="${escapeAttr(String(value))}"`);
        });
        const extraAttrs = normalized.attrs && typeof normalized.attrs === "object" ? normalized.attrs : {};
        Object.entries(extraAttrs).forEach(([name, value]) => {
            const attrName = String(name || "").trim();
            if (!attrName || value === undefined || value === null || value === false) {
                return;
            }
            if (value === true) {
                attrs.push(attrName);
                return;
            }
            attrs.push(`${attrName}="${escapeAttr(String(value))}"`);
        });
        if (buttonTitle) {
            attrs.push(`title="${escapeAttr(buttonTitle)}"`);
        }
        if (buttonId) {
            attrs.push(`id="${escapeAttr(buttonId)}"`);
        }
        if (buttonName) {
            attrs.push(`name="${escapeAttr(buttonName)}"`);
        }
        if (buttonValue) {
            attrs.push(`value="${escapeAttr(buttonValue)}"`);
        }
        if (normalized.disabled) {
            attrs.push("disabled");
        }
        const ariaLabel = String(normalized.ariaLabel || (buttonLabel ? "" : buttonTitle)).trim();
        if (ariaLabel) {
            attrs.push(`aria-label="${escapeAttr(ariaLabel)}"`);
        }
        const iconSpanClass = iconClass ? ` ui-action-btn-icon-${escapeAttr(iconClass)}` : "";
        const iconMarkup = showIcon
            ? `<span class="ui-action-btn-icon${iconSpanClass}" aria-hidden="true">${iconHtml || escape(iconText)}</span>`
            : "";
        const labelMarkup = buttonLabel ? `<span class="ui-action-btn-label">${escape(buttonLabel)}</span>` : "";
        return `<button ${attrs.join(" ")}>${iconMarkup}${labelMarkup}</button>`;
    }

    function createIconActionButtonMarkup(spec = {}, options = {}) {
        const normalized = normalizeActionButtonSpec(spec);
        const iconKey = String(normalized.icon || "").trim().toLowerCase();
        const baseClass = String(normalized.className || "inventory-action-btn").trim() || "inventory-action-btn";
        const className = normalized.danger ? `${baseClass} danger` : baseClass;
        return createActionButtonMarkup({
            ...normalized,
            className,
            type: String(normalized.type || "button").trim() || "button",
            iconHtml: normalized.iconHtml || ACTION_ICON_HTML[iconKey] || "",
            showIcon: normalized.showIcon !== false,
            ariaLabel: normalized.ariaLabel || normalized.title || normalized.label || "",
        }, options);
    }

    function createModalActionsMarkup(options = {}) {
        const escape = typeof options.escapeHtml === "function" ? options.escapeHtml : defaultEscape;
        const escapeAttr = typeof options.escapeAttribute === "function" ? options.escapeAttribute : escape;
        const buttons = Array.isArray(options.buttons) && options.buttons.length
            ? options.buttons
            : [{ preset: "cancel" }, { preset: "save" }];
        const className = ["modal-actions", String(options.className || "").trim()].filter(Boolean).join(" ");
        const buttonMarkup = buttons
            .map((button) => createActionButtonMarkup(button, { escapeHtml: escape, escapeAttribute: escapeAttr }))
            .join("");
        return `<div class="${escapeAttr(className)}">${buttonMarkup}</div>`;
    }

    function normalizeWebPort(rawPort) {
        const parsed = Number(rawPort || 8000);
        if (!Number.isFinite(parsed)) {
            return 8000;
        }
        return Math.max(1, Math.min(65535, Math.trunc(parsed)));
    }

    function buildWebServerSettingsMarkup(options = {}) {
        const settings = options.settings || {};
        const field = typeof options.field === "function"
            ? options.field
            : (key, label, value, wide = false) => createFieldMarkup({ key, label, value, wide });
        const rawProxy = String(settings.web_server_reverse_proxy_type || "aucun").trim().toLowerCase();
        const reverseProxyType = ["aucun", "nginx", "caddy"].includes(rawProxy) ? rawProxy : "aucun";
        return `
    <form id="modal-webserver-form" class="modal-form">
        <div class="modal-settings-grid">
            ${field("web_server_host", "Host", settings.web_server_host || "127.0.0.1")}
            ${field("web_server_port", "Port", settings.web_server_port || 8000)}
            ${field("web_server_public_url", "URL publique", settings.web_server_public_url || "", true)}
            <label class="field">
                <span>Reverse proxy</span>
                <select name="web_server_reverse_proxy_type">
                    <option value="aucun" ${reverseProxyType === "aucun" ? "selected" : ""}>Aucun</option>
                    <option value="nginx" ${reverseProxyType === "nginx" ? "selected" : ""}>Nginx</option>
                    <option value="caddy" ${reverseProxyType === "caddy" ? "selected" : ""}>Caddy</option>
                </select>
            </label>
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
        ${createModalActionsMarkup({
            buttons: [{ preset: "cancel" }, { preset: "save" }],
        })}
    </form>
    `;
    }

    function parseWebServerSettingsForm(form) {
        const formData = new window.FormData(form);
        const rawProxy = String(formData.get("web_server_reverse_proxy_type") || "aucun").trim().toLowerCase();
        const reverseProxyType = ["aucun", "nginx", "caddy"].includes(rawProxy) ? rawProxy : "aucun";
        return {
            web_server_host: String(formData.get("web_server_host") || "127.0.0.1").trim() || "127.0.0.1",
            web_server_port: normalizeWebPort(formData.get("web_server_port")),
            web_server_autostart: form?.querySelector?.('[name="web_server_autostart"]')?.checked ?? false,
            web_server_public_url: String(formData.get("web_server_public_url") || "").trim(),
            web_server_use_public_url: form?.querySelector?.('[name="web_server_use_public_url"]')?.checked ?? false,
            web_server_reverse_proxy_type: reverseProxyType,
        };
    }

    window.NMPSharedUi = {
        closeTopMenu,
        openTopMenu,
        createFieldMarkup,
        createActionButtonMarkup,
        createIconActionButtonMarkup,
        createModalActionsMarkup,
        webServer: {
            buildSettingsMarkup: buildWebServerSettingsMarkup,
            parseSettingsForm: parseWebServerSettingsForm,
        },
        formControls: {
            createActionButtonMarkup,
            createIconActionButtonMarkup,
            createModalActionsMarkup,
        },
        tableTools: {
            updateSearchVisibility,
            filterAndSortRows,
            bindHeaderSort,
        },
        shell: {
            createModalController,
            createTopMenuController,
        },
        treeView: {
            SharedTreeView,
        },
    };
})();
