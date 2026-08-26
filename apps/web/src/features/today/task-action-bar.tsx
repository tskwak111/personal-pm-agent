"use client";

import { Button } from "../../components/ui/button";

export type TodayTask = {
  id: string;
  title: string;
  minutes: number;
  status: string;
  risks?: { label: string; ruleId: string }[];
};

export function TaskActionBar({
  task,
  onStartSession,
}: {
  task: TodayTask;
  onStartSession?: (taskId: string) => void;
}) {
  return (
    <div aria-label={`${task.title} 작업`}>
      <span>{task.title}</span>
      <Button
        onClick={() => {
          if (onStartSession) onStartSession(task.id);
        }}
      >
        {task.title} 시작
      </Button>
    </div>
  );
}
