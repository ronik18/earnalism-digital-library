import { Bell, Search } from "lucide-react";
import EarnalismBrandLockup from "../../components/EarnalismBrandLockup";
import ExperienceIconButton from "./ExperienceIconButton";

export default function ExperienceHeader({ compact = false, onSearch, onNotifications, trailingLabel = "Library" }) {
  return (
    <header className={`experience-header ${compact ? "experience-header--compact" : ""}`.trim()}>
      <EarnalismBrandLockup variant={compact ? "mobile-header" : "desktop-header"} />
      <div className="experience-header__actions">
        {!compact && <span className="experience-header__label">{trailingLabel}</span>}
        {onSearch && <ExperienceIconButton label="Search library" onClick={onSearch}><Search size={17} /></ExperienceIconButton>}
        {onNotifications && <ExperienceIconButton label="Notifications" onClick={onNotifications}><Bell size={17} /></ExperienceIconButton>}
      </div>
    </header>
  );
}
