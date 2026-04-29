(function () {
    function normalizeErrorMessage(defaultNormalize, message) {
        if (typeof defaultNormalize === "function") {
            return defaultNormalize(message);
        }
        return String(message || "").trim() || "Erreur d'import.";
    }

    function resolveFilename(disposition, fallback) {
        const raw = String(disposition || "");
        const match = raw.match(/filename=\"?([^\";]+)\"?/i);
        if (match && match[1]) {
            return String(match[1]);
        }
        return String(fallback || "export.csv");
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
            throw new Error(normalize(detail));
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
    };
})();
