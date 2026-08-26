"use client";

import { Card } from "../../components/ui/card";
import { SourceEvidence, type CandidateSource } from "./source-evidence";

export type InboxCandidate = {
  id: string;
  title: string;
  kind: string;
  /** Processing status: NEW | NEEDS_CONFIRMATION | STRUCTURED | FAILED */
  status?: string;
  deadlineDate: string | null;
  timeKnown: boolean;
  conflictChoices?: { sourceId: string; label: string; date: string }[];
  sources: CandidateSource[];
};

export function CandidateCard({ candidate }: { candidate: InboxCandidate }) {
  return (
    <Card aria-label={`후보 ${candidate.title}`}>
      <h3>{candidate.title}</h3>
      <p>
        {candidate.kind}
        {candidate.status && ` · ${candidate.status}`}
      </p>
      {candidate.deadlineDate && <p>마감일: {candidate.deadlineDate}</p>}
      {!candidate.timeKnown && <p>마감 시각 미확인</p>}
      {candidate.conflictChoices && candidate.conflictChoices.length > 0 && (
        <fieldset>
          <legend>출처 선택</legend>
          {candidate.conflictChoices.map((choice) => (
            <label key={choice.sourceId}>
              <input type="radio" name={`conflict-${candidate.id}`} value={choice.sourceId} />
              {choice.label} ({choice.date})
            </label>
          ))}
        </fieldset>
      )}
      <SourceEvidence sources={candidate.sources} />
    </Card>
  );
}
