import { useState, useCallback } from "react";
import { MenuOutlined } from "@ant-design/icons";
import ChatWindow from "../components/ChatWindow";
import PulseTrace from "../components/PulseTrace";
import { SessionSidebar } from "../components/SessionSidebar";
import {
  getCurrentSessionId,
  setCurrentSessionId,
  clearCurrentSessionId,
} from "../lib/storage";

export default function ChatLayout() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [currentSessionId, setCurrentSessionIdState] = useState<string | null>(
    getCurrentSessionId(),
  );
  // Only an existing, already-selected session resumes automatically - starting a brand-new one always requires an explicit click.
  const [chatStarted, setChatStarted] = useState(
    () => getCurrentSessionId() !== null,
  );
  const [sessionsVersion, setSessionsVersion] = useState(0);

  const handleSelectSession = (sessionId: string) => {
    setCurrentSessionId(sessionId);
    setCurrentSessionIdState(sessionId);
    setChatStarted(true);
    setIsSidebarOpen(false);
  };

  const handleNewSession = () => {
    clearCurrentSessionId();
    setCurrentSessionIdState(null);
    setChatStarted(true);
    setIsSidebarOpen(false);
  };

  // Stable reference - passed into ChatWindow's effect deps, must not change identity every render or it would force a WebSocket reconnect each time.
  const handleSessionCreated = useCallback((sessionId: string) => {
    setCurrentSessionId(sessionId);
    setCurrentSessionIdState(sessionId);
  }, []);

  // Same stability requirement as above - bumping a counter, not the session itself, so the sidebar refetches without forcing the socket to reconnect.
  const handleResponseComplete = useCallback(() => {
    setSessionsVersion((v) => v + 1);
  }, []);

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-troy-clinic relative">
      {/* Mobile Sidebar Overlay */}
      {isSidebarOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar - full screen on mobile, a fixed-width panel from lg up */}
      <div
        className={`
        fixed inset-y-0 left-0 w-screen lg:relative lg:w-auto lg:inset-auto lg:translate-x-0 z-50 lg:z-auto
        transform transition-transform duration-300 ease-in-out
        ${isSidebarOpen ? "translate-x-0" : "-translate-x-full"}
        lg:block
      `}
      >
        <SessionSidebar
          onSelectSession={handleSelectSession}
          onNewSession={handleNewSession}
          onClose={() => setIsSidebarOpen(false)}
          refreshTrigger={sessionsVersion}
        />
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile Header with Sidebar Toggle */}
        <div className="lg:hidden bg-troy-surface border-b border-troy-line px-4 py-3 flex items-center justify-between">
          <button
            onClick={toggleSidebar}
            aria-label="Open sidebar"
            className="p-2 rounded-lg text-troy-ink/70 hover:bg-troy-surface transition-colors text-xl"
          >
            <MenuOutlined />
          </button>
          <h1 className="text-lg font-semibold text-troy-ink">
            Troy HealthLink
          </h1>
          <div className="w-10" /> {/* Spacer for centering */}
        </div>

        {chatStarted ? (
          <ChatWindow
            sessionId={currentSessionId}
            onSessionCreated={handleSessionCreated}
            onResponseComplete={handleResponseComplete}
          />
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center px-6">
            <PulseTrace className="w-24 h-8 mb-6" />

            <h2 className="font-bold font-mono text-3xl text-troy-ink mb-2">
              No conversation open
            </h2>

            <p className="text-troy-ink/60 max-w-sm mb-6 text-md font-mono">
              Pick a conversation from the sidebar, or start a new one.
            </p>

            <button
              onClick={handleNewSession}
              className="bg-troy-red hover:bg-troy-dark text-white px-6 py-3 font-mono hover:shadow-lg transition-all duration-200"
            >
              New Chat
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
