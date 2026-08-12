export function formatDuration(durationSeconds: number) {
  const totalMinutes = Math.floor(Math.max(0, durationSeconds) / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  if (hours > 0) {
    return `${hours} hr ${minutes} min`;
  }

  return `${minutes} min`;
}

export function formatPlayerTime(durationSeconds: number) {
  if (!Number.isFinite(durationSeconds) || durationSeconds < 0) {
    return "0:00";
  }

  const totalSeconds = Math.floor(durationSeconds);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  return hours > 0
    ? `${hours}:${minutes.toString().padStart(2, "0")}:${seconds
        .toString()
        .padStart(2, "0")}`
    : `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

export function formatCompactNumber(value: number) {
  const absoluteValue = Math.abs(value);

  if (absoluteValue >= 1_000_000) {
    return `${formatSingleDecimal(value / 1_000_000)}M`;
  }

  if (absoluteValue >= 1_000) {
    return `${formatSingleDecimal(value / 1_000)}K`;
  }

  return Math.round(value).toString();
}

function formatSingleDecimal(value: number) {
  return Number.isInteger(value) ? value.toString() : value.toFixed(1);
}

export function getProgressPercentage(
  progressSeconds: number,
  durationSeconds: number,
) {
  if (durationSeconds <= 0) {
    return 0;
  }

  return Math.min(100, Math.max(0, (progressSeconds / durationSeconds) * 100));
}
