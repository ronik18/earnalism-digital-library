import React from "react";
import ReactDOM from "react-dom/client";
import { injectSpeedInsights } from "@vercel/speed-insights";
import "@/index.css";
import App from "@/App";
import { initPerformanceMetrics } from "./lib/performanceMetrics";

const rootElement = document.getElementById("root");
const app = (
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

if (rootElement?.dataset.prerendered === "home" && rootElement.hasChildNodes()) {
  ReactDOM.hydrateRoot(rootElement, app);
} else {
  ReactDOM.createRoot(rootElement).render(app);
}

initPerformanceMetrics();
injectSpeedInsights();

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
