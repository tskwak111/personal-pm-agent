"use client";

import { useCallback, useState } from "react";

import type { InitialAnalysis } from "./onboarding-flow";

type OnboardingState = {
  stepIndex: number;
  analysis: InitialAnalysis | null;
};

export function useOnboarding() {
  const [state, setState] = useState<OnboardingState>({
    stepIndex: 0,
    analysis: null,
  });

  const setAnalysis = useCallback((analysis: InitialAnalysis) => {
    setState((s) => ({ ...s, analysis }));
  }, []);

  const next = useCallback(() => {
    setState((s) => ({ ...s, stepIndex: Math.min(s.stepIndex + 1, 4) }));
  }, []);

  return { ...state, setAnalysis, next };
}
