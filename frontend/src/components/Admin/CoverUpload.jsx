import { useCallback, useEffect, useMemo, useState } from "react";
import { useDropzone } from "react-dropzone";
import { ImageOff, ImagePlus } from "lucide-react";
import { api } from "../../lib/api";
import { imageUrlCandidates, optimizedImageUrl } from "../../lib/images";

const ACCEPTED = {
  "image/jpeg": [".jpg", ".jpeg"],
  "image/png": [".png"],
  "image/webp": [".webp"],
};
const MAX_COVER_BYTES = 4 * 1024 * 1024;

export default function CoverUpload({
  bookId,
  kind = "front",
  currentUrl = "",
  bookTitle = "",
  bookAuthor = "",
  onSuccess,
}) {
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");
  const [progress, setProgress] = useState(0);
  const [candidateIndex, setCandidateIndex] = useState(0);
  const [previewFailed, setPreviewFailed] = useState(false);

  const label = kind === "back" ? "Back cover" : "Front cover";
  const candidates = useMemo(() => imageUrlCandidates(currentUrl), [currentUrl]);
  const previewUrl = candidates[candidateIndex] ? optimizedImageUrl(candidates[candidateIndex], { width: 320 }) : "";

  useEffect(() => {
    setCandidateIndex(0);
    setPreviewFailed(false);
  }, [currentUrl]);

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
        const { data } = await api.post(`/admin/books/${bookId}/cover`, fd, {
          params: { kind, confirm_expensive_job: true },
          onUploadProgress: (evt) => {
            if (evt.total) setProgress(Math.round((evt.loaded * 100) / evt.total));
          },
        });
        setProgress(100);
        setStatus("done");
        setPreviewFailed(false);
        setCandidateIndex(0);
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
      setError(items?.[0]?.errors?.[0]?.message || "Use JPG, PNG, or WebP under 4MB.");
    },
    accept: ACCEPTED,
    disabled: status === "uploading" || !bookId,
    maxFiles: 1,
    maxSize: MAX_COVER_BYTES,
  });

  return (
    <div className="rounded-xl border border-brand-soft bg-ivory-warm/60 p-4">
      <div className="flex items-start gap-4">
        <div className="aspect-[3/4] w-20 shrink-0 overflow-hidden rounded-md border border-brand-soft bg-beige-deep">
          {previewUrl && !previewFailed ? (
            <img
              src={previewUrl}
              alt={`${label} preview${bookTitle ? ` for ${bookTitle}${bookAuthor ? ` by ${bookAuthor}` : ""}` : ""}`}
              className="h-full w-full object-contain"
              onError={() => {
                if (candidateIndex + 1 < candidates.length) {
                  setCandidateIndex((index) => index + 1);
                } else {
                  setPreviewFailed(true);
                }
              }}
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-charcoal-soft">
              {currentUrl ? <ImageOff size={20} strokeWidth={1.5} /> : <ImagePlus size={20} strokeWidth={1.5} />}
            </div>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="overline mb-2">{label}</div>
          <div
            {...getRootProps()}
            className={`rounded-lg border border-dashed px-4 py-3 text-sm transition-colors ${status === "uploading" ? "cursor-not-allowed opacity-70" : "cursor-pointer"}`}
            style={{
              borderColor: isDragActive ? "#6B1020" : "#E5DCD3",
              background: isDragActive ? "rgba(107,16,32,0.04)" : "rgba(253,252,248,0.7)",
            }}
          >
            <input
              {...getInputProps({
                "aria-label": `Upload ${label.toLowerCase()} image`,
                "data-testid": `cover-upload-${kind}-${bookId}`,
              })}
            />
            <span className="text-burgundy">{isDragActive ? "Drop cover image" : "Upload image"}</span>
            <span className="block text-[0.72rem] text-charcoal-soft">JPG, PNG, WebP · portrait · max 4MB</span>
          </div>
          {previewFailed && <div className="mt-2 text-[0.72rem] text-burgundy">Preview image not found. Check the URL or upload a new cover.</div>}
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
