import type { SystemStatus } from '$lib/api/types';

export const DEFAULT_CLOUD_BASE_URL = 'https://pluvira.com';

let cachedEndpoints: Record<string, string> | null = null;

/**
 * Stores cloud endpoints dynamically received from backend system status.
 *
 * @param endpoints Key-value map of endpoints or null to reset.
 */
export function setCachedCloudEndpoints(endpoints?: Record<string, string> | null): void {
  if (endpoints) {
    cachedEndpoints = { ...endpoints };
  } else {
    cachedEndpoints = null;
  }
}

/**
 * Resolves the SaaS cloud base URL prioritizing systemStatus, cachedEndpoints, and env variables.
 *
 * @param systemStatus Optional system status snapshot.
 * @returns Normalized base URL string without trailing slash.
 */
export function getCloudBaseUrl(systemStatus?: SystemStatus | null): string {
  const fromStatus = systemStatus?.cloud_endpoints?.base;
  if (fromStatus && typeof fromStatus === 'string') {
    return fromStatus.replace(/\/+$/, '');
  }

  if (cachedEndpoints?.base) {
    return cachedEndpoints.base.replace(/\/+$/, '');
  }

  const fromEnv = (import.meta as any).env?.VITE_CLOUD_BASE_URL;
  if (fromEnv && typeof fromEnv === 'string') {
    return fromEnv.replace(/\/+$/, '');
  }

  return DEFAULT_CLOUD_BASE_URL;
}

/**
 * Resolves a target SaaS cloud service URL.
 *
 * @param endpointKey Target route key ('base', 'portal', 'auth', 'docs').
 * @param systemStatus Optional system status snapshot.
 * @returns Fully qualified endpoint URL.
 */
export function getCloudUrl(
  endpointKey: 'base' | 'portal' | 'auth' | 'docs' = 'portal',
  systemStatus?: SystemStatus | null
): string {
  if (systemStatus?.cloud_endpoints?.[endpointKey]) {
    return systemStatus.cloud_endpoints[endpointKey];
  }

  if (cachedEndpoints?.[endpointKey]) {
    return cachedEndpoints[endpointKey];
  }

  const base = getCloudBaseUrl(systemStatus);
  if (endpointKey === 'base') {
    return base;
  }

  return `${base}/${endpointKey}`;
}

/**
 * Generates the portal pairing verification URL (RFC 8628).
 *
 * @param userCode Optional user code to prefill in verification URL.
 * @param systemStatus Optional system status snapshot.
 * @returns Direct device pairing URL without legacy return parameters.
 */
export function getCloudPairingUrl(
  userCode?: string | null,
  systemStatus?: SystemStatus | null
): string {
  const portalUrl = getCloudUrl('portal', systemStatus);
  if (userCode && userCode.trim()) {
    return `${portalUrl}/pair?code=${encodeURIComponent(userCode.trim())}`;
  }
  return `${portalUrl}/pair`;
}
