<script lang="ts">
  import { onMount } from 'svelte';
  import type { SchedulePayload } from '$lib/api/types';
  import type { SettingsController } from '../utils/SettingsController.svelte';
  import Card from '../../ui/Card.svelte';
  import Button from '../../ui/Button.svelte';
  import ConfirmDialog from '../../ui/ConfirmDialog.svelte';
  import { ConfirmController } from '../../ui/ConfirmController.svelte';
  import JobAccordionCard from '../cards/JobAccordionCard.svelte';
  import { RotateCcw } from '@lucide/svelte';

  interface Props {
    schedule?: SchedulePayload;
    controller?: SettingsController;
  }

  let { schedule = $bindable(), controller }: Props = $props();

  let groupOptions = $derived(controller?.availableGroups || []);
  let sourceOptions = $derived(controller?.sourceOptions || []);

  const confirmController = new ConfirmController();
  let openIndices = $state<Record<number, boolean>>({ 0: true });

  function addJob() {
    controller?.addJob();
    if (schedule?.jobs) {
      openIndices[schedule.jobs.length - 1] = true;
    }
  }

  function requestRemoveJob(index: number) {
    confirmController.requestConfirm('scheduled_job', () => {
      controller?.removeJob(index);
    });
  }

  function requestRestoreDefaults() {
    confirmController.requestConfirm('scheduler_restore_defaults', () => {
      controller?.restoreDefaultSchedulerJobs('missing_only');
    });
  }

  function handleToggleJob(job: any) {
    if (job.is_system && job.enabled) {
      confirmController.requestConfirm('system_job_disable', () => {
        job.enabled = false;
      });
    } else {
      job.enabled = !job.enabled;
    }
  }

  function runJobNow(job: any) {
    controller?.runJobNow(job);
  }

  onMount(() => {
    controller?.loadGroupSuggestions();
  });
</script>

<div class="flex flex-col gap-4 w-full text-xs">
  <ConfirmDialog
    bind:open={confirmController.open}
    scope={confirmController.scope}
    onconfirm={() => confirmController.handleConfirm()}
  />

  {#if schedule}
    <Card title="Background Update Scheduler Options">
    <label class="flex items-center gap-2 cursor-pointer text-muted-foreground font-bold">
      <input type="checkbox" bind:checked={schedule.enabled} class="rounded text-primary" />
      <span>Enable Automatic Background Scheduler updates (daemon lifecycle)</span>
    </label>
  </Card>

  <div class="flex items-center justify-end border-b border-border/30 pb-2 mt-2 gap-2">
    <div class="flex items-center gap-2">
      <Button
        variant="outline"
        size="sm"
        onclick={requestRestoreDefaults}
        class="text-xs !py-1 touch-btn flex items-center gap-1.5"
        title="Restore factory default system and recommended tasks"
      >
        <RotateCcw class="w-3.5 h-3.5" />
        <span>Restore Defaults</span>
      </Button>
      <Button variant="primary" size="sm" onclick={addJob} class="text-xs !py-1 touch-btn">
        + Add Scheduled Job
      </Button>
    </div>
  </div>

  {#if !schedule.jobs || schedule.jobs.length === 0}
    <div class="panel-box !items-center !justify-center !p-6">
      No background scheduled jobs defined. Click "+ Add Scheduled Job" to create one.
    </div>
  {:else}
    <div class="flex flex-col gap-3">
      {#each schedule.jobs as job, idx (job.id || 'job_' + idx)}
        <JobAccordionCard
          bind:job={schedule.jobs[idx]}
          index={idx}
          bind:open={openIndices[idx]}
          {sourceOptions}
          {groupOptions}
          onrunnow={(j) => runJobNow(j)}
          onremove={(i) => requestRemoveJob(i)}
          ontoggleenabled={(j) => handleToggleJob(j)}
        />
      {/each}
    </div>
  {/if}
  {/if}
</div>