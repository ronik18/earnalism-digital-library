import { Link } from "react-router-dom";

export default function LibraryReadingPassCard({ compact = false }) {
  return <section className={`reference-library__pass${compact ? " reference-library__pass--compact" : ""}`} aria-label="Reading Pass invitation">
    <h2>Reading Pass</h2><p>Make time for<br />one more chapter.</p><Link to="/pricing">Explore Passes</Link>
    <span className="reference-library__pass-art" aria-hidden="true"><img src="/assets/library/reading-pass-reference.png" width="1168" height="1474" alt="" loading="lazy" /></span>
  </section>;
}
