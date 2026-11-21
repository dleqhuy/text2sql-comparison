import { record, type Step } from "./flow-model.ts"

export function refinerOutcome(step: Step) {
  if (step.status === "running") return "pending"
  if (step.status === "error" || step.status === "interrupted") return "failed"
  const output = record(step.output)
  if (output?.send_to === "Refiner") return "repair"
  const check = step.checks?.[step.checks.length - 1]
  const result = record(check?.output)
  const sql = output?.pred ?? output?.final_sql
  const tested = record(check?.input)?.sql
  if (
    output?.execution_verified === true ||
    (output?.execution_verified !== false &&
      check?.status === "done" &&
      Array.isArray(result?.data) &&
      !result?.sqlite_error &&
      typeof sql === "string" &&
      typeof tested === "string" &&
      sql.trim() === tested.trim())
  )
    return "success"
  if (result?.sqlite_error || check?.status === "error")
    return "execution-error"
  return "unverified"
}

export function resolveStepDetail(
  parent: Step | undefined,
  detailId: string | null,
) {
  return (
    [...(parent?.checks ?? []), ...(parent?.calls ?? [])].find(
      (s) => s.id === detailId,
    ) ?? parent
  )
}
