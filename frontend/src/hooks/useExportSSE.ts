import { useCallback, useEffect, useRef, useState } from "react";
import { ExportProgressEvent } from "@/types/api";
import api from "@/lib/api";

export function useExportSSE(jobId: string | null) {
  const [events, setEvents] = useState<ExportProgressEvent[]>([]);
  const [isDone, setIsDone] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stop = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
    if (jobId) api.post(`/admin/export/cancel/${jobId}`).catch(() => {});
    setIsDone(true);
  }, [jobId]);

  useEffect(() => {
    if (!jobId) {
      setEvents([]);
      setIsDone(false);
      return;
    }

    setEvents([]);
    setIsDone(false);

    timerRef.current = setInterval(async () => {
      try {
        const res = await api.get(`/admin/export/progress/${jobId}`);
        const { done, results } = res.data;
        setEvents(results);
        if (done) {
          if (timerRef.current) clearInterval(timerRef.current);
          timerRef.current = null;
          setIsDone(true);
        }
      } catch {
        if (timerRef.current) clearInterval(timerRef.current);
        timerRef.current = null;
        setIsDone(true);
      }
    }, 800);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = null;
    };
  }, [jobId]);

  return { events, isDone, stop };
}
