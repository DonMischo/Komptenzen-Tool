"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Plus, Trash2 } from "lucide-react";
import { usersApi } from "@/lib/api";
import { QK } from "@/lib/queries";

interface User {
  id: number;
  username: string;
  role: string;
}

export function UserManagement() {
  const qc = useQueryClient();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("lehrer");

  const { data: users = [], isLoading } = useQuery<User[]>({
    queryKey: QK.users,
    queryFn: () => usersApi.list().then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: () => usersApi.create(username.trim(), password, role),
    onSuccess: () => {
      toast.success(`Benutzer „${username.trim()}" angelegt`);
      setUsername("");
      setPassword("");
      setRole("lehrer");
      qc.invalidateQueries({ queryKey: QK.users });
    },
    onError: (e: any) =>
      toast.error(e?.response?.data?.detail ?? "Fehler beim Anlegen"),
  });

  const deleteMutation = useMutation({
    mutationFn: (u: string) => usersApi.delete(u),
    onSuccess: (_: unknown, u: string) => {
      toast.success(`Benutzer „${u}" gelöscht`);
      qc.invalidateQueries({ queryKey: QK.users });
    },
    onError: (e: any) =>
      toast.error(e?.response?.data?.detail ?? "Fehler beim Löschen"),
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) return;
    createMutation.mutate();
  };

  return (
    <div className="space-y-6">
      {/* Create form */}
      <form onSubmit={handleCreate} className="flex gap-3 items-end flex-wrap">
        <div className="space-y-1">
          <label className="text-sm font-medium">Benutzername</label>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="border rounded-md px-2 py-1.5 text-sm w-44"
            placeholder="lehrer2"
            required
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium">Passwort</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="border rounded-md px-2 py-1.5 text-sm w-44"
            placeholder="••••••"
            required
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium">Rolle</label>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="border rounded-md px-2 py-1.5 text-sm"
          >
            <option value="lehrer">Lehrer</option>
            <option value="admin">Admin</option>
          </select>
        </div>
        <button
          type="submit"
          disabled={createMutation.isPending}
          className="flex items-center gap-2 bg-primary text-white px-4 py-2 rounded-md text-sm hover:bg-primary/90 disabled:opacity-40"
        >
          <Plus className="h-4 w-4" />
          Anlegen
        </button>
      </form>

      {/* User table */}
      {isLoading ? (
        <p className="text-sm text-muted-foreground animate-pulse">Laden…</p>
      ) : users.length === 0 ? (
        <p className="text-sm text-muted-foreground">Keine Benutzer vorhanden.</p>
      ) : (
        <div className="border rounded-xl overflow-hidden">
          <table className="text-sm w-full border-collapse">
            <thead>
              <tr className="bg-muted/50">
                <th className="text-left px-3 py-2 border-b font-medium">Benutzername</th>
                <th className="text-left px-3 py-2 border-b font-medium">Rolle</th>
                <th className="px-3 py-2 border-b" />
              </tr>
            </thead>
            <tbody>
              {users.map((u, ri) => (
                <tr key={u.id} className={ri % 2 === 0 ? "bg-white" : "bg-muted/20"}>
                  <td className="px-3 py-2 border-b font-medium">{u.username}</td>
                  <td className="px-3 py-2 border-b text-muted-foreground">
                    {u.role === "admin" ? "Admin" : "Lehrer"}
                  </td>
                  <td className="px-3 py-2 border-b text-right">
                    <button
                      onClick={() => deleteMutation.mutate(u.username)}
                      disabled={deleteMutation.isPending}
                      className="text-destructive hover:text-destructive/80 disabled:opacity-40"
                      title="Löschen"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
