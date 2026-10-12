<script lang="ts">
  import Dialog from '../../ui/Dialog.svelte';
  import Input from '../../ui/Input.svelte';
  import Button from '../../ui/Button.svelte';

  interface Props {
    title?: string;
    label?: string;
    suggestions?: string[];
    open?: boolean;
    onclose?: () => void;
    onapply?: (value: string) => void;
  }

  let {
    title = 'Bulk Edit Attribute',
    label = 'New Value',
    suggestions = [],
    open = $bindable(),
    onclose,
    onapply
  }: Props = $props();

  let inputValue = $state('');

  $effect(() => {
    if (open) {
      inputValue = '';
    }
  });

  function handleApply() {
    if (onapply) onapply(inputValue);
    open = false;
  }

  function selectSuggestion(sug: string) {
    inputValue = sug;
  }
</script>

<Dialog bind:open {title} {onclose}>
  {#snippet footer()}
    <Button variant="ghost" size="sm" onclick={() => (open = false)} class="touch-btn">Cancel</Button>
    <Button variant="primary" size="sm" onclick={handleApply} class="font-bold touch-btn">Apply to Selected</Button>
  {/snippet}
  <div class="flex flex-col gap-4 w-full text-xs">
    <Input {label} bind:value={inputValue} placeholder="Enter value..." />

    {#if suggestions.length > 0}
      <div class="flex flex-col gap-1 w-full">
        <span class="text-caps-label">Existing Values Suggestions:</span>
        <div class="surface-darkest border border-border/40 rounded-md p-2 max-h-36 overflow-y-auto flex flex-col gap-1">
          {#each suggestions as item, i (item + '_' + i)}
            <button
              type="button"
              onclick={() => selectSuggestion(item)}
              class="text-left text-foreground hover:text-foreground hover:bg-card px-2 py-1.5 rounded transition-colors text-xs truncate cursor-pointer"
            >
              {item}
            </button>
          {/each}
        </div>
      </div>
    {/if}

  </div>
</Dialog>
