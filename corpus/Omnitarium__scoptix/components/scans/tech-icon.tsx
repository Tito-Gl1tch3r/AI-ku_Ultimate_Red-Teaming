"use client";

import { useEffect, useState } from "react";
import { apiUrl } from "@/lib/api-url";

/**
 * Technology icon with a graceful monogram fallback.
 * Tries the local Wappalyzer icon set under /tech-icons; if missing/broken,
 * renders a tinted initial badge derived from the technology name.
 */
export function TechIcon({
  name,
  iconName,
  size = 16,
  className = "",
}: {
  name: string;
  iconName: string | null;
  size?: number;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);

  // Reset on tech change so a previously-failed icon retries.
  useEffect(() => {
    setFailed(false);
  }, [iconName]);

  const showFallback = !iconName || failed;
  const px = `${size}px`;

  if (showFallback) {
    const initial = (name.trim()[0] ?? "?").toUpperCase();
    const hue = hashHue(name);
    return (
      <span
        aria-hidden
        className={`inline-flex shrink-0 items-center justify-center rounded-[4px] font-semibold leading-none ${className}`}
        style={{
          width: px,
          height: px,
          fontSize: `${Math.round(size * 0.55)}px`,
          color: `hsl(${hue} 70% 78%)`,
          background: `hsl(${hue} 45% 22%)`,
          border: `1px solid hsl(${hue} 45% 32%)`,
        }}
      >
        {initial}
      </span>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element -- local static icon set (2400+ files)
    <img
      src={apiUrl(`/tech-icons/${iconName}`)}
      alt=""
      width={size}
      height={size}
      className={`shrink-0 rounded-[3px] object-contain ${className}`}
      style={{ width: px, height: px }}
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}

/** Stable hue (0-359) derived from a string for consistent fallback colors. */
function hashHue(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 360;
  return h;
}
