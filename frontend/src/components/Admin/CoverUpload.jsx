import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import axios from "axios";
import { ImagePlus } from "lucide-react";
import { API, TOKEN_KEY } from "../../lib/api";

const ACCEPTED = {
  "image/jpeg": [".jpg", ".jpeg"],
  "image/png": [".png"],
  "image/webp": [".webp"],
  "image/gif": [".gif"],
};

export default function CoverUpload({ bookId, kind = "front", currentUrl = "", onSuccess }) {
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");
  const [progress, setProgress] = useState(0);

  const label = kind === "back" ? "Back cover" : "Front cover";

  const onDrop = useCallback(
    async (files) => {
      const file = files?.[0];
      if (!file) return;
      setStatus("uploading");
      setProgress(0);
      setError("");

      const fd = new FormData();
      fd.append("file", file);
      try {
        const token = localStorage.getItem(TOKEN_KEY);
        const headers = { "Content-Type": "multipart/form-data" };
        if (token) headers.Authorization = `Bearer ${token}`;
        const { data } = await axios.post(`${API}/admin/books/${bookId}/cover?kind=${kind}`, fd, {
          headers,
          onUploadProgress: (evt) => {
            if (evt.total) setProgress(Math.round((evt.loaded * 100) / evt.total));
          },
        });
        setStatus("done");
        onSuccess?.(data);
      } catch (err) {
        setStatus("error");
        setError(err.response?.data?.detail || err.message || "Cover upload failed");
      }
    },
    [bookId, kind, onSuccess],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    onDropRejected: (items) => {
      setStatus("error");
      setError(items?.[0]?.errors?.[0]?.message || "Use JPG, PNG, WebP, or GIF under 10MB.");
    },
    accept: ACCEPTED,
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024,
  });

  return (
    <div className="rounded-xl border border-brand-soft bg-ivory-warm/60 p-4">
      <div className="flex items-start gap-4">
        <div className="aspect-[3/4] w-20 shrink-0 overflow-hidden rounded-md border border-brand-soft bg-beige-deep">
          {currentUrl ? (
            <img src={currentUrl} alt={`${label} preview`} className="h-full w-full object-contain" />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-charcoal-soft">
              <ImagePlus size={20} strokeWidth={1.5} />
            </div>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="overline mb-2">{label}</div>
          <div
            {...getRootProps()}
            className="cursor-pointer rounded-lg border border-dashed px-4 py-3 text-sm transition-colors"
            style={{
              borderColor: isDragActive ? "#6B1020" : "#E5DCD3",
              background: isDragActive ? "rgba(107,16,32,0.04)" : "rgba(253,252,248,0.7)",
            }}
          >
            <input {...getInputProps()} />
            <span className="text-burgundy">{isDragActive ? "Drop cover image" : "Upload image"}</span>
            <span className="block text-[0.72rem] text-charcoal-soft">JPG, PNG, WebP, GIF · max 10MB</span>
          </div>
          {status === "uploading" && (
            <div className="mt-3">
              <div className="h-1.5 overflow-hidden rounded-full bg-beige-deep">
                <div className="h-full bg-burgundy transition-all" style={{ width: `${progress}%` }} />
              </div>
              <div className="mt-1 text-[0.72rem] text-charcoal-soft">Uploading… {progress}%</div>
            </div>
          )}
          {status === "done" && <div className="mt-2 text-[0.72rem] text-burgundy">Cover saved and optimized.</div>}
          {status === "error" && <div className="mt-2 text-[0.72rem] text-burgundy">{error}</div>}
        </div>
      </div>
    </div>
  );
}
