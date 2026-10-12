<script lang="ts">
  import Button from '../ui/Button.svelte';
  import { Radio, Play } from '@lucide/svelte';

  interface Props {
    ontestlink?: () => void;
    onplaystream?: () => void;
    testTitle?: string;
    playTitle?: string;
    class?: string;
  }

  let {
    ontestlink,
    onplaystream,
    testTitle = 'Test Stream Link',
    playTitle = 'Play Live Stream',
    class: className = ''
  }: Props = $props();
</script>

<div class="flex items-center gap-1 {className}">
  {#if ontestlink}
    <Button variant="ghost" size="sm" onclick={() => ontestlink?.()} class="!p-1 text-xs" title={testTitle}>
      <Radio class="w-3.5 h-3.5" />
    </Button>
  {/if}
  {#if onplaystream}
    <Button variant="ghost" size="sm" onclick={() => onplaystream?.()} class="!p-1 text-xs" title={playTitle}>
      <Play class="w-3.5 h-3.5" />
    </Button>
  {/if}
</div>
