(function () {
    function normalizeErrorMessage(defaultNormalize, message) {
        if (typeof defaultNormalize === "function") {
            return defaultNormalize(message);
        }
        return String(message || "").trim() || "Erreur d'import.";
    }

    function normalizeImportHttpError(response, detail, normalize) {
        const status = Number(response?.status || 0);
        const rawDetail = String(detail || "").trim();
        if (status === 413) {
            return "Le fichier est trop volumineux pour etre importe.";
        }
        if (status === 422) {
            return normalize(rawDetail || "Le fichier ou le mapping contient une valeur invalide.");
        }
        if (status >= 500) {
            const suffix = rawDetail && rawDetail !== `${response.status} ${response.statusText}`
                ? ` Detail: ${normalize(rawDetail)}`
                : "";
            return `L'import a rencontre une erreur serveur. Verifie le fichier, le mapping des colonnes et reessaie.${suffix}`;
        }
        return normalize(rawDetail || `${response.status} ${response.statusText}`);
    }

    function resolveFilename(disposition, fallback) {
        const raw = String(disposition || "");
        const match = raw.match(/filename=\"?([^\";]+)\"?/i);
        if (match && match[1]) {
            return String(match[1]);
        }
        return String(fallback || "export.csv");
    }

    function escapeHtml(value) {
        return String(value || "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");
    }

    function escapeAttribute(value) {
        return escapeHtml(value).replaceAll("`", "&#96;");
    }

    async function parseErrorResponse(response) {
        let detail = `${response.status} ${response.statusText}`;
        try {
            const errorPayload = await response.json();
            detail = errorPayload?.detail || errorPayload?.message || detail;
        } catch (_error) {
        }
        return String(detail || "");
    }

    function normalizeColumnMappingRows(rows = [], options = {}) {
        const defaultTarget = String(options.defaultTarget || "__ignore__").trim() || "__ignore__";
        return (Array.isArray(rows) ? rows : [])
            .map((row) => ({
                source_column: String(row?.source_column || "").trim(),
                target_field: String(row?.target_field || defaultTarget).trim() || defaultTarget,
                custom_key: String(row?.custom_key || "").trim(),
                field_kind: String(row?.field_kind || "auto").trim() || "auto",
            }))
            .filter((row) => row.source_column);
    }

    function mappingRowsFromEffectiveMapping(headers = [], effectiveMapping = [], draftMapping = [], options = {}) {
        const defaultTarget = String(options.defaultTarget || "__ignore__").trim() || "__ignore__";
        const effectiveBySource = new Map(
            normalizeColumnMappingRows(effectiveMapping, { defaultTarget }).map((row) => [row.source_column, row]),
        );
        const draftBySource = new Map(
            normalizeColumnMappingRows(draftMapping, { defaultTarget }).map((row) => [row.source_column, row]),
        );
        return (Array.isArray(headers) ? headers : [])
            .map((header, index) => {
                const sourceColumn = String(header || `Colonne ${index + 1}`).trim();
                const mapped = draftBySource.get(sourceColumn) || effectiveBySource.get(sourceColumn) || {
                    source_column: sourceColumn,
                    target_field: defaultTarget,
                    custom_key: "",
                };
                return {
                    source_column: sourceColumn,
                    target_field: String(mapped.target_field || defaultTarget).trim() || defaultTarget,
                    custom_key: String(mapped.custom_key || "").trim(),
                    field_kind: String(mapped.field_kind || "auto").trim() || "auto",
                };
            })
            .filter((row) => row.source_column);
    }

    function normalizeTargetOptions(options = []) {
        return (Array.isArray(options) ? options : [])
            .map((option) => ({
                value: String(option?.value || "").trim(),
                label: String(option?.label || option?.value || "").trim(),
                required: Boolean(option?.required),
            }))
            .filter((option) => option.value);
    }

    function collectColumnMappings(root, options = {}) {
        const container = root && typeof root.querySelectorAll === "function" ? root : document;
        const rowSelector = String(options.rowSelector || "tr[data-source-column]");
        const targetName = String(options.targetName || "import_mapping_target");
        const customName = String(options.customName || "import_mapping_custom");
        const fieldKindName = String(options.fieldKindName || "import_mapping_field_kind");
        return Array.from(container.querySelectorAll(rowSelector))
            .map((row) => {
                const sourceColumn = String(row.getAttribute("data-source-column") || "").trim();
                const selector = row.querySelector(`select[name="${targetName}"]`);
                const customInput = row.querySelector(`input[name="${customName}"]`);
                const fieldKindSelect = row.querySelector(`select[name="${fieldKindName}"]`);
                return {
                    source_column: sourceColumn,
                    target_field: String(selector?.value || "__ignore__").trim() || "__ignore__",
                    custom_key: String(customInput?.value || "").trim(),
                    field_kind: String(fieldKindSelect?.value || "auto").trim() || "auto",
                };
            })
            .filter((row) => row.source_column);
    }

    function buildSourcePreviewTable(options = {}) {
        const headers = Array.isArray(options.headers) ? options.headers : [];
        const rows = Array.isArray(options.rows) ? options.rows : [];
        const tableClassName = String(options.tableClassName || "device-table");
        const wrapClassName = String(options.wrapClassName || "table-wrap");
        const emptyMarkup = String(options.emptyMarkup || '<p class="muted">Aucune colonne detectee.</p>');
        if (!rows.length) {
            return emptyMarkup;
        }
        const maxColumns = Math.max(
            headers.length,
            ...rows.map((row) => (Array.isArray(row) ? row.length : 0)),
            0,
        );
        const resolvedHeaders = maxColumns
            ? Array.from({ length: maxColumns }, (_value, index) => String(headers[index] || `Colonne ${index + 1}`))
            : [];
        const headCells = resolvedHeaders.map((header) => `<th>${escapeHtml(header)}</th>`).join("");
        const bodyRows = rows.map((row, index) => {
            const cells = resolvedHeaders
                .map((_header, columnIndex) => `<td>${escapeHtml(String(row?.[columnIndex] || ""))}</td>`)
                .join("");
            return `<tr><td class="muted">${index + 1}</td>${cells}</tr>`;
        }).join("");
        return `
            <div class="${escapeAttribute(wrapClassName)}">
                <table class="${escapeAttribute(tableClassName)}">
                    <thead><tr><th>#</th>${headCells}</tr></thead>
                    <tbody>${bodyRows}</tbody>
                </table>
            </div>
        `;
    }

    function buildColumnMappingRows(options = {}) {
        const headers = Array.isArray(options.headers) ? options.headers : [];
        const targetOptions = normalizeTargetOptions(options.targetOptions || []);
        const rows = mappingRowsFromEffectiveMapping(
            headers,
            options.effectiveMapping || [],
            options.draftMapping || [],
            { defaultTarget: options.defaultTarget || "__ignore__" },
        );
        const targetName = String(options.targetName || "import_mapping_target");
        const customName = String(options.customName || "import_mapping_custom");
        const customTargetValue = String(options.customTargetValue || "custom");
        const customTargetValues = new Set(
            [customTargetValue, ...(Array.isArray(options.customTargetValues) ? options.customTargetValues : [])]
                .map((value) => String(value || "").trim())
                .filter(Boolean),
        );
        const showCustomKey = Boolean(options.showCustomKey);
        return rows.map((row) => {
            const selectedTarget = String(row.target_field || "__ignore__");
            const selectedCustom = String(row.custom_key || "");
            const optionMarkup = targetOptions
                .map((option) => `<option value="${escapeAttribute(option.value)}" ${selectedTarget === option.value ? "selected" : ""}>${escapeHtml(option.label)}</option>`)
                .join("");
            return `
                <tr data-source-column="${escapeAttribute(row.source_column)}">
                    <td>${escapeHtml(row.source_column)}</td>
                    <td>
                        <select name="${escapeAttribute(targetName)}">
                            ${optionMarkup}
                        </select>
                    </td>
                    ${showCustomKey ? `
                        <td>
                            <input
                                name="${escapeAttribute(customName)}"
                                value="${escapeAttribute(selectedCustom)}"
                                placeholder="${escapeAttribute(options.customPlaceholder || "Ex: site")}"
                                ${customTargetValues.has(selectedTarget) ? "" : "disabled"}
                                style="${customTargetValues.has(selectedTarget) ? "" : "display:none;"}"
                            >
                        </td>
                    ` : ""}
                </tr>
            `;
        }).join("");
    }

    function firstNonBlankSample(rows = [], columnIndex = 0) {
        for (const row of Array.isArray(rows) ? rows : []) {
            const value = String(Array.isArray(row) ? row[columnIndex] || "" : "").trim();
            if (value) {
                return value;
            }
        }
        return "";
    }

    function importMappingSelectClass(value, ignoreValue = "__ignore__") {
        return String(value || "").trim() === String(ignoreValue || "__ignore__").trim()
            ? "is-ignored"
            : "is-mapped";
    }

    function updateMappingSelectClass(select) {
        if (!(select instanceof HTMLSelectElement)) {
            return;
        }
        const ignoreValue = String(select.getAttribute("data-ignore-value") || "__ignore__");
        select.classList.remove("is-mapped", "is-ignored");
        select.classList.add(importMappingSelectClass(select.value, ignoreValue));
        const label = select.closest(".import-mapping-select-label");
        if (label instanceof HTMLElement) {
            label.classList.remove("is-mapped", "is-ignored");
            label.classList.add(importMappingSelectClass(select.value, ignoreValue));
        }
    }

    function clampNumber(value, min, max) {
        const parsed = Number(value);
        if (!Number.isFinite(parsed)) {
            return min;
        }
        return Math.max(min, Math.min(max, Math.trunc(parsed)));
    }

    function updateIntegratedMappingPagination(root, requestedPage) {
        const container = root instanceof HTMLElement
            ? root.closest("[data-import-mapping-widget]") || root.querySelector("[data-import-mapping-widget]")
            : null;
        if (!(container instanceof HTMLElement)) {
            return false;
        }
        const totalColumns = Math.max(0, Number(container.getAttribute("data-import-mapping-total-columns") || 0));
        const columnsPerPage = Math.max(1, Number(container.getAttribute("data-import-mapping-columns-per-page") || 6));
        const totalPages = Math.max(1, Math.ceil(totalColumns / columnsPerPage));
        const currentPage = clampNumber(container.getAttribute("data-import-mapping-current-page") || 0, 0, totalPages - 1);
        const nextPage = clampNumber(requestedPage, 0, totalPages - 1);
        container.setAttribute("data-import-mapping-current-page", String(nextPage));
        const startIndex = nextPage * columnsPerPage;
        const endIndex = Math.min(startIndex + columnsPerPage, totalColumns);
        container.querySelectorAll("[data-import-mapping-column-index]").forEach((cell) => {
            const columnIndex = Number(cell.getAttribute("data-import-mapping-column-index") || 0);
            cell.classList.toggle("import-mapping-col-hidden", columnIndex < startIndex || columnIndex >= endIndex);
        });
        container.querySelectorAll("[data-import-mapping-page-indicator]").forEach((indicator) => {
            indicator.textContent = totalColumns
                ? `Colonnes ${startIndex + 1} a ${endIndex} sur ${totalColumns}`
                : "Aucune colonne";
        });
        container.querySelectorAll("[data-import-mapping-page-action='previous']").forEach((button) => {
            if (button instanceof HTMLButtonElement) {
                button.disabled = nextPage <= 0;
            }
        });
        container.querySelectorAll("[data-import-mapping-page-action='next']").forEach((button) => {
            if (button instanceof HTMLButtonElement) {
                button.disabled = nextPage >= totalPages - 1;
            }
        });
        return nextPage !== currentPage;
    }

    function handleIntegratedMappingPaginationClick(target) {
        const button = target instanceof HTMLElement ? target.closest("[data-import-mapping-page-action]") : null;
        if (!(button instanceof HTMLElement)) {
            return false;
        }
        const container = button.closest("[data-import-mapping-widget]");
        if (!(container instanceof HTMLElement)) {
            return false;
        }
        const action = String(button.getAttribute("data-import-mapping-page-action") || "");
        const currentPage = Number(container.getAttribute("data-import-mapping-current-page") || 0);
        const requestedPage = action === "previous" ? currentPage - 1 : currentPage + 1;
        updateIntegratedMappingPagination(container, requestedPage);
        return true;
    }

    function buildIntegratedMappingPreviewTable(options = {}) {
        const headers = Array.isArray(options.headers) ? options.headers : [];
        const rows = Array.isArray(options.rows) ? options.rows : [];
        const sampleRows = Array.isArray(options.sampleRows) ? options.sampleRows : rows;
        const targetOptions = normalizeTargetOptions(options.targetOptions || []);
        const mappingRows = mappingRowsFromEffectiveMapping(
            headers,
            options.effectiveMapping || [],
            options.draftMapping || [],
            { defaultTarget: options.defaultTarget || "__ignore__" },
        );
        if (!headers.length && !rows.length) {
            return '<p class="muted">Aucune colonne detectee.</p>';
        }
        const rowBySource = new Map(mappingRows.map((row) => [row.source_column, row]));
        const ignoreValue = String(options.ignoreValue || "__ignore__");
        const selectName = String(options.selectName || "import_mapping_target");
        const customName = String(options.customName || "import_mapping_custom");
        const fieldKindName = String(options.fieldKindName || "import_mapping_field_kind");
        const fieldKindOptions = Array.isArray(options.fieldKindOptions) ? options.fieldKindOptions : [];
        const customTargetValue = String(options.customTargetValue || "custom");
        const customTargetValues = new Set(
            [customTargetValue, ...(Array.isArray(options.customTargetValues) ? options.customTargetValues : [])]
                .map((value) => String(value || "").trim())
                .filter(Boolean),
        );
        const showCustomKey = Boolean(options.showCustomKey);
        const tableClassName = String(options.tableClassName || "device-table import-mapping-table");
        const wrapClassName = String(options.wrapClassName || "table-wrap import-mapping-table-wrap");
        const columnsPerPage = Math.max(1, Number(options.columnsPerPage || 6));
        const requestedPage = Math.max(0, Number(options.columnPage || 0));
        const maxColumns = Math.max(
            headers.length,
            ...rows.map((row) => (Array.isArray(row) ? row.length : 0)),
            0,
        );
        const resolvedHeaders = maxColumns
            ? Array.from({ length: maxColumns }, (_value, index) => String(headers[index] || `Colonne ${index + 1}`))
            : [];
        const totalPages = Math.max(1, Math.ceil(resolvedHeaders.length / columnsPerPage));
        const columnPage = clampNumber(requestedPage, 0, totalPages - 1);
        const visibleStart = columnPage * columnsPerPage;
        const visibleEnd = Math.min(visibleStart + columnsPerPage, resolvedHeaders.length);
        const validateRequiredTargets = options.validateRequiredTargets !== false;
        const requiredTargets = new Set(
            validateRequiredTargets
                ? targetOptions.filter((option) => option.required).map((option) => option.value)
                : [],
        );
        const mappedTargets = new Set(mappingRows.map((row) => row.target_field).filter((value) => value && value !== ignoreValue));
        const missingRequired = Array.from(requiredTargets).filter((value) => !mappedTargets.has(value));
        const targetByValue = new Map(targetOptions.map((option) => [option.value, option]));
        const headCells = resolvedHeaders.map((sourceColumn, columnIndex) => {
            const row = rowBySource.get(sourceColumn) || {
                source_column: sourceColumn,
                target_field: ignoreValue,
            };
            const selectedTarget = String(row.target_field || ignoreValue);
            const selectedCustom = String(row.custom_key || "");
            const selectedFieldKind = String(row.field_kind || "auto").trim() || "auto";
            const sample = firstNonBlankSample(sampleRows, columnIndex);
            const selectClass = importMappingSelectClass(selectedTarget, ignoreValue);
            const optionMarkup = targetOptions
                .map((option) => `<option value="${escapeAttribute(option.value)}" ${selectedTarget === option.value ? "selected" : ""}>${escapeHtml(option.label)}</option>`)
                .join("");
            const fieldKindMarkup = fieldKindOptions.length
                ? `
                    <label class="import-mapping-select-label import-mapping-field-kind-label">
                        <span>Type</span>
                        <select name="${escapeAttribute(fieldKindName)}">
                            ${fieldKindOptions.map((option) => {
                                const value = String(option?.value || "").trim();
                                const label = String(option?.label || value).trim();
                                return `<option value="${escapeAttribute(value)}" ${selectedFieldKind === value ? "selected" : ""}>${escapeHtml(label)}</option>`;
                            }).join("")}
                        </select>
                    </label>
                `
                : "";
            const hiddenClass = columnIndex < visibleStart || columnIndex >= visibleEnd ? " import-mapping-col-hidden" : "";
            return `
                <th data-source-column="${escapeAttribute(sourceColumn)}" data-import-mapping-column-index="${columnIndex}" class="${hiddenClass.trim()}">
                    <div class="import-mapping-col-title">Colonne fichier: ${escapeHtml(sourceColumn)}</div>
                    <div class="import-mapping-col-source">
                        <span>Ligne detectee</span>
                        <strong>${escapeHtml(sample || "-")}</strong>
                    </div>
                    <label class="import-mapping-select-label ${selectClass}">
                        <span>Mapper vers</span>
                        <select name="${escapeAttribute(selectName)}" class="${selectClass}" data-ignore-value="${escapeAttribute(ignoreValue)}">
                            ${optionMarkup}
                        </select>
                    </label>
                    ${showCustomKey ? `
                        <input
                            name="${escapeAttribute(customName)}"
                            value="${escapeAttribute(selectedCustom)}"
                            placeholder="${escapeAttribute(options.customPlaceholder || "Ex: site")}"
                            ${customTargetValues.has(selectedTarget) ? "" : "disabled"}
                            style="${customTargetValues.has(selectedTarget) ? "" : "display:none;"}"
                        >
                    ` : ""}
                    ${fieldKindMarkup}
                </th>
            `;
        }).join("");
        const bodyRows = rows.length
            ? rows.map((row, index) => {
                const cells = resolvedHeaders
                    .map((_header, columnIndex) => {
                        const hiddenClass = columnIndex < visibleStart || columnIndex >= visibleEnd ? " import-mapping-col-hidden" : "";
                        return `<td data-import-mapping-column-index="${columnIndex}" class="${hiddenClass.trim()}">${escapeHtml(String(row?.[columnIndex] || ""))}</td>`;
                    })
                    .join("");
                return `<tr><td class="muted">${index + 1}</td>${cells}</tr>`;
            }).join("")
            : `<tr><td colspan="${resolvedHeaders.length + 1}" class="muted">Aucune ligne de previsualisation.</td></tr>`;
        const missingLabels = missingRequired
            .map((value) => targetByValue.get(value)?.label || value)
            .filter(Boolean);
        const validationMarkup = validateRequiredTargets && targetOptions.some((option) => option.required)
            ? `
                <div class="import-mapping-status ${missingLabels.length ? "is-warning" : "is-valid"}">
                    <strong>${missingLabels.length ? "Mappage incomplet" : "Mappage pret"}</strong>
                    <span>${missingLabels.length ? `Champs a associer: ${escapeHtml(missingLabels.join(", "))}` : "Les champs obligatoires sont associes."}</span>
                </div>
            `
            : "";
        const toolbarMarkup = resolvedHeaders.length > columnsPerPage
            ? `
                <div class="import-mapping-toolbar">
                    <div class="import-mapping-toolbar-left">
                        <button type="button" class="toolbar-btn" data-import-mapping-page-action="previous" ${columnPage <= 0 ? "disabled" : ""}>Colonnes precedentes</button>
                        <span class="muted" data-import-mapping-page-indicator>Colonnes ${visibleStart + 1} a ${visibleEnd} sur ${resolvedHeaders.length}</span>
                        <button type="button" class="toolbar-btn" data-import-mapping-page-action="next" ${columnPage >= totalPages - 1 ? "disabled" : ""}>Colonnes suivantes</button>
                    </div>
                    <div class="import-mapping-toolbar-right">
                        <span class="muted">Toutes les associations restent conservees en changeant de page.</span>
                    </div>
                </div>
            `
            : "";
        return `
            <div
                data-import-mapping-widget
                data-import-mapping-total-columns="${resolvedHeaders.length}"
                data-import-mapping-columns-per-page="${columnsPerPage}"
                data-import-mapping-current-page="${columnPage}"
            >
                ${validationMarkup}
                ${toolbarMarkup}
                <div class="${escapeAttribute(wrapClassName)}">
                    <table class="${escapeAttribute(tableClassName)}">
                        <thead><tr><th>#</th>${headCells}</tr></thead>
                        <tbody>${bodyRows}</tbody>
                </table>
                </div>
            </div>
        `;
    }

    function pickFile(options = {}) {
        const accept = String(options.accept || ".xlsx,.csv,.txt,.tsv").trim() || ".xlsx,.csv,.txt,.tsv";
        const input = document.createElement("input");
        input.type = "file";
        input.accept = accept;
        return new Promise((resolve) => {
            input.addEventListener(
                "change",
                () => resolve(input.files && input.files[0] ? input.files[0] : null),
                { once: true },
            );
            input.click();
        });
    }

    function readAsBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new window.FileReader();
            reader.onload = () => {
                const result = String(reader.result || "");
                const marker = "base64,";
                const markerIndex = result.indexOf(marker);
                if (markerIndex < 0) {
                    reject(new Error("Encodage fichier impossible."));
                    return;
                }
                resolve(result.slice(markerIndex + marker.length));
            };
            reader.onerror = () => reject(new Error("Lecture fichier impossible."));
            reader.readAsDataURL(file);
        });
    }

    async function postImport(options = {}) {
        const file = options.file;
        if (!file) {
            throw new Error("Aucun fichier selectionne.");
        }
        const candidatePaths = Array.isArray(options.candidatePaths) ? options.candidatePaths.filter(Boolean) : [];
        if (!candidatePaths.length) {
            throw new Error("Aucun endpoint d'import configure.");
        }
        const headersFactory = typeof options.headersFactory === "function" ? options.headersFactory : () => ({});
        const normalize = (message) => normalizeErrorMessage(options.normalizeErrorMessage, message);
        const mapper = typeof options.responseMapper === "function" ? options.responseMapper : (payload) => payload;
        const contentBase64 = await readAsBase64(file);
        const requestBodyBuilder = typeof options.requestBodyBuilder === "function"
            ? options.requestBodyBuilder
            : (ctx) => ({
                filename: String(ctx.file?.name || ""),
                content_base64: String(ctx.contentBase64 || ""),
            });
        const body = JSON.stringify(
            requestBodyBuilder({
                file,
                contentBase64,
            }),
        );
        let payload = null;
        let lastErrorMessage = "";
        for (const path of candidatePaths) {
            const response = await fetch(path, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    ...headersFactory(),
                },
                body,
            });
            if (response.ok) {
                payload = await response.json();
                break;
            }
            let detail = `${response.status} ${response.statusText}`;
            try {
                const errorPayload = await response.json();
                detail = errorPayload?.detail || errorPayload?.message || detail;
            } catch (_error) {
            }
            if (response.status === 404 || response.status === 405) {
                lastErrorMessage = String(detail || "");
                continue;
            }
            throw new Error(normalizeImportHttpError(response, detail, normalize));
        }
        if (!payload) {
            const fallbackMessage = lastErrorMessage || "Import indisponible sur ce serveur.";
            throw new Error(
                `${normalize(fallbackMessage)} Verifiez que le serveur a bien ete redemarre apres la mise a jour.`,
            );
        }
        return mapper(payload);
    }

    async function downloadExport(options = {}) {
        const candidatePaths = Array.isArray(options.candidatePaths) ? options.candidatePaths.filter(Boolean) : [];
        if (!candidatePaths.length) {
            throw new Error("Aucun endpoint d'export configure.");
        }
        const method = String(options.method || "GET").trim() || "GET";
        const headersFactory = typeof options.headersFactory === "function" ? options.headersFactory : () => ({});
        const normalize = (message) => normalizeErrorMessage(options.normalizeErrorMessage, message);
        const defaultFilename = String(options.defaultFilename || "export.csv");
        const body = options.body;
        let lastErrorMessage = "";
        for (const path of candidatePaths) {
            const response = await fetch(path, {
                method,
                headers: {
                    ...headersFactory(),
                },
                body,
            });
            if (response.ok) {
                const blob = await response.blob();
                const filename = resolveFilename(response.headers.get("Content-Disposition"), defaultFilename);
                const sharedDownload = window.NMPSharedDownload?.triggerBrowserDownload;
                if (typeof sharedDownload === "function") {
                    sharedDownload(blob, filename);
                } else {
                    const url = window.URL.createObjectURL(blob);
                    const anchor = document.createElement("a");
                    anchor.href = url;
                    anchor.download = filename;
                    document.body.appendChild(anchor);
                    anchor.click();
                    anchor.remove();
                    window.URL.revokeObjectURL(url);
                }
                return {
                    filename,
                    size: Number(blob?.size || 0),
                    path,
                };
            }
            const detail = await parseErrorResponse(response);
            if (response.status === 404 || response.status === 405) {
                lastErrorMessage = detail;
                continue;
            }
            throw new Error(normalize(detail));
        }
        const fallbackMessage = lastErrorMessage || "Export indisponible sur ce serveur.";
        throw new Error(
            `${normalize(fallbackMessage)} Verifiez que le serveur a bien ete redemarre apres la mise a jour.`,
        );
    }

    window.NMPSharedImport = {
        pickFile,
        readAsBase64,
        postImport,
        downloadExport,
        normalizeColumnMappingRows,
        mappingRowsFromEffectiveMapping,
        collectColumnMappings,
        buildSourcePreviewTable,
        buildColumnMappingRows,
        buildIntegratedMappingPreviewTable,
        updateMappingSelectClass,
        updateIntegratedMappingPagination,
        handleIntegratedMappingPaginationClick,
    };
})();
