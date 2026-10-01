export const PUBLIC_NAV_ITEMS = Object.freeze([
  { key: "home", to: "/", label: "Home" },
  { key: "library", to: "/library", label: "Library" },
  { key: "bengali", to: "/library?language=bn&availability=reader-ready", label: "Bengali Classics" },
  { key: "english", to: "/library?language=en", label: "English Classics" },
  { key: "audiobooks", to: "/library?availability=approved-audiobook", label: "Audiobooks" },
  { key: "reading-pass", to: "/pricing", label: "Reading Pass" },
  { key: "journal", to: "/journal", label: "Blog" },
  { key: "about", to: "/about", label: "About" },
]);

export function isPublicNavItemActive(item, location) {
  const pathname = location.pathname.replace(/\/+$/, "") || "/";
  const params = new URLSearchParams(location.search);

  if (item.key === "journal") return pathname === "/journal" || pathname.startsWith("/journal/");
  if (item.key === "home") return pathname === "/";
  if (pathname === "/library") {
    const activeKey = params.get("availability") === "approved-audiobook"
      ? "audiobooks"
      : params.get("language") === "bn"
        ? "bengali"
        : params.get("language") === "en"
          ? "english"
          : "library";
    return item.key === activeKey;
  }
  return pathname === item.to;
}
