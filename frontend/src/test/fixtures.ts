// Golden fixture responses (docs/ACCOUNTING_RULES.md) in the backend's envelope shape.
import type { AppState, CashflowFacts, ChatResponse, Envelope, InvoiceFact, SimulationFacts } from "../types";

export const appState: AppState = {
  mode: "mock",
  model_id: "mock-rule-based-planner",
  simulation_label: "Simulated Alexa+ experience with synthetic demo data",
  storage_backend: "memory",
  business_id: "demo-business",
  business_name: "Demo Business",
  demo_reset_enabled: true,
  dataset: {
    dataset_version: "demo-v1",
    as_of_date: "2026-10-05",
    currency: "INR",
    timezone: "Asia/Kolkata",
    opening_cash: "50000.00",
    invoice_count: 2,
    obligation_count: 2,
    default_horizon_end: "2026-10-09",
    fingerprint: "abc",
  },
};

const evidence = [
  { record_type: "invoice" as const, record_id: "INV-001", source_file_id: "sha256:aaaa", row_number: 2 },
  { record_type: "invoice" as const, record_id: "INV-002", source_file_id: "sha256:aaaa", row_number: 3 },
  { record_type: "obligation" as const, record_id: "BILL-001", source_file_id: "sha256:bbbb", row_number: 2 },
  { record_type: "obligation" as const, record_id: "PAY-001", source_file_id: "sha256:bbbb", row_number: 3 },
];

export const baselineFacts: CashflowFacts = {
  horizon_end: "2026-10-09",
  opening_cash: "50000.00",
  closing_cash: "25000.00",
  total_inflows: "55000.00",
  total_outflows: "80000.00",
  minimum_balance: "25000.00",
  minimum_date: "2026-10-09",
  first_negative_date: null,
  shortfall_below_zero: "0.00",
  daily: [
    { date: "2026-10-05", inflows: "0.00", outflows: "0.00", closing: "50000.00" },
    { date: "2026-10-06", inflows: "0.00", outflows: "10000.00", closing: "40000.00" },
    { date: "2026-10-07", inflows: "40000.00", outflows: "0.00", closing: "80000.00" },
    { date: "2026-10-08", inflows: "0.00", outflows: "0.00", closing: "80000.00" },
    { date: "2026-10-09", inflows: "15000.00", outflows: "70000.00", closing: "25000.00" },
  ],
  movements: [
    { record_type: "obligation", record_id: "BILL-001", counterparty: "Office Landlord", direction: "outflow", amount: "10000.00", effective_date: "2026-10-06", assumption_origin: "baseline" },
    { record_type: "invoice", record_id: "INV-001", counterparty: "Customer A", direction: "inflow", amount: "40000.00", effective_date: "2026-10-07", assumption_origin: "baseline" },
    { record_type: "invoice", record_id: "INV-002", counterparty: "Customer B", direction: "inflow", amount: "15000.00", effective_date: "2026-10-09", assumption_origin: "baseline" },
    { record_type: "obligation", record_id: "PAY-001", counterparty: "Staff Payroll", direction: "outflow", amount: "70000.00", effective_date: "2026-10-09", assumption_origin: "baseline" },
  ],
  beyond_horizon: [],
  unresolved: [],
};

export const forecastEnvelope: Envelope<CashflowFacts> = {
  status: "ok",
  tool: "get_cashflow",
  dataset_version: "demo-v1",
  as_of_date: "2026-10-05",
  currency: "INR",
  facts: baselineFacts,
  evidence,
  warnings: [],
  error: null,
};

export const scenarioFacts: SimulationFacts = {
  invoice_id: "INV-001",
  customer_name: "Customer A",
  delay_days: 14,
  original_date: "2026-10-07",
  shifted_date: "2026-10-21",
  shifted_amount: "40000.00",
  receipt_within_horizon: false,
  horizon_end: "2026-10-09",
  baseline: { opening_cash: "50000.00", closing_cash: "25000.00", total_inflows: "55000.00", total_outflows: "80000.00", minimum_balance: "25000.00", minimum_date: "2026-10-09", first_negative_date: null, shortfall_below_zero: "0.00" },
  scenario: { opening_cash: "50000.00", closing_cash: "-15000.00", total_inflows: "15000.00", total_outflows: "80000.00", minimum_balance: "-15000.00", minimum_date: "2026-10-09", first_negative_date: "2026-10-09", shortfall_below_zero: "15000.00" },
  difference_from_baseline: "-40000.00",
  daily: [
    { date: "2026-10-05", baseline_closing: "50000.00", scenario_closing: "50000.00", difference: "0.00" },
    { date: "2026-10-06", baseline_closing: "40000.00", scenario_closing: "40000.00", difference: "0.00" },
    { date: "2026-10-07", baseline_closing: "80000.00", scenario_closing: "40000.00", difference: "-40000.00" },
    { date: "2026-10-08", baseline_closing: "80000.00", scenario_closing: "40000.00", difference: "-40000.00" },
    { date: "2026-10-09", baseline_closing: "25000.00", scenario_closing: "-15000.00", difference: "-40000.00" },
  ],
  scenario_movements: baselineFacts.movements.filter((m) => m.record_id !== "INV-001"),
  scenario_beyond_horizon: [{ ...baselineFacts.movements[1], effective_date: "2026-10-21", assumption_origin: "scenario:sim-INV-001-14d" }],
  unresolved: [],
};

export const invoices: InvoiceFact[] = [
  { invoice_id: "INV-001", customer_name: "Customer A", total_amount: "40000.00", settled_before_as_of: "0.00", remaining_amount: "40000.00", due_date: "2026-10-07", expected_receipt_date: "2026-10-07", status: "open", currency: "INR", overdue: false },
  { invoice_id: "INV-002", customer_name: "Customer B", total_amount: "15000.00", settled_before_as_of: "0.00", remaining_amount: "15000.00", due_date: "2026-10-09", expected_receipt_date: "2026-10-09", status: "open", currency: "INR", overdue: false },
];

export const chatScenarioResponse: ChatResponse = {
  status: "ok",
  answer: "Short answer: no. If Customer A (INV-001) pays 14 days late, closing cash on 9 October 2026: INR -15,000.00 versus INR 25,000.00 in the baseline.",
  mode: "mock",
  model_id: "mock-rule-based-planner",
  tool_trace: [{ tool: "simulate_payment_delay", arguments: { invoice_id: "INV-001", delay_days: 14, horizon_end: "2026-10-09" }, status: "ok", error_code: null, duration_ms: 1.2 }],
  tool_results: [{ ...forecastEnvelope, tool: "simulate_payment_delay", facts: scenarioFacts as unknown as Record<string, unknown> }],
  evidence,
  warnings: ["The delayed receipt falls after the horizon end, so it is not counted."],
  error: null,
  grounded: true,
  usage: {},
  session: { session_id: "s1", business_id: "demo-business", dataset_version: "demo-v1", horizon_end: "2026-10-09", active_scenario: { invoice_id: "INV-001", delay_days: 14 }, turns: 1 },
  session_id: "s1",
  dataset_version: "demo-v1",
  as_of_date: "2026-10-05",
  currency: "INR",
  simulation_label: "Simulated Alexa+ experience with synthetic demo data",
};

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

/** Minimal fetch router for the golden dashboard. */
export function mockFetch(overrides: Record<string, (init?: RequestInit) => Response | Promise<Response>> = {}) {
  return async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    const path = url.replace(/^https?:\/\/[^/]+/, "");
    const key = Object.keys(overrides).find((k) => path.startsWith(k));
    if (key) return overrides[key](init);
    if (path.startsWith("/api/state")) return jsonResponse(appState);
    if (path.startsWith("/api/forecast")) return jsonResponse(forecastEnvelope);
    if (path.startsWith("/api/invoices")) return jsonResponse({ ...forecastEnvelope, tool: "list_open_invoices", facts: { invoices, total_outstanding: "55000.00" } });
    if (path.startsWith("/api/scenarios")) return jsonResponse({ status: "ok", scenarios: [] });
    if (path.startsWith("/api/chat")) return jsonResponse(chatScenarioResponse);
    return jsonResponse({ status: "error", error: { code: "not_found", message: `no mock for ${path}` } }, 404);
  };
}
