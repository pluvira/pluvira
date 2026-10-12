<script lang="ts">
  import type { SourceStatItem } from '$lib/api/types';
  import BaseSourceTable from './BaseSourceTable.svelte';
  import Button from '../../ui/Button.svelte';
  import { RotateCw, Settings, Tv, Calendar } from '@lucide/svelte';

  interface Props {
    sourcesStats?: SourceStatItem[];
    isCompact?: boolean;
    ontogglesource?: (sourceName: string) => void;
    onsetallstate?: (enable: boolean) => void;
    onrefreshsource?: (sourceNames: string[]) => void;
    class?: string;
  }

  let { sourcesStats = [], isCompact = false, ontogglesource, onsetallstate, onrefreshsource, class: className = '' }: Props = $props();
</script>

<BaseSourceTable
  title="IPTV Sources Analytics"
  items={sourcesStats}
  {isCompact}
  nameHeader="Source Provider"
  refreshTitle="Refresh All IPTV Sources"
  ontogglestatus={ontogglesource}
  {onsetallstate}
  onrefreshnames={onrefreshsource}
  class={className}
>
  {#snippet extraHeaders()}
    <th class="table-th text-center">Total</th>
    <th class="table-th text-center">Included</th>
    <th class="table-th text-center">Excluded</th>
    <th class="table-th text-center">EPG Match (INC)</th>
    <th class="table-th text-center">EPG Match (EXC)</th>
    <th class="table-th text-center">Link Health</th>
  {/snippet}

  {#snippet rowCells(src: SourceStatItem)}
    <td class="table-td text-center">{src.enabled ? src.total_channels : '—'}</td>
    <td class="table-td text-center">{src.enabled ? src.included_channels : '—'}</td>
    <td class="table-td text-center">{src.enabled ? src.excluded_channels : '—'}</td>
    <td class="table-td text-center">{src.enabled ? `${src.epg_match_included_pct.toFixed(1)}%` : '—'}</td>
    <td class="table-td text-center">{src.enabled ? `${src.epg_match_excluded_pct.toFixed(1)}%` : '—'}</td>
    <td class="table-td text-center">
      {#if src.enabled}
        <div class="flex items-center justify-center gap-1">
          <span class="font-bold text-primary">{src.link_health_pct.toFixed(1)}%</span>
          <span class="text-[10px] text-muted-foreground">({src.online_links} OK / {src.offline_links} KO)</span>
        </div>
      {:else}
        —
      {/if}
    </td>
  {/snippet}

  {#snippet actionLinks(src: SourceStatItem)}
    <Button variant="ghost" size="sm" disabled={!src.enabled} onclick={() => onrefreshsource?.([src.name])} class="!p-1 text-xs text-primary" title="Refresh Source">
      <RotateCw class="w-3.5 h-3.5" />
    </Button>
    <a href={`#/settings?tab=sources&expand=${encodeURIComponent(src.name)}`}>
      <Button variant="ghost" size="sm" class="!p-1 text-xs" title="Edit IPTV Settings">
        <Settings class="w-3.5 h-3.5" />
      </Button>
    </a>
    <a href={`#/channels?source=${encodeURIComponent(src.name)}`}>
      <Button variant="ghost" size="sm" disabled={!src.enabled} class="!p-1 text-xs" title="Filter Channels by Source">
        <Tv class="w-3.5 h-3.5" />
      </Button>
    </a>
    <a href={`#/channels?source=${encodeURIComponent(src.name)}`}>
      <Button variant="ghost" size="sm" disabled={!src.enabled} class="!p-1 text-xs" title="Filter Channels by Source">
        <Calendar class="w-3.5 h-3.5" />
      </Button>
    </a>
  {/snippet}
</BaseSourceTable>
