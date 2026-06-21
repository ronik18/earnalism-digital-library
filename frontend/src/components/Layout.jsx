import { Outlet } from "react-router-dom";
import Header from "./Header";
import Footer from "./Footer";
import FirstVisitSiteTour from "./FirstVisitSiteTour";

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      <a href="#main-content" className="skip-link">Skip to main content</a>
      <Header />
      <main id="main-content" className="flex-1" tabIndex={-1}>
        <Outlet />
      </main>
      <Footer />
      <FirstVisitSiteTour />
    </div>
  );
}
