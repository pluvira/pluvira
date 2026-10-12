<script lang="ts">
  import { onMount, onDestroy, untrack } from 'svelte';
  import Hls from 'hls.js';
  import dashjs from 'dashjs';
  import {
    VideoPlayerController,
    getProxyStreamUrl,
    normalizePlaybackError,
    getCurrentStreamTarget,
    type VideoStreamDetails
  } from './VideoPlayerController.svelte';
  import { videoPlayerStore } from './VideoPlayerStore';
  import { toastStore } from '$lib/stores/toastStore';
  import Button from '../ui/Button.svelte';
  import Badge from '../ui/Badge.svelte';
  import { X, AlertTriangle, RotateCw, Maximize, Minimize, Radio } from '@lucide/svelte';
  import type { ChannelItem } from '$lib/api/types';

  interface Props {
    stream?: (VideoStreamDetails & { id?: string; posX?: number; posY?: number; needsProxy?: boolean }) | null;
    channel?: ChannelItem | null;
    embedded?: boolean;
    onclose?: () => void;
    class?: string;
  }

  let {
    stream = null,
    channel = null,
    embedded = false,
    onclose,
    class: className = ''
  }: Props = $props();

  const controller = new VideoPlayerController();
  let videoElement: HTMLVideoElement | null = $state(null);
  let cardElement: HTMLDivElement | null = $state(null);
  let hlsInstance: Hls | null = null;
  let dashInstance: dashjs.MediaPlayerClass | null = null;

  let isResolving = $state(true);
  let resolvedUrl = $state('');
  let usingProxy = $state(false);
  let currentStreamIndex = $state(0);
  let retryCount = $state(0);
  const MAX_RETRIES = 3;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;
  let playbackError = $state<string | null>(null);
  let errorCode = $state<string | number | null>(null);

  let isDragging = $state(false);
  let pos = $state({ x: 100, y: 100 });
  let startOffset = { x: 0, y: 0 };

  function handleMouseDown(e: MouseEvent) {
    if (!cardElement) return;
    isDragging = true;
    startOffset = {
      x: e.clientX - cardElement.offsetLeft,
      y: e.clientY - cardElement.offsetTop
    };
  }

  function handleMouseMove(e: MouseEvent) {
    if (!isDragging) return;
    pos = {
      x: Math.max(0, e.clientX - startOffset.x),
      y: Math.max(0, e.clientY - startOffset.y)
    };
  }

  function handleMouseUp() {
    isDragging = false;
  }

  function cleanupPlayer() {
    if (retryTimer) {
      clearTimeout(retryTimer);
      retryTimer = null;
    }
    if (hlsInstance) {
      hlsInstance.destroy();
      hlsInstance = null;
    }
    if (dashInstance) {
      dashInstance.destroy();
      dashInstance = null;
    }
    if (videoElement) {
      videoElement.pause();
      videoElement.removeAttribute('src');
      videoElement.load();
    }
  }

  function handleStreamError(details: VideoStreamDetails, code: string, message: string) {
    if (retryCount < MAX_RETRIES) {
      retryCount += 1;
      const delay = retryCount * 500;
      if (retryTimer) clearTimeout(retryTimer);
      retryTimer = setTimeout(() => {
        const shouldProxy = usingProxy || retryCount >= 2;
        initPlayer(shouldProxy, currentStreamIndex);
      }, delay);
      return;
    }

    retryCount = 0;
    const target = getCurrentStreamTarget(details, currentStreamIndex);
    controller.reportPlaybackFailure({
      ...details,
      url: target.url,
      originalUrl: target.originalUrl
    }, code, message);

    const totalStreams = 1 + (details.backupStreams?.length || 0);
    if (currentStreamIndex + 1 < totalStreams) {
      currentStreamIndex += 1;
      toastStore.warning(`Stream KO: Switching to backup stream #${currentStreamIndex}`);
      initPlayer(false, currentStreamIndex);
      return;
    }

    isResolving = false;
    errorCode = code;
    playbackError = message;
  }

  function fallbackToNative(forceProxy: boolean, targetUrl: string, targetUa?: string) {
    cleanupPlayer();
    const details = getEffectiveStreamDetails();
    if (!videoElement || !details) return;
    const playUrl = forceProxy ? getProxyStreamUrl(targetUrl, targetUa) : targetUrl;
    videoElement.src = playUrl;
    videoElement.play().catch((err: any) => {
      const code = videoElement?.error?.code ? `MEDIA_ERR_${videoElement.error.code}` : 'NATIVE_PLAY_FAILED';
      const msg = err?.message || 'Native browser video playback failed';
      handleStreamError(details, code, msg);
    });
  }

  function getEffectiveStreamDetails(): VideoStreamDetails | null {
    if (stream) return stream;
    if (channel) {
      return {
        channelId: channel.id,
        source: channel.source,
        url: channel.url,
        originalUrl: channel.original_url,
        title: channel.name,
        userAgent: channel.user_agent,
        backupStreams: channel.backup_streams || []
      };
    }
    return null;
  }

  function handlePlaying() {
    isResolving = false;
    playbackError = null;
    errorCode = null;
    retryCount = 0;
    if (retryTimer) {
      clearTimeout(retryTimer);
      retryTimer = null;
    }
    const details = getEffectiveStreamDetails();
    if (details) {
      const target = getCurrentStreamTarget(details, currentStreamIndex);
      controller.reportPlaybackSuccess({
        ...details,
        url: target.url,
        originalUrl: target.originalUrl
      }, usingProxy);
    }
  }

  async function initPlayer(forceProxy = false, streamIndex = 0) {
    const details = getEffectiveStreamDetails();
    if (!details) {
      cleanupPlayer();
      return;
    }

    currentStreamIndex = streamIndex;
    const target = getCurrentStreamTarget(details, streamIndex);

    isResolving = true;
    playbackError = null;
    errorCode = null;
    usingProxy = forceProxy;

    try {
      resolvedUrl = await controller.resolveStream({
        ...details,
        url: target.url,
        originalUrl: target.originalUrl,
        userAgent: target.userAgent
      });
    } catch (err: any) {
      handleStreamError(details, 'RESOLVE_ERROR', err?.message || 'Failed to resolve stream URL');
      return;
    }

    if (!videoElement) return;
    cleanupPlayer();

    const playUrl = forceProxy ? getProxyStreamUrl(resolvedUrl, target.userAgent) : resolvedUrl;

    if (controller.isDash) {
      try {
        dashInstance = dashjs.MediaPlayer().create();
        dashInstance.initialize(videoElement, playUrl, true);

        if (forceProxy) {
          dashInstance.extend('RequestModifier', () => ({
            modifyRequest: (req: any) => {
              if (req && req.url && !req.url.includes('/api/v1/stream/proxy')) {
                req.url = getProxyStreamUrl(req.url, target.userAgent);
              }
              return req;
            }
          }), true);
        }

        dashInstance.on(dashjs.MediaPlayer.events.ERROR, (e: any) => {
          const errCode = e?.error?.code || 'DASH_ERROR';
          const errMsg = e?.error?.message || 'MPEG-DASH stream playback failed';
          handleStreamError(details, errCode, errMsg);
        });
      } catch {
        fallbackToNative(forceProxy, resolvedUrl, target.userAgent);
      }
    } else if (controller.isHls && Hls.isSupported()) {
      const hlsConfig: any = { enableWorker: true };
      if (forceProxy) {
        hlsConfig.xhrSetup = function(xhr: XMLHttpRequest, url: string) {
          if (!url.includes('/api/v1/stream/proxy')) {
            xhr.open('GET', getProxyStreamUrl(url, target.userAgent), true);
          }
        };
      }

      hlsInstance = new Hls(hlsConfig);
      hlsInstance.loadSource(resolvedUrl);
      hlsInstance.attachMedia(videoElement);

      hlsInstance.on(Hls.Events.MANIFEST_PARSED, () => {
        videoElement?.play().catch(() => {});
      });

      hlsInstance.on(Hls.Events.ERROR, (_, data) => {
        const httpStatus = data.response?.code;
        if (!data.fatal && (!httpStatus || httpStatus < 400)) {
          return;
        }

        if (data.fatal && data.type === Hls.ErrorTypes.MEDIA_ERROR) {
          try {
            hlsInstance?.recoverMediaError();
            return;
          } catch {
            // Fallthrough to fatal error handling if recovery fails
          }
        }

        if (!forceProxy && (data.type === Hls.ErrorTypes.NETWORK_ERROR || data.fatal)) {
          handleStreamError(details, 'HLS_NETWORK_ERROR', 'HLS network error');
        } else if (data.fatal || (httpStatus && httpStatus >= 400)) {
          const normalized = normalizePlaybackError(httpStatus, data.details, data.type);
          handleStreamError(details, normalized.code, normalized.message);
        }
      });
    } else {
      fallbackToNative(forceProxy, resolvedUrl, target.userAgent);
    }
  }

  function handleNativeError() {
    const details = getEffectiveStreamDetails();
    if (!details) return;
    const mediaErrCode = videoElement?.error?.code;
    const normalized = normalizePlaybackError(
      null,
      mediaErrCode ? `MEDIA_ERR_${mediaErrCode}` : 'MEDIA_ERROR',
      videoElement?.error?.message
    );
    handleStreamError(details, normalized.code, normalized.message);
  }

  function handleClose() {
    cleanupPlayer();
    if (stream?.id) {
      videoPlayerStore.closeStream(stream.id);
    }
    if (onclose) onclose();
  }

  let isFullscreen = $state(false);

  function toggleFullscreen() {
    if (!cardElement) return;
    if (!document.fullscreenElement) {
      cardElement.requestFullscreen().then(() => {
        isFullscreen = true;
      }).catch(() => {});
    } else {
      document.exitFullscreen().then(() => {
        isFullscreen = false;
      }).catch(() => {});
    }
  }

  let lastStreamKey = '';

  $effect(() => {
    const details = getEffectiveStreamDetails();
    if (!details) {
      lastStreamKey = '';
      cleanupPlayer();
      return;
    }
    const currentKey = `${details.channelId || ''}_${details.url}_${details.originalUrl}`;
    if (currentKey !== lastStreamKey) {
      lastStreamKey = currentKey;
      untrack(() => {
        currentStreamIndex = 0;
        const needsProxy = stream?.needsProxy ?? channel?.needs_proxy ?? false;
        initPlayer(Boolean(needsProxy), 0);
      });
    }
  });

  onMount(() => {
    if (!embedded && stream) {
      pos = { x: stream.posX ?? 100, y: stream.posY ?? 100 };
    }
  });

  onDestroy(() => {
    cleanupPlayer();
  });

  let effectiveDetails = $derived(getEffectiveStreamDetails());
</script>

<svelte:window onmousemove={handleMouseMove} onmouseup={handleMouseUp} />

<div
  bind:this={cardElement}
  style={embedded ? '' : `left: ${pos.x}px; top: ${pos.y}px;`}
  class={embedded
    ? `surface-card relative overflow-hidden bg-black flex flex-col justify-between aspect-video w-full border border-border/40 shadow-card ${className}`
    : `surface-modal fixed z-50 w-96 h-64 flex flex-col overflow-hidden select-none pointer-events-auto ${className}`}
>
    <div
      role="button"
      tabindex="0"
      onmousedown={handleMouseDown}
      class="surface-header text-foreground px-3 py-2 flex items-center justify-between shrink-0 {embedded ? 'bg-gradient-to-b from-black/80 via-black/40 to-transparent' : 'cursor-move'}"
    >
      <div class="flex items-center gap-2 truncate pr-2">
        <span class="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
        <span class="text-xs font-bold truncate">{effectiveDetails?.title || 'Live Stream'}</span>
        {#if embedded && effectiveDetails}
          <Badge variant={usingProxy ? 'warning' : 'success'}>
            {usingProxy ? 'PROXY' : 'DIRECT'}
          </Badge>
          {#if currentStreamIndex > 0}
            <Badge variant="warning">BACKUP #{currentStreamIndex}</Badge>
          {/if}
        {/if}
      </div>
      <div class="flex items-center gap-1.5 shrink-0">
        {#if effectiveDetails}
          <button
            type="button"
            onclick={(e) => { e.stopPropagation(); initPlayer(!usingProxy); }}
            class="text-[9px] font-bold px-1.5 py-0.5 rounded border transition-colors cursor-pointer {usingProxy ? 'bg-primary/20 border-primary text-primary' : 'bg-transparent border-border text-muted-foreground hover:text-foreground'}"
            title="Toggle Server CORS Proxy"
          >
            PROXY
          </button>
        {/if}
        {#if embedded}
          <Button
            variant="ghost"
            size="sm"
            onclick={toggleFullscreen}
            class="!p-0.5 text-xs text-foreground hover:bg-accent"
            title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
            aria-label="Toggle Fullscreen"
          >
            {#if isFullscreen}
              <Minimize class="w-4 h-4" />
            {:else}
              <Maximize class="w-4 h-4" />
            {/if}
          </Button>
        {:else}
          <Button variant="ghost" size="sm" onclick={handleClose} class="!p-0.5 text-xs" aria-label="Close video player">
            <X class="w-4 h-4" />
          </Button>
        {/if}
      </div>
    </div>

    <div class="flex-1 bg-black relative flex items-center justify-center overflow-hidden">
      {#if !effectiveDetails}
        <div class="flex flex-col items-center gap-2 text-muted-foreground p-6 text-center">
          <Radio class="w-10 h-10 text-muted-foreground/40 animate-pulse" />
          <span class="text-xs font-bold uppercase tracking-wider">Select a channel to start streaming</span>
        </div>
      {:else if isResolving}
        <div class="flex flex-col items-center gap-2 text-muted-foreground">
          <span class="spinner"></span>
          <span class="text-xs font-bold">Resolving stream...</span>
        </div>
      {:else if playbackError}
        <div class="absolute inset-0 bg-black/95 p-4 flex flex-col items-center justify-center text-center gap-2 z-10 select-none">
          <div class="flex items-center gap-1.5 text-destructive font-bold text-xs">
            <AlertTriangle class="w-4 h-4" />
            <span>STREAM PLAYBACK KO</span>
          </div>
          {#if errorCode}
            <Badge variant="error">{errorCode}</Badge>
          {/if}
          <p class="text-[11px] text-muted-foreground max-w-[300px] truncate leading-tight" title={playbackError}>
            {playbackError}
          </p>
          <div class="flex items-center gap-2 mt-1">
            <Button
              variant="outline"
              size="sm"
              onclick={() => initPlayer(usingProxy)}
              class="!py-0.5 !px-2 text-[10px] flex items-center gap-1 font-bold"
              title="Retry current playback"
            >
              <RotateCw class="w-3 h-3" />
              <span>Retry</span>
            </Button>
            <Button
              variant={usingProxy ? 'secondary' : 'primary'}
              size="sm"
              onclick={() => initPlayer(!usingProxy)}
              class="!py-0.5 !px-2 text-[10px] font-bold"
              title={usingProxy ? "Switch to Direct stream playback" : "Retry with Server CORS Proxy"}
            >
              {usingProxy ? 'Direct Mode' : 'Retry with Proxy'}
            </Button>
          </div>
        </div>
      {/if}

      <video
        bind:this={videoElement}
        controls
        autoplay
        playsinline
        onerror={handleNativeError}
        onplaying={handlePlaying}
        class="w-full h-full object-contain bg-black {isResolving || playbackError || !effectiveDetails ? 'hidden' : 'block'}"
      >
        <track kind="captions" />
      </video>
    </div>
</div>
