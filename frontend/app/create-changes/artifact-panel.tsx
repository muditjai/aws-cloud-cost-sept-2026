"use client";

import {
  ArtifactPanelFrame,
  ArtifactPlaceholder,
  type ArtifactPanelProps,
} from "@/components/layout/artifact-panel-frame";

export function CreateChangesArtifactPanel({ onClose }: ArtifactPanelProps) {
  return (
    <ArtifactPanelFrame onClose={onClose}>
      <ArtifactPlaceholder
        title="Change artifacts"
        description="Implementation plans and generated changes will appear here."
      />
    </ArtifactPanelFrame>
  );
}
