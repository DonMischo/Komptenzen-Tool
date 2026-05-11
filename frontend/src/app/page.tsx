"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    authApi
      .me()
      .then((res) => {
        const data = res.data;
        if (!data.authenticated) {
          router.replace("/login");
        } else if (data.role === "admin") {
          router.replace("/setup");
        } else {
          router.replace("/kompetenzen");
        }
      })
      .catch(() => {
        router.replace("/login");
      });
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="animate-pulse text-muted-foreground">Laden…</div>
    </div>
  );
}
