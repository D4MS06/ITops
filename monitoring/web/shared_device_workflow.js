(function () {
    "use strict";

    const EVENT_NAME = "nmp:device-mutated";
    const DEVICE_UPDATE_FIELDS = [
        "name", "ip", "description", "id_Teamviewer", "device_subtype",
        "action_double_click", "web_url", "ssh_user", "device_login",
    ];

    function text(value) {
        return String(value ?? "").trim();
    }

    function normalizedPayload(payload = {}) {
        const result = {
            ...payload,
            custom_data: { ...(payload?.custom_data || {}) },
        };
        if (Object.prototype.hasOwnProperty.call(result, "device_password") && !text(result.device_password)) {
            delete result.device_password;
        }
        return result;
    }

    function updatePayload(device = {}, changes = {}) {
        const result = {};
        DEVICE_UPDATE_FIELDS.forEach((field) => {
            result[field] = Object.prototype.hasOwnProperty.call(changes, field)
                ? changes[field]
                : (device[field] ?? "");
        });
        result.custom_data = {
            ...(device?.custom_data || {}),
            ...(changes?.custom_data || {}),
        };
        result.notify = Object.prototype.hasOwnProperty.call(changes, "notify")
            ? Boolean(changes.notify)
            : Boolean(device?.notify);
        result.version_token = text(changes?.version_token ?? device?.version_token);
        if (Object.prototype.hasOwnProperty.call(changes, "device_password")) {
            result.device_password = changes.device_password;
        }
        return normalizedPayload(result);
    }

    function create({ repository, eventTarget = window } = {}) {
        if (!repository || typeof repository.create !== "function" || typeof repository.save !== "function" || typeof repository.remove !== "function") {
            throw new Error("Le repository d'équipements ne respecte pas le contrat de mutation.");
        }

        function publish(kind, device, context = {}) {
            const detail = Object.freeze({ kind, device, context: { ...context } });
            if (typeof eventTarget?.dispatchEvent === "function" && typeof eventTarget?.CustomEvent === "function") {
                eventTarget.dispatchEvent(new eventTarget.CustomEvent(EVENT_NAME, { detail }));
            }
            return detail;
        }

        async function createDevice(payload, options = {}) {
            const device = await repository.create(normalizedPayload(payload), options);
            publish("device-created", device, options.context);
            return device;
        }

        async function updateDevice(deviceType, deviceId, payload, options = {}) {
            const device = await repository.save(deviceType, deviceId, normalizedPayload(payload), options);
            publish("device-updated", device, options.context);
            return device;
        }

        async function updateDeviceFields(device, changes = {}, options = {}) {
            const deviceType = text(device?.device_type || device?.type);
            const deviceId = text(device?.id);
            if (!deviceType || !deviceId) {
                throw new Error("Équipement introuvable.");
            }
            return updateDevice(deviceType, deviceId, updatePayload(device, changes), options);
        }

        async function deleteDevice(deviceType, deviceId, options = {}) {
            await repository.remove(deviceType, deviceId, options);
            publish("device-deleted", {
                device_type: text(deviceType),
                id: text(deviceId),
            }, options.context);
        }

        return Object.freeze({ createDevice, updateDevice, updateDeviceFields, deleteDevice, normalizedPayload, updatePayload });
    }

    window.NMPDeviceWorkflow = Object.freeze({ create, EVENT_NAME });
}());
