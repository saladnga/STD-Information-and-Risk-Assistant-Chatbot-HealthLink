import { useState, useEffect } from "react";
import { apiFetch } from "../lib/api";
import { getCurrentSessionId, getUser } from "../lib/storage";

export interface Session {
  id: string;
  title: string;
  updated_at: string;
}

// Owns fetching/renaming/deleting chat sessions, so SessionSidebar only has to render. Refetches whenever refreshTrigger changes (new session created, or a response just finished elsewhere in the app).
export function useSessions(
  refreshTrigger: number | undefined,
  onCurrentSessionDeleted: () => void,
) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchSessions = async () => {
    const user = getUser();
    try {
      const response = await apiFetch(`/ws/sessions?user_id=${user?.id}`);
      const data = response.ok ? await response.json() : [];
      setSessions(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Error fetching sessions:", error);
      setSessions([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, [refreshTrigger]);

  const renameSession = async (sessionId: string, title: string) => {
    await apiFetch(`/ws/sessions/${sessionId}/title`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    fetchSessions();
  };

  const deleteSession = async (sessionId: string): Promise<boolean> => {
    if (deletingId) return false;
    setDeletingId(sessionId);
    try {
      const response = await apiFetch(`/ws/sessions/${sessionId}`, {
        method: "DELETE",
      });
      if (response.ok) {
        if (getCurrentSessionId() === sessionId) onCurrentSessionDeleted();
        fetchSessions();
        return true;
      }
      return false;
    } catch (error) {
      console.error("Error deleting session:", error);
      return false;
    } finally {
      setDeletingId(null);
    }
  };

  return { sessions, isLoading, deletingId, renameSession, deleteSession };
}
