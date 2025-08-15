export function parseDuration(duration) {
  const match = duration.match(/^(\d+)([hm])$/);
  if (!match) {
    throw new Error('Invalid duration format. Use: 1h, 30m, etc.');
  }
  
  const [, value, unit] = match;
  const minutes = unit === 'h' ? parseInt(value) * 60 : parseInt(value);
  
  return minutes;
}

export function formatDuration(minutes) {
  if (minutes < 60) {
    return `${minutes}m`;
  } else {
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return remainingMinutes > 0 ? `${hours}h${remainingMinutes}m` : `${hours}h`;
  }
}

export function formatTimestamp(timestamp) {
  return new Date(timestamp).toISOString();
}

export function hoursToMinutes(hours) {
  return hours * 60;
}

export function minutesToSeconds(minutes) {
  return minutes * 60;
}

export function calculateTimeSteps(durationMinutes, stepMinutes = 1) {
  return Math.ceil(durationMinutes / stepMinutes);
}