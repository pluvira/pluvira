<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    label?: string;
    loading?: boolean;
    disabled?: boolean;
    active?: boolean;
    variant?: 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'muted';
    onclick?: (e: MouseEvent | KeyboardEvent) => void;
    children?: Snippet;
    class?: string;
  }

  let {
    label = '',
    loading = false,
    disabled = false,
    active = false,
    variant = 'default',
    onclick,
    children,
    class: className = ''
  }: Props = $props();

  const variantClasses: Record<string, string> = {
    default: 'text-foreground/80 hover:text-foreground hover:bg-card',
    primary: 'text-primary hover:text-primary/80 hover:bg-primary/10',
    success: 'text-success hover:text-success/80 hover:bg-success/10',
    warning: 'text-warning hover:text-warning/80 hover:bg-warning/10',
    danger: 'text-destructive hover:text-destructive/80 hover:bg-destructive/10',
    muted: 'text-muted-foreground/60 hover:text-muted-foreground hover:bg-card'
  };

  function handleKeyDown(e: KeyboardEvent) {
    if (disabled || loading) return;
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onclick?.(e);
    }
  }

  function handleClick(e: MouseEvent) {
    if (disabled || loading) return;
    onclick?.(e);
  }
</script>

<!-- svelte-ignore a11y_no_redundant_roles -->
<button
  type="button"
  role="button"
  tabindex={disabled ? -1 : 0}
  aria-pressed={active || undefined}
  title={label || undefined}
  aria-label={label || 'Indicator'}
  aria-disabled={disabled || loading}
  disabled={disabled || loading}
  onclick={handleClick}
  onkeydown={handleKeyDown}
  class="actionable-indicator inline-flex items-center justify-center p-1 rounded transition-colors cursor-pointer touch-btn disabled:cursor-not-allowed disabled:opacity-50 {variantClasses[variant] || variantClasses.default} {className}"
>
  {#if loading}
    <span class="spinner w-3 h-3 shrink-0" aria-hidden="true"></span>
  {:else if children}
    {@render children()}
  {/if}
</button>
