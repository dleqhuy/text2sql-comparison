import type { RunSnapshot } from "@/client"

/** Local SSE snapshots with reconnect, independent of browser sessions. */
export async function watchRun(
  id: string,
  signal: AbortSignal,
  onSnapshot: (snapshot: RunSnapshot) => void,
  onDisconnect: () => void,
) {
  while (!signal.aborted) {
    try {
      const response = await fetch(`/api/v1/live/runs/${id}/events`, {
        signal,
      })
      if (!response.ok || !response.body)
        throw new Error(`Stream HTTP ${response.status}`)
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""
      try {
        while (!signal.aborted) {
          const { value, done } = await reader.read()
          if (done) break
          buffer += decoder
            .decode(value, { stream: true })
            .replace(/\r\n/g, "\n")
          let end: number
          while ((end = buffer.indexOf("\n\n")) >= 0) {
            const frame = buffer.slice(0, end)
            buffer = buffer.slice(end + 2)
            const data = frame
              .split("\n")
              .filter((line) => line.startsWith("data:"))
              .map((line) => line.slice(5).trimStart())
              .join("\n")
            if (!data) continue
            const snapshot = JSON.parse(data) as RunSnapshot
            onSnapshot(snapshot)
            if (snapshot.meta.status !== "running") return
          }
        }
      } finally {
        await reader.cancel().catch(() => {})
      }
    } catch {
      if (signal.aborted) return
    }
    if (signal.aborted) return
    onDisconnect()
    await new Promise<void>((resolve) => {
      const timer = setTimeout(() => {
        signal.removeEventListener("abort", abort)
        resolve()
      }, 1200)
      const abort = () => {
        clearTimeout(timer)
        resolve()
      }
      signal.addEventListener("abort", abort, { once: true })
    })
  }
}
