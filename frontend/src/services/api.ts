import axios from "axios";

export const API_BASE_URL =
  (import.meta as any).env?.VITE_API_BASE_URL || "/api";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

export interface Source {
  title: string;
  url?: string | null;
  snippet?: string;
  origin: "web" | "pdf";
}

export interface ChatResult {
  session_id: string;
  final_answer: string;
  sources: Source[];
  retry_count: number;
  metrics?: {
    route: string;
    execution_time_seconds: number;
  };
}

export async function uploadPdf(file: File, sessionId?: string) {
  const formData = new FormData();
  formData.append("file", file);
  if (sessionId) formData.append("session_id", sessionId);

  const response = await apiClient.post("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data as { filename: string; chunks_indexed: number; session_id: string };
}

export async function fetchHealth() {
  const response = await apiClient.get("/health");
  return response.data;
}

export async function fetchGraphDescription() {
  const response = await apiClient.get("/graph");
  return response.data;
}
