export type CalendarSyncStatus = {
  internal: "SAVED" | "PENDING";
  external: "SYNCED" | "FAILED" | "PENDING";
  reason?: string;
};

export function SyncStatus({ status }: { status: CalendarSyncStatus }) {
  if (status.external === "FAILED") {
    return (
      <div role="alert">
        <p>앱 내부 저장 완료</p>
        <p>Google Calendar 반영 실패: {status.reason ?? "원인 불명"}</p>
      </div>
    );
  }
  if (status.external === "PENDING") {
    return <p aria-live="polite">Google Calendar 반영 대기 중…</p>;
  }
  return (
    <div>
      <p>앱 내부 저장 완료</p>
      <p>Google Calendar 반영 완료</p>
    </div>
  );
}
