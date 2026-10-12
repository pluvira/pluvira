import { writable } from 'svelte/store';
import type { ChannelItem } from '$lib/api/types';

export interface StreamStatusUpdateEvent {
  channelId?: string;
  originalUrl: string;
  source?: string;
  link_status: 'online' | 'offline';
  cors_supported: boolean;
  needs_proxy: boolean;
  errorCode?: string | number | null;
  errorMessage?: string | null;
}

export type StreamStatusListener = (event: StreamStatusUpdateEvent) => void;

export interface ActiveStreamInstance {
  channelId?: string;
  source?: string;
  id: string;
  url: string;
  originalUrl: string;
  title: string;
  userAgent?: string;
  needsProxy?: boolean;
  posX: number;
  posY: number;
}

function createVideoPlayerStore() {
  const listeners = new Set<StreamStatusListener>();
  const { subscribe, update } = writable<ActiveStreamInstance[]>([]);

  function openStream(stream: { url: string; originalUrl: string; title: string; userAgent?: string; needsProxy?: boolean; channelId?: string; source?: string }) {
    update((streams) => {
      const id = `player_${Math.random().toString(36).substring(2, 9)}`;
      const offset = (streams.length % 5) * 30;
      const newInstance: ActiveStreamInstance = {
        id,
        url: stream.url,
        originalUrl: stream.originalUrl,
        title: stream.title,
        userAgent: stream.userAgent,
        needsProxy: stream.needsProxy,
        channelId: stream.channelId,
        source: stream.source,
        posX: 100 + offset,
        posY: 100 + offset
      };
      return [...streams, newInstance];
    });
  }

  function playChannel(channel: ChannelItem) {
    if (!channel) return;
    openStream({
      url: channel.url,
      originalUrl: channel.original_url,
      title: channel.name,
      userAgent: channel.user_agent,
      needsProxy: channel.needs_proxy,
      channelId: channel.id,
      source: channel.source
    });
  }

  return {
    subscribe,
    openStream,
    playChannel,
    notifyStatus: (event: StreamStatusUpdateEvent) => {
      listeners.forEach((listener) => {
        try {
          listener(event);
        } catch {
          // Ignore listener error
        }
      });
    },
    onStatusUpdate: (listener: StreamStatusListener) => {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    closeStream: (id: string) => {
      update((streams) => streams.filter((s) => s.id !== id));
    },
    clearAll: () => {
      update(() => []);
    }
  };
}

export const videoPlayerStore = createVideoPlayerStore();
