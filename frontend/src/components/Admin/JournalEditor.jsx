import { useEffect, useRef, useState } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Image from "@tiptap/extension-image";
import Typography from "@tiptap/extension-typography";
import axios from "axios";
import { API, TOKEN_KEY } from "../../lib/api";

export default function JournalEditor({ initialData = null, onSave, onPublish, onChange, embedded = false }) {
  const [title, setTitle] = useState(initialData?.title || "");
  const [status, setStatus] = useState("idle");
  const [lastSaved, setLastSaved] = useState(null);
  const imageInputRef = useRef(null);

  const editor = useEditor({
    extensions: [StarterKit, Image.configure({ inline: false }), Typography],
    content: initialData?.content_html || (initialData?.content || "").split("\n\n").map((p) => `<p>${p.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")}</p>`).join(""),
    onUpdate: ({ editor: updatedEditor }) => onChange?.({ content_html: updatedEditor.getHTML(), content: updatedEditor.getText({ blockSeparator: "\n\n" }) }),
    editorProps: {
      attributes: {
        class: "reader-canvas reader-content",
        style: "min-height:400px;outline:none;padding:2rem 0",
      },
    },
  });

  useEffect(() => {
    if (initialData?.title) setTitle(initialData.title);
  }, [initialData?.title]);

  const onPickImage = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !editor) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      const token = localStorage.getItem(TOKEN_KEY);
      const headers = { "Content-Type": "multipart/form-data" };
      if (token) headers.Authorization = `Bearer ${token}`;
      const { data } = await axios.post(`${API}/admin/upload/image?confirm_expensive_job=true`, fd, { headers });
      editor.chain().focus().setImage({ src: data.url }).run();
    } catch {
      setStatus("Image upload failed. Please try again.")
    } finally {
      e.target.value = "";
    }
  };

  const tbBtn = (active) => ({
    padding: 8,
    borderRadius: 6,
    fontFamily: "Inter, sans-serif",
    fontSize: 13,
    background: active ? "rgba(107,16,32,0.12)" : "transparent",
    color: active ? "#6B1020" : "#7A5C62",
    border: "none",
    cursor: "pointer",
  });

  const saveDraft = async () => {
    if (!editor) return;
    setStatus("saving");
    const body = { ...initialData, title, content_html: editor.getHTML(), content: editor.getText(), is_published: false };
    try {
      const token = localStorage.getItem(TOKEN_KEY);
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      if (initialData?._id || initialData?.slug) {
        const idOrSlug = initialData.slug || initialData._id;
        await axios.put(`${API}/admin/blog/${idOrSlug}`, body, { headers });
      } else {
        await axios.post(`${API}/admin/blog`, body, { headers });
      }
      setLastSaved(new Date());
      setStatus("idle");
      onSave?.();
    } catch {
      setStatus("idle");
    }
  };

  const publish = async () => {
    if (!editor) return;
    setStatus("publishing");
    const body = {
      title,
      content_html: editor.getHTML(),
      excerpt: editor.getText().slice(0, 200),
      is_published: true,
    };
    try {
      const token = localStorage.getItem(TOKEN_KEY);
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const { data } = initialData?.slug ? await axios.put(`${API}/admin/blog/${initialData.slug}`, body, { headers }) : await axios.post(`${API}/admin/blog`, body, { headers });
      setStatus("idle");
      onPublish?.(data);
    } catch {
      setStatus("idle");
    }
  };

  const openPreview = () => {
    const html = editor?.getHTML() || "";
    const win = window.open("", "_blank");
    if (!win) return;
    win.opener = null;
    win.document.title = title || "Preview";
    const heading = win.document.createElement("h1");
    heading.textContent = title || "Preview";
    win.document.body.appendChild(heading);
    const frame = win.document.createElement("iframe");
    frame.setAttribute("sandbox", "");
    frame.setAttribute("title", "Article preview");
    frame.style.cssText = "width:100%;height:85vh;border:0";
    frame.srcdoc = `<html><head><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src https:; style-src 'unsafe-inline'"><style>body{background:#F6E8D7;color:#261914;font:22px/1.6 Georgia,serif;padding:24px;max-width:760px;margin:auto}img{max-width:100%;height:auto}</style></head><body>${html}</body></html>`;
    win.document.body.appendChild(frame);
  };

  return (
    <div style={{ background: "#FAF7F0", color: "#1C0A0E" }}>
      <div
        className="px-4 py-2 flex gap-1 flex-wrap"
        style={{ background: "#F5F0E8", borderBottom: "1px solid #E8DDD8" }}
      >
        <button type="button" onClick={() => editor?.chain().focus().toggleBold().run()} style={{ ...tbBtn(editor?.isActive("bold")), fontWeight: 700 }}>B</button>
        <button type="button" onClick={() => editor?.chain().focus().toggleItalic().run()} style={{ ...tbBtn(editor?.isActive("italic")), fontStyle: "italic" }}>I</button>
        <button type="button" onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()} style={tbBtn(editor?.isActive("heading", { level: 2 }))}>H2</button>
        <button type="button" onClick={() => editor?.chain().focus().toggleHeading({ level: 3 }).run()} style={tbBtn(editor?.isActive("heading", { level: 3 }))}>H3</button>
        <button type="button" onClick={() => editor?.chain().focus().toggleBlockquote().run()} style={tbBtn(editor?.isActive("blockquote"))}>"</button>
        <button type="button" onClick={() => editor?.chain().focus().toggleBulletList().run()} style={tbBtn(editor?.isActive("bulletList"))}>•</button>
        <button type="button" onClick={() => editor?.chain().focus().toggleOrderedList().run()} style={tbBtn(editor?.isActive("orderedList"))}>1.</button>
        <button type="button" onClick={() => editor?.chain().focus().setHorizontalRule().run()} style={tbBtn(false)}>─</button>
        <button type="button" onClick={() => { const href = window.prompt("Link URL (https://…)"); if (href && /^https?:\/\//i.test(href)) editor?.chain().focus().extendMarkRange("link").setLink({ href }).run(); }} style={tbBtn(editor?.isActive("link"))}>Link</button>
        <button type="button" aria-label="Upload article photograph" onClick={() => imageInputRef.current?.click()} style={tbBtn(false)}>🖼</button>
        <input ref={imageInputRef} type="file" accept="image/*" hidden onChange={onPickImage} />
      </div>

      {!embedded && <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Journal entry title…"
        style={{
          width: "100%",
          background: "transparent",
          border: "none",
          outline: "none",
          padding: "1.5rem 0 0.5rem",
          marginBottom: 8,
          fontFamily: "'Cormorant Garamond', serif",
          fontSize: 32,
          fontWeight: 500,
          color: "#1C0A0E",
        }}
      />}

      <hr style={{ border: 0, borderTop: "1px solid #E8DDD8" }} />

      <EditorContent editor={editor} />

      {embedded && status !== "idle" && <p role="status">{status}</p>}
      {!embedded && <div
        style={{
          position: "sticky",
          bottom: 0,
          background: "rgba(250,247,240,0.93)",
          borderTop: "1px solid #E8DDD8",
          backdropFilter: "blur(8px)",
          padding: "12px 16px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span style={{ fontFamily: "Inter, sans-serif", fontSize: 12, color: "#A88A8F" }}>
          {lastSaved ? `Saved ${lastSaved.toLocaleTimeString()}` : "Unsaved"}
        </span>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            type="button"
            onClick={saveDraft}
            disabled={status === "saving"}
            style={{
              background: "#F5F0E8",
              color: "#6B1020",
              border: "1px solid #E8DDD8",
              borderRadius: 8,
              padding: "8px 16px",
              fontFamily: "Inter, sans-serif",
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            {status === "saving" ? "Saving…" : "Save Draft"}
          </button>
          <button
            type="button"
            onClick={openPreview}
            style={{
              background: "#F5F0E8",
              color: "#6B1020",
              border: "1px solid #E8DDD8",
              borderRadius: 8,
              padding: "8px 16px",
              fontFamily: "Inter, sans-serif",
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            Preview
          </button>
          <button
            type="button"
            onClick={publish}
            disabled={status === "publishing"}
            style={{
              background: "#6B1020",
              color: "#FAF7F0",
              border: "none",
              borderRadius: 8,
              padding: "8px 16px",
              fontFamily: "Inter, sans-serif",
              fontSize: 13,
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            {status === "publishing" ? "Publishing…" : "Publish →"}
          </button>
        </div>
      </div>}
    </div>
  );
}
