import { useEffect, useMemo, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api, formatError, formatMinutes } from "../lib/api";
import { toast } from "sonner";
import { LogOut, Plus, Trash2, Edit3, Star, X, KeyRound, Share2, Mail, Clock, Ban, Check, ShieldAlert } from "lucide-react";
import { useSettings } from "../context/SettingsContext";
import BrandMark from "../components/BrandMark";
import ChapterUpload from "../components/Admin/ChapterUpload";
import CoverUpload from "../components/Admin/CoverUpload";

const TABS = ["books", "blog", "categories", "newsletter", "contacts", "users", "payments", "security", "settings", "account"];

export default function Admin() {
  const { admin, logout } = useAuth();
  const [tab, setTab] = useState("books");

  if (admin === null) return <div className="py-32 text-center text-charcoal-soft">Loading…</div>;
  if (!admin) return <Navigate to="/admin/login" replace />;

  return (
    <div className="min-h-screen bg-beige" data-testid="admin-page">
      <div className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-10">
        <div className="flex items-center justify-between flex-wrap gap-4 mb-8">
          <div>
            <div className="mb-2 leading-none"><BrandMark variant="compact" /></div>
            <div className="overline">Admin Dashboard</div>
            <p className="text-sm text-charcoal-soft mt-1">{admin.email}</p>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/" className="btn-link" data-testid="admin-view-site">View site</Link>
            <button onClick={logout} className="btn-secondary" data-testid="admin-logout"><LogOut size={14} className="mr-2" /> Sign out</button>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 border-y border-brand py-3 mb-8" data-testid="admin-tabs">
          {TABS.map((t) => (
            <button key={t} onClick={() => setTab(t)} data-testid={`admin-tab-${t}`}
              className={`px-4 py-2 rounded-full text-xs tracking-[0.18em] uppercase ${tab === t ? "bg-burgundy text-[var(--brand-ivory)]" : "text-charcoal-soft hover:text-burgundy"}`}>
              {t}
            </button>
          ))}
        </div>

        {tab === "books" && <BooksAdmin />}
        {tab === "blog" && <BlogAdmin />}
        {tab === "categories" && <CategoriesAdmin />}
        {tab === "newsletter" && <SimpleList endpoint="/admin/newsletter" testid="admin-newsletter" cols={["name", "email", "created_at"]} title="Reading Circle" />}
        {tab === "contacts" && <ContactsAdmin />}
        {tab === "users" && <UsersAdmin />}
        {tab === "payments" && <PaymentsAdmin />}
        {tab === "security" && <SecurityAlertsAdmin />}
        {tab === "settings" && <SettingsTab />}
        {tab === "account" && <AccountTab />}
      </div>
    </div>
  );
}

function SimpleList({ endpoint, cols, title, testid }) {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.get(endpoint).then((r) => setRows(r.data)).catch(() => {}); }, [endpoint]);
  return (
    <div className="card-elegant p-6 sm:p-8 overflow-x-auto" data-testid={testid}>
      <h2 className="font-serif-display text-2xl text-burgundy mb-5">{title} ({rows.length})</h2>
      {rows.length === 0 ? <p className="text-charcoal-soft">No entries yet.</p> : (
        <table className="w-full text-sm">
          <thead><tr className="text-left text-xs uppercase tracking-wider text-charcoal-soft border-b border-brand">{cols.map((c) => <th key={c} className="py-3 pr-4">{c.replace(/_/g, ' ')}</th>)}</tr></thead>
          <tbody>{rows.map((r, i) => (
            <tr key={r.id || r.email || `row-${i}`} className="border-b border-brand/60">
              {cols.map((c) => <td key={c} className="py-3 pr-4 align-top max-w-xs">{c === "created_at" ? new Date(r[c]).toLocaleString() : (r[c] || "—")}</td>)}
            </tr>
          ))}</tbody>
        </table>
      )}
    </div>
  );
}

function SecurityAlertsAdmin() {
  const [summary, setSummary] = useState({ events: 0, sessions: 0, high_risk_sessions: 0 });
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/admin/secure-reader/alerts");
      setSummary(data.summary || {});
      setAlerts(data.alerts || []);
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="space-y-6" data-testid="admin-security-alerts">
      <div className="card-elegant p-6 sm:p-8">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="overline flex items-center gap-2"><ShieldAlert size={14} /> Reader protection</div>
            <h2 className="font-serif-display text-2xl text-burgundy mt-1">Security alerts</h2>
            <p className="text-sm text-charcoal-soft mt-2 max-w-2xl">
              Shows repeated blocked copy, print, right-click, drag, and screenshot-key attempts from the secure reader.
            </p>
          </div>
          <button onClick={load} className="btn-link text-xs" data-testid="security-refresh">Refresh</button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-6">
          {[
            ["Events", summary.events || 0],
            ["Sessions", summary.sessions || 0],
            ["High risk", summary.high_risk_sessions || 0],
          ].map(([label, value]) => (
            <div key={label} className="rounded-lg border border-brand-soft bg-white/55 p-4">
              <div className="text-[0.65rem] uppercase tracking-[0.18em] text-charcoal-soft">{label}</div>
              <div className="font-serif-display text-3xl text-burgundy mt-1">{value}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="card-elegant p-6 sm:p-8 overflow-x-auto">
        {loading ? <p className="text-charcoal-soft text-sm">Loading…</p> : alerts.length === 0 ? (
          <p className="text-charcoal-soft text-sm">No reader protection alerts yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wider text-charcoal-soft border-b border-brand">
                <th className="py-3 pr-4">Latest</th>
                <th className="py-3 pr-4">Reader</th>
                <th className="py-3 pr-4">Book</th>
                <th className="py-3 pr-4">Attempts</th>
                <th className="py-3 pr-4">Events</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((alert) => (
                <tr key={alert.session_id} className="border-b border-brand/60">
                  <td className="py-3 pr-4 text-charcoal-soft text-xs whitespace-nowrap">{alert.latest_at ? new Date(alert.latest_at).toLocaleString() : "—"}</td>
                  <td className="py-3 pr-4 text-charcoal-soft">{alert.user_email || "Guest"}</td>
                  <td className="py-3 pr-4">
                    <div className="font-serif-display text-burgundy">{alert.book_slug || "—"}</div>
                    <div className="text-xs text-charcoal-soft">{alert.chapter_id || "—"}</div>
                  </td>
                  <td className="py-3 pr-4">
                    <span className={`text-[0.65rem] tracking-[0.2em] uppercase px-2 py-0.5 rounded-full ${alert.total_attempts >= 3 ? "bg-rose-100 text-rose-800" : "bg-amber-100 text-amber-800"}`}>
                      {alert.total_attempts}
                    </span>
                  </td>
                  <td className="py-3 pr-4 text-xs text-charcoal-soft">
                    {Object.entries(alert.events || {}).map(([key, value]) => `${key}: ${value}`).join(", ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

const EMPTY_BOOK = { title: "", subtitle: "", author: "The Earnalism", category_slug: "business", short_description: "", description: "", cover_image_url: "", back_cover_image_url: "", estimated_reading_time: "", price_paperback: "", price_ebook: "", buy_url: "", formats: ["Ebook"], benefits: [], who_for: [], learnings: [], about_author: "", is_published: false };

function BooksAdmin() {
  const [books, setBooks] = useState([]);
  const [cats, setCats] = useState([]);
  const [editing, setEditing] = useState(null);
  const [featured, setFeatured] = useState("");

  const load = async () => {
    const [b, c, f] = await Promise.all([api.get("/admin/books"), api.get("/categories"), api.get("/featured")]);
    setBooks(b.data); setCats(c.data); setFeatured(f.data?.book?.slug || "");
  };
  useEffect(() => { load(); }, []);

  const save = async (form, originalSlug) => {
    try {
      const payload = { ...form, benefits: arr(form.benefits), who_for: arr(form.who_for), learnings: arr(form.learnings), formats: arr(form.formats) };
      if (originalSlug) await api.put(`/admin/books/${originalSlug}`, payload);
      else await api.post("/admin/books", payload);
      toast.success("Saved"); setEditing(null); await load();
    } catch (err) { toast.error(formatError(err.response?.data?.detail)); }
  };

  const del = async (slug) => {
    if (!window.confirm("Delete this book?")) return;
    await api.delete(`/admin/books/${slug}`); toast.success("Deleted"); load();
  };

  const setFeat = async (slug) => {
    await api.put("/admin/featured", { book_slug: slug });
    setFeatured(slug); toast.success("Featured updated");
  };

  return (
    <div data-testid="books-admin">
      <div className="flex items-center justify-between mb-5">
        <h2 className="font-serif-display text-2xl text-burgundy">Books ({books.length})</h2>
        <div className="flex flex-wrap gap-2">
          <button onClick={() => setEditing({ ...EMPTY_BOOK, _new: true })} className="btn-secondary" data-testid="add-book"><Plus size={14} className="mr-2" /> New book</button>
          <button onClick={() => setEditing({ ...EMPTY_BOOK, _new: true, _uploadFirst: true })} className="btn-primary" data-testid="upload-book-docx">Upload Book (.DOCX)</button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {books.map((b) => (
          <div key={b.slug} className="card-elegant p-5 flex gap-4" data-testid={`admin-book-${b.slug}`}>
            <div className="w-20 h-28 bg-beige rounded-md overflow-hidden flex-shrink-0">
              {b.cover_image_url && <img src={b.cover_image_url} alt={b.title} className="w-full h-full object-cover" />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="overline">{b.category_slug}</div>
              <h3 className="font-serif-display text-xl text-burgundy leading-snug">{b.title}</h3>
              <div className="mt-1">
                <span className={`rounded-full px-2 py-0.5 text-[0.62rem] uppercase tracking-[0.18em] ${b.is_published ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
                  {b.is_published ? "Published" : "Draft"}
                </span>
              </div>
              <p className="text-xs text-charcoal-soft mt-1 truncate">{b.short_description}</p>
              <div className="text-xs text-charcoal-soft mt-1">Buy URL: {b.buy_url ? "set" : <span className="text-burgundy">empty</span>}</div>
              <div className="flex items-center gap-2 mt-3 flex-wrap">
                <button onClick={() => setEditing({ ...b })} className="text-xs uppercase tracking-wider text-burgundy hover:underline" data-testid={`edit-${b.slug}`}><Edit3 size={12} className="inline mr-1" /> Edit</button>
                <button onClick={() => del(b.slug)} className="text-xs uppercase tracking-wider text-charcoal-soft hover:text-burgundy" data-testid={`delete-${b.slug}`}><Trash2 size={12} className="inline mr-1" /> Delete</button>
                <button onClick={() => setFeat(b.slug)} className={`text-xs uppercase tracking-wider ml-auto ${featured === b.slug ? "text-gold" : "text-charcoal-soft hover:text-burgundy"}`} data-testid={`feature-${b.slug}`}>
                  <Star size={12} className="inline mr-1" />{featured === b.slug ? "Featured" : "Feature"}
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {editing && <BookEditor book={editing} cats={cats} onClose={() => setEditing(null)} onSave={save} />}
    </div>
  );
}

const arr = (v) => Array.isArray(v) ? v : (v || "").split("\n").map((x) => x.trim()).filter(Boolean);
const lines = (v) => Array.isArray(v) ? v.join("\n") : (v || "");
const BENGALI_RE = /[\u0980-\u09FF]/;
const BENGALI_SERIF = "'Noto Serif Bengali', 'Crimson Pro', Georgia, serif";
const ADMIN_SERIF = "'Crimson Pro', 'Noto Serif Bengali', Georgia, serif";

const containsBengaliText = (value) => BENGALI_RE.test(value || "");
const hasHtmlTags = (value) => /<\/?[a-z][\s\S]*>/i.test(value || "");

const processingStatus = (item) => item?.processing_status || "ready";
const blockingChapterStatuses = new Set(["uploaded", "processing", "failed"]);

function publishIssues(book) {
  const issues = [];
  if (!String(book?.title || "").trim()) issues.push("Title is required.");
  if (!book?.is_published) return issues;
  if (!book.cover_image_url) issues.push("Front cover is required before publishing.");
  (book.chapters || []).forEach((chapter) => {
    const status = processingStatus(chapter);
    if (blockingChapterStatuses.has(status)) {
      issues.push(`${chapter.title || "Untitled chapter"} is ${status}.`);
    }
  });
  return issues;
}

function sanitizePreviewHtml(value) {
  if (typeof document === "undefined") return "";
  const template = document.createElement("template");
  template.innerHTML = value || "";
  template.content.querySelectorAll("script,style,iframe,object,embed").forEach((node) => node.remove());
  template.content.querySelectorAll("*").forEach((node) => {
    Array.from(node.attributes).forEach((attr) => {
      if (/^on/i.test(attr.name)) node.removeAttribute(attr.name);
    });
  });
  return template.innerHTML;
}

function ProcessingBadge({ status }) {
  const normalized = status || "ready";
  const styles = normalized === "ready"
    ? "bg-emerald-100 text-emerald-800"
    : normalized === "failed"
      ? "bg-rose-100 text-rose-800"
      : "bg-amber-100 text-amber-800";
  return (
    <span className={`rounded-full px-2 py-0.5 text-[0.62rem] uppercase tracking-[0.18em] ${styles}`}>
      {normalized}
    </span>
  );
}

function BookEditor({ book, cats, onClose, onSave }) {
  const [f, setF] = useState({
    ...book,
    benefits: lines(book.benefits), who_for: lines(book.who_for), learnings: lines(book.learnings), formats: lines(book.formats || ["Paperback", "Ebook"]),
  });
  const [docxTemplate, setDocxTemplate] = useState(null);
  const [frontCoverFile, setFrontCoverFile] = useState(null);
  const [backCoverFile, setBackCoverFile] = useState(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [importStage, setImportStage] = useState("");
  const [importProgress, setImportProgress] = useState(0);
  const [creditReport, setCreditReport] = useState(null);
  const isNew = book._new;
  const issues = publishIssues(f);
  const saveBlocked = f.is_published && issues.length > 0;

  const importTemplate = async () => {
    if (!docxTemplate) {
      toast.error("Choose a DOCX manuscript first.");
      return;
    }
    setImporting(true);
    setImportStage("upload");
    setImportProgress(8);
    setImportResult(null);
    setCreditReport(null);
    try {
      const fd = new FormData();
      fd.append("docx_file", docxTemplate);
      if (frontCoverFile) fd.append("front_cover", frontCoverFile);
      if (backCoverFile) fd.append("back_cover", backCoverFile);
      const { data } = await api.post("/upload_docx", fd, {
        onUploadProgress: (event) => {
          if (!event.total) return;
          const pct = Math.min(45, Math.round((event.loaded / event.total) * 45));
          setImportProgress(pct);
        },
      });
      setImportStage("validation");
      setImportProgress(70);
      const imported = data.book || {};
      const categorySlug = cats.some((c) => c.slug === imported.category_slug) ? imported.category_slug : f.category_slug;
      setF((prev) => ({
        ...prev,
        ...imported,
        category_slug: categorySlug,
        benefits: lines(imported.benefits || []),
        who_for: lines(imported.who_for || []),
        learnings: lines(imported.learnings || []),
        formats: lines(imported.formats || prev.formats || ["Ebook"]),
        is_published: false,
      }));
      setImportResult(data);
      setImportStage("auto-fill");
      setImportProgress(92);
      if (data.credit_report?.user_id) {
        try {
          const report = await api.get(`/credits/report?user_id=${encodeURIComponent(data.credit_report.user_id)}`);
          setCreditReport(report.data);
        } catch {
          setCreditReport(null);
        }
      }
      setImportProgress(100);
      toast.success("DOCX validated. Review before saving.");
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail));
    } finally {
      setImporting(false);
      setImportStage("");
    }
  };

  const printValidationSummary = () => {
    if (!importResult?.validation_summary) return;
    const popup = window.open("", "_blank", "width=900,height=700");
    if (!popup) return;
    const summary = importResult.validation_summary;
    const checks = summary.checks || [];
    popup.document.write(`
      <html>
        <head>
          <title>${summary.title}</title>
          <style>
            body{font-family:Inter,Arial,sans-serif;color:#2C2C2C;padding:32px;line-height:1.6}
            h1{font-family:Georgia,serif;color:#4A1C27}
            table{width:100%;border-collapse:collapse;margin-top:20px}
            th,td{border-bottom:1px solid #E5DCD3;padding:10px;text-align:left;vertical-align:top}
            .status{font-weight:700;color:#4A1C27}
            footer{margin-top:28px;color:#6A655F;font-size:13px}
          </style>
        </head>
        <body>
          <h1>${summary.title}</h1>
          <p class="status">Status: ${summary.status}</p>
          <p>File: ${summary.formatted_file?.file_name || "DOCX upload"}</p>
          <table>
            <thead><tr><th>Check</th><th>Status</th><th>Severity</th><th>Detail</th></tr></thead>
            <tbody>
              ${checks.map((check) => `<tr><td>${check.name}</td><td>${check.status}</td><td>${check.severity}</td><td>${check.detail}</td></tr>`).join("")}
            </tbody>
          </table>
          <footer>${summary.footer_note || "Validated content complies with anti-AI & copyright policies."}</footer>
        </body>
      </html>
    `);
    popup.document.close();
    popup.focus();
    popup.print();
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose} data-testid="book-editor">
      <div className="bg-ivory rounded-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto p-6 sm:p-10" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-serif-display text-2xl text-burgundy">{isNew ? "New Book" : f.title}</h3>
          <button onClick={onClose} className="text-charcoal-soft"><X /></button>
        </div>

        {isNew && (
          <div className="mb-6 rounded-xl border border-brand-soft bg-ivory-warm/70 p-5" data-testid="book-template-import">
            <div className="italic-eyebrow mb-2">Admin-only validator</div>
            <h4 className="font-serif-display text-[1.35rem] text-burgundy leading-snug">Upload Book (.DOCX)</h4>
            <p className="mt-2 text-sm text-charcoal-soft leading-relaxed">
              Upload a completed DOCX manuscript for Earnalism Compliance v1.0 checks, formatting cleanup, secure storage, credit logging, and form auto-fill.
            </p>
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
              <Field label="DOCX manuscript">
                <input type="file" accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={(e) => { setDocxTemplate(e.target.files?.[0] || null); setImportResult(null); setCreditReport(null); setImportProgress(0); }} className="input-elegant text-sm" data-testid="book-import-docx" />
              </Field>
              <Field label="Front cover">
                <input type="file" accept="image/jpeg,image/png,image/webp,image/gif" onChange={(e) => setFrontCoverFile(e.target.files?.[0] || null)} className="input-elegant text-sm" data-testid="book-import-front-cover" />
              </Field>
              <Field label="Back cover">
                <input type="file" accept="image/jpeg,image/png,image/webp,image/gif" onChange={(e) => setBackCoverFile(e.target.files?.[0] || null)} className="input-elegant text-sm" data-testid="book-import-back-cover" />
              </Field>
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button type="button" onClick={importTemplate} disabled={importing || !docxTemplate} className="btn-secondary disabled:opacity-60" data-testid="book-import-submit">
                {importing ? "Validating…" : "Upload Book (.DOCX)"}
              </button>
              {importResult?.success && (
                <span className="text-[0.8rem] text-charcoal-soft">
                  Validated and auto-filled. Review all fields before saving.
                </span>
              )}
            </div>
            {(importing || importProgress > 0) && (
              <div className="mt-4" aria-label="DOCX validation progress">
                <div className="flex justify-between text-[0.72rem] uppercase tracking-[0.16em] text-charcoal-soft">
                  <span>{importStage || (importResult ? "complete" : "ready")}</span>
                  <span>{importProgress}%</span>
                </div>
                <div className="mt-2 h-2 rounded-full bg-white border border-brand-soft overflow-hidden">
                  <div className="h-full bg-[var(--brand-burgundy)] transition-all duration-200" style={{ width: `${importProgress}%` }} />
                </div>
              </div>
            )}
            {Array.isArray(importResult?.warnings) && importResult.warnings.length > 0 && (
              <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                <div className="font-medium">Import warnings</div>
                <ul className="mt-2 list-disc pl-5">
                  {importResult.warnings.map((warning) => <li key={warning}>{warning}</li>)}
                </ul>
              </div>
            )}
            {importResult?.validation_summary && (
              <div className="mt-4 rounded-lg border border-brand-soft bg-white/65 p-4 text-sm text-charcoal-soft" data-testid="docx-validation-summary">
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <div>
                    <div className="font-serif-display text-xl text-burgundy">{importResult.validation_summary.title}</div>
                    <div className="text-xs uppercase tracking-[0.16em] text-charcoal-soft mt-1">
                      Status: {importResult.validation_summary.status} · {importResult.metadata?.word_count || 0} words · {importResult.metadata?.chapter_count || 0} chapters
                    </div>
                  </div>
                  <button type="button" onClick={printValidationSummary} className="btn-link text-xs">Print summary</button>
                </div>
                <div className="mt-3 overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-left uppercase tracking-[0.14em] text-charcoal-soft border-b border-brand">
                        <th className="py-2 pr-3">Check</th>
                        <th className="py-2 pr-3">Status</th>
                        <th className="py-2 pr-3">Severity</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(importResult.validation_summary.checks || []).map((check) => (
                        <tr key={check.name} className="border-b border-brand/60">
                          <td className="py-2 pr-3">{check.name}</td>
                          <td className="py-2 pr-3">{check.status}</td>
                          <td className="py-2 pr-3">{check.severity}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="mt-3 text-xs italic">{importResult.validation_summary.footer_note}</p>
              </div>
            )}
            {Array.isArray(importResult?.credit_usage) && (
              <div className="mt-4 rounded-lg border border-brand-soft bg-white/65 p-4 text-sm text-charcoal-soft" data-testid="docx-credit-usage">
                <div className="font-serif-display text-xl text-burgundy">Credit usage</div>
                <table className="mt-3 w-full text-xs">
                  <thead>
                    <tr className="text-left uppercase tracking-[0.14em] text-charcoal-soft border-b border-brand">
                      <th className="py-2 pr-3">Task</th>
                      <th className="py-2 pr-3">Units</th>
                      <th className="py-2 pr-3">Credits</th>
                    </tr>
                  </thead>
                  <tbody>
                    {importResult.credit_usage.map((row) => (
                      <tr key={row.task} className="border-b border-brand/60">
                        <td className="py-2 pr-3">{row.task}</td>
                        <td className="py-2 pr-3">{row.units} {row.unit_label}</td>
                        <td className="py-2 pr-3">{row.credits_used}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="mt-2 text-xs">Total upload credits: {importResult.credits_used}</p>
                {creditReport && <p className="mt-1 text-xs">Customer report total: {creditReport.total_credits_used} credits.</p>}
              </div>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Title"><input className="input-elegant" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} data-testid="book-title" /></Field>
          <Field label="Subtitle"><input className="input-elegant" value={f.subtitle} onChange={(e) => setF({ ...f, subtitle: e.target.value })} /></Field>
          <Field label="Author"><input className="input-elegant" value={f.author || ""} onChange={(e) => setF({ ...f, author: e.target.value })} placeholder="The Earnalism" data-testid="book-author" /></Field>
          <Field label="Category">
            <select className="input-elegant" value={f.category_slug} onChange={(e) => setF({ ...f, category_slug: e.target.value })}>
              {cats.map((c) => <option key={c.slug} value={c.slug}>{c.name}</option>)}
            </select>
          </Field>
          <Field label="Cover image URL"><input className="input-elegant" value={f.cover_image_url} onChange={(e) => setF({ ...f, cover_image_url: e.target.value })} /></Field>
          <Field label="Back cover image URL"><input className="input-elegant" value={f.back_cover_image_url || ""} onChange={(e) => setF({ ...f, back_cover_image_url: e.target.value })} /></Field>
          <Field label="Estimated reading time"><input className="input-elegant" value={f.estimated_reading_time || ""} onChange={(e) => setF({ ...f, estimated_reading_time: e.target.value })} placeholder="4 hours" data-testid="book-reading-time" /></Field>
          <Field label="Buy Reading Time URL (Razorpay / external)" wide><input className="input-elegant" value={f.buy_url} onChange={(e) => setF({ ...f, buy_url: e.target.value })} placeholder="https://rzp.io/l/your-link (leave empty for 'Request Access')" data-testid="book-buy-url" /></Field>
          <Field label="Publication status" wide>
            <label className="inline-flex items-center gap-3 rounded-lg border border-brand-soft px-4 py-3 text-sm text-charcoal-soft">
              <input type="checkbox" checked={Boolean(f.is_published)} onChange={(e) => setF({ ...f, is_published: e.target.checked })} />
              Published
            </label>
          </Field>
          <Field label="Short description" wide><textarea rows={2} className="input-elegant" value={f.short_description} onChange={(e) => setF({ ...f, short_description: e.target.value })} /></Field>
          <Field label="Description" wide><textarea rows={4} className="input-elegant" value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></Field>
          <Field label="Benefits (one per line)"><textarea rows={3} className="input-elegant" value={f.benefits} onChange={(e) => setF({ ...f, benefits: e.target.value })} /></Field>
          <Field label="Who this is for (one per line)"><textarea rows={3} className="input-elegant" value={f.who_for} onChange={(e) => setF({ ...f, who_for: e.target.value })} /></Field>
          <Field label="What you will learn (one per line)"><textarea rows={3} className="input-elegant" value={f.learnings} onChange={(e) => setF({ ...f, learnings: e.target.value })} /></Field>
          <Field label="About the author / publisher" wide><textarea rows={2} className="input-elegant" value={f.about_author} onChange={(e) => setF({ ...f, about_author: e.target.value })} /></Field>
        </div>

        {!isNew && (
          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
            <CoverUpload
              bookId={book.slug}
              kind="front"
              currentUrl={f.cover_image_url}
              onSuccess={(data) => {
                setF((prev) => ({ ...prev, cover_image_url: data.cover_url, cover_url: data.cover_url, thumbnail_url: data.thumbnail_url, cover_processing_status: "ready", cover_processing_error: "" }));
                toast.success("Front cover uploaded");
              }}
            />
            <CoverUpload
              bookId={book.slug}
              kind="back"
              currentUrl={f.back_cover_image_url}
              onSuccess={(data) => {
                setF((prev) => ({ ...prev, back_cover_image_url: data.cover_url, back_cover_url: data.cover_url, back_cover_thumbnail_url: data.thumbnail_url, back_cover_processing_status: "ready", back_cover_processing_error: "" }));
                toast.success("Back cover uploaded");
              }}
            />
          </div>
        )}

        {saveBlocked && (
          <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            <div className="font-medium">Resolve before publishing:</div>
            <ul className="mt-2 list-disc pl-5">
              {issues.map((issue) => <li key={issue}>{issue}</li>)}
            </ul>
          </div>
        )}

        {!isNew && <ChaptersManager slug={book.slug} />}

        <div className="mt-6 flex items-center justify-between gap-3 flex-wrap">
          {!isNew && (
            <a href={`/reader/${book.slug}`} target="_blank" rel="noreferrer" className="btn-link" data-testid="book-preview-reader">
              Preview reader
            </a>
          )}
          <div className="flex justify-end gap-3 ml-auto">
            <button onClick={onClose} className="btn-secondary">Cancel</button>
            <button onClick={() => onSave(f, isNew ? null : book.slug)} disabled={saveBlocked || !String(f.title || "").trim()} className="btn-primary disabled:opacity-60" data-testid="save-book">Save</button>
          </div>
        </div>
      </div>
    </div>
  );
}

const Field = ({ label, children, wide }) => (
  <label className={`block ${wide ? "sm:col-span-2" : ""}`}>
    <span className="block text-xs uppercase tracking-[0.18em] text-charcoal-soft mb-1">{label}</span>
    {children}
  </label>
);

function BlogAdmin() {
  const [posts, setPosts] = useState([]);
  const [editing, setEditing] = useState(null);

  const load = () => api.get("/admin/blog").then((r) => setPosts(r.data));
  useEffect(() => { load(); }, []);

  const save = async (f, slug) => {
    try {
      if (slug) await api.put(`/admin/blog/${slug}`, f);
      else await api.post("/admin/blog", f);
      toast.success("Saved"); setEditing(null); load();
    } catch (e) { toast.error(formatError(e.response?.data?.detail)); }
  };
  const del = async (slug) => { if (!window.confirm("Delete?")) return; await api.delete(`/admin/blog/${slug}`); load(); };

  return (
    <div data-testid="blog-admin">
      <div className="flex items-center justify-between mb-5">
        <h2 className="font-serif-display text-2xl text-burgundy">Journal ({posts.length})</h2>
        <button onClick={() => setEditing({ _new: true, title: "", excerpt: "", content: "", category: "Reflections", cover_image_url: "", author: "The Earnalism", pull_quote: "", is_published: true })} className="btn-primary" data-testid="add-post"><Plus size={14} className="mr-2" /> New post</button>
      </div>
      <div className="grid gap-4">
        {posts.map((p) => (
          <div key={p.slug} className="card-elegant p-5 flex justify-between items-center gap-4" data-testid={`admin-post-${p.slug}`}>
            <div>
              <div className="overline">{p.category}</div>
              <h3 className="font-serif-display text-xl text-burgundy">{p.title}</h3>
            </div>
            <div className="flex gap-3">
              <button onClick={() => setEditing(p)} className="text-xs uppercase text-burgundy" data-testid={`edit-post-${p.slug}`}><Edit3 size={12} className="inline" /> Edit</button>
              <button onClick={() => del(p.slug)} className="text-xs uppercase text-charcoal-soft hover:text-burgundy"><Trash2 size={12} className="inline" /> Delete</button>
            </div>
          </div>
        ))}
      </div>
      {editing && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={() => setEditing(null)}>
          <div className="bg-ivory rounded-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto p-6 sm:p-10" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-serif-display text-2xl text-burgundy mb-5">{editing._new ? "New Post" : editing.title}</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Title" wide><input className="input-elegant" value={editing.title} onChange={(e) => setEditing({ ...editing, title: e.target.value })} data-testid="post-title" /></Field>
              <Field label="Category"><input className="input-elegant" value={editing.category} onChange={(e) => setEditing({ ...editing, category: e.target.value })} /></Field>
              <Field label="Author"><input className="input-elegant" value={editing.author} onChange={(e) => setEditing({ ...editing, author: e.target.value })} /></Field>
              <Field label="Cover image URL" wide><input className="input-elegant" value={editing.cover_image_url} onChange={(e) => setEditing({ ...editing, cover_image_url: e.target.value })} /></Field>
              <Field label="Excerpt" wide><textarea rows={2} className="input-elegant" value={editing.excerpt} onChange={(e) => setEditing({ ...editing, excerpt: e.target.value })} /></Field>
              <Field label="Content (paragraphs separated by blank line)" wide><textarea rows={10} className="input-elegant" value={editing.content} onChange={(e) => setEditing({ ...editing, content: e.target.value })} /></Field>
              <Field label="Pull quote" wide><input className="input-elegant" value={editing.pull_quote} onChange={(e) => setEditing({ ...editing, pull_quote: e.target.value })} /></Field>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button onClick={() => setEditing(null)} className="btn-secondary">Cancel</button>
              <button onClick={() => { const { _new, ...payload } = editing; save(payload, _new ? null : editing.slug); }} className="btn-primary" data-testid="save-post">Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function CategoriesAdmin() {
  const [cats, setCats] = useState([]);
  const [editing, setEditing] = useState(null);
  const load = () => api.get("/categories").then((r) => setCats(r.data));
  useEffect(() => { load(); }, []);
  const save = async (f, slug) => {
    try {
      if (slug) await api.put(`/admin/categories/${slug}`, f);
      else await api.post("/admin/categories", f);
      toast.success("Saved"); setEditing(null); load();
    } catch (e) { toast.error(formatError(e.response?.data?.detail)); }
  };
  return (
    <div data-testid="cats-admin">
      <div className="flex items-center justify-between mb-5">
        <h2 className="font-serif-display text-2xl text-burgundy">Categories ({cats.length})</h2>
        <button onClick={() => setEditing({ _new: true, name: "", description: "", image_url: "", order: cats.length + 1 })} className="btn-primary"><Plus size={14} className="mr-2" /> New</button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {cats.map((c) => (
          <div key={c.slug} className="card-elegant p-5">
            <div className="overline">{c.slug}</div>
            <h3 className="font-serif-display text-xl text-burgundy">{c.name}</h3>
            <p className="text-sm text-charcoal-soft mt-1">{c.description}</p>
            <button onClick={() => setEditing(c)} className="text-xs uppercase text-burgundy mt-3"><Edit3 size={12} className="inline" /> Edit</button>
          </div>
        ))}
      </div>
      {editing && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={() => setEditing(null)}>
          <div className="bg-ivory rounded-2xl w-full max-w-2xl p-8" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-serif-display text-2xl text-burgundy mb-5">{editing._new ? "New Category" : editing.name}</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Name" wide><input className="input-elegant" value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} /></Field>
              <Field label="Description" wide><textarea rows={2} className="input-elegant" value={editing.description} onChange={(e) => setEditing({ ...editing, description: e.target.value })} /></Field>
              <Field label="Image URL" wide><input className="input-elegant" value={editing.image_url} onChange={(e) => setEditing({ ...editing, image_url: e.target.value })} /></Field>
              <Field label="Order"><input type="number" className="input-elegant" value={editing.order} onChange={(e) => setEditing({ ...editing, order: parseInt(e.target.value) || 0 })} /></Field>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button onClick={() => setEditing(null)} className="btn-secondary">Cancel</button>
              <button onClick={() => { const { _new, ...payload } = editing; save(payload, _new ? null : editing.slug); }} className="btn-primary">Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


function AccountTab() {
  const { logout } = useAuth();
  const [cur, setCur] = useState("");
  const [nxt, setNxt] = useState("");
  const [cfm, setCfm] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (nxt !== cfm) { toast.error("New passwords do not match"); return; }
    if (nxt.length < 8) { toast.error("New password must be at least 8 characters"); return; }
    setBusy(true);
    try {
      await api.post("/auth/change-password", { current_password: cur, new_password: nxt });
      toast.success("Password updated. Please sign in again.");
      setTimeout(logout, 800);
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail));
    } finally { setBusy(false); }
  };

  return (
    <div className="card-elegant p-6 sm:p-10 max-w-xl" data-testid="account-tab">
      <div className="flex items-center gap-2 mb-5">
        <KeyRound className="text-gold" size={18} />
        <h2 className="font-serif-display text-2xl text-burgundy">Change password</h2>
      </div>
      <p className="text-sm text-charcoal-soft mb-6">For your security, choose a password at least 8 characters long. You'll be signed out after updating.</p>
      <form onSubmit={submit} className="space-y-5">
        <input required type="password" value={cur} onChange={(e) => setCur(e.target.value)} placeholder="Current password" className="input-elegant" data-testid="cur-password" />
        <input required type="password" value={nxt} onChange={(e) => setNxt(e.target.value)} placeholder="New password" className="input-elegant" data-testid="new-password" />
        <input required type="password" value={cfm} onChange={(e) => setCfm(e.target.value)} placeholder="Confirm new password" className="input-elegant" data-testid="confirm-password" />
        <button disabled={busy} className="btn-primary disabled:opacity-60" data-testid="change-password-submit">{busy ? "Updating…" : "Update password"}</button>
      </form>
    </div>
  );
}

const SOCIAL_FIELDS = [
  { key: "instagram", label: "Instagram URL", placeholder: "https://instagram.com/theearnalism" },
  { key: "facebook", label: "Facebook URL", placeholder: "https://facebook.com/theearnalism" },
  { key: "youtube", label: "YouTube URL", placeholder: "https://youtube.com/@theearnalism" },
  { key: "linkedin", label: "LinkedIn URL", placeholder: "https://linkedin.com/company/theearnalism" },
  { key: "twitter", label: "X / Twitter URL", placeholder: "https://x.com/theearnalism" },
];

function SettingsTab() {
  const { social, brand, refresh } = useSettings();
  const [form, setForm] = useState(social);
  const [brandForm, setBrandForm] = useState(brand);
  const [busy, setBusy] = useState(false);
  const [busyBrand, setBusyBrand] = useState(false);

  useEffect(() => { setForm(social); }, [social]);
  useEffect(() => { setBrandForm(brand); }, [brand]);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.put("/admin/settings/social", form);
      await refresh();
      toast.success("Social links updated.");
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail));
    } finally { setBusy(false); }
  };

  const submitBrand = async (e) => {
    e.preventDefault();
    setBusyBrand(true);
    try {
      await api.put("/admin/settings/brand", brandForm);
      await refresh();
      toast.success("Brand identity updated.");
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail));
    } finally { setBusyBrand(false); }
  };

  return (
    <div className="space-y-8" data-testid="settings-tab">
      <div className="card-elegant p-6 sm:p-10 max-w-2xl" data-testid="settings-brand">
        <div className="flex items-center gap-2 mb-5">
          <BrandMark variant="compact" />
          <h2 className="font-serif-display text-2xl text-burgundy ml-2">Brand identity</h2>
        </div>
        <p className="text-sm text-charcoal-soft mb-6">
          Paste a hosted image URL for your logo and your social-share preview image.
          Leave blank to keep the premium serif text mark and default hero image.
        </p>
        <form onSubmit={submitBrand} className="space-y-5">
          <Field label="Logo URL" wide>
            <input
              type="url"
              className="input-elegant"
              value={brandForm.logo_url || ""}
              onChange={(e) => setBrandForm({ ...brandForm, logo_url: e.target.value })}
              placeholder="https://your-cdn.com/earnalism-logo.svg"
              data-testid="brand-logo-url"
            />
          </Field>
          {brandForm.logo_url && (
            <div className="border border-brand-soft rounded-sm p-4 bg-ivory/60 inline-flex">
              <img src={brandForm.logo_url} alt="Logo preview" className="h-10 w-auto max-w-[240px] object-contain" data-testid="brand-logo-preview" onError={(e) => { e.currentTarget.style.display = "none"; }} />
            </div>
          )}
          <Field label="Social-share image URL (Open Graph / Twitter Card)" wide>
            <input
              type="url"
              className="input-elegant"
              value={brandForm.og_image_url || ""}
              onChange={(e) => setBrandForm({ ...brandForm, og_image_url: e.target.value })}
              placeholder="https://your-cdn.com/earnalism-og.png (1200×630 recommended)"
              data-testid="brand-og-url"
            />
          </Field>
          <button disabled={busyBrand} className="btn-primary disabled:opacity-60" data-testid="save-brand">{busyBrand ? "Saving…" : "Save brand"}</button>
        </form>
      </div>

      <div className="card-elegant p-6 sm:p-10 max-w-2xl">
        <div className="flex items-center gap-2 mb-5">
          <Share2 className="text-gold" size={18} />
          <h2 className="font-serif-display text-2xl text-burgundy">Social links</h2>
        </div>
        <p className="text-sm text-charcoal-soft mb-6">Paste full profile URLs. Empty fields are hidden from the site.</p>
        <form onSubmit={submit} className="space-y-5">
          {SOCIAL_FIELDS.map((f) => (
            <Field key={f.key} label={f.label} wide>
              <input
                type="url"
                className="input-elegant"
                value={form[f.key] || ""}
                onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                placeholder={f.placeholder}
                data-testid={`social-${f.key}`}
              />
            </Field>
          ))}
          <button disabled={busy} className="btn-primary disabled:opacity-60" data-testid="save-socials">{busy ? "Saving…" : "Save links"}</button>
        </form>
      </div>
    </div>
  );
}


const CONTACT_BADGE_STYLES = {
  new: { background: "rgba(74,28,39,0.10)", color: "var(--brand-burgundy)", border: "1px solid rgba(74,28,39,0.28)" },
  read: { background: "rgba(197,160,89,0.16)", color: "var(--brand-gold-deep)", border: "1px solid rgba(197,160,89,0.32)" },
  responded: { background: "rgba(106,101,95,0.12)", color: "var(--brand-charcoal-soft)", border: "1px solid rgba(106,101,95,0.28)" },
};
const CONTACT_BADGE_LABEL = { new: "New", read: "Read", responded: "Responded" };

function ContactStatusBadge({ status }) {
  const s = CONTACT_BADGE_STYLES[status] || CONTACT_BADGE_STYLES.new;
  return (
    <span style={s} className="inline-flex items-center px-2.5 py-1 rounded-full text-[0.62rem] tracking-[0.24em] uppercase font-medium">
      {CONTACT_BADGE_LABEL[status] || CONTACT_BADGE_LABEL.new}
    </span>
  );
}

function ContactsAdmin() {
  const [rows, setRows] = useState([]);
  const [filter, setFilter] = useState("all");

  const load = () => api.get("/admin/contacts").then((r) => setRows(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const updateStatus = async (id, status) => {
    try {
      await api.patch(`/admin/contacts/${id}/status`, { status });
      toast.success(`Marked as ${CONTACT_BADGE_LABEL[status]}`);
      load();
    } catch (e) { toast.error(formatError(e.response?.data?.detail)); }
  };

  const countBy = (s) => rows.filter((r) => (r.status || "new") === s).length;
  const STATUS_TABS = [
    { key: "all", label: "All", count: rows.length },
    { key: "new", label: "New", count: countBy("new") },
    { key: "read", label: "Read", count: countBy("read") },
    { key: "responded", label: "Responded", count: countBy("responded") },
  ];

  const filtered = filter === "all" ? rows : rows.filter((r) => (r.status || "new") === filter);

  return (
    <div data-testid="contacts-admin">
      <div className="flex items-center justify-between flex-wrap gap-4 mb-6">
        <h2 className="font-serif-display text-2xl text-burgundy">Contact Submissions ({rows.length})</h2>
        <div className="flex gap-2 flex-wrap" data-testid="contacts-filters">
          {STATUS_TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setFilter(t.key)}
              data-testid={`contacts-filter-${t.key}`}
              className={`px-3.5 py-1.5 rounded-full text-[0.66rem] tracking-[0.22em] uppercase transition-colors ${filter === t.key ? "bg-burgundy text-[var(--brand-ivory)]" : "text-charcoal-soft hover:text-burgundy border border-brand-soft"}`}
            >
              {t.label} · {t.count}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="card-elegant p-12 text-center" data-testid="contacts-empty">
          <div className="italic-eyebrow mb-2">Quiet inbox</div>
          <p className="text-charcoal-soft">No submissions in this view yet.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {filtered.map((c) => {
            const status = c.status || "new";
            return (
              <div key={c.id} className="card-elegant p-5 sm:p-6" data-testid={`contact-row-${c.id}`}>
                <div className="flex items-start justify-between gap-5 flex-wrap">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-3 flex-wrap">
                      <ContactStatusBadge status={status} />
                      <span className="text-[0.66rem] tracking-[0.22em] uppercase text-charcoal-soft">{new Date(c.created_at).toLocaleString()}</span>
                    </div>
                    <h3 className="font-serif-display text-xl text-burgundy mt-3 leading-snug">
                      {c.name}
                      <span className="text-charcoal-soft text-base font-normal"> · {c.email}</span>
                    </h3>
                    {c.subject && <div className="italic-accent text-[1.05rem] text-charcoal-soft mt-1">{c.subject}</div>}
                    <p className="text-charcoal-soft mt-3 leading-[1.7] text-[0.95rem] font-light whitespace-pre-wrap">{c.message}</p>
                  </div>
                  <div className="flex flex-col gap-3 shrink-0 min-w-[140px]" data-testid={`contact-actions-${c.id}`}>
                    <a
                      href={`mailto:${c.email}?subject=${encodeURIComponent("Re: " + (c.subject || "your letter to The Earnalism"))}`}
                      className="inline-flex items-center gap-2 text-[0.66rem] tracking-[0.22em] uppercase text-burgundy hover:text-burgundy-soft border-b border-[var(--brand-gold)] pb-[2px] self-start"
                      data-testid={`contact-reply-${c.id}`}
                    >
                      <Mail size={12} /> Reply by email
                    </a>
                    {["new", "read", "responded"].filter((s) => s !== status).map((s) => (
                      <button
                        key={s}
                        onClick={() => updateStatus(c.id, s)}
                        data-testid={`contact-mark-${s}-${c.id}`}
                        className="text-left text-[0.66rem] tracking-[0.22em] uppercase text-charcoal-soft hover:text-burgundy"
                      >
                        Mark {CONTACT_BADGE_LABEL[s].toLowerCase()}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}


function ChaptersManager({ slug }) {
  const [book, setBook] = useState(null);
  const [editing, setEditing] = useState(null); // null | {_new: true} | chapter obj
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const { data } = await api.get(`/admin/books/${slug}`);
      setBook(data);
    } catch (e) { toast.error(formatError(e.response?.data?.detail)); }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [slug]);

  const chapters = (book?.chapters || []).slice().sort((a, b) => (a.order || 0) - (b.order || 0));

  const saveChapter = async (data, cid) => {
    setBusy(true);
    try {
      if (cid) await api.put(`/admin/books/${slug}/chapters/${cid}`, { title: data.title, content: data.content });
      else await api.post(`/admin/books/${slug}/chapters`, { title: data.title, content: data.content });
      toast.success("Chapter saved");
      setEditing(null);
      load();
    } catch (e) { toast.error(formatError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const deleteChapter = async (cid) => {
    if (!window.confirm("Delete this chapter? This cannot be undone.")) return;
    try {
      await api.delete(`/admin/books/${slug}/chapters/${cid}`);
      toast.success("Chapter deleted");
      load();
    } catch (e) { toast.error(formatError(e.response?.data?.detail)); }
  };

  const move = async (i, dir) => {
    const j = i + dir;
    if (j < 0 || j >= chapters.length) return;
    const ids = chapters.map((c) => c.id);
    [ids[i], ids[j]] = [ids[j], ids[i]];
    try {
      await api.put(`/admin/books/${slug}/chapters/reorder`, { ids });
      load();
    } catch (e) { toast.error(formatError(e.response?.data?.detail)); }
  };

  return (
    <div className="mt-8 pt-8 border-t border-brand-soft" data-testid="chapters-manager">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div>
          <div className="italic-eyebrow">Chapters</div>
          <h4 className="font-serif-display text-[1.4rem] text-burgundy leading-snug">Chapter content</h4>
          <p className="text-[0.8rem] text-charcoal-soft mt-1">Paste content manually, or upload DOCX, Markdown, HTML, or TXT for automatic reader formatting.</p>
        </div>
        <button
          onClick={() => setEditing({ _new: true, title: "", content: "" })}
          className="btn-primary"
          data-testid="add-chapter"
        >
          <Plus size={14} className="mr-2" /> New chapter
        </button>
      </div>

      {chapters.length === 0 ? (
        <p className="text-sm text-charcoal-soft italic">No chapters yet. Add the first one to enable the reader.</p>
      ) : (
        <ol className="space-y-2">
          {chapters.map((c, i) => (
            <li key={c.id} className="flex items-center gap-3 p-3 border border-brand-soft rounded-lg" data-testid={`chapter-row-${c.id}`}>
              <span className="italic-accent text-gold-deep w-10 shrink-0 text-center">{String(i + 1).padStart(2, "0")}</span>
              <span className="flex-1 min-w-0 font-serif-display text-[1.05rem] text-burgundy truncate">{c.title}</span>
              <ProcessingBadge status={processingStatus(c)} />
              {Array.isArray(c.processing_warnings) && c.processing_warnings.length > 0 && (
                <span className="hidden sm:inline text-[0.72rem] text-amber-800" title={c.processing_warnings.join("\n")}>Warnings</span>
              )}
              {c.processing_error && (
                <span className="hidden sm:inline text-[0.72rem] text-rose-800" title={c.processing_error}>Error</span>
              )}
              <span className="hidden sm:inline text-[0.72rem] text-charcoal-soft">{(c.content || "").length} chars</span>
              <div className="flex items-center gap-1">
                <button onClick={() => move(i, -1)} disabled={i === 0} className="p-1 text-charcoal-soft disabled:opacity-30 hover:text-burgundy" aria-label="Move up" data-testid={`chapter-up-${c.id}`}>↑</button>
                <button onClick={() => move(i, 1)} disabled={i === chapters.length - 1} className="p-1 text-charcoal-soft disabled:opacity-30 hover:text-burgundy" aria-label="Move down" data-testid={`chapter-down-${c.id}`}>↓</button>
                <button onClick={() => setEditing(c)} className="p-1 text-charcoal-soft hover:text-burgundy" aria-label="Edit" data-testid={`chapter-edit-${c.id}`}><Edit3 size={14} /></button>
                <button onClick={() => deleteChapter(c.id)} className="p-1 text-charcoal-soft hover:text-burgundy" aria-label="Delete" data-testid={`chapter-delete-${c.id}`}><Trash2 size={14} /></button>
              </div>
            </li>
          ))}
        </ol>
      )}

      {editing && (
        <ChapterEditor
          chapter={editing}
          bookId={slug}
          busy={busy}
          onCancel={() => setEditing(null)}
          onUploaded={() => { toast.success("Chapter file processed"); load(); }}
          onSave={(data) => saveChapter(data, editing._new ? null : editing.id)}
        />
      )}
    </div>
  );
}

function ChapterEditor({ chapter, bookId, onCancel, onSave, onUploaded, busy }) {
  const [title, setTitle] = useState(chapter.title || "");
  const [content, setContent] = useState(chapter.content || "");
  const previewHasHtml = hasHtmlTags(content);
  const previewHtml = useMemo(() => previewHasHtml ? sanitizePreviewHtml(content) : "", [content, previewHasHtml]);
  const previewIsBengali = containsBengaliText(`${title} ${content}`);
  const previewFont = previewIsBengali ? BENGALI_SERIF : ADMIN_SERIF;
  const uploadWarnings = Array.isArray(chapter.processing_warnings) ? chapter.processing_warnings : [];
  const handleUploadSuccess = (data) => {
    if (data?.preview_html) setContent(data.preview_html);
    onUploaded?.(data);
  };

  return (
    <div className="fixed inset-0 z-[60] bg-black/55 flex items-center justify-center p-4" onClick={onCancel} data-testid="chapter-editor">
      <div className="bg-ivory rounded-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto p-6 sm:p-10" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-5">
          <div>
            <div className="italic-eyebrow">{chapter._new ? "New chapter" : "Edit chapter"}</div>
            <h3 className="font-serif-display text-2xl text-burgundy">Chapter content</h3>
          </div>
          <button onClick={onCancel} className="text-charcoal-soft"><X /></button>
        </div>
        <Field label="Chapter title" wide>
          <input className="input-elegant" value={title} onChange={(e) => setTitle(e.target.value)} data-testid="chapter-title" />
        </Field>
        {!chapter._new && (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <ProcessingBadge status={processingStatus(chapter)} />
            {chapter.source_filename && <span className="text-[0.72rem] text-charcoal-soft">Source: {chapter.source_filename}</span>}
            {chapter.processing_error && <span className="text-[0.72rem] text-rose-800">{chapter.processing_error}</span>}
          </div>
        )}
        <div className="mt-4">
          <Field label="Chapter body (separate paragraphs with a blank line)" wide>
            <textarea
              rows={16}
              className="input-elegant font-serif-display"
              lang={previewIsBengali ? "bn" : undefined}
              style={{ lineHeight: previewIsBengali ? 1.9 : 1.7, fontSize: "1rem", fontFamily: previewFont }}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              data-testid="chapter-body"
              placeholder="Paste your chapter here. Leave a blank line between paragraphs."
            />
          </Field>
          <p className="text-[0.72rem] text-charcoal-soft mt-2 italic">{content.length.toLocaleString()} characters &middot; approx. {Math.max(1, Math.round(content.split(/\s+/).filter(Boolean).length / 200))} min read</p>
        </div>
        {content.trim() && (
          <div className="mt-5 rounded-xl border border-brand-soft bg-ivory-warm/70 p-5" data-testid="chapter-preview">
            <div className="overline mb-3">Preview</div>
            <h4
              className="text-burgundy leading-snug"
              lang={previewIsBengali ? "bn" : undefined}
              style={{ fontFamily: previewFont, fontSize: "1.35rem" }}
            >
              {title || "Untitled chapter"}
            </h4>
            {previewHasHtml ? (
              <div
                className={previewIsBengali ? "reader-content reader-content--bengali mt-4" : "reader-content mt-4"}
                lang={previewIsBengali ? "bn" : undefined}
                style={{ fontFamily: previewFont, fontSize: "1rem", lineHeight: previewIsBengali ? 1.9 : 1.75, color: "var(--brand-charcoal)", overflowWrap: "break-word" }}
                dangerouslySetInnerHTML={{ __html: previewHtml }}
              />
            ) : (
              <div
                className={previewIsBengali ? "reader-content reader-content--bengali mt-4" : "reader-content mt-4"}
                lang={previewIsBengali ? "bn" : undefined}
                style={{ fontFamily: previewFont, fontSize: "1rem", lineHeight: previewIsBengali ? 1.9 : 1.75, color: "var(--brand-charcoal)", whiteSpace: "pre-wrap", overflowWrap: "break-word" }}
              >
                {content}
              </div>
            )}
          </div>
        )}
        {uploadWarnings.length > 0 && (
          <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            <div className="font-medium">Processing warnings</div>
            <ul className="mt-2 list-disc pl-5">
              {uploadWarnings.map((warning) => <li key={warning}>{warning}</li>)}
            </ul>
          </div>
        )}
        {!chapter._new && (
          <div className="mt-6">
            <div className="overline mb-2">Upload formatted chapter</div>
            <ChapterUpload bookId={bookId} chapterId={chapter.id} onSuccess={handleUploadSuccess} />
          </div>
        )}
        <div className="mt-6 flex justify-end gap-3">
          <button onClick={onCancel} className="btn-secondary">Cancel</button>
          <button
            onClick={() => onSave({ title: title.trim(), content })}
            disabled={busy || !title.trim()}
            className="btn-primary disabled:opacity-60"
            data-testid="save-chapter"
          >
            {busy ? "Saving…" : "Save chapter"}
          </button>
        </div>
      </div>
    </div>
  );
}


function UsersAdmin() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedUser, setSelectedUser] = useState(null);
  const [adjMinutes, setAdjMinutes] = useState("");
  const [adjReason, setAdjReason] = useState("");
  const [txs, setTxs] = useState([]);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/admin/users");
      setUsers(data);
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail));
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const openUser = async (u) => {
    setSelectedUser(u);
    setAdjMinutes("");
    setAdjReason("");
    try {
      const { data } = await api.get(`/admin/users/${u.id}/transactions`);
      setTxs(data);
    } catch { setTxs([]); }
  };

  const adjust = async () => {
    if (!selectedUser) return;
    const mins = parseInt(adjMinutes, 10);
    if (Number.isNaN(mins) || mins === 0) {
      toast.error("Enter a non-zero number of minutes (use negative to deduct).");
      return;
    }
    setBusy(true);
    try {
      await api.post(`/admin/users/${selectedUser.id}/wallet/adjust`, {
        minutes: mins,
        reason: adjReason || "",
      });
      toast.success(mins > 0 ? `Added ${mins} min` : `Deducted ${Math.abs(mins)} min`);
      setAdjMinutes("");
      setAdjReason("");
      await load();
      const fresh = await api.get(`/admin/users/${selectedUser.id}/transactions`);
      setTxs(fresh.data);
      const refreshed = (await api.get("/admin/users")).data.find((x) => x.id === selectedUser.id);
      if (refreshed) setSelectedUser(refreshed);
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail));
    } finally { setBusy(false); }
  };

  const toggleStatus = async (u) => {
    const next = u.status === "blocked" ? "active" : "blocked";
    if (!window.confirm(`${next === "blocked" ? "Block" : "Unblock"} ${u.email}?`)) return;
    try {
      await api.patch(`/admin/users/${u.id}/status`, { status: next });
      toast.success(`Status set to ${next}`);
      await load();
      if (selectedUser?.id === u.id) setSelectedUser({ ...selectedUser, status: next });
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail));
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6" data-testid="admin-users">
      <div className="lg:col-span-2 card-elegant p-6 sm:p-8 overflow-x-auto">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
          <h2 className="font-serif-display text-2xl text-burgundy">Reader accounts ({users.length})</h2>
          <button onClick={load} className="btn-link text-xs" data-testid="users-refresh">Refresh</button>
        </div>
        {loading ? <p className="text-charcoal-soft">Loading…</p> : users.length === 0 ? (
          <p className="text-charcoal-soft text-sm">No reader accounts yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wider text-charcoal-soft border-b border-brand">
                <th className="py-3 pr-4">Name</th>
                <th className="py-3 pr-4">Email</th>
                <th className="py-3 pr-4">Time</th>
                <th className="py-3 pr-4">Status</th>
                <th className="py-3 pr-4">Joined</th>
                <th className="py-3 pr-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className={`border-b border-brand/60 hover:bg-beige/40 transition-colors ${selectedUser?.id === u.id ? "bg-beige/60" : ""}`} data-testid={`user-row-${u.id}`}>
                  <td className="py-3 pr-4 font-serif-display">{u.name}</td>
                  <td className="py-3 pr-4 text-charcoal-soft">{u.email}</td>
                  <td className="py-3 pr-4">
                    <span className="inline-flex items-center gap-1.5"><Clock size={12} strokeWidth={1.5} /> {formatMinutes(u.reading_seconds_balance)}</span>
                  </td>
                  <td className="py-3 pr-4">
                    <span className={`text-[0.65rem] tracking-[0.2em] uppercase px-2 py-0.5 rounded-full ${u.status === "blocked" ? "bg-rose-100 text-rose-800" : "bg-emerald-100 text-emerald-800"}`}>{u.status}</span>
                  </td>
                  <td className="py-3 pr-4 text-charcoal-soft text-xs">{new Date(u.created_at).toLocaleDateString()}</td>
                  <td className="py-3 pr-4 text-right whitespace-nowrap">
                    <button onClick={() => openUser(u)} className="btn-link text-xs mr-3" data-testid={`user-manage-${u.id}`}>Manage</button>
                    <button onClick={() => toggleStatus(u)} className="text-xs text-charcoal-soft hover:text-burgundy" data-testid={`user-toggle-${u.id}`}>
                      {u.status === "blocked" ? <Check size={14} /> : <Ban size={14} />}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Right pane: selected user */}
      <div className="card-elegant p-6 sm:p-8" data-testid="admin-users-detail">
        {!selectedUser ? (
          <div className="text-charcoal-soft text-sm font-light">
            Select a reader on the left to adjust their wallet and view transaction history.
          </div>
        ) : (
          <div>
            <div className="overline">Manage</div>
            <h3 className="font-serif-display text-xl text-burgundy leading-tight mt-1">{selectedUser.name}</h3>
            <p className="text-charcoal-soft text-xs">{selectedUser.email}</p>
            <div className="mt-5 flex items-center gap-3">
              <Clock size={14} strokeWidth={1.5} className="text-burgundy" />
              <span className="font-serif-display text-2xl text-charcoal" data-testid="user-detail-balance">{formatMinutes(selectedUser.reading_seconds_balance)}</span>
            </div>

            <div className="gold-rule-thin my-6" />

            <div className="overline mb-3">Adjust wallet (minutes)</div>
            <div className="flex flex-col gap-3">
              <input
                type="number"
                value={adjMinutes}
                onChange={(e) => setAdjMinutes(e.target.value)}
                placeholder="e.g. 60 or -15"
                className="input-elegant"
                data-testid="user-adjust-minutes"
              />
              <input
                type="text"
                value={adjReason}
                onChange={(e) => setAdjReason(e.target.value)}
                placeholder="Reason (optional)"
                className="input-elegant"
                data-testid="user-adjust-reason"
              />
              <div className="flex flex-wrap gap-2">
                {[30, 60, 180, 600].map((m) => (
                  <button key={m} type="button" onClick={() => setAdjMinutes(String(m))} className="text-[0.7rem] tracking-[0.18em] uppercase px-3 py-1.5 border border-brand rounded-full hover:bg-burgundy hover:text-[var(--brand-ivory)] transition-colors" data-testid={`quick-add-${m}`}>
                    +{m >= 60 ? `${m / 60}h` : `${m}m`}
                  </button>
                ))}
              </div>
              <button onClick={adjust} disabled={busy} className="btn-primary w-full disabled:opacity-60" data-testid="user-adjust-submit">
                {busy ? "Applying…" : "Apply adjustment"}
              </button>
            </div>

            <div className="gold-rule-thin my-6" />

            <div className="overline mb-3">Recent transactions</div>
            {txs.length === 0 ? (
              <p className="text-charcoal-soft text-sm font-light">No transactions yet.</p>
            ) : (
              <ul className="space-y-3 max-h-72 overflow-y-auto">
                {txs.map((t) => (
                  <li key={t.id} className="text-xs border-b border-brand/60 pb-2" data-testid={`user-tx-${t.id}`}>
                    <div className="flex items-center justify-between gap-2">
                      <span className={`font-serif-display ${t.seconds < 0 ? "text-rose-700" : "text-emerald-700"}`}>
                        {t.seconds >= 0 ? "+" : "−"}{formatMinutes(Math.abs(t.seconds))}
                      </span>
                      <span className="text-[0.6rem] tracking-[0.18em] uppercase text-charcoal-soft">{t.type}</span>
                    </div>
                    <div className="text-charcoal-soft mt-1">{t.reason || "—"}</div>
                    <div className="text-charcoal-soft/70 mt-1">{new Date(t.created_at).toLocaleString()}</div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}


function PaymentsAdmin() {
  const [intents, setIntents] = useState([]);
  const [hooks, setHooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [config, setConfig] = useState({ configured: false, mode: "test" });
  const [busyId, setBusyId] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const [a, b, c] = await Promise.all([
        api.get("/admin/payments/intents"),
        api.get("/admin/payments/webhooks"),
        api.get("/payments/config"),
      ]);
      setIntents(a.data || []);
      setHooks(b.data || []);
      setConfig(c.data || {});
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail));
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const reconcile = async (intentId) => {
    const note = window.prompt("Reconciliation note (optional)") || "";
    setBusyId(intentId);
    try {
      await api.post(`/admin/payments/intents/${intentId}/reconcile`, { note });
      toast.success("Reconciled — wallet credited.");
      await load();
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail));
    } finally { setBusyId(null); }
  };

  const totalCredited = intents
    .filter((i) => i.status === "credited")
    .reduce((sum, i) => sum + Number(i.minutes || 0), 0);

  return (
    <div className="space-y-8" data-testid="admin-payments">
      <div className="card-elegant p-6 sm:p-8" data-testid="admin-payments-config">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <div className="overline">Payments configuration</div>
            <h2 className="font-serif-display text-2xl text-burgundy mt-1">Razorpay status</h2>
          </div>
          <span className={`text-[0.65rem] tracking-[0.2em] uppercase px-3 py-1 rounded-full ${config.configured ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`} data-testid="admin-payments-status">
            {config.configured ? `Live · ${config.mode}` : "Keys missing"}
          </span>
        </div>
        <div className="gold-rule-thin my-4" />
        <p className="text-charcoal-soft text-sm font-light leading-relaxed">
          {config.configured
            ? `Razorpay is wired in ${config.mode} mode (key id ${config.key_id || "—"}). Test purchases on /pricing will go through Razorpay Checkout.`
            : "Add RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, and RAZORPAY_WEBHOOK_SECRET to backend/.env and restart the backend. Until then, /pricing will run a local test simulator instead of Razorpay Checkout."}
        </p>
      </div>

      <div className="card-elegant p-6 sm:p-8 overflow-x-auto" data-testid="admin-payments-intents">
        <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
          <div>
            <h2 className="font-serif-display text-2xl text-burgundy">Top-up intents ({intents.length})</h2>
            <p className="text-xs text-charcoal-soft mt-1">Total credited: {totalCredited} minutes across all readers.</p>
          </div>
          <button onClick={load} className="btn-link text-xs" data-testid="payments-refresh">Refresh</button>
        </div>
        {loading ? <p className="text-charcoal-soft text-sm">Loading…</p> : intents.length === 0 ? (
          <p className="text-charcoal-soft text-sm">No top-up intents yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wider text-charcoal-soft border-b border-brand">
                <th className="py-3 pr-4">When</th>
                <th className="py-3 pr-4">User</th>
                <th className="py-3 pr-4">Pack</th>
                <th className="py-3 pr-4">Amount</th>
                <th className="py-3 pr-4">Razorpay</th>
                <th className="py-3 pr-4">Status</th>
                <th className="py-3 pr-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {intents.map((i) => (
                <tr key={i.id} className="border-b border-brand/60" data-testid={`intent-row-${i.id}`}>
                  <td className="py-3 pr-4 text-charcoal-soft text-xs whitespace-nowrap">{new Date(i.created_at).toLocaleString()}</td>
                  <td className="py-3 pr-4 text-charcoal-soft">{i.user_email || i.user_id}</td>
                  <td className="py-3 pr-4 font-serif-display">{i.pack_id} · {i.minutes}m</td>
                  <td className="py-3 pr-4">₹{(Number(i.amount_paise) / 100).toFixed(0)}</td>
                  <td className="py-3 pr-4 text-xs text-charcoal-soft">
                    <div>{i.razorpay_order_id || "—"}</div>
                    {i.razorpay_payment_id && <div className="opacity-70">{i.razorpay_payment_id}</div>}
                  </td>
                  <td className="py-3 pr-4">
                    <span className={`text-[0.65rem] tracking-[0.2em] uppercase px-2 py-0.5 rounded-full ${
                      i.status === "credited" ? "bg-emerald-100 text-emerald-800" :
                      i.status === "failed" ? "bg-rose-100 text-rose-800" :
                      "bg-amber-100 text-amber-800"
                    }`}>{i.status}</span>
                  </td>
                  <td className="py-3 pr-4 text-right">
                    {i.status !== "credited" && (
                      <button
                        disabled={busyId === i.id}
                        onClick={() => reconcile(i.id)}
                        className="btn-link text-xs disabled:opacity-50"
                        data-testid={`intent-reconcile-${i.id}`}
                      >
                        {busyId === i.id ? "…" : "Reconcile"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card-elegant p-6 sm:p-8 overflow-x-auto" data-testid="admin-payments-webhooks">
        <h2 className="font-serif-display text-2xl text-burgundy mb-4">Webhook events ({hooks.length})</h2>
        {hooks.length === 0 ? (
          <p className="text-charcoal-soft text-sm">No webhook events yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wider text-charcoal-soft border-b border-brand">
                <th className="py-3 pr-4">When</th>
                <th className="py-3 pr-4">Event</th>
                <th className="py-3 pr-4">Order</th>
                <th className="py-3 pr-4">Payment</th>
                <th className="py-3 pr-4">Status</th>
              </tr>
            </thead>
            <tbody>
              {hooks.map((h) => (
                <tr key={h.id} className="border-b border-brand/60" data-testid={`webhook-row-${h.id}`}>
                  <td className="py-3 pr-4 text-charcoal-soft text-xs whitespace-nowrap">{new Date(h.created_at).toLocaleString()}</td>
                  <td className="py-3 pr-4 font-serif-display">{h.event || "—"}</td>
                  <td className="py-3 pr-4 text-xs text-charcoal-soft">{h.razorpay_order_id || "—"}</td>
                  <td className="py-3 pr-4 text-xs text-charcoal-soft">{h.razorpay_payment_id || "—"}</td>
                  <td className="py-3 pr-4">
                    <span className={`text-[0.65rem] tracking-[0.2em] uppercase px-2 py-0.5 rounded-full ${
                      h.status?.startsWith("credited") ? "bg-emerald-100 text-emerald-800" :
                      h.status?.startsWith("rejected") ? "bg-rose-100 text-rose-800" :
                      "bg-amber-100 text-amber-800"
                    }`}>{h.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
