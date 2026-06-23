import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useExportJobs } from "./useExportJobs";

vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import api from "@/lib/api";
const mockGet = vi.mocked(api.get);
const mockPost = vi.mocked(api.post);

function progressResponse(done: boolean, count: number) {
  return {
    data: {
      done,
      results: Array.from({ length: count }, (_, i) => ({
        type: "progress",
        success: true,
        basename: `student_${i}`,
      })),
    },
  };
}

// Advance time enough for addJob's setTimeout(poll, 300) to fire, but not
// enough for the 10s interval to also fire (avoids infinite-loop trap).
const AFTER_ADD = 400;

describe("useExportJobs", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockGet.mockResolvedValue(progressResponse(false, 0));
    mockPost.mockResolvedValue({});
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it("starts with no jobs", () => {
    const { result } = renderHook(() => useExportJobs());
    expect(result.current.jobs).toHaveLength(0);
  });

  it("addJob adds a job with correct id, label, total", async () => {
    const { result } = renderHook(() => useExportJobs());

    await act(async () => {
      result.current.addJob("job-1", "7ef", 12);
      await vi.advanceTimersByTimeAsync(AFTER_ADD);
    });

    expect(result.current.jobs).toHaveLength(1);
    const job = result.current.jobs[0];
    expect(job.id).toBe("job-1");
    expect(job.label).toBe("7ef");
    expect(job.total).toBe(12);
  });

  it("new job starts as not done", async () => {
    const { result } = renderHook(() => useExportJobs());

    await act(async () => {
      result.current.addJob("job-1", "7ef", 5);
      await vi.advanceTimersByTimeAsync(AFTER_ADD);
    });

    expect(result.current.jobs[0].isDone).toBe(false);
  });

  it("poll marks job done when server returns done:true", async () => {
    mockGet.mockResolvedValue(progressResponse(true, 3));

    const { result } = renderHook(() => useExportJobs());

    await act(async () => {
      result.current.addJob("job-abc", "6a", 3);
      await vi.advanceTimersByTimeAsync(AFTER_ADD);
    });

    const job = result.current.jobs[0];
    expect(job.isDone).toBe(true);
    expect(job.events).toHaveLength(3);
  });

  it("poll updates events from server response", async () => {
    mockGet.mockResolvedValue(progressResponse(false, 2));

    const { result } = renderHook(() => useExportJobs());

    await act(async () => {
      result.current.addJob("j", "5a", 10);
      await vi.advanceTimersByTimeAsync(AFTER_ADD);
    });

    expect(result.current.jobs[0].events).toHaveLength(2);
  });

  it("dismissJob removes the job from the list", async () => {
    const { result } = renderHook(() => useExportJobs());

    await act(async () => {
      result.current.addJob("job-x", "5b", 2);
      await vi.advanceTimersByTimeAsync(AFTER_ADD);
    });

    act(() => result.current.dismissJob("job-x"));

    expect(result.current.jobs).toHaveLength(0);
  });

  it("cancelJob marks job done immediately", async () => {
    const { result } = renderHook(() => useExportJobs());

    await act(async () => {
      result.current.addJob("job-y", "8c", 10);
      await vi.advanceTimersByTimeAsync(AFTER_ADD);
    });

    act(() => result.current.cancelJob("job-y"));

    expect(result.current.jobs[0].isDone).toBe(true);
  });

  it("cancelJob calls the cancel API endpoint", async () => {
    const { result } = renderHook(() => useExportJobs());

    await act(async () => {
      result.current.addJob("job-y", "8c", 10);
      await vi.advanceTimersByTimeAsync(AFTER_ADD);
    });

    act(() => result.current.cancelJob("job-y"));

    expect(mockPost).toHaveBeenCalledWith("/admin/export/cancel/job-y");
  });

  it("multiple jobs can be tracked simultaneously", async () => {
    const { result } = renderHook(() => useExportJobs());

    await act(async () => {
      result.current.addJob("j1", "7ef", 5);
      result.current.addJob("j2", "6a", 3);
      await vi.advanceTimersByTimeAsync(AFTER_ADD);
    });

    expect(result.current.jobs).toHaveLength(2);
    expect(result.current.jobs.map((j) => j.id)).toEqual(["j1", "j2"]);
  });

  it("done jobs are not polled on the 10s interval", async () => {
    const { result } = renderHook(() => useExportJobs());

    await act(async () => {
      result.current.addJob("done-job", "7ef", 1);
      await vi.advanceTimersByTimeAsync(AFTER_ADD);
    });

    act(() => result.current.cancelJob("done-job"));

    const callsBefore = mockGet.mock.calls.length;

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });

    // No new GET calls — the only job is done
    expect(mockGet.mock.calls.length).toBe(callsBefore);
  });

  it("active jobs are polled again after 10 seconds", async () => {
    const { result } = renderHook(() => useExportJobs());

    await act(async () => {
      result.current.addJob("j", "5a", 5);
      await vi.advanceTimersByTimeAsync(AFTER_ADD);
    });

    const callsAfterAdd = mockGet.mock.calls.length;

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });

    expect(mockGet.mock.calls.length).toBeGreaterThan(callsAfterAdd);
  });
});
