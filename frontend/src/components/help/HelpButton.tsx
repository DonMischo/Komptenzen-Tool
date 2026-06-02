"use client";

import { useState } from "react";
import { X, HelpCircle } from "lucide-react";

export interface HelpSection {
  heading?: string;
  text: string;
}

interface Props {
  title: string;
  sections: HelpSection[];
}

/**
 * A circular ? button that opens a help modal for its parent page/section.
 * Designed to sit next to a page title: <h2>…</h2> <HelpButton … />
 */
export function HelpButton({ title, sections }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        title="Hilfe zu dieser Seite"
        aria-label="Hilfe"
        className={[
          "inline-flex items-center justify-center",
          "w-7 h-7 rounded-full",
          "bg-primary/10 text-primary border border-primary/25",
          "hover:bg-primary/20 hover:border-primary/50",
          "hover:scale-110 active:scale-95",
          "transition-all duration-150",
          "font-bold text-sm select-none shrink-0",
        ].join(" ")}
      >
        ?
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm"
          onClick={() => setOpen(false)}
        >
          <div
            className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Colored header */}
            <div className="bg-primary px-5 py-4 flex items-center justify-between">
              <div className="flex items-center gap-2 text-white">
                <HelpCircle className="h-5 w-5 shrink-0" />
                <span className="font-semibold text-base">{title}</span>
              </div>
              <button
                onClick={() => setOpen(false)}
                className="text-white/70 hover:text-white transition-colors"
                aria-label="Schließen"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Content */}
            <div className="px-5 py-4 space-y-4 max-h-[65vh] overflow-y-auto">
              {sections.map((s, i) => (
                <div key={i}>
                  {s.heading && (
                    <p className="font-semibold text-sm text-foreground mb-0.5">
                      {s.heading}
                    </p>
                  )}
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {s.text}
                  </p>
                </div>
              ))}
            </div>

            <div className="px-5 pb-4">
              <button
                onClick={() => setOpen(false)}
                className="w-full py-2 rounded-lg bg-muted text-sm text-muted-foreground hover:bg-muted/80 transition-colors"
              >
                Schließen
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
