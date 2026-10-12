<script lang="ts">
  import Dialog from '../../ui/Dialog.svelte';
  import Button from '../../ui/Button.svelte';
  import Badge from '../../ui/Badge.svelte';
  import Input from '../../ui/Input.svelte';
  import type { ChannelItem, StreamRef, ApplyMergePayload } from '$lib/api/types';
  import { ScannerMappingController } from '../utils/ScannerMappingController.svelte';
  import {
    addStreamToBackup,
    promoteStreamToPrimary,
    removeStreamFromBackup,
    moveBackupStream,
    type StagedMergeState
  } from '../merge/MergeUtils';
  import { ChevronUp, ChevronDown, Trash2, Plus, Check, X } from '@lucide/svelte';
  import { licenseStore } from '$lib/stores/licenseStore';
  import { getMaxFailoverSlots } from '$lib/utils/bslUtils';
  import { toastStore } from '$lib/stores/toastStore';

  interface Props {
    channel?: ChannelItem | null;
    open?: boolean;
    onclose?: () => void;
    onsaved?: () => void;
  }

  let {
    channel = null,
    open = $bindable(),
    onclose,
    onsaved
  }: Props = $props();

  const controller = new ScannerMappingController();

  let stagedState = $state<StagedMergeState>({
    masterName: '',
    primaryStream: { url: '', source: '' },
    backupStreams: []
  });

  $effect(() => {
    if (open && channel) {
      stagedState = {
        masterName: channel.name,
        primaryStream: {
          url: channel.original_url,
          source: channel.source,
          user_agent: channel.user_agent
        },
        backupStreams: channel.backup_streams ? [...channel.backup_streams] : [],
        logo: channel.logo,
        group: channel.group,
        epgId: channel.epg_id
      };
      controller.loadCandidateMatches(channel);
      controller.loadPersonalChannel(channel);
    }
  });

  let isPro = $derived($licenseStore.isPro);
  let maxSlots = $derived(getMaxFailoverSlots(isPro));
  let totalSlotCount = $derived(1 + (stagedState.backupStreams?.length || 0));
  let isSlotCapReached = $derived(totalSlotCount >= maxSlots);

  async function handleApproveSuggestion(sugId: string) {
    await controller.approveSuggestion(sugId);
    if (channel) {
      controller.loadPersonalChannel(channel);
      onsaved?.();
    }
  }

  async function handleRejectSuggestion(sugId: string) {
    await controller.rejectSuggestion(sugId);
    if (channel) {
      controller.loadPersonalChannel(channel);
    }
  }

  function promoteToPrimary(cand: ChannelItem) { stagedState = promoteStreamToPrimary(stagedState, cand); }

  function addBackupFromCandidate(cand: ChannelItem) {
    if (!isSlotCapReached) stagedState = addStreamToBackup(stagedState, cand);
  }

  function removeBackup(ref: StreamRef) { stagedState = removeStreamFromBackup(stagedState, ref); }

  function moveBackup(index: number, direction: number) { stagedState = moveBackupStream(stagedState, index, direction); }

  async function handleSaveMerge() {
    if (!channel || !stagedState.primaryStream.url) return;
    const payload: ApplyMergePayload = {
      master_name: stagedState.masterName.trim() || channel.name,
      primary_stream: stagedState.primaryStream,
      backup_streams: stagedState.backupStreams,
      logo: stagedState.logo,
      group: stagedState.group,
      epg_id: stagedState.epgId
    };
    const ok = await controller.applyMerge(payload);
    if (ok) {
      open = false;
      onsaved?.();
    }
  }

  async function handleUnmerge() {
    if (!channel) return;
    const ok = await controller.deleteMerge(stagedState.masterName || channel.name);
    if (ok) {
      open = false;
      onsaved?.();
    }
  }
</script>

<Dialog bind:open title={`Failover & Backup Streams (${channel?.name || 'Channel'})`} {onclose} class="max-w-2xl">
  {#snippet footer()}
    <Button variant="ghost" size="sm" onclick={() => (open = false)} class="touch-btn">Cancel</Button>
    {#if stagedState.backupStreams.length > 0}
      <Button variant="danger" size="sm" disabled={controller.savingMerge} onclick={handleUnmerge} class="touch-btn">
        Unmerge
      </Button>
    {/if}
    <Button variant="primary" size="sm" disabled={controller.savingMerge} onclick={handleSaveMerge} class="font-bold touch-btn">
      {controller.savingMerge ? 'Saving...' : 'Apply Failover Chain'}
    </Button>
  {/snippet}

  {#if channel}
    <div class="flex flex-col gap-4 w-full text-xs">
      <Input label="Master Display Name" bind:value={stagedState.masterName} placeholder="Channel name..." />

      <!-- Primary Stream Info -->
      <div class="panel-mono !p-3 flex flex-col gap-1 border-l-4 !border-l-primary">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-[10px] font-bold text-primary uppercase tracking-wider">Primary Active Stream</span>
            <Badge variant="muted" class="text-[9px] !py-0 !px-1">Slot-Pool: {totalSlotCount}/{maxSlots} Slots</Badge>
          </div>
          <Badge variant="success">PRIMARY (Slot 0)</Badge>
        </div>
        <span class="text-foreground font-bold text-sm truncate">{stagedState.primaryStream.source}</span>
        <span class="text-mono-link break-all">{stagedState.primaryStream.url}</span>
        {#if controller.personalChannel?.slots?.[0]}
          {@const slot0 = controller.personalChannel.slots[0]}
          <div class="flex items-center gap-2 pt-1 text-[10px] text-muted-foreground flex-wrap">
            <Badge variant="success" class="text-[9px] !py-0 !px-1">Score: {Math.round(slot0.health_score)}</Badge>
            {#if slot0.latency_ms !== undefined}
              <span class="font-mono">{slot0.latency_ms}ms</span>
            {/if}
            {#if slot0.uptime_pct !== undefined}
              <span class="font-mono">{slot0.uptime_pct.toFixed(1)}% Uptime</span>
            {/if}
          </div>
        {/if}
      </div>

      <!-- Backup Streams Chain -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between">
          <span class="font-bold text-muted-foreground text-xs uppercase tracking-wider">
            Failover Backup Streams ({stagedState.backupStreams.length})
          </span>
          {#if isSlotCapReached}
            <Badge variant="warning" class="text-[9px] !py-0 !px-1">Slot-Cap Reached (Max {maxSlots})</Badge>
          {/if}
        </div>

        {#if !isPro && isSlotCapReached}
          <div class="p-2.5 bg-primary/10 border border-primary/20 rounded text-[11px] text-primary flex items-center justify-between gap-2">
            <span>Free Tier limited to 2 failover slots (Slot 0 + 1). Pro unlocks 7 slots.</span>
            <Button variant="primary" size="sm" onclick={() => toastStore.info('Pluvira Pro: Activate 14-day trial for 7 failover slots.')} class="!py-0.5 !px-2 text-[10px] shrink-0 touch-btn">
              Unlock 7
            </Button>
          </div>
        {/if}

        {#if stagedState.backupStreams.length === 0}
          <div class="p-4 text-center text-muted-foreground italic bg-background rounded border border-border/20">
            No backup streams configured for this channel.
          </div>
        {:else}
          <div class="flex flex-col gap-1.5 max-h-40 overflow-y-auto pr-1">
            {#each stagedState.backupStreams as b, idx (b.url + '_' + b.source)}
              <div class="flex items-center justify-between bg-card p-2 rounded border border-border/30 text-xs">
                <div class="flex flex-col truncate pr-2">
                  <div class="flex items-center gap-2 truncate">
                    <Badge variant="warning">#{idx + 1}</Badge>
                    <span class="font-bold text-foreground truncate">{b.source}</span>
                    {#if controller.personalChannel?.slots?.[idx + 1]}
                      {@const slotN = controller.personalChannel.slots[idx + 1]}
                      <Badge variant="muted" class="text-[9px] !py-0 !px-1">Score: {Math.round(slotN.health_score)}</Badge>
                      {#if slotN.latency_ms !== undefined}
                        <span class="text-[10px] font-mono text-muted-foreground">{slotN.latency_ms}ms</span>
                      {/if}
                    {/if}
                  </div>
                  <span class="font-mono text-[10px] text-muted-foreground truncate">{b.url}</span>
                </div>

                <div class="flex items-center gap-1 shrink-0">
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={idx === 0}
                    onclick={() => moveBackup(idx, -1)}
                    class="!p-0.5 text-xs touch-btn"
                    title="Move Up"
                  >
                    <ChevronUp class="w-3.5 h-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={idx === stagedState.backupStreams.length - 1}
                    onclick={() => moveBackup(idx, 1)}
                    class="!p-0.5 text-xs touch-btn"
                    title="Move Down"
                  >
                    <ChevronDown class="w-3.5 h-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onclick={() => removeBackup(b)}
                    class="!p-0.5 text-xs text-destructive hover:opacity-80 touch-btn"
                    title="Remove Backup"
                  >
                    <Trash2 class="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Suggestions Review Queue (70% - 89% Confidence) -->
      {#if controller.personalChannel?.suggestions && controller.personalChannel.suggestions.length > 0}
        <div class="flex flex-col gap-2 pt-2 border-t border-border/20">
          <div class="flex items-center justify-between">
            <span class="font-bold text-primary text-xs uppercase tracking-wider">
              Pending Suggestions Queue ({controller.personalChannel.suggestions.length})
            </span>
            <Badge variant="warning">REVIEW NEEDED</Badge>
          </div>

          <div class="flex flex-col gap-1.5 max-h-36 overflow-y-auto pr-1">
            {#each controller.personalChannel.suggestions as sug (sug.id)}
              <div class="flex items-center justify-between bg-card p-2 rounded border border-primary/30 text-xs">
                <div class="flex flex-col truncate pr-2">
                  <div class="flex items-center gap-1.5 truncate">
                    <Badge variant="warning" class="text-[9px] !py-0 !px-1">{Math.round(sug.confidence_score)}% Match</Badge>
                    <span class="font-bold text-foreground truncate">{sug.source}</span>
                  </div>
                  <span class="font-mono text-[10px] text-muted-foreground truncate">{sug.url}</span>
                </div>

                <div class="flex items-center gap-1 shrink-0">
                  <Button
                    variant="primary"
                    size="sm"
                    onclick={() => handleApproveSuggestion(sug.id)}
                    class="!py-0.5 !px-2 text-[10px] flex items-center gap-1 touch-btn"
                    title="Approve suggestion into slot-pool"
                  >
                    <Check class="w-3 h-3" />
                    <span>Approve</span>
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onclick={() => handleRejectSuggestion(sug.id)}
                    class="!p-1 text-xs text-destructive hover:opacity-80 touch-btn"
                    title="Reject and dismiss suggestion"
                  >
                    <X class="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            {/each}
          </div>
        </div>
      {/if}

      <!-- Auto-Discovered Alternative Candidate Streams -->
      {#if controller.loadingCandidates}
        <div class="p-3 text-center text-muted-foreground flex items-center justify-center gap-2 border-t border-border/20 pt-2">
          <span class="spinner !w-4 !h-4"></span>
          <span>Scanning for matching streams...</span>
        </div>
      {:else if controller.candidateStreams.length > 0}
        <div class="flex flex-col gap-2 pt-2 border-t border-border/20">
          <span class="font-bold text-muted-foreground text-xs uppercase tracking-wider">
            Discovered Alternative Candidate Streams ({controller.candidateStreams.length})
          </span>

          <div class="flex flex-col gap-1.5 max-h-36 overflow-y-auto pr-1">
            {#each controller.candidateStreams as cand (cand.original_url + '_' + cand.source)}
              <div class="flex items-center justify-between bg-card p-2 rounded border border-border/30 text-xs">
                <div class="flex flex-col truncate pr-2">
                  <span class="font-bold text-foreground truncate">{cand.name} ({cand.source})</span>
                  <span class="font-mono text-[10px] text-muted-foreground truncate">{cand.original_url}</span>
                </div>

                <div class="flex items-center gap-1 shrink-0">
                  <Button
                    variant="outline"
                    size="sm"
                    onclick={() => promoteToPrimary(cand)}
                    class="!py-0.5 !px-1.5 text-[10px] touch-btn"
                  >
                    Set Primary
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    disabled={isSlotCapReached}
                    onclick={() => addBackupFromCandidate(cand)}
                    class="!py-0.5 !px-1.5 text-[10px] flex items-center gap-1 touch-btn"
                    title={isSlotCapReached ? `Slot-Cap reached (Max ${maxSlots} slots)` : 'Add as backup stream'}
                  >
                    <Plus class="w-3 h-3" />
                    <span>Backup</span>
                  </Button>
                </div>
              </div>
            {/each}
          </div>
        </div>
      {/if}
    </div>
  {/if}
</Dialog>
