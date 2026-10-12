<script lang="ts">
  import Card from '../../ui/Card.svelte';
  import Badge from '../../ui/Badge.svelte';
  import Button from '../../ui/Button.svelte';
  import Input from '../../ui/Input.svelte';
  import StreamActions from '../../player/StreamActions.svelte';
  import {
    getCandidateKey,
    isSameStream,
    isStagedStateDirty,
    createInitialStagedState,
    promoteStreamToPrimary,
    addStreamToBackup,
    removeStreamFromBackup,
    moveBackupStream,
    type CandidateCluster,
    type StagedMergeState
  } from './MergeUtils';
  import type { ChannelItem, StreamRef } from '$lib/api/types';
  import { GitCompare, ChevronUp, ChevronDown, Trash2, Info, Save } from '@lucide/svelte';

  interface Props {
    cluster?: CandidateCluster | null;
    loading?: boolean;
    onapplymerge?: (state: StagedMergeState, candidates: ChannelItem[]) => void;
    onunmerge?: (masterName: string) => void;
    ontestlink?: (channel: ChannelItem) => void;
    onplaystream?: (channel: ChannelItem) => void;
    onshowdetails?: (channel: ChannelItem) => void;
    class?: string;
  }

  let {
    cluster = null,
    loading = false,
    onapplymerge,
    onunmerge,
    ontestlink,
    onplaystream,
    onshowdetails,
    class: className = ''
  }: Props = $props();

  let stagedState = $state<StagedMergeState>({
    masterName: '',
    primaryStream: { url: '', source: '' },
    backupStreams: []
  });
  let initialState = $state<StagedMergeState | null>(null);

  $effect(() => {
    if (cluster && cluster.candidates.length > 0) {
      const loaded = createInitialStagedState(cluster);
      stagedState = { ...loaded, backupStreams: [...loaded.backupStreams] };
      initialState = { ...loaded, backupStreams: [...loaded.backupStreams] };
    }
  });

  let isClusterMerged = $derived(Boolean(cluster?.is_merged || cluster?.status === 'merged'));
  let isDirty = $derived(isClusterMerged && isStagedStateDirty(initialState, stagedState));

  let primaryCand = $derived(
    cluster?.candidates.find((c: ChannelItem) => isSameStream({ url: c.original_url, source: c.source }, stagedState.primaryStream)) || cluster?.candidates[0]
  );

  let backupCands = $derived(
    stagedState.backupStreams
      .map((ref) => cluster?.candidates.find((c: ChannelItem) => isSameStream({ url: c.original_url, source: c.source }, ref)))
      .filter((c): c is ChannelItem => Boolean(c))
  );

  function promoteToPrimary(cand: ChannelItem) {
    stagedState = promoteStreamToPrimary(stagedState, cand);
  }

  function addToBackup(cand: ChannelItem) {
    stagedState = addStreamToBackup(stagedState, cand);
  }

  function removeBackup(ref: StreamRef) {
    stagedState = removeStreamFromBackup(stagedState, ref);
  }

  function moveBackup(index: number, direction: number) {
    stagedState = moveBackupStream(stagedState, index, direction);
  }
</script>

{#if !cluster}
  <Card class="p-8 text-center text-muted-foreground italic w-full {className}">
    Select a channel cluster on the left to view comparison matrix and manage failover backups.
  </Card>
{:else}
  <div class="flex flex-col gap-4 w-full {className}">
    <Card class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-l-4 {isClusterMerged ? '!border-l-success' : '!border-l-warning'}">
      <div class="flex items-center gap-2 flex-wrap">
        <GitCompare class="w-5 h-5 {isClusterMerged ? 'text-success' : 'text-warning'} shrink-0" />
        <span class="text-base font-bold text-foreground">{cluster.canonical_name}</span>
        <Badge variant="muted">{cluster.candidates.length} Candidates</Badge>
        {#if isClusterMerged}
          <Badge variant="success">Merged</Badge>
        {:else}
          <Badge variant="warning">Suggested</Badge>
        {/if}
      </div>

      <div class="flex items-center gap-2">
        {#if isClusterMerged}
          {#if isDirty}
            <button
              type="button"
              disabled={loading}
              onclick={() => onapplymerge?.(stagedState, cluster!.candidates)}
              class="w-8 h-8 rounded-full bg-primary hover:opacity-90 text-primary-foreground flex items-center justify-center shadow-elevated cursor-pointer transition-transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed touch-btn"
              title="Save updated merge configuration"
              aria-label="Save updated merge configuration"
            >
              {#if loading}
                <span class="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
              {:else}
                <Save class="w-4 h-4" />
              {/if}
            </button>
          {/if}
          <Button
            variant="danger"
            size="sm"
            disabled={loading}
            onclick={() => onunmerge?.(cluster!.canonical_name)}
            class="text-xs font-bold flex items-center gap-1.5"
            title="Unmerge master channel and restore separate streams"
          >
            {#if loading}
              <span class="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
              <span>Unmerging...</span>
            {:else}
              <span>UNMERGE</span>
            {/if}
          </Button>
        {:else}
          <Button
            variant="primary"
            size="sm"
            disabled={loading}
            onclick={() => onapplymerge?.(stagedState, cluster!.candidates)}
            class="text-xs font-bold flex items-center gap-1.5"
            title="Save and apply merge configuration"
          >
            {#if loading}
              <span class="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
              <span>Merging...</span>
            {:else}
              <span>MERGE</span>
            {/if}
          </Button>
        {/if}
      </div>
    </Card>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 w-full">
      <Card title="Master Channel (Result)" class="flex flex-col gap-3">
        <Input label="Master Display Name" bind:value={stagedState.masterName} placeholder="Canonical name..." />

        {#if primaryCand}
          <div class="panel-mono !p-3 !gap-1.5">
            <span class="text-[10px] font-bold text-primary uppercase tracking-wider">Primary Active Stream</span>
            <span class="text-foreground font-bold text-sm truncate">{primaryCand.name} ({primaryCand.source})</span>
            <span class="text-mono-link">{primaryCand.original_url}</span>
            <span class="text-muted-foreground text-[10px]">User-Agent: {primaryCand.user_agent || 'Default'}</span>
          </div>
        {/if}
      </Card>

      <Card title={`Failover Backup Streams (${backupCands.length})`} class="flex flex-col gap-3">
        {#if backupCands.length === 0}
          <span class="text-xs text-muted-foreground italic p-3 text-center bg-background rounded border border-border/20">
            No backup streams assigned. Click "ADD TO BACKUP" on any candidate card below.
          </span>
        {:else}
          <div class="flex flex-col gap-1.5 max-h-48 overflow-y-auto pr-1">
            {#each backupCands as b, idx (b.original_url)}
              <div class="flex items-center justify-between bg-background p-2 rounded border border-border/30 text-xs">
                <div class="flex items-center gap-2 truncate pr-2">
                  <Badge variant="warning">#{idx + 1}</Badge>
                  <span class="font-bold text-foreground truncate">{b.name} ({b.source})</span>
                </div>

                <div class="flex items-center gap-1 shrink-0">
                  <Button variant="outline" size="sm" onclick={() => promoteToPrimary(b)} class="!py-0.5 !px-1.5 text-[10px]">
                    Set Primary
                  </Button>
                  <Button variant="ghost" size="sm" disabled={idx === 0} onclick={() => moveBackup(idx, -1)} class="!p-0.5 text-xs">
                    <ChevronUp class="w-3.5 h-3.5" />
                  </Button>
                  <Button variant="ghost" size="sm" disabled={idx === backupCands.length - 1} onclick={() => moveBackup(idx, 1)} class="!p-0.5 text-xs">
                    <ChevronDown class="w-3.5 h-3.5" />
                  </Button>
                  <Button variant="ghost" size="sm" onclick={() => removeBackup({ url: b.original_url, source: b.source })} class="!p-0.5 text-xs text-destructive hover:opacity-80">
                    <Trash2 class="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </Card>
    </div>

    <div class="flex flex-col gap-2 w-full">
      <span class="text-xs font-bold text-muted-foreground uppercase tracking-wider">Candidate Streams Grid</span>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 w-full">
        {#each cluster.candidates as cand (getCandidateKey(cand))}
          {@const candRef = { url: cand.original_url, source: cand.source }}
          {@const isPrimary = isSameStream(candRef, stagedState.primaryStream)}
          {@const isBackup = stagedState.backupStreams.some((b) => isSameStream(b, candRef))}

          <Card class="flex flex-col justify-between gap-3 h-64 border-2 {isPrimary ? '!border-success' : isBackup ? '!border-warning' : '!border-border/30'}">
            <div class="flex flex-col gap-2 overflow-hidden">
              <div class="flex items-center justify-between">
                <Badge variant="muted">{cand.source}</Badge>
                {#if isPrimary}
                  <Badge variant="success">PRIMARY</Badge>
                {:else if isBackup}
                  <Badge variant="warning">BACKUP</Badge>
                {/if}
              </div>

              <span class="font-bold text-foreground text-sm truncate">{cand.name}</span>

              {#if cand.logo}
                <img src={cand.logo} alt={cand.name} class="h-8 max-w-[100px] object-contain bg-black rounded p-0.5 mx-auto border border-border/30 shrink-0" />
              {/if}

              <span class="text-mono-link max-h-12 overflow-y-auto">{cand.original_url}</span>
              <span class="text-[10px] text-muted-foreground truncate">UA: {cand.user_agent || 'Default'}</span>
            </div>

            <div class="flex items-center justify-between border-t border-border/30 pt-2">
              <div class="flex items-center gap-1.5">
                <Button
                  variant="ghost"
                  size="sm"
                  onclick={() => onshowdetails?.(cand)}
                  class="!p-1 text-xs text-muted-foreground hover:text-foreground"
                  title="View Channel Details"
                  aria-label="View Channel Details"
                >
                  <Info class="w-3.5 h-3.5" />
                </Button>
                <div class="h-3.5 w-px bg-border/40"></div>
                <StreamActions ontestlink={() => ontestlink?.(cand)} onplaystream={() => onplaystream?.(cand)} />
              </div>

              {#if !isPrimary}
                <div class="flex items-center gap-1">
                  <Button variant="outline" size="sm" onclick={() => promoteToPrimary(cand)} class="!py-0.5 !px-1.5 text-[10px]">
                    Set Primary
                  </Button>
                  {#if !isBackup}
                    <Button variant="outline" size="sm" onclick={() => addToBackup(cand)} class="!py-0.5 !px-1.5 text-[10px]">
                      + Backup
                    </Button>
                  {/if}
                </div>
              {/if}
            </div>
          </Card>
        {/each}
      </div>
    </div>
  </div>
{/if}
