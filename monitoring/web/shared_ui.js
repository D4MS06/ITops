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

    function normalizeSearchText(value) {
        return String(value || "")
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .toLowerCase()
            .trim();
    }

    function filterAndSortRows(rows, options = {}) {
        const source = Array.isArray(rows) ? rows.slice() : [];
        const query = normalizeSearchText(options.query);
        const searchText = typeof options.searchText === "function" ? options.searchText : () => "";
        const sortColumn = String(options.sortColumn || "").trim();
        const sortDirection = String(options.sortDirection || "asc").trim();
        const compare = typeof options.compare === "function" ? options.compare : null;

        const filtered = query
            ? source.filter((item) => normalizeSearchText(searchText(item)).includes(query))
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

    let activeTreeViewColumnMenu = null;

    function closeTreeViewColumnMenu() {
        if (activeTreeViewColumnMenu instanceof HTMLElement) {
            activeTreeViewColumnMenu.remove();
        }
        activeTreeViewColumnMenu = null;
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
            this.renderRowCells = typeof options.renderRowCells === "function" ? options.renderRowCells : null;
            this.onSearchChanged = typeof options.onSearchChanged === "function" ? options.onSearchChanged : null;
            this.onRowsRendered = typeof options.onRowsRendered === "function" ? options.onRowsRendered : null;
            this.onSelectionChanged = typeof options.onSelectionChanged === "function" ? options.onSelectionChanged : null;
            this.onBackgroundContextMenu = typeof options.onBackgroundContextMenu === "function"
                ? options.onBackgroundContextMenu
                : null;
            this.columnVisibilityEnabled = options.columnVisibility !== false;
            this.columnVisibilityStorageKey = String(options.columnVisibilityStorageKey || "").trim();
            this.hiddenColumnKeys = new Set(
                Array.isArray(options.hiddenColumnKeys)
                    ? options.hiddenColumnKeys.map((key) => String(key || "").trim()).filter(Boolean)
                    : [],
            );
            this.selectionEnabled = Boolean(options.selectable || options.selectionEnabled);
            this.selectedRowKeys = new Set(
                Array.isArray(options.selectedRowKeys)
                    ? options.selectedRowKeys.map((key) => String(key || "").trim()).filter(Boolean)
                    : [],
            );
            this.escapeHtml = typeof options.escapeHtml === "function" ? options.escapeHtml : defaultEscape;
            this.escapeAttribute = typeof options.escapeAttribute === "function" ? options.escapeAttribute : this.escapeHtml;
            this.tableElement = options.tableElement instanceof HTMLTableElement ? options.tableElement : this._resolveTableElement();
            this.wrapElement = options.wrapElement instanceof HTMLElement ? options.wrapElement : this._resolveWrapElement();
            if (!this.columnVisibilityStorageKey) {
                this.columnVisibilityStorageKey = this._resolveColumnVisibilityStorageKey();
            }
            this._loadColumnVisibility();
            this._visibleRows = [];
            this._decorateStructure();
            this._bindInteractions();
        }

        _resolveTableElement() {
            if (this.bodyElement instanceof HTMLElement) {
                const fromBody = this.bodyElement.closest("table");
                if (fromBody instanceof HTMLTableElement) {
                    return fromBody;
                }
            }
            if (this.headElement instanceof HTMLElement) {
                const fromHead = this.headElement.closest("table");
                if (fromHead instanceof HTMLTableElement) {
                    return fromHead;
                }
            }
            return null;
        }

        _resolveWrapElement() {
            if (this.tableElement instanceof HTMLElement) {
                const tableWrap = this.tableElement.closest(".table-wrap");
                if (tableWrap instanceof HTMLElement) {
                    return tableWrap;
                }
                if (this.tableElement.parentElement instanceof HTMLElement) {
                    return this.tableElement.parentElement;
                }
            }
            return null;
        }

        _resolveColumnVisibilityStorageKey() {
            const tableId = String(this.tableElement?.id || "").trim();
            if (tableId) {
                return `nmp:treeview:columns:${tableId}`;
            }
            const headId = String(this.headElement?.id || "").trim();
            if (headId) {
                return `nmp:treeview:columns:${headId}`;
            }
            const bodyId = String(this.bodyElement?.id || "").trim();
            if (bodyId) {
                return `nmp:treeview:columns:${bodyId}`;
            }
            return "";
        }

        _loadColumnVisibility() {
            if (!this.columnVisibilityStorageKey || !window.localStorage) {
                return;
            }
            try {
                const raw = window.localStorage.getItem(this.columnVisibilityStorageKey);
                const parsed = raw ? JSON.parse(raw) : [];
                if (Array.isArray(parsed)) {
                    parsed.map((key) => String(key || "").trim()).filter(Boolean).forEach((key) => {
                        this.hiddenColumnKeys.add(key);
                    });
                }
            } catch (_error) {
                // Local preferences are optional; invalid data must not break Treeview rendering.
            }
        }

        _saveColumnVisibility() {
            if (!this.columnVisibilityStorageKey || !window.localStorage) {
                return;
            }
            try {
                window.localStorage.setItem(this.columnVisibilityStorageKey, JSON.stringify(Array.from(this.hiddenColumnKeys)));
            } catch (_error) {
                // Ignore localStorage failures (private mode, quota, locked profile).
            }
        }

        _decorateStructure() {
            if (this.wrapElement instanceof HTMLElement) {
                this.wrapElement.classList.add("shared-treeview-wrap");
            }
            if (this.tableElement instanceof HTMLTableElement) {
                this.tableElement.classList.add("shared-treeview-table");
                if (!this.tableElement.classList.contains("device-table")) {
                    this.tableElement.classList.add("device-table");
                }
            }
            if (this.headElement instanceof HTMLElement) {
                this.headElement.classList.add("shared-treeview-head");
                this.headElement.title = this.columnVisibilityEnabled
                    ? "Clic droit: afficher ou masquer les colonnes"
                    : this.headElement.title;
            }
            if (this.bodyElement instanceof HTMLElement) {
                this.bodyElement.classList.add("shared-treeview-body");
            }
            this._syncSortableHeadState();
        }

        _syncSortableHeadState() {
            if (!(this.headElement instanceof HTMLElement)) {
                return;
            }
            const targetColumn = String(this.sortState?.column || "").trim();
            const targetDirection = String(this.sortState?.direction || "asc").trim() === "desc" ? "desc" : "asc";
            const sortAttr = `data-${this.columnAttr}`;
            const headers = Array.from(this.headElement.querySelectorAll("th"));
            headers.forEach((th) => {
                const rawColumn = String(th.getAttribute(sortAttr) || "").trim();
                const sortable = Boolean(rawColumn);
                th.classList.remove("shared-treeview-sortable", "shared-treeview-sort-asc", "shared-treeview-sort-desc");
                if (!sortable) {
                    th.removeAttribute("aria-sort");
                    return;
                }
                th.classList.add("shared-treeview-sortable");
                if (rawColumn === targetColumn) {
                    th.classList.add(targetDirection === "desc" ? "shared-treeview-sort-desc" : "shared-treeview-sort-asc");
                    th.setAttribute("aria-sort", targetDirection === "desc" ? "descending" : "ascending");
                } else {
                    th.setAttribute("aria-sort", "none");
                }
            });
        }

        _columnKey(column, index) {
            return String(column?.key || column?.generatedKey || `column:${index}`).trim();
        }

        _columnLabel(column, index) {
            return String(column?.label || column?.title || this._columnKey(column, index) || `Colonne ${index + 1}`).trim();
        }

        _columnHideable(column, index) {
            if (column?.hideable === false) {
                return false;
            }
            const key = this._columnKey(column, index);
            const label = this._columnLabel(column, index).toLowerCase();
            if (!key) {
                return false;
            }
            if (label === "actions" || label === "action") {
                return false;
            }
            return true;
        }

        _isColumnVisible(column, index) {
            if (!this._columnHideable(column, index)) {
                return true;
            }
            return !this.hiddenColumnKeys.has(this._columnKey(column, index));
        }

        _resolveColumnsFromHead() {
            if (!(this.headElement instanceof HTMLElement)) {
                return [];
            }
            const sortAttr = `data-${this.columnAttr}`;
            return Array.from(this.headElement.querySelectorAll("th"))
                .filter((th) => !th.matches(".shared-treeview-select-col"))
                .map((th, index) => {
                    const key = String(th.getAttribute(sortAttr) || th.getAttribute("data-tree-column-key") || "").trim();
                    const label = String(th.textContent || "").trim() || `Colonne ${index + 1}`;
                    const generatedKey = key || `head:${index}:${label.toLowerCase().replace(/\s+/g, "-")}`;
                    return {
                        key,
                        generatedKey,
                        label,
                        sortable: Boolean(key),
                        hideable: label.toLowerCase() === "actions" ? false : undefined,
                    };
                });
        }

        _resolveColumns() {
            const columns = this.getColumns();
            const safeColumns = Array.isArray(columns) ? columns.filter(Boolean) : [];
            if (safeColumns.length) {
                return safeColumns;
            }
            return this._resolveColumnsFromHead();
        }

        _visibleColumns(columns) {
            return (Array.isArray(columns) ? columns : []).filter((column, index) => this._isColumnVisible(column, index));
        }

        _hideableColumns(columns) {
            return (Array.isArray(columns) ? columns : []).filter((column, index) => this._columnHideable(column, index));
        }

        _visibleHideableColumnCount(columns) {
            return this._hideableColumns(columns).filter((column, index) => {
                const originalIndex = columns.indexOf(column);
                return this._isColumnVisible(column, originalIndex >= 0 ? originalIndex : index);
            }).length;
        }

        _setColumnHidden(column, index, hidden) {
            const key = this._columnKey(column, index);
            if (!key || !this._columnHideable(column, index)) {
                return;
            }
            if (hidden) {
                this.hiddenColumnKeys.add(key);
            } else {
                this.hiddenColumnKeys.delete(key);
            }
            this._saveColumnVisibility();
            this.render();
        }

        _resetColumnVisibility() {
            this.hiddenColumnKeys.clear();
            this._saveColumnVisibility();
            this.render();
        }

        _applyColumnVisibilityToHead(columns) {
            if (!(this.headElement instanceof HTMLElement)) {
                return;
            }
            const headerCells = Array.from(this.headElement.querySelectorAll("th"))
                .filter((th) => !th.matches(".shared-treeview-select-col"));
            headerCells.forEach((th, index) => {
                const column = columns[index];
                const hidden = column ? !this._isColumnVisible(column, index) : false;
                th.classList.toggle("shared-treeview-col-hidden", hidden);
                th.setAttribute("aria-hidden", hidden ? "true" : "false");
                if (column) {
                    th.setAttribute("data-tree-column-key", this._columnKey(column, index));
                }
            });
        }

        _applyColumnVisibilityToRenderedCells(columns) {
            if (!(this.bodyElement instanceof HTMLElement)) {
                return;
            }
            const selectionOffset = this.selectionEnabled ? 1 : 0;
            for (const row of Array.from(this.bodyElement.querySelectorAll("tr"))) {
                const cells = Array.from(row.children).filter((cell) => cell instanceof HTMLTableCellElement);
                columns.forEach((column, index) => {
                    const cell = cells[index + selectionOffset];
                    if (!(cell instanceof HTMLElement)) {
                        return;
                    }
                    const hidden = !this._isColumnVisible(column, index);
                    cell.classList.toggle("shared-treeview-col-hidden", hidden);
                    cell.setAttribute("aria-hidden", hidden ? "true" : "false");
                    cell.setAttribute("data-tree-column-key", this._columnKey(column, index));
                });
            }
        }

        _positionColumnMenu(menu, x, y) {
            document.body.appendChild(menu);
            const rect = menu.getBoundingClientRect();
            const left = Math.max(8, Math.min(Number(x || 0), window.innerWidth - rect.width - 8));
            const top = Math.max(8, Math.min(Number(y || 0), window.innerHeight - rect.height - 8));
            menu.style.left = `${left}px`;
            menu.style.top = `${top}px`;
        }

        _openColumnVisibilityMenu(event) {
            const columns = this._resolveColumns();
            const hideableColumns = this._hideableColumns(columns);
            if (!this.columnVisibilityEnabled || !hideableColumns.length) {
                return false;
            }
            event.preventDefault();
            event.stopPropagation();
            closeTreeViewColumnMenu();
            const menu = document.createElement("div");
            menu.className = "context-menu shared-treeview-column-menu";
            menu.innerHTML = `
                <div class="context-menu-group">
                    <div class="context-menu-label">Colonnes</div>
                    ${hideableColumns.map((column) => {
                        const index = columns.indexOf(column);
                        const safeIndex = index >= 0 ? index : 0;
                        const key = this._columnKey(column, safeIndex);
                        const checked = this._isColumnVisible(column, safeIndex) ? "checked" : "";
                        return `
                            <label class="context-menu-item shared-treeview-column-menu-item">
                                <span>${this.escapeHtml(this._columnLabel(column, safeIndex))}</span>
                                <input type="checkbox" data-tree-column-toggle value="${this.escapeAttribute(key)}" ${checked}>
                            </label>
                        `;
                    }).join("")}
                </div>
                <div class="context-menu-group">
                    <button class="context-menu-item" type="button" data-tree-column-reset>
                        <span>Tout afficher</span>
                    </button>
                </div>
            `;
            menu.addEventListener("click", (clickEvent) => {
                clickEvent.stopPropagation();
                const target = clickEvent.target;
                if (target instanceof HTMLElement && target.matches("[data-tree-column-reset]")) {
                    this._resetColumnVisibility();
                    closeTreeViewColumnMenu();
                }
            });
            menu.addEventListener("change", (changeEvent) => {
                changeEvent.stopPropagation();
                const target = changeEvent.target;
                if (!(target instanceof HTMLInputElement) || !target.matches("[data-tree-column-toggle]")) {
                    return;
                }
                const key = String(target.value || "").trim();
                const columnIndex = columns.findIndex((column, index) => this._columnKey(column, index) === key);
                if (columnIndex < 0) {
                    return;
                }
                const column = columns[columnIndex];
                const visibleCount = this._visibleHideableColumnCount(columns);
                if (!target.checked && visibleCount <= 1) {
                    target.checked = true;
                    return;
                }
                this._setColumnHidden(column, columnIndex, !target.checked);
            });
            activeTreeViewColumnMenu = menu;
            this._positionColumnMenu(menu, event.clientX, event.clientY);
            setTimeout(() => {
                document.addEventListener("click", closeTreeViewColumnMenu, { once: true });
                document.addEventListener("keydown", (keyEvent) => {
                    if (keyEvent.key === "Escape") {
                        closeTreeViewColumnMenu();
                    }
                }, { once: true });
            }, 0);
            return true;
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
            if (this.columnVisibilityEnabled && this.headElement && !this.headElement.dataset.treeColumnMenuBound) {
                this.headElement.dataset.treeColumnMenuBound = "1";
                this.headElement.addEventListener("contextmenu", (event) => {
                    this._openColumnVisibilityMenu(event);
                });
            }
            if (this.selectionEnabled && this.headElement && !this.headElement.dataset.treeSelectionBound) {
                this.headElement.dataset.treeSelectionBound = "1";
                this.headElement.addEventListener("click", (event) => {
                    const target = event.target;
                    if (target instanceof HTMLInputElement && target.matches("[data-tree-select-all]")) {
                        event.stopPropagation();
                    }
                });
                this.headElement.addEventListener("mousedown", (event) => {
                    const target = event.target;
                    if (target instanceof HTMLInputElement && target.matches("[data-tree-select-all]")) {
                        event.stopPropagation();
                    }
                });
                this.headElement.addEventListener("change", (event) => {
                    const target = event.target;
                    if (!(target instanceof HTMLInputElement) || !target.matches("[data-tree-select-all]")) {
                        return;
                    }
                    event.stopPropagation();
                    this.setVisibleRowsSelected(target.checked);
                });
            }
            if (this.selectionEnabled && this.bodyElement && !this.bodyElement.dataset.treeSelectionBound) {
                this.bodyElement.dataset.treeSelectionBound = "1";
                this.bodyElement.addEventListener("click", (event) => {
                    const target = event.target;
                    if (target instanceof HTMLInputElement && target.matches("[data-tree-select-row]")) {
                        event.stopPropagation();
                    }
                });
                this.bodyElement.addEventListener("mousedown", (event) => {
                    const target = event.target;
                    if (target instanceof HTMLInputElement && target.matches("[data-tree-select-row]")) {
                        event.stopPropagation();
                    }
                });
                this.bodyElement.addEventListener("change", (event) => {
                    const target = event.target;
                    if (!(target instanceof HTMLInputElement) || !target.matches("[data-tree-select-row]")) {
                        return;
                    }
                    event.stopPropagation();
                    const key = String(target.value || "").trim();
                    if (!key) {
                        return;
                    }
                    if (target.checked) {
                        this.selectedRowKeys.add(key);
                    } else {
                        this.selectedRowKeys.delete(key);
                    }
                    const row = target.closest("tr");
                    if (row instanceof HTMLElement) {
                        row.classList.toggle("shared-treeview-row-selected", target.checked);
                    }
                    this._syncSelectionHeaderState();
                    this._emitSelectionChanged();
                });
            }
            if (this.onBackgroundContextMenu && this.wrapElement instanceof HTMLElement) {
                this.wrapElement.addEventListener("contextmenu", (event) => {
                    const target = event.target;
                    if (!(target instanceof Element)) {
                        return;
                    }
                    if (target.closest("thead")) {
                        return;
                    }
                    const row = target.closest("tbody tr");
                    if (row && !row.classList.contains("shared-treeview-empty")) {
                        return;
                    }
                    event.preventDefault();
                    event.stopPropagation();
                    this.onBackgroundContextMenu({
                        event,
                        x: event.clientX,
                        y: event.clientY,
                        rows: Array.isArray(this._visibleRows) ? [...this._visibleRows] : [],
                        selectedRows: this.getSelectedRows(),
                        tree: this,
                    });
                });
            }
        }

        _resolveQuery() {
            return normalizeSearchText(this.searchInput?.value || "");
        }

        _resolveRawRows() {
            const rows = this.getRows();
            return Array.isArray(rows) ? rows : [];
        }

        _renderHead(columns) {
            if (!this.renderHeadEnabled || !(this.headElement instanceof HTMLElement)) {
                this._syncSortableHeadState();
                this._applyColumnVisibilityToHead(columns);
                return;
            }
            const safeColumns = Array.isArray(columns) ? columns : [];
            const selectionHeader = this.selectionEnabled
                ? `
                    <th class="shared-treeview-select-col">
                        <input type="checkbox" data-tree-select-all aria-label="Selectionner toutes les lignes visibles">
                    </th>
                `
                : "";
            const headerMarkup = safeColumns
                .map((column) => {
                    const label = String(column?.label || "").trim();
                    const key = String(column?.key || "").trim();
                    const sortable = column?.sortable !== false && key;
                    const attrs = [];
                    const classNames = [];
                    const hidden = !this._isColumnVisible(column, safeColumns.indexOf(column));
                    if (sortable) {
                        attrs.push(`data-${this.columnAttr}="${this.escapeAttribute(key)}"`);
                        classNames.push("shared-treeview-sortable");
                    }
                    attrs.push(`data-tree-column-key="${this.escapeAttribute(this._columnKey(column, safeColumns.indexOf(column)))}"`);
                    if (hidden) {
                        attrs.push('aria-hidden="true"');
                        classNames.push("shared-treeview-col-hidden");
                    }
                    const className = String(column?.className || "").trim();
                    if (className) {
                        classNames.push(className);
                    }
                    if (classNames.length) {
                        attrs.push(`class="${this.escapeAttribute(classNames.join(" "))}"`);
                    }
                    return `<th ${attrs.join(" ")}>${this.escapeHtml(label)}</th>`;
                })
                .join("");
            this.headElement.innerHTML = `<tr>${selectionHeader}${headerMarkup}</tr>`;
            this._syncSortableHeadState();
            this._syncSelectionHeaderState();
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

        _columnCellValue(column, row, index) {
            if (typeof column?.renderCell === "function") {
                return String(column.renderCell(row, index, column) || "");
            }
            if (typeof column?.value === "function") {
                return this.escapeHtml(column.value(row, index, column));
            }
            const key = String(column?.key || "").trim();
            if (!key) {
                return "";
            }
            return this.escapeHtml(row?.[key] ?? "");
        }

        _renderCellsFromColumns(row, index, columns) {
            const safeColumns = Array.isArray(columns) ? columns : [];
            return safeColumns
                .map((column, columnIndex) => {
                    const className = String(column?.cellClassName || "").trim();
                    const hidden = !this._isColumnVisible(column, columnIndex);
                    const classNames = [];
                    if (className) {
                        classNames.push(className);
                    }
                    if (hidden) {
                        classNames.push("shared-treeview-col-hidden");
                    }
                    const attrs = [
                        `data-tree-column-key="${this.escapeAttribute(this._columnKey(column, columnIndex))}"`,
                    ];
                    if (classNames.length) {
                        attrs.push(`class="${this.escapeAttribute(classNames.join(" "))}"`);
                    }
                    if (hidden) {
                        attrs.push('aria-hidden="true"');
                    }
                    return `<td ${attrs.join(" ")}>${this._columnCellValue(column, row, index)}</td>`;
                })
                .join("");
        }

        _renderSelectionCell(row, index) {
            if (!this.selectionEnabled) {
                return "";
            }
            const rowKey = String(this.getRowKey(row, index) || `${index}`);
            const checked = this.selectedRowKeys.has(rowKey);
            return `
                <td class="shared-treeview-select-cell">
                    <input
                        type="checkbox"
                        data-tree-select-row
                        value="${this.escapeAttribute(rowKey)}"
                        aria-label="Selectionner la ligne"
                        ${checked ? "checked" : ""}
                    >
                </td>
            `;
        }

        _visibleRowKeys() {
            return (Array.isArray(this._visibleRows) ? this._visibleRows : [])
                .map((row, index) => String(this.getRowKey(row, index) || `${index}`))
                .filter(Boolean);
        }

        _syncSelectionHeaderState() {
            if (!this.selectionEnabled || !(this.headElement instanceof HTMLElement)) {
                return;
            }
            const checkbox = this.headElement.querySelector("[data-tree-select-all]");
            if (!(checkbox instanceof HTMLInputElement)) {
                return;
            }
            const visibleKeys = this._visibleRowKeys();
            const selectedCount = visibleKeys.filter((key) => this.selectedRowKeys.has(key)).length;
            checkbox.checked = visibleKeys.length > 0 && selectedCount === visibleKeys.length;
            checkbox.indeterminate = selectedCount > 0 && selectedCount < visibleKeys.length;
            checkbox.disabled = visibleKeys.length === 0;
        }

        _emitSelectionChanged() {
            if (typeof this.onSelectionChanged === "function") {
                this.onSelectionChanged({
                    selectedKeys: this.getSelectedKeys(),
                    selectedRows: this.getSelectedRows(),
                });
            }
        }

        setVisibleRowsSelected(selected) {
            const visibleKeys = this._visibleRowKeys();
            visibleKeys.forEach((key) => {
                if (selected) {
                    this.selectedRowKeys.add(key);
                } else {
                    this.selectedRowKeys.delete(key);
                }
            });
            this.render();
            this._emitSelectionChanged();
        }

        clearSelection() {
            this.selectedRowKeys.clear();
            this.render();
            this._emitSelectionChanged();
        }

        getSelectedKeys() {
            return Array.from(this.selectedRowKeys);
        }

        getSelectedRows({ visibleOnly = false } = {}) {
            const sourceRows = visibleOnly ? (this._visibleRows || []) : this._resolveRawRows();
            const selected = new Set(this.getSelectedKeys());
            return sourceRows.filter((row, index) => selected.has(String(this.getRowKey(row, index) || `${index}`)));
        }

        render() {
            const columns = this._resolveColumns();
            const visibleColumns = this._visibleColumns(columns);
            const rows = this.getVisibleRows();
            this._renderHead(columns);
            if (!(this.bodyElement instanceof HTMLElement)) {
                return rows;
            }
            if (!rows.length) {
                const colspan = Math.max(1, (visibleColumns.length || 0) + (this.selectionEnabled ? 1 : 0));
                this.bodyElement.innerHTML = `
                    <tr class="shared-treeview-empty">
                        <td class="shared-treeview-empty-cell" colspan="${colspan}">${this.escapeHtml(this.emptyMessage)}</td>
                    </tr>
                `;
                this._syncSelectionHeaderState();
                return rows;
            }
            this.bodyElement.innerHTML = rows
                .map((row, index) => {
                    const rowKey = String(this.getRowKey(row, index) || `${index}`);
                    const rowClassName = String(this.getRowClassName(row, index) || "").trim();
                    const rowClassNames = ["shared-treeview-row"];
                    if (rowClassName) {
                        rowClassNames.push(rowClassName);
                    }
                    if (this.selectionEnabled && this.selectedRowKeys.has(rowKey)) {
                        rowClassNames.push("shared-treeview-row-selected");
                    }
                    const attrs = [
                        `data-tree-row-key="${this.escapeAttribute(rowKey)}"`,
                    ];
                    attrs.push(`class="${this.escapeAttribute(rowClassNames.join(" "))}"`);
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
                    const cells = this.renderRowCells
                        ? String(this.renderRowCells(row, index, columns) || "")
                        : this._renderCellsFromColumns(row, index, columns);
                    return `<tr ${attrs.join(" ")}>${this._renderSelectionCell(row, index)}${cells}</tr>`;
                })
                .join("");
            this._applyColumnVisibilityToRenderedCells(columns);
            this._syncSelectionHeaderState();
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

    function buildTreeViewSectionMarkup(options = {}) {
        const escape = typeof options.escapeHtml === "function" ? options.escapeHtml : defaultEscape;
        const escapeAttr = typeof options.escapeAttribute === "function" ? options.escapeAttribute : escape;
        const title = String(options.title || "").trim();
        const description = String(options.description || "").trim();
        const sectionClassName = ["modal-section", "shared-treeview-section", String(options.sectionClassName || "").trim()]
            .filter(Boolean)
            .join(" ");
        const titleActionsMarkup = String(options.titleActionsMarkup || "");
        const searchId = String(options.searchId || "").trim();
        const searchPlaceholder = String(options.searchPlaceholder || "").trim();
        const searchLabel = String(options.searchLabel || "Recherche").trim() || "Recherche";
        const searchValue = String(options.searchValue || "");
        const searchInTitleRow = Boolean(options.searchInTitleRow);
        const extraToolsMarkup = String(options.extraToolsMarkup || "");
        const beforeTableMarkup = String(options.beforeTableMarkup || "");
        const afterTableMarkup = String(options.afterTableMarkup || "");
        const feedbackId = String(options.feedbackId || "").trim();
        const footerActionsMarkup = String(options.footerActionsMarkup || "");
        const tableClassName = String(options.tableClassName || "device-table inventory-table").trim() || "device-table inventory-table";
        const headId = String(options.headId || "").trim();
        const bodyId = String(options.bodyId || "").trim();
        const headMarkup = String(options.headMarkup || "");
        const bodyMarkup = String(options.bodyMarkup || "");
        const tableWrapClassName = ["table-wrap", "shared-treeview-table-wrap", String(options.tableWrapClassName || "").trim()]
            .filter(Boolean)
            .join(" ");
        const searchMarkup = searchId
            ? `
                <label class="field inline-field shared-treeview-search">
                    <span>${escape(searchLabel)}</span>
                    <input id="${escapeAttr(searchId)}" type="search" placeholder="${escapeAttr(searchPlaceholder)}" value="${escapeAttr(searchValue)}">
                </label>
            `
            : "";
        const toolsMarkup = ((!searchInTitleRow && searchMarkup) || extraToolsMarkup)
            ? `
                <div class="inventory-controls shared-treeview-tools">
                    ${searchInTitleRow ? "" : searchMarkup}
                    ${extraToolsMarkup}
                </div>
            `
            : "";
        const feedbackMarkup = feedbackId
            ? `<p id="${escapeAttr(feedbackId)}" class="muted inventory-feedback shared-treeview-feedback"></p>`
            : "";
        return `
            <section class="${escapeAttr(sectionClassName)}">
                <div class="section-head shared-treeview-title-row">
                    <h3>${escape(title)}</h3>
                    ${(titleActionsMarkup || (searchInTitleRow && searchMarkup))
        ? `<div class="inventory-row-actions shared-treeview-title-actions">${titleActionsMarkup}${searchInTitleRow ? searchMarkup : ""}</div>`
        : ""}
                </div>
                ${description ? `<p class="muted shared-treeview-description">${escape(description)}</p>` : ""}
                ${toolsMarkup}
                ${beforeTableMarkup}
                <div class="${escapeAttr(tableWrapClassName)}">
                    <table class="${escapeAttr(tableClassName)} shared-treeview-table">
                        <thead ${headId ? `id="${escapeAttr(headId)}"` : ""}>${headMarkup}</thead>
                        <tbody ${bodyId ? `id="${escapeAttr(bodyId)}"` : ""}>${bodyMarkup}</tbody>
                    </table>
                </div>
                ${afterTableMarkup}
                ${feedbackMarkup}
                ${footerActionsMarkup}
            </section>
        `;
    }

    function normalizeWebPort(rawPort) {
        const parsed = Number(rawPort || 8000);
        if (!Number.isFinite(parsed)) {
            return 8000;
        }
        return Math.max(1, Math.min(65535, Math.trunc(parsed)));
    }

    function normalizeSessionTtlMinutes(rawMinutes) {
        const parsed = Number(rawMinutes || 60);
        if (!Number.isFinite(parsed)) {
            return 60;
        }
        return Math.max(5, Math.min(1440, Math.trunc(parsed)));
    }

    function buildWebServerSettingsMarkup(options = {}) {
        const settings = options.settings || {};
        const field = typeof options.field === "function"
            ? options.field
            : (key, label, value, wide = false) => createFieldMarkup({ key, label, value, wide });
        const rawProxy = String(settings.web_server_reverse_proxy_type || "aucun").trim().toLowerCase();
        const reverseProxyType = ["aucun", "nginx", "caddy"].includes(rawProxy) ? rawProxy : "aucun";
        const sessionTtlSeconds = Number(settings.web_session_ttl_seconds || 3600);
        const sessionTtlMinutes = normalizeSessionTtlMinutes(Math.round((Number.isFinite(sessionTtlSeconds) ? sessionTtlSeconds : 3600) / 60));
        return `
    <form id="modal-webserver-form" class="modal-form">
        <div class="modal-settings-grid">
            ${field("web_server_host", "Host", settings.web_server_host || "127.0.0.1")}
            ${field("web_server_port", "Port", settings.web_server_port || 8000)}
            ${field("web_session_ttl_minutes", "Session utilisateur (minutes)", sessionTtlMinutes)}
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
        <label class="check-field">
            <input name="web_revoke_sessions_on_startup" type="checkbox" ${settings.web_revoke_sessions_on_startup !== false ? "checked" : ""}>
            <span>Invalider les sessions au demarrage d'ITops</span>
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
            web_session_ttl_seconds: normalizeSessionTtlMinutes(formData.get("web_session_ttl_minutes")) * 60,
            web_server_autostart: form?.querySelector?.('[name="web_server_autostart"]')?.checked ?? false,
            web_server_public_url: String(formData.get("web_server_public_url") || "").trim(),
            web_server_use_public_url: form?.querySelector?.('[name="web_server_use_public_url"]')?.checked ?? false,
            web_server_reverse_proxy_type: reverseProxyType,
            web_revoke_sessions_on_startup: form?.querySelector?.('[name="web_revoke_sessions_on_startup"]')?.checked ?? true,
        };
    }

    function createDashboardEditor(options = {}) {
        const scope = String(options.scope || "dashboard").trim() || "dashboard";
        const grid = options.grid instanceof HTMLElement ? options.grid : null;
        const editButton = options.editButton instanceof HTMLButtonElement ? options.editButton : null;
        const loadPreferences = typeof options.loadPreferences === "function" ? options.loadPreferences : async () => ({});
        const savePreferences = typeof options.savePreferences === "function" ? options.savePreferences : async () => {};
        const getCardId = typeof options.getCardId === "function"
            ? options.getCardId
            : (card) => String(card?.dataset?.cardId || "").trim();
        const isCardActive = typeof options.isCardActive === "function" ? options.isCardActive : () => true;
        const toggleCardActive = typeof options.toggleCardActive === "function" ? options.toggleCardActive : null;
        const onChanged = typeof options.onChanged === "function" ? options.onChanged : () => {};
        const state = {
            editing: false,
            preferences: null,
            order: [],
            hidden: [],
            draggingId: "",
        };
        let editDock = null;

        const cardId = (card) => String(getCardId(card) || "").trim();
        const cards = () => grid instanceof HTMLElement ? Array.from(grid.querySelectorAll("[data-dashboard-card-id]")) : [];

        async function loadPrefs() {
            try {
                state.preferences = await loadPreferences(scope);
            } catch (_error) {
                state.preferences = {};
            }
            state.order = Array.isArray(state.preferences?.cards_order)
                ? state.preferences.cards_order.map((item) => String(item || "").trim()).filter(Boolean)
                : [];
            state.hidden = Array.isArray(state.preferences?.hidden_cards)
                ? state.preferences.hidden_cards.map((item) => String(item || "").trim()).filter(Boolean)
                : [];
        }

        async function persistPrefs() {
            const next = {
                scope,
                cards_order: Array.from(new Set(state.order.map((item) => String(item || "").trim()).filter(Boolean))),
                hidden_cards: Array.from(new Set(state.hidden.map((item) => String(item || "").trim()).filter(Boolean))),
            };
            state.preferences = await savePreferences(next, scope) || next;
        }

        function syncOrderFromDom() {
            state.order = cards().map((card) => cardId(card)).filter(Boolean);
        }

        function applyOrder() {
            if (!(grid instanceof HTMLElement) || !state.order.length) {
                return;
            }
            const byId = new Map(cards().map((card) => [cardId(card), card]));
            state.order.forEach((id) => {
                const card = byId.get(id);
                if (card instanceof HTMLElement) {
                    grid.appendChild(card);
                }
            });
        }

        function setHidden(id, hidden) {
            const next = new Set(state.hidden);
            if (hidden) {
                next.add(id);
            } else {
                next.delete(id);
            }
            state.hidden = Array.from(next);
        }

        function renderOverlay(card) {
            const id = cardId(card);
            if (!id) {
                return;
            }
            card.querySelector(".dashboard-card-editor")?.remove();
            if (!state.editing) {
                return;
            }
            const hidden = state.hidden.includes(id);
            const active = Boolean(isCardActive(id, card));
            const overlay = document.createElement("div");
            overlay.className = "dashboard-card-editor";
            overlay.innerHTML = `
                <button class="dashboard-card-editor-btn ${hidden ? "is-muted" : "is-visible"}" type="button" data-dashboard-action="visibility" title="${hidden ? "Afficher la tuile" : "Masquer la tuile"}">&#128065;</button>
                <button class="dashboard-card-editor-btn ${active ? "is-power-on" : "is-power-off"}" type="button" data-dashboard-action="power" title="${active ? "Desactiver" : "Activer"}">&#x23FB;</button>
            `;
            card.appendChild(overlay);
        }

        function ensureEditDock() {
            if (editDock instanceof HTMLElement) {
                return editDock;
            }
            editDock = document.createElement("div");
            editDock.className = "dashboard-edit-dock";
            editDock.innerHTML = `
                <div>
                    <strong>Modification du dashboard</strong>
                    <span>Les changements sont enregistres automatiquement.</span>
                </div>
                <button class="toolbar-btn primary-btn dashboard-edit-done" type="button">Terminer</button>
            `;
            editDock.querySelector(".dashboard-edit-done")?.addEventListener("click", () => {
                setEditing(false).catch(() => {});
            });
            document.body.appendChild(editDock);
            return editDock;
        }

        function updateEditDock() {
            const dock = ensureEditDock();
            dock.hidden = !state.editing;
        }

        function decorateCards() {
            applyOrder();
            cards().forEach((card) => {
                const id = cardId(card);
                const hidden = state.hidden.includes(id);
                card.classList.toggle("dashboard-card-editing", state.editing);
                card.classList.toggle("dashboard-card-hidden", hidden);
                card.draggable = state.editing;
                card.hidden = hidden && !state.editing;
                renderOverlay(card);
            });
            updateEditDock();
        }

        async function refresh() {
            await loadPrefs();
            decorateCards();
        }

        async function setEditing(editing) {
            state.editing = Boolean(editing);
            if (editButton) {
                editButton.classList.toggle("active", state.editing);
            }
            if (state.editing) {
                await loadPrefs();
            }
            decorateCards();
        }

        async function toggleEditing() {
            await setEditing(!state.editing);
        }

        function bind() {
            if (editButton) {
                editButton.addEventListener("click", () => {
                    toggleEditing().catch(() => {});
                });
            }
            if (!(grid instanceof HTMLElement)) {
                return;
            }
            grid.addEventListener("click", async (event) => {
                if (!state.editing) {
                    return;
                }
                const target = event.target;
                if (!(target instanceof Element)) {
                    return;
                }
                const actionButton = target.closest("[data-dashboard-action]");
                if (!(actionButton instanceof HTMLButtonElement)) {
                    return;
                }
                event.preventDefault();
                event.stopPropagation();
                const card = actionButton.closest("[data-dashboard-card-id]");
                const id = card instanceof HTMLElement ? cardId(card) : "";
                if (!id) {
                    return;
                }
                const action = String(actionButton.dataset.dashboardAction || "").trim();
                if (action === "visibility") {
                    setHidden(id, !state.hidden.includes(id));
                    await persistPrefs();
                    decorateCards();
                    onChanged({ action, id });
                    return;
                }
                if (action === "power" && toggleCardActive) {
                    actionButton.disabled = true;
                    try {
                        await toggleCardActive(id, card);
                        onChanged({ action, id });
                    } finally {
                        actionButton.disabled = false;
                    }
                }
            });
            grid.addEventListener("dragstart", (event) => {
                if (!state.editing) {
                    event.preventDefault();
                    return;
                }
                const card = event.target instanceof Element ? event.target.closest("[data-dashboard-card-id]") : null;
                const id = card instanceof HTMLElement ? cardId(card) : "";
                if (!id) {
                    event.preventDefault();
                    return;
                }
                state.draggingId = id;
                card.classList.add("dashboard-card-dragging");
                event.dataTransfer?.setData("text/plain", id);
            });
            grid.addEventListener("dragover", (event) => {
                if (!state.editing || !state.draggingId) {
                    return;
                }
                const targetCard = event.target instanceof Element ? event.target.closest("[data-dashboard-card-id]") : null;
                if (!(targetCard instanceof HTMLElement) || cardId(targetCard) === state.draggingId) {
                    return;
                }
                event.preventDefault();
                const dragging = cards().find((card) => cardId(card) === state.draggingId);
                if (!(dragging instanceof HTMLElement)) {
                    return;
                }
                const rect = targetCard.getBoundingClientRect();
                const after = event.clientY > rect.top + rect.height / 2 || event.clientX > rect.left + rect.width / 2;
                grid.insertBefore(dragging, after ? targetCard.nextSibling : targetCard);
            });
            grid.addEventListener("dragend", async () => {
                cards().forEach((card) => card.classList.remove("dashboard-card-dragging"));
                if (!state.editing || !state.draggingId) {
                    state.draggingId = "";
                    return;
                }
                state.draggingId = "";
                syncOrderFromDom();
                await persistPrefs();
                decorateCards();
                onChanged({ action: "order" });
            });
        }

        bind();
        return {
            refresh,
            decorateCards,
            setEditing,
            toggleEditing,
            isEditing: () => state.editing,
        };
    }

    const LOCAL_UI_THEME_STORAGE_KEY = "nmp_ui_theme";

    function normalizeThemeKey(theme) {
        return String(theme || "").trim().toLowerCase() === "dark" ? "dark" : "light";
    }

    function getLocalUiTheme(config = null) {
        const stored = window.localStorage.getItem(LOCAL_UI_THEME_STORAGE_KEY);
        if (stored) {
            return normalizeThemeKey(stored);
        }
        return normalizeThemeKey(config?.ui_theme || "light");
    }

    function resolveLocalUiConfig(config) {
        const baseConfig = config || {};
        return {
            ...baseConfig,
            local_ui_theme: getLocalUiTheme(baseConfig),
        };
    }

    function setLocalUiTheme(theme, config = null) {
        window.localStorage.setItem(LOCAL_UI_THEME_STORAGE_KEY, normalizeThemeKey(theme));
        applyThemeConfig(resolveLocalUiConfig(config));
    }

    function toggleLocalUiTheme(config = null) {
        const current = getLocalUiTheme(config);
        const nextTheme = current === "dark" ? "light" : "dark";
        setLocalUiTheme(nextTheme, config);
        return nextTheme;
    }

    function updateThemeToggleButton(button, theme) {
        if (!(button instanceof HTMLElement)) {
            return;
        }
        const normalized = normalizeThemeKey(theme);
        const nextTheme = normalized === "dark" ? "light" : "dark";
        const icon = normalized === "dark" ? "☀" : "☾";
        const label = normalized === "dark" ? "Theme sombre actif" : "Theme clair actif";
        button.dataset.theme = normalized;
        button.innerHTML = `<span class="theme-toggle-icon" aria-hidden="true">${icon}</span>`;
        button.setAttribute("aria-label", `${label}. Basculer vers le theme ${nextTheme === "dark" ? "sombre" : "clair"}`);
        button.title = `Basculer vers le theme ${nextTheme === "dark" ? "sombre" : "clair"}`;
    }

    function createThemeToggleController(options = {}) {
        const button = options.button;
        const getTheme = typeof options.getTheme === "function" ? options.getTheme : () => document.documentElement.dataset.uiTheme;
        const onToggle = typeof options.onToggle === "function" ? options.onToggle : null;
        if (!(button instanceof HTMLElement) || !onToggle) {
            return null;
        }
        const refresh = () => updateThemeToggleButton(button, getTheme());
        button.addEventListener("click", async () => {
            const previousTheme = normalizeThemeKey(getTheme());
            const nextTheme = previousTheme === "dark" ? "light" : "dark";
            button.disabled = true;
            updateThemeToggleButton(button, nextTheme);
            try {
                await onToggle(nextTheme);
                refresh();
            } catch (_error) {
                updateThemeToggleButton(button, previousTheme);
            } finally {
                button.disabled = false;
            }
        });
        refresh();
        return { refresh };
    }

    function createProfileMenuController(options = {}) {
        const button = options.button;
        const panel = options.panel;
        const state = options.state || {};
        const closePeers = typeof options.closePeers === "function" ? options.closePeers : () => {};
        const getUiConfig = typeof options.getUiConfig === "function" ? options.getUiConfig : () => null;
        const onThemeChanged = typeof options.onThemeChanged === "function" ? options.onThemeChanged : () => {};
        const onDashboardEdit = typeof options.onDashboardEdit === "function" ? options.onDashboardEdit : null;
        const onLogout = typeof options.onLogout === "function" ? options.onLogout : null;
        const escapeHtml = typeof options.escapeHtml === "function"
            ? options.escapeHtml
            : (value) => String(value || "")
                .replaceAll("&", "&amp;")
                .replaceAll("<", "&lt;")
                .replaceAll(">", "&gt;")
                .replaceAll('"', "&quot;")
                .replaceAll("'", "&#039;");
        const createMenuButton = typeof options.createMenuButton === "function"
            ? options.createMenuButton
            : (label, action, hint = "", disabled = false) => `
                <button class="context-menu-item" type="button" data-action="${escapeHtml(action)}" ${disabled ? "disabled" : ""}>
                    <span>${escapeHtml(label)}</span>
                    <span class="context-menu-hint">${escapeHtml(hint)}</span>
                </button>
            `;

        if (!(button instanceof HTMLElement) || !(panel instanceof HTMLElement)) {
            return null;
        }

        function renderLabel() {
            const label = String(state.sessionLabel || state.sessionSubject || "-").trim() || "-";
            button.textContent = label;
        }

        function close() {
            panel.hidden = true;
            button.setAttribute("aria-expanded", "false");
        }

        function markup() {
            const accountLabel = String(state.sessionLabel || state.sessionSubject || "Utilisateur").trim() || "Utilisateur";
            const theme = getLocalUiTheme(getUiConfig());
            const themeLabel = theme === "dark" ? "Sombre" : "Clair";
            const nextThemeLabel = theme === "dark" ? "clair" : "sombre";
            const dashboardEdit = onDashboardEdit
                ? createMenuButton("Modifier le dashboard", "profile:dashboard-edit")
                : "";
            const logout = onLogout
                ? createMenuButton("Se deconnecter", "profile:logout")
                : "";
            return `
                <div class="context-menu-group">
                    <div class="context-menu-label">Compte</div>
                    <button class="context-menu-item" type="button" disabled>
                        <span>${escapeHtml(accountLabel)}</span>
                    </button>
                </div>
                <div class="context-menu-group">
                    ${createMenuButton(`Theme: ${themeLabel}`, "profile:theme-toggle", `Passer en ${nextThemeLabel}`)}
                    ${dashboardEdit}
                </div>
                ${logout ? `<div class="context-menu-group">${logout}</div>` : ""}
            `;
        }

        function open() {
            if (!panel.hidden) {
                close();
                return;
            }
            closePeers();
            panel.innerHTML = markup();
            panel.hidden = false;
            button.setAttribute("aria-expanded", "true");
            const rect = button.getBoundingClientRect();
            const panelRect = panel.getBoundingClientRect();
            panel.style.left = `${Math.max(8, Math.min(rect.right - panelRect.width, window.innerWidth - panelRect.width - 8))}px`;
            panel.style.top = `${rect.bottom + 4}px`;
        }

        button.addEventListener("click", (event) => {
            event.stopPropagation();
            open();
        });

        panel.addEventListener("click", async (event) => {
            const actionButton = event.target?.closest?.("[data-action]");
            if (!actionButton || actionButton.disabled) {
                return;
            }
            const action = String(actionButton.dataset.action || "");
            close();
            if (action === "profile:theme-toggle") {
                toggleLocalUiTheme(getUiConfig());
                onThemeChanged();
                return;
            }
            if (action === "profile:dashboard-edit" && onDashboardEdit) {
                await onDashboardEdit();
                return;
            }
            if (action === "profile:logout" && onLogout) {
                await onLogout();
            }
        });

        renderLabel();
        return {
            close,
            open,
            renderLabel,
            contains: (target) => panel.contains(target) || button.contains(target),
            isOpen: () => !panel.hidden,
        };
    }

    function applyThemeConfig(config) {
        const root = document.documentElement;
        const themeKey = normalizeThemeKey((config && (config.local_ui_theme || config.ui_theme)) || "light");
        const palettes = (config && config.theme_palettes) || {};
        const colors = palettes[themeKey] || (config && config.theme_colors) || {};
        root.dataset.uiTheme = themeKey;
        const hoverBase = colors.interaction_hover_bg || colors.control_hover_bg || colors.nav_active_bg;
        const mapped = {
            "--bg": colors.app_bg,
            "--surface": colors.surface_bg,
            "--panel": colors.panel_bg,
            "--panel-hover": colors.panel_hover_bg,
            "--text": colors.text_primary,
            "--text-secondary": colors.text_secondary,
            "--muted": colors.text_muted,
            "--line": colors.placeholder_border || colors.line_soft,
            "--accent": colors.accent_primary || colors.button_global_bg || colors.nav_active_bg,
            "--accent-strong": colors.interaction_hover_border || colors.control_hover_border || colors.button_global_bg || colors.nav_active_bg,
            "--accent-deep": colors.interaction_hover_fg || colors.control_hover_fg || colors.text_primary,
            "--interaction-hover-bg": hoverBase,
            "--interaction-hover-bg-top": colors.interaction_hover_bg_top
                || (hoverBase ? `color-mix(in srgb, ${hoverBase} 82%, white 18%)` : ""),
            "--interaction-hover-fg": colors.interaction_hover_fg || colors.control_hover_fg || colors.text_primary,
            "--interaction-hover-border": colors.interaction_hover_border || colors.control_hover_border || colors.nav_active_bg,
            "--interaction-selected-bg": colors.interaction_selected_bg || colors.tree_select_bg || colors.nav_active_bg,
            "--interaction-selected-fg": colors.interaction_selected_fg || colors.tree_fg || colors.text_primary,
            "--interaction-selected-border": colors.interaction_selected_border || colors.control_hover_border || colors.nav_active_bg,
            "--success": colors.success_bg || colors.button_active_bg,
            "--danger": "#dc2626",
            "--warning": "#d97706",
            "--control-bg": colors.control_bg || colors.button_inactive_bg,
            "--control-fg": colors.control_fg || colors.button_inactive_fg,
            "--control-border": colors.control_border || colors.placeholder_border || colors.line_soft,
            "--control-hover-bg": colors.interaction_hover_bg || colors.control_hover_bg || colors.nav_active_bg,
            "--control-hover-fg": colors.interaction_hover_fg || colors.control_hover_fg || colors.text_primary,
            "--control-hover-border": colors.interaction_hover_border || colors.control_hover_border || colors.nav_active_bg,
            "--tree-bg": colors.tree_bg,
            "--tree-fg": colors.tree_fg,
            "--tree-heading-bg": colors.tree_heading_bg,
            "--tree-heading-fg": colors.tree_heading_fg,
            "--tree-hover-bg": colors.interaction_hover_bg || colors.control_hover_bg || colors.nav_active_bg,
            "--tree-selected-bg": colors.interaction_selected_bg || colors.tree_select_bg || colors.nav_active_bg,
            "--tree-selected-border": colors.interaction_selected_border || colors.control_hover_border || colors.nav_active_bg,
        };
        Object.entries(mapped).forEach(([name, value]) => {
            if (value) {
                root.style.setProperty(name, value);
            }
        });
    }

    window.NMPSharedUi = {
        closeTopMenu,
        openTopMenu,
        applyThemeConfig,
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
            normalizeSearchText,
        },
        shell: {
            applyThemeConfig,
            createModalController,
            createTopMenuController,
        },
        theme: {
            createThemeToggleController,
            updateThemeToggleButton,
            getLocalUiTheme,
            resolveLocalUiConfig,
            setLocalUiTheme,
            toggleLocalUiTheme,
        },
        profileMenu: {
            createController: createProfileMenuController,
        },
        treeView: {
            SharedTreeView,
            buildSectionMarkup: buildTreeViewSectionMarkup,
        },
        dashboard: {
            createEditor: createDashboardEditor,
        },
    };
})();
