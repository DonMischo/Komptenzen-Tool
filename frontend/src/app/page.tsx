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
        if (data.authenticated) {
          router.replace("/kompetenzen");
        } else {
          router.replace("/public");
        }
      })
      .catch(() => {
        router.replace("/public");
      });
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="animate-pulse text-muted-foreground">Laden…</div>
    </div>
  );
}
