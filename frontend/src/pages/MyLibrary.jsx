import { BookOpen, Headphones, LibraryBig } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import ExperienceBottomNavigation from "../experiences-v2/shared/ExperienceBottomNavigation";
import ExperienceShell from "../experiences-v2/shared/ExperienceShell";
import "./MyLibrary.css";

export default function MyLibrary() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const accountName = user?.name || "My Library";

  return (
    <ExperienceShell className="my-library-v2" labelledBy="my-library-title">
      <section className="my-library-v2__content" data-testid="my-library-mobile">
        <p className="my-library-v2__eyebrow">{accountName}</p>
        <h1 id="my-library-title">My Library</h1>
        <div className="my-library-v2__tabs" role="tablist" aria-label="Library format">
          <button type="button" role="tab" aria-selected="true"><BookOpen size={15} /> Books</button>
          <button type="button" role="tab" aria-selected="false" disabled><Headphones size={15} /> Audiobooks</button>
        </div>
        <section className="my-library-v2__empty" aria-live="polite">
          <LibraryBig size={28} aria-hidden="true" />
          <h2>Your shelf is ready.</h2>
          <p>Saved editions will appear here when your account records them. Browse the public Library to begin reading.</p>
          <Link to="/library">Browse the Library</Link>
        </section>
      </section>
      <ExperienceBottomNavigation active="library" onNavigate={(target) => {
        if (target === "home") navigate("/");
        if (target === "library") navigate("/library");
        if (target === "passes") navigate("/pricing");
        if (target === "profile") navigate("/account");
      }} />
    </ExperienceShell>
  );
}
