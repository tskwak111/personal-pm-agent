"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { api } from "../../../lib/api";
import { setToken } from "../../../lib/session";

function configuredProviderUrl(): string | null {
  const value = process.env.NEXT_PUBLIC_SIGN_IN_URL;
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" ? url.toString() : null;
  } catch {
    return null;
  }
}

export default function SignInPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const providerUrl = configuredProviderUrl();
  const testEnvironment = process.env.NEXT_PUBLIC_APP_ENVIRONMENT === "test";

  async function createTestSession(formData: FormData) {
    setError(null);
    const email = String(formData.get("email") ?? "");
    const { data, error: apiError } = await api.POST("/api/v1/identity/test-session", {
      body: { email, seed_demo: false },
    });
    if (apiError || !data) {
      setError("테스트 세션을 만들지 못했습니다");
      return;
    }
    setToken(data.token);
    router.push("/today");
  }

  return (
    <main>
      <h1>로그인</h1>
      {providerUrl ? <a href={providerUrl}>Google로 계속</a> : <p>로그인 공급자 미설정</p>}
      {testEnvironment ? (
        <form action={createTestSession}>
          <label htmlFor="test-email">테스트 이메일</label>
          <input id="test-email" name="email" type="email" required />
          <button type="submit">테스트 세션 만들기</button>
        </form>
      ) : null}
      {error ? <p role="alert">{error}</p> : null}
    </main>
  );
}
