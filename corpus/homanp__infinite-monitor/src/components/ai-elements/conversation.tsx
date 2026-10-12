"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ComponentProps,
  type ReactNode,
} from "react";
import { ArrowDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ConversationContextValue {
  contentRef: React.RefObject<HTMLDivElement | null>;
  isAtBottom: boolean;
  scrollToBottom: () => void;
}

const ConversationContext = createContext<ConversationContextValue | null>(null);

function useConversationContext() {
  const ctx = useContext(ConversationContext);
  if (!ctx) throw new Error("Must be used within <Conversation>");
  return ctx;
}

export function Conversation({
  className,
  children,
  ...props
}: ComponentProps<"div">) {
  const contentRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);

  const scrollToBottom = useCallback(() => {
    contentRef.current?.scrollTo({
      top: contentRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, []);

  useEffect(() => {
    const node = contentRef.current;
    if (!node) return;

    const handleScroll = () => {
      setIsAtBottom(
        node.scrollHeight - node.scrollTop - node.clientHeight < 24
      );
    };

    handleScroll();
    node.addEventListener("scroll", handleScroll);
    return () => node.removeEventListener("scroll", handleScroll);
  }, []);

  const value = useMemo(
    () => ({ contentRef, isAtBottom, scrollToBottom }),
    [isAtBottom, scrollToBottom]
  );

  return (
    <ConversationContext.Provider value={value}>
      <div
        className={cn("relative flex min-h-0 flex-1 overflow-hidden", className)}
        {...props}
      >
        {children}
      </div>
    </ConversationContext.Provider>
  );
}

export function ConversationContent({
  className,
  children,
  ...props
}: ComponentProps<"div"> & { children?: ReactNode }) {
  const { contentRef, scrollToBottom } = useConversationContext();

  useEffect(() => {
    scrollToBottom();
  }, [children, scrollToBottom]);

  return (
    <div
      ref={contentRef}
      className={cn("flex-1 overflow-x-hidden overflow-y-auto px-5 py-4", className)}
      {...props}
    >
      <div className="flex min-h-full flex-col gap-6">{children}</div>
    </div>
  );
}

export function ConversationEmptyState({
  className,
  title = "Start building",
  description = "Describe the widget you want to create.",
  icon,
  ...props
}: ComponentProps<"div"> & {
  title?: string;
  description?: string;
  icon?: ReactNode;
}) {
  return (
    <div
      className={cn(
        "flex min-h-full flex-col items-center justify-center gap-3 px-6 text-center",
        className
      )}
      {...props}
    >
      {icon && <div className="text-zinc-500">{icon}</div>}
      <div className="space-y-1">
        <p className="text-sm font-medium text-zinc-200 uppercase tracking-wider">{title}</p>
        <p className="text-sm text-zinc-500">{description}</p>
      </div>
    </div>
  );
}

export function ConversationScrollButton({
  className,
  ...props
}: ComponentProps<typeof Button>) {
  const { isAtBottom, scrollToBottom } = useConversationContext();
  if (isAtBottom) return null;

  return (
    <Button
      type="button"
      size="icon-sm"
      variant="outline"
      className={cn(
        "absolute right-4 bottom-4 rounded-none border-zinc-700 bg-zinc-900 text-zinc-200 hover:bg-zinc-800",
        className
      )}
      onClick={scrollToBottom}
      {...props}
    >
      <ArrowDown className="size-4" />
    </Button>
  );
}
