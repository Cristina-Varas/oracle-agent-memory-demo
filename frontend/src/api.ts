export type MemoryRecord = {
  memory_id: string;
  title: string;
  content: string;
  category: string;
  customer_project: string | null;
  tags: string[];
  source: string | null;
  created_at: string | null;
  score?: number | null;
};

export type ChatResponse = {
  answer: string;
  sources: MemoryRecord[];
};

export type NewMemory = {
  title: string;
  content: string;
  category: string;
  customer_project?: string | null;
  tags: string[];
  source?: string | null;
};

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      message = body.detail ?? message;
    } catch {
      // Keep the generic message when the API does not return JSON.
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export function getHealth() {
  return request<{ status: string }>("/health");
}

export function getCategories() {
  return request<{ categories: string[] }>("/config/categories");
}

export function createMemory(payload: NewMemory) {
  return request<{ memory_id: string }>("/memories", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listMemories(limit = 50) {
  return request<MemoryRecord[]>(`/memories?limit=${limit}`);
}

export function searchMemories(params: {
  query: string;
  category?: string;
  customer_project?: string;
  tags?: string[];
  limit?: number;
}) {
  const search = new URLSearchParams();
  search.set("query", params.query);
  if (params.category) search.set("category", params.category);
  if (params.customer_project) search.set("customer_project", params.customer_project);
  for (const tag of params.tags ?? []) search.append("tags", tag);
  search.set("limit", String(params.limit ?? 10));
  return request<MemoryRecord[]>(`/memories/search?${search.toString()}`);
}

export function deleteMemory(memoryId: string) {
  return request<{ deleted: number }>(`/memories/${memoryId}`, {
    method: "DELETE",
  });
}

export function chatWithMemory(params: {
  question: string;
  category?: string;
  customer_project?: string;
}) {
  return request<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify(params),
  });
}
