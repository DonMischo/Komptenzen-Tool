// Streaming proxy for SSE — Next.js rewrites buffer responses, so we
// proxy the backend SSE stream here using a proper streaming Response.
export const dynamic = "force-dynamic";

export async function GET(
  request: Request,
  { params }: { params: { job_id: string } }
) {
  const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";

  const upstream = await fetch(
    `${backendUrl}/api/admin/export/stream/${params.job_id}`,
    { headers: { Accept: "text/event-stream" } }
  );

  if (!upstream.ok || !upstream.body) {
    return new Response("Stream not found", { status: upstream.status });
  }

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
      Connection: "keep-alive",
    },
  });
}
