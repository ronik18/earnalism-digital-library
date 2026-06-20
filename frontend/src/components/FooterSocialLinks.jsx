import {
  Facebook,
  Instagram,
  Linkedin,
  MessageCircle,
  Send,
  Twitter,
  Youtube,
} from "lucide-react";
import { getEnabledSocialLinks } from "../config/socialLinks";

const ICONS = {
  facebook: Facebook,
  instagram: Instagram,
  linkedin: Linkedin,
  telegram: Send,
  whatsapp: MessageCircle,
  x: Twitter,
  youtube: Youtube,
};

export default function FooterSocialLinks({ links }) {
  const enabledLinks = getEnabledSocialLinks(links);
  if (!enabledLinks.length) return null;

  return (
    <div className="footer-social" data-testid="footer-socials">
      <div className="footer-social__label">Follow The Earnalism</div>
      <nav className="footer-social__links" aria-label="Earnalism social links">
        {enabledLinks.map((link) => {
          const Icon = ICONS[link.icon] || MessageCircle;
          return (
            <a
              key={link.id}
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={link.ariaLabel}
              className="footer-social__link"
              data-testid={`footer-social-${link.id}`}
            >
              <Icon className="footer-social__icon" size={17} strokeWidth={1.55} aria-hidden="true" />
              <span className="footer-social__sr-label">{link.label}</span>
            </a>
          );
        })}
      </nav>
    </div>
  );
}
