"use client";

import { useCallback } from "react";
import Link from "next/link";
import type { components } from "@personal-pm/api-client";

import { ApiState } from "../../../components/api-state";
import { api, requireApiData } from "../../../lib/api";
import { useApiResource } from "../../../lib/use-api-resource";

type ProjectsData = components["schemas"]["ProjectsResponse"];
const isEmpty = (value: ProjectsData) => value.projects.length === 0;

export default function ProjectsPage() {
  const load = useCallback(async () => requireApiData(await api.GET("/api/v1/projects")), []);
  const resource = useApiResource(load, isEmpty);
  return (
    <main>
      <h1>프로젝트</h1>
      {resource.state === "ready" && resource.data ? (
        <ul>
          {resource.data.projects.map((project) => (
            <li key={project.id}>
              <Link href={`/projects/${project.id}`}>{project.title}</Link>
              {` · 진행 ${project.execution_progress}% · 위험 ${project.risk_level}`}
            </li>
          ))}
        </ul>
      ) : (
        <ApiState state={resource.state}>프로젝트</ApiState>
      )}
    </main>
  );
}
