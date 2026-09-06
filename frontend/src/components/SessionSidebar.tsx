import { useRef, useState } from "react";
import { Popconfirm } from "antd";
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  CloseOutlined,
} from "@ant-design/icons";
import { useSessions } from "../hooks/useSessions";
import { useNotify } from "../lib/notify";

const LONG_PRESS_MS = 500;

export function SessionSidebar({
  onSelectSession,
  onNewSession,
  onClose,
  refreshTrigger,
}: {
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onClose?: () => void;
  refreshTrigger?: number;
}) {
  const notify = useNotify();
  const { sessions, isLoading, deletingId, renameSession, deleteSession } =
    useSessions(refreshTrigger, onNewSession);
  const [editingSession, setEditingSession] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState("");
  // Which session's edit/delete buttons a long-press pinned open - hover does this on desktop, but touchscreens have no hover.
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const longPressTimer = useRef<number | null>(null);

  const commitRename = () => {
    if (editingSession) renameSession(editingSession, newTitle);
    setEditingSession(null);
  };

  const handleDelete = async (sessionId: string) => {
    const ok = await deleteSession(sessionId);
    if (ok) {
      notify.success("Conversation deleted");
    } else {
      notify.error("Failed to delete session. Please try again.");
    }
    setActiveSessionId(null);
  };

  const handleSelect = (id: string) => {
    setActiveSessionId(null);
    onSelectSession(id);
  };

  const startLongPress = (id: string) => {
    longPressTimer.current = window.setTimeout(
      () => setActiveSessionId(id),
      LONG_PRESS_MS,
    );
  };
  const cancelLongPress = () => {
    if (longPressTimer.current !== null) {
      clearTimeout(longPressTimer.current);
      longPressTimer.current = null;
    }
  };

  return (
    <div className="w-screen lg:w-64 bg-troy-surface border-r border-troy-line flex flex-col h-full">
      {/* Sidebar Header */}
      <div className="p-4 border-b border-troy-line flex items-center gap-3">
        <h2 className="flex-1 text-lg text-troy-ink text-center font-mono">
          CHAT HISTORY
        </h2>
        {onClose && (
          <button
            onClick={onClose}
            aria-label="Close chat history"
            className="lg:hidden text-troy-ink/60 hover:text-troy-red text-xl"
          >
            <CloseOutlined />
          </button>
        )}
      </div>
      <div className="p-4 pb-0">
        <button
          onClick={onNewSession}
          className="w-full border bg-white text-troy-red py-3 px-4 font-medium font-mono transition-all duration-200 transform flex items-center justify-center gap-2 hover:opacity-90"
        >
          <PlusOutlined />
          NEW CHAT
        </button>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto p-4">
        {isLoading ? (
          <div className="space-y-2">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="p-3 rounded-lg animate-pulse">
                <div className="h-4 bg-troy-line rounded w-3/4 mb-2" />
                <div className="h-3 bg-troy-line rounded w-1/2" />
              </div>
            ))}
          </div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-8">
            <div className="w-12 h-12 bg-troy-surface rounded-full flex items-center justify-center mx-auto mb-3"></div>
            <p className="text-sm text-troy-ink/60">No conversations yet</p>
            <p className="text-xs text-troy-ink/40 mt-1">
              Start a new chat to begin
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {sessions.map((session) => {
              const actionsVisible = activeSessionId === session.id;
              return (
                <div
                  key={session.id}
                  className="group relative"
                  onTouchStart={() => startLongPress(session.id)}
                  onTouchEnd={cancelLongPress}
                  onTouchMove={cancelLongPress}
                >
                  {editingSession === session.id ? (
                    <div className="p-3 bg-troy-surface border border-troy-red rounded-lg">
                      <input
                        value={newTitle}
                        onChange={(e) => setNewTitle(e.target.value)}
                        className="w-full p-2 text-sm border border-troy-line rounded-md focus:outline-none focus:ring-2 focus:ring-troy-red focus:border-transparent"
                        onBlur={commitRename}
                        onKeyPress={(e) => {
                          if (e.key === "Enter") commitRename();
                        }}
                        autoFocus
                      />
                    </div>
                  ) : (
                    <div className="flex items-center hover:opacity-90">
                      <button
                        onClick={() => handleSelect(session.id)}
                        className="flex-1 text-left p-3 hover:bg-troy-surface hover:shadow-sm rounded-lg transition-all duration-200 group"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-troy-ink truncate text-sm mb-1">
                              {session.title}
                            </p>
                            <p className="text-xs text-troy-ink/60">
                              {new Date(session.updated_at).toLocaleDateString(
                                "en-US",
                                {
                                  month: "short",
                                  day: "numeric",
                                  hour: "2-digit",
                                  minute: "2-digit",
                                },
                              )}
                            </p>
                          </div>
                        </div>
                      </button>

                      {/* Action buttons - hover reveals them on desktop, a long-press pins them open on touch devices. */}
                      <div
                        className={`absolute right-2 bottom-1 flex gap-1 transition-opacity ${
                          actionsVisible
                            ? "opacity-100"
                            : "opacity-0 group-hover:opacity-100"
                        }`}
                      >
                        <button
                          onClick={() => {
                            setEditingSession(session.id);
                            setNewTitle(session.title);
                            setActiveSessionId(null);
                          }}
                          className="p-1.5 text-troy-ink/40 hover:text-troy-red hover:bg-troy-red/10 rounded-md transition-colors"
                          title="Rename conversation"
                        >
                          <EditOutlined />
                        </button>
                        <Popconfirm
                          title="Delete this conversation?"
                          description="This can't be undone."
                          okText="Delete"
                          okButtonProps={{ danger: true }}
                          onConfirm={() => handleDelete(session.id)}
                        >
                          <button
                            disabled={deletingId === session.id}
                            className="p-1.5 text-troy-ink/40 hover:text-red-400 hover:bg-red-950/40 rounded-md transition-colors disabled:opacity-30"
                            title="Delete conversation"
                          >
                            <DeleteOutlined />
                          </button>
                        </Popconfirm>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
