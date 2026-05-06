"use client";

import { ExportProgressEvent } from "@/types/api";
import { CheckCircle, XCircle, Square, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  events: ExportProgressEvent[];
  total: number;
  isDone: boolean;
  onStop: () => void;
  onClose: () => void;
}

export function ExportProgress({ events, total, isDone, onStop, onClose }: Props) {
  const progressEvents = events.filter((e) => e.type === "progress");
  const current = progressEvents.length;
  const pct = total > 0 ? Math.round((current / total) * 100) : 0;

  const errors = progressEvents.filter((e) => !e.success);
  const successes = progressEvents.filter((e) => e.success);

  return (
    <div className="bg-white border rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">Zeugnisse erstellen</h3>
        {isDone && (
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Progress bar */}
      <div className="space-y-1">
        <div className="flex justify-between text-sm text-muted-foreground">
          <span>{current} / {total}</span>
          <span>{pct}%</span>
        </div>
        <div className="h-2 bg-muted rounded-full overflow-hidden">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-300",
              isDone && errors.length === 0
                ? "bg-green-500"
                : isDone && errors.length > 0
                ? "bg-amber-500"
                : "bg-primary"
            )}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* Last processed */}
      {!isDone && progressEvents.length > 0 && (
        <p className="text-sm text-muted-foreground">
          Kompiliere: {progressEvents[progressEvents.length - 1]?.basename}
        </p>
      )}

      {/* Done summary */}
      {isDone && (
        <div className="text-sm space-y-1">
          <p className="flex items-center gap-1.5 text-green-600">
            <CheckCircle className="h-4 w-4" />
            {successes.length} Zeugnis{successes.length !== 1 ? "se" : ""} erstellt
          </p>
          {errors.length > 0 && (
            <p className="flex items-center gap-1.5 text-red-600">
              <XCircle className="h-4 w-4" />
              {errors.length} Fehler
            </p>
          )}
        </div>
      )}

      {/* Error details */}
      {errors.length > 0 && (
        <details className="border rounded-md p-3 bg-red-50">
          <summary className="cursor-pointer text-sm font-medium text-red-700">
            Fehler anzeigen ({errors.length})
          </summary>
          <ul className="mt-2 space-y-2">
            {errors.map((e, i) => (
              <li key={i} className="text-xs">
                <span className="font-medium">{e.basename}</span>
                {e.error && (
                  <pre className="mt-1 bg-white rounded p-2 overflow-x-auto text-red-600 whitespace-pre-wrap break-all">
                    {e.error.slice(-2000)}
                  </pre>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}

      {/* Progress list */}
      <div className="max-h-48 overflow-y-auto space-y-1">
        {progressEvents.map((e, i) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            {e.success ? (
              <CheckCircle className="h-3.5 w-3.5 text-green-500 shrink-0" />
            ) : (
              <XCircle className="h-3.5 w-3.5 text-red-500 shrink-0" />
            )}
            <span className="font-mono truncate">{e.basename}</span>
          </div>
        ))}
        {!isDone && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground animate-pulse">
            <Square className="h-3.5 w-3.5 shrink-0" />
            <span>Kompiliere…</span>
          </div>
        )}
      </div>

      {!isDone && (
        <button
          onClick={onStop}
          className="border border-red-300 text-red-600 text-sm px-3 py-1.5 rounded-md hover:bg-red-50"
        >
          ⏹ Stopp
        </button>
      )}
    </div>
  );
}
