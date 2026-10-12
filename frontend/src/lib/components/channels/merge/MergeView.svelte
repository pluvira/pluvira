<script lang="ts">
  import { onMount } from 'svelte';
  import { MergeController } from './MergeController.svelte';
  import { videoPlayerStore } from '$lib/components/player/VideoPlayerStore';
import { licenseStore } from '$lib/stores/licenseStore';
  import FilterBar from '../bars/FilterBar.svelte';
  import Select from '../../ui/Select.svelte';
  import Card from '../../ui/Card.svelte';
  import Badge from '../../ui/Badge.svelte';
  import Button from '../../ui/Button.svelte';
  import MergeMatrix from './MergeMatrix.svelte';
  import ChannelDetailsModal from '../modals/ChannelDetailsModal.svelte';
  import DeepLinkTestModal from '../modals/DeepLinkTestModal.svelte';
  import ConfirmDialog from '../../ui/ConfirmDialog.svelte';
  import { ConfirmController } from '../../ui/ConfirmController.svelte';
  import type { ChannelItem } from '$lib/api/types';
  import type { CandidateCluster, StagedMergeState } from './MergeUtils';
  import { Zap, Trash2, CheckCircle2 } from '@lucide/svelte';

  const controller = new MergeController();
  let isPro = $derived($licenseStore.isPro);

$effect(() => {
  if (!isPro && controller.similarityThreshold < 0.85) {
    controller.setThreshold(0.85, isPro);
  }
});

  let activeChannel = $state<ChannelItem | null>(null);
  let showScannerModal = $state(false);
  let showDetailsModal = $state(false);

  function handleShowDetails(ch: ChannelItem) {
    activeChannel = ch;
    showDetailsModal = true;
  }

  function refreshData() {
    controller.loadClusters();
  }

  function handleSelectCluster(cluster: CandidateCluster) {
    controller.selectedCluster = cluster;
  }

  async function handleApplyMerge(state: StagedMergeState, candidates: ChannelItem[]) {
    const ok = await controller.applyMerge(state, candidates);
    if (ok) refreshData();
  }

  const confirmController = new ConfirmController();

  function requestUnmergeAll() {
    confirmController.requestConfirm('bulk_unmerge', () => controller.bulkUnmergeAll());
  }

  function handleUnmerge(masterName: string) {
    confirmController.requestConfirm('master_merge', async () => {
      const ok = await controller.unmerge(masterName);
      if (ok) refreshData();
    });
  }

  function handleTestLink(ch: ChannelItem) {
    activeChannel = ch;
    showScannerModal = true;
  }

  function handlePlayStream(ch: ChannelItem) {
    videoPlayerStore.playChannel(ch);
  }

  onMount(() => {
    refreshData();
    const unsubscribePlayer = videoPlayerStore.onStatusUpdate((evt) => {
      controller.handleStreamStatusUpdate(evt);
    });
    return () => {
      unsubscribePlayer();
    };
  });
</script>

<div class="flex flex-col gap-4 w-full">
  <ConfirmDialog
    bind:open={confirmController.open}
    scope={confirmController.scope}
    onconfirm={() => confirmController.handleConfirm()}
  />

  {#if controller.stats}
    <div class="surface-card p-3 flex flex-wrap items-center justify-between gap-3 w-full animate-fade-in">
      <div class="flex items-center gap-2 flex-wrap text-xs font-bold text-foreground">
        <Badge variant="muted">Clusters: {controller.stats.total_clusters_detected}</Badge>
        <Badge variant="success">Merged: {controller.stats.total_merged_channels}</Badge>
        <Badge variant="warning">Unmerged: {controller.stats.total_unmerged_clusters}</Badge>
        <Badge variant="primary">Backups: {controller.stats.total_backup_streams}</Badge>
      </div>

      <div class="flex items-center gap-2">
        <Button
          variant={isPro ? 'primary' : 'secondary'}
          size="sm"
          disabled={!isPro || controller.loading}
          onclick={() => controller.autoMergeAll(isPro)}
          class="text-xs font-bold"
          title={isPro ? 'Automatically merge clusters with similarity >= 95%' : 'Pro Engine required for Auto-Merge'}
        >
          <div class="flex items-center gap-1.5">
            <Zap class="w-3.5 h-3.5" />
            <span>AUTO-MERGE ALL (≥ 95%)</span>
          </div>
        </Button>
        {#if controller.stats.total_merged_channels > 0}
          <Button
            variant="danger"
            size="sm"
            disabled={controller.loading}
            onclick={requestUnmergeAll}
            class="text-xs"
            title="Unmerge all active master channels"
          >
            <div class="flex items-center gap-1.5">
              <Trash2 class="w-3.5 h-3.5" />
              <span>UNMERGE ALL</span>
            </div>
          </Button>
        {/if}
      </div>
    </div>
  {/if}

  <div class="sticky top-0 z-30 bg-background/95 backdrop-blur-xs pb-1">
    <FilterBar
      bind:searchQuery={controller.searchQuery}
      delayMs={300}
      onsearch={() => controller.applyFilters()}
    >
    {#snippet extraFilters()}
      <div class="w-44">
        <Select
          label="Status Filter"
          bind:value={controller.clusterStatusFilter}
          options={[
            { label: 'All Clusters', value: 'all' },
            { label: 'Unmerged Only', value: 'unmerged_only' },
            { label: 'Merged Only', value: 'merged_only' }
          ]}
          onchange={() => controller.applyFilters()}
        />
      </div>

      <div class="flex flex-col gap-1 w-44">
        <label for="fuzzy-sensitivity-input" class="text-xs font-bold text-muted-foreground flex justify-between">
          <span>Sensitivity</span>
          <span class="text-primary">{Math.round(controller.similarityThreshold * 100)}%</span>
        </label>
        <input
          id="fuzzy-sensitivity-input"
          type="range"
          min={isPro ? "0.5" : "0.85"}
          max="1.0"
          step="0.05"
          value={controller.similarityThreshold}
          oninput={(e) => controller.setThreshold(parseFloat((e.target as HTMLInputElement).value), isPro)}
          onchange={() => refreshData()}
          class="w-full accent-primary cursor-pointer"
        />
        {#if !isPro}
          <span class="text-[10px] text-amber-400/90 italic">Pro Engine required for 50%-80% sensitivity</span>
        {/if}
      </div>
    {/snippet}
  </FilterBar>
  </div>

  {#if controller.loading && controller.allClusters.length === 0}
    <div class="state-empty">
      <span class="spinner mr-3"></span>
      <span class="text-sm font-bold">Scanning for duplicate channel clusters...</span>
    </div>
  {:else if controller.filteredClusters.length === 0}
    <Card class="p-12 text-center items-center justify-center flex flex-col gap-2">
      <CheckCircle2 class="w-8 h-8 text-green-500 mb-1" />
      <span class="text-base font-bold text-foreground">No duplicate channel clusters detected.</span>
      <span class="text-xs text-muted-foreground">Try adjusting the Fuzzy Sensitivity slider above to scan for looser matches.</span>
    </Card>
  {:else}
    <div class="flex flex-col md:flex-row gap-4 w-full items-start">
      <Card title={`Clusters (${controller.filteredClusters.length})`} class="w-full md:w-72 shrink-0 max-h-[75vh] overflow-y-auto">
        {#snippet actions()}
          {#if controller.loading}
            <span class="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin"></span>
          {/if}
        {/snippet}
        <div class="flex flex-col gap-1.5">
          {#each controller.filteredClusters as cluster (cluster.cluster_id)}
            {@const isSelected = controller.selectedCluster?.cluster_id === cluster.cluster_id}
            <button
              type="button"
              onclick={() => handleSelectCluster(cluster)}
              class="list-item-btn {isSelected ? 'list-item-btn-selected' : ''}"
            >
              <div class="flex items-center justify-between gap-1">
                <span class="font-bold text-xs text-foreground truncate flex-1">{cluster.canonical_name}</span>
                {#if cluster.is_merged || cluster.status === 'merged'}
                  <Badge variant="success">Merged</Badge>
                {:else}
                  <Badge variant="muted">Suggested</Badge>
                {/if}
              </div>
              <span class="text-[10px] text-muted-foreground">{cluster.candidates.length} candidate streams</span>
            </button>
          {/each}
        </div>
      </Card>

      <div class="flex-1 w-full min-w-0">
        <MergeMatrix
          cluster={controller.selectedCluster}
          loading={controller.loading}
          onapplymerge={handleApplyMerge}
          onunmerge={handleUnmerge}
          ontestlink={handleTestLink}
          onplaystream={handlePlayStream}
          onshowdetails={handleShowDetails}
        />
      </div>
    </div>
  {/if}

  <ChannelDetailsModal
    channel={activeChannel}
    bind:open={showDetailsModal}
    ontestlink={handleTestLink}
    onplaystream={handlePlayStream}
  />
  <DeepLinkTestModal channel={activeChannel} bind:open={showScannerModal} />
</div>
