"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { useExportJobs } from "@/hooks/useExportJobs";
import { ExportJobsContext } from "@/contexts/ExportJobsContext";

function ExportJobsProvider({ children }: { children: React.ReactNode }) {
  const { jobs, addJob, cancelJob, dismissJob } = useExportJobs();
  return (
    <ExportJobsContext.Provider value={{ jobs, addJob, cancelJob, dismissJob }}>
      {children}
    </ExportJobsContext.Provider>
  );
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ExportJobsProvider>{children}</ExportJobsProvider>
    </QueryClientProvider>
  );
}
