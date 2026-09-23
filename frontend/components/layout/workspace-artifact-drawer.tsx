"use client";

import { AuditArtifactPanel } from "@/app/audit/artifact-panel";
import { ConnectArtifactPanel } from "@/app/connect/artifact-panel";
import { CreateChangesArtifactPanel } from "@/app/create-changes/artifact-panel";
import { DeployArtifactPanel } from "@/app/deploy/artifact-panel";
import { IngestArtifactPanel } from "@/app/ingest/artifact-panel";
import { LiveValidateArtifactPanel } from "@/app/live-validate/artifact-panel";
import { ProveSavingsArtifactPanel } from "@/app/prove-savings/artifact-panel";
import { RecommendArtifactPanel } from "@/app/recommend/artifact-panel";
import { TestArtifactPanel } from "@/app/test/artifact-panel";
import { Button } from "@/components/ui/button";
import { Drawer, DrawerContent, DrawerTrigger } from "@/components/ui/drawer";
import type { ArtifactPanelProps } from "@/lib/artifacts";
import type { WorkflowId } from "@/lib/workflow";
import { PanelRightOpen } from "lucide-react";
import { type ComponentType, useState } from "react";

interface WorkspaceArtifactDrawerProps {
  readonly workflowId: WorkflowId;
}

type ArtifactPanelDictionary = {
  [workflowId in WorkflowId]: ComponentType<ArtifactPanelProps>;
};

const artifactPanels = {
  connect: ConnectArtifactPanel,
  ingest: IngestArtifactPanel,
  audit: AuditArtifactPanel,
  recommend: RecommendArtifactPanel,
  "create-changes": CreateChangesArtifactPanel,
  test: TestArtifactPanel,
  deploy: DeployArtifactPanel,
  "live-validate": LiveValidateArtifactPanel,
  "prove-savings": ProveSavingsArtifactPanel,
} satisfies ArtifactPanelDictionary;

export function WorkspaceArtifactDrawer({
  workflowId,
}: WorkspaceArtifactDrawerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const ArtifactPanel = artifactPanels[workflowId];

  return (
    <Drawer direction="right" open={isOpen} onOpenChange={setIsOpen}>
      <DrawerTrigger asChild>
        <Button
          className="absolute top-4 right-5 z-10 sm:right-7"
          variant="outline"
          size="sm"
        >
          <PanelRightOpen data-icon="inline-start" aria-hidden="true" />
          Artifacts
        </Button>
      </DrawerTrigger>
      <DrawerContent className="h-dvh max-h-none sm:max-w-md">
        <ArtifactPanel onClose={() => setIsOpen(false)} />
      </DrawerContent>
    </Drawer>
  );
}
