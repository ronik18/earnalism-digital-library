import React from 'react';

const ctas = [
  'Read the Dracula preview',
  'Start a 7-day reading pass',
  'Preview the study companion',
];

export default function DraculaLandingDraft() {
  return (
    <main className="dracula-draft" data-public-route-enabled="false">
      <section className="dracula-draft__hero" aria-labelledby="dracula-draft-title">
        <p className="dracula-draft__eyebrow">Earnalism controlled-publication draft</p>
        <h1 id="dracula-draft-title">Dracula by Bram Stoker</h1>
        <p className="dracula-draft__lede">
          A quiet reading-room draft for Bram Stoker&apos;s Gothic classic, prepared for source,
          rights, QA, revenue, and launch-safety review before any public activation.
        </p>
        <nav className="dracula-draft__ctas" aria-label="Draft calls to action">
          {ctas.map((cta) => (
            <span className="dracula-draft__cta" key={cta}>
              {cta}
            </span>
          ))}
        </nav>
      </section>
      <section className="dracula-draft__grid" aria-label="Draft publication evidence">
        <article>
          <h2>Source And Rights</h2>
          <p>
            Primary source target: Project Gutenberg eBook #345. This draft remains non-public
            until source hash, content hash, provenance hash, and Tier A rights approval pass.
          </p>
        </article>
        <article>
          <h2>Reading Experience</h2>
          <p>
            Draft scope includes a reading preview, study guide preview, seven-day challenge,
            and reading-pass CTA. Full audiobook promotion is excluded unless audio QA passes.
          </p>
        </article>
        <article>
          <h2>Rollback</h2>
          <p>
            Keep public publish actions at zero, remove draft artifacts, and disable any future
            Dracula activation flag if a later gate fails.
          </p>
        </article>
      </section>
    </main>
  );
}
