(function registerDeviceConfigFiles(global) {
    "use strict";

    async function pickFile() {
        const picker = global.NMPSharedImport?.pickFile;
        if (typeof picker === "function") {
            return picker({ accept: ".cfg,.conf,.txt,*/*" });
        }
        const input = document.createElement("input");
        input.type = "file";
        input.accept = ".cfg,.conf,.txt,*/*";
        return new Promise((resolve) => {
            input.addEventListener("change", () => resolve(input.files?.[0] || null), { once: true });
            input.click();
        });
    }

    async function readAsBase64(file) {
        const reader = global.NMPSharedImport?.readAsBase64;
        if (typeof reader !== "function") {
            throw new Error("Le lecteur de fichiers partagé est indisponible.");
        }
        return String(await reader(file));
    }

    async function importFile(options = {}) {
        const device = options.device;
        const requestJson = options.requestJson;
        const file = options.file;
        if (!device?.device_type || !device?.id) {
            throw new Error("Équipement introuvable.");
        }
        if (!file) {
            return false;
        }
        if (typeof requestJson !== "function") {
            throw new Error("Client API indisponible.");
        }
        await requestJson("/config-files/import", {
            method: "POST",
            body: JSON.stringify({
                device_type: String(device.device_type),
                device_id: String(device.id),
                device_name: String(device.name || ""),
                device_ip: String(device.ip || ""),
                filename: String(file.name || "import.cfg"),
                content_base64: await readAsBase64(file),
                detail: String(options.detail || "Import web"),
            }),
        });
        return true;
    }

    async function importFromPicker(options = {}) {
        const file = await pickFile();
        return importFile({ ...options, file });
    }

    global.NMPDeviceConfigFiles = Object.freeze({ importFile, importFromPicker });
})(window);
