"use client";

import { useState } from "react";
import { RichTextEditorModal } from "@/components/stammdaten/RichTextEditorModal";

// ---------------------------------------------------------------------------
// Option definitions
// ---------------------------------------------------------------------------

export const NIVEAU_OPTIONS = [
  { value: "",         label: "— kein Niveau —" },
  { value: "1",        label: "1 – Anforderungsebene 1" },
  { value: "2",        label: "2 – Anforderungsebene 2" },
  { value: "3",        label: "3 – Anforderungsebene 3" },
  { value: "7",        label: "7 – bis Kl. 7 ohne AE" },
  { value: "8",        label: "8 – bis Kl. 8 ohne AE" },
  { value: "9",        label: "9 – bis Kl. 9 ohne AE" },
  { value: "ne",       label: "ne – nicht erteilt" },
  { value: "HJ2",      label: "HJ2 – 2. Halbjahr belegt" },
  { value: "__text__", label: "Freitext…" },
] as const;

const KNOWN_VALUES = new Set<string>(
  NIVEAU_OPTIONS.map((o) => o.value).filter((v) => v !== "__text__")
);

// A value is "custom free text" if it's non-empty and not a known code
export function isNiveauCustom(value: string): boolean {
  return value !== "" && !KNOWN_VALUES.has(value);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface Props {
  value: string;
  studentName?: string;
  onChange: (v: string) => void;
}

export function NiveauSelect({ value, studentName, onChange }: Props) {
  const [modalOpen, setModalOpen] = useState(false);

  const isCustom = isNiveauCustom(value);
  const selectValue = isCustom ? "__text__" : value;

  const handleSelectChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const v = e.target.value;
    if (v === "__text__") {
      setModalOpen(true);
    } else {
      onChange(v);
    }
  };

  return (
    <>
      <div className="flex items-center gap-1">
        <select
          value={selectValue}
          onChange={handleSelectChange}
          className="border rounded px-1.5 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
          style={{ maxWidth: 150 }}
        >
          {NIVEAU_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        {/* Edit button when a free-text value is already stored */}
        {isCustom && (
          <button
            type="button"
            onClick={() => setModalOpen(true)}
            className="text-blue-600 hover:text-blue-800 shrink-0"
            title="Freitext bearbeiten"
          >
            ✏️
          </button>
        )}
      </div>

      <RichTextEditorModal
        title={studentName ? `Niveau – Freitext (${studentName})` : "Niveau – Freitext"}
        initialHtml={isCustom ? value : ""}
        open={modalOpen}
        onSave={(html) => {
          onChange(html && html !== "<p></p>" ? html : "");
          setModalOpen(false);
        }}
        onClose={() => setModalOpen(false)}
      />
    </>
  );
}
