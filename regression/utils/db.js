function getMongoUrl() {
  return process.env.REGRESSION_MONGODB_URL || process.env.MONGODB_URL || "";
}

async function getMongoClient() {
  const url = getMongoUrl();
  if (!url) return { skipped: true, reason: "MONGODB_URL is not configured." };
  let mongodb;
  try {
    mongodb = require("mongodb");
  } catch {
    return { skipped: true, reason: "mongodb package is not installed for regression DB checks." };
  }
  const client = new mongodb.MongoClient(url, { serverSelectionTimeoutMS: 5000 });
  await client.connect();
  const dbName = process.env.REGRESSION_MONGODB_DB || process.env.DB_NAME;
  return { client, db: client.db(dbName), skipped: false };
}

async function withDb(fn) {
  const state = await getMongoClient();
  if (state.skipped) return state;
  try {
    return await fn(state.db, state.client);
  } finally {
    await state.client.close();
  }
}

module.exports = { getMongoUrl, getMongoClient, withDb };
