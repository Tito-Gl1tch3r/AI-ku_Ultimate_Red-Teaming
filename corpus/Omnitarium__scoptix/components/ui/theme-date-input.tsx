"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import { IconCalendar, IconChevronRight } from "@/components/ui-icons";

function pad2(n: number) {
  return String(n).padStart(2, "0");
}

function toIso(year: number, month: number, day: number) {
  return `${year}-${pad2(month + 1)}-${pad2(day)}`;
}

function parseIso(value?: string): Date | null {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const d = new Date(`${value}T00:00:00`);
  return Number.isNaN(d.getTime()) ? null : d;
}

function formatDisplay(iso: string) {
  const d = parseIso(iso);
  if (!d) return iso;
  return d.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

const MONTHS = Array.from({ length: 12 }, (_, i) =>
  new Date(2000, i, 1).toLocaleDateString("en-GB", { month: "long" }),
);

const WEEKDAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];

type CalendarCell = {
  day: number;
  inMonth: boolean;
  monthOffset: number;
};

function buildCalendarWeeks(year: number, month: number): CalendarCell[][] {
  const firstWeekday = (new Date(year, month, 1).getDay() + 6) % 7;
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const daysInPrevMonth = new Date(year, month, 0).getDate();

  const cells: CalendarCell[] = [];

  for (let i = firstWeekday - 1; i >= 0; i--) {
    cells.push({ day: daysInPrevMonth - i, inMonth: false, monthOffset: -1 });
  }
  for (let day = 1; day <= daysInMonth; day++) {
    cells.push({ day, inMonth: true, monthOffset: 0 });
  }
  let nextDay = 1;
  while (cells.length % 7 !== 0 || cells.length < 35) {
    cells.push({ day: nextDay++, inMonth: false, monthOffset: 1 });
  }

  const weeks: CalendarCell[][] = [];
  for (let i = 0; i < cells.length; i += 7) {
    weeks.push(cells.slice(i, i + 7));
  }
  return weeks;
}

function yearOptions(anchor: number) {
  const start = anchor - 8;
  return Array.from({ length: 17 }, (_, i) => start + i);
}

export function ThemeDateInput({
  id,
  name,
  defaultValue,
  align = "start",
  "aria-label": ariaLabel,
}: {
  id: string;
  name: string;
  defaultValue?: string;
  align?: "start" | "end";
  "aria-label"?: string;
}) {
  const [value, setValue] = useState(defaultValue ?? "");
  const [open, setOpen] = useState(false);
  const [viewYear, setViewYear] = useState(
    () => parseIso(defaultValue)?.getFullYear() ?? new Date().getFullYear(),
  );
  const [viewMonth, setViewMonth] = useState(
    () => parseIso(defaultValue)?.getMonth() ?? new Date().getMonth(),
  );
  const rootRef = useRef<HTMLDivElement>(null);
  const popoverId = useId();

  const weeks = useMemo(
    () => buildCalendarWeeks(viewYear, viewMonth),
    [viewYear, viewMonth],
  );

  const years = useMemo(() => yearOptions(viewYear), [viewYear]);
  const selected = parseIso(value);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  function selectCell(cell: CalendarCell) {
    if (!cell.inMonth) return;
    setValue(toIso(viewYear, viewMonth, cell.day));
    setOpen(false);
  }

  function shiftMonth(delta: number) {
    const d = new Date(viewYear, viewMonth + delta, 1);
    setViewYear(d.getFullYear());
    setViewMonth(d.getMonth());
  }

  function isSelected(cell: CalendarCell) {
    if (!selected || !cell.inMonth) return false;
    return (
      selected.getFullYear() === viewYear &&
      selected.getMonth() === viewMonth &&
      selected.getDate() === cell.day
    );
  }

  const today = new Date();
  const isToday = (cell: CalendarCell) =>
    cell.inMonth &&
    today.getFullYear() === viewYear &&
    today.getMonth() === viewMonth &&
    today.getDate() === cell.day;

  return (
    <div ref={rootRef} className="scx-date-input-wrap">
      <input type="hidden" name={name} value={value} />
      <button
        type="button"
        id={id}
        aria-label={ariaLabel}
        aria-expanded={open}
        aria-controls={popoverId}
        onClick={() => setOpen((v) => !v)}
        className="scx-date-input-trigger"
      >
        <span className={value ? "text-cream" : "text-muted"}>
          {value ? formatDisplay(value) : "Select date"}
        </span>
        <IconCalendar className="size-3.5 shrink-0 text-muted" />
      </button>

      {open ? (
        <div
          id={popoverId}
          className={`scx-date-picker-popover${align === "end" ? " scx-date-picker-popover--end" : ""}`}
          role="dialog"
          aria-label={ariaLabel}
        >
          <div className="scx-date-picker-header">
            <button
              type="button"
              onClick={() => shiftMonth(-1)}
              className="scx-date-picker-nav-btn"
              aria-label="Previous month"
            >
              <IconChevronRight className="size-3.5 rotate-180" />
            </button>

            <div className="scx-date-picker-month-year">
              <select
                value={viewMonth}
                onChange={(e) => setViewMonth(Number(e.target.value))}
                className="scx-date-picker-select"
                aria-label="Month"
              >
                {MONTHS.map((label, idx) => (
                  <option key={label} value={idx}>
                    {label}
                  </option>
                ))}
              </select>
              <span className="text-muted">/</span>
              <select
                value={viewYear}
                onChange={(e) => setViewYear(Number(e.target.value))}
                className="scx-date-picker-select scx-date-picker-select--year"
                aria-label="Year"
              >
                {years.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="button"
              onClick={() => shiftMonth(1)}
              className="scx-date-picker-nav-btn"
              aria-label="Next month"
            >
              <IconChevronRight className="size-3.5" />
            </button>
          </div>

          <div className="scx-date-picker-body">
            <div className="scx-date-picker-weekdays">
              {WEEKDAYS.map((day) => (
                <span key={day} className="scx-date-picker-weekday">
                  {day}
                </span>
              ))}
            </div>

            {weeks.map((week, weekIdx) => (
              <div key={`week-${weekIdx}`} className="scx-date-picker-week">
                {week.map((cell, dayIdx) => {
                  const selectedDay = isSelected(cell);
                  const todayDay = isToday(cell);
                  return (
                    <button
                      key={`${weekIdx}-${dayIdx}-${cell.day}-${cell.inMonth}`}
                      type="button"
                      disabled={!cell.inMonth}
                      onClick={() => selectCell(cell)}
                      className={[
                        "scx-date-picker-day-btn",
                        !cell.inMonth ? "scx-date-picker-day-btn--muted" : "",
                        selectedDay ? "scx-date-picker-day-btn--selected" : "",
                        todayDay && !selectedDay ? "scx-date-picker-day-btn--today" : "",
                      ]
                        .filter(Boolean)
                        .join(" ")}
                    >
                      {cell.day}
                    </button>
                  );
                })}
              </div>
            ))}
          </div>

          <div className="scx-date-picker-footer">
            <span className="scx-date-picker-footer-value">
              {value ? formatDisplay(value) : "No date selected"}
            </span>
            {value ? (
              <button
                type="button"
                onClick={() => {
                  setValue("");
                  setOpen(false);
                }}
                className="scx-date-picker-footer-clear"
              >
                Clear
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="scx-date-picker-footer-clear"
              >
                Close
              </button>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
