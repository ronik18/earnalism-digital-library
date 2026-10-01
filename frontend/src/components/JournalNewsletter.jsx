import { useState } from "react";
import { api } from "../lib/api";
export default function JournalNewsletter() {
  const [name, setName] = useState(""); const [email, setEmail] = useState(""); const [busy, setBusy] = useState(false); const [status, setStatus] = useState("");
  const submit = async (event) => { event.preventDefault(); setBusy(true); setStatus(""); try { await api.post("/newsletter", { name: name.trim(), email: email.trim() }); setStatus("Thank you. You’re on the list."); setName(""); setEmail(""); } catch { setStatus("Your subscription could not be saved. Please try again."); } finally { setBusy(false); } };
  return <section className="journal-newsletter" aria-label="Journal newsletter"><div><h2>Letters for a more thoughtful you.</h2><p>Reading notes and new arrivals — straight to your inbox.</p></div><form onSubmit={submit}><label><span className="sr-only">Your name</span><input required autoComplete="name" placeholder="Your name" value={name} onChange={(e) => setName(e.target.value)} /></label><label><span className="sr-only">Email address</span><input required type="email" autoComplete="email" placeholder="Your email address" value={email} onChange={(e) => setEmail(e.target.value)} /></label><button className="btn-primary" disabled={busy}>{busy ? "Subscribing…" : "Subscribe"}</button><p role="status">{status}</p></form></section>;
}
