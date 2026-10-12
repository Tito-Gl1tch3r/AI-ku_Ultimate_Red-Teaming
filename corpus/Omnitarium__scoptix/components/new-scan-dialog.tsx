"use client";

import { useId, useRef, useState } from "react";
import { NewScanForm } from "@/components/new-scan-form";

type NewScanDialogProps = {
  buttonLabel?: string;
  buttonClassName?: string;
  renderTrigger?: (props: { onClick: () => void }) => React.ReactNode;
};

export function NewScanDialog({
  buttonLabel = "New Scan",
  buttonClassName = "shadow-clay inline-flex items-center justify-center rounded-xl bg-gradient-to-r from-accent to-accent-dim px-4 py-3 text-[13px] font-semibold text-void transition-transform hover:scale-[1.02]",
  renderTrigger,
}: NewScanDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const [open, setOpen] = useState(false);

  function openDialog() {
    const dialog = dialogRef.current;
    if (!dialog) return;
    setOpen(true);
    if (!dialog.open) dialog.showModal();
  }

  function closeDialog() {
    setOpen(false);
    dialogRef.current?.close();
  }

  return (
    <>
      {renderTrigger ? (
        renderTrigger({ onClick: openDialog })
      ) : (
        <button type="button" onClick={openDialog} className={buttonClassName}>
          {buttonLabel}
        </button>
      )}

      <dialog
        ref={dialogRef}
        onClose={() => setOpen(false)}
        className="url-search-dialog w-[min(100%,520px)] max-w-[calc(100vw-2rem)] rounded-2xl border border-line bg-[var(--glass-panel-bg)] p-0 text-cream shadow-glass"
        aria-labelledby={titleId}
      >
        <div className="border-b border-line px-5 py-4">
          <h2 id={titleId} className="text-[14px] font-semibold text-cream">
            Start new scan
          </h2>
          <p className="mt-1 text-[11px] text-muted">
            Type a domain or subdomain. Engine detection, target creation, and expansion remain automatic.
          </p>
        </div>

        <div className="px-5 py-5">
          {open ? <NewScanForm autoFocus /> : null}
        </div>

        <div className="flex justify-end border-t border-line px-5 py-4">
          <button
            type="button"
            onClick={closeDialog}
            className="rounded-lg border border-line px-3 py-2 text-[12px] text-muted transition-colors hover:bg-[var(--nav-hover-bg)] hover:text-cream"
          >
            Close
          </button>
        </div>
      </dialog>
    </>
  );
}
