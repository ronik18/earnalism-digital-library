const crypto = require("crypto");

function sha256(value) {
  return crypto.createHash("sha256").update(value || "").digest("hex");
}

function stableJson(value) {
  return JSON.stringify(value, Object.keys(value || {}).sort());
}

module.exports = { sha256, stableJson };
