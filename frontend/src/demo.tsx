import { useState, useEffect, useRef } from "react";
import "./App.css";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

function Demo() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const currentMessageRef = useRef("");

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Connect to WebSocket
  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws/chat");

    ws.onopen = () => {
      console.log("✅ Connected to Troy HealthLink");
      setIsConnected(true);
      setMessages([
        {
          role: "assistant",
          content:
            "Hi! I'm Troy HealthLink. I'm here to help you understand any health concerns you might have. What brings you here today?",
          timestamp: new Date(),
        },
      ]);
    };

    ws.onmessage = (event) => {
      const chunk = event.data;

      if (chunk === "\n") {
        // Completion signal
        setIsTyping(false);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: currentMessageRef.current,
            timestamp: new Date(),
          },
        ]);
        currentMessageRef.current = "";
      } else {
        // Streaming chunk
        currentMessageRef.current += chunk;
        setIsTyping(true);

        // Update last message with streaming content
        setMessages((prev) => {
          const newMessages = [...prev];
          if (
            newMessages.length > 0 &&
            newMessages[newMessages.length - 1].role === "assistant"
          ) {
            // Update existing streaming message
            newMessages[newMessages.length - 1] = {
              role: "assistant",
              content: currentMessageRef.current,
              timestamp: new Date(),
            };
          } else {
            // Create new streaming message
            newMessages.push({
              role: "assistant",
              content: currentMessageRef.current,
              timestamp: new Date(),
            });
          }
          return newMessages;
        });
      }
    };

    ws.onerror = (error) => {
      console.error("❌ WebSocket error:", error);
      setIsConnected(false);
    };

    ws.onclose = () => {
      console.log("🔌 Disconnected from Troy HealthLink");
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
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex flex-col">
      {/* Header */}
      <header className="bg-white shadow-md">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-600 rounded-full flex items-center justify-center">
              <span className="text-white font-bold text-xl">TH</span>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-800">
                Troy HealthLink
              </h1>
              <p className="text-sm text-gray-500">
                Your Sexual Health Assistant
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div
              className={`w-3 h-3 rounded-full ${
                isConnected ? "bg-green-500" : "bg-red-500"
              }`}
            />
            <span className="text-sm text-gray-600">
              {isConnected ? "Connected" : "Disconnected"}
            </span>
          </div>
        </div>
      </header>

      {/* Chat Messages */}
      <div className="flex-1 max-w-4xl w-full mx-auto px-4 py-6 overflow-y-auto">
        <div className="space-y-4">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                  msg.role === "user"
                    ? "bg-indigo-600 text-white"
                    : "bg-white text-gray-800 shadow-md"
                }`}
              >
                <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                <p
                  className={`text-xs mt-1 ${
                    msg.role === "user" ? "text-indigo-200" : "text-gray-400"
                  }`}
                >
                  {msg.timestamp.toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
              </div>
            </div>
          ))}

          {isTyping && (
            <div className="flex justify-start">
              <div className="bg-white rounded-2xl px-4 py-3 shadow-md">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                  <div
                    className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: "0.1s" }}
                  />
                  <div
                    className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: "0.2s" }}
                  />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200 shadow-lg">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex gap-3">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Describe your symptoms..."
              className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              rows={1}
              disabled={!isConnected}
            />
            <button
              onClick={sendMessage}
              disabled={!input.trim() || !isConnected}
              className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              Send
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2 text-center">
            ⚠️ This is an AI assistant, not a medical diagnosis. Always consult
            healthcare professionals.
          </p>
        </div>
      </div>
    </div>
  );
}

export default Demo;
