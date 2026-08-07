export function formatDateShort(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    if (Number.isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString("it-IT", {
      day: "2-digit",
      month: "short",
    });
  } catch {
    return dateStr;
  }
}

export function formatDateFull(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    if (Number.isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString("it-IT", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}

export function formatDuration(minutes: number): string {
  const mins = Number(minutes) || 0;
  const h = Math.floor(mins / 60);
  const m = Math.floor(mins % 60);
  const s = Math.floor((mins % 1) * 60);
  if (h > 0) {
    return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  }
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function formatNumber(value: number, decimals = 1): string {
  if (value == null || Number.isNaN(value)) return "—";
  return Number(value).toFixed(decimals);
}

export function formatPct(value: number, showSign = true): string {
  if (value == null || Number.isNaN(value)) return "—";
  const sign = showSign && value > 0 ? "+" : "";
  return `${sign}${Number(value).toFixed(1)}%`;
}

export function unitLabel(unit?: string): string {
  return unit ? `(${unit})` : "";
}
