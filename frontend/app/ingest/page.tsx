import { StageChat } from "@/components/workspace/stage-chat";

export const instant = false;

export default function IngestPage() {
  return <StageChat workflowId="ingest" />;
}
