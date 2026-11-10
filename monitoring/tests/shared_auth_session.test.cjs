const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

function sessionHarness() {
    let now = Date.parse("2026-11-10T10:00:00Z");
    let nextId = 0;
    const timers = new Map();
    const listeners = new Map();
    const stored = new Map();
    class ClockDate extends Date {
        static now() { return now; }
    }
    const listen = (name, callback) => {
        const callbacks = listeners.get(name) || new Set();
        callbacks.add(callback);
        listeners.set(name, callbacks);
    };
    const unlisten = (name, callback) => listeners.get(name)?.delete(callback);
    const window = {
        localStorage: {
            getItem: (key) => stored.get(key) || null,
            setItem: (key, value) => stored.set(key, value),
        },
        setTimeout: (callback, delay) => {
            const id = ++nextId;
            timers.set(id, { callback, at: now + delay });
            return id;
        },
        clearTimeout: (id) => timers.delete(id),
        addEventListener: listen,
        removeEventListener: unlisten,
    };
    const document = {
        visibilityState: "visible",
        addEventListener: listen,
        removeEventListener: unlisten,
    };
    const source = fs.readFileSync(path.join(__dirname, "..", "web", "shared_auth.js"), "utf8");
    vm.runInNewContext(source, { window, document, Date: ClockDate });
    return {
        auth: window.NMPSharedAuth,
        now: () => now,
        settle: () => new Promise(setImmediate),
        dispatch: (name, event = {}) => listeners.get(name)?.forEach((callback) => callback(event)),
        otherTabActivity: () => {
            const entry = JSON.parse(stored.get("nmp_session_last_activity"));
            stored.set("nmp_session_last_activity", JSON.stringify({ ...entry, at: now }));
            listeners.get("storage")?.forEach((callback) => callback({ key: "nmp_session_last_activity" }));
        },
        advance: async (duration) => {
            const target = now + duration;
            while (true) {
                const pending = [...timers.entries()]
                    .filter(([, timer]) => timer.at <= target)
                    .sort((left, right) => left[1].at - right[1].at)[0];
                if (!pending) break;
                now = pending[1].at;
                timers.delete(pending[0]);
                pending[1].callback();
                await Promise.resolve();
                await Promise.resolve();
            }
            now = target;
        },
    };
}

test("une activité renouvelée repousse la déconnexion au-delà de l'échéance initiale", async () => {
    const clock = sessionHarness();
    const state = { token: "session", sessionExpiresAt: new Date(clock.now() + 900_000).toISOString() };
    let expired = 0;
    let idle = 0;
    let checks = 0;
    clock.auth.scheduleSessionExpiry(state, () => { expired++; }, {
        verifySession: async () => {
            checks++;
            return { expires_at: new Date(clock.now() + 900_000).toISOString() };
        },
        onIdle: () => { idle++; },
    });

    await clock.advance(60_000);
    clock.dispatch("keydown");
    await clock.settle();
    await clock.advance(840_000);

    assert.equal(checks, 1);
    assert.equal(expired, 0);
    assert.equal(idle, 0);
    assert.equal(Date.parse(state.sessionExpiresAt), Date.parse("2026-11-10T10:16:00Z"));
});

test("une session sans activité se termine après le délai prévu", async () => {
    const clock = sessionHarness();
    const state = { token: "session", sessionExpiresAt: new Date(clock.now() + 900_000).toISOString() };
    let idle = 0;
    let checks = 0;
    clock.auth.scheduleSessionExpiry(state, () => {}, {
        verifySession: async () => { checks++; return { expires_at: new Date(clock.now() + 900_000).toISOString() }; },
        onIdle: () => { idle++; },
    });

    await clock.advance(900_000);

    assert.equal(idle, 1);
    assert.equal(checks, 0);
});

test("l'activité dans un autre onglet empêche la déconnexion sur une ancienne échéance", async () => {
    const clock = sessionHarness();
    const state = { token: "session", sessionExpiresAt: new Date(clock.now() + 900_000).toISOString() };
    let expired = 0;
    let idle = 0;
    let checks = 0;
    clock.auth.scheduleSessionExpiry(state, () => { expired++; }, {
        verifySession: async () => {
            checks++;
            return { expires_at: new Date(clock.now() + 900_000).toISOString() };
        },
        onIdle: () => { idle++; },
    });

    await clock.advance(600_000);
    clock.otherTabActivity();
    await clock.advance(300_000);
    await clock.settle();

    assert.equal(checks, 1);
    assert.equal(expired, 0);
    assert.equal(idle, 0);
    assert.equal(Date.parse(state.sessionExpiresAt), Date.parse("2026-11-10T10:30:00Z"));
});

test("une erreur réseau au renouvellement conserve la session et réessaie", async () => {
    const clock = sessionHarness();
    const state = { token: "session", sessionExpiresAt: new Date(clock.now() + 900_000).toISOString() };
    let checks = 0;
    let expired = 0;
    clock.auth.scheduleSessionExpiry(state, () => { expired++; }, {
        verifySession: async () => {
            checks++;
            if (checks === 1) throw new Error("Réseau indisponible");
            return { expires_at: new Date(clock.now() + 900_000).toISOString() };
        },
    });

    await clock.advance(60_000);
    clock.dispatch("keydown");
    await clock.settle();
    await clock.advance(10_000);
    clock.dispatch("pointermove");
    await clock.settle();
    assert.equal(checks, 1);
    await clock.advance(50_001);
    await clock.settle();

    assert.equal(checks, 2);
    assert.equal(expired, 0);
    assert.equal(state.token, "session");
});

test("une requête de renouvellement bloquée ne désactive pas le délai d'inactivité", async () => {
    const clock = sessionHarness();
    const state = { token: "session", sessionExpiresAt: new Date(clock.now() + 900_000).toISOString() };
    let idle = 0;
    clock.auth.scheduleSessionExpiry(state, () => {}, {
        verifySession: () => new Promise(() => {}),
        onIdle: () => { idle++; },
    });

    await clock.advance(60_000);
    clock.dispatch("keydown");
    await clock.advance(900_000);

    assert.equal(idle, 1);
});

test("une ancienne échéance dépassée ne provoque pas de rafale de requêtes hors réseau", async () => {
    const clock = sessionHarness();
    const state = { token: "session", sessionExpiresAt: new Date(clock.now() + 900_000).toISOString() };
    let checks = 0;
    clock.auth.scheduleSessionExpiry(state, () => {}, {
        verifySession: async () => { checks++; throw new Error("Réseau indisponible"); },
    });

    await clock.advance(899_000);
    clock.dispatch("keydown");
    await clock.settle();
    await clock.advance(2_000);
    clock.dispatch("pointermove");
    await clock.settle();
    await clock.advance(10_000);

    assert.equal(checks, 1);
});

test("un refus d'authentification confirmé termine la session", async () => {
    const clock = sessionHarness();
    const state = { token: "session", sessionExpiresAt: new Date(clock.now() + 900_000).toISOString() };
    let expired = 0;
    clock.auth.scheduleSessionExpiry(state, () => { expired++; }, {
        verifySession: async () => {
            const error = new Error("Session expirée");
            error.isAuthFailure = true;
            throw error;
        },
    });

    await clock.advance(60_000);
    clock.dispatch("keydown");
    await clock.settle();

    assert.equal(expired, 1);
});

test("la restauration de secours conserve la date d'expiration du serveur", async () => {
    const clock = sessionHarness();
    const expiry = new Date(clock.now() + 900_000).toISOString();
    const context = await clock.auth.fetchSessionContext(async (endpoint) => {
        if (endpoint === "/auth/me") return { subject: "alice", expires_at: expiry };
        throw new Error("Contexte indisponible");
    });

    assert.equal(context.subject, "alice");
    assert.equal(context.expires_at, expiry);
});
