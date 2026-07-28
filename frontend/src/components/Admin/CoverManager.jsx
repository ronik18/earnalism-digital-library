import { useCallback, useEffect, useMemo, useState } from "react";
import { RefreshCw, Search } from "lucide-react";
import { toast } from "sonner";
import { api, formatError } from "../../lib/api";
import CoverUpload from "./CoverUpload";

const FILTERS = [
  ["needs-attention", "Needs attention"],
  ["missing", "Missing"],
  ["pending", "Uploaded, pending review"],
  ["mismatch", "Mismatched"],
  ["complete", "Canonical pair ready"],
  ["all", "All Sprint 1"],
];

const STATUS_LABELS = {
  CANONICAL_READY: "Canonical ready",
  MISSING: "Missing",
  MISMATCH_REVIEW_REQUIRED: "Mismatched",
  UPLOADED_PENDING_CANONICAL_REVIEW: "Uploaded · review pending",
};

function matchesFilter(book, filter) {
  const statuses = [book.front_status, book.back_status];
  if (filter === "all") return true;
  if (filter === "complete") return book.cover_status === "COMPLETE";
  if (filter === "needs-attention") return book.cover_status !== "COMPLETE";
  if (filter === "missing") return statuses.includes("MISSING");
  if (filter === "pending") return statuses.includes("UPLOADED_PENDING_CANONICAL_REVIEW");
  if (filter === "mismatch") return statuses.includes("MISMATCH_REVIEW_REQUIRED");
  return true;
}

function statusTone(status) {
  if (status === "CANONICAL_READY") return "bg-emerald-100 text-emerald-800";
  if (status === "UPLOADED_PENDING_CANONICAL_REVIEW") return "bg-sky-100 text-sky-800";
  return "bg-amber-100 text-amber-900";
}

function CoverStatus({ label, status }) {
  return (
    <div className="flex items-center justify-between gap-3 text-xs">
      <span className="text-charcoal-soft">{label}</span>
      <span className={`rounded-full px-2 py-1 text-[0.58rem] uppercase tracking-[0.14em] ${statusTone(status)}`}>
        {STATUS_LABELS[status] || status}
      </span>
    </div>
  );
}

export default function CoverManager() {
  const [books, setBooks] = useState([]);
  const [source, setSource] = useState({});
  const [summary, setSummary] = useState({});
  const [filter, setFilter] = useState("needs-attention");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get("/admin/books/cover-status");
      setBooks(Array.isArray(data?.books) ? data.books : []);
      setSource(data?.source || {});
      setSummary(data?.summary || {});
    } catch (err) {
      const message = formatError(err.response?.data?.detail) || "Cover inventory could not be loaded.";
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const visibleBooks = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    return books.filter((book) => {
      if (!matchesFilter(book, filter)) return false;
      if (!needle) return true;
      return [book.title, book.author, book.slug]
        .some((value) => String(value || "").toLocaleLowerCase().includes(needle));
    });
  }, [books, filter, query]);

  const applyUpload = useCallback((slug, kind, data) => {
    const statusField = kind === "back" ? "back_status" : "front_status";
    const adminUrlField = kind === "back" ? "admin_back_cover_url" : "admin_front_cover_url";
    const displayUrlField = kind === "back" ? "back_display_url" : "front_display_url";
    setBooks((current) => current.map((book) => (
      book.slug === slug
        ? {
          ...book,
          [statusField]: "UPLOADED_PENDING_CANONICAL_REVIEW",
          [adminUrlField]: data.cover_url,
          [displayUrlField]: data.cover_url,
          cover_status: "NEEDS_ATTENTION",
        }
        : book
    )));
  }, []);

  return (
    <section className="space-y-6" data-testid="admin-cover-manager" aria-labelledby="admin-cover-manager-title">
      <div className="card-elegant p-6 sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="overline">Canonical cover desk</div>
            <h2 id="admin-cover-manager-title" className="mt-1 font-serif-display text-2xl text-burgundy">
              Sprint 1 cover inventory
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-relaxed text-charcoal-soft">
              Upload finished front and back cover art to the private admin record. New files stay marked for canonical review; this screen cannot change reader availability or audiobook release state.
            </p>
          </div>
          <button type="button" onClick={load} disabled={loading} className="btn-secondary min-h-11 disabled:opacity-60" data-testid="cover-inventory-refresh">
            <RefreshCw size={14} className={`mr-2 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            ["Sprint 1", summary.books_total || source.active_count || 0],
            ["Canonical pairs", summary.books_complete || 0],
            ["Need attention", summary.books_needing_attention || 0],
            ["Uploads", source.admin_cover_uploads_enabled && source.cloudinary_configured ? "Ready" : "Unavailable"],
          ].map(([label, value]) => (
            <div key={label} className="rounded-lg border border-brand-soft bg-white/55 p-4">
              <div className="text-[0.62rem] uppercase tracking-[0.18em] text-charcoal-soft">{label}</div>
              <div className="mt-1 font-serif-display text-2xl text-burgundy">{value}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="card-elegant p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap gap-2" role="group" aria-label="Filter cover inventory">
            {FILTERS.map(([value, label]) => (
              <button
                key={value}
                type="button"
                onClick={() => setFilter(value)}
                aria-pressed={filter === value}
                className={`min-h-11 rounded-full px-3 py-2 text-[0.62rem] uppercase tracking-[0.16em] ${
                  filter === value
                    ? "bg-burgundy text-[var(--brand-ivory)]"
                    : "border border-brand-soft text-charcoal-soft hover:text-burgundy"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <label className="relative block w-full lg:max-w-sm">
            <span className="sr-only">Search books by title, author, or slug</span>
            <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-charcoal-soft" aria-hidden="true" />
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="input-elegant pl-10"
              placeholder="Search title, author, or slug"
              data-testid="cover-inventory-search"
            />
          </label>
        </div>
      </div>

      {error ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-900" role="alert">{error}</div>
      ) : loading ? (
        <div className="card-elegant p-8 text-sm text-charcoal-soft">Loading canonical cover truth…</div>
      ) : visibleBooks.length === 0 ? (
        <div className="card-elegant p-8 text-sm text-charcoal-soft">No books match this cover filter.</div>
      ) : (
        <div className="grid grid-cols-1 gap-5 xl:grid-cols-2" data-testid="cover-inventory-list">
          {visibleBooks.map((book) => {
            const uploadReady = Boolean(
              book.can_upload
              && source.admin_cover_uploads_enabled
              && source.cloudinary_configured
            );
            return (
              <article key={book.slug} className="card-elegant p-5 sm:p-6" data-testid={`cover-record-${book.slug}`}>
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="overline">{book.language || "Classic"} · {book.slug}</div>
                    <h3 className="mt-1 font-serif-display text-xl leading-snug text-burgundy">{book.title}</h3>
                    <p className="mt-1 text-sm text-charcoal-soft">{book.author || "Author unavailable"}</p>
                  </div>
                  <span className={`rounded-full px-2.5 py-1 text-[0.6rem] uppercase tracking-[0.16em] ${
                    book.cover_status === "COMPLETE"
                      ? "bg-emerald-100 text-emerald-800"
                      : "bg-amber-100 text-amber-900"
                  }`}>
                    {book.cover_status === "COMPLETE" ? "Pair ready" : "Needs attention"}
                  </span>
                </div>

                <div className="mt-4 space-y-2">
                  <CoverStatus label="Front cover" status={book.front_status} />
                  <CoverStatus label="Back cover" status={book.back_status} />
                </div>

                {book.canonical_exclusion_reason ? (
                  <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs leading-relaxed text-amber-900">
                    {book.canonical_exclusion_reason}
                  </p>
                ) : null}

                {uploadReady ? (
                  <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
                    <CoverUpload
                      bookId={book.slug}
                      kind="front"
                      currentUrl={book.front_display_url}
                      bookTitle={book.title}
                      bookAuthor={book.author}
                      onSuccess={(data) => {
                        applyUpload(book.slug, "front", data);
                        toast.success(`Front cover uploaded for ${book.title}`);
                      }}
                    />
                    <CoverUpload
                      bookId={book.slug}
                      kind="back"
                      currentUrl={book.back_display_url}
                      bookTitle={book.title}
                      bookAuthor={book.author}
                      onSuccess={(data) => {
                        applyUpload(book.slug, "back", data);
                        toast.success(`Back cover uploaded for ${book.title}`);
                      }}
                    />
                  </div>
                ) : (
                  <div className="mt-5 rounded-lg border border-brand-soft bg-ivory-warm/60 p-4 text-xs leading-relaxed text-charcoal-soft">
                    {!book.admin_book_exists
                      ? "Create or import the admin book record before uploading its covers."
                      : "Cloudinary-backed cover uploads are unavailable in the current backend runtime."}
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
