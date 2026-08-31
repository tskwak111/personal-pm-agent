"use client";

import { useState } from "react";

import { Button } from "../../components/ui/button";

export type TodayTask = {
  id: string;
  title: string;
  minutes: number;
  status: string;
  version: number;
  risks?: { label: string; ruleId: string }[];
};

export function TaskActionBar({
  task,
  onStartSession,
}: {
  task: TodayTask;
  onStartSession?: (task: TodayTask) => Promise<void> | void;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(false);

  async function start() {
    if (!onStartSession || pending) return;
    setPending(true);
    setError(false);
    try {
      await onStartSession(task);
    } catch {
      setError(true);
    } finally {
      setPending(false);
    }
  }

  return (
    <div aria-label={`${task.title} 작업`}>
      <span>{task.title}</span>
      <Button onClick={start} disabled={pending || task.status !== "ready" || !onStartSession}>
        {pending ? "시작 중…" : `${task.title} 시작`}
      </Button>
      {error ? <p role="alert">작업을 시작하지 못했습니다</p> : null}
    </div>
  );
}
