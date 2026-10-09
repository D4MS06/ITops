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
        window.URL.revokeObjectURL(url);
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
    };
})();
