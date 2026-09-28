(function () {
    function normalizeText(value) {
        return String(value || "").trim();
    }

    const ROLE_PERMISSION_TEMPLATES = Object.freeze({
        administrator: Object.freeze(["read", "create", "update", "delete", "import", "export", "credentials_view", "credentials_manage", "configure"]),
        business_manager: Object.freeze(["read", "create", "update", "delete", "import", "export"]),
        technician: Object.freeze(["read", "create", "update", "credentials_view", "credentials_manage"]),
        reader: Object.freeze(["read"]),
    });

    function asArray(value) {
        return Array.isArray(value) ? value : [];
    }

    function htmlEscapeFactory(escapeHtml) {
        if (typeof escapeHtml === "function") {
            return escapeHtml;
        }
        return (raw) => String(raw || "");
    }

    function fieldMarkupFactory(createFieldMarkup, escapeHtml) {
        if (typeof createFieldMarkup === "function") {
            return createFieldMarkup;
        }
        return (key, label, value, wide = false) => `
            <label class="field ${wide ? "wide" : ""}">
                <span>${escapeHtml(label)}</span>
                <input name="${escapeHtml(key)}" value="${escapeHtml(value)}">
            </label>
        `;
    }

    function actionButtonFactory(escapeHtml) {
        const shared = window.NMPSharedUi?.formControls?.createActionButtonMarkup;
        if (typeof shared === "function") {
            return (options = {}) => shared({
                ...options,
                escapeHtml,
                escapeAttribute: escapeHtml,
            });
        }
        return (options = {}) => {
            const className = String(options.className || "toolbar-btn").trim() || "toolbar-btn";
            const type = String(options.type || "button").trim() || "button";
            const action = String(options.action || "").trim();
            const label = String(options.label || "").trim();
            return `
                <button class="${escapeHtml(className)}" type="${escapeHtml(type)}" ${action ? `data-action="${escapeHtml(action)}"` : ""}>
                    ${escapeHtml(label)}
                </button>
            `;
        };
    }

    function iconActionButtonFactory(escapeHtml) {
        const shared = window.NMPSharedUi?.formControls?.createIconActionButtonMarkup;
        if (typeof shared === "function") {
            return (options = {}) => shared({
                ...options,
                escapeHtml,
                escapeAttribute: escapeHtml,
            });
        }
        const createActionButton = actionButtonFactory(escapeHtml);
        return (options = {}) => createActionButton({
            ...options,
            className: options.danger ? "inventory-action-btn danger" : "inventory-action-btn",
            showIcon: false,
        });
    }

    function modalActionsFactory(escapeHtml) {
        const shared = window.NMPSharedUi?.formControls?.createModalActionsMarkup;
        if (typeof shared === "function") {
            return (options = {}) => shared({
                ...options,
                escapeHtml,
                escapeAttribute: escapeHtml,
            });
        }
        const createActionButton = actionButtonFactory(escapeHtml);
        return (options = {}) => {
            const buttons = Array.isArray(options.buttons) ? options.buttons : [];
            const className = ["modal-actions", String(options.className || "").trim()].filter(Boolean).join(" ");
            return `<div class="${escapeHtml(className)}">${buttons.map((button) => createActionButton(button)).join("")}</div>`;
        };
    }

    function buildRolesModalMarkup(options = {}) {
        const escapeHtml = htmlEscapeFactory(options.escapeHtml);
        const createActionButton = actionButtonFactory(escapeHtml);
        return `
            <section class="modal-section">
                <div class="section-head">
                    <h3>Roles</h3>
                    ${createActionButton({
                        preset: "add",
                        type: "button",
                        action: "admin-role-create",
                        label: "Creer role",
                    })}
                </div>
                <div class="inventory-controls">
                    <label class="modal-inline-search">
                        <span>Recherche</span>
                        <input id="modal-admin-roles-search" type="search" placeholder="Code, libelle, modules">
                    </label>
                </div>
                <div class="table-wrap">
                    <table class="device-table">
                        <thead id="admin-roles-head">
                            <tr>
                                <th data-admin-roles-col="code">Code</th>
                                <th data-admin-roles-col="label">Libelle</th>
                                <th data-admin-roles-col="modules">Modules</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="admin-roles-body"></tbody>
                    </table>
                </div>
                <p id="modal-admin-feedback" class="muted inventory-feedback"></p>
            </section>
        `;
    }

    function buildUsersModalMarkup(options = {}) {
        const escapeHtml = htmlEscapeFactory(options.escapeHtml);
        const createActionButton = actionButtonFactory(escapeHtml);
        return `
            <section class="modal-section">
                <div class="section-head">
                    <h3>Comptes applicatifs</h3>
                    ${createActionButton({
                        preset: "add",
                        type: "button",
                        action: "admin-user-create",
                        label: "Creer un compte",
                    })}
                </div>
                <div class="inventory-controls">
                    <label class="modal-inline-search">
                        <span>Recherche</span>
                        <input id="modal-admin-users-search" type="search" placeholder="Identifiant, libelle, role">
                    </label>
                </div>
                <div class="table-wrap">
                    <table class="device-table">
                        <thead id="admin-users-head">
                            <tr>
                                <th data-admin-users-col="subject">Identifiant</th>
                                <th data-admin-users-col="label">Libelle</th>
                                <th data-admin-users-col="role">Role</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="admin-users-body"></tbody>
                    </table>
                </div>
                <p id="modal-admin-feedback" class="muted inventory-feedback"></p>
            </section>
        `;
    }

    function buildRoleFormMarkup(options = {}) {
        const escapeHtml = htmlEscapeFactory(options.escapeHtml);
        const createFieldMarkup = fieldMarkupFactory(options.createFieldMarkup, escapeHtml);
        const createModalActions = modalActionsFactory(escapeHtml);
        const role = options.role || null;
        const modules = asArray(options.modules).filter((module) => normalizeText(module?.code).toLowerCase() !== "admin");
        const selected = new Set(Array.isArray(role?.module_codes) ? role.module_codes : []);
        const permissionsByModule = role?.module_permissions && typeof role.module_permissions === "object" ? role.module_permissions : {};
        const permissionColumns = [
            ["read", "Lecture"], ["create", "Creer"], ["update", "Modifier"], ["delete", "Supprimer"],
            ["import", "Importer"], ["export", "Exporter"], ["credentials_view", "Voir secrets"],
            ["credentials_manage", "Gerer secrets"], ["configure", "Configurer"],
        ];
        const templates = ROLE_PERMISSION_TEMPLATES;
        const moduleProfiles = [
            ["none", "Aucun acces", []],
            ["reader", "Lecture", templates.reader],
            ["business_manager", "Gestion", templates.business_manager],
            ["technician", "Technique", templates.technician],
            ["administrator", "Complet", templates.administrator],
        ];
        const templateCode = role?.code === "admin" ? "administrator" : "";
        const samePermissions = (left, right) => left.length === right.length && left.every((value) => right.includes(value));
        const moduleCards = modules.map((module) => {
            const active = Boolean(module?.is_active);
            const suffix = active ? "" : " (desactive)";
            const modulePermissions = new Set(Array.isArray(permissionsByModule[module.code]) ? permissionsByModule[module.code] : []);
            const hasModule = selected.has(module.code);
            const currentPermissions = Array.from(modulePermissions);
            const profile = !hasModule ? "none" : (moduleProfiles.find(([, , permissions]) => samePermissions(currentPermissions, permissions))?.[0] || "custom");
            const profileOptions = [
                ...moduleProfiles.map(([code, label]) => `<option value="${code}" ${profile === code ? "selected" : ""}>${label}</option>`),
                `<option value="custom" ${profile === "custom" ? "selected" : ""}>Personnalise</option>`,
            ].join("");
            const permissionChecks = permissionColumns.map(([code, label]) => `<label class="check-field"><input type="checkbox" name="role_permission_${escapeHtml(module.code)}" value="${escapeHtml(code)}" ${modulePermissions.has(code) ? "checked" : ""}><span>${escapeHtml(label)}</span></label>`).join("");
            return `<section class="role-module-card"><div class="role-module-summary"><div><strong>${escapeHtml(`${module.label || ""}${suffix}`)}</strong><code>${escapeHtml(module.code)}</code></div><label class="field"><span>Niveau d'acces</span><select name="role_module_profile_${escapeHtml(module.code)}">${profileOptions}</select></label></div><details class="role-module-details"><summary>Droits detailles</summary><div class="role-permission-grid">${permissionChecks}</div></details></section>`;
        }).join("");
        return `
            <form id="modal-role-form" class="modal-form" data-edit-code="${escapeHtml(role?.code || "")}" data-version-token="${escapeHtml(role?.version_token || "")}">
                <div class="modal-settings-grid">
                    ${createFieldMarkup("role_code", "Code role", role?.code || "")}
                    ${createFieldMarkup("role_label", "Libelle role", role?.label || "")}
                    <label class="field"><span>Modele global</span><select name="role_template"><option value="">Conserver les niveaux choisis</option><option value="administrator" ${templateCode === "administrator" ? "selected" : ""}>Administrateur</option><option value="business_manager">Gestionnaire metier</option><option value="technician">Technicien</option><option value="reader">Lecteur</option></select></label>
                </div>
                <section class="role-access-intro"><strong>Acces aux modules</strong><p class="muted">Choisis un niveau par module. Ouvre les droits detailles uniquement pour une exception. Les identifiants et mots de passe restent des droits separes.</p></section>
                <div class="role-module-list">${moduleCards}</div>
                ${createModalActions({
                    buttons: [
                        { preset: "back", action: "admin-back-roles" },
                        { preset: role ? "save" : "add", label: role ? "Enregistrer" : "Creer" },
                    ],
                })}
                <p id="modal-role-feedback" class="muted inventory-feedback"></p>
            </form>
        `;
    }
    function buildUserFormMarkup(options = {}) {
        const escapeHtml = htmlEscapeFactory(options.escapeHtml);
        const createFieldMarkup = fieldMarkupFactory(options.createFieldMarkup, escapeHtml);
        const createModalActions = modalActionsFactory(escapeHtml);
        const user = options.user || null;
        const roles = asArray(options.roles).map((role) => ({
            code: String(role?.code || ""),
            label: String(role?.label || ""),
        }));
        const selected = String((user?.role_codes || [])[0] || "");
        const optionsMarkup = roles
            .map((role) => `<option value="${escapeHtml(role.code)}" ${selected === role.code ? "selected" : ""}>${escapeHtml(role.label)}</option>`)
            .join("");
        const isEdit = Boolean(user && user.subject);
        const subjectField = isEdit
            ? `
                <label class="field">
                    <span>Identifiant</span>
                    <input name="user_subject" value="${escapeHtml(user?.subject || "")}" disabled aria-disabled="true">
                </label>
            `
            : createFieldMarkup("user_subject", "Identifiant", user?.subject || "");
        return `
            <form id="modal-user-form" class="modal-form" data-edit-subject="${escapeHtml(user?.subject || "")}" data-version-token="${escapeHtml(user?.version_token || "")}">
                <div class="modal-settings-grid">
                    ${subjectField}
                    ${createFieldMarkup("user_label", "Libelle", user?.label || "")}
                    ${createFieldMarkup("user_password", "Mot de passe", "")}
                    <label class="field">
                        <span>Role</span>
                        <select name="user_role_code" required>
                            <option value="">Choisir un role</option>
                            ${optionsMarkup}
                        </select>
                    </label>
                </div>
                ${createModalActions({
                    buttons: [
                        { preset: "back", action: "admin-back-users" },
                        {
                            preset: user ? "save" : "add",
                            label: user ? "Enregistrer" : "Creer",
                        },
                    ],
                })}
                <p id="modal-user-feedback" class="muted inventory-feedback"></p>
            </form>
        `;
    }

    function parseRoleForm(form) {
        const formData = new window.FormData(form);
        const templates = ROLE_PERMISSION_TEMPLATES;
        const profileInputs = Array.from(form.querySelectorAll('select[name^="role_module_profile_"]'));
        const profileByModule = Object.fromEntries(profileInputs.map((node) => [
            String(node.name || "").replace("role_module_profile_", ""),
            String(node.value || "none"),
        ]));
        const moduleCodes = Object.entries(profileByModule)
            .filter(([, profile]) => profile !== "none")
            .map(([moduleCode]) => moduleCode);
        const modulePermissions = Object.fromEntries(moduleCodes.map((moduleCode) => {
            const profile = profileByModule[moduleCode];
            const customPermissions = Array.from(form.querySelectorAll(`input[name="role_permission_${CSS.escape(moduleCode)}"]:checked`))
                .map((node) => String(node.value || ""));
            return [moduleCode, templates[profile] ? [...templates[profile]] : customPermissions];
        }));
        const template = normalizeText(formData.get("role_template"));
        if (templates[template]) {
            moduleCodes.forEach((moduleCode) => {
                modulePermissions[moduleCode] = [...templates[template]];
            });
        }
        const editCode = normalizeText(form?.dataset?.editCode).toLowerCase();
        return {
            editCode,
            payload: {
                code: normalizeText(formData.get("role_code")),
                label: normalizeText(formData.get("role_label")),
                module_codes: moduleCodes,
                module_permissions: modulePermissions,
                is_system: false,
                sort_order: 100,
                version_token: normalizeText(form?.dataset?.versionToken),
            },
        };
    }

    function syncRolePermissionProfile(form, profileInput) {
        if (!(form instanceof HTMLFormElement) || !(profileInput instanceof HTMLSelectElement)) {
            return;
        }
        const moduleCode = String(profileInput.name || "").replace("role_module_profile_", "");
        if (!moduleCode) {
            return;
        }
        const templates = {
            none: [],
            ...ROLE_PERMISSION_TEMPLATES,
        };
        const permissions = templates[String(profileInput.value || "")];
        if (!permissions) {
            return;
        }
        form.querySelectorAll(`input[name="role_permission_${CSS.escape(moduleCode)}"]`).forEach((node) => {
            node.checked = permissions.includes(String(node.value || ""));
        });
        if (profileInput.value === "custom") {
            return;
        }
        const details = profileInput.closest(".role-module-card")?.querySelector("details");
        if (details instanceof HTMLDetailsElement) {
            details.open = false;
        }
    }
    function parseUserForm(form) {
        const formData = new window.FormData(form);
        const editSubject = normalizeText(form?.dataset?.editSubject).toLowerCase();
        const selectedRole = normalizeText(formData.get("user_role_code"));
        if (!selectedRole) {
            return { error: "Selectionne un role." };
        }
        const payload = {
            subject: normalizeText(formData.get("user_subject")),
            label: normalizeText(formData.get("user_label")),
            password: String(formData.get("user_password") || ""),
            role_codes: [selectedRole],
            is_active: true,
            must_change_password: false,
            version_token: normalizeText(form?.dataset?.versionToken),
        };
        if (!editSubject && !payload.subject) {
            return { error: "Identifiant requis." };
        }
        return {
            editSubject,
            payload,
        };
    }

    window.NMPSharedAdminUi = {
        buildRolesModalMarkup,
        buildUsersModalMarkup,
        buildRoleFormMarkup,
        buildUserFormMarkup,
        parseRoleForm,
        syncRolePermissionProfile,
        parseUserForm,
    };
})();
