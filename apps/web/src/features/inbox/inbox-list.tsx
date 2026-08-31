"use client";

import { useState } from "react";

import { CandidateCard, type InboxCandidate } from "./candidate-card";

const FILTERS = ["ALL", "NEW", "NEEDS_CONFIRMATION", "STRUCTURED", "FAILED"] as const;

export function InboxList({
  candidates,
  onDecision,
}: {
  candidates: InboxCandidate[];
  onDecision?: (candidateId: string, decision: "confirm" | "ignore") => Promise<void> | void;
}) {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("ALL");
  // Filter on processing STATUS (not candidate kind): kind is WHAT it is,
  // status is WHERE it is in review. Both are shown so neither is hidden.
  const visible = filter === "ALL" ? candidates : candidates.filter((c) => c.status === filter);
  return (
    <section aria-label="인박스 검토">
      <div role="tablist" aria-label="상태 필터">
        {FILTERS.map((f) => (
          <button
            key={f}
            type="button"
            role="tab"
            aria-selected={filter === f}
            onClick={() => setFilter(f)}
          >
            {f}
          </button>
        ))}
      </div>
      <p aria-live="polite">
        {visible.length} / {candidates.length} 건
      </p>
      {visible.map((c) => (
        <CandidateCard key={c.id} candidate={c} onDecision={onDecision} />
      ))}
    </section>
  );
}
