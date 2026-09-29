export const PUBLIC_NAV_ITEMS = Object.freeze([
  { key: "home", to: "/", label: "Home" },
  { key: "library", to: "/library", label: "Library" },
  { key: "bengali", to: "/library?language=bn&availability=reader-ready", label: "Bengali Classics" },
  { key: "english", to: "/library?language=en", label: "English Classics" },
  { key: "audiobooks", to: "/library?availability=approved-audiobook", label: "Audiobooks" },
  { key: "reading-pass", to: "/pricing", label: "Reading Pass" },
  { key: "about", to: "/about", label: "About" },
]);

export function isPublicNavItemActive(item, location) {
  const pathname = location.pathname.replace(/\/+$/, "") || "/";
  const params = new URLSearchParams(location.search);

  if (item.key === "home") return pathname === "/";
  if (item.key === "library") {
    const language = params.get("language");
    return pathname === "/library" && !["bn", "en"].includes(language) && params.get("availability") !== "approved-audiobook";
  }
  if (item.key === "bengali") return pathname === "/library" && params.get("language") === "bn";
  if (item.key === "english") return pathname === "/library" && params.get("language") === "en";
  if (item.key === "audiobooks") return pathname === "/library" && params.get("availability") === "approved-audiobook";
  return pathname === item.to;
}
