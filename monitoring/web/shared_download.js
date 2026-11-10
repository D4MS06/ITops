(function () {
    function resolveFilename(disposition, fallback) {
        const raw = String(disposition || "");
        const match = raw.match(/filename=\"?([^\";]+)\"?/i);
        if (match && match[1]) {
            return String(match[1]);
        }
        return String(fallback || "download.bin");
    }

    function triggerBrowserDownload(blob, filename) {
        const url = window.URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = filename;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        window.setTimeout(() => window.URL.revokeObjectURL(url), 1200);
    }

    async function chooseSaveDestination(filename) {
        if (!window.isSecureContext || typeof window.showSaveFilePicker !== "function") return null;
        return window.showSaveFilePicker({
            suggestedName: filename,
            types: [{ description: "Fichier CSV", accept: { "text/csv": [".csv"] } }],
        });
    }

    async function saveBlob(blob, filename, destination = null) {
        if (!destination) {
            triggerBrowserDownload(blob, filename);
            return filename;
        }
        const writable = await destination.createWritable();
        try {
            await writable.write(blob);
            await writable.close();
        } catch (error) {
            if (typeof writable.abort === "function") {
                try { await writable.abort(); } catch (_abortError) {}
            }
            throw error;
        }
        return destination.name || filename;
    }

    async function downloadBinary(options = {}) {
        const url = String(options.url || "").trim();
        if (!url) {
            throw new Error("URL de telechargement manquante.");
        }
        const method = String(options.method || "GET").trim() || "GET";
        const headers = options.headers || {};
        const body = options.body;
        const defaultFilename = String(options.defaultFilename || "download.bin");
        const normalizeErrorMessage = typeof options.normalizeErrorMessage === "function"
            ? options.normalizeErrorMessage
            : (message) => String(message || "");

        const response = await fetch(url, {
            method,
            headers,
            body,
        });
        if (!response.ok) {
            let detail = `${response.status} ${response.statusText}`;
            try {
                const payload = await response.json();
                detail = payload.detail || payload.message || detail;
            } catch (_error) {
            }
            throw new Error(normalizeErrorMessage(detail));
        }

        const blob = await response.blob();
        const filename = resolveFilename(response.headers.get("Content-Disposition"), defaultFilename);
        triggerBrowserDownload(blob, filename);
        return {
            filename,
            size: Number(blob?.size || 0),
        };
    }

    window.NMPSharedDownload = {
        downloadBinary,
        triggerBrowserDownload,
        chooseSaveDestination,
        saveBlob,
    };
})();
