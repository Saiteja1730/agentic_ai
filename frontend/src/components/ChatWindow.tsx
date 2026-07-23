import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";
import MessageBubble, { ChatMessage } from "./MessageBubble";
import FileUpload from "./FileUpload";
import { useChatStream } from "../hooks/useChatStream";

interface ChatWindowProps {
  sessionId: string | null;
  clearTrigger: number;
  onSessionCreated: (sessionId: string) => void;
  onFirstMessage: (question: string) => void;
  onUploaded: (sid: string, filename: string) => void;
}

export default function ChatWindow({ sessionId, clearTrigger, onSessionCreated, onFirstMessage, onUploaded }: ChatWindowProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const { isStreaming, currentStatus, result, error, sendQuestion } = useChatStream();
  const bottomRef = useRef<HTMLDivElement>(null);
  const assistantMsgId = useRef<string | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, currentStatus]);

  useEffect(() => {
    if (clearTrigger > 0) {
      setMessages([]);
      setInput("");
      assistantMsgId.current = null;
    }
  }, [clearTrigger]);

  useEffect(() => {
    if (!assistantMsgId.current) return;
    setMessages((prev) =>
      prev.map((m) => {
        if (m.id === assistantMsgId.current) {
          const newStatus = currentStatus?.message;
          let updatedStatuses = m.statusMessages || [];
          if (newStatus && !updatedStatuses.includes(newStatus)) {
            updatedStatuses = [...updatedStatuses, newStatus];
          }
          return { ...m, statusMessages: updatedStatuses, isStreaming };
        }
        return m;
      })
    );
  }, [currentStatus, isStreaming]);

  useEffect(() => {
    if (!result || !assistantMsgId.current) return;
    const route = result.metrics?.route;
    setMessages((prev) =>
      prev.map((m) =>
        m.id === assistantMsgId.current
          ? { ...m, content: result.final_answer, sources: result.sources, route, isStreaming: false }
          : m
      )
    );
    if (result.session_id) onSessionCreated(result.session_id);
  }, [result]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!error || !assistantMsgId.current) return;
    setMessages((prev) =>
      prev.map((m) =>
        m.id === assistantMsgId.current
          ? {
              ...m,
              content: "⚠️ We couldn't complete this request due to an AI service issue. Please try again in a few moments.",
              isStreaming: false,
            }
          : m
      )
    );
  }, [error]);

  const handleSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      const question = input.trim();
      if (!question || isStreaming) return;

      if (messages.length === 0) onFirstMessage(question);

      const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", content: question };
      const assistantId = crypto.randomUUID();
      assistantMsgId.current = assistantId;
      const assistantMsg: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        isStreaming: true,
        statusMessages: ["Planner Started..."],
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setInput("");

      const qLower = question.toLowerCase();
      if (qLower === "compare both" || qLower === "compare them") {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  content:
                    "What would you like me to compare?\n\n• The two uploaded PDFs\n• Resume with latest AI trends\n• Resume with latest research",
                  isStreaming: false,
                  route: "CLARIFICATION",
                }
              : m
          )
        );
        return;
      }

      await sendQuestion(question, sessionId || undefined, true);
    },
    [input, isStreaming, messages.length, onFirstMessage, sendQuestion, sessionId]
  );

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto px-4 py-6 md:px-10">
        {messages.length === 0 && (
          <div className="mx-auto max-w-lg pt-32 text-center">
            <h1 className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100 mb-3">
              Ready to Research
            </h1>
            <p className="text-sm text-neutral-500 dark:text-neutral-400">
              Upload a PDF to begin document research or ask a general knowledge question.
            </p>
          </div>
        )}
        <div className="mx-auto flex max-w-5xl flex-col gap-6">
          {messages.map((m) => (
            <MessageBubble key={m.id} message={m} />
          ))}
        </div>
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950 px-4 py-4 md:px-10">
        <div className="mx-auto max-w-4xl flex flex-col gap-2">
          <form onSubmit={handleSubmit} className="flex items-end gap-2">
            <FileUpload sessionId={sessionId || undefined} onUploaded={onUploaded} />
            <div className="flex flex-1 items-end rounded-2xl border border-neutral-300 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-900 px-3 py-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit(e as unknown as FormEvent);
                  }
                }}
                placeholder="Ask a research question..."
                rows={1}
                className="max-h-40 flex-1 resize-none bg-transparent text-sm text-neutral-900 dark:text-neutral-100 outline-none placeholder:text-neutral-400"
              />
            </div>
            <button
              type="submit"
              disabled={isStreaming || !input.trim()}
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-600 text-white transition-colors hover:bg-brand-700 disabled:opacity-40"
            >
              <Send size={16} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
