export type OperationStepView = { step: string; status: string };

export function OperationTimeline({ steps }: { steps: OperationStepView[] }) {
  return (
    <ol aria-label="작업 단계">
      {steps.map((s, i) => (
        <li key={`${s.step}-${i}`} data-status={s.status}>
          {s.step}: {s.status}
        </li>
      ))}
    </ol>
  );
}
