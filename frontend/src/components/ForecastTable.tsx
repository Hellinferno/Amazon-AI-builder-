import { isNegative, longDate, money, shortDate, weekday } from "../format";
import type { CashflowFacts, SimulationFacts } from "../types";

interface Props {
  baseline: CashflowFacts;
  scenario: SimulationFacts | null;
  currency: string;
}

export function ForecastTable({ baseline, scenario, currency }: Props) {
  const scenarioByDate = new Map(scenario?.daily.map((d) => [d.date, d]) ?? []);
  return (
    <div className="table-wrap">
      <table>
        <caption>
          End-of-day balances from {longDate(baseline.daily[0]?.date)} to {longDate(baseline.horizon_end)} in {currency}.
          {scenario ? ` Scenario: ${scenario.customer_name} (${scenario.invoice_id}) pays ${scenario.delay_days} days late.` : ""}
        </caption>
        <thead>
          <tr>
            <th scope="col">Date</th>
            <th scope="col" className="num">Receipts</th>
            <th scope="col" className="num">Payments</th>
            <th scope="col" className="num">Baseline closing</th>
            {scenario && (
              <>
                <th scope="col" className="num">Scenario closing</th>
                <th scope="col" className="num">Difference</th>
              </>
            )}
          </tr>
        </thead>
        <tbody>
          {baseline.daily.map((d) => {
            const s = scenarioByDate.get(d.date);
            const highlight = s ? s.scenario_closing !== s.baseline_closing : false;
            return (
              <tr key={d.date} className={highlight ? "highlight" : undefined}>
                <th scope="row">
                  {weekday(d.date)} {shortDate(d.date)}
                </th>
                <td className="num">{d.inflows === "0.00" ? "–" : money(d.inflows, "")}</td>
                <td className="num">{d.outflows === "0.00" ? "–" : money(d.outflows, "")}</td>
                <td className={`num${isNegative(d.closing) ? " negative" : ""}`}>{money(d.closing, "")}</td>
                {scenario && (
                  <>
                    <td className={`num${s && isNegative(s.scenario_closing) ? " negative" : ""}`}>{s ? money(s.scenario_closing, "") : "–"}</td>
                    <td className={`num${s && isNegative(s.difference) ? " negative" : ""}`}>{s ? money(s.difference, "") : "–"}</td>
                  </>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
