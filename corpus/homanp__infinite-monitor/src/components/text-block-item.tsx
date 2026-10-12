"use client";

import { useRef, useState, useCallback, useEffect } from "react";
import { Trash2, GripVertical, Minus, Plus } from "lucide-react";
import { CELL_W, CELL_H, MARGIN } from "@/components/infinite-canvas";
import type { CanvasLayout } from "@/store/widget-store";

const MIN_W = 1;
const MIN_H = 1;

const FONT_SIZES = [14, 18, 24, 32, 48, 64, 96];

function gridToPixelX(col: number) {
  return col * (CELL_W + MARGIN);
}
function gridToPixelY(row: number) {
  return row * (CELL_H + MARGIN);
}
function gridWidth(cols: number) {
  return cols * (CELL_W + MARGIN) - MARGIN;
}
function gridHeight(rows: number) {
  return rows * (CELL_H + MARGIN) - MARGIN;
}

interface TextBlockItemProps {
  id: string;
  text: string;
  fontSize: number;
  layout: CanvasLayout;
  zoom: number;
  onTextChange: (text: string) => void;
  onFontSizeChange: (fontSize: number) => void;
  onLayoutChange: (layout: CanvasLayout) => void;
  onRemove: () => void;
}

export function TextBlockItem({
  id,
  text,
  fontSize,
  layout,
  zoom,
  onTextChange,
  onFontSizeChange,
  onLayoutChange,
  onRemove,
}: TextBlockItemProps) {
  const [isEditing, setIsEditing] = useState(!text);
  const [dragOffset, setDragOffset] = useState<{ dx: number; dy: number } | null>(null);
  const [resizeOffset, setResizeOffset] = useState<{ dw: number; dh: number } | null>(null);
  const [isHovered, setIsHovered] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const dragStart = useRef({ clientX: 0, clientY: 0 });
  const dragOffsetRef = useRef<{ dx: number; dy: number } | null>(null);
  const resizeOffsetRef = useRef<{ dw: number; dh: number } | null>(null);

  const { x, y, w, h } = layout;

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isEditing]);

  const handleDragStart = useCallback(
    (e: React.PointerEvent) => {
      if (!(e.target as HTMLElement).closest(".text-drag-handle")) return;
      e.stopPropagation();
      e.preventDefault();
      dragStart.current = { clientX: e.clientX, clientY: e.clientY };
      const initial = { dx: 0, dy: 0 };
      dragOffsetRef.current = initial;
      setDragOffset(initial);
      (e.target as HTMLElement).setPointerCapture(e.pointerId);

      const onMove = (me: PointerEvent) => {
        const dx = (me.clientX - dragStart.current.clientX) / zoom;
        const dy = (me.clientY - dragStart.current.clientY) / zoom;
        const offset = { dx, dy };
        dragOffsetRef.current = offset;
        setDragOffset(offset);
      };
      const onUp = () => {
        document.removeEventListener("pointermove", onMove);
        document.removeEventListener("pointerup", onUp);
        const prev = dragOffsetRef.current;
        dragOffsetRef.current = null;
        setDragOffset(null);
        if (prev) {
          const newX = Math.round((gridToPixelX(x) + prev.dx) / (CELL_W + MARGIN));
          const newY = Math.round((gridToPixelY(y) + prev.dy) / (CELL_H + MARGIN));
          onLayoutChange({ x: newX, y: newY, w, h });
        }
      };
      document.addEventListener("pointermove", onMove);
      document.addEventListener("pointerup", onUp);
    },
    [x, y, w, h, zoom, onLayoutChange]
  );

  const handleResizeStart = useCallback(
    (e: React.PointerEvent) => {
      e.stopPropagation();
      e.preventDefault();
      dragStart.current = { clientX: e.clientX, clientY: e.clientY };
      const initial = { dw: 0, dh: 0 };
      resizeOffsetRef.current = initial;
      setResizeOffset(initial);
      (e.target as HTMLElement).setPointerCapture(e.pointerId);

      const onMove = (me: PointerEvent) => {
        const dw = (me.clientX - dragStart.current.clientX) / zoom;
        const dh = (me.clientY - dragStart.current.clientY) / zoom;
        const offset = { dw, dh };
        resizeOffsetRef.current = offset;
        setResizeOffset(offset);
      };
      const onUp = () => {
        document.removeEventListener("pointermove", onMove);
        document.removeEventListener("pointerup", onUp);
        const prev = resizeOffsetRef.current;
        resizeOffsetRef.current = null;
        setResizeOffset(null);
        if (prev) {
          const newW = Math.max(
            MIN_W,
            Math.round((gridWidth(w) + prev.dw + MARGIN) / (CELL_W + MARGIN))
          );
          const newH = Math.max(
            MIN_H,
            Math.round((gridHeight(h) + prev.dh + MARGIN) / (CELL_H + MARGIN))
          );
          onLayoutChange({ x, y, w: newW, h: newH });
        }
      };
      document.addEventListener("pointermove", onMove);
      document.addEventListener("pointerup", onUp);
    },
    [x, y, w, h, zoom, onLayoutChange]
  );

  const cycleFontSize = (direction: 1 | -1) => {
    const idx = FONT_SIZES.indexOf(fontSize);
    const nextIdx = Math.max(0, Math.min(FONT_SIZES.length - 1, (idx === -1 ? 2 : idx) + direction));
    onFontSizeChange(FONT_SIZES[nextIdx]);
  };

  const pixelX = gridToPixelX(x) + (dragOffset?.dx ?? 0);
  const pixelY = gridToPixelY(y) + (dragOffset?.dy ?? 0);
  const pixelW = gridWidth(w) + (resizeOffset?.dw ?? 0);
  const pixelH = gridHeight(h) + (resizeOffset?.dh ?? 0);

  const snappedX = dragOffset ? Math.round(pixelX / (CELL_W + MARGIN)) : null;
  const snappedY = dragOffset ? Math.round(pixelY / (CELL_H + MARGIN)) : null;

  const showControls = isHovered || isEditing;

  return (
    <>
      {dragOffset && snappedX !== null && snappedY !== null && (
        <div
          className="absolute border border-dashed border-teal-500/50 bg-teal-500/5 pointer-events-none"
          style={{
            left: gridToPixelX(snappedX),
            top: gridToPixelY(snappedY),
            width: gridWidth(w),
            height: gridHeight(h),
          }}
        />
      )}
      <div
        data-widget
        data-text-block={id}
        className="absolute group"
        style={{
          left: pixelX,
          top: pixelY,
          width: Math.max(gridWidth(MIN_W), pixelW),
          height: Math.max(gridHeight(MIN_H), pixelH),
          zIndex: dragOffset || resizeOffset ? 50 : "auto",
          cursor: "default",
        }}
        onPointerDown={handleDragStart}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        <div
          className="w-full h-full relative flex flex-col"
          style={{
            borderRadius: 0,
          }}
        >
          {showControls && (
            <div className="absolute -top-7 left-0 flex items-center gap-0.5 bg-zinc-800 border border-zinc-700 px-1 py-0.5 z-20">
              <button
                className="text-drag-handle p-0.5 text-zinc-500 hover:text-zinc-300 cursor-grab active:cursor-grabbing"
                title="Drag to move"
              >
                <GripVertical className="w-3 h-3" />
              </button>
              <button
                className="p-0.5 text-zinc-500 hover:text-zinc-300"
                onClick={() => cycleFontSize(-1)}
                title="Decrease font size"
              >
                <Minus className="w-3 h-3" />
              </button>
              <span className="text-[9px] text-zinc-500 w-5 text-center tabular-nums select-none">
                {fontSize}
              </span>
              <button
                className="p-0.5 text-zinc-500 hover:text-zinc-300"
                onClick={() => cycleFontSize(1)}
                title="Increase font size"
              >
                <Plus className="w-3 h-3" />
              </button>
              <button
                className="p-0.5 text-zinc-500 hover:text-red-400"
                onClick={onRemove}
                title="Remove text block"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          )}

          {isEditing ? (
            <textarea
              ref={inputRef}
              value={text}
              onChange={(e) => onTextChange(e.target.value)}
              onBlur={() => setIsEditing(false)}
              onKeyDown={(e) => {
                if (e.key === "Escape") setIsEditing(false);
              }}
              className="w-full h-full bg-transparent text-zinc-100 outline-none resize-none overflow-hidden placeholder:text-zinc-600"
              style={{
                fontSize: `${fontSize}px`,
                lineHeight: 1.2,
                fontWeight: fontSize >= 32 ? 600 : 400,
              }}
              placeholder="Type here..."
            />
          ) : (
            <div
              className="w-full h-full cursor-text overflow-hidden"
              onDoubleClick={() => setIsEditing(true)}
              style={{
                fontSize: `${fontSize}px`,
                lineHeight: 1.2,
                fontWeight: fontSize >= 32 ? 600 : 400,
                color: text ? "rgb(228 228 231)" : "rgb(82 82 91)",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {text || "Double-click to edit"}
            </div>
          )}
        </div>

        {showControls && (
          <div
            className="absolute bottom-0 right-0 w-4 h-4 cursor-se-resize z-10"
            onPointerDown={handleResizeStart}
          >
            <svg
              className="absolute right-0.5 bottom-0.5 w-2.5 h-2.5 text-zinc-600"
              viewBox="0 0 10 10"
              fill="currentColor"
            >
              <circle cx="8" cy="2" r="1.2" />
              <circle cx="8" cy="6" r="1.2" />
              <circle cx="4" cy="6" r="1.2" />
            </svg>
          </div>
        )}
      </div>
    </>
  );
}
