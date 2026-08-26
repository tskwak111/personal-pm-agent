"use client";

import { Button, Card } from "../../components/ui";

export type ProposalView = {
  id: string;
  beforeState: string;
  proposedState: string;
  minutesSavedOrAdded: number;
  resultingRisk: string;
  reversible: boolean;
};

export function ProposalCard({ proposal }: { proposal: ProposalView }) {
  const saved = proposal.minutesSavedOrAdded >= 0;
  return (
    <Card aria-label={`제안 ${proposal.id}`}>
      <p>{`${proposal.beforeState} → ${proposal.proposedState}`}</p>
      <p>
        {saved
          ? `예상 절감 ${proposal.minutesSavedOrAdded}분`
          : `예상 추가 ${-proposal.minutesSavedOrAdded}분`}
      </p>
      <p>결과 리스크: {proposal.resultingRisk}</p>
      <Button>승인</Button>
      <Button variant="ghost">거절</Button>
      {proposal.reversible && <Button variant="ghost">되돌리기</Button>}
    </Card>
  );
}
