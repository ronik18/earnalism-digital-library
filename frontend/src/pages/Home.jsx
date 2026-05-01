import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, BookOpen, Sparkles, Compass } from "lucide-react";
import { toast } from "sonner";
import { api, formatError } from "../lib/api";

const HERO_IMG = "https://images.unsplash.com/photo-1739918075668-fc7844c6d921?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzNTl8MHwxfHNlYXJjaHwyfHxsdXh1cnklMjBsaWJyYXJ5JTIwaW50ZXJpb3IlMjB3YXJtJTIwbGlnaHRpbmd8ZW58MHx8fHwxNzc3NjE3MTkwfDA&ixlib=rb-4.1.0&q=85";
const FOUNDER_IMG = "https://images.unsplash.com/photo-1773067752075-2cfd37ab02dd?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1ODB8MHwxfHNlYXJjaHw0fHxsdXh1cnklMjBmb3VudGFpbiUyMHBlbiUyMHdyaXRpbmclMjBkZXNrfGVufDB8fHx8MTc3NzYxNzE3N3ww&ixlib=rb-4.1.0&q=85";

export default function Home() {
  const [categories, setCategories] = useState([]);
  const [featured, setFeatured] = useState(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.get("/categories").then((r) => setCategories(r.data)).catch(() => {});
    api.get("/featured").then((r) => setFeatured(r.data?.book)).catch(() => {});
  }, []);

  const subscribe = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const { data } = await api.post("/newsletter", { name, email });
      toast.success(data.message || "Welcome to the Reading Circle.");
      setName(""); setEmail("");
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail));
    } finally { setSubmitting(false); }
  };

  return (
    <div data-testid="home-page">
      {/* HERO */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 -z-10">
          <img src={HERO_IMG} alt="" loading="eager" className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-b from-[#1a0a0e]/85 via-[#2a1218]/70 to-[#F4EFEA] " />
        </div>
        <div className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 pt-24 sm:pt-36 pb-32 sm:pb-44">
          <div className="max-w-3xl">
            <div className="overline text-[var(--brand-gold-soft)] mb-6" data-testid="hero-overline">A Boutique Bookstore & Publishing House</div>
            <h1 className="font-serif-display text-4xl sm:text-6xl lg:text-7xl leading-[1.05] text-[#FDFCF8] tracking-tight text-balance" data-testid="hero-headline">
              Books for Those Who Read With Depth.
            </h1>
            <p className="mt-7 text-base sm:text-lg text-[#F4EFEA]/85 max-w-xl leading-relaxed">
              Curated titles in business, self-growth, literature, spirituality, and Bengali reading — chosen for readers who value depth, beauty, and meaning.
            </p>
            <div className="mt-10 flex flex-wrap gap-3 sm:gap-4">
              <Link to="/shop" className="btn-primary" data-testid="hero-cta-explore">Explore the Collection</Link>
              <Link to={featured ? `/shop/${featured.slug}` : "/shop"} className="btn-secondary !text-[#FDFCF8] !border-[var(--brand-gold)] hover:!bg-[var(--brand-gold)]/15" data-testid="hero-cta-featured">Start With Our Featured Book</Link>
            </div>
          </div>
        </div>
      </section>

      {/* CATEGORIES */}
      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-20 sm:py-28" id="collection">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-6 mb-12 sm:mb-16">
          <div>
            <div className="overline mb-3">The Shelves</div>
            <h2 className="font-serif-display text-4xl sm:text-5xl text-burgundy tracking-tight">A small library, carefully kept.</h2>
          </div>
          <Link to="/shop" className="btn-link" data-testid="categories-view-all">View the full collection <ArrowRight size={14} /></Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 sm:gap-7">
          {categories.map((c, i) => (
            <Link
              key={c.slug}
              to={`/shop?category=${c.slug}`}
              className={`card-elegant overflow-hidden group ${i === 0 ? "lg:col-span-2 lg:row-span-2" : ""}`}
              data-testid={`category-card-${c.slug}`}
            >
              <div className={`relative ${i === 0 ? "aspect-[16/10] lg:aspect-[16/12]" : "aspect-[4/3]"} overflow-hidden`}>
                {c.image_url && (
                  <img src={c.image_url} alt={c.name} loading="lazy" className="w-full h-full object-cover transition-transform [transition-duration:1200ms] group-hover:scale-[1.06]" />
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-[#2a1218]/65 via-transparent to-transparent" />
                <div className="absolute bottom-0 left-0 right-0 p-6 sm:p-7">
                  <h3 className={`font-serif-display text-[#FDFCF8] ${i === 0 ? "text-3xl sm:text-4xl" : "text-2xl"} mb-1`}>{c.name}</h3>
                  <p className="text-[#F4EFEA]/85 text-sm leading-relaxed max-w-md">{c.description}</p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* FEATURED BOOK */}
      {featured && (
        <section className="bg-ivory border-y border-brand">
          <div className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-20 sm:py-28 grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
            <div className="lg:col-span-5">
              <div className="aspect-[3/4] rounded-2xl overflow-hidden border border-brand shadow-[0_30px_60px_-30px_rgba(74,28,39,0.35)]">
                <img src={featured.cover_image_url} alt={featured.title} loading="lazy" className="w-full h-full object-cover" />
              </div>
            </div>
            <div className="lg:col-span-7">
              <div className="overline mb-4">Currently Featured</div>
              <h2 className="font-serif-display text-4xl sm:text-5xl text-burgundy leading-[1.1] tracking-tight">{featured.title}</h2>
              <p className="font-serif-display italic text-xl sm:text-2xl text-charcoal-soft mt-3">{featured.subtitle}</p>
              <p className="text-charcoal-soft mt-6 leading-relaxed max-w-2xl">{featured.description}</p>
              <div className="mt-8 flex flex-wrap gap-3 sm:gap-4">
                <Link to={`/shop/${featured.slug}`} className="btn-secondary" data-testid="featured-view">View Book</Link>
                {featured.buy_url ? (
                  <a href={featured.buy_url} target="_blank" rel="noreferrer" className="btn-primary" data-testid="featured-buy">Buy Now</a>
                ) : (
                  <Link to="/contact" className="btn-primary" data-testid="featured-request">Request Purchase Info</Link>
                )}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* WHY EARNALISM */}
      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-20 sm:py-28">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <div className="overline mb-3">Why The Earnalism</div>
          <h2 className="font-serif-display text-4xl sm:text-5xl text-burgundy tracking-tight">A bookstore for readers who linger.</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8">
          {[
            { icon: Sparkles, title: "Curated With Meaning", body: "Every shelf is a slow act of selection. We choose books we would lend to a close friend — and never apologise for the smaller list." },
            { icon: BookOpen, title: "Built for Thoughtful Readers", body: "Our writing, design, and packaging assume a patient reader. Margins to think in. Typography to return to. A pace that respects you." },
            { icon: Compass, title: "From Reading to Enterprise", body: "We publish founder-grade books and help authors release with grace — manuscripts, covers, KDP-ready files, and launches that endure." },
          ].map((c) => (
            <div key={c.title} className="card-elegant p-8 sm:p-10" data-testid={`why-card-${c.title.toLowerCase().replace(/\s/g, '-')}`}>
              <c.icon className="text-gold" size={28} />
              <div className="gold-rule mt-5 mb-6" />
              <h3 className="font-serif-display text-2xl text-burgundy mb-3">{c.title}</h3>
              <p className="text-charcoal-soft leading-relaxed">{c.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* FOUNDER NOTE */}
      <section className="bg-ivory border-y border-brand">
        <div className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-20 sm:py-28 grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-5 order-2 lg:order-1">
            <div className="aspect-[4/5] rounded-2xl overflow-hidden border border-brand">
              <img src={FOUNDER_IMG} alt="" loading="lazy" className="w-full h-full object-cover" />
            </div>
          </div>
          <div className="lg:col-span-7 order-1 lg:order-2">
            <div className="overline mb-4">A Founder's Note</div>
            <h2 className="font-serif-display text-4xl sm:text-5xl text-burgundy leading-[1.1] tracking-tight">A Bookstore for the Reader Who Still Believes in Depth.</h2>
            <p className="text-charcoal-soft mt-7 leading-relaxed text-base sm:text-lg max-w-2xl">
              The Earnalism began as a quiet rebellion against noisy bookshelves. We believe a book is a long conversation — patient, particular, and worth the careful season it takes to write. As a reading destination and a publishing house, we keep the list small and the standard generous. Every title here, whether ours or curated, is chosen for one reader: the one who still believes that meaning compounds, slowly, across the right pages.
            </p>
            <div className="gold-rule mt-8" />
          </div>
        </div>
      </section>

      {/* NEWSLETTER */}
      <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-20 sm:py-28">
        <div className="card-elegant p-8 sm:p-14 lg:p-20 text-center max-w-3xl mx-auto" data-testid="newsletter-card">
          <div className="overline mb-3">The Reading Circle</div>
          <h2 className="font-serif-display text-3xl sm:text-5xl text-burgundy tracking-tight">Join the Earnalism Reading Circle</h2>
          <p className="text-charcoal-soft mt-4 max-w-xl mx-auto leading-relaxed">
            Receive thoughtful book notes, publishing updates, and curated reading recommendations — written with the care of a private letter.
          </p>
          <form onSubmit={subscribe} className="mt-10 grid grid-cols-1 sm:grid-cols-2 gap-5 max-w-xl mx-auto text-left">
            <input
              required value={name} onChange={(e) => setName(e.target.value)}
              placeholder="Your name" className="input-elegant" data-testid="newsletter-name"
            />
            <input
              required type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              placeholder="Your email" className="input-elegant" data-testid="newsletter-email"
            />
            <div className="sm:col-span-2 flex justify-center mt-4">
              <button disabled={submitting} type="submit" className="btn-primary disabled:opacity-60" data-testid="newsletter-submit">
                {submitting ? "Joining…" : "Join the Circle"}
              </button>
            </div>
          </form>
        </div>
      </section>
    </div>
  );
}
