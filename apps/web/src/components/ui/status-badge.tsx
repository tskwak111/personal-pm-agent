export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      data-status={status}
      className="inline-block rounded-full border border-[var(--color-border)] px-2 py-0.5 text-xs"
    >
      {status}
    </span>
  );
}
