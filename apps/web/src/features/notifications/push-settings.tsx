"use client";

import { useState } from "react";

import { Button } from "../../components/ui";

type PushState = "unsupported" | "default" | "subscribed";

function initialPushState(): PushState {
  if (typeof window === "undefined") return "default";
  if (typeof Notification === "undefined" || !("serviceWorker" in navigator)) {
    return "unsupported";
  }
  return Notification.permission === "granted" ? "subscribed" : "default";
}

export function PushSettings() {
  // Capability detection is deterministic at hydration; no effect needed.
  const [state, setState] = useState<PushState>(initialPushState);

  async function optIn() {
    const permission = await Notification.requestPermission();
    if (permission !== "granted") return;
    const registration = await navigator.serviceWorker.ready;
    await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: undefined, // VAPID key injected at deploy time
    });
    setState("subscribed");
  }

  if (state === "unsupported") return null;
  if (state === "subscribed") return <p>알림이 켜졌습니다</p>;
  return (
    <Button variant="ghost" onClick={() => void optIn()}>
      푸시 알림 받기(선택)
    </Button>
  );
}
