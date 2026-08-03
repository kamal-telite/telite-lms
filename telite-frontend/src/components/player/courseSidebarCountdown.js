export function shouldShowSectionCountdown({
  isSectionLocked,
  isSectionCompleted,
  minimumTimeSeconds,
  timeSpentSeconds,
}) {
  if (!minimumTimeSeconds || minimumTimeSeconds <= 0) return false;
  if (isSectionCompleted) return false;
  if (!isSectionLocked) return false;
  if (timeSpentSeconds >= minimumTimeSeconds) return false;

  return true;
}
