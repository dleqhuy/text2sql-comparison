import { record, type Step } from "./flow-model.ts"

/** Keep each tool associated with its own visible agent session, including retries. */
export function codexContext(step: Step, steps: Step[]) {
  const sessions = steps.filter(
    (s) => s.id.startsWith("codex_mcp-") && s.stage === "Codex turn",
  )
  const session =
    step.stage === "Codex turn"
      ? step
      : [...sessions].reverse().find((s) => s.time <= step.time)
  const next = sessions.find((s) => s.time > (session?.time ?? step.time))
  const tools = steps.filter(
    (s) =>
      s.id.startsWith("codex_mcp-") &&
      ["search_objects", "execute_sql"].includes(s.stage) &&
      s.time >= (session?.time ?? -Infinity) &&
      s.time < (next?.time ?? Infinity),
  )
  const request = record(session?.input)
  let prompt = request?.prompt
  if (typeof prompt === "string") {
    try {
      prompt = JSON.parse(prompt)
    } catch {
      /* Preserve a plain user prompt. */
    }
  }
  const output = record(session?.output)
  let finalResponse = output?.final_response
  if (typeof finalResponse === "string") {
    try {
      finalResponse = JSON.parse(finalResponse)
    } catch {
      /* Keep the public response visible. */
    }
  }
  return {
    request,
    prompt,
    output,
    finalResponse,
    runtime: record(request?.runtime),
    returnedSql: record(finalResponse)?.sql,
    tools,
    callNumber: tools.findIndex((s) => s.id === step.id) + 1,
  }
}
