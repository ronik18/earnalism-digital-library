import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import axios from "axios";
import { API, TOKEN_KEY } from "../../lib/api";

const ACCEPTED = {
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "text/markdown": [".md", ".markdown"],
  "text/html": [".html"],
  "text/plain": [".txt"],
};

export default function ChapterUpload({ bookId, chapterId, onSuccess }) {
  const [status, setStatus] = useState("idle"); // idle | uploading | done | error
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(0);

  const onDrop = useCallback(
    async (files) => {
      const file = files?.[0];
      if (!file) return;
      setStatus("uploading");
      setProgress(0);
      setError(null);
      setResult(null);
      const fd = new FormData();
      fd.append("file", file);
      try {
        const token = localStorage.getItem(TOKEN_KEY);
        const headers = { "Content-Type": "multipart/form-data" };
        if (token) headers.Authorization = `Bearer ${token}`;
        const { data } = await axios.post(
          `${API}/admin/books/${bookId}/chapters/${chapterId}/upload`,
          fd,
          {
            headers,
            onUploadProgress: (evt) => {
              if (evt.total) setProgress(Math.round((evt.loaded * 100) / evt.total));
            },
          }
        );
        setResult(data);
        setStatus("done");
        onSuccess?.(data);
      } catch (err) {
        setError(err.response?.data?.detail || err.message || "Upload failed");
        setStatus("error");
      }
    },
    [bookId, chapterId, onSuccess]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    maxFiles: 1,
  });

  return (
    <div className="w-full">
      <div
        {...getRootProps()}
        className="rounded-xl border-2 border-dashed transition-colors cursor-pointer p-8 text-center"
        style={{
          borderColor: isDragActive ? "#6B1020" : "#E8DDD8",
          background: isDragActive ? "rgba(107,16,32,0.04)" : "#FAF7F0",
        }}
      >
        <input {...getInputProps()} />
        <div style={{ fontSize: 32 }}>📄</div>
        <div
          style={{
            fontFamily: "'Crimson Pro', Georgia, serif",
            fontSize: 17,
            color: "#1C0A0E",
            marginTop: 8,
          }}
        >
          {isDragActive ? "Drop the file here" : "Drag chapter file here"}
        </div>
        <div
          style={{
            fontFamily: "Inter, sans-serif",
            fontSize: 12,
            color: "#A88A8F",
            marginTop: 6,
          }}
        >
          DOCX · Markdown · HTML · TXT — up to 50MB
        </div>
      </div>

      {status === "uploading" && (
        <div className="mt-4">
          <div
            style={{
              height: 6,
              background: "#E8DDD8",
              borderRadius: 3,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${progress}%`,
                height: "100%",
                background: "#6B1020",
                transition: "width 200ms ease",
              }}
            />
          </div>
          <div
            style={{
              fontFamily: "Inter, sans-serif",
              fontSize: 12,
              color: "#7A5C62",
              marginTop: 6,
            }}
          >
            Uploading… {progress}%
          </div>
        </div>
      )}

      {status === "done" && result && (
        <div
          className="mt-4 rounded-xl p-4"
          style={{
            background: "rgba(107,16,32,0.06)",
            border: "1px solid rgba(107,16,32,0.15)",
            color: "#6B1020",
            fontFamily: "Inter, sans-serif",
            fontSize: 13,
          }}
        >
          ✓ Saved · {result.word_count} words · {result.reading_minutes} min read · {result.image_count} image{result.image_count === 1 ? "" : "s"}
        </div>
      )}

      {status === "error" && (
        <div
          className="mt-4 rounded-xl p-4"
          style={{
            background: "#F9F0F2",
            color: "#6B1020",
            fontFamily: "Inter, sans-serif",
            fontSize: 13,
          }}
        >
          {error}
        </div>
      )}
    </div>
  );
}
