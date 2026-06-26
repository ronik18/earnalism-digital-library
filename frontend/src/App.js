import { lazy, Suspense, useEffect } from "react";
import { BrowserRouter, Routes, Route, useLocation, Navigate } from "react-router-dom";
import "@/index.css";
import { AuthProvider } from "./context/AuthContext";
import { SettingsProvider } from "./context/SettingsContext";
import Layout from "./components/Layout";
import { AppToaster } from "./components/AppToaster";

const pageImports = {
  Home: () => import("./pages/Home"),
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

const Home = lazy(pageImports.Home);
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

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => { window.scrollTo({ top: 0, behavior: "instant" }); }, [pathname]);
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
    const idle = window.requestIdleCallback || ((callback) => window.setTimeout(callback, 1600));
    const cancelIdle = window.cancelIdleCallback || window.clearTimeout;
    const id = idle(prefetch, { timeout: 3000 });
    return () => cancelIdle(id);
  }, []);
}

export default function App() {
  useHighIntentRoutePrefetch();

  return (
    <AuthProvider>
      <SettingsProvider>
        <BrowserRouter>
          <ScrollToTop />
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
        </BrowserRouter>
      </SettingsProvider>
    </AuthProvider>
  );
}
