import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import {
  CreateWebWorkerMLCEngine,
  InitProgressReport,
  MLCEngineInterface,
} from "@mlc-ai/web-llm";

const selectedModel = "gemma-2-2b-it-q4f16_1-MLC";

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
}

interface LLMContextProps {
  messages: Message[];
  sendMessage: (content: string) => Promise<void>;
  isLoading: boolean;
  isReady: boolean;
  showChat: boolean;
  setShowChat: React.Dispatch<React.SetStateAction<boolean>>;
  progress?: InitProgressReport;
  enableLLM: boolean;
  initializeLLM: () => void;
}

const initialSystemMessage: Message = {
  role: "system",
  content:
    "You are Infectio, an AI assistant integrated into a malware analysis tool called Infectio. This tool was developed by Filippo Finke, a first-year master's student as part of a semester project for SUPSI’s Master in Cyber Security program. Built with WebAssembly, Infectio focuses on offline malware analysis. Your role is to provide accurate, concise guidance on cybersecurity concepts, including static analysis, dynamic analysis, reverse engineering, imports, DLLs, system calls, and code structure. Politely decline any requests outside this scope. Provide short answers, and if you don't know the answer, simply say so. If your response requires formatting, please use Markdown.",
};

const initialAssistantMessage: Message = {
  role: "assistant",
  content:
    "Hi! I'm Infectio.\nI'm here to help you with malware analysis. Feel free to ask me anything!",
};

const LLMContext = createContext<LLMContextProps | undefined>(undefined);

export const LLMProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  const [engine, setEngine] = useState<MLCEngineInterface | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    initialSystemMessage,
    initialAssistantMessage,
  ]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [progress, setProgress] = useState<InitProgressReport>();
  const [showChat, setShowChat] = useState<boolean>(false);
  const [enableLLM, setEnableLLM] = useState<boolean>(() => {
    // Check localStorage for saved preference
    const saved = localStorage.getItem("infectio-llm-enabled");
    return saved === "true";
  });

  const initializeLLM = () => {
    setEnableLLM(true);
    localStorage.setItem("infectio-llm-enabled", "true");
  };

  useEffect(() => {
    if (!enableLLM) return;

    const initializeEngine = async () => {
      try {
        const eng = await CreateWebWorkerMLCEngine(
          new Worker(new URL("./../workers/llm.ts", import.meta.url), {
            type: "module",
          }),
          selectedModel,
          {
            initProgressCallback: (progress) => setProgress(progress),
          }
        );
        setEngine(eng);
      } catch (error) {
        console.error("Error initializing MLCEngine:", error);
      }
    };

    initializeEngine();
  }, [enableLLM]);

  const sendMessage = async (content: string) => {
    if (!content.trim()) return;
    if (!engine) {
      console.error("Engine not initialized yet.");
      return;
    }

    const userMessage: Message = { role: "user", content: content.trim() };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setIsLoading(true);

    try {
      const chunks = await engine.chat.completions.create({
        messages: updatedMessages.map((msg) => ({
          role: msg.role,
          content: msg.content,
        })),
        temperature: 0.7,
        stream: true,
        stream_options: { include_usage: true },
      });

      for await (const chunk of chunks) {
        const contentChunk = chunk.choices[0]?.delta.content || "";
        setMessages((prevMessages) => {
          const lastMessage = prevMessages[prevMessages.length - 1];
          if (lastMessage.role === "assistant") {
            return [
              ...prevMessages.slice(0, -1),
              { ...lastMessage, content: lastMessage.content + contentChunk },
            ];
          } else {
            return [
              ...prevMessages,
              { role: "assistant", content: contentChunk },
            ];
          }
        });

        if (chunk.usage) {
          console.log("Usage:", chunk.usage);
        }
      }
    } catch (error) {
      console.error("Error during chat completion:", error);
      setMessages((prevMessages) => [
        ...prevMessages,
        { role: "assistant", content: "Sorry, something went wrong." },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <LLMContext.Provider
      value={{
        isReady: !!engine,
        messages,
        sendMessage,
        isLoading,
        progress,
        setShowChat,
        showChat,
        enableLLM,
        initializeLLM,
      }}
    >
      {children}
    </LLMContext.Provider>
  );
};

export const useLLM = (): LLMContextProps => {
  const context = useContext(LLMContext);
  if (context === undefined) {
    throw new Error("useLLM must be used within an LLMProvider");
  }
  return context;
};
