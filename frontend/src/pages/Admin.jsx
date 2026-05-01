import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api, formatError } from "../lib/api";
import { toast } from "sonner";
import { LogOut, Plus, Trash2, Edit3, Star, X, KeyRound } from "lucide-react";

const TABS = ["books", "blog", "categories", "newsletter", "contacts", "publishing", "account"];

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
            <div className="overline">Admin Dashboard</div>
            <h1 className="font-serif-display text-3xl sm:text-4xl text-burgundy">The Earnalism</h1>
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
        {tab === "contacts" && <SimpleList endpoint="/admin/contacts" testid="admin-contacts" cols={["name", "email", "subject", "message", "created_at"]} title="Contact Submissions" />}
        {tab === "publishing" && <SimpleList endpoint="/admin/publishing-requests" testid="admin-publishing" cols={["name", "email", "project_title", "message", "created_at"]} title="Publishing Requests" />}
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
            <tr key={i} className="border-b border-brand/60">
              {cols.map((c) => <td key={c} className="py-3 pr-4 align-top max-w-xs">{c === "created_at" ? new Date(r[c]).toLocaleString() : (r[c] || "—")}</td>)}
            </tr>
          ))}</tbody>
        </table>
      )}
    </div>
  );
}

const EMPTY_BOOK = { title: "", subtitle: "", category_slug: "business", short_description: "", description: "", cover_image_url: "", price_paperback: "", price_ebook: "", buy_url: "", formats: ["Paperback", "Ebook"], benefits: [], who_for: [], learnings: [], about_author: "", is_published: true };

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
        <button onClick={() => setEditing({ ...EMPTY_BOOK, _new: true })} className="btn-primary" data-testid="add-book"><Plus size={14} className="mr-2" /> New book</button>
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

function BookEditor({ book, cats, onClose, onSave }) {
  const [f, setF] = useState({
    ...book,
    benefits: lines(book.benefits), who_for: lines(book.who_for), learnings: lines(book.learnings), formats: lines(book.formats || ["Paperback", "Ebook"]),
  });
  const isNew = book._new;
  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose} data-testid="book-editor">
      <div className="bg-ivory rounded-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto p-6 sm:p-10" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-serif-display text-2xl text-burgundy">{isNew ? "New Book" : f.title}</h3>
          <button onClick={onClose} className="text-charcoal-soft"><X /></button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Title"><input className="input-elegant" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} data-testid="book-title" /></Field>
          <Field label="Subtitle"><input className="input-elegant" value={f.subtitle} onChange={(e) => setF({ ...f, subtitle: e.target.value })} /></Field>
          <Field label="Category">
            <select className="input-elegant" value={f.category_slug} onChange={(e) => setF({ ...f, category_slug: e.target.value })}>
              {cats.map((c) => <option key={c.slug} value={c.slug}>{c.name}</option>)}
            </select>
          </Field>
          <Field label="Cover image URL"><input className="input-elegant" value={f.cover_image_url} onChange={(e) => setF({ ...f, cover_image_url: e.target.value })} /></Field>
          <Field label="Price (Paperback)"><input className="input-elegant" value={f.price_paperback} onChange={(e) => setF({ ...f, price_paperback: e.target.value })} placeholder="₹499" /></Field>
          <Field label="Price (Ebook)"><input className="input-elegant" value={f.price_ebook} onChange={(e) => setF({ ...f, price_ebook: e.target.value })} placeholder="₹199" /></Field>
          <Field label="Buy Now URL (Razorpay / Amazon / etc.)" wide><input className="input-elegant" value={f.buy_url} onChange={(e) => setF({ ...f, buy_url: e.target.value })} placeholder="https://rzp.io/l/your-link" data-testid="book-buy-url" /></Field>
          <Field label="Short description" wide><textarea rows={2} className="input-elegant" value={f.short_description} onChange={(e) => setF({ ...f, short_description: e.target.value })} /></Field>
          <Field label="Description" wide><textarea rows={4} className="input-elegant" value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></Field>
          <Field label="Formats (one per line)"><textarea rows={2} className="input-elegant" value={f.formats} onChange={(e) => setF({ ...f, formats: e.target.value })} /></Field>
          <Field label="Benefits (one per line)"><textarea rows={3} className="input-elegant" value={f.benefits} onChange={(e) => setF({ ...f, benefits: e.target.value })} /></Field>
          <Field label="Who this is for (one per line)"><textarea rows={3} className="input-elegant" value={f.who_for} onChange={(e) => setF({ ...f, who_for: e.target.value })} /></Field>
          <Field label="What you will learn (one per line)"><textarea rows={3} className="input-elegant" value={f.learnings} onChange={(e) => setF({ ...f, learnings: e.target.value })} /></Field>
          <Field label="About the author / publisher" wide><textarea rows={2} className="input-elegant" value={f.about_author} onChange={(e) => setF({ ...f, about_author: e.target.value })} /></Field>
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={() => onSave(f, isNew ? null : book.slug)} className="btn-primary" data-testid="save-book">Save</button>
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
