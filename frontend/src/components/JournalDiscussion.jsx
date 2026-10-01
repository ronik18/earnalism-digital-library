import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Heart, MessageCircle } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, userApi } from "../lib/api";

export default function JournalDiscussion({ slug }) {
  const { user } = useAuth();
  const generationRef = useRef(0);
  const [discussion, setDiscussion] = useState({ likes: 0, comments: [] });
  const [loading, setLoading] = useState(true);
  const [liked, setLiked] = useState(false);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let current = true;
    generationRef.current += 1;
    setText(""); setBusy(false);
    setLiked(false); setError(""); setLoading(true); setDiscussion({ likes: 0, comments: [] });
    api.get(`/blog/${slug}/discussion`).then(({ data }) => { if (current) setDiscussion(data); }).catch(() => { if (current) setError("The conversation could not be loaded. Please try again later."); }).finally(() => { if (current) setLoading(false); });
    if (user) userApi.get(`/blog/${slug}/my-like`).then(({ data }) => { if (current) setLiked(data.liked); }).catch(() => {});
    return () => { current = false; generationRef.current += 1; };
  }, [slug, user]);
  const toggleLike = async () => {
    const generation = generationRef.current;
    setBusy(true); setError("");
    try {
      const { data } = liked ? await userApi.delete(`/blog/${slug}/like`) : await userApi.put(`/blog/${slug}/like`);
      if (generation !== generationRef.current) return;
      setLiked(data.liked); setDiscussion((prev) => ({ ...prev, likes: data.likes }));
    } catch { if (generation === generationRef.current) setError("Your like could not be saved. Please try again."); }
    finally { if (generation === generationRef.current) setBusy(false); }
  };
  const submit = async (event) => {
    event.preventDefault(); if (!text.trim()) return;
    const generation = generationRef.current;
    setBusy(true); setError("");
    try {
      const { data } = await userApi.post(`/blog/${slug}/comments`, { text: text.trim() });
      if (generation !== generationRef.current) return;
      setDiscussion((prev) => ({ ...prev, comments: [data, ...prev.comments] })); setText("");
    } catch { if (generation === generationRef.current) setError("Your comment could not be saved. Please try again."); }
    finally { if (generation === generationRef.current) setBusy(false); }
  };
  return <section className="journal-discussion" aria-label="Article discussion">
    {loading && <p role="status">Opening the conversation…</p>}
    <div className="journal-discussion__actions">
      {user ? <button type="button" aria-pressed={liked} disabled={busy || loading} onClick={toggleLike}><Heart size={20} fill={liked ? "currentColor" : "none"} />{liked ? "Liked" : "Like"}{!loading && ` · ${discussion.likes}`}</button> : <Link to={`/login?next=${encodeURIComponent(`/journal/${slug}`)}`}><Heart size={20} /> Sign in to like</Link>}
      <a href="#article-conversation"><MessageCircle size={20} /> Join the conversation{!loading && ` · ${discussion.comments.length}`}</a>
    </div>
    <h2 id="article-conversation">What stayed with you?</h2>
    <p className="journal-discussion__guidance">Keep the conversation thoughtful and respectful. Your display name and comment will be public.</p>
    {user ? <form onSubmit={submit}><label className="sr-only" htmlFor="journal-comment">Your comment</label><textarea id="journal-comment" required maxLength={2000} value={text} onChange={(e) => setText(e.target.value)} placeholder="Share a thoughtful response…" /><button className="btn-primary" disabled={busy || !text.trim()}>{busy ? "Saving…" : "Post comment"}</button></form> : <p><Link to={`/login?next=${encodeURIComponent(`/journal/${slug}`)}`}>Sign in</Link> to share a thoughtful response.</p>}
    {error && <p role="alert">{error}</p>}
    <div aria-live="polite">{discussion.comments.map((comment) => <article key={comment.id} className="journal-comment"><span className="journal-comment__avatar" aria-hidden="true">{String(comment.author || "Reader").slice(0, 2).toUpperCase()}</span><div><strong>{comment.author}</strong><time dateTime={comment.created_at}>{new Date(comment.created_at).toLocaleDateString()}</time><p>{comment.text}</p></div></article>)}</div>
  </section>;
}
