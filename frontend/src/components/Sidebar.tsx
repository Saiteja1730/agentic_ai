import { MessageSquarePlus, Sparkles } from "lucide-react";
import SessionDocuments from "./SessionDocuments";

export interface Conversation {
  id: string;
  title: string;
}

interface SidebarProps {
  conversations: Conversation[];
  activeId: string | null;
  sessionId: string | null;
  uploadCount: number;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  onClearSession: () => void;
}

export default function Sidebar({
  conversations,
  activeId,
  sessionId,
  uploadCount,
  onSelect,
  onNewChat,
  onClearSession
}: SidebarProps) {
  return (
    <aside className="hidden md:flex w-72 shrink-0 flex-col border-r border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-950 p-4">
      <div className="mb-4 flex items-center gap-2 px-1">
        <Sparkles className="text-brand-600" size={20} />
        <span className="font-semibold text-neutral-900 dark:text-neutral-100">Research Assistant</span>
      </div>

      <button
        onClick={onNewChat}
        className="mb-4 flex items-center gap-2 rounded-lg border border-neutral-300 dark:border-neutral-700 px-3 py-2 text-sm text-neutral-700 dark:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-900 transition-colors"
      >
        <MessageSquarePlus size={16} />
        New research
      </button>

      <div className="flex-1 overflow-y-auto mb-4">
        <p className="mb-2 px-1 text-xs font-medium uppercase text-neutral-400">History (this session)</p>
        <div className="flex flex-col gap-1">
          {conversations.length === 0 && (
            <p className="px-1 text-xs text-neutral-400">No conversations yet.</p>
          )}
          {conversations.map((c) => (
            <button
              key={c.id}
              onClick={() => onSelect(c.id)}
              className={`truncate rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                c.id === activeId
                  ? "bg-brand-100 dark:bg-brand-700/30 text-brand-700 dark:text-brand-300"
                  : "text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-900"
              }`}
            >
              {c.title}
            </button>
          ))}
        </div>
      </div>

      {sessionId ? (
        <SessionDocuments 
          sessionId={sessionId} 
          updateTrigger={uploadCount}
          onClearSession={onClearSession} 
        />
      ) : (
        <div className="mb-4 rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-4 w-full">
          <h3 className="mb-3 text-sm font-semibold text-neutral-900 dark:text-neutral-100">
            Current Research Documents
          </h3>
          <p className="text-sm text-neutral-500 dark:text-neutral-400">No documents uploaded.</p>
        </div>
      )}

      <p className="px-1 pt-2 text-[11px] text-neutral-400">
        History is temporary and clears on refresh.
      </p>
    </aside>
  );
}
