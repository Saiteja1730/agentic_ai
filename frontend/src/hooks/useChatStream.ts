import { useCallback, useRef, useState } from "react";
import { API_BASE_URL, ChatResult } from "../services/api";

export interface StreamStatus {
  stage: string;
  message: string;
}

interface UseChatStreamResult {
  isStreaming: boolean;
  currentStatus: StreamStatus | null;
  result: ChatResult | null;
  error: string | null;
  sendQuestion: (question: string, sessionId?: string, usePdfContext?: boolean) => Promise<void>;
}

/**
 * Parses a text/event-stream response body (SSE) delivered over a POST
 * fetch request, since the browser's native EventSource only supports GET.
 */
async function* parseSSEStream(response: Response): AsyncGenerator<{ event: string; data: any }> {
  const reader = response.body?.getReader();
  if (!reader) return;
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const chunks = buffer.split(/\r\n\r\n|\n\n/);
    buffer = chunks.pop() || "";

    for (const chunk of chunks) {
      const lines = chunk.split(/\r?\n/);
      let event = "message";
      let data = "";
      for (const line of lines) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (data) {
        try {
          yield { event, data: JSON.parse(data) };
        } catch {
          yield { event, data };
        }
      }
    }
  }
}

export function useChatStream(): UseChatStreamResult {
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStatus, setCurrentStatus] = useState<StreamStatus | null>(null);
  const [result, setResult] = useState<ChatResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const sendQuestion = useCallback(
    async (question: string, sessionId?: string, usePdfContext = true) => {
      setIsStreaming(true);
      setResult(null);
      setError(null);
      setCurrentStatus({ stage: "started", message: "Planner Started..." });

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const response = await fetch(`${API_BASE_URL}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question,
            session_id: sessionId,
            use_pdf_context: usePdfContext,
          }),
          signal: controller.signal,
        });

        if (!response.ok || !response.body) {
          throw new Error(`Request failed with status ${response.status}`);
        }

        for await (const evt of parseSSEStream(response)) {
          if (evt.event === "status") {
            setCurrentStatus(evt.data as StreamStatus);
          } else if (evt.event === "result") {
            setResult(evt.data as ChatResult);
          } else if (evt.event === "error") {
            console.error("Backend Error:", evt.data);
            setError("We couldn't complete this request due to an AI service issue. Please try again in a few moments.");
          }
        }
      } catch (err: any) {
        if (err.name !== "AbortError") {
          console.error("Stream Error:", err);
          setError("We couldn't complete this request due to an AI service issue. Please try again in a few moments.");
        }
      } finally {
        setIsStreaming(false);
      }
    },
    []
  );

  return { isStreaming, currentStatus, result, error, sendQuestion };
}
