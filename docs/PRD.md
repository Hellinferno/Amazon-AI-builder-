# Product requirements

Status: proposed MVP specification, 28 September 2026.

## User and problem

A small-business owner needs to understand whether expected customer receipts will cover upcoming bills and payroll. The product connects a conversational question to inspectable records and deterministic scenario calculations.

Primary question: “Can we cover Friday's payroll if customer A pays two weeks late?”

## MVP scope

| Capability | Acceptance condition |
| --- | --- |
| Import sample records | Valid CSVs load; invalid records return row errors without partial writes |
| Baseline forecast | Opening cash plus scheduled future inflows minus outflows yields a dated balance series |
| Delayed-payment scenario | User-selected receipt moves to a new date; baseline remains unchanged |
| Evidence | Each amount is linked to an input record or labeled assumption |
| Conversation | Follow-up questions retain scenario context within the selected business |
| Saved scenario | Explicit save survives reload and identifies the dataset version |
| Reminder draft | Produces editable text for review; does not send |
| AWS integration | At least one successful real Bedrock-powered workflow is recorded for submission |
| Demonstration | Synthetic dataset, repeatable reset, clear simulation label |

## Product experience

Show a sample-business selector, dataset/as-of label, cash summary, baseline/scenario comparison, supporting records, and chat. Responses should lead with the result and then the cause. Resolve ambiguous invoice names before changing a scenario. Provide text interaction first; voice is stretch scope.

Persist a scenario only when the user selects Save. When a dataset is reimported, warn that old scenarios use a different dataset version and require recomputation. Show a clear model-service error while preserving access to the calculation results.

## Explicit scope limits

Single business context per workspace and INR-only MVP. No foreign-exchange conversion, bank synchronization, payments, automatic messages, investment recommendations, statutory compliance claims, GST filing, or credit scoring. No custom model training. Expense anomaly detection, invoice OCR, MCP, and voice are later options.

## Success evidence

Demonstrate correct fixture calculations, a real tool-backed conversation, scenario isolation, reliable reset, clean setup instructions, and a coherent under-three-minute video. Capture task completion and failures from a small set of representative prompts; label the sample size and avoid broad accuracy claims.

## Release gate

All mandatory acceptance conditions must pass on the tagged submission version. Remove unsupported claims from Devpost and the demo. Optional features can be cut according to ROADMAP.md.
