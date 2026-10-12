<script lang="ts">
  import Badge from '../../ui/Badge.svelte';

  interface Props {
    status?: 'online' | 'offline' | 'unchecked' | string;
    onclick?: (e: MouseEvent) => void;
    class?: string;
  }

  let {
    status = 'unchecked',
    onclick,
    class: className = ''
  }: Props = $props();

  let variant = $derived<'success' | 'error' | 'muted'>(
    status === 'online' ? 'success' : status === 'offline' ? 'error' : 'muted'
  );
  let labelText = $derived(
    status === 'online' ? 'OK' : status === 'offline' ? 'KO' : '-'
  );
  let tooltipText = $derived(
    onclick
      ? 'Test Stream Link Status'
      : status === 'online'
        ? 'Stream Link Online (OK)'
        : status === 'offline'
          ? 'Stream Link Offline (KO)'
          : 'Stream Link Unchecked'
  );
</script>

{#if onclick}
  <button
    type="button"
    {onclick}
    class="cursor-pointer shrink-0 inline-flex {className}"
    title={tooltipText}
  >
    <Badge {variant}>
      {labelText}
    </Badge>
  </button>
{:else}
  <Badge {variant} title={tooltipText} class={className}>
    {labelText}
  </Badge>
{/if}
