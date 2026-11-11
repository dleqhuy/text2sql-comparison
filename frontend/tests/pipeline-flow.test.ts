import assert from "node:assert/strict"
import { test } from "node:test"
import {
  buildSteps,
  classification,
  stepDetails,
  type Method,
} from "../src/features/pipeline/flow-model.ts"
import { createFlow } from "../src/features/pipeline/flow-graph.ts"

type E = Parameters<typeof buildSteps>[0][number]
const event = (
  stage: string,
  kind: string,
  time: number,
  data: Partial<E> = {},
): E => ({ method: "dail_sql", stage, kind, time, ...data })

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
  assert.equal(steps.length, 4)
  assert.equal(stepDetails(steps[0], steps).prompt, "actual first prompt")
  assert.equal(stepDetails(steps[0], steps).sql, "SELECT 1")
  assert.equal(stepDetails(steps[2], steps).prompt, "retry prompt")
  assert.equal(steps[2].attempt, 2)
  assert.equal(new Set(steps.map((s) => s.id)).size, 4)
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
  const gateway = createFlow("din_sql", actual).nodes.find(
    (n) => n.id === "classification-gateway",
  )
  assert.equal(gateway?.data.branch, "EASY")
  assert.equal(gateway?.data.stepIndex, 0)
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
