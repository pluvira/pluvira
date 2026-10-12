export interface TableColumn<T = unknown> {
  key: string;
  label: string;
  sortable?: boolean;
  align?: 'left' | 'center' | 'right';
  width?: string;
  getValue?: (row: T) => unknown;
}

export type SortDirection = 'asc' | 'desc' | null;

export interface SortState {
  columnKey: string | null;
  direction: SortDirection;
}

/**
 * Sorts an array of row objects by column key and direction.
 *
 * @param items Array of data row items.
 * @param sortState Active sorting state.
 * @returns Sorted array shallow copy.
 */
export function sortTableData<T>(
  items: T[],
  sortState: SortState
): T[] {
  if (!sortState.columnKey || !sortState.direction) {
    return [...items];
  }

  const { columnKey, direction } = sortState;

  return [...items].sort((a, b) => {
    const valA = (a as Record<string, unknown>)[columnKey];
    const valB = (b as Record<string, unknown>)[columnKey];

    if (valA === valB) return 0;
    if (valA === undefined || valA === null) return 1;
    if (valB === undefined || valB === null) return -1;

    let comparison = 0;
    if (typeof valA === 'string' && typeof valB === 'string') {
      comparison = valA.localeCompare(valB);
    } else if (typeof valA === 'number' && typeof valB === 'number') {
      comparison = valA - valB;
    } else {
      comparison = String(valA).localeCompare(String(valB));
    }

    return direction === 'asc' ? comparison : -comparison;
  });
}

/**
 * Paginate an array of items for target page and page size.
 *
 * @param items Source data array.
 * @param page 1-indexed target page.
 * @param pageSize Number of rows per page.
 * @returns Paginated slice of items.
 */
export function paginateData<T>(items: T[], page: number, pageSize: number): T[] {
  const start = (page - 1) * pageSize;
  return items.slice(start, start + pageSize);
}
