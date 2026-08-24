import { BookHeart, Gem, ShieldCheck, Sparkles } from "lucide-react";
import ExperienceBottomNavigation from "../shared/ExperienceBottomNavigation";
import ExperienceHeader from "../shared/ExperienceHeader";
import ExperienceShell from "../shared/ExperienceShell";
import "./about-v2.css";

export const ABOUT_TRUST_CARDS = Object.freeze([
  { title: "Curated classics", body: "Handpicked Bengali and English literary editions.", Icon: BookHeart },
  { title: "Immersive experience", body: "Designed for thoughtful reading and listening when approved.", Icon: Sparkles },
  { title: "Thoughtful design", body: "A calm, readable digital library across devices.", Icon: Gem },
  { title: "Trusted & transparent", body: "Rights and release claims stay evidence-led.", Icon: ShieldCheck },
]);

export default function AboutExperienceV2({ buildLabel = "", onNavigate }) {
  return <ExperienceShell className="about-v2" labelledBy="about-v2-title"><ExperienceHeader compact onSearch={() => onNavigate?.("search")} /><section className="about-v2__content"><span className="about-v2__eyebrow">Earnalism</span><h1 id="about-v2-title">About Earnalism</h1><p className="about-v2__intro">Earnalism is a calm Bengali and English digital library for readers who value enduring literature, thoughtful design, and release truth before every public claim.</p><div className="about-v2__cards">{ABOUT_TRUST_CARDS.map(({ title, body, Icon }) => <article key={title}><Icon size={23} aria-hidden="true" /><div><h2>{title}</h2><p>{body}</p></div></article>)}</div>{buildLabel && <small className="about-v2__build">{buildLabel}</small>}</section><ExperienceBottomNavigation active="profile" onNavigate={onNavigate} /></ExperienceShell>;
}
