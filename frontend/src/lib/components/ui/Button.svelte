<script lang="ts">
  import type { Snippet } from 'svelte';
  import { Button as BitsButton } from 'bits-ui';

  interface Props {
    variant?: 'primary' | 'secondary' | 'outline' | 'danger' | 'ghost';
    size?: 'sm' | 'md' | 'lg';
    disabled?: boolean;
    type?: 'button' | 'submit' | 'reset';
    title?: string;
    'aria-label'?: string;
    onclick?: (e: MouseEvent) => void;
    children?: Snippet;
    class?: string;
  }

  let {
    variant = 'primary',
    size = 'md',
    disabled = false,
    type = 'button',
    title = undefined,
    'aria-label': ariaLabel = undefined,
    onclick,
    children,
    class: className = ''
  }: Props = $props();

  const variantClasses = {
    primary: 'btn-primary',
    secondary: 'btn-secondary',
    outline: 'btn-outline',
    danger: 'btn-danger',
    ghost: 'btn-ghost'
  };

  const sizeClasses = {
    sm: 'px-2 py-1 text-xs rounded-sm',
    md: 'px-4 py-2 text-sm rounded-md font-bold',
    lg: 'px-6 py-3 text-base rounded-lg font-bold'
  };
</script>

<BitsButton.Root
  {type}
  {disabled}
  {title}
  aria-label={ariaLabel}
  {onclick}
  class="{variantClasses[variant]} {sizeClasses[size]} {className}"
>
  {#if children}
    {@render children()}
  {/if}
</BitsButton.Root>
