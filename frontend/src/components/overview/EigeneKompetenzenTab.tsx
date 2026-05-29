"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Pencil, Trash2, Check, X } from "lucide-react";
import { overviewApi } from "@/lib/api";
import { QK } from "@/lib/queries";
import { CustomCompetenceGroup } from "@/types/api";

interface Props {
  classNameValue: string;
}

function EditableItem({
  id,
  text,
  onSave,
  onDelete,
}: {
  id: number;
  text: string;
  onSave: (id: number, text: string) => void;
  onDelete: (id: number) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(text);

  if (!editing) {
    return (
      <li className="flex items-start gap-2 py-1">
        <span className="flex-1 text-sm">{text}</span>
        <button
          onClick={() => { setDraft(text); setEditing(true); }}
          className="text-slate-400 hover:text-blue-600 shrink-0"
          title="Bearbeiten"
        >
          <Pencil className="h-3.5 w-3.5" />
        </button>
        <button
          onClick={() => onDelete(id)}
          className="text-slate-400 hover:text-red-500 shrink-0"
          title="Löschen"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </li>
    );
  }

  return (
    <li className="flex items-start gap-2 py-1">
      <textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        rows={2}
        className="flex-1 text-sm border rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-primary resize-none"
      />
      <button
        onClick={() => { onSave(id, draft); setEditing(false); }}
        disabled={!draft.trim()}
        className="text-green-600 hover:text-green-700 shrink-0 disabled:opacity-40"
        title="Speichern"
      >
        <Check className="h-4 w-4" />
      </button>
      <button
        onClick={() => setEditing(false)}
        className="text-slate-400 hover:text-slate-600 shrink-0"
        title="Abbrechen"
      >
        <X className="h-4 w-4" />
      </button>
    </li>
  );
}

export function EigeneKompetenzenTab({ classNameValue }: Props) {
  const qc = useQueryClient();

  const { data, isLoading } = useQuery<CustomCompetenceGroup[]>({
    queryKey: QK.overviewCustom(classNameValue),
    queryFn: () => overviewApi.customCompetences(classNameValue).then((r) => r.data),
    enabled: !!classNameValue,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, text }: { id: number; text: string }) =>
      overviewApi.updateCustom(id, text),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QK.overviewCustom(classNameValue) });
      toast.success("Gespeichert");
    },
    onError: () => toast.error("Fehler beim Speichern"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => overviewApi.deleteCustom(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QK.overviewCustom(classNameValue) });
      toast.success("Gelöscht");
    },
    onError: () => toast.error("Fehler beim Löschen"),
  });

  if (isLoading) return <p className="text-sm text-muted-foreground animate-pulse">Laden…</p>;

  if (!data || data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Keine eigenen Kompetenzen für diese Klasse vorhanden.
      </p>
    );
  }

  // Group by subject
  const bySubject: Record<string, CustomCompetenceGroup[]> = {};
  for (const g of data) {
    if (!bySubject[g.subject]) bySubject[g.subject] = [];
    bySubject[g.subject].push(g);
  }

  return (
    <div className="space-y-6">
      {Object.entries(bySubject).map(([subject, groups]) => (
        <div key={subject}>
          <h3 className="font-semibold text-sm mb-2 text-slate-700">{subject}</h3>
          <div className="space-y-3 pl-3 border-l-2 border-muted">
            {groups.map((g) => (
              <div key={g.topic_id}>
                <p className="text-xs text-muted-foreground mb-1">{g.topic_name}</p>
                <ul className="space-y-0.5">
                  {g.customs.map((cc) => (
                    <EditableItem
                      key={cc.id}
                      id={cc.id}
                      text={cc.text}
                      onSave={(id, text) => updateMutation.mutate({ id, text })}
                      onDelete={(id) => deleteMutation.mutate(id)}
                    />
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
