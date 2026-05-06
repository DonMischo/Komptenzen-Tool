"use client";

import { useRouter, usePathname } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { authApi } from "@/lib/api";
import { QK } from "@/lib/queries";
import { cn } from "@/lib/utils";
import {
  Settings,
  CheckSquare,
  Users,
  ClipboardList,
  ShieldCheck,
  LogOut,
} from "lucide-react";

const NAV = [
  { href: "/setup",         label: "Setup",         icon: Settings },
  { href: "/kompetenzen",   label: "Kompetenzen",   icon: CheckSquare },
  { href: "/schuelerdaten", label: "Schülerdaten",  icon: Users },
  { href: "/stammdaten",    label: "Stammdaten",    icon: ClipboardList },
  { href: "/admin",         label: "Admin",         icon: ShieldCheck },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const qc = useQueryClient();

  const logout = useMutation({
    mutationFn: () => authApi.logout(),
    onSuccess: () => {
      qc.clear();
      router.replace("/login");
    },
  });

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-56 bg-slate-900 text-slate-100 flex flex-col shrink-0">
        <div className="px-4 py-5 border-b border-slate-700">
          <h1 className="font-bold text-base leading-tight">Kompetenzen-Tool</h1>
        </div>

        <nav className="flex-1 py-4 space-y-1 px-2">
          {NAV.map(({ href, label, icon: Icon }) => (
            <button
              key={href}
              onClick={() => router.push(href)}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors text-left",
                pathname === href
                  ? "bg-slate-700 text-white"
                  : "text-slate-300 hover:bg-slate-800 hover:text-white"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </button>
          ))}
        </nav>

        <div className="px-2 pb-4 border-t border-slate-700 pt-4">
          <button
            onClick={() => logout.mutate()}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <LogOut className="h-4 w-4" />
            Abmelden
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto bg-muted/20">
        <div className="max-w-6xl mx-auto p-6">{children}</div>
      </main>
    </div>
  );
}
