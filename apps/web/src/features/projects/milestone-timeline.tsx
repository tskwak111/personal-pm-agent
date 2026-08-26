export type Milestone = {
  id: string;
  title: string;
  deadlineDate: string | null;
  status: string;
};

export function MilestoneTimeline({ milestones }: { milestones: Milestone[] }) {
  return (
    <ol aria-label="마일스톤 타임라인">
      {milestones.map((m) => (
        <li key={m.id}>
          {m.title} — {m.deadlineDate ?? "날짜 미확정"} ({m.status})
        </li>
      ))}
    </ol>
  );
}
