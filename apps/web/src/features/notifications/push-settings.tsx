"use client";

import { useEffect, useState } from "react";

import { Button } from "../../components/ui";

type PushState = "unsupported" | "default" | "subscribed";

export function PushSettings() {
  const [state, setState] = useState<PushState>("default");

  useEffect(() => {
    if (typeof Notification === "undefined" || !("serviceWorker" in navigator)) {
      setState("unsupported");
    }
  }, []);

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
    <Button variant="ghost" onClick={optIn}>
      푸시 알림 받기(선택)
    </Button>
  );
}
