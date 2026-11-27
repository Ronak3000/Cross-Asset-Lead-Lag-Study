const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const output = path.join(root, ".vercel", "output");
const assets = path.join(output, "static");
const backend = process.env.RENDER_API_ORIGIN?.trim();
const routes = [];

if (backend) {
  const url = new URL(backend);
  if (url.protocol !== "https:" || url.pathname !== "/" || url.search || url.hash || url.username || url.password) {
    throw new Error("Set RENDER_API_ORIGIN to the HTTPS origin of your FastAPI service.");
  }
  routes.push({ src: "^/api/(.*)$", dest: url.origin + "/api/$1" });
}
routes.push({ handle: "filesystem" });

// Only replace generated output. The CLI stores the project link in its parent.
fs.mkdirSync(output, { recursive: true });
if (fs.realpathSync(output) !== path.join(fs.realpathSync(root), ".vercel", "output")) {
  throw new Error("Unexpected Vercel output location.");
}
fs.rmSync(output, { recursive: true });
fs.mkdirSync(path.join(assets, "ui"), { recursive: true });
for (const file of ["app.js", "style.css", "THIRD-PARTY-LICENSES.txt"]) {
  fs.copyFileSync(path.join(__dirname, file), path.join(assets, "ui", file));
}
fs.copyFileSync(require.resolve("plotly.js-dist-min"), path.join(assets, "plot.js"));
fs.copyFileSync(require.resolve("plotly.js-dist-min/LICENSE"), path.join(assets, "plotly-LICENSE.txt"));
const archive = path.join(root, "archive");
for (const entry of fs.readdirSync(archive, { recursive: true, withFileTypes: true })) {
  if (!entry.isFile()) continue;
  const source = path.join(entry.parentPath, entry.name);
  const destination = path.join(assets, "archive", path.relative(archive, source));
  fs.mkdirSync(path.dirname(destination), { recursive: true });
  fs.copyFileSync(source, destination);
}

let html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
if (!backend) {
  html = html.replace("</head>", "<script>window.PHASE_STATIC=true</script></head>");
}
fs.writeFileSync(path.join(assets, "index.html"), html);
fs.writeFileSync(path.join(output, "config.json"), JSON.stringify({ version: 3, routes }, null, 2));
console.log(backend ? "Historical dashboard and simulator proxy built." : "Historical dashboard built in archive-only mode.");
