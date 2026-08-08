const fs = require("node:fs");
const path = require("node:path");
const babel = require("@babel/core");
const React = require("react");
const { renderToString } = require("react-dom/server");

const frontendDir = path.resolve(__dirname, "..");
const defaultJsLoader = require.extensions[".js"];

function compileApplicationModule(module, filename) {
  if (filename.includes(`${path.sep}node_modules${path.sep}`)) {
    return defaultJsLoader(module, filename);
  }
  const source = fs.readFileSync(filename, "utf8");
  const result = babel.transformSync(source, {
    filename,
    babelrc: false,
    configFile: false,
    presets: [
      [require.resolve("@babel/preset-env"), { modules: "commonjs", targets: { node: "current" } }],
      [require.resolve("@babel/preset-react"), { runtime: "automatic" }],
    ],
    sourceMaps: false,
  });
  module._compile(result.code, filename);
}

require.extensions[".js"] = compileApplicationModule;
require.extensions[".jsx"] = compileApplicationModule;
require.extensions[".css"] = () => {};

process.env.NODE_ENV = "production";
process.chdir(frontendDir);

const PrerenderApp = require(path.join(frontendDir, "src", "PrerenderApp.jsx")).default;
const html = renderToString(
  React.createElement(
    React.StrictMode,
    null,
    React.createElement(PrerenderApp, { location: "/" }),
  ),
);

process.stdout.write(html);
