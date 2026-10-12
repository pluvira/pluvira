<script lang="ts">
  import Card from '../../ui/Card.svelte';
  import Badge from '../../ui/Badge.svelte';
  import Button from '../../ui/Button.svelte';
  import type { HistoryRecord } from '$lib/api/types';
  import { Trash2, Zap, Clock, User } from '@lucide/svelte';
  import { formatDuration, formatHistoryDate } from '../utils/DashboardUtils';

  interface Props {
    history?: HistoryRecord[];
    isCompact?: boolean;
    ondeleterecord?: (id: string) => void;
    onclearhistory?: () => void;
    class?: string;
  }

  let { history = [], isCompact = false, ondeleterecord, onclearhistory, class: className = '' }: Props = $props();

  let filterTrigger = $state<'all' | 'manual' | 'scheduled'>('all');

  let allCount = $derived(history.length);
  let manualCount = $derived(history.filter((r) => r.trigger !== 'scheduled').length);
  let scheduledCount = $derived(history.filter((r) => r.trigger === 'scheduled').length);

  let filteredHistory = $derived.by(() => {
    if (filterTrigger === 'manual') {
      return history.filter((r) => r.trigger !== 'scheduled');
    }
    if (filterTrigger === 'scheduled') {
      return history.filter((r) => r.trigger === 'scheduled');
    }
    return history;
  });
</script>

<Card title="Execution History" class="w-full h-full flex flex-col justify-between {isCompact ? 'compact' : ''} {className}">
  {#snippet actions()}
    <div class="flex items-center gap-1.5">
      <select
        bind:value={filterTrigger}
        class="bg-muted/40 border border-border/40 text-xs text-foreground rounded px-2 py-1 focus:outline-none focus:border-primary transition-colors cursor-pointer"
        aria-label="Filter execution history by trigger"
      >
        <option value="all">All ({allCount})</option>
        <option value="manual">Manual ({manualCount})</option>
        <option value="scheduled">Scheduled ({scheduledCount})</option>
      </select>
      {#if history.length > 0}
        <Button variant="ghost" size="sm" onclick={onclearhistory} class="!p-1 text-xs text-destructive hover:opacity-80 touch-btn" title="Clear Execution History">
          <Trash2 class="w-3.5 h-3.5" />
        </Button>
      {/if}
    </div>
  {/snippet}

  {#if history.length === 0}
    <div class="p-6 text-center text-muted-foreground italic bg-card rounded-md border border-border/20">
      No execution history records available.
    </div>
  {:else if filteredHistory.length === 0}
    <div class="p-6 text-center text-muted-foreground italic bg-card rounded-md border border-border/20">
      No execution records matching selected filter.
    </div>
  {:else}
    <div class="w-full max-h-96 overflow-y-auto flex flex-col gap-2.5 pr-1">
      {#each filteredHistory as record (record.id)}
        {@const isSuccess = record.status.toLowerCase() === 'success'}
        {@const isScheduled = record.trigger === 'scheduled'}
        <div
          class="surface-card !p-3 rounded-lg border-l-4 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-3 {isSuccess ? 'border-l-primary' : 'border-l-destructive'}"
        >
          <div class="flex flex-col gap-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="font-bold text-sm text-foreground uppercase tracking-wide">{record.mode}</span>
              {#if isScheduled}
                <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-primary/15 text-primary border border-primary/30">
                  <Clock class="w-2.5 h-2.5 text-primary" />
                  <span>Scheduled</span>
                </span>
              {:else}
                <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-muted/40 text-muted-foreground border border-border/40">
                  <User class="w-2.5 h-2.5 text-muted-foreground" />
                  <span>Manual</span>
                </span>
              {/if}
              {#if record.is_turbo}
                <Badge variant="primary" class="!px-1.5 !py-0.5 text-[10px] font-extrabold flex items-center gap-0.5">
                  <Zap class="w-2.5 h-2.5 text-primary" />
                  <span>TURBO</span>
                </Badge>
              {/if}
            </div>
            <div class="text-xs font-mono text-muted-foreground">
              {formatHistoryDate(record.timestamp)}
            </div>
          </div>

          <div class="flex items-center justify-between md:justify-end gap-2 flex-wrap">
            <div class="flex items-center gap-1.5 flex-wrap">
              <span class="px-2 py-0.5 text-xs font-mono rounded bg-muted/40 text-foreground">
                {formatDuration(record.duration)}
              </span>
              <span class="px-2 py-0.5 text-xs font-semibold rounded bg-muted/40 text-foreground">
                {record.total_channels} ch
              </span>
              <Badge variant={isSuccess ? 'success' : 'error'} class="text-[10px] font-bold">
                {record.status.toUpperCase()}
              </Badge>
            </div>

            <Button
              variant="ghost"
              size="sm"
              onclick={() => ondeleterecord?.(record.id)}
              class="!p-1.5 text-destructive hover:bg-destructive/10 min-h-[36px] min-w-[36px] flex items-center justify-center touch-btn"
              title="Delete Record"
              aria-label="Delete Record"
            >
              <Trash2 class="w-4 h-4" />
            </Button>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</Card>
