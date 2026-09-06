import { useState, useEffect, useRef } from "react";
import { API_URL, apiFetch } from "../lib/api";
import { getToken, getUser } from "../lib/storage";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

// Owns the WebSocket connection, reconnect, and streaming-message assembly for one chat session, so ChatWindow only has to render.
export function useChatSocket({
  sessionId,
  onSessionCreated,
  onResponseComplete,
}: {
  sessionId: string | null;
  onSessionCreated: (sessionId: string) => void;
  onResponseComplete: () => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);
  const currentMessageRef = useRef("");
  const isStreamingRef = useRef(false);
  // Separate from reconnectAttempt (a state var that only exists to trigger a reopen) - resetting a ref on connect doesn't itself force a reopen.
  const backoffCountRef = useRef(0);

  const loadChatHistory = async (id: string) => {
    try {
      const user = getUser();
      const response = await apiFetch(
        `/ws/chat-history?session_id=${id}&user_id=${user?.id}`,
      );
      if (response.ok) {
        const history = await response.json();
        setMessages(
          history.map(
            (msg: { role: string; content: string; created_at: string }) => ({
              role: msg.role as "user" | "assistant",
              content: msg.content,
              timestamp: new Date(msg.created_at),
            }),
          ),
        );
      }
    } catch (error) {
      console.error("Failed to load chat history:", error);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  useEffect(() => {
    const token = getToken();
    if (!token) {
      window.location.href = "/login";
      return;
    }

    if (sessionId) {
      setIsLoadingHistory(true);
      loadChatHistory(sessionId);
    }

    const wsBase = API_URL.replace(/^http/, "ws");
    const wsUrl = `${wsBase}/ws/chat?token=${token}${
      sessionId ? `&session_id=${sessionId}` : ""
    }`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setIsConnected(true);
      backoffCountRef.current = 0; // connected - next drop starts backoff over
    };

    ws.onmessage = (event) => {
      const chunk = event.data;

      // Backend announces the session id right after connecting - capture it so a refresh resumes this chat instead of silently starting a new one.
      if (chunk.startsWith("__SESSION__:")) {
        onSessionCreated(chunk.slice("__SESSION__:".length));
        return;
      }

      // Keepalive during a slow/silent reply (RAG lookup, a fully-buffered
      // LLM call) - nothing to render, just proof the connection is alive.
      if (chunk === "__PING__") {
        return;
      }

      if (chunk === "__DONE__") {
        setIsTyping(false);
        isStreamingRef.current = false;
        onResponseComplete(); // sidebar title/order may have changed server-side
        return;
      }

      if (!isStreamingRef.current) {
        isStreamingRef.current = true;
        currentMessageRef.current = chunk;
        setIsTyping(false); // real content is here now, drop the placeholder
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: chunk, timestamp: new Date() },
        ]);
        return;
      }

      currentMessageRef.current += chunk;
      setMessages((prev) => {
        const next = [...prev];
        const last = next.length - 1;
        if (last >= 0 && next[last].role === "assistant") {
          next[last] = {
            ...next[last],
            content: currentMessageRef.current,
            timestamp: new Date(),
          };
        }
        return next;
      });
    };

    ws.onerror = () => setIsConnected(false);

    let cancelled = false;
    ws.onclose = () => {
      setIsConnected(false);
      if (!cancelled) {
        // Exponential backoff, capped at 30s: 1s, 2s, 4s, 8s, 16s, 30s, 30s...
        // Resets to 1s once a connection actually succeeds (see onopen).
        const delay = Math.min(30000, 1000 * 2 ** backoffCountRef.current);
        backoffCountRef.current += 1;
        setTimeout(() => {
          if (!cancelled) setReconnectAttempt((n) => n + 1);
        }, delay);
      }
    };

    wsRef.current = ws;
    return () => {
      cancelled = true;
      ws.close();
    };
  }, [sessionId, onSessionCreated, onResponseComplete, reconnectAttempt]);

  const sendText = (text: string) => {
    if (!text.trim() || !wsRef.current || !isConnected) return;
    setMessages((prev) => [
      ...prev,
      { role: "user", content: text, timestamp: new Date() },
    ]);
    wsRef.current.send(text);
    currentMessageRef.current = "";
    setIsTyping(true); // shows immediately - the reply can take a few seconds
  };

  return { messages, isConnected, isTyping, isLoadingHistory, sendText };
}
