import { FileText, Globe } from "lucide-react";
import { Source } from "../services/api";

export default function SourceCard({ source, index }: { source: Source; index: number }) {
  const isPdf = source.origin === "pdf";

  const content = (
    <div className="flex items-start gap-2 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-900 p-3 hover:border-brand-500 transition-colors">
      <div className="mt-0.5 shrink-0 text-brand-600 dark:text-brand-500">
        {isPdf ? <FileText size={16} /> : <Globe size={16} />}
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium text-neutral-500 dark:text-neutral-400">
          [{index}] {isPdf ? "PDF Document" : "Web Source"}
        </p>
        <p className="truncate text-sm font-medium text-neutral-900 dark:text-neutral-100">
          {source.title}
        </p>
        {source.snippet && (
          <p className="mt-1 line-clamp-2 text-xs text-neutral-500 dark:text-neutral-400">
            {source.snippet}
          </p>
        )}
      </div>
    </div>
  );

  if (source.url) {
    return (
      <a href={source.url} target="_blank" rel="noreferrer" className="block">
        {content}
      </a>
    );
  }
  return content;
}
