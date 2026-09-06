import { useState, useEffect, useRef } from "react";
import { MedicineBoxOutlined, SendOutlined } from "@ant-design/icons";
import PulseTrace from "./PulseTrace";
import { useChatSocket } from "../hooks/useChatSocket";

const SUGGESTIONS = [
  "I have a symptom I'm not sure about",
  "What happens to what I tell you?",
  "Can you explain how STI testing works?",
];

interface ChatWindowProps {
  sessionId: string | null;
  onSessionCreated: (sessionId: string) => void;
  onResponseComplete: () => void;
}

function ChatWindow({
  sessionId,
  onSessionCreated,
  onResponseComplete,
}: ChatWindowProps) {
  const { messages, isConnected, isTyping, isLoadingHistory, sendText } =
    useChatSocket({ sessionId, onSessionCreated, onResponseComplete });
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const submit = (text: string) => {
    sendText(text);
    setInput("");
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit(input);
    }
  };

  return (
    <div className="flex-1 min-h-0 flex flex-col bg-troy-clinic">
      {/* Loading state: only surfaces while the socket isn't up yet */}
      {!isConnected && (
        <div className="bg-troy-amber/10 border-b border-troy-amber/30 text-troy-amber text-xs font-mono text-center py-1.5">
          Connecting to Troy HealthBot…
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-5">
          {isLoadingHistory ? (
            <div className="space-y-6">
              {[...Array(3)].map((_, i) => (
                <div
                  key={i}
                  className={`flex ${i % 2 === 0 ? "justify-start" : "justify-end"}`}
                >
                  <div
                    className={`animate-pulse rounded-2xl px-4 py-3 max-w-[75%] ${
                      i % 2 === 0 ? "bg-troy-surface" : "bg-troy-line"
                    }`}
                  >
                    <div className="h-3 bg-troy-line rounded w-40" />
                  </div>
                </div>
              ))}
            </div>
          ) : messages.length === 0 ? (
            <div className="text-center py-10">
              <h2 className="font-mono font-bold text-3xl text-troy-ink mb-2">
                What's on your mind?
              </h2>
              <p className="text-troy-ink/60 text-md max-w-sm mx-auto mb-8 font-mono">
                Ask about a symptom, a medication, or how testing works — it
                stays between us.
              </p>
              <div className="flex flex-wrap justify-center gap-2 max-w-lg mx-auto">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => submit(s)}
                    disabled={!isConnected}
                    className="text-base px-4 py-2 border border-troy-line text-troy-ink/80 hover:border-troy-red hover:text-troy-red transition-colors disabled:opacity-40 disabled:cursor-not-allowed font-mono"
                  >
                    {s}
                  </button>
                ))}
              </div>
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
                  <div className="flex items-start gap-3 max-w-[85%] sm:max-w-[75%]">
                    {msg.role === "assistant" && (
                      <div className="w-8 h-8 bg-troy-red rounded-full flex items-center justify-center flex-shrink-0 mt-1 text-white text-sm">
                        <MedicineBoxOutlined />
                      </div>
                    )}
                    <div
                      className={`rounded-2xl px-4 py-3 text-base ${
                        msg.role === "user"
                          ? "bg-troy-red text-white"
                          : "bg-troy-surface text-troy-ink border border-troy-line"
                      }`}
                    >
                      <div className="whitespace-pre-wrap break-words leading-relaxed">
                        {msg.content}
                      </div>
                      <p
                        className={`font-mono text-xs mt-2 ${
                          msg.role === "user"
                            ? "text-white/70"
                            : "text-troy-ink/40"
                        }`}
                      >
                        {msg.timestamp.toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {isTyping && (
            <div className="flex justify-start mt-6">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 bg-troy-red rounded-full flex items-center justify-center flex-shrink-0 text-white text-sm">
                  <MedicineBoxOutlined />
                </div>
                <div className="bg-troy-surface border border-troy-line rounded-2xl px-4 py-3">
                  <div className="flex gap-2 items-center">
                    <PulseTrace animated className="w-16 h-5" />
                    <span className="text-troy-ink/60 text-sm">
                      Thinking...
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-troy-line bg-troy-surface">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3">
          <div className="flex items-end gap-2 bg-troy-clinic border border-troy-line px-2 py-1.5 focus-within:border-troy-red transition-colors">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Describe your symptoms or ask a health question..."
              className="flex-1 bg-transparent resize-none border-0 focus:outline-none focus:ring-0 px-3 py-2 text-lg min-h-[28px] max-h-32 text-troy-ink placeholder:text-troy-ink/40"
              rows={1}
              disabled={!isConnected}
            />
            <button
              onClick={() => submit(input)}
              disabled={!input.trim() || !isConnected}
              className="w-11 h-11 rounded-full bg-troy-red text-white flex items-center justify-center hover:bg-troy-dark disabled:bg-troy-line disabled:text-troy-ink/30 transition-colors flex-shrink-0"
            >
              <SendOutlined />
            </button>
          </div>
          <p className="font-mono text-sm text-white text-center mt-3">
            General guidance only — always confirm with a healthcare
            professional.
          </p>
        </div>
      </div>
    </div>
  );
}

export default ChatWindow;
