"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { authApi } from "@/lib/api";
import { QK } from "@/lib/queries";
import { AuthStatusResponse } from "@/types/api";

export default function LoginPage() {
  const router = useRouter();
  const qc = useQueryClient();

  const { data: status, isLoading } = useQuery<AuthStatusResponse>({
    queryKey: QK.authStatus,
    queryFn: () => authApi.status().then((r) => r.data),
  });

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const loginMutation = useMutation({
    mutationFn: () => authApi.login(username, password),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QK.authStatus });
      router.replace("/kompetenzen");
    },
    onError: () => toast.error("Ungültige Anmeldedaten"),
  });

  const setupMutation = useMutation({
    mutationFn: () => authApi.setup(username, password),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QK.authStatus });
      router.replace("/setup");
    },
    onError: (e: unknown) => {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Fehler beim Anlegen des Kontos";
      toast.error(msg);
    },
  });

  const isSetup = status?.needs_setup ?? false;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) {
      toast.error("Benutzername und Passwort eingeben");
      return;
    }
    if (isSetup) {
      if (password.length < 8) {
        toast.error("Passwort muss mindestens 8 Zeichen lang sein");
        return;
      }
      setupMutation.mutate();
    } else {
      loginMutation.mutate();
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-pulse text-muted-foreground">Laden…</div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-muted/30">
      <div className="w-full max-w-sm bg-white rounded-xl shadow-lg p-8 space-y-6">
        <div className="text-center space-y-1">
          <h1 className="text-2xl font-bold">Kompetenzen-Tool</h1>
          <p className="text-sm text-muted-foreground">
            {isSetup ? "Erstes Admin-Konto anlegen" : "Admin-Login"}
          </p>
        </div>

        {isSetup && (
          <div className="bg-blue-50 border border-blue-200 rounded-md p-3 text-sm text-blue-800">
            Noch kein Admin-Konto vorhanden. Lege jetzt das erste Konto an.
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1">
            <label className="text-sm font-medium">Benutzername</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              autoComplete="username"
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">Passwort</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              autoComplete={isSetup ? "new-password" : "current-password"}
            />
            {isSetup && (
              <p className="text-xs text-muted-foreground">Mindestens 8 Zeichen</p>
            )}
          </div>

          <button
            type="submit"
            disabled={loginMutation.isPending || setupMutation.isPending}
            className="w-full bg-primary text-primary-foreground rounded-md py-2 text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
          >
            {loginMutation.isPending || setupMutation.isPending
              ? "Bitte warten…"
              : isSetup
              ? "Konto anlegen"
              : "Anmelden"}
          </button>
        </form>
      </div>
    </div>
  );
}
