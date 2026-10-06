import { useId, useMemo, useState } from "react";
import { longDate, money, shortDate, shortMoney, toNumber } from "../format";

export interface ChartPoint {
  date: string;
  baseline: string;
  scenario?: string;
}

interface Props {
  points: ChartPoint[];
  currency: string;
  scenarioLabel?: string;
}

const W = 640;
const H = 240;
const PAD = { top: 18, right: 86, bottom: 28, left: 56 };

function ticks(min: number, max: number, count = 4): number[] {
  if (max === min) return [min];
  const span = max - min;
  const raw = span / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? mag;
  const out: number[] = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) out.push(Math.round(v));
  return out;
}

export function BalanceChart({ points, currency, scenarioLabel }: Props) {
  const [hover, setHover] = useState<number | null>(null);
  const titleId = useId();
  const descId = useId();
  const hasScenario = points.some((p) => p.scenario != null);

  const { xs, yScale, yTicks, zeroY } = useMemo(() => {
    const values = points.flatMap((p) => [toNumber(p.baseline), ...(p.scenario != null ? [toNumber(p.scenario)] : [])]);
    let min = Math.min(0, ...values);
    let max = Math.max(0, ...values);
    if (min === max) max = min + 1;
    const padV = (max - min) * 0.08;
    min -= padV;
    max += padV;
    const innerW = W - PAD.left - PAD.right;
    const innerH = H - PAD.top - PAD.bottom;
    const n = points.length;
    const xs = points.map((_, i) => PAD.left + (n === 1 ? innerW / 2 : (i / (n - 1)) * innerW));
    const yScale = (v: number) => PAD.top + ((max - v) / (max - min)) * innerH;
    return { xs, yScale, yTicks: ticks(min, max), zeroY: yScale(0) };
  }, [points]);

  if (points.length === 0) return null;

  const path = (key: "baseline" | "scenario") =>
    points
      .map((p, i) => {
        const v = p[key];
        return v == null ? null : `${i === 0 ? "M" : "L"}${xs[i].toFixed(1)},${yScale(toNumber(v)).toFixed(1)}`;
      })
      .filter(Boolean)
      .join(" ");

  const last = points[points.length - 1];
  const summary = hasScenario
    ? `Line chart of end-of-day cash from ${longDate(points[0].date)} to ${longDate(last.date)}. Baseline ends at ${money(last.baseline, currency)}; the scenario ends at ${money(last.scenario ?? null, currency)}. The table below lists every day.`
    : `Line chart of end-of-day cash from ${longDate(points[0].date)} to ${longDate(last.date)}, ending at ${money(last.baseline, currency)}. The table below lists every day.`;

  const labelStep = Math.max(1, Math.ceil(points.length / 8));
  const hovered = hover == null ? null : points[hover];

  return (
    <div className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-labelledby={titleId} aria-describedby={descId}>
        <title id={titleId}>End-of-day cash balance</title>
        <desc id={descId}>{summary}</desc>
        {yTicks.map((t) => (
          <g key={t}>
            <line className={t === 0 ? "zero-line" : "grid-line"} x1={PAD.left} x2={W - PAD.right} y1={yScale(t)} y2={yScale(t)} />
            <text className="axis-label" x={PAD.left - 8} y={yScale(t) + 4} textAnchor="end">
              {shortMoney(String(t))}
            </text>
          </g>
        ))}
        {yTicks.every((t) => t !== 0) && <line className="zero-line" x1={PAD.left} x2={W - PAD.right} y1={zeroY} y2={zeroY} />}
        {points.map((p, i) =>
          i % labelStep === 0 || i === points.length - 1 ? (
            <text key={p.date} className="axis-label" x={xs[i]} y={H - 8} textAnchor="middle">
              {shortDate(p.date)}
            </text>
          ) : null,
        )}
        <path className="line-1" d={path("baseline")} />
        {hasScenario && <path className="line-2" d={path("scenario")} />}
        {points.map((p, i) => (
          <g key={p.date}>
            <circle className="dot-1" cx={xs[i]} cy={yScale(toNumber(p.baseline))} r={hover === i ? 5 : 3.5} />
            {p.scenario != null && <circle className="dot-2" cx={xs[i]} cy={yScale(toNumber(p.scenario))} r={hover === i ? 5 : 3.5} />}
          </g>
        ))}
        <text className="end-label" x={xs[xs.length - 1] + 8} y={yScale(toNumber(last.baseline)) + 4}>
          Baseline {shortMoney(last.baseline)}
        </text>
        {hasScenario && last.scenario != null && (
          <text className="end-label" x={xs[xs.length - 1] + 8} y={yScale(toNumber(last.scenario)) + (toNumber(last.scenario) === toNumber(last.baseline) ? 16 : 4)}>
            Scenario {shortMoney(last.scenario)}
          </text>
        )}
        {hovered && <line className="crosshair" x1={xs[hover!]} x2={xs[hover!]} y1={PAD.top} y2={H - PAD.bottom} />}
        {points.map((p, i) => {
          const left = i === 0 ? PAD.left : (xs[i - 1] + xs[i]) / 2;
          const right = i === points.length - 1 ? W - PAD.right : (xs[i] + xs[i + 1]) / 2;
          return (
            <rect
              key={p.date}
              className="hit"
              x={left}
              y={PAD.top}
              width={Math.max(1, right - left)}
              height={H - PAD.top - PAD.bottom}
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
              onFocus={() => setHover(i)}
              onBlur={() => setHover(null)}
              tabIndex={0}
              aria-label={`${longDate(p.date)}: baseline ${money(p.baseline, currency)}${p.scenario != null ? `, scenario ${money(p.scenario, currency)}` : ""}`}
            />
          );
        })}
      </svg>
      {hovered && (
        <div
          className="tooltip"
          style={{ left: `${(xs[hover!] / W) * 100}%`, top: 0, transform: xs[hover!] > W * 0.6 ? "translateX(-105%)" : "translateX(8px)" }}
        >
          <div className="t-date">{longDate(hovered.date)}</div>
          <div className="t-row">
            <span>Baseline</span>
            <span>{money(hovered.baseline, currency)}</span>
          </div>
          {hovered.scenario != null && (
            <div className="t-row">
              <span>Scenario</span>
              <span>{money(hovered.scenario, currency)}</span>
            </div>
          )}
        </div>
      )}
      <div className="legend" aria-hidden="true">
        <span>
          <span className="key" /> Baseline
        </span>
        {hasScenario && (
          <span>
            <span className="key dashed" /> {scenarioLabel ?? "Scenario"}
          </span>
        )}
      </div>
    </div>
  );
}
