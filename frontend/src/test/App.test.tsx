import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { chatScenarioResponse, jsonResponse, mockFetch } from "./fixtures";

describe("App", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(mockFetch()));
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows the simulation label, mock badge, as-of date and golden baseline", async () => {
    render(<App />);
    expect(screen.getByText(/Simulated Alexa\+ experience/)).toBeInTheDocument();
    await screen.findByText(/Mock mode: no model call/);
    expect(await screen.findByText("5 October 2026 (Asia/Kolkata)")).toBeInTheDocument();
    const tiles = screen.getByLabelText("Cash summary");
    expect(within(tiles).getByText("INR 50,000.00")).toBeInTheDocument();
    expect(within(tiles).getAllByText("INR 25,000.00").length).toBeGreaterThanOrEqual(1); // closing and lowest balance
    expect(within(tiles).getByText("None")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "End-of-day cash balance" })).toBeInTheDocument();
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText(/Draft only|draft a reminder/)).toBeInTheDocument();
  });

  it("sends a question, shows the grounded answer, and switches the dashboard to the scenario", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("5 October 2026 (Asia/Kolkata)");
    await user.type(screen.getByLabelText("Your question"), "What if Customer A pays two weeks late?");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByText(/Short answer: no\./)).toBeInTheDocument();
    expect(screen.getByText("figures grounded in tools")).toBeInTheDocument();
    expect(screen.getByText("simulate_payment_delay")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Baseline vs scenario" })).toBeInTheDocument();
    const tiles = screen.getByLabelText("Cash summary");
    expect(within(tiles).getAllByText("INR -15,000.00").length).toBeGreaterThanOrEqual(1); // closing and lowest balance
    expect(within(tiles).getByText("9 October 2026")).toBeInTheDocument();
    expect(screen.getByText(/shortfall INR 15,000.00/)).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Scenario closing" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save scenario" })).toBeInTheDocument();
    const chatCall = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls.find((c) => String(c[0]).includes("/api/chat"));
    expect(JSON.parse((chatCall![1] as RequestInit).body as string)).toEqual({ message: "What if Customer A pays two weeks late?", session_id: null, horizon_end: null });
  });

  it("shows a clear error when the assistant fails and keeps the figures", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(mockFetch({ "/api/chat": () => jsonResponse({ status: "error", error: { code: "provider_timeout", message: "the model service did not answer in time" } }, 503) })),
    );
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("5 October 2026 (Asia/Kolkata)");
    await user.type(screen.getByLabelText("Your question"), "hello");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/did not answer in time \(provider_timeout\)/);
    expect(screen.getByText(/figures on this page are unaffected/)).toBeInTheDocument();
    expect(within(screen.getByLabelText("Cash summary")).getAllByText("INR 25,000.00").length).toBeGreaterThanOrEqual(1);
  });

  it("explains when the backend is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("Failed to fetch"); }));
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/Could not reach the backend/);
    expect(screen.getByText("Backend unreachable")).toBeInTheDocument();
  });

  it("marks the reminder draft as not sent and lets the user edit it", async () => {
    const draft = { ...chatScenarioResponse, answer: "Here is a draft.", tool_trace: [{ tool: "draft_collection_reminder", arguments: {}, status: "ok", error_code: null, duration_ms: 1 }], tool_results: [{ status: "ok", tool: "draft_collection_reminder", dataset_version: "demo-v1", as_of_date: "2026-10-05", currency: "INR", facts: { draft: { invoice_id: "INV-001", customer_name: "Customer A", amount_outstanding: "40000.00", currency: "INR", due_date: "2026-10-07", days_overdue: -2, tone: "firm", subject: "Payment reminder: invoice INV-001 (INR 40,000.00)", body: "Dear Customer A, ...", status: "draft_not_sent", sent: false } }, evidence: [], warnings: ["This is a draft for review. Nothing has been sent."], error: null }] };
    vi.stubGlobal("fetch", vi.fn(mockFetch({ "/api/chat": () => jsonResponse(draft) })));
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("5 October 2026 (Asia/Kolkata)");
    await user.click(screen.getByRole("button", { name: "Draft a firm reminder for Customer A" }));
    expect(await screen.findByText(/Draft only — not sent\./)).toBeInTheDocument();
    const body = screen.getByLabelText("Message") as HTMLTextAreaElement;
    expect(body.value).toContain("Dear Customer A");
    await user.type(body, " Edited.");
    await waitFor(() => expect(body.value).toContain("Edited."));
  });
});
