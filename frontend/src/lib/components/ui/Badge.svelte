<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    variant?: 'primary' | 'success' | 'warning' | 'error' | 'muted';
    title?: string;
    children?: Snippet;
    class?: string;
  }

  let { variant = 'primary', title, children, class: className = '' }: Props = $props();

  const variantClasses = {
    primary: 'badge-primary',
    success: 'badge-success',
    warning: 'badge-warning',
    error: 'badge-error',
    muted: 'badge-muted'
  };
</script>

<span {title} class="{variantClasses[variant]} {className}">
  {#if children}
    {@render children()}
  {/if}
</span>
