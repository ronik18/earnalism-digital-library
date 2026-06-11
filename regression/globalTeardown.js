const fs = require("fs");
const path = require("path");

module.exports = async () => {
  const statePath = path.resolve(__dirname, "artifacts", "run-state.json");
  if (!fs.existsSync(statePath)) return;
  const state = JSON.parse(fs.readFileSync(statePath, "utf8"));
  state.finishedAt = new Date().toISOString();
  fs.writeFileSync(statePath, JSON.stringify(state, null, 2));
};
