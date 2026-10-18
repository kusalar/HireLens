/**
 * Centralized Timezone Utility for HireLens AI
 * Default and Canonical Display Timezone: Asia/Kolkata (IST, UTC+05:30)
 */

export const DEFAULT_TIMEZONE = "Asia/Kolkata";
export const IST_LABEL = "IST (UTC+05:30)";

/**
 * Format a date/time string or Date object into a readable IST date string.
 * Example: "20 Oct 2026"
 */
export function formatDateIST(
  dateInput: string | Date | null | undefined,
  options?: Intl.DateTimeFormatOptions
): string {
  if (!dateInput) return "";
  try {
    const d = typeof dateInput === "string" ? new Date(dateInput) : dateInput;
    if (isNaN(d.getTime())) return String(dateInput);

    const defaultOptions: Intl.DateTimeFormatOptions = {
      timeZone: DEFAULT_TIMEZONE,
      day: "numeric",
      month: "short",
      year: "numeric",
      ...options,
    };

    return new Intl.DateTimeFormat("en-IN", defaultOptions).format(d);
  } catch {
    return String(dateInput);
  }
}

/**
 * Format a date/time string or Date object into a readable IST time string.
 * Example: "02:00 PM"
 */
export function formatTimeIST(
  dateInput: string | Date | null | undefined,
  options?: Intl.DateTimeFormatOptions
): string {
  if (!dateInput) return "";
  try {
    const d = typeof dateInput === "string" ? new Date(dateInput) : dateInput;
    if (isNaN(d.getTime())) return String(dateInput);

    const defaultOptions: Intl.DateTimeFormatOptions = {
      timeZone: DEFAULT_TIMEZONE,
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
      ...options,
    };

    return new Intl.DateTimeFormat("en-IN", defaultOptions).format(d);
  } catch {
    return String(dateInput);
  }
}

/**
 * Format a date/time string or Date object into a full IST string with explicit IST indicator.
 * Example: "20 October 2026, 2:00 PM IST"
 */
export function formatDateTimeIST(
  dateInput: string | Date | null | undefined,
  options?: { showIndicator?: boolean }
): string {
  if (!dateInput) return "";
  try {
    const d = typeof dateInput === "string" ? new Date(dateInput) : dateInput;
    if (isNaN(d.getTime())) return String(dateInput);

    const datePart = new Intl.DateTimeFormat("en-IN", {
      timeZone: DEFAULT_TIMEZONE,
      day: "numeric",
      month: "long",
      year: "numeric",
    }).format(d);

    const timePart = new Intl.DateTimeFormat("en-IN", {
      timeZone: DEFAULT_TIMEZONE,
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    }).format(d);

    const indicator = options?.showIndicator !== false ? " IST" : "";
    return `${datePart}, ${timePart}${indicator}`;
  } catch {
    return String(dateInput);
  }
}

/**
 * Format an interview start and end time range with IST (UTC+05:30) indicator.
 * Example: "02:00 PM - 03:00 PM IST (UTC+05:30)"
 */
export function formatInterviewTimeRange(
  startInput: string | Date,
  endInput: string | Date,
  tz: string = DEFAULT_TIMEZONE
): string {
  try {
    const start = typeof startInput === "string" ? new Date(startInput) : startInput;
    const end = typeof endInput === "string" ? new Date(endInput) : endInput;

    const timeOptions: Intl.DateTimeFormatOptions = {
      timeZone: tz || DEFAULT_TIMEZONE,
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    };

    const startTime = new Intl.DateTimeFormat("en-IN", timeOptions).format(start);
    const endTime = new Intl.DateTimeFormat("en-IN", timeOptions).format(end);

    const isIST = !tz || tz === "Asia/Kolkata" || tz === "Asia/Calcutta";
    const label = isIST ? IST_LABEL : tz;

    return `${startTime} - ${endTime} ${label}`;
  } catch {
    return `${startInput} - ${endInput}`;
  }
}

/**
 * Extract YYYY-MM-DD in the target timezone (default Asia/Kolkata) for HTML date pickers.
 * Avoids browser-local day shifting.
 */
export function formatDateForPicker(
  dateInput: string | Date | null | undefined,
  tz: string = DEFAULT_TIMEZONE
): string {
  if (!dateInput) return "";
  try {
    const d = typeof dateInput === "string" ? new Date(dateInput) : dateInput;
    if (isNaN(d.getTime())) return "";

    const formatter = new Intl.DateTimeFormat("en-CA", {
      timeZone: tz || DEFAULT_TIMEZONE,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
    return formatter.format(d); // en-CA outputs YYYY-MM-DD
  } catch {
    return "";
  }
}

/**
 * Extract HH:mm in the target timezone (default Asia/Kolkata) for HTML time pickers.
 * Avoids browser-local hour shifting.
 */
export function formatTimeForPicker(
  dateInput: string | Date | null | undefined,
  tz: string = DEFAULT_TIMEZONE
): string {
  if (!dateInput) return "";
  try {
    const d = typeof dateInput === "string" ? new Date(dateInput) : dateInput;
    if (isNaN(d.getTime())) return "";

    const parts = new Intl.DateTimeFormat("en-GB", {
      timeZone: tz || DEFAULT_TIMEZONE,
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).formatToParts(d);

    const hour = parts.find((p) => p.type === "hour")?.value || "00";
    const minute = parts.find((p) => p.type === "minute")?.value || "00";
    return `${hour}:${minute}`;
  } catch {
    return "";
  }
}

/**
 * Check if a date falls on today's calendar date in Asia/Kolkata.
 */
export function isKolkataToday(dateInput: string | Date | null | undefined): boolean {
  if (!dateInput) return false;
  const targetDateStr = formatDateForPicker(dateInput, DEFAULT_TIMEZONE);
  const todayStr = formatDateForPicker(new Date(), DEFAULT_TIMEZONE);
  return targetDateStr === todayStr;
}
