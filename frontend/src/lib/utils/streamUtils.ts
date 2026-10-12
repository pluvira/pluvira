/**
 * Stream URL composition and playback error normalization helpers.
 */

/**
 * Composes a stream CORS proxy URL with optional User-Agent query parameter.
 *
 * @param url Target media stream URL.
 * @param userAgent Optional custom User-Agent header.
 * @returns Proxied stream URL string.
 */
export function getStreamProxyUrl(url: string, userAgent?: string): string {
  if (!url) return '';
  if (url.includes('/api/v1/stream/proxy')) {
    return url;
  }
  const params = new URLSearchParams({ url });
  if (userAgent) {
    params.set('user_agent', userAgent);
  }
  return `/api/v1/stream/proxy?${params.toString()}`;
}

/**
 * Normalizes player error details into a standardized taxonomy code and message.
 *
 * @param httpStatus Optional HTTP status code.
 * @param detail Optional error detail string from player engine.
 * @param type Optional error type string.
 * @returns Object containing normalized error code and message.
 */
export function normalizePlaybackError(
  httpStatus?: number | null,
  detail?: string | null,
  type?: string | null
): { code: string; message: string } {
  if (httpStatus && httpStatus >= 400) {
    return {
      code: `HTTP ${httpStatus}`,
      message: detail ? `HTTP ${httpStatus} (${detail})` : `HTTP ${httpStatus} Error`
    };
  }

  const raw = (detail || type || '').toLowerCase();
  if (raw.includes('levelparsing') || raw.includes('manifestparsing')) {
    return {
      code: 'EMPTY_OR_INVALID_PLAYLIST',
      message: 'Received empty or invalid HLS manifest / playlist'
    };
  }
  if (raw.includes('codec') || raw.includes('bufferaddcodec')) {
    return {
      code: 'CODEC_UNSUPPORTED',
      message: 'Video or audio codec not supported natively'
    };
  }
  if (raw.includes('media_err_4') || raw.includes('notsupportederror')) {
    return {
      code: 'SRC_NOT_SUPPORTED',
      message: 'Video format not supported or stream unreachable'
    };
  }
  if (raw.includes('media_err_3')) {
    return {
      code: 'DECODE_ERROR',
      message: 'Error encountered while decoding media stream'
    };
  }
  if (raw.includes('media_err_2')) {
    return {
      code: 'NETWORK_ERROR',
      message: 'Media network error occurred'
    };
  }

  const fallbackCode = detail
    ? detail.toUpperCase().replace(/[^\w]/g, '_').substring(0, 30)
    : 'STREAM_ERROR';

  return {
    code: fallbackCode,
    message: detail || 'Stream playback failed'
  };
}
