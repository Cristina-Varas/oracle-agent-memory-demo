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
  used_memories: UsedMemory[];
};

export type UsedMemory = {
  title: string;
  category: string;
  customer_project: string | null;
  source: string | null;
  score: number | null;
  content_preview: string;
};

export type NewMemory = {
  title: string;
  content: string;
  category: string;
  customer_project?: string | null;
  tags: string[];
  source?: string | null;
};

export type ChatModelOption = {
  model_id: string;
  provider: string;
  label: string;
  description: string;
};

export type ModelConfig = {
  active_chat_model_id: string;
  active_chat_provider: string;
  embedding_model_id: string;
  embedding_dimensions: number;
  chat_model_options: ChatModelOption[];
  runtime_config_file: string;
};

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const API_KEY = import.meta.env.VITE_AGENT_MEMORY_API_KEY ?? "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
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

export function getModelConfig() {
  return request<ModelConfig>("/models");
}

export function updateChatModel(params: { model_id: string; provider: string; validate: boolean }) {
  return request<ModelConfig>("/models/chat", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export function testChatModel(params: { model_id: string; provider: string }) {
  return request<{ status: string; model_id: string; provider: string; message: string }>("/models/chat/test", {
    method: "POST",
    body: JSON.stringify({ ...params, validate: true }),
  });
}

export function createMemory(payload: NewMemory) {
  return request<{ memory_id: string }>("/memories", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listMemories(limit = 50) {
  return request<{ count: number; memories: MemoryRecord[] }>(`/memories?limit=${limit}`).then(
    (response) => response.memories,
  );
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
