<script lang="ts">
  import Badge from '../../ui/Badge.svelte';

  interface Props {
    count?: number;
    compact?: boolean;
    onclick?: (e: MouseEvent) => void;
    class?: string;
  }

  let {
    count = 0,
    compact = false,
    onclick,
    class: className = ''
  }: Props = $props();

  let labelText = $derived(compact ? `+${count}` : `MERGED +${count}`);
  let tooltipText = $derived(
    onclick
      ? `Merged Master Channel with ${count} backup stream(s) - Click to manage`
      : `Merged Master Channel with ${count} backup stream(s)`
  );
</script>

{#if count > 0}
  {#if onclick}
    <button
      type="button"
      {onclick}
      class="cursor-pointer shrink-0 inline-flex {className}"
      title={tooltipText}
    >
      <Badge variant="primary" class={compact ? "!py-0 !px-1 text-[8px]" : ""}>
        {labelText}
      </Badge>
    </button>
  {:else}
    <Badge variant="primary" title={tooltipText} class="{compact ? '!py-0 !px-1 text-[8px]' : ''} {className}">
      {labelText}
    </Badge>
  {/if}
{/if}
