import { useEffect } from "react";
import { BrowserRouter, Routes, Route, useLocation, Navigate } from "react-router-dom";
import "@/index.css";
import { AuthProvider } from "./context/AuthContext";
import { SettingsProvider } from "./context/SettingsContext";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import Library from "./pages/Library";
import BookDetail from "./pages/BookDetail";
import Journal from "./pages/Journal";
import JournalArticle from "./pages/JournalArticle";
import About from "./pages/About";
import Contact from "./pages/Contact";
import SignIn from "./pages/SignIn";
import Reader from "./pages/Reader";
import AdminLogin from "./pages/AdminLogin";
import Admin from "./pages/Admin";

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => { window.scrollTo({ top: 0, behavior: "instant" }); }, [pathname]);
  return null;
}

export default function App() {
  return (
    <AuthProvider>
      <SettingsProvider>
        <BrowserRouter>
          <ScrollToTop />
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<Home />} />
              <Route path="/library" element={<Library />} />
              <Route path="/book/:slug" element={<BookDetail />} />
              <Route path="/journal" element={<Journal />} />
              <Route path="/journal/:slug" element={<JournalArticle />} />
              <Route path="/about" element={<About />} />
              <Route path="/contact" element={<Contact />} />
              <Route path="/signin" element={<SignIn />} />
              {/* Legacy redirects */}
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
        </BrowserRouter>
      </SettingsProvider>
    </AuthProvider>
  );
}

function LegacyShopRedirect() {
  const path = window.location.pathname.replace(/^\/shop\//, "/book/");
  return <Navigate to={path} replace />;
}
