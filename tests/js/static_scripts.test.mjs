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

function createMockElement(tag = "DIV", initial = {}) {
  const classes = new Set();
  const listeners = {};
  const children = [];
  const attributes = {};
  return {
    tagName: tag.toUpperCase(),
    value: initial.value ?? "",
    textContent: "",
    innerHTML: "",
    style: {},
    children,
    attributes,
    listeners,
    classList: {
      add: (...names) => names.forEach((n) => classes.add(n)),
      remove: (...names) => names.forEach((n) => classes.delete(n)),
      toggle: (name) => {
        if (classes.has(name)) {
          classes.delete(name);
          return false;
        }
        classes.add(name);
        return true;
      },
      contains: (name) => classes.has(name),
    },
    setAttribute(name, val) {
      attributes[name] = val;
    },
    getAttribute(name) {
      return attributes[name] ?? null;
    },
    appendChild(child) {
      children.push(child);
      return child;
    },
    insertAdjacentHTML() {},
    addEventListener(event, handler) {
      listeners[event] = handler;
    },
    reset() {},
  };
}

function findElementsByTag(root, tag) {
  const results = [];
  for (const child of root.children ?? []) {
    if (child.tagName === tag.toUpperCase()) {
      results.push(child);
    }
    results.push(...findElementsByTag(child, tag));
  }
  return results;
}

function loadDetailScript(rawPostId) {
  const detailPath = path.join(SRC_DIR, "posts/static/posts/detail.js");
  const code = fs.readFileSync(detailPath, "utf8");

  const elements = new Map([
    ["post-box", createMockElement("DIV")],
    ["extra-box", createMockElement("DIV")],
    ["alert-box", createMockElement("DIV")],
    ["back-btn", createMockElement("A")],
    ["update-btn", createMockElement("BUTTON")],
    ["delete-btn", createMockElement("BUTTON")],
    ["update-form", createMockElement("FORM")],
    ["delete-form", createMockElement("FORM")],
    ["spinner-box", createMockElement("DIV")],
    ["id_title", createMockElement("INPUT")],
    ["id_body", createMockElement("TEXTAREA")],
    ["title", createMockElement("H3")],
    ["body", createMockElement("P")],
  ]);
  if (rawPostId !== undefined) {
    elements.set("update-post-id", createMockElement("INPUT", { value: rawPostId }));
  }

  const ajaxCalls = [];
  const dropzoneConfigs = [];
  function MockDropzone(selector, config) {
    dropzoneConfigs.push({ selector, config });
    this.on = () => {};
  }
  MockDropzone.autoDiscover = true;

  const context = vm.createContext({
    console: { log() {} },
    document: {
      getElementById: (id) => elements.get(id) ?? null,
      getElementsByName: (name) =>
        name === "csrfmiddlewaretoken" ? [{ value: "test-csrf" }] : [],
      createElement: (tag) => createMockElement(tag),
    },
    $: {
      ajax: (opts) => ajaxCalls.push(opts),
    },
    Dropzone: MockDropzone,
    window: {
      location: {
        origin: "https://example.test",
        href: "https://example.test/42/",
      },
    },
    localStorage: {
      setItem() {},
      getItem() {
        return null;
      },
      clear() {},
    },
    handleAlerts() {},
  });

  new vm.Script(`"use strict";\n${code}`, {
    filename: "posts/static/posts/detail.js",
  }).runInContext(context);

  return { code, context, elements, ajaxCalls, dropzoneConfigs };
}

test("detail.js sanitizes avatar URLs and constructs relative same-origin URLs from validated postId", () => {
  const { code, context, elements, ajaxCalls, dropzoneConfigs } = loadDetailScript("42");

  assert.doesNotMatch(
    code,
    /window\.location\.href\s*\+/,
    "detail.js must not concatenate window.location.href into AJAX URLs",
  );

  // Unit-check sanitizeMediaUrl directly
  assert.equal(
    context.sanitizeMediaUrl("/media/avatars/user.png"),
    "/media/avatars/user.png",
  );
  assert.equal(
    context.sanitizeMediaUrl("/media/avatar.png"),
    "/media/avatar.png",
  );
  assert.equal(
    context.sanitizeMediaUrl("javascript:alert(1)"),
    "/media/avatar.png",
  );
  assert.equal(
    context.sanitizeMediaUrl("data:text/html,<script>alert(1)</script>"),
    "/media/avatar.png",
  );
  assert.equal(
    context.sanitizeMediaUrl("https://evil.example/a.png"),
    "/media/avatar.png",
  );
  assert.equal(
    context.sanitizeMediaUrl("/media/../../etc/passwd"),
    "/media/avatar.png",
  );
  assert.equal(context.sanitizeMediaUrl(null), "/media/avatar.png");
  assert.equal(context.sanitizeMediaUrl(""), "/media/avatar.png");

  // Initial GET request uses validated /42/data/
  assert.equal(ajaxCalls.length, 1);
  assert.equal(ajaxCalls[0].type, "GET");
  assert.equal(ajaxCalls[0].url, "/42/data/");

  // Render response with unsafe avatar URL -> sanitized to /media/avatar.png
  ajaxCalls[0].success({
    data: {
      id: 42,
      title: "Post Title",
      body: "Post Body",
      author: "alice",
      logged_in: "alice",
      author_avatar: "javascript:alert(1)",
      liked: false,
      count: 0,
    },
  });

  const extraBox = elements.get("extra-box");
  const imgsAfterUnsafe = findElementsByTag(extraBox, "IMG");
  assert.equal(imgsAfterUnsafe.length, 1);
  assert.equal(imgsAfterUnsafe[0].src, "/media/avatar.png");

  // Render response with valid avatar URL -> preserved
  ajaxCalls[0].success({
    data: {
      id: 42,
      title: "Post Title",
      body: "Post Body",
      author: "alice",
      logged_in: "alice",
      author_avatar: "/media/avatars/user.png",
      liked: false,
      count: 0,
    },
  });
  const imgsAfterValid = findElementsByTag(extraBox, "IMG");
  assert.equal(imgsAfterValid[1].src, "/media/avatars/user.png");

  // Like button posts to relative /42/like-unlike/
  const likeButtons = findElementsByTag(extraBox, "BUTTON");
  likeButtons[0].listeners.click();
  assert.equal(ajaxCalls[1].type, "POST");
  assert.equal(ajaxCalls[1].url, "/42/like-unlike/");

  // Update and delete forms post to relative /42/update/ and /42/delete/
  elements.get("update-form").listeners.submit({ preventDefault() {} });
  assert.equal(ajaxCalls[2].type, "POST");
  assert.equal(ajaxCalls[2].url, "/42/update/");

  elements.get("delete-form").listeners.submit({ preventDefault() {} });
  assert.equal(ajaxCalls[3].type, "POST");
  assert.equal(ajaxCalls[3].url, "/42/delete/");

  // Dropzone uses relative /upload/
  assert.equal(dropzoneConfigs.length, 1);
  assert.equal(dropzoneConfigs[0].config.url, "/upload/");
});

test("detail.js safely skips AJAX calls when #update-post-id is missing or invalid", () => {
  for (const invalidId of [undefined, "", "abc", "0", "-5", "42/../../evil"]) {
    const { elements, ajaxCalls } = loadDetailScript(invalidId);
    assert.equal(
      ajaxCalls.length,
      0,
      `Expected no initial AJAX call for invalid post ID: ${String(invalidId)}`,
    );
    elements.get("update-form").listeners.submit({ preventDefault() {} });
    elements.get("delete-form").listeners.submit({ preventDefault() {} });
    assert.equal(
      ajaxCalls.length,
      0,
      `Expected no form AJAX calls for invalid post ID: ${String(invalidId)}`,
    );
  }
});

test("main.js explicitly declares newPostId and runs cleanly in strict mode", () => {
  const mainPath = path.join(SRC_DIR, "posts/static/posts/main.js");
  const code = fs.readFileSync(mainPath, "utf8");

  assert.match(code, /\blet\s+newPostId\b/);

  const elements = new Map([
    ["hello-world", createMockElement("DIV")],
    ["posts-box", createMockElement("DIV")],
    ["spinner-box", createMockElement("DIV")],
    ["load-btn", createMockElement("BUTTON")],
    ["end-box", createMockElement("DIV")],
    ["post-form", createMockElement("FORM")],
    ["id_title", createMockElement("INPUT", { value: "Title" })],
    ["id_body", createMockElement("TEXTAREA", { value: "Body" })],
    ["alert-box", createMockElement("DIV")],
    ["add-btn", createMockElement("BUTTON")],
    ["my-dropzone", createMockElement("FORM")],
    ["search-input", createMockElement("INPUT")],
    ["search-btn", createMockElement("BUTTON")],
  ]);

  const ajaxCalls = [];
  const dropzoneInstances = [];
  function MockDropzone(selector, config) {
    const handlers = {};
    this.selector = selector;
    this.config = config;
    this.on = (event, fn) => {
      handlers[event] = fn;
    };
    this.handlers = handlers;
    this.removeAllFiles = () => {};
    if (typeof config?.init === "function") {
      config.init.call(this);
    }
    dropzoneInstances.push(this);
  }
  MockDropzone.autoDiscover = true;
  MockDropzone.forElement = () => dropzoneInstances[0];

  const context = vm.createContext({
    console: { log() {} },
    setTimeout: (fn) => fn(),
    document: {
      cookie: "csrftoken=abc123",
      getElementById: (id) => elements.get(id) ?? null,
      getElementsByName: (name) =>
        name === "csrfmiddlewaretoken" ? [{ value: "abc123" }] : [],
      getElementsByClassName: () => [],
    },
    $: {
      ajax: (opts) => ajaxCalls.push(opts),
    },
    Dropzone: MockDropzone,
    window: { location: { href: "https://example.test/" } },
    localStorage: {
      getItem: () => null,
      clear() {},
    },
    handleAlerts() {},
  });

  assert.doesNotThrow(() => {
    new vm.Script(`"use strict";\n${code}`, {
      filename: "posts/static/posts/main.js",
    }).runInContext(context);
  });

  // Trigger post creation and Dropzone sending to verify shared newPostId state
  elements.get("post-form").listeners.submit({ preventDefault() {} });
  const createCall = ajaxCalls.find((call) => call.type === "POST" && call.url === "");
  assert.ok(createCall, "Expected post-form submit to trigger POST AJAX");
  createCall.success({ id: 99, title: "Title", body: "Body" });

  const appended = new Map();
  dropzoneInstances[0].handlers.sending(null, null, {
    append: (key, val) => appended.set(key, val),
  });
  assert.equal(appended.get("new_post_id"), 99);
});

test("detail.html has no duplicate IDs and pairs updateModalLabel and deleteModalLabel", () => {
  const detailHtmlPath = path.join(SRC_DIR, "posts/templates/posts/detail.html");
  const html = fs.readFileSync(detailHtmlPath, "utf8");

  const idMatches = [...html.matchAll(/\bid\s*=\s*["']([^"']+)["']/g)].map(
    (m) => m[1],
  );
  assert.equal(
    new Set(idMatches).size,
    idMatches.length,
    `Duplicate id attributes found in detail.html: ${idMatches.join(", ")}`,
  );

  assert.doesNotMatch(html, /exampleModalLabel/);
  assert.match(html, /aria-labelledby="updateModalLabel"/);
  assert.match(html, /<h1[^>]*\bid="updateModalLabel"/);
  assert.match(html, /aria-labelledby="deleteModalLabel"/);
  assert.match(html, /<h1[^>]*\bid="deleteModalLabel"/);
});

test("main.html associates labels with dropzone-file-input and search-input", () => {
  const mainHtmlPath = path.join(SRC_DIR, "posts/templates/posts/main.html");
  const html = fs.readFileSync(mainHtmlPath, "utf8");

  const idMatches = [...html.matchAll(/\bid\s*=\s*["']([^"']+)["']/g)].map(
    (m) => m[1],
  );
  assert.equal(
    new Set(idMatches).size,
    idMatches.length,
    `Duplicate id attributes found in main.html: ${idMatches.join(", ")}`,
  );

  assert.match(html, /<label[^>]*\bfor="dropzone-file-input"/);
  assert.match(html, /<input[^>]*\bid="dropzone-file-input"/);
  assert.match(html, /<label[^>]*\bfor="search-input"/);
  assert.match(html, /<input[^>]*\bid="search-input"/);
});
