import { useState, useEffect } from "react";

interface Session {
  id: string;
  title: string;
  updated_at: string;
}

export function SessionSidebar({
  onSelectSession,
}: {
  onSelectSession: (id: string) => void;
}) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [editingSession, setEditingSession] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState("");

  const updateSessionTitle = async (sessionId: string, title: string) => {
    const token = localStorage.getItem("access_token");

    await fetch(`http://localhost:8000/ws/sessions/${sessionId}/title`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ title }),
    });

    fetchSessions(); // Refresh the list
    setEditingSession(null);
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    const token = localStorage.getItem("access_token");
    const user = JSON.parse(localStorage.getItem("user") || "{}");

    try {
      const response = await fetch(
        `http://localhost:8000/ws/sessions?user_id=${user.id}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        // Ensure data is an array
        setSessions(Array.isArray(data) ? data : []);
      } else {
        console.error("Failed to fetch sessions:", response.status);
        setSessions([]); // Set empty array on error
      }
    } catch (error) {
      console.error("Error fetching sessions:", error);
      setSessions([]); // Set empty array on error
    }
  };

  const createNewSession = () => {
    localStorage.removeItem("current_session_id");
    window.location.reload();
  };

  const deleteSession = async (sessionId: string) => {
    if (!confirm("Are you sure you want to delete this conversation?")) return;

    const token = localStorage.getItem("access_token");

    try {
      const response = await fetch(
        `http://localhost:8000/ws/sessions/${sessionId}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        // If we're currently in the deleted session, go to a new one
        const currentSessionId = localStorage.getItem("current_session_id");
        if (currentSessionId === sessionId) {
          localStorage.removeItem("current_session_id");
          window.location.reload();
        }

        fetchSessions(); // Refresh the list
      } else {
        console.error("Failed to delete session:", response.statusText);
        alert("Failed to delete session. Please try again.");
      }
    } catch (error) {
      console.error("Error deleting session:", error);
      alert("Error deleting session. Please check your connection.");
    }
  };

  return (
    <div className="w-64 bg-gradient-to-b from-gray-50 to-white border-r border-gray-200 flex flex-col h-full">
      {/* Sidebar Header */}
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-3 text-center">
          Chat History
        </h2>
        <button
          onClick={createNewSession}
          className="w-full bg-gradient-to-r from-troy-red to-troy-dark text-white py-3 px-4 rounded-xl font-medium hover:shadow-lg transition-all duration-200 transform hover:scale-105 flex items-center justify-center gap-2"
        >
          <svg
            className="w-4 h-4 mr-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M12 4v16m8-8H4"
            />
          </svg>
          New Chat
        </button>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto p-4">
        {sessions.length === 0 ? (
          <div className="text-center py-8">
            <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
            </div>
            <p className="text-sm text-gray-500">No conversations yet</p>
            <p className="text-xs text-gray-400 mt-1">
              Start a new chat to begin
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {sessions.map((session) => (
              <div key={session.id} className="group relative">
                {editingSession === session.id ? (
                  <div className="p-3 bg-white border border-troy-red rounded-lg">
                    <input
                      value={newTitle}
                      onChange={(e) => setNewTitle(e.target.value)}
                      className="w-full p-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-troy-red focus:border-transparent"
                      onBlur={() => {
                        updateSessionTitle(session.id, newTitle);
                      }}
                      onKeyPress={(e) => {
                        if (e.key === "Enter") {
                          updateSessionTitle(session.id, newTitle);
                        }
                      }}
                      autoFocus
                    />
                  </div>
                ) : (
                  <div className="flex items-center">
                    <button
                      onClick={() => onSelectSession(session.id)}
                      className="flex-1 text-left p-3 hover:bg-white hover:shadow-sm rounded-lg transition-all duration-200 group"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-gray-900 truncate text-sm mb-1">
                            {session.title}
                          </p>
                          <p className="text-xs text-gray-500">
                            {new Date(session.updated_at).toLocaleDateString(
                              "en-US",
                              {
                                month: "short",
                                day: "numeric",
                                hour: "2-digit",
                                minute: "2-digit",
                              }
                            )}
                          </p>
                        </div>
                      </div>
                    </button>

                    {/* Action buttons - appear on hover */}
                    <div className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 flex gap-1 transition-opacity">
                      <button
                        onClick={() => {
                          setEditingSession(session.id);
                          setNewTitle(session.title);
                        }}
                        className="p-1.5 text-gray-400 hover:text-troy-red hover:bg-troy-red/10 rounded-md transition-colors"
                        title="Rename conversation"
                      >
                        <svg
                          className="w-3 h-3"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth="2"
                            d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                          />
                        </svg>
                      </button>
                      <button
                        onClick={() => deleteSession(session.id)}
                        className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-md transition-colors"
                        title="Delete conversation"
                      >
                        <svg
                          className="w-3 h-3"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth="2"
                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                          />
                        </svg>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
