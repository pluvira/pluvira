/**
 * Generic string manipulation and formatting helpers.
 */

/**
 * Splits multiline string text into an array of non-empty trimmed strings.
 *
 * @param text Multiline string input.
 * @returns Cleaned array of string lines.
 */
export function parseNewlineList(text: string): string[] {
  if (!text) return [];
  return text.split('\n').map((s) => s.trim()).filter(Boolean);
}

/**
 * Formats an array of string items into a newline-separated string.
 *
 * @param list Array of string items.
 * @returns Joined multiline string.
 */
export function formatNewlineList(list?: string[] | null): string {
  if (!Array.isArray(list)) return '';
  return list.join('\n');
}

/**
 * Truncates a long text string in the middle with an ellipsis if it exceeds total length bounds.
 *
 * @param text Source text string.
 * @param startLen Characters to keep at the start (default 35).
 * @param endLen Characters to keep at the end (default 25).
 * @returns Middle-truncated string.
 */
export function truncateMiddle(text?: string | null, startLen = 35, endLen = 25): string {
  if (!text) return '';
  if (text.length <= startLen + endLen + 5) return text;
  return `${text.substring(0, startLen)} ... ${text.substring(text.length - endLen)}`;
}
