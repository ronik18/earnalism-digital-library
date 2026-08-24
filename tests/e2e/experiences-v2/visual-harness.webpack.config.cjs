const path = require("path");
const { createRequire } = require("module");
const frontendRequire = createRequire(path.resolve(__dirname, "../../../frontend/package.json"));
const webpack = frontendRequire("webpack");
const HtmlWebpackPlugin = frontendRequire("html-webpack-plugin");

module.exports = {
  mode: "production",
  entry: path.resolve(__dirname, "visual-entry.jsx"),
  output: { path: path.resolve(__dirname, "visual-harness"), filename: "bundle.js", clean: true },
  resolve: { extensions: [".js", ".jsx"], modules: [path.resolve(__dirname, "../../../frontend/node_modules"), "node_modules"] },
  module: { rules: [
    { test: /\.jsx?$/, exclude: /node_modules/, use: { loader: frontendRequire.resolve("babel-loader"), options: { presets: [[frontendRequire.resolve("@babel/preset-env"), { targets: "defaults" }], [frontendRequire.resolve("@babel/preset-react"), { runtime: "automatic" }]] } } },
    { test: /\.css$/, use: [frontendRequire.resolve("style-loader"), frontendRequire.resolve("css-loader")] },
    { test: /\.(png|jpe?g|svg)$/i, type: "asset/resource" },
  ] },
  plugins: [new webpack.DefinePlugin({ "process.env": JSON.stringify({ PUBLIC_URL: "", REACT_APP_BACKEND_URL: "" }) }), new HtmlWebpackPlugin({ title: "RLA v2 visual harness", templateContent: "<!doctype html><html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>RLA v2 visual harness</title></head><body><div id=\"root\"></div></body></html>" })],
  devtool: false,
};
