import { useLLM } from "@/contexts/useLLM";
import React, { useEffect, useState, FormEvent, useRef } from "react";
import { FaComments, FaPaperPlane, FaSpinner, FaTimes } from "react-icons/fa";
import ReactMarkdown from "react-markdown";

const Chat = () => {
  const {
    messages,
    sendMessage,
    isLoading,
    isReady,
    progress,
    showChat,
    setShowChat,
    enableLLM,
    initializeLLM,
  } = useLLM();
  const [input, setInput] = useState<string>("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const chatRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "instant" });
  }, [messages]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    await sendMessage(input);
    setInput("");
    setTimeout(() => inputRef.current?.focus(), 50);
  };

  const toggleChat = () => {
    if (!enableLLM) {
      setShowChat(true);
      return;
    }

    if (!isReady) return;

    setShowChat((prev) => !prev);
    if (!showChat) {
      setTimeout(() => {
        inputRef.current?.focus();
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    }
  };

  const handleClickOutside = (event: MouseEvent) => {
    if (chatRef.current && !chatRef.current.contains(event.target as Node)) {
      setShowChat(false);
    }
  };

  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Escape") {
      setShowChat(false);
    }
  };

  useEffect(() => {
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  return (
    <div
      className={`fixed bottom-2 right-2 transition-all ${
        showChat ? "z-50" : "z-10"
      }`}
    >
      {!showChat && (
        <button
          onClick={toggleChat}
          className="bg-blue-600 text-white p-3 rounded-full shadow-lg flex items-center justify-center hover:bg-blue-700"
        >
          {!enableLLM ? (
            <FaComments size={20} />
          ) : isReady ? (
            <FaComments size={20} />
          ) : (
            <div className="flex items-center space-x-2">
              {progress && <span>{(progress.progress * 100).toFixed()}%</span>}
              <FaSpinner className="animate-spin" size={20} />
            </div>
          )}
        </button>
      )}

      {showChat && (
        <div
          ref={chatRef}
          className="bg-white shadow-lg rounded-lg border border-gray-300 mt-2 flex flex-col"
          style={{ width: 400, maxHeight: "80vh" }}
        >
          <header className="bg-blue-600 text-white p-4 flex items-center justify-between">
            <span className="text-lg font-semibold">Infectio AI</span>
            <button
              onClick={toggleChat}
              className="text-white hover:text-gray-200 focus:outline-none"
            >
              <FaTimes size={20} />
            </button>
          </header>

          {!enableLLM ? (
            <div className="flex-1 p-6 flex flex-col items-center justify-center text-center">
              <FaComments size={48} className="text-blue-500 mb-4" />
              <h3 className="text-lg font-semibold mb-2">
                Enable AI Assistant
              </h3>
              <p className="text-gray-600 mb-4">
                The AI assistant can help you with malware analysis questions.
                It requires downloading a ~1.5GB language model that runs
                locally in your browser.
              </p>
              <button
                onClick={() => {
                  initializeLLM();
                }}
                className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 focus:outline-none"
              >
                Enable AI Assistant
              </button>
            </div>
          ) : !isReady ? (
            <div className="flex-1 p-6 flex flex-col items-center justify-center text-center">
              <FaSpinner
                className="animate-spin text-blue-500 mb-4"
                size={48}
              />
              <h3 className="text-lg font-semibold mb-2">
                Loading AI Model...
              </h3>
              {progress && (
                <div className="w-full max-w-xs">
                  <div className="bg-gray-200 rounded-full h-2 mb-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all"
                      style={{ width: `${progress.progress * 100}%` }}
                    />
                  </div>
                  <p className="text-sm text-gray-600">
                    {(progress.progress * 100).toFixed(0)}% - {progress.text}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <>
              <div className="flex-1 p-4 overflow-y-auto">
                {messages.map((msg, index) => {
                  if (msg.role === "system") {
                    return null;
                  }

                  return (
                    <div
                      key={index}
                      className={`flex ${
                        msg.role === "user" ? "justify-end" : "justify-start"
                      } mb-2`}
                    >
                      <div
                        className={`rounded-lg px-4 py-2 max-w-xs break-words ${
                          msg.role === "user"
                            ? "bg-blue-500 text-white"
                            : "bg-gray-300 text-gray-800"
                        }`}
                      >
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      </div>
                    </div>
                  );
                })}
                <div ref={messagesEndRef} />
              </div>

              <form
                onSubmit={handleSubmit}
                className="p-4 bg-white flex space-x-2"
              >
                <input
                  type="text"
                  ref={inputRef}
                  className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Type your message..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  disabled={isLoading}
                />
                <button
                  type="submit"
                  className={`bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 focus:outline-none ${
                    isLoading ? "opacity-50 cursor-not-allowed" : ""
                  }`}
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <FaSpinner className="animate-spin" />
                  ) : (
                    <FaPaperPlane />
                  )}
                </button>
              </form>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default Chat;
