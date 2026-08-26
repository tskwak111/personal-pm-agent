"use client";

import { Card } from "../../components/ui/card";
import { RiskCard } from "./risk-card";
import { TaskActionBar, type TodayTask } from "./task-action-bar";

export type TodayPlan = {
  coreOutcome: string;
  selectionReason: string;
  fixedEvents: { title: string; minutes: number }[];
  mustDo: TodayTask[];
  queue: TodayTask[];
  notToday: TodayTask[];
};

export function TodayView({
  plan,
  onStartSession,
}: {
  plan: TodayPlan;
  onStartSession?: (taskId: string) => void;
}) {
  return (
    <main aria-label="오늘 화면">
      <h1>오늘</h1>
      <Card>
        <h2>오늘의 핵심 결과</h2>
        <p>{plan.coreOutcome}</p>
        <p>
          <span className="font-medium">선정 이유: </span>
          {plan.selectionReason || "아직 계획이 없습니다"}
        </p>
      </Card>

      <section aria-label="고정 일정">
        <h2>고정 일정</h2>
        {plan.fixedEvents.map((e) => (
          <p key={e.title}>
            {e.title} ({e.minutes}분)
          </p>
        ))}
      </section>

      <section aria-label="반드시 할 일">
        <h2>반드시 할 일</h2>
        {plan.mustDo.map((task) => (
          <div key={task.id}>
            {task.risks?.map((r) => (
              <RiskCard key={r.ruleId} label={r.label} ruleId={r.ruleId} />
            ))}
            <TaskActionBar task={task} onStartSession={onStartSession} />
          </div>
        ))}
      </section>
    </main>
  );
}
