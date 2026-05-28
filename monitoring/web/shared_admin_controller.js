(function () {
    function normalizeText(value) {
        return String(value || "").trim();
    }

    function normalizeLower(value) {
        return normalizeText(value).toLowerCase();
    }

    function feedbackNode(documentRef, id) {
        if (!documentRef || typeof documentRef.getElementById !== "function") {
            return null;
        }
        const node = documentRef.getElementById(id);
        if (!(node instanceof HTMLElement)) {
            return null;
        }
        return node;
    }

    function setFeedback(documentRef, id, message) {
        const node = feedbackNode(documentRef, id);
        if (node) {
            node.textContent = String(message || "");
        }
    }

    function fallbackParseRoleForm(form) {
        const formData = new window.FormData(form);
        return {
            editCode: normalizeLower(form?.dataset?.editCode),
            payload: {
                code: normalizeText(formData.get("role_code")),
                label: normalizeText(formData.get("role_label")),
                module_codes: Array.from(form.querySelectorAll('input[name="role_modules"]:checked')).map((node) => String(node.value || "")),
                is_system: false,
                sort_order: 100,
                version_token: normalizeText(form?.dataset?.versionToken),
            },
        };
    }

    function fallbackParseUserForm(form) {
        const formData = new window.FormData(form);
        const editSubject = normalizeLower(form?.dataset?.editSubject);
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
        return { editSubject, payload };
    }

    function findRoleByCode(adminData, roleCode) {
        const rows = Array.isArray(adminData?.roles) ? adminData.roles : [];
        const wanted = normalizeLower(roleCode);
        if (!wanted) {
            return null;
        }
        return rows.find((row) => normalizeLower(row?.code) === wanted) || null;
    }

    function findUserBySubject(adminData, subject) {
        const rows = Array.isArray(adminData?.users) ? adminData.users : [];
        const wanted = normalizeLower(subject);
        if (!wanted) {
            return null;
        }
        return rows.find((row) => normalizeLower(row?.subject) === wanted) || null;
    }

    async function handleModalClick(actionButton, options = {}) {
        if (!(actionButton instanceof HTMLElement)) {
            return false;
        }
        const action = String(actionButton.dataset.action || "");
        if (!action.startsWith("admin-")) {
            return false;
        }
        const documentRef = options.documentRef || document;
        const normalizeErrorMessage = typeof options.normalizeErrorMessage === "function"
            ? options.normalizeErrorMessage
            : (value) => String(value || "");
        const confirmFn = typeof options.confirmFn === "function" ? options.confirmFn : (message) => window.confirm(message);
        const roleFormMarkup = typeof options.roleFormMarkup === "function" ? options.roleFormMarkup : () => "";
        const userFormMarkup = typeof options.userFormMarkup === "function" ? options.userFormMarkup : () => "";
        const openModal = typeof options.openModal === "function" ? options.openModal : () => {};
        const requestJson = typeof options.requestJson === "function" ? options.requestJson : null;
        const invalidateAdminData = typeof options.invalidateAdminData === "function" ? options.invalidateAdminData : () => {};
        const openRolesModal = typeof options.openRolesModal === "function" ? options.openRolesModal : async () => {};
        const openUsersModal = typeof options.openUsersModal === "function" ? options.openUsersModal : async () => {};
        const adminData = options.adminData || {};
        const resolveModalOptions = typeof options.resolveModalOptions === "function"
            ? options.resolveModalOptions
            : () => ({});

        if (action === "admin-role-create") {
            openModal("Role - Creation", roleFormMarkup(null), {
                width: "min(980px, calc(100vw - 40px))",
                ...resolveModalOptions(action),
            });
            return true;
        }
        if (action === "admin-role-edit") {
            const code = normalizeLower(actionButton.dataset.roleCode);
            const role = findRoleByCode(adminData, code);
            openModal("Role - Edition", roleFormMarkup(role), {
                width: "min(980px, calc(100vw - 40px))",
                ...resolveModalOptions(action),
            });
            return true;
        }
        if (action === "admin-role-delete") {
            if (!requestJson) {
                return true;
            }
            const code = normalizeLower(actionButton.dataset.roleCode);
            const versionToken = normalizeText(actionButton.dataset.roleVersionToken);
            if (!code) {
                return true;
            }
            if (!confirmFn(`Supprimer le role '${code}' ?`)) {
                return true;
            }
            try {
                const path = versionToken
                    ? `/admin/roles/${encodeURIComponent(code)}?version_token=${encodeURIComponent(versionToken)}`
                    : `/admin/roles/${encodeURIComponent(code)}`;
                await requestJson(path, { method: "DELETE" });
                invalidateAdminData(["roles", "users"]);
                await openRolesModal();
            } catch (error) {
                setFeedback(documentRef, "modal-admin-feedback", normalizeErrorMessage(error.message));
            }
            return true;
        }
        if (action === "admin-user-create") {
            openModal("Utilisateur - Creation", userFormMarkup(null), {
                width: "min(860px, calc(100vw - 40px))",
                ...resolveModalOptions(action),
            });
            return true;
        }
        if (action === "admin-user-edit") {
            const subject = normalizeLower(actionButton.dataset.userSubject);
            const user = findUserBySubject(adminData, subject);
            openModal("Utilisateur - Edition", userFormMarkup(user), {
                width: "min(860px, calc(100vw - 40px))",
                ...resolveModalOptions(action),
            });
            return true;
        }
        if (action === "admin-user-delete") {
            if (!requestJson) {
                return true;
            }
            const subject = normalizeLower(actionButton.dataset.userSubject);
            const versionToken = normalizeText(actionButton.dataset.userVersionToken);
            if (!subject) {
                return true;
            }
            if (!confirmFn(`Supprimer l'utilisateur '${subject}' ?`)) {
                return true;
            }
            try {
                const path = versionToken
                    ? `/admin/users/${encodeURIComponent(subject)}?version_token=${encodeURIComponent(versionToken)}`
                    : `/admin/users/${encodeURIComponent(subject)}`;
                await requestJson(path, { method: "DELETE" });
                invalidateAdminData(["users"]);
                await openUsersModal();
            } catch (error) {
                setFeedback(documentRef, "modal-admin-feedback", normalizeErrorMessage(error.message));
            }
            return true;
        }
        if (action === "admin-back-roles") {
            await openRolesModal();
            return true;
        }
        if (action === "admin-back-users") {
            await openUsersModal();
            return true;
        }
        return false;
    }

    async function handleModalSubmit(form, options = {}) {
        if (!(form instanceof HTMLFormElement)) {
            return false;
        }
        const requestJson = typeof options.requestJson === "function" ? options.requestJson : null;
        if (!requestJson) {
            return false;
        }
        const documentRef = options.documentRef || document;
        const normalizeErrorMessage = typeof options.normalizeErrorMessage === "function"
            ? options.normalizeErrorMessage
            : (value) => String(value || "");
        const invalidateAdminData = typeof options.invalidateAdminData === "function" ? options.invalidateAdminData : () => {};
        const openRolesModal = typeof options.openRolesModal === "function" ? options.openRolesModal : async () => {};
        const openUsersModal = typeof options.openUsersModal === "function" ? options.openUsersModal : async () => {};
        const parseRoleForm = typeof options.parseRoleForm === "function" ? options.parseRoleForm : fallbackParseRoleForm;
        const parseUserForm = typeof options.parseUserForm === "function" ? options.parseUserForm : fallbackParseUserForm;

        if (form.id === "modal-role-form") {
            setFeedback(documentRef, "modal-role-feedback", "");
            try {
                const parsed = parseRoleForm(form);
                const editCode = normalizeLower(parsed?.editCode);
                const payload = parsed?.payload || fallbackParseRoleForm(form).payload;
                await requestJson(editCode ? `/admin/roles/${encodeURIComponent(editCode)}` : "/admin/roles", {
                    method: editCode ? "PUT" : "POST",
                    body: JSON.stringify({
                        ...payload,
                        code: editCode || payload.code,
                    }),
                });
                invalidateAdminData(["roles", "users"]);
                await openRolesModal();
            } catch (error) {
                setFeedback(documentRef, "modal-role-feedback", normalizeErrorMessage(error.message));
            }
            return true;
        }

        if (form.id === "modal-user-form") {
            setFeedback(documentRef, "modal-user-feedback", "");
            try {
                const parsed = parseUserForm(form);
                const validationError = normalizeText(parsed?.error);
                if (validationError) {
                    setFeedback(documentRef, "modal-user-feedback", validationError);
                    return true;
                }
                const editSubject = normalizeLower(parsed?.editSubject);
                const payload = parsed?.payload || fallbackParseUserForm(form).payload;
                await requestJson(editSubject ? `/admin/users/${encodeURIComponent(editSubject)}` : "/admin/users", {
                    method: editSubject ? "PUT" : "POST",
                    body: JSON.stringify({
                        ...payload,
                        subject: editSubject || payload.subject,
                    }),
                });
                invalidateAdminData(["users"]);
                await openUsersModal();
            } catch (error) {
                setFeedback(documentRef, "modal-user-feedback", normalizeErrorMessage(error.message));
            }
            return true;
        }

        return false;
    }

    window.NMPSharedAdminController = {
        handleModalClick,
        handleModalSubmit,
    };
})();
