import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Header from "./Header";
import Footer from "./Footer";

const FirstVisitSiteTour = lazy(() => import("./FirstVisitSiteTour"));
const TOUR_IMPORT_DELAY_MS = 2600;

export default function Layout() {
  const location = useLocation();
  const [tourReady, setTourReady] = useState(false);
  const forcedTour = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return params.get("tour") === "1";
  }, [location.search]);

  useEffect(() => {
    if (location.pathname !== "/") {
      setTourReady(false);
      return undefined;
    }
    if (forcedTour) {
      setTourReady(true);
      return undefined;
    }
    const timer = window.setTimeout(() => setTourReady(true), TOUR_IMPORT_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [forcedTour, location.pathname]);

  return (
    <div className="min-h-screen flex flex-col">
      <a href="#main-content" className="skip-link">Skip to main content</a>
      <Header />
      <main id="main-content" className="flex-1" tabIndex={-1}>
        <Outlet />
      </main>
      <Footer />
      {tourReady && (
        <Suspense fallback={null}>
          <FirstVisitSiteTour />
        </Suspense>
      )}
    </div>
  );
}
