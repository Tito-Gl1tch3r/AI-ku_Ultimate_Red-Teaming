"use client";

import { useCallback, useRef, type ComponentProps, type FormEventHandler, type KeyboardEvent } from "react";
import { CornerDownLeft, Paperclip } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function PromptInput({
  className,
  children,
  onSubmit,
  ...props
}: Omit<ComponentProps<"form">, "onSubmit"> & {
  onSubmit?: FormEventHandler<HTMLFormElement>;
}) {
  return (
    <form
      className={cn("flex flex-col gap-3", className)}
      onSubmit={onSubmit}
      {...props}
    >
      {children}
    </form>
  );
}

export function PromptInputTextarea({
  className,
  onKeyDown,
  ...props
}: ComponentProps<"textarea">) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      onKeyDown?.(e);
      if (e.defaultPrevented) return;
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        e.currentTarget.form?.requestSubmit();
      }
    },
    [onKeyDown]
  );

  return (
    <textarea
      rows={3}
      className={cn(
        "min-h-20 w-full resize-none rounded-none border border-zinc-700 bg-black px-2.5 py-2 text-xs text-zinc-100 outline-none placeholder:text-zinc-500 focus:border-zinc-600",
        className
      )}
      onKeyDown={handleKeyDown}
      {...props}
    />
  );
}

export function PromptInputSubmit({
  className,
  children,
  ...props
}: ComponentProps<typeof Button>) {
  return (
    <Button
      type="submit"
      size="icon-sm"
      className={cn(
        "border border-zinc-700 bg-zinc-100 text-zinc-900 hover:bg-white",
        className
      )}
      {...props}
    >
      {children ?? <CornerDownLeft className="size-4" />}
      <span className="sr-only">Send message</span>
    </Button>
  );
}

export function PromptInputActions({
  className,
  children,
  ...props
}: ComponentProps<"div">) {
  return (
    <div className={cn("flex items-center gap-1", className)} {...props}>
      {children}
    </div>
  );
}

const ACCEPT_TYPES = "image/png,image/jpeg,image/gif,image/webp,application/pdf";

export function PromptInputFileUpload({
  className,
  onFiles,
  accept = ACCEPT_TYPES,
  disabled,
  ...props
}: Omit<ComponentProps<typeof Button>, "onClick"> & {
  onFiles?: (files: FileList) => void;
  accept?: string;
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <>
      <input
        type="file"
        ref={inputRef}
        className="hidden"
        accept={accept}
        multiple
        onChange={(e) => {
          if (e.target.files?.length) {
            onFiles?.(e.target.files);
            e.target.value = "";
          }
        }}
      />
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        className={cn("text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800", className)}
        onClick={() => inputRef.current?.click()}
        disabled={disabled}
        {...props}
      >
        <Paperclip className="size-3.5" />
        <span className="sr-only">Attach files</span>
      </Button>
    </>
  );
}
