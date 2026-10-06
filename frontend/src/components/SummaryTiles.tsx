import { isNegative, longDate, money } from "../format";
import type { CashflowFacts, SimulationFacts } from "../types";

interface Props {
  baseline: CashflowFacts | null;
  scenario: SimulationFacts | null;
  currency: string;
}

export function SummaryTiles({ baseline, scenario, currency }: Props) {
  if (!baseline) return null;
  const s = scenario?.scenario ?? null;
  const main = s ?? baseline;
  const label = s ? "Scenario" : "Baseline";
  return (
    <div className="tiles" aria-label="Cash summary">
      <div className="tile">
        <div className="label">Opening cash</div>
        <div className={`value${isNegative(baseline.opening_cash) ? " negative" : ""}`}>{money(baseline.opening_cash, currency)}</div>
        <div className="meta">start of the as-of date</div>
      </div>
      <div className="tile">
        <div className="label">Closing cash on {longDate(baseline.horizon_end)}</div>
        <div className={`value${isNegative(main.closing_cash) ? " negative" : ""}`}>{money(main.closing_cash, currency)}</div>
        <div className="meta">
          {s ? (
            <>
              <span className="swatch swatch-2" aria-hidden="true" />scenario; baseline {money(baseline.closing_cash, currency)}
            </>
          ) : (
            <>
              <span className="swatch swatch-1" aria-hidden="true" />baseline
            </>
          )}
        </div>
      </div>
      <div className="tile">
        <div className="label">Lowest end-of-day balance</div>
        <div className={`value${isNegative(main.minimum_balance) ? " negative" : ""}`}>{money(main.minimum_balance, currency)}</div>
        <div className="meta">
          {label} on {longDate(main.minimum_date)}
        </div>
      </div>
      <div className="tile">
        <div className="label">First negative day</div>
        <div className={`value${main.first_negative_date ? " negative" : ""}`}>
          {main.first_negative_date ? longDate(main.first_negative_date) : "None"}
        </div>
        <div className="meta">
          {main.first_negative_date ? `shortfall ${money(main.shortfall_below_zero, currency)}` : `${label}: every day stays at or above zero`}
        </div>
      </div>
    </div>
  );
}
