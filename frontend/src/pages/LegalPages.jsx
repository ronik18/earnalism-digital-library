import { Link } from "react-router-dom";
import PublicPageFrame from "../components/PublicPageFrame";
import useSEO from "../hooks/useSEO";
import policies from "../content/legalPolicies.json";

function LegalPage({ canonicalPath }) {
  const policy = policies[canonicalPath];
  useSEO({ title: `${policy.title} | The Earnalism`, description: policy.description, canonicalPath });
  return (
    <PublicPageFrame tone="quiet">
      <main id="main-content" tabIndex={-1}><article className="mx-auto max-w-3xl px-5 py-16 sm:px-8 sm:py-24" data-testid={`legal-${policy.title.toLowerCase().replace(/\s+/g, "-")}`}>
        <p className="editorial-kicker">Earnalism</p>
        <h1 className="mt-5 font-serif-light text-4xl leading-tight text-burgundy sm:text-6xl">{policy.title}</h1>
        <p className="mt-4">Updated {policy.updated}</p>
        <div className="editorial-surface mt-10 space-y-7 p-6 text-[1rem] leading-8 text-charcoal-soft sm:p-10">
          <p>{policy.intro}</p>
          {policy.sections.map(({ heading, paragraphs }) => <section key={heading}>
            <h2 className="font-serif-display text-2xl text-burgundy">{heading}</h2>
            {paragraphs.map((paragraph) => <p className="mt-3" key={paragraph}>{paragraph}</p>)}
          </section>)}
          <p><a className="text-burgundy underline" href="mailto:sales@reoenterprise.org">sales@reoenterprise.org</a>{" · "}
            <Link className="text-burgundy underline" to="/contact?intent=reader">Support and privacy requests</Link>{" · "}
            <Link className="text-burgundy underline" to="/contact?intent=rights">Rights concerns</Link>
          </p>
        </div>
      </article></main>
    </PublicPageFrame>
  );
}

export function Terms() { return <LegalPage canonicalPath="/terms" />; }
export function Privacy() { return <LegalPage canonicalPath="/privacy" />; }
export function CopyrightNotice() { return <LegalPage canonicalPath="/copyright" />; }
