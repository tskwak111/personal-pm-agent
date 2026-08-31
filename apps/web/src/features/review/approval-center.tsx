import type { ProposalView } from "./proposal-card";
import { ProposalCard } from "./proposal-card";

export function ApprovalCenter({
  proposals,
  onDecision,
}: {
  proposals: ProposalView[];
  onDecision?: (proposal: ProposalView, decision: "approve" | "reject") => Promise<void> | void;
}) {
  return (
    <section aria-label="승인 센터">
      <h1>승인 대기</h1>
      {proposals.map((p) => (
        <ProposalCard key={p.id} proposal={p} onDecision={onDecision} />
      ))}
    </section>
  );
}
