import { useEffect, useRef, useState } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Image from "@tiptap/extension-image";
import Typography from "@tiptap/extension-typography";
import axios from "axios";
import { API, TOKEN_KEY } from "../../lib/api";

export default function JournalEditor({ initialData = null, onSave, onPublish }) {
  const [title, setTitle] = useState(initialData?.title || "");
  const [status, setStatus] = useState("idle");
  const [lastSaved, setLastSaved] = useState(null);
  const imageInputRef = useRef(null);

  const editor = useEditor({
    extensions: [StarterKit, Image.configure({ inline: false }), Typography],
    content: initialData?.content_html || "",
    editorProps: {
      attributes: {
        class: "reader-canvas reader-content reader-journal-editor__content",
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
      const { data } = await axios.post(`${API}/admin/upload/image`, fd, { headers });
      editor.chain().focus().setImage({ src: data.url }).run();
    } catch {
      // swallow — toolbar stays available
    } finally {
      e.target.value = "";
    }
  };

  const tbBtnClass = (active) => `reader-journal-toolbar-btn${active ? " reader-journal-toolbar-btn--active" : ""}`;

  const saveDraft = async () => {
    if (!editor) return;
    setStatus("saving");
    const body = { title, content_html: editor.getHTML(), is_draft: true };
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
      is_draft: false,
    };
    try {
      const token = localStorage.getItem(TOKEN_KEY);
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const { data } = await axios.post(`${API}/admin/blog`, body, { headers });
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
    win.document.write(`<!DOCTYPE html><html><head><title>${title || "Preview"}</title>
      <link rel="stylesheet" href="${window.location.origin}/static/css/main.css"/>
      <style>.reader-journal-preview{background:#FAF7F0;margin:0;padding:48px 16px;}.reader-journal-preview__title{font-family:var(--font-display, var(--font-body));color:#6B1020;}</style>
      </head><body class="reader-journal-preview"><div class="reader-canvas reader-content"><h1 class="reader-journal-preview__title">${title}</h1>${html}</div></body></html>`);
    win.document.close();
  };

  return (
    <div className="reader-journal-shell">
      <div className="reader-journal-toolbar">
        <button type="button" onClick={() => editor?.chain().focus().toggleBold().run()} className={`${tbBtnClass(editor?.isActive("bold"))} reader-journal-toolbar-btn reader-journal-toolbar-btn--semibold`}>B</button>
        <button type="button" onClick={() => editor?.chain().focus().toggleItalic().run()} className={`${tbBtnClass(editor?.isActive("italic"))} reader-journal-toolbar-btn--emphasis`}>I</button>
        <button type="button" onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()} className={tbBtnClass(editor?.isActive("heading", { level: 2 }))}>H2</button>
        <button type="button" onClick={() => editor?.chain().focus().toggleHeading({ level: 3 }).run()} className={tbBtnClass(editor?.isActive("heading", { level: 3 }))}>H3</button>
        <button type="button" onClick={() => editor?.chain().focus().toggleBlockquote().run()} className={tbBtnClass(editor?.isActive("blockquote"))}>"</button>
        <button type="button" onClick={() => editor?.chain().focus().toggleBulletList().run()} className={tbBtnClass(editor?.isActive("bulletList"))}>•</button>
        <button type="button" onClick={() => editor?.chain().focus().toggleOrderedList().run()} className={tbBtnClass(editor?.isActive("orderedList"))}>1.</button>
        <button type="button" onClick={() => editor?.chain().focus().setHorizontalRule().run()} className={tbBtnClass(false)}>─</button>
        <button type="button" onClick={() => imageInputRef.current?.click()} className={tbBtnClass(false)}>🖼</button>
        <input ref={imageInputRef} type="file" accept="image/*" hidden onChange={onPickImage} />
      </div>

      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Journal entry title…"
        className="reader-journal-title"
      />

      <hr className="reader-journal-divider" />

      <EditorContent editor={editor} />

      <div className="reader-journal-action-bar">
        <span className="reader-journal-meta">
          {lastSaved ? `Saved ${lastSaved.toLocaleTimeString()}` : "Unsaved"}
        </span>
        <div className="flex gap-2">
          <button type="button" onClick={saveDraft} disabled={status === "saving"} className="reader-journal-action-btn">
            {status === "saving" ? "Saving…" : "Save Draft"}
          </button>
          <button type="button" onClick={openPreview} className="reader-journal-action-btn">
            Preview
          </button>
          <button type="button" onClick={publish} disabled={status === "publishing"} className="reader-journal-action-btn">
            {status === "publishing" ? "Publishing…" : "Publish →"}
          </button>
        </div>
      </div>
    </div>
  );
}
