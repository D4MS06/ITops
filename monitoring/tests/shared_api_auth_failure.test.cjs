const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

test("un 401 d'une autre ressource ne ferme pas la session ITops", async () => {
    let detail = "Jeton d'accès manquant.";
    let authFailures = 0;
    const window = {};
    const source = fs.readFileSync(path.join(__dirname, "..", "web", "shared_api.js"), "utf8");
    vm.runInNewContext(source, {
        window,
        fetch: async () => ({
            ok: false,
            status: 401,
            statusText: "Unauthorized",
            json: async () => ({ detail }),
        }),
    });
    const context = {
        token: "session",
        onAuthFailure: () => { authFailures++; },
    };

    await assert.rejects(window.NMPSharedApi.requestJson("/device/access", {}, context), (error) => error.isAuthFailure === false);
    assert.equal(authFailures, 0);

    detail = "Identifiants invalides.";
    await assert.rejects(window.NMPSharedApi.requestJson("/auth/login", {}, context), (error) => error.isAuthFailure === false);
    assert.equal(authFailures, 0);

    detail = "Session invalide ou expiree.";
    await assert.rejects(window.NMPSharedApi.requestJson("/devices", {}, context), (error) => error.isAuthFailure === true);
    assert.equal(authFailures, 1);

    detail = "Unauthorized";
    await assert.rejects(window.NMPSharedApi.requestJson("/auth/me", {}, context), (error) => error.isAuthFailure === true);
    assert.equal(authFailures, 2);
});
