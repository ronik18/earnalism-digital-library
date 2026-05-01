import useSEO from "../hooks/useSEO";
import { Link } from "react-router-dom";

export default function SignIn() {
  useSEO({
    title: "Sign In — The Earnalism Digital Library",
    description: "Reader accounts are opening in Phase 2 of The Earnalism Digital Library. Join the Reading Circle to be notified.",
  });
  return (
    <div className="min-h-[70vh] flex items-center justify-center px-5 py-16" data-testid="signin-page">
      <div className="card-elegant p-10 sm:p-14 max-w-xl w-full text-center">
        <div className="italic-eyebrow mb-4">Coming Soon</div>
        <h1 className="font-serif-light text-3xl sm:text-4xl text-burgundy leading-tight">Reader accounts are <span className="italic-accent">opening soon.</span></h1>
        <div className="gold-rule-thin mx-auto mt-6" />
        <p className="text-charcoal-soft mt-7 leading-[1.8] font-light">
          For now, every visitor can read the Library preview freely. Personal accounts, saved progress, and reading-time wallets arrive in the next phase of the Digital Library.
        </p>
        <div className="mt-9 flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center">
          <Link to="/library" className="btn-primary w-full sm:w-auto">Explore the Library</Link>
          <Link to="/#newsletter" className="btn-secondary w-full sm:w-auto">Join the Reading Circle</Link>
        </div>
      </div>
    </div>
  );
}
