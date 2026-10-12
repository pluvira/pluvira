/**
 * Business Source License 1.1 (BSL) Free Tier resource thresholds and quota checkers.
 */

export const BSL_MAX_ACTIVE_SOURCES = 2;
export const BSL_MAX_CHANNELS = 2500;
export const BSL_MAX_CURATED_CHANNELS = 25;
export const BSL_MAX_CONCURRENT_STREAMS = 2;
export const BSL_MAX_SLOTS_FREE = 2;
export const BSL_MAX_SLOTS_PRO = 7;

/**
 * Checks if the number of active M3U sources exceeds the BSL Free Tier threshold.
 *
 * @param activeSourcesCount Number of active (enabled) sources.
 * @param isPro Whether an active Pro subscription is present.
 * @returns True if threshold exceeded in Free tier.
 */
export function isSourcesQuotaExceeded(activeSourcesCount: number, isPro = false): boolean {
  if (isPro) return false;
  return activeSourcesCount > BSL_MAX_ACTIVE_SOURCES;
}

/**
 * Checks if total channel count exceeds the BSL Free Tier threshold.
 *
 * @param channelsCount Total processed channels.
 * @param isPro Whether an active Pro subscription is present.
 * @returns True if threshold reached or exceeded in Free tier.
 */
export function isChannelsQuotaExceeded(channelsCount: number, isPro = false): boolean {
  if (isPro) return false;
  return channelsCount >= BSL_MAX_CHANNELS;
}

/**
 * Formats a user-facing quota label for active M3U sources.
 *
 * @param activeSourcesCount Number of active sources.
 * @param isPro Whether an active Pro subscription is present.
 * @returns Formatted quota label string.
 */
export function formatBslSourcesQuota(activeSourcesCount: number, isPro = false): string {
  if (isPro) return `${activeSourcesCount} Active (Pro Unlimited)`;
  return `${activeSourcesCount}/${BSL_MAX_ACTIVE_SOURCES} Active Playlists (Free Tier)`;
}

/**
 * Formats a user-facing quota label for channels.
 *
 * @param channelsCount Total channels count.
 * @param isPro Whether an active Pro subscription is present.
 * @returns Formatted quota label string.
 */
export function formatBslChannelsQuota(channelsCount: number, isPro = false): string {
  if (isPro) return `${channelsCount} Channels (Pro Unlimited)`;
  return `${channelsCount}/${BSL_MAX_CHANNELS} Channels (Free Tier)`;
}

/**
 * Checks if the number of curated channels in "My List" has reached the Free Tier cap.
 *
 * @param curatedCount Number of channels in curated playlist.
 * @param isPro Whether an active Pro subscription is present.
 * @returns True if threshold reached or exceeded in Free tier.
 */
export function isCuratedQuotaExceeded(curatedCount: number, isPro = false): boolean {
  if (isPro) return false;
  return curatedCount >= BSL_MAX_CURATED_CHANNELS;
}

/**
 * Formats a user-facing quota label for curated playlist channels.
 *
 * @param curatedCount Number of curated channels.
 * @param isPro Whether an active Pro subscription is present.
 * @returns Formatted quota label string.
 */
export function formatBslCuratedQuota(curatedCount: number, isPro = false): string {
  if (isPro) return `${curatedCount} Curated (Pro Unlimited)`;
  return `${curatedCount}/${BSL_MAX_CURATED_CHANNELS} Channels (Free Tier)`;
}

/**
 * Checks if a channel position in "My List" is locked due to Free Tier cap (positions 26+).
 *
 * @param positionIndex Zero-based channel position index.
 * @param isPro Whether an active Pro subscription is present.
 * @returns True if channel is locked in Free tier.
 */
export function isChannelPositionLocked(positionIndex: number, isPro = false): boolean {
  if (isPro) return false;
  return positionIndex >= BSL_MAX_CURATED_CHANNELS;
}

/**
 * Returns maximum allowable failover stream slots based on tier.
 *
 * @param isPro Whether an active Pro subscription is present.
 * @returns Max slot capacity (2 in Free, 7 in Pro).
 */
export function getMaxFailoverSlots(isPro = false): number {
  return isPro ? BSL_MAX_SLOTS_PRO : BSL_MAX_SLOTS_FREE;
}
