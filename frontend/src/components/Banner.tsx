import type { AppState } from "../types";

interface Props {
  state: AppState | null;
  backendError: string | null;
}

export function Banner({ state, backendError }: Props) {
  const mode = state?.mode ?? null;
  return (
    <div className="banner" role="status">
      <strong>Simulated Alexa+ experience.</strong>
      <span>Synthetic demo data only; nothing here is a real business or a real bank balance.</span>
      {backendError ? (
        <span className="badge error">
          <span className="dot" aria-hidden="true" /> Backend unreachable
        </span>
      ) : mode === "live" ? (
        <span className="badge live" title={state?.model_id}>
          <span className="dot" aria-hidden="true" /> Live model: {state?.model_id}
        </span>
      ) : mode === "mock" ? (
        <span className="badge mock" title="No model is called. A rule-based planner drives the same tools.">
          <span className="dot" aria-hidden="true" /> Mock mode: no model call
        </span>
      ) : null}
      {state?.storage_backend && <span className="badge">Storage: {state.storage_backend}</span>}
    </div>
  );
}
