// src/services/api.ts
const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export async function getJSON<T>(path: string): Promise<T> {
  const r = await fetch(`${API}${path}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<T>;
}
