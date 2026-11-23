const path = require("node:path");
require("esbuild").buildSync({
  absWorkingDir: __dirname,
  entryPoints: ["src/main.jsx"],
  outfile: path.join(__dirname, "app.js"),
  bundle: true, minify: true, legalComments: "eof",
  define: { "process.env.NODE_ENV": '"production"' }
});
