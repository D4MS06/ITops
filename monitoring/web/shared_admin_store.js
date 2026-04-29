(function () {
    function createAdminStore(options = {}) {
        const requestJson = typeof options.requestJson === "function" ? options.requestJson : null;
        const data = {
            modules: [],
            roles: [],
            users: [],
            services: [],
            sharedLists: [],
        };
        const loaded = {
            modules: false,
            roles: false,
            users: false,
            services: false,
            sharedLists: false,
        };

        function invalidate(parts = []) {
            const normalized = Array.isArray(parts) && parts.length ? parts : ["modules", "roles", "users", "services", "sharedLists"];
            normalized.forEach((part) => {
                if (part === "modules") {
                    data.modules = [];
                    loaded.modules = false;
                }
                if (part === "roles") {
                    data.roles = [];
                    loaded.roles = false;
                }
                if (part === "users") {
                    data.users = [];
                    loaded.users = false;
                }
                if (part === "services") {
                    data.services = [];
                    loaded.services = false;
                }
                if (part === "sharedLists") {
                    data.sharedLists = [];
                    loaded.sharedLists = false;
                }
            });
        }

        async function load(options = {}) {
            if (!requestJson) {
                return;
            }
            const includeModules = options.includeModules !== false;
            const includeRoles = options.includeRoles !== false;
            const includeUsers = options.includeUsers !== false;
            const includeServices = Boolean(options.includeServices);
            const includeSharedLists = Boolean(options.includeSharedLists);
            const forceRefresh = Boolean(options.forceRefresh);
            const tasks = [];
            if (includeModules && (forceRefresh || !loaded.modules)) {
                tasks.push(
                    requestJson("/admin/modules").then((rows) => {
                        data.modules = Array.isArray(rows) ? rows : [];
                        loaded.modules = true;
                    }),
                );
            }
            if (includeRoles && (forceRefresh || !loaded.roles)) {
                tasks.push(
                    requestJson("/admin/roles").then((rows) => {
                        data.roles = Array.isArray(rows) ? rows : [];
                        loaded.roles = true;
                    }),
                );
            }
            if (includeUsers && (forceRefresh || !loaded.users)) {
                tasks.push(
                    requestJson("/admin/users").then((rows) => {
                        data.users = Array.isArray(rows) ? rows : [];
                        loaded.users = true;
                    }),
                );
            }
            if (includeServices && (forceRefresh || !loaded.services)) {
                tasks.push(
                    requestJson("/admin/custom-services").then((rows) => {
                        data.services = Array.isArray(rows) ? rows : [];
                        loaded.services = true;
                    }),
                );
            }
            if (includeSharedLists && (forceRefresh || !loaded.sharedLists)) {
                tasks.push(
                    requestJson("/admin/shared-lists").then((rows) => {
                        data.sharedLists = Array.isArray(rows) ? rows : [];
                        loaded.sharedLists = true;
                    }),
                );
            }
            if (tasks.length) {
                await Promise.all(tasks);
            }
        }

        return {
            data,
            loaded,
            invalidate,
            load,
        };
    }

    window.NMPSharedAdminStore = {
        createAdminStore,
    };
})();
