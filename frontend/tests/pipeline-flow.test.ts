import assert from "node:assert/strict"
import { test } from "node:test"
import {
  buildSteps,
  evaluationNodeTitle,
  evaluationFrameTitle,
  classification,
  methodContext,
  stepDetails,
  type Method,
} from "../src/features/pipeline/flow-model.ts"
import { createFlow } from "../src/features/pipeline/flow-graph.ts"
import { codexContext } from "../src/features/pipeline/codex-model.ts"
import {
  refinerOutcome,
  resolveStepDetail,
} from "../src/features/pipeline/mac-model.ts"

type E = Parameters<typeof buildSteps>[0][number]
const event = (
  stage: string,
  kind: string,
  time: number,
  data: Partial<E> = {},
): E => ({ method: "dail_sql", stage, kind, time, ...data })

const macEvent = (
  stage: string,
  kind: string,
  time: number,
  data: Partial<E> = {},
) => event(stage, kind, time, { ...data, method: "mac_sql" })

test("all four methods place EX nodes in a separate supplemental evaluation frame", () => {
  for (const method of [
    "din_sql",
    "dail_sql",
    "mac_sql",
    "codex_mcp",
  ] as Method[])
    for (const kind of [undefined, "start", "finish", "error"]) {
      const steps = kind
        ? buildSteps([
            event("SQLite execution", kind, 1, {
              method,
              input: { sql: "SELECT 1", gold_sql: "SELECT 1" },
            }),
          ])
        : []
      const graph = createFlow(method, steps)
      const evaluation = graph.nodes.find(
        (n) => n.type === "task" && n.data.stage === "SQLite execution",
      )!
      assert.equal(evaluation.data.title, evaluationNodeTitle)
      const frame = graph.nodes.find((n) => n.id === evaluation.parentId)!
      assert.equal(frame.type, "session")
      assert.equal(frame.data.title, evaluationFrameTitle)
      assert.equal(frame.data.supplemental, true)
      assert.ok(
        !graph.nodes
          .filter((n) => n.parentId === frame.id)
          .some(
            (n) => n.type === "task" && n.data.stage !== "SQLite execution",
          ),
      )
      if (kind) assert.equal(evaluation.id, steps[0].id)
    }
})

test("all methods place every label outside task cards and other labels, including Refiner loops", () => {
  for (const method of [
    "din_sql",
    "dail_sql",
    "codex_mcp",
    "mac_sql",
  ] as Method[]) {
    let time = 0
    const e = (stage: string, kind: string = "finish", data: Partial<E> = {}) =>
      event(stage, kind, ++time, { ...data, method })
    const events = [e("Input")]
    if (method === "codex_mcp") {
      events.push(e("Codex turn", "start"))
      for (let i = 0; i < 20; i++)
        events.push(
          e(
            i % 2 ? "execute_sql" : "search_objects",
            i % 5 === 0 ? "error" : "tool",
            { output: i % 5 === 0 ? "retry error" : {} },
          ),
        )
      events.push(
        e("Codex turn", "finish", {
          output: { audit_verified: true, sql: "SELECT 1" },
        }),
      )
    } else if (method === "mac_sql") {
      events.push(e("Selector · state"), e("Decomposer · state"))
      for (let round = 0; round < 3; round++) {
        events.push(
          e("Refiner · state", "start"),
          e("Refiner · execution", "start", {
            input: { sql: `SELECT ${round}` },
          }),
          e("Refiner · execution", "finish", {
            output:
              round < 2
                ? { sqlite_error: "missing column" }
                : { data: [[2]], sqlite_error: "" },
          }),
        )
        if (round < 2)
          events.push(
            e("Refiner", "start", { input: "repair prompt" }),
            e("Refiner", "finish", { output: `SELECT ${round + 1}` }),
          )
        events.push(
          e("Refiner · state", "finish", {
            output: {
              pred: `SELECT ${round < 2 ? round + 1 : round}`,
              send_to: round < 2 ? "Refiner" : "System",
              execution_verified: round === 2,
            },
          }),
        )
      }
    } else
      for (const stage of method === "din_sql"
        ? [
            "Schema linking",
            "Classification",
            "SQL generation",
            "Self-correction",
          ]
        : [
            "Preprocessing",
            "Example selection · pass 1",
            "SQL generation · pass 1",
            "Example selection · pass 2",
            "SQL generation · pass 2",
          ])
        events.push(
          e(stage, "finish", {
            output: stage === "Classification" ? { label: "EASY" } : "SELECT 1",
          }),
        )
    events.push(e("SQLite execution"))
    const graph = createFlow(method, buildSteps(events, true))
    const rect = (
      id: string,
    ): { x: number; y: number; width: number; height: number } => {
      const node = graph.nodes.find((n) => n.id === id)!
      const parent = node.parentId ? rect(node.parentId) : { x: 0, y: 0 }
      return {
        x: parent.x + node.position.x,
        y: parent.y + node.position.y,
        width: node.width!,
        height: node.height!,
      }
    }
    const overlap = (a: ReturnType<typeof rect>, b: ReturnType<typeof rect>) =>
      a.x < b.x + b.width &&
      a.x + a.width > b.x &&
      a.y < b.y + b.height &&
      a.y + a.height > b.y
    const labels: ReturnType<typeof rect>[] = []
    for (const edge of graph.edges.filter((e) => e.label)) {
      assert.equal(edge.type, "positionedLabel", `${method}: ${edge.label}`)
      const label = edge.data?.labelPosition as ReturnType<typeof rect>
      assert.ok(label)
      for (const card of graph.nodes.filter((n) => n.type === "task"))
        assert.ok(
          !overlap(label, rect(card.id)),
          `${method}: ${edge.label} overlaps ${card.id}`,
        )
      for (const previous of labels)
        assert.ok(!overlap(label, previous), `${method}: overlapping labels`)
      labels.push(label)
    }
  }
})

test("DIN provider retries stay in one logical stage and only recorded retries create a loop", () => {
  const din = (
    stage: string,
    kind: string,
    time: number,
    data: Partial<E> = {},
  ) => event(stage, kind, time, { ...data, method: "din_sql" })
  const events = [
    din("SQL generation", "start", 1, {
      input: { prompt: "same prompt", branch: "EASY" },
    }),
    din("SQL generation", "error", 2, { output: "provider unavailable" }),
    din("SQL generation", "start", 3, {
      input: { prompt: "same prompt", branch: "EASY" },
    }),
    din("SQL generation", "finish", 4, {
      output: { response: "SELECT 1", sql: "SELECT 1" },
    }),
    din("Self-correction", "start", 5, { input: { prompt: "check once" } }),
    din("Self-correction", "finish", 6, {
      output: { response: "SELECT 1", sql: "SELECT 1" },
    }),
    din("SQLite execution", "error", 7, { output: "SQLite failure" }),
  ]
  for (let prefix = 1; prefix <= 4; prefix++) {
    const steps = buildSteps(events.slice(0, prefix))
    assert.equal(steps.length, 1)
    assert.equal(steps[0].id, "din_sql-0")
    const loops = createFlow("din_sql", steps).edges.filter(
      (e) => e.data?.kind === "provider-retry",
    )
    assert.equal(loops.length, prefix >= 3 ? 1 : 0)
  }
  const steps = buildSteps(events, true)
  assert.equal(steps.length, 3)
  assert.equal(steps[0].calls?.length, 2)
  assert.equal(steps[0].calls?.[0].output, "provider unavailable")
  assert.equal(steps[0].status, "done")
  assert.equal(stepDetails(steps[0], steps).sql, "SELECT 1")
  const graph = createFlow("din_sql", steps)
  assert.ok(!graph.edges.some((e) => e.source === steps[2].id))
  assert.equal(
    graph.edges.filter((e) => e.data?.kind === "provider-retry")[0].target,
    steps[0].id,
  )
})

test("DIN calls with different prompts are not misrepresented as API retries", () => {
  const steps = buildSteps([
    event("SQL generation", "error", 1, {
      method: "din_sql",
      input: { prompt: "one" },
      output: "failed",
    }),
    event("SQL generation", "start", 2, {
      method: "din_sql",
      input: { prompt: "different" },
    }),
  ])
  assert.equal(steps.length, 2)
  assert.ok(
    !createFlow("din_sql", steps).edges.some(
      (e) => e.data?.kind === "provider-retry",
    ),
  )
})

test("DAIL two-pass dependency is forward data flow; only provider retries have loop edges", () => {
  const steps = buildSteps(
    [
      event("SQL generation · pass 1", "start", 1),
      event("LLM response · pass 1", "start", 2, {
        input: { prompt: "first prompt" },
      }),
      event("LLM response · pass 1", "error", 3, { output: "timeout" }),
      event("LLM response · pass 1", "start", 4, {
        input: { prompt: "first prompt" },
      }),
      event("LLM response · pass 1", "finish", 5, {
        output: { response: ["SELECT 1"] },
      }),
      event("SQL generation · pass 1", "finish", 6, { output: "SELECT 1" }),
      event("Example selection · pass 2", "finish", 7, {
        output: { examples: [], prompt: "second prompt" },
      }),
      event("SQL generation · pass 2", "finish", 8, { output: "SELECT 2" }),
      event("SQLite execution", "error", 9, { output: "SQLite failed" }),
    ],
    true,
  )
  const graph = createFlow("dail_sql", steps)
  const dependency = graph.edges.find(
    (e) => e.source === steps[0].id && e.target === steps[1].id,
  )!
  assert.equal(dependency.data?.kind, "data-dependency")
  assert.ok(String(dependency.label).includes("SQL sơ bộ"))
  assert.equal(
    graph.edges.filter((e) => e.data?.kind === "provider-retry").length,
    1,
  )
  assert.ok(!graph.edges.some((e) => e.source === steps[3].id))
  assert.equal(steps[0].calls?.[0].output, "timeout")
})

test("MAC evaluation success edges require a successful execution of the exact returned SQL", () => {
  for (const [result, sql, outcome] of [
    [{ data: [], sqlite_error: "" }, "SELECT 1", "success"],
    [{ data: [[1]], sqlite_error: "" }, "SELECT 2", "unverified"],
    [{ sqlite_error: "no such column" }, "SELECT 1", "execution-error"],
  ] as const) {
    const steps = buildSteps(
      [
        macEvent("Refiner · state", "start", 1),
        macEvent("Refiner · execution", "start", 2, {
          input: { sql: "SELECT 1" },
        }),
        macEvent("Refiner · execution", "finish", 3, { output: result }),
        macEvent("Refiner · state", "finish", 4, {
          output: { pred: sql, send_to: "System" },
        }),
        macEvent("SQLite execution", "finish", 5),
      ],
      true,
    )
    assert.equal(refinerOutcome(steps[0]), outcome)
    const graph = createFlow("mac_sql", steps)
    assert.equal(
      graph.edges.some((e) => e.data?.kind === "success"),
      outcome === "success",
    )
    const evaluation = graph.nodes.find((n) => n.id === steps[1].id)!
    assert.equal(
      graph.nodes.find((n) => n.id === evaluation.parentId)?.data.supplemental,
      true,
    )
  }
})

test("MAC last repair without a rerun remains a planned loop and never a success exit", () => {
  const steps = buildSteps(
    [
      macEvent("Refiner · state", "start", 1),
      macEvent("Refiner · execution", "start", 2, {
        input: { sql: "SELECT missing" },
      }),
      macEvent("Refiner · execution", "finish", 3, {
        output: { sqlite_error: "missing column" },
      }),
      macEvent("Refiner", "start", 4, { input: "repair prompt" }),
      macEvent("Refiner", "finish", 5, { output: "SELECT 1" }),
      macEvent("Refiner · state", "finish", 6, {
        output: {
          pred: "SELECT 1",
          send_to: "Refiner",
          execution_verified: false,
        },
      }),
      macEvent("Run failed", "failed", 7, { output: "Refiner limit reached" }),
    ],
    true,
  )
  const graph = createFlow("mac_sql", steps)
  const retry = graph.edges.find((e) => e.data?.kind === "retry")!
  assert.ok(retry.style?.strokeDasharray)
  assert.ok(!graph.edges.some((e) => e.data?.kind === "success"))
  const detail = resolveStepDetail(steps[0], steps[0].calls![0].id)!
  assert.equal(detail.input, "repair prompt")
  assert.equal(graph.nodes.find((n) => n.id === detail.id)?.data.stepIndex, 0)
})

test("Codex tools are inside the session and every completed call returns to its agent", () => {
  const codex = (
    stage: string,
    kind: string,
    time: number,
    data: Partial<E> = {},
  ) => event(stage, kind, time, { ...data, method: "codex_mcp" })
  const steps = buildSteps(
    [
      codex("Input", "finish", 1),
      codex("Codex turn", "start", 2),
      codex("search_objects", "tool", 3, { output: { objects: [], total: 0 } }),
      codex("execute_sql", "error", 4, { output: "missing column" }),
      codex("execute_sql", "tool", 5, {
        output: { columns: ["1"], rows: [[1]] },
      }),
      codex("Codex turn", "finish", 6, {
        output: { audit_verified: true, sql: "SELECT 1" },
      }),
      codex("SQLite execution", "finish", 7),
    ],
    true,
  )
  const graph = createFlow("codex_mcp", steps, steps[3].id)
  const session = graph.nodes.find((n) => n.type === "session")!
  const agent = graph.nodes.find((n) => n.id === steps[1].id)!
  assert.equal(agent.parentId, session.id)
  for (const [i, step] of steps.slice(2, 5).entries()) {
    const tool = graph.nodes.find((n) => n.id === step.id)!
    assert.equal(tool.parentId, session.id)
    assert.ok(tool.data.title.startsWith(`#${i + 1} ·`))
    const call = graph.edges.find(
      (e) => e.source === agent.id && e.target === tool.id,
    )!
    const feedback = graph.edges.find(
      (e) => e.source === tool.id && e.target === agent.id,
    )!
    assert.equal(call.data?.kind, "call")
    assert.equal(feedback.data?.kind, "feedback")
    assert.equal(feedback.targetHandle, "bottom-in")
    assert.equal(feedback.style?.strokeDasharray, undefined)
    if (step.status === "error")
      assert.equal(feedback.label, "#2 · Lỗi → agent")
  }
  assert.equal(graph.nodes.find((n) => n.id === steps[3].id)?.selected, true)
  assert.notEqual(
    graph.nodes.find((n) => n.id === steps[5].id)?.parentId,
    session.id,
  )
  assert.ok(
    graph.edges.some((e) => e.source === agent.id && e.target === steps[5].id),
  )
  assert.ok(
    !graph.edges.some(
      (e) => e.source === steps[2].id && e.target === steps[3].id,
    ),
  )
})

test("Codex partial traces do not invent completed tool feedback or an accepted SQL exit", () => {
  const steps = buildSteps([
    event("Codex turn", "start", 1, { method: "codex_mcp" }),
    event("execute_sql", "start", 2, {
      method: "codex_mcp",
      input: { sql: "SELECT 1" },
    }),
  ])
  const graph = createFlow("codex_mcp", steps)
  assert.ok(
    graph.edges.some(
      (e) => e.source === steps[0].id && e.target === steps[1].id,
    ),
  )
  assert.ok(
    !graph.edges.some(
      (e) => e.source === steps[1].id && e.target === steps[0].id,
    ),
  )
  const execution = graph.nodes.find(
    (n) => n.type === "task" && n.data.stage === "SQLite execution",
  )!
  assert.equal(execution.data.status, "planned")
  assert.ok(
    graph.edges.find((e) => e.target === execution.id)?.style?.strokeDasharray,
  )
  const interrupted = buildSteps(
    [
      event("Codex turn", "start", 1, { method: "codex_mcp" }),
      event("execute_sql", "start", 2, { method: "codex_mcp" }),
      event("Run failed", "failed", 3, {
        method: "codex_mcp",
        output: "cancelled",
      }),
    ],
    true,
  )
  assert.ok(
    !createFlow("codex_mcp", interrupted).edges.some(
      (e) => e.source === interrupted[1].id && e.data?.kind === "feedback",
    ),
  )
})

test("Codex preserves separate tool attempts and keeps prompts scoped to each session", () => {
  const codex = (
    stage: string,
    kind: string,
    time: number,
    data: Partial<E> = {},
  ) => event(stage, kind, time, { ...data, method: "codex_mcp" })
  const steps = buildSteps([
    codex("Codex turn", "start", 1, {
      input: {
        prompt: { question: "first", db_id: "demo" },
        instructions: "first instructions",
        runtime: { max_rows: 100 },
      },
    }),
    codex("execute_sql", "error", 2, {
      input: { sql: "SELECT 1", max_rows: 0 },
      output: "invalid max_rows",
    }),
    codex("execute_sql", "tool", 3, {
      input: { sql: "SELECT 1", max_rows: 1 },
      output: { columns: ["1"], rows: [[1]], truncated_cells: true },
    }),
    codex("Codex turn", "finish", 4, {
      output: {
        status: "completed",
        final_response: '{"sql":"SELECT 1"}',
        sql: "SELECT 1",
        audit_verified: true,
      },
    }),
    codex("Codex turn", "start", 5, {
      input: {
        prompt: '{"question":"second","db_id":"demo"}',
        instructions: "second instructions",
        runtime: { max_rows: 50 },
      },
    }),
    codex("search_objects", "tool", 6, {
      input: { query: "" },
      output: { objects: [], total: 0, has_more: false },
    }),
  ])
  assert.equal(steps.length, 5)
  const first = codexContext(steps[0], steps)
  assert.deepEqual(first.prompt, { question: "first", db_id: "demo" })
  assert.equal(first.request?.instructions, "first instructions")
  assert.equal(first.returnedSql, "SELECT 1")
  assert.equal(first.tools.length, 2)
  assert.equal(codexContext(steps[2], steps).callNumber, 2)
  assert.equal(stepDetails(steps[2], steps).table?.truncated_cells, true)
  const second = codexContext(steps[4], steps)
  assert.deepEqual(second.prompt, { question: "second", db_id: "demo" })
  assert.equal(second.request?.instructions, "second instructions")
  assert.equal(second.runtime?.max_rows, 50)
  assert.equal(second.tools.length, 1)
  assert.equal(second.callNumber, 1)
  const graph = createFlow("codex_mcp", steps)
  const firstParent = graph.nodes.find((n) => n.id === steps[0].id)?.parentId
  const secondParent = graph.nodes.find((n) => n.id === steps[3].id)?.parentId
  assert.notEqual(firstParent, secondParent)
  assert.equal(
    graph.nodes.find((n) => n.id === steps[1].id)?.parentId,
    firstParent,
  )
  assert.equal(
    graph.nodes.find((n) => n.id === steps[4].id)?.parentId,
    secondParent,
  )
})

test("Codex SDK completion with an error is not displayed as a successful session", () => {
  const steps = buildSteps(
    [
      event("Codex turn", "start", 1, { method: "codex_mcp" }),
      event("Codex turn", "finish", 2, {
        method: "codex_mcp",
        output: { status: "TurnStatus.failed", error: "provider failed" },
      }),
    ],
    true,
  )
  assert.equal(steps[0].status, "error")
  assert.equal(
    createFlow("codex_mcp", steps).nodes.find((n) => n.id === steps[0].id)?.data
      .status,
    "error",
  )
})

test("DAIL streaming keeps one generation node with its exact prompt, response and SQL", () => {
  const events = [
    event("SQL generation · pass 2", "start", 1, {
      input: { script: "ask_llm.py" },
    }),
    event("LLM response · pass 2", "start", 2, {
      input: { prompt: "second pass prompt", model: "test" },
    }),
    event("LLM response · pass 2", "finish", 3, {
      output: { response: ["```sql\nSELECT 2\n```"], total_tokens: 12 },
    }),
    event("SQL generation · pass 2", "finish", 4, { output: "SELECT 2" }),
  ]
  for (let prefix = 1; prefix <= events.length; prefix++) {
    const steps = buildSteps(events.slice(0, prefix))
    assert.equal(steps.length, 1)
    assert.equal(steps[0].id, "dail_sql-0")
    assert.equal(steps[0].status, prefix === 4 ? "done" : "running")
    assert.equal(
      stepDetails(steps[0], steps).prompt,
      prefix > 1 ? "second pass prompt" : undefined,
    )
    assert.ok(
      createFlow("dail_sql", steps).nodes.every(
        (n) => n.type !== "task" || !n.data.stage.startsWith("LLM response"),
      ),
    )
  }
  const steps = buildSteps(events, true)
  assert.equal(stepDetails(steps[0], steps).sql, "SELECT 2")
  assert.deepEqual(steps[0].calls?.[0].output, events[2].output)
})

test("DAIL retains nested provider failures and never borrows prompts across failed retries", () => {
  const steps = buildSteps(
    [
      event("SQL generation · pass 1", "start", 1),
      event("SQL generation · pass 1", "start", 3),
      event("LLM response · pass 1", "start", 4, {
        input: { prompt: "retry prompt" },
      }),
      event("LLM response · pass 1", "error", 5, {
        output: "provider unavailable",
      }),
      event("SQL generation · pass 1", "error", 6, {
        output: "provider unavailable",
      }),
      event("Run failed", "failed", 7),
    ],
    true,
  )
  assert.equal(steps[0].calls?.length, 0)
  assert.equal(stepDetails(steps[0], steps).prompt, undefined)
  assert.equal(steps[1].calls?.[0].status, "error")
  assert.equal(steps[1].calls?.[0].output, "provider unavailable")
  assert.equal(steps[1].status, "error")
})

test("DAIL pass 2 selection shows preceding preliminary SQL and keeps prompt as an output artifact", () => {
  const steps = buildSteps(
    [
      event("Input", "finish", 1, {
        output: { question: "Count", db_id: "demo" },
      }),
      event("SQL generation · pass 1", "finish", 2, { output: "SELECT 1" }),
      event("Example selection · pass 2", "start", 3, {
        input: {
          arguments: [
            "--selector_type",
            "EUCDISMASKPRESKLSIMTHR",
            "--k_shot",
            "9",
          ],
        },
      }),
      event("Example selection · pass 2", "finish", 4, {
        output: { prompt: "new prompt", examples: [], n_examples: 0 },
      }),
      event("SQL generation · pass 2", "finish", 5, { output: "SELECT 2" }),
    ],
    true,
  )
  const context = methodContext(steps[2], steps)
  assert.equal(context.question, "Count")
  assert.equal(context.db_id, "demo")
  assert.equal(context.preliminary_sql, "SELECT 1")
  assert.equal(context.selector, "EUCDISMASKPRESKLSIMTHR")
  assert.equal(context.k_shot, "9")
  assert.equal(context.sql, undefined)
  assert.equal(context.prompt, "new prompt")
})

test("DIN recorded parser decisions and SQL artifacts are distinct from raw responses", () => {
  const din = (
    stage: string,
    kind: string,
    time: number,
    data: Partial<E> = {},
  ) => event(stage, kind, time, { ...data, method: "din_sql" })
  const steps = buildSteps(
    [
      din("Input", "finish", 1, {
        output: { question: "Count", db_id: "demo" },
      }),
      din("Schema linking", "finish", 2, {
        output: { response: "raw linking", schema_links: "[items.id]" },
      }),
      din("Classification", "finish", 3, {
        output: {
          response: "ambiguous",
          label: "NESTED",
          sub_questions: "Count",
        },
      }),
      din("SQL generation", "start", 4, {
        input: { prompt: "nested generation", branch: "NESTED" },
      }),
      din("SQL generation", "finish", 5, {
        output: { response: "SQL: `SELECT 1`", sql: "SELECT 1" },
      }),
      din("Self-correction", "start", 6, {
        input: { prompt: "check SQL", sql: "SELECT 1" },
      }),
      din("Self-correction", "finish", 7, {
        output: { response: "1", sql: "SELECT 1" },
      }),
    ],
    true,
  )
  assert.equal(classification(steps), "NESTED")
  assert.equal(methodContext(steps[3], steps).schema_links, "[items.id]")
  assert.equal(methodContext(steps[3], steps).branch, "NESTED")
  assert.equal(methodContext(steps[4], steps).sql_before, "SELECT 1")
  assert.equal(stepDetails(steps[4], steps).response, "1")
  assert.equal(stepDetails(steps[4], steps).sql, "SELECT 1")
  const graph = createFlow("din_sql", steps)
  assert.ok(!graph.nodes.some((n) => n.id === "classification-gateway"))
  assert.equal(
    graph.edges.find(
      (e) => e.source === steps[2].id && e.target === steps[3].id,
    )?.label,
    "NESTED",
  )
})

test("legacy DIN SQL prefixes remain readable and context never uses future outputs", () => {
  const steps = buildSteps([
    event("SQL generation", "finish", 1, {
      method: "din_sql",
      output: "SQL: `SELECT 1`",
    }),
    event("Self-correction", "start", 2, {
      method: "din_sql",
      input: "check candidate",
    }),
    event("SQL generation", "finish", 3, {
      method: "din_sql",
      output: "SELECT 99",
    }),
  ])
  assert.equal(methodContext(steps[1], steps).sql_before, "SELECT 1")
  const exactInput = {
    ...steps[1],
    input:
      "#### SQLite SQL QUERY\n-- candidate\nSELECT 3\n#### SQLite FIXED SQL QUERY\nSELECT",
  }
  assert.equal(
    methodContext(exactInput, steps).sql_before,
    "-- candidate\nSELECT 3",
  )
  const recordedSql = {
    ...steps[0],
    output: {
      response: "raw model text",
      sql: "-- actual normalized artifact\nSELECT 4",
    },
  }
  assert.equal(
    stepDetails(recordedSql, steps).sql,
    "-- actual normalized artifact\nSELECT 4",
  )
})

test("MAC groups Decomposer state and LLM into one stable node during streaming and replay", () => {
  const events = [
    macEvent("Decomposer · state", "start", 1, {
      input: { query: "Count items", desc_str: "items(id)" },
    }),
    macEvent("Decomposer", "start", 2, { input: "actual decomposer prompt" }),
    macEvent("Decomposer", "finish", 3, {
      output: "```sql\nSELECT COUNT(*) FROM items\n```",
    }),
    macEvent("Decomposer · state", "finish", 4, {
      output: {
        final_sql: "SELECT COUNT(*) FROM items",
        qa_pairs: "decomposition",
        send_to: "Refiner",
      },
    }),
  ]
  for (let prefix = 1; prefix <= events.length; prefix++) {
    const steps = buildSteps(events.slice(0, prefix))
    assert.equal(steps.length, 1)
    assert.equal(steps[0].id, "mac_sql-0")
    assert.equal(steps[0].status, prefix === 4 ? "done" : "running")
    assert.equal(steps[0].calls?.length, prefix > 1 ? 1 : 0)
    assert.equal(
      stepDetails(steps[0], steps).prompt,
      prefix > 1 ? "actual decomposer prompt" : undefined,
    )
    const graph = createFlow("mac_sql", steps)
    assert.equal(
      graph.nodes.filter(
        (n) => n.type === "task" && n.data.stage.startsWith("Decomposer"),
      ).length,
      1,
    )
  }
  const steps = buildSteps(events, true)
  assert.equal(stepDetails(steps[0], steps).sql, "SELECT COUNT(*) FROM items")
  assert.equal(steps[0].calls?.[0].output, events[2].output)
})

test("MAC Selector exposes its own prompt only when a call was recorded", () => {
  const steps = buildSteps(
    [
      macEvent("Selector · state", "start", 1, { input: { query: "test" } }),
      macEvent("Selector · state", "finish", 2, {
        output: { pruned: false, desc_str: "whole schema" },
      }),
      macEvent("Selector · state", "start", 3),
      macEvent("Selector", "start", 4, { input: "real selector prompt" }),
      macEvent("Selector", "error", 5, { output: "provider error" }),
      macEvent("Selector · state", "finish", 6, { output: { pruned: true } }),
    ],
    true,
  )
  assert.equal(steps.length, 2)
  assert.equal(stepDetails(steps[0], steps).prompt, undefined)
  assert.equal(stepDetails(steps[1], steps).prompt, "real selector prompt")
  assert.equal(steps[1].calls?.[0].status, "error")
})

test("MAC Refiner retains execution errors and scopes repair prompts to their own round", () => {
  const steps = buildSteps(
    [
      macEvent("Refiner · state", "start", 1, {
        input: { final_sql: "SELECT missing" },
      }),
      macEvent("Refiner · execution", "start", 2, {
        input: { sql: "SELECT missing", db_id: "demo" },
      }),
      macEvent("Refiner · execution", "finish", 3, {
        output: { sqlite_error: "no such column", sql: "SELECT missing" },
      }),
      macEvent("Refiner", "start", 4, { input: "fix missing column" }),
      macEvent("Refiner", "finish", 5, { output: "```sql\nSELECT 1\n```" }),
      macEvent("Refiner · state", "finish", 6, {
        output: { pred: "SELECT 1", send_to: "Refiner" },
      }),
      macEvent("Refiner · state", "start", 7, { input: { pred: "SELECT 1" } }),
      macEvent("Refiner · execution", "start", 8, {
        input: { sql: "SELECT 1", db_id: "demo" },
      }),
      macEvent("Refiner · execution", "finish", 9, {
        output: { data: [[1]], sqlite_error: "" },
      }),
      macEvent("Refiner · state", "finish", 10, {
        output: { pred: "SELECT 1", send_to: "System" },
      }),
    ],
    true,
  )
  assert.equal(steps.length, 2)
  assert.equal(steps[0].checks?.[0].stage, "Refiner · execution")
  assert.deepEqual(steps[0].checks?.[0].output, {
    sqlite_error: "no such column",
    sql: "SELECT missing",
  })
  assert.equal(stepDetails(steps[0], steps).prompt, "fix missing column")
  assert.equal(stepDetails(steps[1], steps).prompt, undefined)
  assert.equal(steps[1].calls?.length, 0)
  assert.equal(steps[1].checks?.length, 1)
  const graph = createFlow("mac_sql", steps)
  const edge = graph.edges.find(
    (e) =>
      e.source === steps[0].calls?.[0].id &&
      e.target === steps[1].checks?.[0].id,
  )
  assert.equal(edge?.label, "SQL đã sửa → chạy lại")
  assert.equal(edge?.data?.kind, "retry")
  assert.equal(edge?.style?.strokeDasharray, undefined)
  assert.equal(refinerOutcome(steps[0]), "repair")
  assert.equal(refinerOutcome(steps[1]), "success")
  assert.equal(
    graph.nodes.find((n) => n.id === steps[0].checks?.[0].id)?.data.status,
    "error",
  )
  const child = graph.nodes.find((n) => n.id === steps[0].calls?.[0].id)!
  assert.equal(child.data.stepIndex, 0)
  assert.equal(
    resolveStepDetail(steps[0], steps[0].calls![0].id)?.stage,
    "Refiner",
  )
  assert.equal(resolveStepDetail(steps[0], "unknown"), steps[0])
})

test("MAC interrupted invocations cannot borrow a later retry's calls", () => {
  const steps = buildSteps(
    [
      macEvent("Decomposer · state", "start", 1),
      macEvent("Decomposer · state", "start", 3),
      macEvent("Decomposer", "start", 4, { input: "retry only" }),
      macEvent("Decomposer", "error", 5, { output: "failed" }),
      macEvent("Run failed", "failed", 6),
    ],
    true,
  )
  assert.equal(steps.length, 3)
  assert.equal(steps[0].calls?.length, 0)
  assert.equal(steps[1].calls?.[0].output, "failed")
  assert.equal(steps[1].status, "interrupted")
})

test("all methods omit Final SQL in preview and replay and keep execution connected", () => {
  for (const method of [
    "din_sql",
    "mac_sql",
    "dail_sql",
    "codex_mcp",
  ] as Method[]) {
    const steps = buildSteps([
      event("Input", "finish", 1, { method }),
      event("Final SQL", "result", 2, { method, output: "SELECT 1" }),
      event("SQLite execution", "start", 3, {
        method,
        input: { sql: "SELECT 1", gold_sql: "SELECT 1" },
      }),
    ])
    assert.deepEqual(
      steps.map((s) => s.stage),
      ["Input", "SQLite execution"],
    )
    for (const trace of [[], steps]) {
      const graph = createFlow(method, trace)
      assert.ok(graph.nodes.every((n) => n.data.stage !== "Final SQL"))
      if (trace.length) {
        if (method === "codex_mcp") {
          const hub = graph.nodes.find(
            (n) => n.type === "task" && n.data.stage === "Codex turn",
          )!
          assert.ok(
            graph.edges.some(
              (e) => e.source === steps[0].id && e.target === hub.id,
            ),
          )
          assert.ok(
            graph.edges.some(
              (e) => e.source === hub.id && e.target === steps[1].id,
            ),
          )
        } else {
          const visited = new Set([steps[0].id])
          for (let i = 0; i < graph.nodes.length; i++)
            for (const edge of graph.edges)
              if (visited.has(edge.source)) visited.add(edge.target)
          assert.ok(visited.has(steps[1].id))
        }
      }
    }
  }
})

test("execution inputs retain both SQLs, support saved traces and leave errors visible", () => {
  const steps = buildSteps([
    event("SQLite execution", "start", 1, {
      input: { sql: "SELECT missing", gold_sql: "SELECT 1" },
    }),
    event("SQLite execution", "error", 2, {
      output: "no such column: missing",
    }),
    event("SQLite execution", "start", 3, { input: "SELECT 1" }),
    event("SQLite execution", "finish", 4, {
      output: {
        columns: ["1"],
        rows: [[1]],
        evaluation: {
          correct: true,
          metric: "SQLite EX",
          gold_sql: "SELECT 1 AS gold",
        },
      },
    }),
    event("SQLite execution", "start", 5, {
      input: { sql: "SELECT 2", gold_sql: null },
    }),
  ])
  assert.deepEqual(stepDetails(steps[0], steps).executionInput, {
    sql: "SELECT missing",
    gold_sql: "SELECT 1",
  })
  assert.equal(stepDetails(steps[0], steps).sql, undefined)
  assert.equal(steps[0].output, "no such column: missing")
  assert.deepEqual(stepDetails(steps[1], steps).executionInput, {
    sql: "SELECT 1",
    gold_sql: "SELECT 1 AS gold",
  })
  assert.deepEqual(stepDetails(steps[2], steps).executionInput, {
    sql: "SELECT 2",
    gold_sql: null,
  })
})

test("SSE prefixes and replay keep node identity stable across completion", () => {
  const start = event("Preprocessing", "start", 1, {
    input: { question: "test" },
  })
  const finish = event("Preprocessing", "finish", 2, {
    output: { examples: 1 },
    elapsed: 1,
  })
  const partial = buildSteps([start]),
    complete = buildSteps([start, finish], true)
  assert.equal(partial[0].id, complete[0].id)
  assert.equal(partial[0].status, "running")
  assert.equal(complete[0].status, "done")
  assert.deepEqual(complete[0].input, { question: "test" })
})
test("failed completion closes the matching step; interrupted parents are never marked done", () => {
  const steps = buildSteps(
    [
      event("Parent", "start", 1),
      event("Child", "start", 2),
      event("Child", "failed", 3, { output: "provider failed" }),
    ],
    true,
  )
  assert.equal(steps[0].status, "interrupted")
  assert.equal(steps[1].status, "error")
  assert.equal(steps.length, 2)
})
test("nested parent and LLM responses preserve their own outputs and correlate prompts", () => {
  const steps = buildSteps(
    [
      event("SQL generation · pass 1", "start", 1, {
        input: { arguments: ["ask_llm.py"] },
      }),
      event("LLM response · pass 1", "start", 2, {
        input: { prompt: "actual first prompt" },
      }),
      event("LLM response · pass 1", "finish", 3, {
        output: { response: ["SELECT 1"] },
      }),
      event("SQL generation · pass 1", "finish", 4, { output: "SELECT 1" }),
      event("SQL generation · pass 1", "start", 5),
      event("LLM response · pass 1", "start", 6, {
        input: { prompt: "retry prompt" },
      }),
      event("LLM response · pass 1", "finish", 7, {
        output: { response: ["SELECT 2"] },
      }),
      event("SQL generation · pass 1", "finish", 8, { output: "SELECT 2" }),
    ],
    true,
  )
  assert.equal(steps.length, 2)
  assert.equal(stepDetails(steps[0], steps).prompt, "actual first prompt")
  assert.equal(stepDetails(steps[0], steps).sql, "SELECT 1")
  assert.equal(stepDetails(steps[1], steps).prompt, "retry prompt")
  assert.equal(steps[1].attempt, 2)
  assert.equal(
    steps[0].calls?.[0].output && steps[0].calls?.[0].stage,
    "LLM response · pass 1",
  )
  assert.equal(new Set(steps.map((s) => s.id)).size, 2)
})
test("an interrupted earlier invocation cannot borrow a retry's prompt", () => {
  const steps = buildSteps(
    [
      event("SQL generation · pass 1", "start", 1),
      event("SQL generation · pass 1", "start", 3),
      event("LLM response · pass 1", "start", 4, {
        input: { prompt: "only retry" },
      }),
    ],
    true,
  )
  assert.equal(stepDetails(steps[0], steps).prompt, undefined)
  assert.equal(stepDetails(steps[1], steps).prompt, "only retry")
})
test("DAIL selections expose real examples and prompts, never generate intermediate SQL", () => {
  const examples = [
    {
      db_id: "train",
      question: "Count entries",
      query: "SELECT COUNT(*) FROM entries",
    },
  ]
  const steps = buildSteps(
    [
      event("Example selection · pass 2", "finish", 1, {
        output: { prompt: "real combined prompt", examples, n_examples: 1 },
      }),
    ],
    true,
  )
  const details = stepDetails(steps[0], steps)
  assert.deepEqual(details.examples, examples)
  assert.equal(details.prompt, "real combined prompt")
  assert.equal(details.sql, undefined)
})
test("Codex tool retries keep error and success nodes, including structured SQL and rows", () => {
  const steps = buildSteps(
    [
      event("execute_sql", "error", 1, {
        method: "codex_mcp",
        input: { sql: "SELECT 4" },
        output: "max_rows invalid",
      }),
      event("execute_sql", "tool", 2, {
        method: "codex_mcp",
        input: { sql: "SELECT 4" },
        output: { columns: ["count"], rows: [[4]], truncated: false },
      }),
    ],
    true,
  )
  const graph = createFlow("codex_mcp", steps)
  const real = graph.nodes.filter(
    (n) => n.type === "task" && n.data.stepIndex !== undefined,
  )
  assert.equal(real.length, 2)
  assert.notEqual(real[0].id, real[1].id)
  assert.equal(real[0].data.status, "error")
  assert.equal(real[1].data.status, "done")
  assert.equal(steps[1].attempt, 2)
  assert.equal(stepDetails(steps[1], steps).sql, "SELECT 4")
  assert.deepEqual(stepDetails(steps[1], steps).table?.rows, [[4]])
})
test("all four blueprints show only planned placeholders before receiving trace", () => {
  for (const method of [
    "dail_sql",
    "din_sql",
    "mac_sql",
    "codex_mcp",
  ] as Method[]) {
    const graph = createFlow(method, [])
    assert.ok(graph.nodes.some((n) => n.type === "lane"))
    for (const node of graph.nodes.filter((n) => n.type === "task")) {
      assert.equal(node.data.status, "planned")
      assert.equal(node.data.stepIndex, undefined)
    }
    assert.ok(graph.edges.every((e) => e.style?.strokeDasharray))
  }
})
test("DIN branch is highlighted only when the response explicitly records a label", () => {
  const ambiguous = buildSteps(
    [
      event("Classification", "finish", 1, {
        output: "Consider EASY, NON-NESTED and NESTED",
      }),
    ],
    true,
  )
  assert.equal(classification(ambiguous), undefined)
  const actual = buildSteps(
    [
      event("Classification", "finish", 1, {
        output: 'No JOIN needed.\nLabel: "EASY"',
      }),
    ],
    true,
  )
  assert.equal(classification(actual), "EASY")
  const graph = createFlow("din_sql", actual)
  const node = graph.nodes.find(
    (n) => n.type === "task" && n.data.stage === "Classification",
  )
  assert.equal(node?.data.branch, "EASY")
  assert.equal(node?.data.stepIndex, 0)
  assert.ok(graph.nodes.every((n) => n.id !== "classification-gateway"))
})
test("MAC repeated rounds and unknown failure stages remain selectable", () => {
  const steps = buildSteps(
    [
      event("Refiner · state", "start", 1),
      event("Refiner · state", "finish", 2),
      event("Refiner · state", "start", 3),
      event("Refiner · state", "finish", 4),
      event("Run failed", "failed", 5, { output: "budget exceeded" }),
    ],
    true,
  )
  const graph = createFlow("mac_sql", steps)
  assert.deepEqual(
    graph.nodes
      .filter((n) => n.type === "task" && n.data.stepIndex !== undefined)
      .map((n) => n.data.stepIndex),
    [0, 1, 2],
  )
  assert.equal(steps[1].attempt, 2)
  assert.equal(new Set(graph.nodes.map((n) => n.id)).size, graph.nodes.length)
})
test("raw Codex final JSON and valid empty query results retain their meaning", () => {
  const steps = buildSteps(
    [
      event("Codex turn", "finish", 1, {
        output: { final_response: '{"sql":"SELECT name FROM items"}' },
      }),
      event("SQLite execution", "finish", 2, {
        output: {
          columns: ["name"],
          rows: [],
          evaluation: { correct: true, metric: "SQLite EX" },
        },
      }),
    ],
    true,
  )
  assert.equal(stepDetails(steps[0], steps).sql, "SELECT name FROM items")
  assert.deepEqual(stepDetails(steps[1], steps).table?.rows, [])
  assert.equal(stepDetails(steps[1], steps).table?.evaluation?.correct, true)
})

test("a terminal method failure interrupts open tasks even before replay reaches other methods", () => {
  const steps = buildSteps([
    event("SQL generation · pass 1", "start", 1),
    event("Run failed", "failed", 3, { output: "worker exited" }),
  ])
  assert.equal(steps[0].status, "interrupted")
  assert.equal(steps[0].endTime, 3)
  assert.equal(steps[1].status, "error")
})

test("every flow publishes dimensions for minimap and keeps child nodes inside lanes", () => {
  for (const method of [
    "din_sql",
    "mac_sql",
    "dail_sql",
    "codex_mcp",
  ] as Method[]) {
    const graph = createFlow(method, [])
    for (const node of graph.nodes) {
      assert.ok(node.width! > 0 && node.height! > 0)
      if (node.parentId) {
        const parent = graph.nodes.find((p) => p.id === node.parentId)!
        assert.ok(node.position.x + node.width! <= parent.width!)
        assert.ok(node.position.y + node.height! <= parent.height!)
      }
    }
  }
})
