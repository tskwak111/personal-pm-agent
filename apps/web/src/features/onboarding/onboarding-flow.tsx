"use client";

import { useMemo, useState } from "react";

export type OnboardingStep = {
  id: "basics" | "sources" | "analysis" | "questions" | "report";
  title: string;
};

export const ONBOARDING_STEPS: OnboardingStep[] = [
  { id: "basics", title: "기본 정보" },
  { id: "sources", title: "기존 자료" },
  { id: "analysis", title: "자동 구조" },
  { id: "questions", title: "필요한 확인" },
  { id: "report", title: "초기 상황 보고서" },
];

export type InitialAnalysis = {
  foundFacts: string[];
  conflicts: { id: string; label: string }[];
  conflictCount: number;
};

type Props = {
  initialAnalysis?: InitialAnalysis;
};

export function OnboardingFlow({ initialAnalysis }: Props) {
  const analysis = useMemo<InitialAnalysis>(
    () => initialAnalysis ?? { foundFacts: [], conflicts: [], conflictCount: 0 },
    [initialAnalysis],
  );
  const [stepIndex, setStepIndex] = useState(0);
  const step = ONBOARDING_STEPS[stepIndex];

  // Facts already discovered from imported sources are never asked again.
  const timezoneKnown = analysis.foundFacts.some((f) => f.startsWith("timezone:"));

  return (
    <section aria-label={`온보딩 ${step.title}`}>
      <h1>{step.title}</h1>
      <ol aria-label="진행 단계">
        {ONBOARDING_STEPS.map((s, i) => (
          <li key={s.id} aria-current={i === stepIndex ? "step" : undefined}>
            {s.title}
          </li>
        ))}
      </ol>

      <div hidden={step.id !== "basics"}>
        {!timezoneKnown && <label htmlFor="tz">시간대</label>}
        {!timezoneKnown && <input id="tz" name="timezone" placeholder="Asia/Seoul" />}
      </div>

      <div hidden={step.id !== "questions"}>
        <p>날짜 충돌 {analysis.conflictCount}개</p>
        <ul>
          {analysis.conflicts.map((c) => (
            <li key={c.id}>{c.label}</li>
          ))}
        </ul>
      </div>

      {stepIndex < ONBOARDING_STEPS.length - 1 && (
        <button type="button" onClick={() => setStepIndex((i) => i + 1)}>
          계속
        </button>
      )}
    </section>
  );
}
