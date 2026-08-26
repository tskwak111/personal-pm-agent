export function RiskCard({ label, ruleId }: { label: string; ruleId: string }) {
  return (
    <div role="note" data-rule-id={ruleId} className="text-sm text-[var(--color-danger)]">
      {label}
    </div>
  );
}
