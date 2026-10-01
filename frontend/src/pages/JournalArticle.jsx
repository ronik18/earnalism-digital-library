import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowUpRight, ChevronLeft } from "lucide-react";
import { api } from "../lib/api";
import { optimizedImageUrl } from "../lib/images";
import JournalDiscussion from "../components/JournalDiscussion";
import ShareButtons from "../components/ShareButtons";
import JsonLd from "../components/JsonLd";
import useSEO from "../hooks/useSEO";
import JournalNewsletter from "../components/JournalNewsletter";
import PublicPageFrame from "../components/PublicPageFrame";
import "../styles/editorial-support.css";
import "../styles/journal-option-b.css";

const articleReadMinutes = (content = "") => Math.max(2, Math.round(String(content).split(/\s+/).filter(Boolean).length / 200));

export default function JournalArticle() {
  const { slug } = useParams();
  const [post, setPost] = useState(null);
  const [related, setRelated] = useState([]);
  const [loading, setLoading] = useState(true);
  const postNotFound = !loading && !post;

  useSEO({
    title: postNotFound
      ? "Article not found — The Earnalism Journal"
      : post ? `${post.title} — The Earnalism Journal` : "Journal — The Earnalism",
    description: postNotFound
      ? "This Earnalism journal article is no longer available."
      : post?.excerpt || "An essay from The Earnalism Journal — notes on literature, business, technology, and the quiet craft of reading.",
    image: post?.cover_image_url,
    imageAlt: post?.title,
    type: "article",
    robots: postNotFound ? "noindex, nofollow" : "index, follow",
    canonicalPath: post ? "/journal/" + post.slug : undefined,
  });

  const articleSchema = post ? {
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": post.title,
    "description": post.excerpt || (post.content || "").slice(0, 220),
    ...(post.cover_image_url ? { "image": [post.cover_image_url] } : {}),
    "datePublished": post.created_at,
    "dateModified": post.updated_at || post.created_at,
    "articleSection": post.category,
    "inLanguage": "en",
    "author": { "@type": "Organization", "name": post.author || "The Earnalism" },
    "publisher": {
      "@type": "Organization",
      "name": "The Earnalism",
      "logo": {
        "@type": "ImageObject",
        "url": "https://theearnalism.com/assets/brand/earnalism-brand-lockup.png",
      },
    },
    "mainEntityOfPage": {
      "@type": "WebPage",
      "@id": `https://theearnalism.com/journal/${post.slug}`,
    },
  } : null;

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    api.get(`/blog/${slug}`, { signal: controller.signal })
      .then((r) => setPost(r.data))
      .catch((err) => {
        if (err.name !== "CanceledError") setPost(null);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    api.get("/blog", { signal: controller.signal })
      .then((r) => setRelated((Array.isArray(r.data) ? r.data : []).filter((p) => p.slug !== slug).slice(0, 3)))
      .catch(() => {});
    return () => controller.abort();
  }, [slug]);

  if (loading) return <PublicPageFrame tone="editorial"><div className="editorial-surface mx-auto my-20 max-w-3xl px-6 py-16 text-center text-charcoal-soft" role="status" data-testid="journal-article-loading">Opening this journal note…</div></PublicPageFrame>;
  if (!post) return (
    <PublicPageFrame tone="editorial"><div className="error-route-panel journal-v2__empty mx-auto my-20 max-w-3xl px-6 py-20 text-center" data-testid="journal-article-not-found">
      <h1>Article not found</h1>
      <p>This note is no longer available. The Journal and Library are still open for discovery.</p>
      <div className="journal-v2__error-actions"><Link to="/journal" data-testid="journal-article-not-found-journal-link">Back to Journal</Link><Link to="/library" data-testid="journal-article-not-found-library-link">Explore the Library <ArrowUpRight size={15} aria-hidden="true" /></Link></div>
    </div></PublicPageFrame>
  );

  return (
    <PublicPageFrame tone="editorial" testId="journal-article"><article>
      {articleSchema && <JsonLd id="article" data={articleSchema} />}
      <div className="journal-v2__article-back">
        <Link to="/journal" className="inline-flex items-center gap-1 text-xs tracking-[0.18em] uppercase text-charcoal-soft hover:text-burgundy" data-testid="back-journal">
          <ChevronLeft size={14} /> Back to Journal
        </Link>
      </div>

      <header className="journal-v2__article-masthead">
      <div>
        <div className="editorial-kicker">{post.category || "Journal"}</div>
        <h1>{post.title}</h1>
        {post.excerpt && <p className="journal-option-b__standfirst">{post.excerpt}</p>}
        <div className="journal-v2__article-metadata">
          <span>By {post.author}</span><span>·</span>
          <span>{new Date(post.created_at).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" })}</span><span>·</span>
          <span>{articleReadMinutes(post.content)} min read</span>
        </div>
        <div className="journal-v2__rule" />
      </div><aside className="journal-option-b__share-rail" aria-label="Share article"><span>Share</span><ShareButtons title={post.title} variant="article" testIdPrefix="article-share" labelled /></aside></header>

      {post.cover_image_url && (
        <div className="journal-option-b__photo-wrap">
          <div className="journal-option-b__cover">
            <img src={optimizedImageUrl(post.cover_image_url, { width: 1200 })} width="1200" height="675" alt={post.cover_image_alt || post.title} decoding="async" fetchPriority="high" className="w-full h-full object-cover" />
          </div>
          {post.image_caption && <p className="journal-option-b__caption">{post.image_caption}</p>}
        </div>
      )}

      <div className="journal-option-b__body">
        <div className="editorial-prose journal-option-b__prose">
          {post.content_html ? <div dangerouslySetInnerHTML={{ __html: post.content_html }} /> : String(post.content || "").split("\n\n").filter(Boolean).map((para, i) => <p key={`${post.slug}-p-${i}`}>{para}</p>)}
        </div>
        {post.pull_quote && (
        <div className="my-12 pull-quote" data-testid="pull-quote">{post.pull_quote}</div>
        )}
        <JournalDiscussion slug={post.slug} />
        <aside className="journal-v2__library-cta" data-testid="article-library-discovery">
          <div><p className="editorial-kicker">Continue with a book</p><h2>Take the thought back to the shelf.</h2><p>Explore the Library for a story to read next.</p></div>
          <Link to="/library" data-testid="article-library-cta">Explore the Library <ArrowUpRight size={16} aria-hidden="true" /></Link>
        </aside>
      </div>

      {related.length > 0 && (
        <section className="journal-v2__related">
          <div className="editorial-kicker">Continue reading</div>
          <h3>Other notes from the journal</h3>
          <div>
            {related.map((r) => (
              <Link key={r.slug} to={`/journal/${r.slug}`}>
                <span>{r.category}</span>
                <h4>{r.title}</h4>
                <span>Read note <ArrowUpRight size={15} aria-hidden="true" /></span>
              </Link>
            ))}
          </div>
        </section>
      )}
    </article><JournalNewsletter /></PublicPageFrame>
  );
}
