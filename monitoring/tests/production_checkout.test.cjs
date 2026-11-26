const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { execFileSync } = require("node:child_process");
const test = require("node:test");

const project = path.resolve(__dirname, "../..");
const bash = process.platform === "win32" ? "C:/Program Files/Git/bin/bash.exe" : "bash";

function runGit(directory, ...args) {
    return execFileSync("git", ["-C", directory, ...args], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
}

function write(directory, relative, text) {
    const destination = path.join(directory, relative);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.writeFileSync(destination, text);
}

function commit(directory, message) {
    runGit(directory, "add", ".");
    runGit(directory, "-c", "user.name=ITops Test", "-c", "user.email=test@example.invalid", "commit", "-m", message);
}

function fixture(t) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "itops-production-test-"));
    t.after(() => {
        const resolved = path.resolve(root);
        assert.ok(resolved.startsWith(path.resolve(os.tmpdir()) + path.sep));
        assert.ok(path.basename(resolved).startsWith("itops-production-test-"));
        fs.rmSync(resolved, { recursive: true, force: true });
    });
    const source = path.join(root, "source");
    fs.mkdirSync(source);
    runGit(source, "init", "-b", "main");
    runGit(source, "config", "core.autocrlf", "false");
    const files = {
        ".gitattributes": "scripts/linux/*.sh text eol=lf\n",
        ".gitignore": ".venv/\n",
        "__init__.py": "",
        "main.py": "# application\n",
        "requirements.txt": "",
        "requirements-dev.txt": "pytest\n",
        "monitoring/api/app.py": "# runtime\n",
        "monitoring/web/portal.html": "<html></html>\n",
        "monitoring/tests/test_hidden.py": "# development\n",
        "tests/test_hidden.py": "# development\n",
        "docs/recette.md": "Documentation\n",
        "scripts/local_dev_env.ps1": "# development\n",
        "scripts/linux/itops_storage_helper.py": "# runtime\n",
        "deployment/sql/migration.sql": "SELECT 1;\n",
    };
    for (const [relative, text] of Object.entries(files)) write(source, relative, text);
    for (const name of ["production_checkout.sh", "production.sparse-checkout"]) {
        write(source, "scripts/linux/" + name, fs.readFileSync(path.join(project, "scripts/linux", name), "utf8"));
    }
    commit(source, "Initial");
    return { root, source };
}

test("le clone de production et les prochains pulls excluent les fichiers de développement", (t) => {
    const { root, source } = fixture(t);
    const server = path.join(root, "server");
    runGit(root, "clone", "--sparse", "--branch", "main", source, server);
    execFileSync(bash, ["-c",
        'PRODUCTION_CHECKOUT="$(git show HEAD:scripts/linux/production_checkout.sh)" && bash -s -- . <<< "$PRODUCTION_CHECKOUT"',
    ], { cwd: server });
    assert.equal(fs.existsSync(path.join(server, "monitoring/api/app.py")), true);
    assert.equal(fs.existsSync(path.join(server, "monitoring/web/portal.html")), true);
    assert.equal(fs.existsSync(path.join(server, "scripts/linux/itops_storage_helper.py")), true);
    assert.equal(fs.existsSync(path.join(server, "deployment/sql/migration.sql")), true);
    for (const relative of ["monitoring/tests", "tests", "docs", "requirements-dev.txt", "scripts/local_dev_env.ps1"]) {
        assert.equal(fs.existsSync(path.join(server, relative)), false, relative);
    }
    write(source, "monitoring/api/new.py", "# new runtime\n");
    write(source, "monitoring/tests/test_new.py", "# new test\n");
    commit(source, "Update");
    runGit(server, "pull", "--ff-only", "origin", "main");
    assert.equal(fs.existsSync(path.join(server, "monitoring/api/new.py")), true);
    assert.equal(fs.existsSync(path.join(server, "monitoring/tests/test_new.py")), false);
    assert.equal(runGit(server, "status", "--porcelain").trim(), "");
});

test("l'activation sur une installation existante préserve les données locales et refuse un code modifié", (t) => {
    const { source } = fixture(t);
    write(source, ".venv/local.txt", "local environment");
    write(source, "main.py", "# local modification\n");
    assert.throws(() => execFileSync(bash, ["scripts/linux/production_checkout.sh", "."], {
        cwd: source, stdio: ["ignore", "pipe", "pipe"],
    }));
    assert.equal(fs.existsSync(path.join(source, "monitoring/tests/test_hidden.py")), true);
    write(source, "main.py", "# application\n");
    execFileSync(bash, ["scripts/linux/production_checkout.sh", "."], { cwd: source });
    assert.equal(fs.existsSync(path.join(source, "monitoring/tests/test_hidden.py")), false);
    assert.equal(fs.readFileSync(path.join(source, ".venv/local.txt"), "utf8"), "local environment");
    execFileSync(bash, ["scripts/linux/production_checkout.sh", "."], { cwd: source });
    assert.equal(runGit(source, "status", "--porcelain").trim(), "");
    runGit(source, "sparse-checkout", "disable");
    assert.equal(fs.existsSync(path.join(source, "monitoring/tests/test_hidden.py")), true);
    assert.equal(fs.readFileSync(path.join(source, ".venv/local.txt"), "utf8"), "local environment");
});
