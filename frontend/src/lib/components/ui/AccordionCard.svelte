<script lang="ts">
  import type { Snippet } from 'svelte';
  import Button from './Button.svelte';
  import Badge from './Badge.svelte';
  import { Accordion as BitsAccordion } from 'bits-ui';
  import { ChevronDown, ChevronUp, RotateCw, Trash2 } from '@lucide/svelte';

  interface Props {
    title?: string;
    open?: boolean;
    badgeText?: string;
    badgeVariant?: 'primary' | 'success' | 'warning' | 'error' | 'muted';
    statusDot?: 'success' | 'error' | 'muted' | null;
    statusDotTitle?: string;
    index?: number;
    totalCount?: number;
    showRefresh?: boolean;
    showMove?: boolean;
    showDelete?: boolean;
    ontoggle?: (open: boolean) => void;
    onrefresh?: () => void;
    onmoveup?: () => void;
    onmovedown?: () => void;
    ondelete?: () => void;
    children?: Snippet;
    class?: string;
  }

  let {
    title = '',
    open = $bindable(),
    badgeText = '',
    badgeVariant = 'muted',
    statusDot = null,
    statusDotTitle = '',
    index = 0,
    totalCount = 0,
    showRefresh = false,
    showMove = true,
    showDelete = true,
    ontoggle,
    onrefresh,
    onmoveup,
    onmovedown,
    ondelete,
    children,
    class: className = ''
  }: Props = $props();

  let accordionValue = $state<string | undefined>(open ? 'item' : undefined);

  $effect(() => {
    accordionValue = open ? 'item' : undefined;
  });

  function handleValueChange(val: string | undefined) {
    const isOpen = val === 'item';
    open = isOpen;
    ontoggle?.(isOpen);
  }
</script>

<div class="surface-card overflow-hidden !p-0 {className}">
  <BitsAccordion.Root
    type="single"
    value={accordionValue}
    onValueChange={handleValueChange}
  >
    <BitsAccordion.Item value="item">
      <BitsAccordion.Header class="flex items-center justify-between px-4 py-3 surface-header">
        <BitsAccordion.Trigger
          class="flex items-center gap-3 text-left font-bold text-foreground text-sm cursor-pointer flex-grow select-none truncate mr-4 group"
        >
          <ChevronDown class="w-4 h-4 text-muted-foreground shrink-0 transition-transform duration-200 group-data-[state=open]:rotate-180" />
          {#if statusDot}
            <span
              class="w-2.5 h-2.5 rounded-full shrink-0 {
                statusDot === 'success'
                  ? 'bg-primary shadow-xs shadow-primary/50'
                  : statusDot === 'error'
                    ? 'bg-destructive shadow-xs shadow-destructive/50'
                    : 'bg-muted-foreground/40'
              }"
              title={statusDotTitle || (statusDot === 'success' ? 'Active' : statusDot === 'error' ? 'Connection Error' : 'Disabled')}
            ></span>
          {/if}
          <span class="truncate">{title || 'Item'}</span>
          {#if badgeText}
            <Badge variant={badgeVariant}>{badgeText}</Badge>
          {/if}
        </BitsAccordion.Trigger>

        <div class="flex items-center gap-1.5 shrink-0">
          {#if showRefresh && onrefresh}
            <Button
              variant="ghost"
              size="sm"
              onclick={(e) => { e.stopPropagation(); onrefresh(); }}
              class="!p-1 text-xs text-primary hover:text-primary/80"
              title="Refresh Item"
            >
              <RotateCw class="w-3.5 h-3.5" />
            </Button>
          {/if}

          {#if showMove}
            <Button
              variant="ghost"
              size="sm"
              disabled={index === 0}
              onclick={(e) => { e.stopPropagation(); onmoveup?.(); }}
              class="!p-1 text-xs"
              title="Move Up"
            >
              <ChevronUp class="w-3.5 h-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              disabled={index >= totalCount - 1}
              onclick={(e) => { e.stopPropagation(); onmovedown?.(); }}
              class="!p-1 text-xs"
              title="Move Down"
            >
              <ChevronDown class="w-3.5 h-3.5" />
            </Button>
          {/if}

          {#if showDelete && ondelete}
            <Button
              variant="ghost"
              size="sm"
              onclick={(e) => { e.stopPropagation(); ondelete(); }}
              class="!p-1 text-xs text-destructive hover:opacity-90"
              title="Delete Item"
            >
              <Trash2 class="w-3.5 h-3.5" />
            </Button>
          {/if}
        </div>
      </BitsAccordion.Header>

      <BitsAccordion.Content class="p-4 flex flex-col gap-4 bg-card border-t border-border/20 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0">
        {#if children}
          {@render children()}
        {/if}
      </BitsAccordion.Content>
    </BitsAccordion.Item>
  </BitsAccordion.Root>
</div>
