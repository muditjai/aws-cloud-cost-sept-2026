import { StageChat } from "@/components/workspace/stage-chat";

export const instant = false;

export default function DeployPage() {
  return <StageChat workflowId="deploy" />;
}
