"use client";

import { useState } from "react";

import type { InboxCandidate } from "./candidate-card";
import { CandidateCard } from "./candidate-card";

const FILTERS = ["ALL", "NEEDS_CONFIRMATION", "STRUCTURED", "FAILED"] as const;

export function InboxList({ candidates }: { candidates: InboxCandidate[] }) {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("ALL");
  const visible = filter === "ALL" ? candidates : candidates.filter((c) => c.kind === filter);
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
      {visible.map((c) => (
        <CandidateCard key={c.id} candidate={c} />
      ))}
    </section>
  );
}
