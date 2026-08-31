"use client";

import { useEffect, useState } from "react";

import type { ApiStateName } from "../components/api-state";
import { ApiRequestError } from "./api";

export function useApiResource<T>(load: () => Promise<T>, isEmpty: (value: T) => boolean) {
  const [revision, setRevision] = useState(0);
  const [state, setState] = useState<ApiStateName>("loading");
  const [data, setData] = useState<T | null>(null);

  useEffect(() => {
    let active = true;
    void load()
      .then((value) => {
        if (!active) return;
        setData(value);
        setState(isEmpty(value) ? "empty" : "ready");
      })
      .catch((error: unknown) => {
        if (!active) return;
        setState(
          error instanceof ApiRequestError && error.status === 401 ? "unauthenticated" : "error",
        );
      });
    return () => {
      active = false;
    };
  }, [isEmpty, load, revision]);

  return {
    state,
    data,
    reload: () => {
      setState("loading");
      setRevision((value) => value + 1);
    },
  };
}
