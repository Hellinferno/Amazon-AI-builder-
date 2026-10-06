// Typed client for the backend. Every failure becomes an ApiFailure with the
// backend's stable error code so the UI can show it without guessing.

import type {
  ApiError,
  AppState,
  CashflowFacts,
  ChatResponse,
  Envelope,
  ImportIssue,
  InvoiceFact,
  RecordFacts,
  ReminderFacts,
  SavedScenario,
  SimulationFacts,
} from "./types";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ?? "";
const DEFAULT_TIMEOUT_MS = 45_000;

export class ApiFailure extends Error {
  code: string;
  httpStatus: number;
  details: unknown;
  constructor(code: string, message: string, httpStatus: number, details?: unknown) {
    super(message);
    this.code = code;
    this.httpStatus = httpStatus;
    this.details = details;
  }
}

async function request<T>(path: string, init: RequestInit = {}, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let response: Response;
  try {
    response = await fetch(BASE + path, { ...init, signal: controller.signal });
  } catch (err) {
    clearTimeout(timer);
    if ((err as Error).name === "AbortError") {
      throw new ApiFailure("timeout", `The backend did not answer within ${timeoutMs / 1000}s.`, 0);
    }
    throw new ApiFailure("network", "Could not reach the backend. Is it running on port 8000?", 0);
  }
  clearTimeout(timer);
  let body: unknown = null;
  const text = await response.text();
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = null;
    }
  }
  if (!response.ok) {
    const err = (body as { error?: ApiError } | null)?.error;
    const detail = (body as { detail?: unknown } | null)?.detail; // FastAPI validation errors
    const message = err?.message ?? (typeof detail === "string" ? detail : `Request failed (${response.status})`);
    throw new ApiFailure(err?.code ?? (detail ? "validation_error" : "http_error"), message, response.status, body);
  }
  return body as T;
}

const json = (payload: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(payload),
});

export const api = {
  state: () => request<AppState>("/api/state"),
  forecast: (horizonEnd?: string) =>
    request<Envelope<CashflowFacts>>(`/api/forecast${horizonEnd ? `?horizon_end=${encodeURIComponent(horizonEnd)}` : ""}`),
  invoices: () => request<Envelope<{ invoices: InvoiceFact[]; total_outstanding: string }>>("/api/invoices"),
  simulate: (invoiceId: string, delayDays: number, horizonEnd?: string) =>
    request<Envelope<SimulationFacts>>(
      "/api/simulate",
      json({ invoice_id: invoiceId, delay_days: delayDays, horizon_end: horizonEnd ?? null }),
    ),
  record: (type: string, id: string) =>
    request<Envelope<RecordFacts>>(`/api/records/${encodeURIComponent(type)}/${encodeURIComponent(id)}`),
  reminder: (invoiceId: string, tone: "friendly" | "firm") =>
    request<Envelope<ReminderFacts>>("/api/reminders/draft", json({ invoice_id: invoiceId, tone })),
  chat: (message: string, sessionId: string | null, horizonEnd?: string) =>
    request<ChatResponse>("/api/chat", json({ message, session_id: sessionId, horizon_end: horizonEnd ?? null })),
  scenarios: () => request<{ scenarios: SavedScenario[] }>("/api/scenarios"),
  saveScenario: (invoiceId: string, delayDays: number, name: string) =>
    request<{ scenario: SavedScenario; result: Envelope<SimulationFacts> }>(
      "/api/scenarios",
      json({ invoice_id: invoiceId, delay_days: delayDays, name }),
    ),
  getScenario: (id: string) =>
    request<{ scenario: SavedScenario; result: Envelope<SimulationFacts> }>(`/api/scenarios/${encodeURIComponent(id)}`),
  recomputeScenario: (id: string) =>
    request<{ scenario: SavedScenario; result: Envelope<SimulationFacts> }>(
      `/api/scenarios/${encodeURIComponent(id)}/recompute`,
      { method: "POST" },
    ),
  deleteScenario: (id: string) => request<{ deleted: string }>(`/api/scenarios/${encodeURIComponent(id)}`, { method: "DELETE" }),
  reset: () => request<{ dataset_version: string; scenarios_cleared: number; warnings: string[] }>("/api/demo/reset", { method: "POST" }),
  importDataset: (snapshot: string, invoices: File, obligations: File) => {
    const form = new FormData();
    form.append("snapshot", snapshot);
    form.append("invoices", invoices);
    form.append("obligations", obligations);
    return request<{ dataset_version: string; invoice_count: number; obligation_count: number; warnings: ImportIssue[]; stale_scenarios: string[] }>(
      "/api/datasets/import",
      { method: "POST", body: form },
    );
  },
};

export function importErrors(failure: ApiFailure): ImportIssue[] {
  const body = failure.details as { errors?: ImportIssue[] } | null;
  return body?.errors ?? [];
}
