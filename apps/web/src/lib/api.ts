import { createPersonalPmClient } from "@personal-pm/api-client";

import { getToken } from "./session";

export const api = createPersonalPmClient({
  baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL ?? "",
  token: getToken,
});

export class ApiRequestError extends Error {
  constructor(readonly status: number) {
    super(`API request failed: ${status}`);
  }
}

export function requireApiData<T>(result: { data?: T; response: Response }): T {
  if (result.data === undefined) throw new ApiRequestError(result.response.status);
  return result.data;
}
