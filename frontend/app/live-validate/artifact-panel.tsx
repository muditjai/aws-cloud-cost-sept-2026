"use client";

import {
  ArtifactPanelFrame,
  ArtifactPlaceholder,
  type ArtifactPanelProps,
} from "@/components/layout/artifact-panel-frame";

export function LiveValidateArtifactPanel({ onClose }: ArtifactPanelProps) {
  return (
    <ArtifactPanelFrame onClose={onClose}>
      <ArtifactPlaceholder
        title="Live validation artifacts"
        description="Production validation evidence will appear here."
      />
    </ArtifactPanelFrame>
  );
}
