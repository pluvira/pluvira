<script lang="ts">
  import { fly } from 'svelte/transition';
  import { cubicOut } from 'svelte/easing';
  import { toastStore, type ToastNotification } from '$lib/stores/toastStore';
  import { X, CheckCircle2, AlertTriangle, AlertCircle, Info } from '@lucide/svelte';

  let toasts: ToastNotification[] = $state([]);

  toastStore.subscribe((value) => {
    toasts = value;
  });

  const typeConfig = {
    info: {
      border: 'border-primary',
      text: 'text-primary',
      icon: Info
    },
    success: {
      border: 'border-primary',
      text: 'text-primary',
      icon: CheckCircle2
    },
    warning: {
      border: 'border-primary/80',
      text: 'text-primary',
      icon: AlertTriangle
    },
    error: {
      border: 'border-destructive',
      text: 'text-destructive',
      icon: AlertCircle
    }
  };

  const typeClasses = {
    info: 'bg-card border-primary text-card-foreground',
    success: 'bg-card border-primary text-card-foreground',
    warning: 'bg-card border-primary/80 text-card-foreground',
    error: 'bg-card border-destructive text-card-foreground'
  };
</script>

<div class="fixed bottom-4 right-4 z-[9999] flex flex-col gap-2 max-w-md w-full pointer-events-none">
  {#each toasts as toast (toast.id)}
    {@const config = typeConfig[toast.type] || typeConfig.info}
    {@const IconComp = config.icon}
    <div
      transition:fly={{ y: 16, duration: 300, easing: cubicOut }}
      class="flex items-start justify-between p-3 rounded-md border-l-4 shadow-elevated pointer-events-auto {typeClasses[toast.type]}"
    >
      <div class="flex items-start gap-2.5 flex-1 mr-2 min-w-0">
        <IconComp class="w-4 h-4 shrink-0 mt-0.5 {config.text}" />
        <p class="text-sm font-semibold break-words whitespace-normal flex-1 leading-snug">{toast.message}</p>
      </div>
      <button
        type="button"
        onclick={() => toastStore.remove(toast.id)}
        class="text-muted-foreground hover:text-foreground text-xs p-1 rounded cursor-pointer shrink-0 mt-[-2px]"
        aria-label="Dismiss toast"
      >
        <X class="w-3.5 h-3.5" />
      </button>
    </div>
  {/each}
</div>
