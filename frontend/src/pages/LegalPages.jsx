import { Link } from "react-router-dom";
import PublicPageFrame from "../components/PublicPageFrame";
import useSEO from "../hooks/useSEO";

const CONTACT_EMAIL = "sales@reoenterprise.org";

function LegalPage({ title, description, canonicalPath, children }) {
  useSEO({ title: `${title} | The Earnalism`, description, canonicalPath });
  return (
    <PublicPageFrame tone="quiet">
      <article className="mx-auto max-w-3xl px-5 py-16 sm:px-8 sm:py-24" data-testid={`legal-${title.toLowerCase().replace(/\s+/g, "-")}`}>
        <p className="editorial-kicker">Earnalism</p>
        <h1 className="mt-5 font-serif-light text-4xl leading-tight text-burgundy sm:text-6xl">{title}</h1>
        <div className="editorial-surface mt-10 space-y-7 p-6 text-[1rem] leading-8 text-charcoal-soft sm:p-10">
          {children}
        </div>
      </article>
    </PublicPageFrame>
  );
}

export function Terms() {
  return <LegalPage title="Terms of Use" canonicalPath="/terms" description="The terms that apply to the current Earnalism reading experience.">
    <p>Earnalism is a digital library venture operated by REO ENTERPRISE, Reo Enterprise, Nihar Bhawan, 73, Nandan Nagar, Kolkata - 700083, District - North 24 Parganas, Kolkata - 700083. These terms apply to the website and the reading features actually enabled for your location.</p>
    <section><h2 className="font-serif-display text-2xl text-burgundy">The service and Reading Passes</h2><p className="mt-3">The six released India titles provide a free preview of pages 1–3; page 4 onward requires a valid Reading Pass entitlement. Reading Passes are one-time purchases: ₹49 for 30 minutes, ₹89 for 60 minutes, ₹239 for 3 hours, or ₹499 for 10 hours. There is no subscription or automatic renewal. Purchased unused reading time does not expire. Reading time is deducted only for eligible delivered reading, not previews, prefetching, or failed content delivery. Public audiobooks are unavailable.</p></section>
    <section><h2 className="font-serif-display text-2xl text-burgundy">Cancellation, refunds and remedies</h2><p className="mt-3">Before any paid entitlement is consumed, you may request cancellation or a refund through support, subject to transaction verification and payment-provider processing. Paid reading time already validly consumed is ordinarily non-refundable for voluntary cancellation, while remaining unused time stays available and does not expire. Verified duplicate or erroneous charges will be remedied. Failed delivery must not consume time; if a technical failure does, Earnalism will restore the incorrectly consumed entitlement where determinable or provide an appropriate remedy. If a title is withdrawn, remaining balance remains usable across other eligible titles. Failed or cancelled payments do not create entitlement. These terms do not limit rights or remedies that cannot lawfully be excluded.</p></section>
    <section><h2 className="font-serif-display text-2xl text-burgundy">Accounts and use</h2><p className="mt-3">Where an account feature is enabled, keep your sign-in details confidential and use the service lawfully. Do not copy, redistribute, scrape, or commercially reuse protected site material or a title beyond any rights that law permits.</p></section>
    <section><h2 className="font-serif-display text-2xl text-burgundy">Support and grievances</h2><p className="mt-3">For support, privacy requests, a rights concern, or a consumer grievance, contact the Grievance Officer, REO ENTERPRISE, at <a className="text-burgundy underline" href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a> or use the <Link className="text-burgundy underline" to="/contact?intent=rights">contact form</Link>.</p></section>
  </LegalPage>;
}

export function Privacy() {
  return <LegalPage title="Privacy" canonicalPath="/privacy" description="How the current Earnalism website handles information used to operate the service.">
    <p>Earnalism is operated by REO ENTERPRISE, Reo Enterprise, Nihar Bhawan, 73, Nandan Nagar, Kolkata - 700083, District - North 24 Parganas, Kolkata - 700083. This notice describes the information used by the current website and reading experience.</p>
    <section><h2 className="font-serif-display text-2xl text-burgundy">Information used to operate the service</h2><p className="mt-3">When you create or use an account, the service may process the name, email address, account identifiers and sign-in information you provide. Reading features may store reading position, session and device-related identifiers needed to operate the reader. Messages sent through the contact form include the name, email address, subject and message you submit.</p></section>
    <section><h2 className="font-serif-display text-2xl text-burgundy">Purpose and service providers</h2><p className="mt-3">We use this information to provide accounts, Reader features, Reading Pass entitlement and accounting, support, grievance handling and service security. The website relies on hosting, database, storage, payment and email-capable service providers to operate these functions. Public audiobooks are not enabled.</p></section>
    <section><h2 className="font-serif-display text-2xl text-burgundy">Browser storage</h2><p className="mt-3">The site uses browser storage for sign-in and requested Reader preferences. Reading position is also handled by the account service. Public homepage data and optional prompts use temporary in-memory state, not persistent browser storage. Optional launch analytics and advertising trackers are not enabled in the current website build. You can clear locally stored data using your browser, although doing so may sign you out or reset preferences.</p></section>
    <section><h2 className="font-serif-display text-2xl text-burgundy">Your requests</h2><p className="mt-3">For a privacy question or request concerning information you provided, contact <a className="text-burgundy underline" href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a> or use the <Link className="text-burgundy underline" to="/contact?intent=reader">contact form</Link>. Please include enough information for us to identify the account or message concerned. We do not publish a fixed retention schedule where none is configured; requests are handled against the information and service records then available.</p></section>
  </LegalPage>;
}

export function CopyrightNotice() {
  return <LegalPage title="Copyright and Content" canonicalPath="/copyright" description="Information about Earnalism content, intellectual property, and rights concerns.">
    <p>Earnalism’s site design, branding and cover artwork are owned or used by REO ENTERPRISE and its licensors. Literary titles are presented only when the applicable title evidence supports the enabled release scope.</p>
    <section><h2 className="font-serif-display text-2xl text-burgundy">Source and edition information</h2><p className="mt-3">A title may follow an identified historical or source edition. Source and edition statements describe that edition; they are not a claim that every edition, translation, annotation, image or adaptation is unrestricted.</p></section>
    <section><h2 className="font-serif-display text-2xl text-burgundy">Copyright concerns</h2><p className="mt-3">To raise a copyright or content concern, email <a className="text-burgundy underline" href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a> or use the <Link className="text-burgundy underline" to="/contact?intent=rights">contact form</Link>. Please identify the work, the Earnalism title or page, your basis for the concern, and contact details. We record, review and, where warranted, temporarily hold the affected title while the concern is assessed.</p></section>
  </LegalPage>;
}
