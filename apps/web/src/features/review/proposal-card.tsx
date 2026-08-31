"use client";

import { useState } from "react";

import { Button, Card } from "../../components/ui";

export type ProposalView = {
  id: string;
  version: number;
  beforeState: string;
  proposedState: string;
  minutesSavedOrAdded: number;
  resultingRisk: string;
  reversible: boolean;
};

export function ProposalCard({
  proposal,
  onDecision,
}: {
  proposal: ProposalView;
  onDecision?: (proposal: ProposalView, decision: "approve" | "reject") => Promise<void> | void;
}) {
  const saved = proposal.minutesSavedOrAdded >= 0;
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(false);

  async function decide(decision: "approve" | "reject") {
    if (!onDecision || pending) return;
    setPending(true);
    setError(false);
    try {
      await onDecision(proposal, decision);
    } catch {
      setError(true);
    } finally {
      setPending(false);
    }
  }

  return (
    <Card aria-label={`제안 ${proposal.id}`}>
      <p>{`${proposal.beforeState} → ${proposal.proposedState}`}</p>
      <p>
        {saved
          ? `예상 절감 ${proposal.minutesSavedOrAdded}분`
          : `예상 추가 ${-proposal.minutesSavedOrAdded}분`}
      </p>
      <p>결과 리스크: {proposal.resultingRisk}</p>
      <Button onClick={() => decide("approve")} disabled={pending || !onDecision}>
        {pending ? "처리 중…" : "승인"}
      </Button>
      <Button variant="ghost" onClick={() => decide("reject")} disabled={pending || !onDecision}>
        거절
      </Button>
      {proposal.reversible && <Button variant="ghost">되돌리기</Button>}
      {error ? <p role="alert">제안을 처리하지 못했습니다</p> : null}
    </Card>
  );
}
