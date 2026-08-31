import createClient from "openapi-fetch";

import type { paths } from "./generated/schema.js";

export interface PersonalPmClientOptions {
  baseUrl: string;
  token: () => string | null;
}

export function createPersonalPmClient({
  baseUrl,
  token,
}: PersonalPmClientOptions) {
  const client = createClient<paths>({ baseUrl });
  client.use({
    onRequest({ request }) {
      const value = token();
      if (value) {
        request.headers.set("Authorization", `Bearer ${value}`);
      }
      return request;
    },
  });
  return client;
}
