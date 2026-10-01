import Header from "../../components/Header";

// Immersive routes share the public shell while retaining their existing
// navigation callback so leaving a Reader/Listener settles its session.
export default function ExperienceHeader({ onNavigatePath }) {
  return <div className="experience-header-shell" data-testid="experience-header"><Header onNavigatePath={onNavigatePath} /></div>;
}
