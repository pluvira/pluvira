import { api } from '$lib/api/client';
import { videoPlayerStore } from './VideoPlayerStore';
import type { StreamRef } from '$lib/api/types';
import { getStreamProxyUrl, normalizePlaybackError } from '$lib/utils/streamUtils';

export { getStreamProxyUrl, getStreamProxyUrl as getProxyStreamUrl, normalizePlaybackError };

export interface VideoStreamDetails {
  channelId?: string;
  source?: string;
  url: string;
  originalUrl: string;
  title: string;
  userAgent?: string;
  backupStreams?: StreamRef[];
}

export function getCurrentStreamTarget(details: VideoStreamDetails, index: number) {
  if (index === 0 || !details.backupStreams || !details.backupStreams[index - 1]) {
    return {
      url: details.url,
      originalUrl: details.originalUrl,
      userAgent: details.userAgent,
      source: details.source,
      isBackup: false
    };
  }
  const b = details.backupStreams[index - 1];
  return {
    url: b.url,
    originalUrl: b.url,
    userAgent: b.user_agent || details.userAgent,
    source: b.source || details.source,
    isBackup: true
  };
}

export class VideoPlayerController {
  public isResolving = $state(false);
  public resolvedUrl = $state('');
  public isHls = $state(false);
  public isDash = $state(false);
  public lastReportedStatus = $state<'online' | 'offline' | null>(null);
  public errorMessage = $state<string | null>(null);
  public errorCode = $state<string | number | null>(null);
  public errorDetails = $state<string | null>(null);

  public async resolveStream(details: VideoStreamDetails): Promise<string> {
    this.isResolving = true;
    this.errorMessage = null;

    try {
      const result = await api.testStreamLink({
        url: details.url,
        original_url: details.originalUrl,
        user_agent: details.userAgent || 'Mozilla/5.0'
      });

      this.resolvedUrl = (result.url as string) || details.url;
    } catch {
      this.resolvedUrl = details.url;
    } finally {
      this.isResolving = false;
    }

    const lower = this.resolvedUrl.toLowerCase();
    this.isDash = lower.includes('.mpd') || lower.includes('format=mpd');
    this.isHls = !this.isDash && (lower.includes('.m3u8') || lower.includes('.m3u') || !lower.endsWith('.mp4'));

    return this.resolvedUrl;
  }

  public reportPlaybackSuccess(details: VideoStreamDetails, usingProxy: boolean): void {
    this.lastReportedStatus = 'online';
    this.errorCode = null;
    this.errorMessage = null;
    this.errorDetails = null;

    videoPlayerStore.notifyStatus({
      channelId: details.channelId,
      originalUrl: details.originalUrl,
      source: details.source,
      link_status: 'online',
      cors_supported: !usingProxy,
      needs_proxy: usingProxy
    });

    api.reportStreamStatus({
      original_url: details.originalUrl,
      url: details.url,
      source: details.source,
      link_status: 'online',
      code: 200,
      cors_supported: !usingProxy,
      needs_proxy: usingProxy
    }).catch(() => {
      // Non-blocking background report
    });
  }

  public reportPlaybackFailure(
    details: VideoStreamDetails,
    errorCode?: string | number | null,
    errorMessage?: string | null
  ): void {
    this.lastReportedStatus = 'offline';
    this.errorCode = errorCode ?? 'PLAYBACK_FAILED';
    this.errorMessage = errorMessage ?? 'Stream playback failed or unreachable';
    this.errorDetails = errorMessage || null;

    const numericCode = typeof errorCode === 'number'
      ? errorCode
      : (typeof errorCode === 'string' && errorCode.startsWith('HTTP ') ? parseInt(errorCode.replace('HTTP ', ''), 10) : 0);

    videoPlayerStore.notifyStatus({
      channelId: details.channelId,
      originalUrl: details.originalUrl,
      source: details.source,
      link_status: 'offline',
      cors_supported: false,
      needs_proxy: false,
      errorCode: this.errorCode,
      errorMessage: this.errorMessage
    });

    api.reportStreamStatus({
      original_url: details.originalUrl,
      url: details.url,
      source: details.source,
      link_status: 'offline',
      code: numericCode || 0,
      cors_supported: false,
      needs_proxy: false,
      error_message: `${this.errorCode}: ${this.errorMessage}`
    }).catch(() => {
      // Non-blocking background report
    });
  }
}
