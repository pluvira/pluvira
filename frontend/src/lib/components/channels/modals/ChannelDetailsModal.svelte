<script lang="ts">
  import Dialog from '../../ui/Dialog.svelte';
  import Badge from '../../ui/Badge.svelte';
  import Button from '../../ui/Button.svelte';
  import MergedBadge from '../badges/MergedBadge.svelte';
  import LinkStatusBadge from '../badges/LinkStatusBadge.svelte';
  import InclusionBadge from '../badges/InclusionBadge.svelte';
  import EpgStatusBadge from '../badges/EpgStatusBadge.svelte';
  import CorsBadge from '../badges/CorsBadge.svelte';
  import { Camera, Pencil, Radio, Play, GitCompare } from '@lucide/svelte';
  import { truncateMiddle, CHANNEL_METADATA_FIELDS } from '../utils/ChannelsUtils';
  import type { ChannelItem } from '$lib/api/types';

  interface Props {
    channel?: ChannelItem | null;
    open?: boolean;
    onclose?: () => void;
    ontoggleinclusion?: (channel: ChannelItem) => void;
    ontestlink?: (channel: ChannelItem) => void;
    oneditmapping?: (channel: ChannelItem) => void;
    oneditname?: (channel: ChannelItem) => void;
    oneditlogo?: (channel: ChannelItem) => void;
    onediturl?: (channel: ChannelItem) => void;
    onedituseragent?: (channel: ChannelItem) => void;
    oneditmetadata?: (channel: ChannelItem) => void;
    onplaystream?: (channel: ChannelItem) => void;
    onopenfailover?: (channel: ChannelItem) => void;
  }

  let {
    channel = null,
    open = $bindable(),
    onclose,
    ontoggleinclusion,
    ontestlink,
    oneditmapping,
    oneditname,
    oneditlogo,
    onediturl,
    onedituseragent,
    oneditmetadata,
    onplaystream,
    onopenfailover
  }: Props = $props();

  function handleFieldAction(key: string, ch: ChannelItem) {
    if (key === 'name') oneditname?.(ch);
    else if (key === 'group') oneditmetadata?.(ch);
    else if (key === 'logo') oneditlogo?.(ch);
    else if (key === 'user_agent') onedituseragent?.(ch);
    else if (key === 'url') onediturl?.(ch);
  }
</script>

<Dialog bind:open title="Channel Metadata Details" {onclose} class="max-w-2xl">
  {#if channel}
    <div class="flex flex-col gap-6 w-full text-xs">
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 w-full">
        <div class="panel-box">
          <span class="text-[10px] font-bold text-muted-foreground uppercase">Failover & Merge</span>
          {#if channel.backup_streams && channel.backup_streams.length > 0}
            <MergedBadge
              count={channel.backup_streams.length}
              onclick={onopenfailover ? () => onopenfailover(channel!) : undefined}
            />
          {:else}
            <Badge variant="muted">SINGLE</Badge>
          {/if}
        </div>
        <div class="panel-box">
          <span class="text-[10px] font-bold text-muted-foreground uppercase">Catalog Visibility</span>
          <InclusionBadge
            included={channel.is_included}
            onclick={ontoggleinclusion ? () => ontoggleinclusion(channel!) : undefined}
          />
        </div>

        <div class="panel-box">
          <span class="text-[10px] font-bold text-muted-foreground uppercase">Link Test</span>
          <LinkStatusBadge
            status={channel.link_status}
            onclick={ontestlink ? () => ontestlink(channel!) : undefined}
          />
        </div>

        <div class="panel-box">
          <span class="text-[10px] font-bold text-muted-foreground uppercase">CORS / Proxy</span>
          <CorsBadge
            corsSupported={channel.cors_supported}
            needsProxy={channel.needs_proxy}
          />
        </div>

        <div class="panel-box">
          <span class="text-[10px] font-bold text-muted-foreground uppercase">EPG Mapping</span>
          <EpgStatusBadge
            isMapped={channel.is_mapped}
            epgId={channel.epg_id}
            showId={true}
            emptyLabel="NONE"
            onclick={oneditmapping ? () => oneditmapping(channel!) : undefined}
          />
        </div>
      </div>

      <div class="flex flex-col gap-2 w-full">
        <h3 class="text-sm font-bold text-foreground border-b border-border/30 pb-1">
          Processed Data
        </h3>

        <div class="flex flex-col gap-2.5 w-full">
          {#each CHANNEL_METADATA_FIELDS as f (f.key)}
            {@const origVal = String((channel.original_data && channel.original_data[f.key as keyof typeof channel.original_data]) || '')}
            {@const procVal = String(channel[f.key as keyof ChannelItem] || '')}
            {@const isModified = Boolean(procVal && procVal !== origVal)}

            <div class="surface-darkest p-3 rounded-md border border-border/30 flex flex-col gap-1.5">
              <div class="flex items-center justify-between gap-2">
                <span class="font-extrabold text-xs text-foreground uppercase tracking-wider">{f.label}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onclick={() => handleFieldAction(f.key, channel!)}
                  class="!p-1 text-xs text-muted-foreground hover:text-foreground touch-btn"
                  title={f.actionTitle}
                >
                  {#if f.isLogo}
                    <Camera class="w-3.5 h-3.5" />
                  {:else}
                    <Pencil class="w-3.5 h-3.5" />
                  {/if}
                </Button>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono pt-1 border-t border-border/20">
                <div class="flex flex-col gap-0.5">
                  <span class="text-[10px] text-muted-foreground uppercase">Original</span>
                  <span class="text-muted-foreground/80 break-all">{truncateMiddle(origVal) || '—'}</span>
                </div>

                <div class="flex flex-col gap-0.5 sm:text-right">
                  <span class="text-[10px] text-muted-foreground uppercase">Processed</span>
                  {#if isModified}
                    <span class="text-amber-400 font-bold break-all" title={procVal}>
                      {truncateMiddle(procVal)}
                    </span>
                  {:else}
                    <span class="text-muted-foreground/40 italic">—</span>
                  {/if}
                </div>
              </div>
            </div>
          {/each}
        </div>

        <div class="flex items-center justify-end gap-2 pt-2 flex-wrap">
          {#if onopenfailover}
            <Button
              variant="outline"
              size="sm"
              onclick={() => onopenfailover?.(channel)}
              class="!py-1 !px-2.5 text-xs font-bold flex items-center gap-1.5 touch-btn"
              title="Manage Failover Backup Streams"
            >
              <GitCompare class="w-3.5 h-3.5 text-primary" />
              <span>Failover & Backups</span>
            </Button>
          {/if}
          {#if oneditmetadata}
            <Button
              variant="outline"
              size="sm"
              onclick={() => oneditmetadata?.(channel)}
              class="!py-1 !px-2.5 text-xs font-bold flex items-center gap-1.5 touch-btn"
              title="Edit Individual Metadata Rewrites"
            >
              <Pencil class="w-3.5 h-3.5 text-primary" />
              <span>Edit Rewrites</span>
            </Button>
          {/if}
          {#if ontestlink}
            <Button
              variant="outline"
              size="sm"
              onclick={() => ontestlink?.(channel)}
              class="!py-1 !px-2.5 text-xs font-bold flex items-center gap-1.5 touch-btn"
              title="Test Stream Link Reachability"
            >
              <Radio class="w-3.5 h-3.5 text-blue-400" />
              <span>Test Link</span>
            </Button>
          {/if}
          {#if onplaystream}
            <Button
              variant="primary"
              size="sm"
              onclick={() => onplaystream?.(channel)}
              class="!py-1 !px-2.5 text-xs font-bold flex items-center gap-1.5 touch-btn"
              title="Play Live Video Stream"
            >
              <Play class="w-3.5 h-3.5" />
              <span>Play Stream</span>
            </Button>
          {/if}
        </div>
      </div>
    </div>
  {/if}
</Dialog>
