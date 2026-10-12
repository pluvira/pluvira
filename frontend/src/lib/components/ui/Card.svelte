<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    title?: string;
    actions?: Snippet;
    children?: Snippet;
    class?: string;
  }

  let { title, actions, children, class: className = '' }: Props = $props();
</script>

<div class="surface-card p-4 {className}">
  {#if title || actions}
    <div class="flex items-center justify-between mb-3 border-b border-border/30 pb-2">
      {#if title}
        <h3 class="text-lg font-bold text-foreground">{title}</h3>
      {/if}
      {#if actions}
        <div class="flex items-center gap-2">
          {@render actions()}
        </div>
      {/if}
    </div>
  {/if}
  {#if children}
    {@render children()}
  {/if}
</div>
