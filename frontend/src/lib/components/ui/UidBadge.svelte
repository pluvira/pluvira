<script lang="ts">
  import { formatCrockfordId } from '$lib/utils/crockfordUtils';
  import { copyToClipboard } from '$lib/utils/clipboardUtils';
  import { toastStore } from '$lib/stores/toastStore';
  import { Copy, Check } from '@lucide/svelte';

  interface Props {
    uid?: string | null;
    showCopy?: boolean;
    showLabel?: boolean;
    label?: string;
    size?: 'sm' | 'md' | 'lg';
    variant?: 'default' | 'success' | 'primary' | 'muted';
    class?: string;
  }

  let {
    uid,
    showCopy = true,
    showLabel = false,
    label = 'UID',
    size = 'md',
    variant = 'default',
    class: className = ''
  }: Props = $props();

  let copied = $state(false);
  let copyTimer: ReturnType<typeof setTimeout> | null = null;

  let formattedUid = $derived(formatCrockfordId(uid) || '----');
  let isValid = $derived(Boolean(formattedUid && formattedUid !== '----'));

  const sizeClasses: Record<string, string> = {
    sm: 'px-2 py-0.5 text-[10px]',
    md: 'px-2.5 py-1 text-xs',
    lg: 'px-3.5 py-1.5 text-sm'
  };

  const variantClasses: Record<string, string> = {
    default: 'border-border/60 bg-card text-primary',
    primary: 'border-primary/40 bg-primary/10 text-primary',
    success: 'border-primary/40 bg-primary/10 text-primary',
    muted: 'border-border/40 bg-muted/20 text-muted-foreground'
  };

  async function handleCopy() {
    if (!isValid) return;
    const success = await copyToClipboard(formattedUid);
    if (success) {
      copied = true;
      if (copyTimer) clearTimeout(copyTimer);
      copyTimer = setTimeout(() => {
        copied = false;
      }, 2000);
      toastStore.info(`Copied UID ${formattedUid} to clipboard.`);
    } else {
      toastStore.error('Failed to copy UID to clipboard.');
    }
  }
</script>

<div
  class="inline-flex items-center gap-1.5 rounded-md border font-mono font-bold tracking-wider {sizeClasses[size] || sizeClasses.md} {variantClasses[variant] || variantClasses.default} {className}"
  title={isValid ? `UID: ${formattedUid}` : 'No UID Available'}
>
  {#if showLabel}
    <span class="font-sans font-semibold tracking-normal text-muted-foreground text-[10px] uppercase">
      {label}:
    </span>
  {/if}
  <span>{formattedUid}</span>

  {#if showCopy && isValid}
    <button
      type="button"
      onclick={handleCopy}
      class="ml-0.5 rounded p-0.5 text-muted-foreground transition-colors hover:text-foreground focus:outline-none cursor-pointer"
      title="Copy UID"
      aria-label="Copy UID"
    >
      {#if copied}
        <Check class="size-3.5 text-primary" />
      {:else}
        <Copy class="size-3.5" />
      {/if}
    </button>
  {/if}
</div>
