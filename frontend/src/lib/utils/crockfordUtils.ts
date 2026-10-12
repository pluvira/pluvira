/**
 * Crockford Base32 alphabet: 0123456789ABCDEFGHJKMNPQRSTVWXYZ
 * Ambiguous characters: I and L map to 1, O maps to 0. U is strictly excluded.
 */
const CROCKFORD_ALPHABET = /^[0-9ABCDEFGHJKMNPQRSTVWXYZ]+$/;

/**
 * Normalizes an input string to canonical Crockford Base32 format.
 *
 * @param input Raw input string.
 * @returns Clean uppercase string with ambiguous characters mapped.
 */
export function normalizeCrockford(input?: string | null): string {
  if (!input) return '';
  return input
    .toUpperCase()
    .replace(/[\s-]/g, '')
    .replace(/[IL]/g, '1')
    .replace(/O/g, '0');
}

/**
 * Validates whether a given string is a valid 12-character Crockford Base32 UID.
 *
 * @param id UID candidate string.
 * @returns True if valid 12-char Crockford identifier.
 */
export function isValidCrockfordId(id?: string | null): boolean {
  const clean = normalizeCrockford(id);
  return clean.length === 12 && CROCKFORD_ALPHABET.test(clean);
}

/**
 * Formats a 12-character Crockford Base32 identifier into chunked display format XXXX-XXXX-XXXX.
 *
 * @param raw Raw UID string.
 * @returns Formatted XXXX-XXXX-XXXX string or empty string.
 */
export function formatCrockfordId(raw?: string | null): string {
  const clean = normalizeCrockford(raw);
  if (!clean) return '';
  if (clean.length !== 12) return clean;
  return `${clean.slice(0, 4)}-${clean.slice(4, 8)}-${clean.slice(8, 12)}`;
}

/**
 * Formats a 12-character User ID (UID) into chunked display format XXXX-XXXX-XXXX.
 */
export const formatUid = formatCrockfordId;
export const formatUserId = formatCrockfordId;
