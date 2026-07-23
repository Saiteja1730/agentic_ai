import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, Loader2, User } from "lucide-react";
import SourceCard from "./SourceCard";
import { Source } from "../services/api";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  isStreaming?: boolean;
  statusMessages?: string[];
  route?: string;
}

function RouteBadge({ route }: { route: string }) {
  switch (route) {
    case "GENERAL_SIMPLE":
      return (
        <div className="mb-3 inline-flex items-center gap-1.5 rounded-full bg-blue-100 dark:bg-blue-900/40 px-3 py-1 text-xs font-semibold text-blue-800 dark:text-blue-300">
          🧠 General Knowledge
        </div>
      );
    case "WEB_SIMPLE":
      return (
        <div className="mb-3 inline-flex items-center gap-1.5 rounded-full bg-green-100 dark:bg-green-900/40 px-3 py-1 text-xs font-semibold text-green-800 dark:text-green-300">
          🌐 Web Research
        </div>
      );
    case "PDF_SIMPLE":
      return (
        <div className="mb-3 inline-flex items-center gap-1.5 rounded-full bg-orange-100 dark:bg-orange-900/40 px-3 py-1 text-xs font-semibold text-orange-800 dark:text-orange-300">
          📄 PDF Research
        </div>
      );
    case "COMPLEX_RESEARCH":
      return (
        <div className="mb-3 inline-flex items-center gap-1.5 rounded-full bg-purple-100 dark:bg-purple-900/40 px-3 py-1 text-xs font-semibold text-purple-800 dark:text-purple-300">
          🔀 Hybrid Research
        </div>
      );
    case "CLARIFICATION":
      return (
        <div className="mb-3 inline-flex items-center gap-1.5 rounded-full bg-yellow-100 dark:bg-yellow-900/40 px-3 py-1 text-xs font-semibold text-yellow-800 dark:text-yellow-300">
          ❓ Clarification Needed
        </div>
      );
    default:
      return null;
  }
}

function StatusList({ messages }: { messages: string[] }) {
  return (
    <div className="flex flex-col gap-1.5 text-sm text-neutral-500 dark:text-neutral-400">
      {messages.map((msg, i) => {
        const isLast = i === messages.length - 1;
        return (
          <div key={i} className="flex items-center gap-2">
            {isLast ? (
              <Loader2 size={14} className="animate-spin text-brand-500 shrink-0" />
            ) : (
              <span className="text-brand-500 shrink-0">✓</span>
            )}
            <span className={isLast ? "text-neutral-900 dark:text-neutral-100 font-medium" : ""}>{msg}</span>
          </div>
        );
      })}
    </div>
  );
}

export default function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const hasContent = !!message.content;
  const isStreaming = !!message.isStreaming;
  const statusMessages = message.statusMessages || [];

  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-600 text-white">
          <Bot size={16} />
        </div>
      )}
      <div className={`w-full max-w-4xl ${isUser ? "order-1 flex justify-end" : ""}`}>
        {isUser ? (
          <div className="rounded-2xl bg-brand-600 px-5 py-2.5 text-white max-w-2xl shadow-sm">
            {message.content}
          </div>
        ) : (
          <div className="rounded-2xl bg-white border border-neutral-200 shadow-sm dark:border-neutral-800 dark:bg-neutral-900 px-6 py-5 w-full">
            {message.route && <RouteBadge route={message.route} />}

            {/* Show status steps while streaming and no content yet */}
            {isStreaming && !hasContent && statusMessages.length > 0 && (
              <StatusList messages={statusMessages} />
            )}

            {/* Main answer content */}
            {hasContent && (
              <div className="markdown-body text-[15px] leading-relaxed text-neutral-800 dark:text-neutral-200">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
              </div>
            )}

            {/* Show last status below content if still streaming */}
            {isStreaming && hasContent && statusMessages.length > 0 && (
              <div className="mt-4 border-t border-neutral-100 dark:border-neutral-800 pt-3">
                <div className="flex items-center gap-2 text-sm text-neutral-500 dark:text-neutral-400">
                  <Loader2 size={14} className="animate-spin text-brand-500 shrink-0" />
                  <span className="text-neutral-900 dark:text-neutral-100 font-medium">
                    {statusMessages[statusMessages.length - 1]}
                  </span>
                </div>
              </div>
            )}

            {/* Sources */}
            {message.sources && message.sources.length > 0 && (
              <div className="mt-4 border-t border-neutral-200 dark:border-neutral-800 pt-3">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-neutral-500">Sources</p>
                <div className="flex flex-col gap-2">
                  {Object.entries(
                    message.sources.reduce((acc, source) => {
                      if (source.origin === "pdf") {
                        acc[source.title] = (acc[source.title] || 0) + 1;
                      }
                      return acc;
                    }, {} as Record<string, number>)
                  ).map(([title, count]) => (
                    <div
                      key={title}
                      className="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-400 bg-white dark:bg-neutral-950 px-3 py-2 rounded-lg border border-neutral-200 dark:border-neutral-800"
                    >
                      📄 <span>{title} ({count} chunk{count !== 1 ? "s" : ""})</span>
                    </div>
                  ))}
                  {message.sources
                    .filter((s) => s.origin !== "pdf")
                    .map((source, idx) => (
                      <SourceCard key={idx} source={source} index={idx + 1} />
                    ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
      {isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-neutral-300 dark:bg-neutral-700 order-2">
          <User size={16} />
        </div>
      )}
    </div>
  );
}
