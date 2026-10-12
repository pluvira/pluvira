<script lang="ts">
  interface Props {
    timelineWidth?: number;
    rowCount?: number;
    selectedDateStr?: string;
    class?: string;
  }

  let {
    timelineWidth = $bindable(),
    rowCount = 0,
    selectedDateStr = (() => {
      const d = new Date();
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    })(),
    class: className = ''
  }: Props = $props();

  const hours = Array.from({ length: 72 }, (_, i) => i);
  let effectiveWidth = $derived(timelineWidth ?? 7200);
  const hourStepPx = $derived(effectiveWidth / 72);

  let now = $state(new Date());

  $effect(() => {
    const timer = setInterval(() => {
      now = new Date();
    }, 30000);
    return () => clearInterval(timer);
  });
  
  let currentTimeLeftPx = $derived.by(() => {
    const windowStart = new Date(selectedDateStr + 'T00:00:00');
    const windowEnd = new Date(windowStart.getTime() + 3 * 86400 * 1000);
    
    if (now < windowStart || now > windowEnd) return null;
    
    const elapsedMs = now.getTime() - windowStart.getTime();
    const windowMs = 3 * 86400 * 1000;
    return (elapsedMs / windowMs) * effectiveWidth;
  });
</script>

<div class="surface-header flex flex-col w-full select-none {className}">
  <div class="relative flex items-center h-8 w-full overflow-visible" style="width: {effectiveWidth}px;">
    {#each hours as h (h)}
      {@const displayHour = h % 24}
      {@const isMidnight = displayHour === 0}
      <div
        class="absolute text-[10px] font-bold pl-1 border-l h-full flex items-center {isMidnight ? 'border-primary/50 text-primary' : 'border-border/20 text-muted-foreground'}"
        style="left: {h * hourStepPx}px; width: {hourStepPx}px;"
      >
        {displayHour.toString().padStart(2, '0')}:00
      </div>
    {/each}

    {#if currentTimeLeftPx !== null && currentTimeLeftPx >= 0 && currentTimeLeftPx <= effectiveWidth}
      <div
        class="absolute top-0 bottom-0 border-l-2 border-primary z-30 pointer-events-none"
        style="left: {currentTimeLeftPx}px; height: {32 + rowCount * 64}px;"
      >
        <span class="absolute -top-1 -left-1.5 w-3 h-3 rounded-full bg-primary shadow-md"></span>
      </div>
    {/if}
  </div>
</div>
