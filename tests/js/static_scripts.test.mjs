import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";

const ROOT_DIR = path.resolve(import.meta.dirname, "../..");
const SRC_DIR = path.join(ROOT_DIR, "dj_ajax", "src");

const JS_FILES = [
  "static/functions.js",
  "posts/static/posts/main.js",
  "posts/static/posts/detail.js",
  "profiles/static/profiles/main.js",
];

const CONFLICT_REGEX = new RegExp(
  `^(${"<".repeat(7)}|${"=".repeat(7)}|${">".repeat(7)})(\\s|$)`,
  "m",
);

test("all Django static JS files parse cleanly and contain no merge-conflict markers", () => {
  for (const relPath of JS_FILES) {
    const fullPath = path.join(SRC_DIR, relPath);
    assert.ok(fs.existsSync(fullPath), `Missing expected JS file: ${relPath}`);
    const code = fs.readFileSync(fullPath, "utf8");
    assert.doesNotMatch(
      code,
      CONFLICT_REGEX,
      `Merge conflict marker detected in ${relPath}`,
    );
    assert.doesNotThrow(
      () => new vm.Script(code, { filename: relPath }),
      `JavaScript syntax error in ${relPath}`,
    );
  }
});

test("handleAlerts renders success and danger alert markup into alertBox", () => {
  const functionsPath = path.join(SRC_DIR, "static/functions.js");
  const code = fs.readFileSync(functionsPath, "utf8");

  const alertBox = { innerHTML: "" };
  const context = vm.createContext({ alertBox });
  new vm.Script(code, { filename: "static/functions.js" }).runInContext(
    context,
  );

  vm.runInContext("handleAlerts('success', 'Post updated')", context);
  assert.match(alertBox.innerHTML, /class="alert alert-success"/);
  assert.match(alertBox.innerHTML, /role="alert"/);
  assert.match(alertBox.innerHTML, /Post updated/);

  vm.runInContext("handleAlerts('danger', 'Post deleted')", context);
  assert.match(alertBox.innerHTML, /class="alert alert-danger"/);
  assert.match(alertBox.innerHTML, /Post deleted/);
  assert.doesNotMatch(alertBox.innerHTML, /alert-success/);
});
