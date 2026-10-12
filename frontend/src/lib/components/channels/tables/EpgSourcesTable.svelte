<script lang="ts">
  import type { EpgSourceStatItem } from '$lib/api/types';
  import BaseSourceTable from './BaseSourceTable.svelte';
  import Button from '../../ui/Button.svelte';
  import Badge from '../../ui/Badge.svelte';
  import { RotateCw, Settings, Calendar, Zap, AlertTriangle } from '@lucide/svelte';
  import { formatDuration } from '../../settings/utils/DashboardUtils';

  interface Props {
    epgSourcesStats?: EpgSourceStatItem[];
    isCompact?: boolean;
    ontoggleepgsource?: (sourceName: string) => void;
    onsetallstate?: (enable: boolean) => void;
    onrefreshepgsource?: (sourceNames: string[]) => void;
    class?: string;
  }

  let { epgSourcesStats = [], isCompact = false, ontoggleepgsource, onsetallstate, onrefreshepgsource, class: className = '' }: Props = $props();
</script>

<BaseSourceTable
  title="EPG Sources Analytics"
  items={epgSourcesStats}
  {isCompact}
  nameHeader="EPG Source Guide"
  refreshTitle="Refresh All EPG Sources"
  ontogglestatus={ontoggleepgsource}
  {onsetallstate}
  onrefreshnames={onrefreshepgsource}
  class={className}
>
  {#snippet extraHeaders()}
    <th class="table-th text-center">EPG Channels</th>
    <th class="table-th text-center">M3U Mapped</th>
    <th class="table-th text-center">Utilization</th>
    <th class="table-th text-center">Programmes</th>
    <th class="table-th text-center">Last Sync</th>
    <th class="table-th text-center">Coverage</th>
  {/snippet}

  {#snippet rowCells(src: EpgSourceStatItem)}
    <td class="table-td text-center">{src.enabled ? src.total_epg_channels : '—'}</td>
    <td class="table-td text-center">{src.enabled ? src.mapped_m3u_channels : '—'}</td>
    <td class="table-td text-center">{src.enabled ? `${src.utilization_pct.toFixed(1)}%` : '—'}</td>
    <td class="table-td text-center">{src.enabled ? src.total_programmes : '—'}</td>
    <td class="table-td text-center">
      {#if src.enabled && (src.last_sync_duration_s !== undefined || src.last_sync_programmes !== undefined)}
        <div class="flex flex-col items-center justify-center gap-0.5">
          <div class="flex items-center gap-1">
            {#if src.is_turbo}
              <Badge variant="success" class="!py-0 !px-1 text-[9px] font-bold flex items-center gap-0.5 bg-primary/20 text-primary border-primary/30" title="Sync accelerated by Rust Pro engine">
                <Zap class="w-2.5 h-2.5 fill-current" />
                <span>TURBO</span>
              </Badge>
            {/if}
            {#if src.slow_sync_warning}
              <Badge variant="warning" class="!py-0 !px-1 text-[9px] font-bold flex items-center gap-0.5" title="Slow sync (>30s) in standard Core engine">
                <AlertTriangle class="w-2.5 h-2.5" />
                <span>SLOW</span>
              </Badge>
            {/if}
            <span class="text-[11px] font-mono text-muted-foreground">{src.last_sync_duration_s !== undefined ? formatDuration(src.last_sync_duration_s) : '—'}</span>
          </div>
          {#if src.last_sync_programmes !== undefined && src.last_sync_programmes > 0}
            <span class="text-[10px] text-muted-foreground/80 font-mono">+{src.last_sync_programmes.toLocaleString('en-US')} progs</span>
          {/if}
        </div>
      {:else}
        <span class="text-muted-foreground">—</span>
      {/if}
    </td>
    <td class="table-td text-center">{src.enabled ? src.coverage_days : '—'}</td>
  {/snippet}

  {#snippet actionLinks(src: EpgSourceStatItem)}
    <Button variant="ghost" size="sm" disabled={!src.enabled} onclick={() => onrefreshepgsource?.([src.name])} class="!p-1 text-xs text-primary" title="Refresh EPG Source">
      <RotateCw class="w-3.5 h-3.5" />
    </Button>
    <a href={`#/settings?tab=sources&sub=epg&expand=${encodeURIComponent(src.name)}`}>
      <Button variant="ghost" size="sm" class="!p-1 text-xs" title="Edit EPG Guide Settings">
        <Settings class="w-3.5 h-3.5" />
      </Button>
    </a>
    <a href={`#/channels?source=${encodeURIComponent(src.name)}`}>
      <Button variant="ghost" size="sm" disabled={!src.enabled} class="!p-1 text-xs" title="Filter Channels by Source">
        <Calendar class="w-3.5 h-3.5" />
      </Button>
    </a>
  {/snippet}
</BaseSourceTable>
