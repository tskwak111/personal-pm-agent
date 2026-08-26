export type ProjectHealth = {
  title: string;
  executionProgress: number;
  riskLevel: string;
  riskReasons: string[];
};

function Metric({ label, value }: { label: string; value: string }) {
  return <p>{`${label} ${value}`}</p>;
}

export function ProjectHeader({ project }: { project: ProjectHealth }) {
  return (
    <header>
      <h1>{project.title}</h1>
      {/* Progress and schedule risk are deliberately separate metrics. */}
      <Metric label="실행 진행률" value={`${project.executionProgress}%`} />
      <Metric label="마감 가능성" value={project.riskLevel} />
      <ul aria-label="판단 근거">
        {project.riskReasons.map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>
    </header>
  );
}
