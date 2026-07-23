import { useState } from "react";
import Sidebar, { Conversation } from "./components/Sidebar";
import ChatWindow from "./components/ChatWindow";

export default function App() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [uploadCount, setUploadCount] = useState(0);
  const [clearTrigger, setClearTrigger] = useState(0);

  const handleNewChat = () => {
    setSessionId(null);
    setActiveId(null);
    setClearTrigger((c) => c + 1);
  };

  const handleClearSession = () => {
    setSessionId(null);
    setActiveId(null);
    setClearTrigger((c) => c + 1);
  };

  const handleUploaded = (sid: string, _filename: string) => {
    setSessionId(sid);
    setUploadCount((c) => c + 1);
  };

  const handleFirstMessage = (question: string) => {
    const id = crypto.randomUUID();
    setActiveId(id);
    setConversations((prev) => [
      { id, title: question.length > 40 ? `${question.slice(0, 40)}...` : question },
      ...prev,
    ]);
  };

  return (
    <div className="flex h-screen w-full bg-white dark:bg-neutral-950 text-neutral-900 dark:text-neutral-100">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        sessionId={sessionId}
        uploadCount={uploadCount}
        onSelect={setActiveId}
        onNewChat={handleNewChat}
        onClearSession={handleClearSession}
      />
      <main className="flex-1 overflow-hidden">
        <ChatWindow
          sessionId={sessionId}
          clearTrigger={clearTrigger}
          onSessionCreated={setSessionId}
          onFirstMessage={handleFirstMessage}
          onUploaded={handleUploaded}
        />
      </main>
    </div>
  );
}
