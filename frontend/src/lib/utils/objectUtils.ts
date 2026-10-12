/**
 * Generic object and collection filter utilities.
 */

/**
 * Counts active filters based on an object or filter definitions.
 *
 * @param filters Record of filter values or object.
 * @param defaultValues Optional record of default values for exclusion.
 * @returns Total active filter items count.
 */
export function countActiveFilters(
  filters: Record<string, any> | undefined | null,
  defaultValues: Record<string, any> = {}
): number {
  if (!filters || typeof filters !== 'object') return 0;

  let count = 0;
  for (const [key, val] of Object.entries(filters)) {
    if (val === undefined || val === null) continue;

    const defaultVal = defaultValues[key];

    if (Array.isArray(val)) {
      count += val.length;
    } else if (typeof val === 'boolean') {
      const defBool = typeof defaultVal === 'boolean' ? defaultVal : false;
      if (val !== defBool) count += 1;
    } else if (typeof val === 'number') {
      const defNum = typeof defaultVal === 'number' ? defaultVal : 0;
      if (val > defNum) count += 1;
    } else if (typeof val === 'string') {
      const defStr = typeof defaultVal === 'string' ? defaultVal : '';
      if (val.trim() && val !== defStr) count += 1;
    }
  }

  return count;
}

/**
 * Counts active channel filter options using standard default values.
 */
export function countChannelFilters(filters?: Record<string, any> | null): number {
  return countActiveFilters(filters, {
    linkStatus: 'all',
    inclusionStatus: 'all',
    epgStatus: 'all',
    corsStatus: 'all',
    bookmarkStatus: 'all',
    searchQuery: '',
    selectedGroup: '',
    selectedSource: ''
  });
}
