import assert from "node:assert/strict";
import test from "node:test";

import { isHardSmokeNetworkFailure } from "./journey_smoke_network.mjs";

test("the reported aborted request fixture is not a server or network blocker", () => {
  assert.equal(isHardSmokeNetworkFailure({
    type: "requestfailed",
    resource_type: "fetch",
    failure: "net::ERR_ABORTED",
    url: "http://127.0.0.1:3000/api/home",
  }), false);
});

test("a real failed API request remains a blocker", () => {
  assert.equal(isHardSmokeNetworkFailure({
    type: "requestfailed",
    resource_type: "fetch",
    failure: "net::ERR_CONNECTION_REFUSED",
    url: "http://127.0.0.1:3000/api/home",
  }), true);
});

test("a server response failure remains a blocker", () => {
  assert.equal(isHardSmokeNetworkFailure({
    type: "http_error",
    status: 503,
    resource_type: "fetch",
    url: "http://127.0.0.1:3000/api/home",
  }), true);
});

test("a client HTTP response remains non-blocking", () => {
  assert.equal(isHardSmokeNetworkFailure({
    type: "http_error",
    status: 404,
    resource_type: "fetch",
    url: "http://127.0.0.1:3000/missing",
  }), false);
});
