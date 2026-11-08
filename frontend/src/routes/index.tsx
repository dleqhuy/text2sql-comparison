import { createFileRoute } from "@tanstack/react-router"
import PipelineExplorer from "@/features/pipeline/PipelineExplorer"
import "@/features/pipeline/pipeline.css"
export const Route = createFileRoute("/")({
  component: () => (
    <div className="sql-lab">
      <PipelineExplorer />
    </div>
  ),
  head: () => ({ meta: [{ title: "SQL / Lab — Pipeline explorer" }] }),
})
