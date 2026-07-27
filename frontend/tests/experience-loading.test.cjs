const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const projectRoot = path.resolve(__dirname, "..", "..");
const loaderPath = path.join(
  projectRoot,
  "frontend",
  "shared",
  "experience-views.js"
);
const loaderSource = fs.readFileSync(loaderPath, "utf8");

function createBrowserHarness() {
  const scripts = [];
  const panels = [];
  const host = { innerHTML: "" };

  const document = {
    body: {
      appendChild(script) {
        scripts.push(script.src);
        queueMicrotask(() => script.onload());
      }
    },
    createElement(tagName) {
      assert.equal(tagName, "script");
      return { dataset: {}, src: "", onload: null, onerror: null };
    },
    getElementById(id) {
      return id === "experienceViews" ? host : null;
    },
    querySelector() {
      return null;
    }
  };

  async function fetch(resourcePath) {
    panels.push(resourcePath);
    return {
      ok: true,
      status: 200,
      async text() {
        return `<section data-source="${resourcePath}"></section>`;
      }
    };
  }

  const context = vm.createContext({
    console,
    document,
    fetch,
    Promise,
    queueMicrotask
  });
  vm.runInContext(loaderSource, context, { filename: loaderPath });

  return {
    scripts,
    panels,
    host,
    load(entityType) {
      return vm.runInContext(`loadExperience(${JSON.stringify(entityType)})`, context);
    }
  };
}

test("Autopartes carga únicamente su panel, su lógica y el demo de taller", async () => {
  const browser = createBrowserHarness();

  await browser.load("auto_parts_store");

  assert.deepEqual(browser.scripts, [
    "frontend/experiences/hospitality/hospitality.js",
    "frontend/experiences/auto-parts/auto-parts.js",
    "frontend/experiences/auto-parts/workshop-demo.js"
  ]);
  assert.deepEqual(browser.panels, [
    "frontend/experiences/auto-parts/panel.html"
  ]);
  assert.match(browser.host.innerHTML, /auto-parts\/panel\.html/);
});

test("Ferretería y Farmasi cargan solamente sus recursos específicos", async () => {
  const hardware = createBrowserHarness();
  await hardware.load("hardware_store");
  assert.deepEqual(hardware.scripts, [
    "frontend/experiences/hospitality/hospitality.js",
    "frontend/experiences/hardware/hardware.js"
  ]);
  assert.deepEqual(hardware.panels, [
    "frontend/experiences/hardware/panel.html"
  ]);

  const farmasi = createBrowserHarness();
  await farmasi.load("wellness_sales_assistant");
  assert.deepEqual(farmasi.scripts, [
    "frontend/experiences/hospitality/hospitality.js",
    "frontend/experiences/farmasi/farmasi.js"
  ]);
  assert.deepEqual(farmasi.panels, [
    "frontend/experiences/farmasi/panel.html"
  ]);
});

test("Hotel, Airbnb y Turismo cargan turismo sin panel comercial", async () => {
  for (const entityType of ["hotel", "airbnb", "lodging", "Tourism Assistant"]) {
    const browser = createBrowserHarness();
    await browser.load(entityType);

    assert.deepEqual(browser.scripts, [
      "frontend/experiences/hospitality/hospitality.js",
      "frontend/experiences/tourism/tourism.js"
    ]);
    assert.deepEqual(browser.panels, []);
    assert.equal(browser.host.innerHTML, "");
  }
});

test("Una entidad desconocida conserva solo las acciones compartidas", async () => {
  const browser = createBrowserHarness();

  await browser.load("unknown_entity");

  assert.deepEqual(browser.scripts, [
    "frontend/experiences/hospitality/hospitality.js"
  ]);
  assert.deepEqual(browser.panels, []);
});

test("index.html no carga de forma fija los módulos opcionales", () => {
  const html = fs.readFileSync(path.join(projectRoot, "index.html"), "utf8");
  const optionalScripts = [
    "frontend/experiences/hospitality/hospitality.js",
    "frontend/experiences/tourism/tourism.js",
    "frontend/experiences/auto-parts/auto-parts.js",
    "frontend/experiences/auto-parts/workshop-demo.js",
    "frontend/experiences/hardware/hardware.js",
    "frontend/experiences/farmasi/farmasi.js"
  ];

  for (const scriptPath of optionalScripts) {
    assert.doesNotMatch(html, new RegExp(`<script[^>]+${scriptPath}`));
  }
});

test("las experiencias guiadas reciben fillSelect desde el núcleo compartido", () => {
  const html = fs.readFileSync(path.join(projectRoot, "index.html"), "utf8");
  const sharedUtility = "frontend/shared/form-controls.js";
  const bootstrap = "frontend/shared/bootstrap.js";

  assert.match(html, new RegExp(`<script[^>]+${sharedUtility}`));
  assert.ok(
    html.indexOf(sharedUtility) < html.indexOf(bootstrap),
    "form-controls.js debe cargarse antes de bootstrap.js"
  );

  const utilitySource = fs.readFileSync(
    path.join(projectRoot, sharedUtility),
    "utf8"
  );
  assert.match(utilitySource, /function\s+fillSelect\s*\(/);

  for (const experience of ["auto-parts", "hardware", "farmasi"]) {
    const source = fs.readFileSync(
      path.join(
        projectRoot,
        "frontend",
        "experiences",
        experience,
        `${experience}.js`
      ),
      "utf8"
    );
    assert.doesNotMatch(source, /function\s+fillSelect\s*\(/);
  }
});
