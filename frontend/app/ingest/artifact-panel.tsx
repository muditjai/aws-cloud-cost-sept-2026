"use client";

import {
  ArtifactPanelFrame,
  ArtifactPlaceholder,
  type ArtifactPanelProps,
} from "@/components/layout/artifact-panel-frame";

export function IngestArtifactPanel({ onClose }: ArtifactPanelProps) {
  return (
    <ArtifactPanelFrame onClose={onClose}>
      <ArtifactPlaceholder
        title="Ingest artifacts"
        description="Billing and usage data summaries will appear here."
      />
    </ArtifactPanelFrame>
  );
}
