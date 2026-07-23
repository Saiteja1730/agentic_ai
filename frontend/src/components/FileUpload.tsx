import { useRef, useState } from "react";
import { Paperclip, Loader2, CheckCircle2 } from "lucide-react";
import { uploadPdf } from "../services/api";

interface FileUploadProps {
  sessionId?: string;
  onUploaded: (sessionId: string, filename: string) => void;
}

export default function FileUpload({ sessionId, onUploaded }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [lastUploaded, setLastUploaded] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setError(null);
    try {
      const result = await uploadPdf(file, sessionId);
      setLastUploaded(result.filename);
      onUploaded(result.session_id, result.filename);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Upload failed.");
    } finally {
      setIsUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div className="flex flex-col gap-1">
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={isUploading}
        className="flex items-center gap-2 rounded-lg border border-neutral-300 dark:border-neutral-700 px-3 py-2 text-sm text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors disabled:opacity-50"
      >
        {isUploading ? <Loader2 size={16} className="animate-spin" /> : <Paperclip size={16} />}
        {isUploading ? "Uploading..." : "Attach PDF"}
      </button>
      <input ref={inputRef} type="file" accept="application/pdf" className="hidden" onChange={handleFileChange} />
      {lastUploaded && !isUploading && (
        <span className="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
          <CheckCircle2 size={12} /> {lastUploaded} indexed
        </span>
      )}
      {error && <span className="text-xs text-red-500">{error}</span>}
    </div>
  );
}
