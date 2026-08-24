import { BookOpen, House, LibraryBig, UserRound } from "lucide-react";

const ITEMS = [
  { key: "home", label: "Home", Icon: House },
  { key: "library", label: "Library", Icon: LibraryBig },
  { key: "passes", label: "Passes", Icon: BookOpen },
  { key: "profile", label: "Profile", Icon: UserRound },
];

export default function ExperienceBottomNavigation({ active = "", onNavigate }) {
  return <nav className="experience-bottom-nav" aria-label="Primary navigation">{ITEMS.map(({ key, label, Icon }) => <button key={key} type="button" aria-current={active === key ? "page" : undefined} onClick={() => onNavigate?.(key)}><Icon size={17} aria-hidden="true" /><span>{label}</span></button>)}</nav>;
}
