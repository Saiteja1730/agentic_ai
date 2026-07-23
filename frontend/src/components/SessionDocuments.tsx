import { useEffect, useState } from "react";
import { Trash2 } from "lucide-react";
import axios from "axios";
import { API_BASE_URL } from "../services/api";

interface SessionDocumentsProps {
  sessionId: string;
  updateTrigger?: number;
  onClearSession: () => void;
}

export default function SessionDocuments({ sessionId, updateTrigger, onClearSession }: SessionDocumentsProps) {
  const [files, setFiles] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchFiles();
  }, [sessionId, updateTrigger]);

  const fetchFiles = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/session/${sessionId}/files`);
      setFiles(res.data.files || []);
    } catch (err) {
      console.error("Failed to fetch session files", err);
    }
  };

  const handleRemove = async (filename: string) => {
    if (!window.confirm(`Remove "${filename}" from this research session?`)) return;

    setLoading(true);
    try {
      await axios.delete(`${API_BASE_URL}/session/${sessionId}/files/${encodeURIComponent(filename)}`);
      setFiles((prev) => prev.filter((f) => f !== filename));
    } catch (err) {
      console.error("Failed to remove file", err);
      alert("Failed to remove the document. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleClearSession = async () => {
    if (!window.confirm("Clear all documents from this session? This cannot be undone.")) return;

    setLoading(true);
    try {
      await axios.delete(`${API_BASE_URL}/session/${sessionId}`);
      setFiles([]);
      onClearSession();
    } catch (err) {
      console.error("Failed to clear session", err);
      alert("Failed to clear the session. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (files.length === 0) {
    return (
      <div className="mb-4 rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-4 w-full">
        <h3 className="mb-3 text-sm font-semibold text-neutral-900 dark:text-neutral-100">
          Current Research Documents
        </h3>
        <p className="text-sm text-neutral-500 dark:text-neutral-400">No documents uploaded.</p>
      </div>
    );
  }

  return (
    <div className="mb-4 rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-4 w-full">
      <h3 className="mb-3 text-sm font-semibold text-neutral-900 dark:text-neutral-100">
        Current Research Documents
      </h3>
      <ul className="mb-4 space-y-2">
        {files.map((file) => (
          <li key={file} className="flex items-center justify-between text-sm bg-neutral-50 dark:bg-neutral-950 p-2 rounded-lg border border-neutral-100 dark:border-neutral-800">
            <span className="truncate flex-1 text-neutral-700 dark:text-neutral-300" title={file}>
              ✓ {file}
            </span>
            <button
              onClick={() => handleRemove(file)}
              disabled={loading}
              aria-label={`Remove ${file}`}
              className="ml-2 text-red-500 hover:text-red-700 disabled:opacity-50 text-xs flex items-center gap-1 transition-colors"
            >
              <Trash2 size={12} /> Remove
            </button>
          </li>
        ))}
      </ul>
      <button
        onClick={handleClearSession}
        disabled={loading}
        className="w-full rounded-lg py-2 text-sm font-medium text-red-600 bg-red-50 hover:bg-red-100 dark:text-red-400 dark:bg-red-950/30 dark:hover:bg-red-950/50 transition-colors disabled:opacity-50"
      >
        {loading ? "Clearing…" : "Clear Session"}
      </button>
    </div>
  );
}
