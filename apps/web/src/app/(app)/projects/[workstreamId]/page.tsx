"use client";

import { use, useCallback } from "react";

import { ApiState } from "../../../../components/api-state";
import { DependencyPanel } from "../../../../features/projects/dependency-panel";
import { MilestoneTimeline } from "../../../../features/projects/milestone-timeline";
import { ProjectHeader } from "../../../../features/projects/project-header";
import { api, requireApiData } from "../../../../lib/api";
import { useApiResource } from "../../../../lib/use-api-resource";

const neverEmpty = () => false;

export default function ProjectDetailPage({
  params,
}: {
  params: Promise<{ workstreamId: string }>;
}) {
  const { workstreamId } = use(params);
  const load = useCallback(
    async () =>
      requireApiData(
        await api.GET("/api/v1/projects/{workstream_id}", {
          params: { path: { workstream_id: workstreamId } },
        }),
      ),
    [workstreamId],
  );
  const resource = useApiResource(load, neverEmpty);
  if (resource.state !== "ready" || !resource.data) {
    return (
      <main>
        <h1>프로젝트</h1>
        <ApiState state={resource.state}>프로젝트</ApiState>
      </main>
    );
  }
  const data = resource.data;
  return (
    <main>
      <ProjectHeader
        project={{
          title: data.project.title,
          executionProgress: data.project.execution_progress,
          riskLevel: data.project.risk_level,
          riskReasons: data.project.risk_reasons,
        }}
      />
      <MilestoneTimeline
        milestones={data.milestones.map((milestone) => ({
          id: milestone.id,
          title: milestone.title,
          deadlineDate: milestone.deadline_date,
          status: milestone.status,
        }))}
      />
      <DependencyPanel
        dependencies={data.external_dependencies.map((dependency) => ({
          id: dependency.id,
          label: dependency.deliverable,
          owner: dependency.owner_label ?? undefined,
          isExternal: true,
        }))}
      />
    </main>
  );
}
