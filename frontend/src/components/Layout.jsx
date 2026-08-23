import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Header from "./Header";
import Footer from "./Footer";

const FirstVisitSiteTour = lazy(() => import("./FirstVisitSiteTour"));
const TOUR_STORAGE_KEY = "earnalism:first-visit-site-tour:v1";

function hasCompletedFirstVisitTour() {
  try {
    return window.localStorage.getItem(TOUR_STORAGE_KEY) === "complete";
  } catch (_) {
    return false;
  }
}

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

    // The public reference surfaces must never be obstructed by an automatic
    // tour. A tour remains available only through the deliberate ?tour=1 path.
    setTourReady(false);
    return undefined;
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
