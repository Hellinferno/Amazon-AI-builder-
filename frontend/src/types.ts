// Shapes returned by the backend (docs/TOOLS_AND_API.md). Money is a decimal string.

export interface Evidence {
  record_type: "invoice" | "obligation";
  record_id: string;
  source_file_id: string;
  row_number: number;
}

export interface ApiError {
  code: string;
  message: string;
  field?: string | null;
  details?: unknown;
}

export interface Envelope<F = Record<string, unknown>> {
  status: "ok" | "error";
  tool: string | null;
  dataset_version: string | null;
  as_of_date: string | null;
  currency: string | null;
  facts: F;
  evidence: Evidence[];
  warnings: string[];
  error: ApiError | null;
}

export interface DailyBalance {
  date: string;
  inflows: string;
  outflows: string;
  closing: string;
}

export interface MovementFact {
  record_type: "invoice" | "obligation";
  record_id: string;
  counterparty: string;
  direction: "inflow" | "outflow";
  amount: string;
  effective_date: string;
  assumption_origin: string;
}

export interface UnresolvedFact {
  record_type: "invoice" | "obligation";
  record_id: string;
  counterparty: string;
  direction: "inflow" | "outflow";
  amount: string;
  expected_date: string | null;
  reason: string;
}

export interface ForecastSummary {
  opening_cash: string;
  closing_cash: string;
  total_inflows: string;
  total_outflows: string;
  minimum_balance: string;
  minimum_date: string;
  first_negative_date: string | null;
  shortfall_below_zero: string;
}

export interface CashflowFacts extends ForecastSummary {
  horizon_end: string;
  daily: DailyBalance[];
  movements: MovementFact[];
  beyond_horizon: MovementFact[];
  unresolved: UnresolvedFact[];
}

export interface ScenarioDay {
  date: string;
  baseline_closing: string;
  scenario_closing: string;
  difference: string;
}

export interface SimulationFacts {
  invoice_id: string;
  customer_name: string;
  delay_days: number;
  original_date: string;
  shifted_date: string;
  shifted_amount: string;
  receipt_within_horizon: boolean;
  horizon_end: string;
  baseline: ForecastSummary;
  scenario: ForecastSummary;
  difference_from_baseline: string;
  daily: ScenarioDay[];
  scenario_movements: MovementFact[];
  scenario_beyond_horizon: MovementFact[];
  unresolved: UnresolvedFact[];
}

export interface InvoiceFact {
  invoice_id: string;
  customer_name: string;
  total_amount: string;
  settled_before_as_of: string;
  remaining_amount: string;
  due_date: string;
  expected_receipt_date: string | null;
  status: string;
  currency: string;
  overdue: boolean;
}

export interface ObligationFact {
  obligation_id: string;
  payee_name: string;
  category: string;
  total_amount: string;
  settled_before_as_of: string;
  remaining_amount: string;
  due_date: string;
  expected_payment_date: string | null;
  status: string;
  currency: string;
}

export interface RecordFacts {
  record_type: "invoice" | "obligation";
  record: InvoiceFact | ObligationFact;
  source: Evidence;
}

export interface ReminderDraft {
  invoice_id: string;
  customer_name: string;
  amount_outstanding: string;
  currency: string;
  due_date: string;
  days_overdue: number;
  tone: "friendly" | "firm";
  subject: string;
  body: string;
  status: "draft_not_sent";
  sent: false;
}

export interface ReminderFacts {
  draft: ReminderDraft;
  invoice: InvoiceFact;
}

export interface ToolTrace {
  tool: string;
  arguments: Record<string, unknown>;
  status: "ok" | "error";
  error_code: string | null;
  duration_ms: number;
}

export interface SessionInfo {
  session_id: string;
  business_id: string;
  dataset_version: string;
  horizon_end: string;
  active_scenario: { invoice_id: string; delay_days: number } | null;
  turns: number;
}

export interface ChatResponse {
  status: "ok" | "error";
  answer: string;
  mode: "mock" | "live";
  model_id: string;
  tool_trace: ToolTrace[];
  tool_results: Envelope[];
  evidence: Evidence[];
  warnings: string[];
  error: ApiError | null;
  grounded: boolean;
  usage: Record<string, number>;
  session: SessionInfo;
  session_id: string;
  dataset_version: string;
  as_of_date: string;
  currency: string;
  simulation_label: string;
}

export interface DatasetInfo {
  dataset_version: string;
  as_of_date: string;
  currency: string;
  timezone: string;
  opening_cash: string;
  invoice_count: number;
  obligation_count: number;
  default_horizon_end: string;
  fingerprint: string;
}

export interface AppState {
  mode: "mock" | "live";
  model_id: string;
  simulation_label: string;
  storage_backend: string;
  business_id: string;
  business_name: string;
  demo_reset_enabled: boolean;
  dataset: DatasetInfo | null;
}

export interface SavedScenario {
  scenario_id: string;
  business_id: string;
  dataset_version: string;
  invoice_id: string;
  delay_days: number;
  name: string;
  created_at: string;
  stale: boolean;
  current_dataset_version: string | null;
}

export interface ImportIssue {
  file: string;
  row_number: number | null;
  field: string | null;
  reason: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  response?: ChatResponse;
  failed?: boolean;
}
