import React from "react";
import ReactDOM from "react-dom/client";
import { injectSpeedInsights } from "@vercel/speed-insights";
import "@/index.css";
import App from "@/App";
import { initPerformanceMetrics } from "./lib/performanceMetrics";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Earnalism requires an empty #root mount element.");
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

initPerformanceMetrics();
const speedInsightsHost = window.location.hostname;
const canUseSpeedInsights = speedInsightsHost === "theearnalism.com"
  || speedInsightsHost === "www.theearnalism.com"
  || speedInsightsHost.endsWith(".vercel.app");

if (canUseSpeedInsights) injectSpeedInsights();

const serviceWorkerAvailable = process.env.NODE_ENV === "production" && "serviceWorker" in navigator;
const serviceWorkerEnabled = process.env.REACT_APP_ENABLE_SERVICE_WORKER === "true";

if (serviceWorkerAvailable && serviceWorkerEnabled) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js").catch(() => {
      // Service worker caching is an enhancement; failures must not affect reading.
    });
  });
} else if (serviceWorkerAvailable) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.getRegistrations?.().then((registrations) => {
      registrations.forEach((registration) => registration.unregister());
    }).catch(() => {
      // Preview protection can redirect service-worker scripts; keep validation noise out.
    });
  });
}
