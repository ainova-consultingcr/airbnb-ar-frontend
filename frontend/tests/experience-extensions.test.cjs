const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const projectRoot = path.resolve(__dirname, "..", "..");
const registryPath = path.join(projectRoot, "frontend", "shared", "experience-extensions.js");
const registrySource = fs.readFileSync(registryPath, "utf8");

function createRegistry() {
  const errors = [];
  const context = vm.createContext({
    console: { error(...args) { errors.push(args); } }
  });
  vm.runInContext(registrySource, context, { filename: registryPath });
  return { extensions: context.AVIExperienceExtensions, errors };
}

test("ejecuta las extensiones registradas en orden", () => {
  const { extensions } = createRegistry();
  const calls = [];
  extensions.register("suggestions:after-render", "first", ({ value }) => calls.push(`first:${value}`));
  extensions.register("suggestions:after-render", "second", ({ value }) => calls.push(`second:${value}`));

  extensions.run("suggestions:after-render", { value: "ok" });

  assert.deepEqual(calls, ["first:ok", "second:ok"]);
});

test("el registro por id es idempotente y permite desregistrar", () => {
  const { extensions } = createRegistry();
  const calls = [];
  extensions.register("hook", "hospitality", () => calls.push("old"));
  const unregister = extensions.register("hook", "hospitality", () => calls.push("new"));

  assert.equal(extensions.has("hook", "hospitality"), true);
  extensions.run("hook");
  unregister();
  extensions.run("hook");

  assert.deepEqual(calls, ["new"]);
  assert.equal(extensions.has("hook", "hospitality"), false);
});

test("un error de una experiencia no bloquea las demás", () => {
  const { extensions, errors } = createRegistry();
  const calls = [];
  extensions.register("hook", "broken", () => { throw new Error("boom"); });
  extensions.register("hook", "healthy", () => calls.push("healthy"));

  extensions.run("hook");

  assert.deepEqual(calls, ["healthy"]);
  assert.equal(errors.length, 1);
});

test("chat-ui no conoce funciones específicas y Hospitality se registra como extensión", () => {
  const chatUi = fs.readFileSync(path.join(projectRoot, "frontend", "shared", "chat-ui.js"), "utf8");
  const hospitality = fs.readFileSync(path.join(projectRoot, "frontend", "experiences", "hospitality", "hospitality.js"), "utf8");
  const html = fs.readFileSync(path.join(projectRoot, "index.html"), "utf8");

  assert.doesNotMatch(chatUi, /appendServiceRequestHelpSuggestion/);
  assert.match(chatUi, /AVIExperienceExtensions\?\.run\("suggestions:after-render"/);
  assert.match(hospitality, /AVIExperienceExtensions\?\.register\(/);
  assert.ok(
    html.indexOf("frontend/shared/experience-extensions.js") < html.indexOf("frontend/shared/chat-ui.js"),
    "el registro debe cargarse antes de chat-ui"
  );
});
