import { createPersonalPmClient } from "@personal-pm/api-client";

import { getToken } from "./session";

export const api = createPersonalPmClient({
  baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL ?? "",
  token: getToken,
});
