<script lang="ts">
  import Badge from '../../ui/Badge.svelte';

  interface Props {
    isMapped?: boolean;
    epgId?: string;
    showId?: boolean;
    emptyLabel?: string;
    onclick?: (e: MouseEvent) => void;
    class?: string;
  }

  let {
    isMapped = false,
    epgId = '',
    showId = false,
    emptyLabel = 'NO EPG',
    onclick,
    class: className = ''
  }: Props = $props();

  let variant = $derived<'success' | 'muted'>(isMapped ? 'success' : 'muted');
  let labelText = $derived(isMapped ? 'EPG' : emptyLabel);
  let tooltipText = $derived(
    onclick
      ? 'Edit Manual EPG Mapping'
      : isMapped
        ? (epgId ? `EPG Mapped: ${epgId}` : 'EPG Guide Mapped')
        : 'No EPG Guide Mapped'
  );
</script>

{#if onclick}
  <button
    type="button"
    {onclick}
    class="cursor-pointer shrink-0 inline-flex items-center gap-1 truncate {className}"
    title={tooltipText}
  >
    <Badge {variant}>
      {labelText}
    </Badge>
    {#if showId && epgId}
      <span class="font-mono text-[10px] text-foreground/80 truncate">{epgId}</span>
    {/if}
  </button>
{:else}
  <span class="inline-flex items-center gap-1 truncate {className}" title={tooltipText}>
    <Badge {variant}>
      {labelText}
    </Badge>
    {#if showId && epgId}
      <span class="font-mono text-[10px] text-foreground/80 truncate">{epgId}</span>
    {/if}
  </span>
{/if}
