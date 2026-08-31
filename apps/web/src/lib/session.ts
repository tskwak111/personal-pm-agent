const SESSION_KEY = "personal-pm.session";

let memoryToken: string | null | undefined;

export function getToken(): string | null {
  if (memoryToken !== undefined) return memoryToken;
  memoryToken = typeof window === "undefined" ? null : sessionStorage.getItem(SESSION_KEY);
  return memoryToken;
}

export function setToken(token: string): void {
  memoryToken = token;
  if (typeof window !== "undefined") sessionStorage.setItem(SESSION_KEY, token);
}

export function clearToken(): void {
  memoryToken = null;
  if (typeof window !== "undefined") sessionStorage.removeItem(SESSION_KEY);
}
