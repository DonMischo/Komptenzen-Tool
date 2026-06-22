"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { setupApi } from "@/lib/api";
import { QK } from "@/lib/queries";
import { StudentImportResponse, StudentPreviewResponse, StudentDiffRow } from "@/types/api";
import { Upload, ChevronDown, ChevronRight } from "lucide-react";

const FIELD_OPTIONS = [
  { key: "klasse",      label: "Klasse aktualisieren" },
  { key: "fehltage",    label: "Fehlzeiten aktualisieren" },
  { key: "zeugnistext", label: "Zeugnistext überschreiben ⚠" },
  { key: "bemerkungen", label: "Bemerkungen überschreiben ⚠" },
];

function DiffSection({
  title,
  rows,
  color,
}: {
  title: string;
  rows: StudentDiffRow[];
  color: string;
}) {
  const [open, setOpen] = useState(rows.length <= 5);
  if (rows.length === 0) return null;
  return (
    <div className="space-y-1">
      <button
        className={`flex items-center gap-1.5 text-sm font-medium ${color}`}
        onClick={() => setOpen((o) => !o)}
      >
        {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        {title} ({rows.length})
      </button>
      {open && (
        <ul className="ml-5 space-y-1 text-xs text-muted-foreground">
          {rows.map((r, i) => (
            <li key={i}>
              <span className="font-medium text-foreground">{r.name}</span>
              {" "}
              <span className="text-muted-foreground">({r.school_class})</span>
              {r.changes.length > 0 && (
                <ul className="ml-3 mt-0.5 space-y-0.5">
                  {r.changes.map((c, j) => (
                    <li key={j}>
                      <span className="font-medium">{c.field}:</span>{" "}
                      {c.old ? (
                        <>
                          <span className="line-through text-red-500">{c.old}</span>
                          {" → "}
                          <span className="text-green-700">{c.new || "—"}</span>
                        </>
                      ) : (
                        <span className="text-green-700">{c.new}</span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function StudentImportPanel() {
  const qc = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [removeMissing, setRemoveMissing] = useState(false);
  const [updateFields, setUpdateFields] = useState<string[]>(["klasse", "fehltage"]);
  const [preview, setPreview] = useState<StudentPreviewResponse | null>(null);
  const [result, setResult] = useState<StudentImportResponse | null>(null);

  const toggleField = (key: string) =>
    setUpdateFields((prev) =>
      prev.includes(key) ? prev.filter((f) => f !== key) : [...prev, key]
    );

  const previewMutation = useMutation({
    mutationFn: () => setupApi.previewStudents(file!, removeMissing, updateFields),
    onSuccess: (res) => {
      setPreview(res.data);
      setResult(null);
    },
    onError: () => toast.error("Vorschau fehlgeschlagen"),
  });

  const applyMutation = useMutation({
    mutationFn: () => setupApi.uploadStudents(file!, removeMissing, updateFields),
    onSuccess: (res) => {
      setResult(res.data);
      setPreview(null);
      qc.invalidateQueries({ queryKey: QK.schemaStatus });
      toast.success(
        `${res.data.added} hinzugefügt, ${res.data.updated} aktualisiert, ${res.data.removed} entfernt`
      );
    },
    onError: () => toast.error("Import fehlgeschlagen"),
  });

  const hasChanges =
    preview &&
    (preview.to_add.length > 0 ||
      preview.to_update.length > 0 ||
      preview.to_remove.length > 0);

  return (
    <div className="bg-white rounded-xl border p-5 space-y-4">
      <h3 className="font-semibold text-lg">Schüler importieren</h3>
      <p className="text-xs text-muted-foreground">
        Pflichtfelder: Nachname, Vorname, Klasse, Geburtsdatum (DD.MM.YYYY)
      </p>

      {/* Step 1: file + options */}
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 cursor-pointer border rounded-md px-3 py-1.5 text-sm hover:bg-muted">
            <Upload className="h-4 w-4" />
            {file ? file.name : "CSV auswählen…"}
            <input
              type="file"
              accept=".csv"
              className="hidden"
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null);
                setPreview(null);
                setResult(null);
              }}
            />
          </label>
        </div>

        {/* Field selection */}
        <div className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground">Was soll aktualisiert werden?</p>
          <div className="flex flex-wrap gap-x-4 gap-y-1">
            {FIELD_OPTIONS.map(({ key, label }) => (
              <label key={key} className="flex items-center gap-1.5 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={updateFields.includes(key)}
                  onChange={() => toggleField(key)}
                  className="rounded"
                />
                {label}
              </label>
            ))}
            <label className="flex items-center gap-1.5 text-sm cursor-pointer text-red-600">
              <input
                type="checkbox"
                checked={removeMissing}
                onChange={(e) => setRemoveMissing(e.target.checked)}
                className="rounded"
              />
              Fehlende Schüler entfernen ⚠
            </label>
          </div>
        </div>

        <button
          onClick={() => previewMutation.mutate()}
          disabled={!file || previewMutation.isPending}
          className="bg-muted text-foreground text-sm px-4 py-1.5 rounded-md hover:bg-muted/70 border disabled:opacity-50"
        >
          {previewMutation.isPending ? "Prüfe…" : "Vorschau anzeigen"}
        </button>
      </div>

      {/* Step 2: diff preview */}
      {preview && (
        <div className="border rounded-md p-4 space-y-3 bg-muted/20">
          <p className="text-sm font-semibold">Vorschau der Änderungen</p>

          {!hasChanges && (
            <p className="text-sm text-muted-foreground">
              Keine Änderungen — {preview.unchanged} Schüler unverändert.
            </p>
          )}

          <DiffSection
            title="Neu hinzufügen"
            rows={preview.to_add}
            color="text-green-700"
          />
          <DiffSection
            title="Aktualisieren"
            rows={preview.to_update}
            color="text-blue-700"
          />
          <DiffSection
            title="Entfernen"
            rows={preview.to_remove}
            color="text-red-600"
          />

          {preview.unchanged > 0 && hasChanges && (
            <p className="text-xs text-muted-foreground">
              {preview.unchanged} Schüler unverändert
            </p>
          )}

          {preview.errors.length > 0 && (
            <details>
              <summary className="cursor-pointer text-sm text-amber-600">
                {preview.errors.length} Warnung(en)
              </summary>
              <ul className="mt-1 space-y-0.5 text-xs text-muted-foreground ml-3">
                {preview.errors.map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            </details>
          )}

          {preview.to_remove.length > 0 && (
            <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded p-2">
              ⚠ {preview.to_remove.length} Schüler werden unwiderruflich gelöscht (inkl. Noten und Texte).
            </div>
          )}

          <div className="flex gap-2 pt-1">
            <button
              onClick={() => applyMutation.mutate()}
              disabled={applyMutation.isPending || !hasChanges}
              className="bg-primary text-white text-sm px-4 py-1.5 rounded-md hover:bg-primary/90 disabled:opacity-50"
            >
              {applyMutation.isPending ? "Importiere…" : "Jetzt anwenden"}
            </button>
            <button
              onClick={() => setPreview(null)}
              className="text-sm px-4 py-1.5 rounded-md border hover:bg-muted"
            >
              Abbrechen
            </button>
          </div>
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="border rounded-md p-3 bg-muted/30 text-sm space-y-1">
          <p>✅ {result.added} hinzugefügt · {result.updated} aktualisiert · {result.removed} entfernt</p>
          {result.errors.length > 0 && (
            <details>
              <summary className="cursor-pointer text-amber-600">
                {result.errors.length} Warnung(en)
              </summary>
              <ul className="mt-1 space-y-0.5 text-xs text-muted-foreground">
                {result.errors.map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
