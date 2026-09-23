"use client";

import {
  ArtifactPanelFrame,
  ArtifactPlaceholder,
  type ArtifactPanelProps,
} from "@/components/layout/artifact-panel-frame";

export function ConnectArtifactPanel({ onClose }: ArtifactPanelProps) {
  return (
    <ArtifactPanelFrame onClose={onClose}>
      <ArtifactPlaceholder
        title="Connect artifacts"
        description="Cloud connection details and access checks will appear here."
      />
    </ArtifactPanelFrame>
  );
}
