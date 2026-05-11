import { lazy, Suspense, useEffect } from "react";
import { BrowserRouter, Routes, Route, useLocation, Navigate } from "react-router-dom";
import { GoogleOAuthProvider } from "@react-oauth/google";
import "@/index.css";
import { AuthProvider } from "./context/AuthContext";
import { SettingsProvider } from "./context/SettingsContext";
import Layout from "./components/Layout";
import { AppToaster } from "./components/AppToaster";

const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID || "";

const Home = lazy(() => import("./pages/Home"));
const Library = lazy(() => import("./pages/Library"));
const BookDetail = lazy(() => import("./pages/BookDetail"));
const Journal = lazy(() => import("./pages/Journal"));
const JournalArticle = lazy(() => import("./pages/JournalArticle"));
const About = lazy(() => import("./pages/About"));
const Contact = lazy(() => import("./pages/Contact"));
const Login = lazy(() => import("./pages/Login"));
const Signup = lazy(() => import("./pages/Signup"));
const Account = lazy(() => import("./pages/Account"));
const Pricing = lazy(() => import("./pages/Pricing"));
const Reader = lazy(() => import("./pages/Reader"));
const AdminLogin = lazy(() => import("./pages/AdminLogin"));
const Admin = lazy(() => import("./pages/Admin"));

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => { window.scrollTo({ top: 0, behavior: "instant" }); }, [pathname]);
  return null;
}

function PageFallback() {
  return <div className="min-h-screen bg-[var(--beige-canvas)]" aria-busy="true" />;
}

export default function App() {
  const tree = (
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
                <Route path="/login" element={<Login />} />
                <Route path="/signup" element={<Signup />} />
                <Route path="/account" element={<Account />} />
                {/* Legacy redirects */}
                <Route path="/signin" element={<Navigate to="/login" replace />} />
                <Route path="/shop" element={<Navigate to="/library" replace />} />
                <Route path="/shop/:slug" element={<LegacyShopRedirect />} />
                <Route path="/publishing" element={<Navigate to="/library" replace />} />
                <Route path="/publishing/*" element={<Navigate to="/library" replace />} />
              </Route>
              {/* Standalone full-screen routes (no public header/footer) */}
              <Route path="/reader/:slug" element={<Reader />} />
              <Route path="/admin/login" element={<AdminLogin />} />
              <Route path="/admin" element={<Admin />} />
            </Routes>
          </Suspense>
          <AppToaster position="bottom-right" />
        </BrowserRouter>
      </SettingsProvider>
    </AuthProvider>
  );
  return GOOGLE_CLIENT_ID
    ? <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>{tree}</GoogleOAuthProvider>
    : tree;
}

function LegacyShopRedirect() {
  const path = window.location.pathname.replace(/^\/shop\//, "/book/");
  return <Navigate to={path} replace />;
}
