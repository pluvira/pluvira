<script lang="ts">
  import Card from '../../ui/Card.svelte';
  import Input from '../../ui/Input.svelte';
  import Select from '../../ui/Select.svelte';
  import Button from '../../ui/Button.svelte';
  import Badge from '../../ui/Badge.svelte';
  import MultiSelectTags from '../../ui/MultiSelectTags.svelte';
  import DayOfWeekSelector from './DayOfWeekSelector.svelte';
  import { SCHEDULER_MODE_OPTIONS, DAY_PRESETS, matchDayPreset } from '../utils/SchedulerUtils';
  import { Play, Power, Trash2, Lock, Sparkles, ChevronDown, ChevronUp } from '@lucide/svelte';

  interface Props {
    job?: any;
    index?: number;
    open?: boolean;
    sourceOptions?: any[];
    groupOptions?: any[];
    onrunnow?: (job: any) => void;
    onremove?: (index: number) => void;
    ontoggleenabled?: (job: any) => void;
  }

  let {
    job = $bindable(),
    index = 0,
    open = $bindable(),
    sourceOptions = [],
    groupOptions = [],
    onrunnow,
    onremove,
    ontoggleenabled
  }: Props = $props();

  let isOpen = $derived(Boolean(open));

  let modeOptions = $derived(
    SCHEDULER_MODE_OPTIONS.map((m) => ({
      label: `${m.label}${m.is_system ? ' (System)' : ''}`,
      value: m.value
    }))
  );

  function handlePresetChange(presetKey: string) {
    const matched = DAY_PRESETS.find((p) => p.key === presetKey);
    if (matched && matched.cronValue) {
      job.day_of_week = matched.cronValue;
    }
  }

  function handleToggle() {
    if (ontoggleenabled) {
      ontoggleenabled(job);
    } else {
      job.enabled = !job.enabled;
    }
  }
</script>

<Card class="job-accordion-card relative flex flex-col gap-3 transition-colors">
  <!-- Accordion Compact Header -->
  <div class="flex flex-wrap items-center justify-between border-b border-border/20 pb-2 gap-2 select-none">
    <button
      type="button"
      onclick={() => (open = !isOpen)}
      class="flex items-center gap-2 truncate cursor-pointer text-left hover:opacity-90 flex-1 min-w-0"
    >
      <span class="w-2.5 h-2.5 rounded-full shrink-0 {job?.enabled ? 'bg-primary' : 'bg-muted-foreground'}"></span>
      <span class="font-bold text-foreground text-sm truncate">
        {job?.id || 'Unnamed Job'}
      </span>
      {#if job?.is_system}
        <Badge variant="primary" class="text-[9px] py-0 px-1 shrink-0 flex items-center gap-1">
          <Lock class="w-2.5 h-2.5" />
          <span>SYSTEM</span>
        </Badge>
      {:else if job?.is_recommended}
        <Badge variant="muted" class="text-[9px] py-0 px-1 shrink-0 flex items-center gap-1">
          <Sparkles class="w-2.5 h-2.5" />
          <span>RECOMMENDED</span>
        </Badge>
      {/if}
    </button>

    <div class="flex items-center gap-1.5 shrink-0">
      <Button
        variant="outline"
        size="sm"
        onclick={() => onrunnow?.(job)}
        class="!p-1.5 touch-btn"
        title="Run Now"
        aria-label="Run Now"
      >
        <Play class="w-3.5 h-3.5 text-primary" />
      </Button>

      <Button
        type="button"
        variant={job?.enabled ? 'outline' : 'ghost'}
        size="sm"
        onclick={handleToggle}
        class="!p-1.5 touch-btn {job?.enabled ? 'text-primary border-primary/30 hover:bg-primary/10' : 'text-muted-foreground/60 hover:text-foreground'}"
        title={job?.enabled ? 'Job Enabled (Click to disable)' : 'Job Disabled (Click to enable)'}
        aria-label={job?.enabled ? 'Disable Job' : 'Enable Job'}
      >
        <Power class="w-3.5 h-3.5" />
      </Button>

      {#if job?.is_system}
        <span class="p-1.5 text-muted-foreground/40 cursor-not-allowed" title="System jobs cannot be deleted">
          <Lock class="w-3.5 h-3.5" />
        </span>
      {:else}
        <Button
          variant="ghost"
          size="sm"
          onclick={() => onremove?.(index)}
          class="!p-1.5 text-xs text-destructive hover:opacity-80 touch-btn"
          title="Delete Job"
          aria-label="Delete Job"
        >
          <Trash2 class="w-3.5 h-3.5" />
        </Button>
      {/if}

      <button
        type="button"
        onclick={() => (open = !isOpen)}
        class="p-1.5 text-muted-foreground hover:text-foreground cursor-pointer"
        title={isOpen ? 'Collapse details' : 'Expand details'}
        aria-label={isOpen ? 'Collapse details' : 'Expand details'}
      >
        {#if isOpen}
          <ChevronUp class="w-4 h-4" />
        {:else}
          <ChevronDown class="w-4 h-4" />
        {/if}
      </button>
    </div>
  </div>

  <!-- Expanded Details Body -->
  {#if isOpen}
    <div class="flex flex-col gap-3 pt-1 animate-fade-in text-xs">
      <!-- Row 1: Job ID | Task | Type -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <Input
          label="Job ID"
          bind:value={job.id}
          disabled={job?.is_system}
          placeholder="e.g. update_job_daily"
        />

        <Select
          label="Task"
          bind:value={job.mode}
          options={modeOptions}
          disabled={job?.is_system}
        />

        <Select
          label="Type"
          bind:value={job.trigger}
          options={[
            { label: 'Cron (Calendar)', value: 'cron' },
            { label: 'Interval (Timer)', value: 'interval' }
          ]}
          disabled={job?.is_system}
        />
      </div>

      <!-- Row 2 & 3: Cron (Hour | Minute | Days Preset) & Active Days Pills -->
      {#if job?.trigger === 'cron'}
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <Input
            label="Hour"
            bind:value={job.hour}
            placeholder="e.g. 4 or *"
          />
          <Input
            label="Minute"
            bind:value={job.minute}
            placeholder="e.g. 0 or */15"
          />
          <Select
            label="Days Preset"
            value={matchDayPreset(job?.day_of_week)}
            options={DAY_PRESETS.map((p) => ({ label: p.label, value: p.key }))}
            onchange={(e) => handlePresetChange((e.target as HTMLSelectElement).value)}
            disabled={job?.is_system}
          />
        </div>

        <div class="flex flex-col gap-1.5 pt-0.5">
          <span class="text-[11px] font-semibold text-muted-foreground">Active Days</span>
          <DayOfWeekSelector bind:value={job.day_of_week} disabled={job?.is_system} />
        </div>
      {:else if job?.trigger === 'interval'}
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <Input label="Hours" bind:value={job.hours} placeholder="0" />
          <Input label="Minutes" bind:value={job.minutes} placeholder="2" />
        </div>
      {/if}

      <Input
        label="Description / Notes"
        bind:value={job.description}
        placeholder="Identify this job purpose..."
      />

      {#if (job?.mode === 'stream_health_scan' || job?.mode === 'link_test') && job?.link_test_filters}
        <div class="surface-darkest p-4 rounded border border-primary/20 flex flex-col gap-3 mt-1">
          <span class="text-[10px] font-bold text-primary uppercase tracking-wider">Polite Scanner Link Test Filters</span>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            <Select
              label="Channel Inclusion Filter"
              bind:value={job.link_test_filters.inclusion}
              options={[
                { label: 'Included Only', value: 'included_only' },
                { label: 'All Channels', value: 'all' },
                { label: 'Excluded Only', value: 'excluded_only' }
              ]}
            />

            <Select
              label="Stream Link Status Filter"
              bind:value={job.link_test_filters.status_filter}
              options={[
                { label: 'All Link Statuses', value: 'all' },
                { label: 'OK Only', value: 'ok_only' },
                { label: 'KO Only', value: 'ko_only' },
                { label: 'Unchecked Only', value: 'unchecked_only' }
              ]}
            />

            <Input type="number" label="Max Scan Limit" bind:value={job.link_test_filters.max_channels} />
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mt-1">
            <MultiSelectTags
              label="Target Sources"
              placeholder="All sources..."
              options={sourceOptions}
              bind:selectedValues={job.link_test_filters.sources}
            />

            <MultiSelectTags
              label="Target Groups"
              placeholder="All groups..."
              options={groupOptions}
              bind:selectedValues={job.link_test_filters.groups}
            />
          </div>

          <Input
            label="Channel Name RegEx Filter"
            bind:value={job.link_test_filters.name_regex}
            placeholder="e.g. (?i)Channel \d+"
          />
        </div>
      {/if}
    </div>
  {/if}
</Card>
