<script lang="ts">
  import Card from '../ui/Card.svelte';
  import MergedBadge from '../channels/badges/MergedBadge.svelte';
  import LiveBadge from '../channels/badges/LiveBadge.svelte';
  import InclusionBadge from '../channels/badges/InclusionBadge.svelte';
  import EpgStatusBadge from '../channels/badges/EpgStatusBadge.svelte';
  import ScheduleList from './ScheduleList.svelte';
  import { getCurrentAndNextProgram, formatTimeRemaining, type EpgProgramItem, type RenderedBlock } from './utils';
  import type { ChannelItem } from '$lib/api/types';
  import Button from '../ui/Button.svelte';
  import SegmentedControl, { type SegmentOption } from '../ui/SegmentedControl.svelte';
  import { Clock, Info, Pencil, Calendar, GitCompare } from '@lucide/svelte';

  interface Props {
    channel?: ChannelItem | null;
    programmes?: EpgProgramItem[];
    onshowdetails?: (channel: ChannelItem) => void;
    oneditmetadata?: (channel: ChannelItem) => void;
    oneditmapping?: (channel: ChannelItem) => void;
    ontoggleinclusion?: (channel: ChannelItem) => void;
    onopenfailover?: (channel: ChannelItem) => void;
    onselectprogram?: (block: RenderedBlock) => void;
    class?: string;
  }

  let {
    channel = null,
    programmes = [],
    onshowdetails,
    oneditmetadata,
    oneditmapping,
    ontoggleinclusion,
    onopenfailover,
    onselectprogram,
    class: className = ''
  }: Props = $props();

  let now = $state(new Date());

  $effect(() => {
    const timer = setInterval(() => {
      now = new Date();
    }, 30000);
    return () => clearInterval(timer);
  });

  let liveInfo = $derived(getCurrentAndNextProgram(programmes, now));

  type ProgramInfoTab = 'now' | 'schedule';
  let activeTab = $state<ProgramInfoTab>('now');

  const tabOptions: SegmentOption<ProgramInfoTab>[] = [
    { value: 'now', label: 'Now Playing', icon: Clock },
    { value: 'schedule', label: 'Schedule', icon: Calendar }
  ];
</script>

<Card class="flex flex-col h-full min-h-0 max-h-full bg-card border border-border/40 p-3 gap-2 text-xs overflow-hidden select-none {className}">
  {#if !channel}
    <div class="flex flex-col items-center justify-center h-full text-muted-foreground p-6 text-center gap-2">
      <Info class="w-8 h-8 text-muted-foreground/50" />
      <span class="font-bold text-sm">Select a channel to view programme details</span>
    </div>
  {:else}
    <!-- Channel Header -->
    <div class="flex items-center justify-between border-b border-border/30 pb-3 gap-3 shrink-0">
      <div class="flex items-center gap-3 truncate">
        {#if channel.logo}
          <img src={channel.logo} alt={channel.name} class="w-10 h-7 object-contain bg-black rounded p-0.5 border border-border/30 shrink-0" />
        {/if}
        <div class="flex flex-col truncate">
          <span class="text-sm font-extrabold text-foreground truncate">{channel.name}</span>
          <div class="flex items-center gap-1.5 text-[10px] text-muted-foreground">
            <span>{channel.source}</span>
            {#if channel.group}
              <span>•</span>
              <span class="truncate">{channel.group}</span>
            {/if}
          </div>
        </div>
      </div>

      <div class="flex items-center gap-1.5 shrink-0">
        {#if channel.backup_streams && channel.backup_streams.length > 0}
          <MergedBadge
            count={channel.backup_streams.length}
            onclick={onopenfailover ? () => onopenfailover(channel!) : undefined}
          />
        {/if}
        {#if liveInfo.current}
          <LiveBadge />
        {:else}
          <EpgStatusBadge isMapped={Boolean(channel.is_mapped || channel.epg_id)} />
        {/if}
      </div>
    </div>

    <!-- Segmented Control Tabs Switcher -->
    <div class="shrink-0 w-full">
      <SegmentedControl
        options={tabOptions}
        bind:value={activeTab}
        class="w-full"
      />
    </div>

    {#if activeTab === 'now'}
      <!-- Current Live Programme Details -->
    <div class="flex flex-col gap-2 flex-1 min-h-0 overflow-y-auto pr-0.5">
      {#if liveInfo.current}
        <div class="flex flex-col gap-1">
          <span class="text-base sm:text-lg font-extrabold text-foreground line-clamp-2 leading-tight">
            {liveInfo.current.t}
          </span>

          <div class="flex items-center justify-between text-xs text-muted-foreground">
            <div class="flex items-center gap-1.5 font-mono text-primary font-bold">
              <Clock class="w-3.5 h-3.5" />
              <span>{liveInfo.timeLabel}</span>
            </div>
            <span class="text-[11px] font-semibold text-muted-foreground">{formatTimeRemaining(liveInfo.timeRemainingMins)}</span>
          </div>

          <!-- Progress Bar -->
          <div class="w-full bg-background/80 rounded-full h-1.5 overflow-hidden border border-border/20 my-1">
            <div
              class="bg-primary h-full rounded-full transition-all duration-500"
              style="width: {liveInfo.progressPct}%"
            ></div>
          </div>
        </div>

        <!-- Description -->
        <div class="text-xs text-foreground/80 leading-relaxed line-clamp-3">
          {liveInfo.current.d || 'No detailed programme description available.'}
        </div>

        <!-- Up Next Teaser -->
        {#if liveInfo.next}
          <div class="p-2 bg-background/60 border border-border/30 rounded flex items-center justify-between gap-2 mt-auto shrink-0">
            <div class="flex flex-col min-w-0">
              <span class="text-[10px] font-bold text-muted-foreground uppercase">Up Next</span>
              <span class="text-xs font-bold text-foreground truncate">{liveInfo.next.t}</span>
            </div>
            <span class="text-[10px] font-mono text-muted-foreground shrink-0">
              {liveInfo.next.s ? liveInfo.next.s.slice(8, 10) + ':' + liveInfo.next.s.slice(10, 12) : ''}
            </span>
          </div>
        {/if}
      {:else}
        <div class="flex flex-col items-center justify-center p-3 text-center text-muted-foreground italic gap-1">
          <span>No current programme guide broadcast found for this channel.</span>
        </div>
      {/if}
      </div>
    {:else}
      <!-- Full Daily Vertical Schedule -->
      <div class="flex flex-col gap-1 flex-1 min-h-0 h-full max-h-full overflow-hidden pt-0.5">
        <ScheduleList {programmes} {onselectprogram} class="flex-1 min-h-0 h-full max-h-full overflow-hidden" />
      </div>
    {/if}

    <!-- Bottom Quick Channel Actions Toolbar -->
    <div class="border-t border-border/30 pt-2 flex items-center justify-between gap-2 flex-wrap bg-background/50 p-2 rounded mt-auto shrink-0">
      <div class="flex items-center gap-1 flex-wrap">
        <Button
          variant="ghost"
          size="sm"
          onclick={() => onshowdetails?.(channel!)}
          class="!p-1.5 text-xs text-muted-foreground hover:text-foreground"
          title="View Channel Details"
          aria-label="View Channel Details"
        >
          <Info class="w-3.5 h-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onclick={() => oneditmetadata?.(channel!)}
          class="!p-1 text-xs text-muted-foreground hover:text-foreground"
          title="Edit Channel Rewrites"
          aria-label="Edit Channel Rewrites"
        >
          <Pencil class="w-3.5 h-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onclick={() => oneditmapping?.(channel!)}
          class="!p-1 text-xs text-muted-foreground hover:text-foreground"
          title="Edit EPG Mapping"
          aria-label="Edit EPG Mapping"
        >
          <Calendar class="w-3.5 h-3.5" />
        </Button>
        {#if onopenfailover}
          <Button
            variant="ghost"
            size="sm"
            onclick={() => onopenfailover?.(channel!)}
            class="!p-1.5 text-xs text-muted-foreground hover:text-foreground"
            title="Manage Failover & Merges"
            aria-label="Manage Failover & Merges"
          >
            <GitCompare class="w-3.5 h-3.5" />
          </Button>
        {:else}
          <a href="#/channels?tab=merge" title="Open Merge & Failover Tool">
            <Button
              variant="ghost"
              size="sm"
              class="!p-1 text-xs text-muted-foreground hover:text-foreground"
              title="Open Merge & Failover Tool"
              aria-label="Open Merge & Failover Tool"
            >
              <GitCompare class="w-3.5 h-3.5" />
            </Button>
          </a>
        {/if}
      </div>

      <div class="flex items-center gap-1.5">
        <InclusionBadge
          included={channel.is_included}
          onclick={ontoggleinclusion ? () => ontoggleinclusion(channel!) : undefined}
        />
      </div>
    </div>
  {/if}
</Card>
