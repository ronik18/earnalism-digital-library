import { Outlet } from "react-router-dom";
import Header from "./Header";
import Footer from "./Footer";
import { AppToaster } from "./AppToaster";

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1">
        <Outlet />
      </main>
      <Footer />
      <AppToaster position="bottom-right" />
    </div>
  );
}
