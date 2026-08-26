import { Card } from "../../components/ui";
import { OperationTimeline } from "./operation-timeline";

export type AgentOperation = {
  id: string;
  steps: { step: string; status: string }[];
  verified: boolean;
};

export function AgentPanel({ initialOperation }: { initialOperation?: AgentOperation }) {
  const op = initialOperation;
  return (
    <Card aria-label="에이전트 패널">
      <h2>에이전트</h2>
      {op && (
        <>
          <OperationTimeline steps={op.steps} />
          {/* Success is claimed only after VERIFY succeeded. */}
          {!op.verified ? <p>외부 반영 확인 중</p> : <p>완료되었습니다</p>}
        </>
      )}
    </Card>
  );
}
