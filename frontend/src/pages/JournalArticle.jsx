import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ChevronLeft } from "lucide-react";
import { api } from "../lib/api";

export default function JournalArticle() {
  const { slug } = useParams();
  const [post, setPost] = useState(null);
  const [related, setRelated] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get(`/blog/${slug}`).then((r) => setPost(r.data)).catch(() => setPost(null)).finally(() => setLoading(false));
    api.get("/blog").then((r) => setRelated(r.data.filter((p) => p.slug !== slug).slice(0, 3))).catch(() => {});
  }, [slug]);

  if (loading) return <div className="py-32 text-center text-charcoal-soft">Loading…</div>;
  if (!post) return (
    <div className="max-w-3xl mx-auto px-6 py-32 text-center">
      <h1 className="font-serif-display text-4xl text-burgundy">Article not found</h1>
      <Link to="/journal" className="btn-secondary mt-6">Back to Journal</Link>
    </div>
  );

  return (
    <article data-testid="journal-article">
      <div className="max-w-3xl mx-auto px-5 sm:px-8 pt-12">
        <Link to="/journal" className="inline-flex items-center gap-1 text-xs tracking-[0.18em] uppercase text-charcoal-soft hover:text-burgundy" data-testid="back-journal">
          <ChevronLeft size={14} /> Back to Journal
        </Link>
      </div>

      <header className="max-w-3xl mx-auto px-5 sm:px-8 pt-8 pb-10">
        <div className="overline mb-4">{post.category}</div>
        <h1 className="font-serif-display text-4xl sm:text-5xl lg:text-6xl text-burgundy leading-[1.05] tracking-tight text-balance">{post.title}</h1>
        <div className="mt-6 flex items-center gap-4 text-sm text-charcoal-soft">
          <span>{post.author}</span><span>·</span>
          <span>{new Date(post.created_at).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" })}</span>
        </div>
      </header>

      {post.cover_image_url && (
        <div className="max-w-5xl mx-auto px-5 sm:px-8">
          <div className="aspect-[16/9] overflow-hidden rounded-2xl border border-brand">
            <img src={post.cover_image_url} alt={post.title} className="w-full h-full object-cover" />
          </div>
        </div>
      )}

      <div className="max-w-2xl mx-auto px-5 sm:px-8 py-12 sm:py-16">
        <div className="font-serif-display text-lg sm:text-xl leading-[1.75] text-charcoal drop-cap">
          {post.content.split("\n\n").map((para, i) => (
            <p key={i} className={i === 0 ? "" : "mt-6"}>{para}</p>
          ))}
        </div>
        {post.pull_quote && (
          <div className="my-12 pull-quote" data-testid="pull-quote">{post.pull_quote}</div>
        )}
      </div>

      {related.length > 0 && (
        <section className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-16 border-t border-brand">
          <div className="overline mb-3">Continue reading</div>
          <h3 className="font-serif-display text-3xl text-burgundy mb-8">Other notes from the journal</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {related.map((r) => (
              <Link key={r.slug} to={`/journal/${r.slug}`} className="card-elegant p-6">
                <div className="overline mb-2">{r.category}</div>
                <h4 className="font-serif-display text-xl text-burgundy leading-snug">{r.title}</h4>
              </Link>
            ))}
          </div>
        </section>
      )}
    </article>
  );
}
