<script lang="ts">
  import ChannelRow from './ChannelRow.svelte';
  import Checkbox from '../../ui/Checkbox.svelte';
  import Button from '../../ui/Button.svelte';
  import { paginateData } from '../../ui/TableUtils';
  import type { ChannelItem } from '$lib/api/types';

  interface Props {
    channels?: ChannelItem[];
    visibleColumns?: string[];
    selectable?: boolean;
    selectedKeys?: Set<string>;
    onselectrow?: (rowKey: string) => void;
    ontoggleinclusion?: (channel: ChannelItem) => void;
    ontogglebookmark?: (channel: ChannelItem) => void;
    onshowdetails?: (channel: ChannelItem) => void;
    oneditmetadata?: (channel: ChannelItem) => void;
    oneditlogo?: (channel: ChannelItem) => void;
    oneditname?: (channel: ChannelItem) => void;
    oneditgroup?: (channel: ChannelItem) => void;
    onediturl?: (channel: ChannelItem) => void;
    onedituseragent?: (channel: ChannelItem) => void;
    oneditmapping?: (channel: ChannelItem) => void;
    ontestlink?: (channel: ChannelItem) => void;
    onplaystream?: (channel: ChannelItem) => void;
    onopenfailover?: (channel: ChannelItem) => void;
    class?: string;
  }

  let {
    channels = [],
    visibleColumns = $bindable(),
    selectable = true,
    selectedKeys = $bindable(),
    ontoggleinclusion,
    ontogglebookmark,
    onshowdetails,
    oneditmetadata,
    oneditlogo,
    oneditname,
    oneditgroup,
    onediturl,
    onedituseragent,
    oneditmapping,
    ontestlink,
    onplaystream,
    onopenfailover,
    class: className = ''
  }: Props = $props();

  let currentPage = $state(1);
  let pageSize = $state(50);

  let currentSelectedKeys = $derived(selectedKeys || new Set<string>());

  let cols = $derived(new Set(visibleColumns && visibleColumns.length > 0 ? visibleColumns : []));
  let showLogo = $derived(cols.has('logo'));
  let showName = $derived(cols.has('name'));
  let showSource = $derived(cols.has('source'));
  let showGroup = $derived(cols.has('group'));
  let showBookmark = $derived(cols.has('bookmark'));
  let showLinkStatus = $derived(cols.has('link_status'));
  let showEpg = $derived(cols.has('epg'));
  let showInclusion = $derived(cols.has('inclusion'));
  let showMerge = $derived(cols.has('merge'));
  let showDetails = $derived(cols.has('details'));
  let showPlay = $derived(cols.has('play'));

  let pipelineResult = $derived.by(() => {
    const totalCount = channels.length;
    const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
    let safePage = currentPage;
    if (safePage > totalPages && totalPages > 0) safePage = totalPages;
    if (safePage < 1) safePage = 1;
    const items = paginateData(channels, safePage, pageSize);
    return { items, totalPages, totalCount, safePage };
  });

  let displayedChannels = $derived(pipelineResult.items);
  let totalPages = $derived(pipelineResult.totalPages);
  let totalCount = $derived(pipelineResult.totalCount);

  $effect(() => {
    if (currentPage !== pipelineResult.safePage) {
      currentPage = pipelineResult.safePage;
    }
  });

  function setPage(p: number) {
    if (p >= 1 && p <= totalPages) {
      currentPage = p;
    }
  }

  let isAllSelected = $derived(
    channels.length > 0 && channels.every((ch) => currentSelectedKeys.has(ch.id))
  );

  let isIndeterminate = $derived(
    currentSelectedKeys.size > 0 && !isAllSelected
  );

  function handleToggleSelectAll() {
    if (isAllSelected) {
      selectedKeys = new Set();
    } else {
      const allIds = new Set(channels.map((ch) => ch.id));
      selectedKeys = allIds;
    }
  }

  function handleToggleRowSelect(channel: ChannelItem) {
    const newSet = new Set(currentSelectedKeys);
    if (newSet.has(channel.id)) {
      newSet.delete(channel.id);
    } else {
      newSet.add(channel.id);
    }
    selectedKeys = newSet;
  }
</script>

<div class="channels-table flex flex-col gap-2 w-full {className}">
  <!-- List Header Toolbar -->
  <div class="surface-header flex items-center justify-between gap-3 px-3 py-2 rounded-t-md text-xs font-bold text-muted-foreground border-b border-border/40">
    <div class="flex items-center gap-2.5">
      {#if selectable}
        <Checkbox
          checked={isAllSelected ? true : isIndeterminate ? 'indeterminate' : false}
          onCheckedChange={handleToggleSelectAll}
          aria-label="Select all channels"
        />
      {/if}
      <span>Channels List ({totalCount})</span>
    </div>

    <!-- Pagination Controls (Header) -->
    <div class="flex items-center gap-3">
      <div class="hidden sm:flex items-center gap-1.5">
        <label for="channels-page-size-select" class="text-[11px] text-muted-foreground font-bold">Rows:</label>
        <select
          id="channels-page-size-select"
          bind:value={pageSize}
          class="select-compact"
        >
          <option value={25}>25</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
          <option value={250}>250</option>
        </select>
      </div>

      <div class="flex items-center gap-1">
        <Button
          variant="ghost"
          size="sm"
          disabled={currentPage <= 1}
          onclick={() => setPage(currentPage - 1)}
          class="!py-1 !px-2 text-xs touch-btn"
          title="Previous page"
        >
          Prev
        </Button>
        <span class="font-bold text-foreground text-xs">{currentPage}/{totalPages}</span>
        <Button
          variant="ghost"
          size="sm"
          disabled={currentPage >= totalPages}
          onclick={() => setPage(currentPage + 1)}
          class="!py-1 !px-2 text-xs touch-btn"
          title="Next page"
        >
          Next
        </Button>
      </div>
    </div>
  </div>

  <!-- Rows Container -->
  {#if displayedChannels.length === 0}
    <div class="p-8 text-center text-muted-foreground italic bg-card rounded-md border border-border/30">
      No channels available for the current filter selection.
    </div>
  {:else}
    <div class="flex flex-col gap-1.5 md:gap-0 bg-card rounded-b-md border border-border/30 overflow-hidden shadow-xs">
      {#each displayedChannels as ch (ch.id)}
        <ChannelRow
          channel={ch}
          {selectable}
          isSelected={currentSelectedKeys.has(ch.id)}
          {showLogo}
          {showName}
          {showSource}
          {showGroup}
          {showBookmark}
          {showLinkStatus}
          {showEpg}
          {showInclusion}
          {showDetails}
          {showMerge}
          {showPlay}
          ontoggleselect={handleToggleRowSelect}
          {ontoggleinclusion}
          {ontogglebookmark}
          {onshowdetails}
          {oneditmetadata}
          {oneditlogo}
          {oneditname}
          {oneditgroup}
          {onediturl}
          {onedituseragent}
          {oneditmapping}
          {ontestlink}
          {onplaystream}
          {onopenfailover}
        />
      {/each}
    </div>
  {/if}

  <!-- Footer Pagination (for mobile / long lists) -->
  {#if totalPages > 1}
    <div class="surface-card p-2 flex items-center justify-between text-xs text-muted-foreground border border-border/30 rounded-md">
      <span class="text-[11px]">Showing {displayedChannels.length} of {totalCount}</span>
      <div class="flex items-center gap-1">
        <Button
          variant="ghost"
          size="sm"
          disabled={currentPage <= 1}
          onclick={() => setPage(currentPage - 1)}
          class="!py-1 !px-2 text-xs touch-btn"
        >
          Prev
        </Button>
        <span class="font-bold text-foreground text-xs">{currentPage}/{totalPages}</span>
        <Button
          variant="ghost"
          size="sm"
          disabled={currentPage >= totalPages}
          onclick={() => setPage(currentPage + 1)}
          class="!py-1 !px-2 text-xs touch-btn"
        >
          Next
        </Button>
      </div>
    </div>
  {/if}
</div>
