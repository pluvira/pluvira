<script lang="ts">
  import Button from '../../ui/Button.svelte';
  import {
    DAYS_OF_WEEK,
    parseCronDays,
    formatCronDays
  } from '../utils/SchedulerUtils';

  interface Props {
    value?: string;
    disabled?: boolean;
  }

  let { value = $bindable(), disabled = false }: Props = $props();

  let effectiveValue = $derived(value || '*');
  let activeDays = $derived(parseCronDays(effectiveValue));

  function toggleDay(dayKey: string) {
    if (disabled) return;
    let next: string[];
    if (activeDays.includes(dayKey)) {
      if (activeDays.length > 1) {
        next = activeDays.filter((k) => k !== dayKey);
      } else {
        next = activeDays;
      }
    } else {
      next = [...activeDays, dayKey];
    }
    value = formatCronDays(next);
  }
</script>

<div class="grid grid-cols-7 gap-1.5 sm:gap-2 w-full select-none">
  {#each DAYS_OF_WEEK as day (day.key)}
    {@const isActive = activeDays.includes(day.key)}
    <Button
      type="button"
      variant={isActive ? 'secondary' : 'outline'}
      size="sm"
      {disabled}
      onclick={() => toggleDay(day.key)}
      class="w-full !py-0.5 !h-[26px] text-[11px] font-semibold touch-btn justify-center truncate {isActive ? '!border-primary/50 text-primary bg-primary/10 font-bold' : 'opacity-60 text-muted-foreground'}"
      title={day.label}
      aria-label={day.label}
    >
      <span class="hidden sm:inline truncate">{day.label}</span>
      <span class="sm:hidden truncate">{day.shortLabel}</span>
    </Button>
  {/each}
</div>
