"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { setupApi } from "@/lib/api";
import { QK } from "@/lib/queries";
import { DatabaseListResponse } from "@/types/api";
import { PlusCircle, Trash2, Check } from "lucide-react";

export function DatabasePanel() {
  const qc = useQueryClient();
  const [newName, setNewName] = useState("");
  const [term, setTerm] = useState<"hj" | "ej">("hj");
  const [showCreate, setShowCreate] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const { data, isLoading } = useQuery<DatabaseListResponse>({
    queryKey: QK.databases,
    queryFn: () => setupApi.listDatabases().then((r) => r.data),
  });

  const { data: suggest } = useQuery({
    queryKey: ["suggest", term],
    queryFn: () => setupApi.suggestDatabase(term).then((r) => r.data),
  });

  const activeDb = typeof window !== "undefined" ? localStorage.getItem("activeDb") ?? "" : "";

  const selectMutation = useMutation({
    mutationFn: (name: string) => setupApi.selectDatabase(name),
    onSuccess: (_, name) => {
      localStorage.setItem("activeDb", name);
      qc.invalidateQueries();
      toast.success(`Datenbank ${name} ausgewählt`);
    },
    onError: () => toast.error("Fehler beim Auswählen der Datenbank"),
  });

  const createMutation = useMutation({
    mutationFn: (name: string) => setupApi.createDatabase(name),
    onSuccess: (_, name) => {
      localStorage.setItem("activeDb", name);
      qc.invalidateQueries();
      setShowCreate(false);
      setNewName("");
      toast.success(`Datenbank ${name} erstellt`);
    },
    onError: (e: unknown) => {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Fehler";
      toast.error(msg);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (name: string) => setupApi.deleteDatabase(name),
    onSuccess: (_, name) => {
      if (localStorage.getItem("activeDb") === name) localStorage.removeItem("activeDb");
      qc.invalidateQueries();
      setConfirmDelete(null);
      toast.success(`Datenbank ${name} gelöscht`);
    },
    onError: () => toast.error("Löschen fehlgeschlagen"),
  });

  const databases: string[] = data?.databases ?? [];

  return (
    <div className="bg-white rounded-xl border p-5 space-y-4">
      <h3 className="font-semibold text-lg">Datenbanken</h3>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Laden…</p>
      ) : databases.length === 0 ? (
        <p className="text-sm text-muted-foreground">Keine Report-Datenbanken vorhanden.</p>
      ) : (
        <ul className="space-y-2">
          {databases.map((db) => (
            <li key={db} className="flex items-center gap-3 border rounded-md px-3 py-2">
              <span className="flex-1 text-sm font-mono">{db}</span>
              {db === activeDb && (
                <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full flex items-center gap-1">
                  <Check className="h-3 w-3" /> Aktiv
                </span>
              )}
              {db !== activeDb && (
                <button
                  onClick={() => selectMutation.mutate(db)}
                  className="text-xs text-blue-600 hover:underline"
                >
                  Auswählen
                </button>
              )}
              {confirmDelete === db ? (
                <div className="flex gap-2 text-xs">
                  <button onClick={() => deleteMutation.mutate(db)} className="text-red-600 font-medium">Ja, löschen</button>
                  <button onClick={() => setConfirmDelete(null)} className="text-muted-foreground">Abbrechen</button>
                </div>
              ) : (
                <button onClick={() => setConfirmDelete(db)} className="text-muted-foreground hover:text-red-600">
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {/* Create new */}
      {showCreate ? (
        <div className="border rounded-md p-3 space-y-3 bg-muted/30">
          <div className="flex gap-2">
            <select
              value={term}
              onChange={(e) => {
                setTerm(e.target.value as "hj" | "ej");
                setNewName("");
              }}
              className="border rounded px-2 py-1 text-sm"
            >
              <option value="hj">Halbjahr (hj)</option>
              <option value="ej">Endjahr (ej)</option>
            </select>
            <input
              type="text"
              value={newName || suggest?.suggested || ""}
              onChange={(e) => setNewName(e.target.value)}
              placeholder={suggest?.suggested}
              className="flex-1 border rounded px-2 py-1 text-sm font-mono"
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => createMutation.mutate(newName || suggest?.suggested || "")}
              disabled={createMutation.isPending}
              className="bg-primary text-white text-sm px-3 py-1.5 rounded-md hover:bg-primary/90 disabled:opacity-50"
            >
              Erstellen
            </button>
            <button onClick={() => setShowCreate(false)} className="text-sm text-muted-foreground hover:text-foreground">
              Abbrechen
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 text-sm text-blue-600 hover:underline"
        >
          <PlusCircle className="h-4 w-4" /> Neue Datenbank anlegen
        </button>
      )}
    </div>
  );
}
