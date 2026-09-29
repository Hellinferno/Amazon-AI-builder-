# Roadmap and deadlines

Prepared 28 September 2026. **All working deadlines below are India Standard Time (IST, UTC+05:30).** These are proposed delivery targets, not completed work or scheduled reminders. Adjust task scope to available study/work time; do not silently move the final deadline.

## Key dates

- Internal submission target: **22 October 2026, 8:00 p.m. IST**.
- Official submission deadline: **24 October 2026, 12:30 a.m. IST** (23 October, noon PDT).
- Optional credit-request cutoff: **22 October 2026, 12:30 a.m. IST** (21 October, noon PDT), while supplies last. User has deferred this request; if needed, aim to apply by 20 October, 8:00 p.m. IST.
- Judging: 9–20 November, Pacific time; preserve reviewer access through **21 November, 1:30 a.m. IST**, corresponding to the stated judging end at noon PST on 20 November.

Official dates must be rechecked before submission using [the rules](https://amazonappdev2026.devpost.com/rules).

## Milestone gates

| Gate | Complete by (IST) | What must be done | Evidence |
| --- | --- | --- | --- |
| M0 Setup | 30 Sep, 10 p.m. | Docs installed; repo, venv, package structure, synthetic fixture designed | Interpreter path; Git status; fixture review |
| M1 Accounting engine | 6 Oct, 10 p.m. | Imports, baseline, delay scenario, evidence IDs | Automated financial and validation tests |
| M2 Conversation | 12 Oct, 10 p.m. | Bedrock + tools + usable web conversation | Real integration trace and working UI |
| M3 Product complete | 17 Oct, 10 p.m. | Persistence, evidence cards, draft, reset, errors | End-to-end demo rehearsal |
| M4 Release candidate | 21 Oct, 10 p.m. | Tests, clean setup, docs, video, submission text | Frozen commit and evidence checklist |
| M5 Submit | 22 Oct, 8 p.m. | Devpost submitted; repository/video accessible | Submission confirmation checked by Ravi |

## Daily implementation targets

| Date | Target time IST | Deliverable / finish condition |
| --- | --- | --- |
| 28 Sep | 11 p.m. | Save and read docs; confirm project directory |
| 29 Sep | 10 p.m. | Initialize backend layout, money/date types, tests, Git ignore rules |
| 30 Sep | 10 p.m. | Create deterministic sample fixture and schema validation |
| 1 Oct | 10 p.m. | Implement atomic CSV import and source-row references |
| 2 Oct | 10 p.m. | Implement dated baseline forecast and running balance |
| 3 Oct | 10 p.m. | Implement immutable delayed-receipt scenario |
| 4 Oct | 10 p.m. | Implement overdue reporting and missing-date warnings |
| 5 Oct | 10 p.m. | Cover boundaries, partial payments, duplicate IDs, invalid imports |
| 6 Oct | 10 p.m. | Pass M1; document engine usage; fix defects before AI integration |
| 7 Oct | 10 p.m. | Verify AWS account/model access; complete one real Bedrock call |
| 8 Oct | 10 p.m. | Connect typed read-only calculation tools through Strands |
| 9 Oct | 10 p.m. | Implement follow-up context and structured evidence response |
| 10 Oct | 10 p.m. | Build React shell, sample loading, chat, loading/error states |
| 11 Oct | 10 p.m. | Connect UI to backend; show baseline and scenario results |
| 12 Oct | 10 p.m. | Pass M2 with real model/tool trace; freeze core feature list |
| 13 Oct | 10 p.m. | Save/load scenario with dataset version; integrate S3/DynamoDB if access ready |
| 14 Oct | 10 p.m. | Add editable reminder draft and source-record panels |
| 15 Oct | 10 p.m. | Improve accessibility, keyboard flow, date/currency labels |
| 16 Oct | 10 p.m. | Test missing data, timeout, import isolation, and prompt injection |
| 17 Oct | 10 p.m. | Pass M3; record full rehearsal; cut unfinished stretch features |
| 18 Oct | 10 p.m. | Run calculation and integration evaluation; record actual results |
| 19 Oct | 10 p.m. | Reproduce from clean checkout; pin dependencies; complete README |
| 20 Oct | 8 p.m. | Optional credit decision if required; otherwise continue without request |
| 20 Oct | 10 p.m. | Finish feedback, genuine friction entries, draft Devpost text |
| 21 Oct | 10 p.m. | Record final video; freeze release; pass all M4 checks |
| 22 Oct | 6 p.m. | Verify links, reviewer access, track selections, English materials |
| 22 Oct | 8 p.m. | Ravi submits and verifies confirmation; M5 complete |
| 23 Oct | 8 p.m. | Contingency only: resolve submission/access errors before official cutoff |

## Working-session pattern

Choose a study-compatible block each day. Suggested allocation: 10 minutes reviewing the next task, 60–90 minutes implementing, 20–30 minutes verifying, and 10 minutes updating TASKS.md and the friction log. Some milestones may need longer sessions. If time is insufficient, reduce features using the rules below.

## If behind schedule

1. Preserve calculations, one real AWS workflow, evidence, reproducible setup, and the video.
2. Drop voice, OCR, and MCP first. They are not required for our chosen simulation route.
3. Keep local persistence if cloud storage integration jeopardizes the release; document actual AWS services used.
4. If AWS access is blocked, continue engine/UI work with visibly mocked responses. Resolve a real AWS integration before claiming AWS Builder participation.
5. Freeze features on 17 October; use later time for defects and submission quality.
6. If M1 is late, prioritize its correctness before adding agent complexity.

## Status updates

For each missed or passed gate, record actual time, evidence, remaining defects, and revised scope in TASKS.md. No milestones in this schedule are automatically marked complete.
