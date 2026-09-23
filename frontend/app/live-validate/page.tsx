import { StageChat } from "@/components/workspace/stage-chat";

export const instant = false;

export default function LiveValidatePage() {
  return <StageChat workflowId="live-validate" />;
}
