<script lang="ts">
  import Badge from '../../ui/Badge.svelte';
  import { Eye, EyeOff } from '@lucide/svelte';

  interface Props {
    included?: boolean;
    onclick?: (e: MouseEvent) => void;
    class?: string;
  }

  let {
    included = true,
    onclick,
    class: className = ''
  }: Props = $props();

  let variant = $derived<'success' | 'error'>(included ? 'success' : 'error');
  let labelText = $derived(included ? 'VISIBLE' : 'HIDDEN');
  let tooltipText = $derived(
    onclick
      ? (included ? 'Click to hide channel from catalog' : 'Click to show channel in catalog')
      : (included ? 'Visible in catalog' : 'Hidden from catalog')
  );
</script>

{#if onclick}
  <button
    type="button"
    {onclick}
    class="cursor-pointer shrink-0 inline-flex items-center gap-1 {className}"
    title={tooltipText}
  >
    <Badge {variant} class="flex items-center gap-1">
      {#if included}
        <Eye class="w-3 h-3" />
      {:else}
        <EyeOff class="w-3 h-3" />
      {/if}
      <span>{labelText}</span>
    </Badge>
  </button>
{:else}
  <Badge {variant} title={tooltipText} class="flex items-center gap-1 {className}">
    {#if included}
      <Eye class="w-3 h-3" />
    {:else}
      <EyeOff class="w-3 h-3" />
    {/if}
    <span>{labelText}</span>
  </Badge>
{/if}
