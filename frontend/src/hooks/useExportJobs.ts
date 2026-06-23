"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ExportProgressEvent } from "@/types/api";
import api from "@/lib/api";

export type ExportJob = {
  id: string;
  label: string;   // e.g. class name
  total: number;
  events: ExportProgressEvent[];
  isDone: boolean;
};

export function useExportJobs() {
  const [jobs, setJobs] = useState<ExportJob[]>([]);
  // Ref keeps closures up-to-date without re-creating the interval
  const jobsRef = useRef<ExportJob[]>([]);

  const _set = useCallback((updater: (prev: ExportJob[]) => ExportJob[]) => {
    setJobs(prev => {
      const next = updater(prev);
      jobsRef.current = next;
      return next;
    });
  }, []);

  const poll = useCallback(async () => {
    const active = jobsRef.current.filter(j => !j.isDone);
    if (!active.length) return;

    const results = await Promise.all(
      active.map(job =>
        api.get(`/admin/export/progress/${job.id}`)
          .then(res => ({ id: job.id, events: res.data.results as ExportProgressEvent[], done: res.data.done as boolean }))
          .catch(() => ({ id: job.id, events: [] as ExportProgressEvent[], done: true }))
      )
    );

    _set(prev => prev.map(job => {
      const r = results.find(r => r.id === job.id);
      if (!r) return job;
      return { ...job, events: r.events, isDone: r.done };
    }));
  }, [_set]);

  // 10-second polling interval; also poll immediately on mount
  useEffect(() => {
    poll();
    const t = setInterval(poll, 10_000);
    return () => clearInterval(t);
  }, [poll]);

  const addJob = useCallback((id: string, label: string, total: number) => {
    _set(prev => [...prev, { id, label, total, events: [], isDone: false }]);
    // Immediate poll so the new card fills in quickly
    setTimeout(poll, 300);
  }, [_set, poll]);

  const cancelJob = useCallback((id: string) => {
    api.post(`/admin/export/cancel/${id}`).catch(() => {});
    _set(prev => prev.map(j => j.id === id ? { ...j, isDone: true } : j));
  }, [_set]);

  const dismissJob = useCallback((id: string) => {
    _set(prev => prev.filter(j => j.id !== id));
  }, [_set]);

  return { jobs, addJob, cancelJob, dismissJob };
}
