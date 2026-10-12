<script lang="ts">
  import type { Snippet } from 'svelte';
  import { Dialog as BitsDialog } from 'bits-ui';
  import { X } from '@lucide/svelte';

  interface Props {
    open?: boolean;
    title?: string;
    onclose?: () => void;
    children?: Snippet;
    footer?: Snippet;
    class?: string;
  }

  let { open = $bindable(), title = '', onclose, children, footer, class: className = '' }: Props = $props();

  function handleOpenChange(isOpen: boolean) {
    open = isOpen;
    if (!isOpen && onclose) {
      onclose();
    }
  }
</script>

<BitsDialog.Root open={open ?? false} onOpenChange={handleOpenChange}>
  <BitsDialog.Portal>
    <BitsDialog.Overlay
      class="fixed inset-0 z-50 bg-black/60 transition-opacity duration-150"
    />
    <div class="fixed inset-0 z-50 flex items-end justify-center p-0 pointer-events-none">
      <BitsDialog.Content
        class="surface-modal w-full max-w-2xl overflow-hidden flex flex-col max-h-[85dvh] pointer-events-auto shadow-elevated focus:outline-hidden transition-all duration-150 {className}"
      >
        <!-- Mobile Drag / Sheet Handle Indicator -->
        <div class="w-12 h-1.5 bg-border/60 rounded-full mx-auto mt-2.5 mb-1 shrink-0"></div>

        <div class="flex items-center justify-between px-4 py-3 surface-header">
          <BitsDialog.Title class="text-base md:text-lg font-bold text-foreground truncate pr-2">
            {title}
          </BitsDialog.Title>
          <BitsDialog.Close
            class="btn-ghost !p-1 shrink-0 rounded-md text-muted-foreground hover:text-foreground cursor-pointer inline-flex items-center justify-center"
            aria-label="Close dialog"
          >
            <X class="w-4 h-4" />
          </BitsDialog.Close>
        </div>

        <div class="p-4 overflow-y-auto flex-1 text-xs">
          {#if children}
            {@render children()}
          {/if}
        </div>

        {#if footer}
          <div class="px-4 py-3 bg-background border-t border-border/20 flex justify-end gap-2 shrink-0">
            {@render footer()}
          </div>
        {/if}
      </BitsDialog.Content>
    </div>
  </BitsDialog.Portal>
</BitsDialog.Root>
