<script lang="ts">
  import Dialog from '../../ui/Dialog.svelte';
  import Button from '../../ui/Button.svelte';
  import { ALL_CHANNEL_COLUMNS } from '../utils/ChannelsUtils';

  interface Props {
    visibleColumns?: string[];
    open?: boolean;
    onclose?: () => void;
    ontogglecolumn?: (key: string, visible: boolean) => void;
  }

  let {
    visibleColumns = $bindable(),
    open = $bindable(),
    onclose,
    ontogglecolumn
  }: Props = $props();

  function isColumnVisible(key: string): boolean {
    return (visibleColumns || []).includes(key);
  }

  function handleCheckChange(key: string, e: Event) {
    const target = e.target as HTMLInputElement;
    const checked = target.checked;
    if (ontogglecolumn) {
      ontogglecolumn(key, checked);
    } else {
      const current = visibleColumns || [];
      if (checked && !current.includes(key)) {
        visibleColumns = [...current, key];
      } else if (!checked) {
        visibleColumns = (visibleColumns || []).filter((k) => k !== key);
      }
    }
  }
</script>

<Dialog bind:open title="Customize Visible Elements" {onclose} class="max-w-md surface-modal !bg-card/95 backdrop-blur-md">
  {#snippet footer()}
    <Button variant="primary" size="sm" onclick={() => (open = false)} class="font-bold touch-btn">Close</Button>
  {/snippet}

  <div class="flex flex-col gap-3 w-full text-xs">
    <span class="text-muted-foreground">Toggle visibility of elements in the channel rows:</span>

    <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5 surface-darkest p-2.5 rounded border border-border/40 max-h-64 overflow-y-auto">
      {#each ALL_CHANNEL_COLUMNS as col (col.key)}
        <label class="flex items-center gap-2 text-foreground cursor-pointer hover:bg-card/80 p-1.5 rounded transition-colors select-none">
          <input
            type="checkbox"
            checked={isColumnVisible(col.key)}
            onchange={(e) => handleCheckChange(col.key, e)}
            class="rounded text-primary focus:ring-primary h-4 w-4 shrink-0"
          />
          <span class="font-semibold text-xs">{col.label}</span>
        </label>
      {/each}
    </div>
  </div>
</Dialog>
