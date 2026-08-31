export type ApiStateName = "loading" | "unauthenticated" | "empty" | "error" | "ready";

const MESSAGES: Record<Exclude<ApiStateName, "ready">, string> = {
  loading: "불러오는 중",
  unauthenticated: "로그인이 필요합니다",
  empty: "표시할 항목이 없습니다",
  error: "요청을 완료하지 못했습니다",
};

export function ApiState({
  state,
  children,
}: Readonly<{ state: ApiStateName; children: React.ReactNode }>) {
  if (state === "ready") return children;
  return <p role={state === "error" ? "alert" : "status"}>{MESSAGES[state]}</p>;
}
