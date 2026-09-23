"use client";

import {
  ArtifactPanelFrame,
  ArtifactPlaceholder,
  type ArtifactPanelProps,
} from "@/components/layout/artifact-panel-frame";

export function ProveSavingsArtifactPanel({ onClose }: ArtifactPanelProps) {
  return (
    <ArtifactPanelFrame onClose={onClose}>
      <ArtifactPlaceholder
        title="Savings artifacts"
        description="Realized savings evidence and outcome reports will appear here."
      />
    </ArtifactPanelFrame>
  );
}
