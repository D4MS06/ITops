(function () {
    "use strict";

    function deviceKey(deviceType, deviceId) {
        return `${String(deviceType || "").trim().toLowerCase()}:${String(deviceId || "").trim()}`;
    }

    function create({ requestJson }) {
        if (typeof requestJson !== "function") {
            throw new Error("Le client API device est requis.");
        }

        const devices = new Map();
        const schemas = new Map();
        const schemaLoads = new Map();
        const runtimeStatuses = new Map();

        function getByKey(key) {
            const [deviceType, ...idParts] = String(key || "").split(":");
            return devices.get(deviceKey(deviceType, idParts.join(":"))) || null;
        }

        function remember(device) {
            const key = deviceKey(device?.device_type || device?.type, device?.id);
            if (key !== ":") {
                const runtimeStatus = runtimeStatuses.get(key);
                const next = runtimeStatus ? { ...device, status: runtimeStatus } : device;
                devices.set(key, next);
                return next;
            }
            return device;
        }

        function replaceDevices(rows) {
            devices.clear();
            (Array.isArray(rows) ? rows : []).forEach(remember);
            return Array.from(devices.values());
        }

        function setSchema(deviceType, schema) {
            const typeCode = String(deviceType || "").trim().toLowerCase();
            if (!typeCode) {
                throw new Error("Type d'équipement manquant.");
            }
            schemas.set(typeCode, schema || {});
            return schemas.get(typeCode);
        }

        function updateRuntime(deviceType, deviceId, runtime = {}) {
            const key = deviceKey(deviceType, deviceId);
            if (!Object.prototype.hasOwnProperty.call(runtime, "status")) {
                return devices.get(key) || null;
            }
            const nextStatus = String(runtime.status || "").trim() || "idle";
            runtimeStatuses.set(key, nextStatus);
            const current = devices.get(key);
            if (!current) {
                return current || null;
            }
            if (String(current.status || "") === nextStatus) {
                return current;
            }
            const next = { ...current, status: nextStatus };
            devices.set(key, next);
            return next;
        }

        function syncRuntimeSnapshot(snapshot) {
            let changed = 0;
            Object.entries(snapshot?.devices || {}).forEach(([typeCode, rows]) => {
                (Array.isArray(rows) ? rows : []).forEach((row) => {
                    const before = devices.get(deviceKey(typeCode, row?.id)) || null;
                    const after = updateRuntime(typeCode, row?.id, row || {});
                    if (after && after !== before) {
                        changed += 1;
                    }
                });
            });
            return changed;
        }

        async function loadAll(options = {}) {
            const rows = await requestJson("/devices", options);
            return replaceDevices(rows);
        }

        async function load(deviceType, deviceId, options = {}) {
            const key = deviceKey(deviceType, deviceId);
            const row = await requestJson(`/devices/${encodeURIComponent(String(deviceType || ""))}/${encodeURIComponent(String(deviceId || ""))}`, options);
            devices.set(key, row);
            return row;
        }

        async function loadSchema(deviceType, { force = false, requestOptions = {} } = {}) {
            const typeCode = String(deviceType || "").trim().toLowerCase();
            if (!typeCode) {
                throw new Error("Type d'équipement manquant.");
            }
            if (!force && schemas.has(typeCode)) {
                return schemas.get(typeCode);
            }
            if (!force && schemaLoads.has(typeCode)) {
                return schemaLoads.get(typeCode);
            }
            const loading = requestJson(`/device-types/${encodeURIComponent(typeCode)}/schema`, requestOptions)
                .then((schema) => {
                    return setSchema(typeCode, schema);
                })
                .finally(() => schemaLoads.delete(typeCode));
            schemaLoads.set(typeCode, loading);
            return loading;
        }

        async function save(deviceType, deviceId, payload, options = {}) {
            const row = await requestJson(
                `/devices/${encodeURIComponent(String(deviceType || ""))}/${encodeURIComponent(String(deviceId || ""))}`,
                { method: "PUT", body: JSON.stringify(payload), ...options },
            );
            return remember(row);
        }

        async function create(payload, options = {}) {
            const row = await requestJson("/devices", {
                method: "POST",
                body: JSON.stringify(payload),
                ...options,
            });
            return remember(row);
        }

        async function remove(deviceType, deviceId, { versionToken = "", requestOptions = {} } = {}) {
            const query = String(versionToken || "").trim()
                ? `?version_token=${encodeURIComponent(String(versionToken).trim())}`
                : "";
            await requestJson(
                `/devices/${encodeURIComponent(String(deviceType || ""))}/${encodeURIComponent(String(deviceId || ""))}${query}`,
                { method: "DELETE", ...requestOptions },
            );
            devices.delete(deviceKey(deviceType, deviceId));
            runtimeStatuses.delete(deviceKey(deviceType, deviceId));
        }

        return Object.freeze({
            deviceKey,
            get: (deviceType, deviceId) => devices.get(deviceKey(deviceType, deviceId)) || null,
            getByKey,
            values: () => Array.from(devices.values()),
            replaceDevices,
            updateRuntime,
            syncRuntimeSnapshot,
            getSchema: (deviceType) => schemas.get(String(deviceType || "").trim().toLowerCase()) || null,
            setSchema,
            schemaCodes: () => Array.from(schemas.keys()),
            loadAll,
            load,
            loadSchema,
            save,
            create,
            remove,
            invalidateSchema: (deviceType) => schemas.delete(String(deviceType || "").trim().toLowerCase()),
            clearSchemas: () => {
                schemas.clear();
                schemaLoads.clear();
            },
            clear: () => {
                devices.clear();
                schemas.clear();
                schemaLoads.clear();
                runtimeStatuses.clear();
            },
        });
    }

    window.NMPDeviceRepository = Object.freeze({ create, deviceKey });
}());
