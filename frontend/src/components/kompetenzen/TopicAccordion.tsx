"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { competenceApi } from "@/lib/api";
import { TopicGroup } from "@/types/api";
import { ChevronDown, ChevronRight, PlusCircle, Trash2, ToggleLeft, ToggleRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  topic: TopicGroup;
  className: string;
  pendingChanges: Map<number, boolean>;
  onToggle: (compId: number, value: boolean) => void;
  onRefresh: () => void;
}

export function TopicAccordion({ topic, className, pendingChanges, onToggle, onRefresh }: Props) {
  const [open, setOpen] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newText, setNewText] = useState("");

  const addMutation = useMutation({
    mutationFn: () => competenceApi.addCustom(className, topic.topic_id, newText),
    onSuccess: () => {
      setNewText("");
      setShowAddForm(false);
      onRefresh();
      toast.success("Ergänzung hinzugefügt");
    },
    onError: () => toast.error("Fehler beim Hinzufügen"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => competenceApi.deleteCustom(id),
    onSuccess: () => {
      onRefresh();
      toast.success("Ergänzung gelöscht");
    },
    onError: () => toast.error("Fehler beim Löschen"),
  });

  const toggleAllMutation = useMutation({
    mutationFn: (value: boolean) =>
      competenceApi.toggleTopic(className, topic.topic_id, value),
    onSuccess: (_, value) => {
      topic.competences.forEach((c) => onToggle(c.competence_id, value));
      onRefresh();
    },
    onError: () => toast.error("Fehler"),
  });

  const allSelected = topic.competences.every((c) => {
    const pending = pendingChanges.get(c.competence_id);
    return pending !== undefined ? pending : c.selected;
  });

  return (
    <div className="border rounded-xl overflow-hidden">
      {/* Header */}
      <button
        className="w-full flex items-center gap-2 px-4 py-3 bg-muted/40 hover:bg-muted/60 text-left transition-colors"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
        )}
        <span className="font-medium text-sm flex-1">{topic.topic_name}</span>
        <span className="text-xs text-muted-foreground">
          {topic.competences.filter((c) => {
            const p = pendingChanges.get(c.competence_id);
            return p !== undefined ? p : c.selected;
          }).length}{" "}
          / {topic.competences.length}
        </span>
        <div className="flex gap-2 ml-2" onClick={(e) => e.stopPropagation()}>
          <button
            title={allSelected ? "Alle abwählen" : "Alle auswählen"}
            onClick={() => toggleAllMutation.mutate(!allSelected)}
            className="text-muted-foreground hover:text-foreground"
          >
            {allSelected ? (
              <ToggleRight className="h-4 w-4" />
            ) : (
              <ToggleLeft className="h-4 w-4" />
            )}
          </button>
        </div>
      </button>

      {/* Content */}
      {open && (
        <div className="px-4 py-3 space-y-2">
          {topic.competences.map((comp) => {
            const isSelected =
              pendingChanges.get(comp.competence_id) ?? comp.selected;
            return (
              <label
                key={comp.competence_id}
                className="flex items-start gap-3 cursor-pointer group"
              >
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={(e) => onToggle(comp.competence_id, e.target.checked)}
                  className="mt-0.5 h-4 w-4 rounded border-gray-300"
                />
                <span
                  className={cn(
                    "text-sm leading-relaxed",
                    !isSelected && "text-muted-foreground"
                  )}
                >
                  {comp.text}
                </span>
              </label>
            );
          })}

          {/* Custom competences */}
          {topic.custom_competences.length > 0 && (
            <div className="pt-2 border-t space-y-1.5">
              <p className="text-xs font-medium text-muted-foreground">Eigene Ergänzungen</p>
              {topic.custom_competences.map((cc) => (
                <div key={cc.id} className="flex items-start gap-2">
                  <span className="flex-1 text-sm text-muted-foreground">{cc.text}</span>
                  <button
                    onClick={() => deleteMutation.mutate(cc.id)}
                    className="text-muted-foreground hover:text-red-600 shrink-0"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Add custom */}
          {showAddForm ? (
            <div className="flex gap-2 pt-2 border-t">
              <input
                type="text"
                value={newText}
                onChange={(e) => setNewText(e.target.value)}
                placeholder="Neue Ergänzung…"
                className="flex-1 border rounded px-2 py-1 text-sm"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && newText.trim()) addMutation.mutate();
                  if (e.key === "Escape") setShowAddForm(false);
                }}
                autoFocus
              />
              <button
                onClick={() => addMutation.mutate()}
                disabled={!newText.trim() || addMutation.isPending}
                className="bg-primary text-white text-xs px-2 py-1 rounded hover:bg-primary/90 disabled:opacity-50"
              >
                Hinzufügen
              </button>
              <button
                onClick={() => setShowAddForm(false)}
                className="text-xs text-muted-foreground"
              >
                Abbrechen
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowAddForm(true)}
              className="flex items-center gap-1.5 text-xs text-blue-600 hover:underline pt-1"
            >
              <PlusCircle className="h-3.5 w-3.5" /> Ergänzen
            </button>
          )}
        </div>
      )}
    </div>
  );
}
