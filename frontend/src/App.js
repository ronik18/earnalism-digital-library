import { lazy, Suspense, useEffect } from "react";
import { BrowserRouter, Routes, Route, useLocation, Navigate, useParams } from "react-router-dom";
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
  AboutLegacy: () => import("./pages/About"),
  Contact: () => import("./pages/Contact"),
  Login: () => import("./pages/Login"),
  Signup: () => import("./pages/Signup"),
  Account: () => import("./pages/Account"),
  MyLibrary: () => import("./pages/MyLibrary"),
  Pricing: () => import("./pages/Pricing"),
  ReaderLegacy: () => import("./pages/Reader"),
  ReaderV2: () => import("./experiences-v2/reader/ReaderExperienceV2Route"),
  ListenerV2: () => import("./experiences-v2/listener/ListenerExperienceV2Route"),
  AboutV2: () => import("./experiences-v2/about/AboutExperienceV2Route"),
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
const AboutLegacy = lazy(pageImports.AboutLegacy);
const Contact = lazy(pageImports.Contact);
const Login = lazy(pageImports.Login);
const Signup = lazy(pageImports.Signup);
const Account = lazy(pageImports.Account);
const MyLibrary = lazy(pageImports.MyLibrary);
const Pricing = lazy(pageImports.Pricing);
const ReaderLegacy = lazy(pageImports.ReaderLegacy);
const ReaderV2 = lazy(pageImports.ReaderV2);
const ListenerV2 = lazy(pageImports.ListenerV2);
const AboutV2 = lazy(pageImports.AboutV2);
const MicroStoryLanding = lazy(pageImports.MicroStoryLanding);
const SecureReaderHarness = lazy(pageImports.SecureReaderHarness);
const AdminLogin = lazy(pageImports.AdminLogin);
const Admin = lazy(pageImports.Admin);
const NotFound = lazy(pageImports.NotFound);
const GoogleAuthBoundary = lazy(pageImports.GoogleAuthBoundary);
const ROUTE_FONT_STYLESHEET_ID = "earnalism-route-fonts";
const ROUTE_FONT_STYLESHEET = "https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Noto+Sans+Bengali:wght@400;500;600&family=Noto+Serif+Bengali:wght@500;600&family=Outfit:wght@400;500;600;700&display=swap";

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

function LegacyListenerRedirect() {
  const { slug = "" } = useParams();
  return <Navigate to={`/reader-legacy/${encodeURIComponent(slug)}?listen=1`} replace />;
}

function useHighIntentRoutePrefetch() {
  useEffect(() => {
    const prefetch = () => {
      [
        pageImports.Library,
        pageImports.BookDetail,
        pageImports.ReaderV2,
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
            <Route path="/about-legacy" element={<AboutLegacy />} />
            <Route path="/contact" element={<Contact />} />
            <Route path="/pricing" element={<Pricing />} />
            <Route path="/micro-story" element={<MicroStoryLanding />} />
            <Route path="/secure-reader-test" element={<SecureReaderHarness />} />
            <Route path="/login" element={<GoogleAuthBoundary><Login /></GoogleAuthBoundary>} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/account" element={<Account />} />
            <Route path="/my-library" element={<MyLibrary />} />
            {/* Legacy redirects */}
            <Route path="/signin" element={<Navigate to="/login" replace />} />
            <Route path="/publishing" element={<Navigate to="/library" replace />} />
            <Route path="/publishing/*" element={<Navigate to="/library" replace />} />
            <Route path="*" element={<NotFound />} />
          </Route>
          {/* Standalone full-screen routes (no public header/footer) */}
          <Route path="/about" element={<AboutV2 />} />
          <Route path="/reader/:slug" element={<ReaderV2 />} />
          <Route path="/reader-legacy/:slug" element={<ReaderLegacy />} />
          <Route path="/listener/:slug" element={<ListenerV2 />} />
          <Route path="/listener-legacy/:slug" element={<LegacyListenerRedirect />} />
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
