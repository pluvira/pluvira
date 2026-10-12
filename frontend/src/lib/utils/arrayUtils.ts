/**
 * Generic array and collection manipulation helpers.
 */

/**
 * Removes an item from an array at a given index immutably.
 *
 * @param array Source array.
 * @param index Index of element to remove.
 * @returns New array without the specified element.
 */
export function removeArrayItem<T>(array: T[] | undefined | null, index: number): T[] {
  if (!Array.isArray(array)) return [];
  return array.filter((_, i) => i !== index);
}

/**
 * Moves an item within an array up or down in position immutably.
 *
 * @param array Source array.
 * @param index Index of element to move.
 * @param direction Movement step (-1 for up, 1 for down).
 * @returns New array with reordered elements or shallow copy if out of bounds.
 */
export function moveArrayItem<T>(array: T[] | undefined | null, index: number, direction: number): T[] {
  if (!Array.isArray(array) || array.length === 0) return [];
  const newIndex = index + direction;
  if (newIndex < 0 || newIndex >= array.length) return [...array];

  const updated = [...array];
  const temp = updated[index];
  updated[index] = updated[newIndex];
  updated[newIndex] = temp;
  return updated;
}


export interface TagOption {
  label: string;
  value: string;
}

/**
 * Formats raw option strings or objects into TagOption array.
 */
export function formatTagOptions(options: TagOption[] | string[] | undefined | null): TagOption[] {
  if (!Array.isArray(options)) return [];
  return options.map((opt) => (typeof opt === 'string' ? { label: opt, value: opt } : opt));
}

/**
 * Filters out options that are already selected.
 */
export function getUnselectedTagOptions(options: TagOption[], selectedValues: string[]): TagOption[] {
  if (!Array.isArray(options)) return [];
  const selected = Array.isArray(selectedValues) ? selectedValues : [];
  return options.filter((opt) => !selected.includes(opt.value));
}

/**
 * Adds a tag value to selected list immutably.
 */
export function addTagValue(current: string[], val: string): string[] {
  if (!val || current.includes(val)) return current;
  return [...current, val];
}

/**
 * Removes a tag value from selected list immutably.
 */
export function removeTagValue(current: string[], val: string): string[] {
  return current.filter((v) => v !== val);
}
