import { useState, useEffect, useRef } from "react";
import "../App.css";
import { UserOutlined } from "@ant-design/icons";
const API_URL = import.meta.env.VITE_API_URL

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const currentMessageRef = useRef("");
  const isStreamingRef = useRef(false);

  // Load chat history for existing session
  const loadChatHistory = async (sessionId: string, token: string) => {
    try {
      const user = JSON.parse(localStorage.getItem("user") || "{}");
      const response = await fetch(
        `${API_URL}/ws/chat-history?session_id=${sessionId}&user_id=${user.id}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const history = await response.json();
        const historyMessages = history.map(
          (msg: { role: string; content: string; created_at: string }) => ({
            role: msg.role as "user" | "assistant",
            content: msg.content,
            timestamp: new Date(msg.created_at),
          })
        );
        setMessages(historyMessages);
      }
    } catch (error) {
      console.error("Failed to load chat history:", error);
    }
  };

  // Connect to WebSocket
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    const sessionId = localStorage.getItem("current_session_id"); // Optional

    if (!token) {
      console.error("No access token found");
      // Redirect to login
      window.location.href = "/login";
      return;
    }

    // Load existing chat history if resuming a session
    if (sessionId) {
      loadChatHistory(sessionId, token);
    }

    // Connect with authentication
    const wsBase = API_URL.replace(/^http/, "ws");
    const wsUrl = `${wsBase}/ws/chat?token=${token}${
      sessionId ? `&session_id=${sessionId}` : ""
    }`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("Connected to Troy HealthBot");
      setIsConnected(true);

      // Only show welcome message for new sessions (no sessionId in localStorage)
      if (!sessionId) {
        setMessages([
          {
            role: "assistant",
            content:
              "Hi! I'm Troy HealthBot. I'm here to help you understand any health concerns you might have. What brings you here today?",
            timestamp: new Date(),
          },
        ]);
      }
    };

    ws.onmessage = (event) => {
      const chunk = event.data;

      // If it's the end of the message
      if (chunk === "\n") {
        setIsTyping(false);
        isStreamingRef.current = false;
        // Keep currentMessageRef - it will be reset when next message starts
        return;
      }

      // If it's the start of a new assistant message
      if (!isStreamingRef.current) {
        isStreamingRef.current = true;
        currentMessageRef.current = chunk; // Reset and start fresh
        setIsTyping(true);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: chunk,
            timestamp: new Date(),
          },
        ]);
        return;
      }

      // Otherwise, update the last assistant message in place
      currentMessageRef.current += chunk;
      setMessages((prev) => {
        const newMessages = [...prev];
        const lastIndex = newMessages.length - 1;
        if (lastIndex >= 0 && newMessages[lastIndex].role === "assistant") {
          newMessages[lastIndex] = {
            ...newMessages[lastIndex],
            content: currentMessageRef.current,
            timestamp: new Date(),
          };
        }
        return newMessages;
      });
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      setIsConnected(false);
    };

    ws.onclose = () => {
      console.log("Disconnected from Troy HealthBot");
      setIsConnected(false);
    };

    wsRef.current = ws;

    return () => {
      ws.close();
    };
  }, []);

  const sendMessage = () => {
    if (!input.trim() || !wsRef.current || !isConnected) return;

    // Add user message
    const userMessage: Message = {
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);

    // Send to WebSocket
    wsRef.current.send(input);

    // Clear input
    setInput("");
    currentMessageRef.current = "";
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="h-screen bg-gradient-to-br from-slate-50 to-gray-100 flex flex-col">
      {/* Chat Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-troy-red to-troy-dark rounded-full flex items-center justify-center">
              <span className="text-white text-lg">
                <UserOutlined />
              </span>
            </div>
            <div className="flex flex-col">
              <h2 className="text-lg font-semibold text-gray-900">
                Troy HealthBot
              </h2>
              <p className="text-sm text-gray-600">AI Health Assistant</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  isConnected ? "bg-green-500" : "bg-red-500"
                }`}
              />
              <span className="text-sm text-gray-600 hidden sm:inline">
                {isConnected ? "Connected" : "Connecting..."}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6">
          {messages.length === 0 ? (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-gradient-to-br from-troy-red to-troy-dark rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-white text-2xl">👋</span>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Welcome to Troy HealthBot
              </h3>
              <p className="text-gray-600 max-w-md mx-auto">
                I'm here to help you with health questions and symptom analysis.
                How can I assist you today?
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex ${
                    msg.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  <div
                    className={`flex items-start gap-3 max-w-[85%] sm:max-w-[75%]`}
                  >
                    {msg.role === "assistant" && (
                      <div className="w-8 h-8 bg-gradient-to-br from-troy-red to-troy-dark rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                        <span className="text-white text-sm">
                          {" "}
                          <UserOutlined />
                        </span>
                      </div>
                    )}
                    <div
                      className={`rounded-2xl px-4 py-3 ${
                        msg.role === "user"
                          ? "bg-troy-red text-white ml-auto"
                          : "bg-white text-gray-800 shadow-sm border border-gray-100"
                      }`}
                    >
                      <div className="whitespace-pre-wrap break-words leading-relaxed">
                        {msg.content}
                      </div>
                      <p
                        className={`text-xs mt-2 ${
                          msg.role === "user"
                            ? "text-troy-gray/80"
                            : "text-gray-400"
                        }`}
                      >
                        {msg.timestamp.toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
                    </div>
                    {msg.role === "user" && (
                      <div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                        <span className="text-gray-600 text-sm">
                          {" "}
                          <UserOutlined />
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {isTyping && (
            <div className="flex justify-start mt-6">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 bg-gradient-to-br from-troy-red to-troy-dark rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-white text-sm">
                    {" "}
                    <UserOutlined />
                  </span>
                </div>
                <div className="bg-white rounded-2xl px-4 py-3 shadow-sm border border-gray-100">
                  <div className="flex gap-1 items-center">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                    <div
                      className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                      style={{ animationDelay: "0.1s" }}
                    />
                    <div
                      className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                      style={{ animationDelay: "0.2s" }}
                    />
                    <span className="text-gray-500 text-sm ml-2">
                      Typing...
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200 shadow-lg">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex gap-3 items-start">
            <div className="flex-1">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Describe your symptoms or ask a health question..."
                className="w-full resize-none rounded-2xl border border-gray-300 px-4 py-3 pr-12 focus:outline-none focus:ring-2 focus:ring-troy-red focus:border-transparent transition-all duration-200 min-h-[48px] max-h-32"
                rows={1}
                disabled={!isConnected}
              />
            </div>
            <button
              onClick={sendMessage}
              disabled={!input.trim() || !isConnected}
              className="px-6 py-3 bg-gradient-to-r from-troy-red to-troy-dark text-white rounded-2xl font-medium hover:shadow-lg disabled:bg-gray-300 disabled:cursor-not-allowed transition-all duration-200 transform hover:scale-105 disabled:transform-none flex items-center gap-2"
            >
              <span className="hidden sm:inline">Send</span>
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                />
              </svg>
            </button>
          </div>

          {/* Enhanced Disclaimer */}
          <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-xs text-yellow-800 text-center flex items-center justify-center gap-2">
              <span className="text-yellow-950">WARNING:</span>
              <span>
                This AI assistant provides general guidance only. Always consult
                a healthcare professional for medical advice.
              </span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ChatWindow;
