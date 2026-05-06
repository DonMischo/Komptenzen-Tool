import { useEffect, useRef, useState } from "react";
import { ExportProgressEvent } from "@/types/api";

export function useExportSSE(jobId: string | null) {
  const [events, setEvents] = useState<ExportProgressEvent[]>([]);
  const [isDone, setIsDone] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!jobId) return;

    setEvents([]);
    setIsDone(false);

    const es = new EventSource(`/api/admin/export/stream/${jobId}`);
    esRef.current = es;

    es.onmessage = (e) => {
      const data = JSON.parse(e.data) as ExportProgressEvent;
      setEvents((prev) => [...prev, data]);
      if (data.type === "done") {
        setIsDone(true);
        es.close();
      }
    };

    es.onerror = () => {
      setIsDone(true);
      es.close();
    };

    return () => {
      es.close();
    };
  }, [jobId]);

  const stop = () => {
    esRef.current?.close();
    setIsDone(true);
  };

  return { events, isDone, stop };
}
