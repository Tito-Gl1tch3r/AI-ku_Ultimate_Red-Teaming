
import { useCallback, useEffect, useRef, useState, type CSSProperties, type PointerEvent as ReactPointerEvent } from "react";

const STORAGE_KEY = "tracesurface:detail-width";
const MIN_PX = 320;
const MAX_RATIO = 0.55;

function defaultWidth() {
  return Math.min(420, Math.round(window.innerWidth * 0.36));
}

function clampWidth(px: number) {
  const max = Math.round(window.innerWidth * MAX_RATIO);
  return Math.min(max, Math.max(MIN_PX, Math.round(px)));
}

function readStored(): number {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaultWidth();
    const n = Number.parseInt(raw, 10);
    return Number.isFinite(n) ? clampWidth(n) : defaultWidth();
  } catch {
    return defaultWidth();
  }
}

export function useResizablePanel() {
  const [width, setWidth] = useState(readStored);
  const dragging = useRef(false);
  const startX = useRef(0);
  const startWidth = useRef(width);

  const persist = useCallback((next: number) => {
    const clamped = clampWidth(next);
    setWidth(clamped);
    try {
      localStorage.setItem(STORAGE_KEY, String(clamped));
    } catch {

    }
  }, []);

  const onPointerDown = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      event.preventDefault();
      dragging.current = true;
      startX.current = event.clientX;
      startWidth.current = width;
      event.currentTarget.setPointerCapture(event.pointerId);
    },
    [width],
  );

  useEffect(() => {
    const onMove = (event: PointerEvent) => {
      if (!dragging.current) return;
      const delta = startX.current - event.clientX;
      persist(startWidth.current + delta);
    };
    const onUp = () => {
      dragging.current = false;
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointercancel", onUp);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onUp);
    };
  }, [persist]);

  useEffect(() => {
    const onResize = () => setWidth((w) => clampWidth(w));
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  return { width, onPointerDown, widthStyle: { "--detail-width": `${width}px` } as CSSProperties };
}
