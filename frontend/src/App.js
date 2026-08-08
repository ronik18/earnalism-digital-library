import { lazy, Suspense, useEffect } from "react";
import { BrowserRouter, Routes, Route, useLocation, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { SettingsProvider } from "./context/SettingsContext";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import { AppToaster } from "./components/AppToaster";

const pageImports = {
  Library: () => import("./pages/Library"),
  BookDetail: () => import("./pages/BookDetail"),
  Journal: () => import("./pages/Journal"),
  JournalArticle: () => import("./pages/JournalArticle"),
  About: () => import("./pages/About"),
  Contact: () => import("./pages/Contact"),
  Login: () => import("./pages/Login"),
  Signup: () => import("./pages/Signup"),
  Account: () => import("./pages/Account"),
  Pricing: () => import("./pages/Pricing"),
  Reader: () => import("./pages/Reader"),
  MicroStoryLanding: () => import("./pages/MicroStoryLanding"),
  SecureReaderHarness: () => import("./pages/SecureReaderHarness"),
  AdminLogin: () => import("./pages/AdminLogin"),
  Admin: () => import("./pages/Admin"),
  NotFound: () => import("./pages/NotFound"),
  GoogleAuthBoundary: () => import("./components/GoogleAuthBoundary"),
};

const Library = lazy(pageImports.Library);
const BookDetail = lazy(pageImports.BookDetail);
const Journal = lazy(pageImports.Journal);
const JournalArticle = lazy(pageImports.JournalArticle);
const About = lazy(pageImports.About);
const Contact = lazy(pageImports.Contact);
const Login = lazy(pageImports.Login);
const Signup = lazy(pageImports.Signup);
const Account = lazy(pageImports.Account);
const Pricing = lazy(pageImports.Pricing);
const Reader = lazy(pageImports.Reader);
const MicroStoryLanding = lazy(pageImports.MicroStoryLanding);
const SecureReaderHarness = lazy(pageImports.SecureReaderHarness);
const AdminLogin = lazy(pageImports.AdminLogin);
const Admin = lazy(pageImports.Admin);
const NotFound = lazy(pageImports.NotFound);
const GoogleAuthBoundary = lazy(pageImports.GoogleAuthBoundary);
const ROUTE_FONT_STYLESHEET_ID = "earnalism-route-fonts";
const ROUTE_FONT_STYLESHEET = "https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;500;600&family=Crimson+Pro:wght@400;500;600&family=Noto+Serif+Bengali:wght@400;500;600&family=Outfit:wght@400;500;600&display=optional";

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => { window.scrollTo({ top: 0, behavior: "instant" }); }, [pathname]);
  return null;
}

function RouteFontLoader() {
  const { pathname } = useLocation();

  useEffect(() => {
    if (pathname === "/" || document.getElementById(ROUTE_FONT_STYLESHEET_ID)) return;
    const stylesheet = document.createElement("link");
    stylesheet.id = ROUTE_FONT_STYLESHEET_ID;
    stylesheet.rel = "stylesheet";
    stylesheet.href = ROUTE_FONT_STYLESHEET;
    document.head.appendChild(stylesheet);
  }, [pathname]);

  return null;
}

function PageFallback() {
  return (
    <div className="min-h-screen bg-[var(--beige-canvas)]" role="status" aria-live="polite" aria-busy="true">
      <span className="sr-only">Loading The Earnalism reading room.</span>
    </div>
  );
}

function useHighIntentRoutePrefetch() {
  useEffect(() => {
    const prefetch = () => {
      [
        pageImports.Library,
        pageImports.BookDetail,
        pageImports.Reader,
        pageImports.Pricing,
        pageImports.Login,
      ].forEach((load) => load().catch(() => {}));
    };
    const id = window.setTimeout(prefetch, 5600);
    return () => window.clearTimeout(id);
  }, []);
}

export function AppProviders({ children }) {
  return (
    <AuthProvider>
      <SettingsProvider>{children}</SettingsProvider>
    </AuthProvider>
  );
}

export function AppRouterContent() {
  useHighIntentRoutePrefetch();

  return (
    <>
      <ScrollToTop />
      <RouteFontLoader />
      <Suspense fallback={<PageFallback />}>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Home />} />
            <Route path="/library" element={<Library />} />
            <Route path="/book/:slug" element={<BookDetail />} />
            <Route path="/journal" element={<Journal />} />
            <Route path="/journal/:slug" element={<JournalArticle />} />
            <Route path="/about" element={<About />} />
            <Route path="/contact" element={<Contact />} />
            <Route path="/pricing" element={<Pricing />} />
            <Route path="/micro-story" element={<MicroStoryLanding />} />
            <Route path="/secure-reader-test" element={<SecureReaderHarness />} />
            <Route path="/login" element={<GoogleAuthBoundary><Login /></GoogleAuthBoundary>} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/account" element={<Account />} />
            {/* Legacy redirects */}
            <Route path="/signin" element={<Navigate to="/login" replace />} />
            <Route path="/publishing" element={<Navigate to="/library" replace />} />
            <Route path="/publishing/*" element={<Navigate to="/library" replace />} />
            <Route path="*" element={<NotFound />} />
          </Route>
          {/* Standalone full-screen routes (no public header/footer) */}
          <Route path="/reader/:slug" element={<Reader />} />
          <Route path="/admin/login" element={<AdminLogin />} />
          <Route path="/admin" element={<Admin />} />
          <Route path="/admin/launch-monitor" element={<Admin initialTab="launch-monitor" />} />
        </Routes>
      </Suspense>
      <AppToaster position="bottom-right" />
    </>
  );
}

export default function App() {
  return (
    <AppProviders>
      <BrowserRouter>
        <AppRouterContent />
      </BrowserRouter>
    </AppProviders>
  );
}
