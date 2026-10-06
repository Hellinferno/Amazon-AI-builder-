// Display helpers. Digits are never altered: "40000.00" -> "INR 40,000.00".

export function money(value: string | null | undefined, currency = "INR"): string {
  if (value == null || value === "") return "n/a";
  const negative = value.startsWith("-");
  const [whole, frac = "00"] = value.replace("-", "").split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return `${currency} ${negative ? "-" : ""}${grouped}.${frac.padEnd(2, "0")}`;
}

export function shortMoney(value: string | null | undefined): string {
  if (value == null) return "n/a";
  const n = Number(value);
  if (!Number.isFinite(n)) return value;
  const abs = Math.abs(n);
  const sign = n < 0 ? "-" : "";
  if (abs >= 100_000) return `${sign}${(abs / 100_000).toFixed(abs % 100_000 === 0 ? 0 : 1)}L`;
  if (abs >= 1_000) return `${sign}${(abs / 1_000).toFixed(abs % 1_000 === 0 ? 0 : 1)}k`;
  return `${sign}${abs.toFixed(0)}`;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTHS_LONG = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function parts(iso: string): { d: number; m: number; y: number } {
  const [y, m, d] = iso.split("-").map(Number);
  return { d, m, y };
}

export function longDate(iso: string | null | undefined): string {
  if (!iso) return "no date";
  const { d, m, y } = parts(iso);
  return `${d} ${MONTHS_LONG[m - 1]} ${y}`;
}

export function shortDate(iso: string): string {
  const { d, m } = parts(iso);
  return `${d} ${MONTHS[m - 1]}`;
}

export function weekday(iso: string): string {
  const { d, m, y } = parts(iso);
  return ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][new Date(Date.UTC(y, m - 1, d)).getUTCDay()];
}

export function isNegative(value: string): boolean {
  return value.startsWith("-") && Number(value) < 0;
}

export function toNumber(value: string): number {
  return Number(value);
}
