<script lang="ts">
  import Card from '../../ui/Card.svelte';
  import Button from '../../ui/Button.svelte';
  import Badge from '../../ui/Badge.svelte';
  import Input from '../../ui/Input.svelte';
  import Select from '../../ui/Select.svelte';
  import SegmentedControl, { type SegmentOption } from '../../ui/SegmentedControl.svelte';
  import { Tv, Settings } from '@lucide/svelte';
  import { ThemePreviewController, THEME_OPTIONS } from '../utils/ThemePreviewController.svelte';

  const controller = new ThemePreviewController();
  let sampleSegment = $state<'live' | 'channels' | 'settings'>('live');
  const sampleSegments: SegmentOption<'live' | 'channels' | 'settings'>[] = [
    { value: 'live', label: 'Live TV', icon: Tv },
    { value: 'channels', label: 'Channels' },
    { value: 'settings', label: 'Settings', icon: Settings }
  ];
</script>

<Card title="UI Theme Customization & Live Preview">
  <div class="flex flex-col gap-4 w-full">
    <span class="text-xs text-muted-foreground">
      Select a theme to preview its colors and components live before applying it to your session.
    </span>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 items-start">
      <!-- Selector & Apply Controls -->
      <div class="flex flex-col gap-3 md:col-span-1">
        <Select
          label="Select Theme to Preview"
          bind:value={controller.previewTheme}
          options={THEME_OPTIONS.map((t) => ({ label: t.label, value: t.value }))}
        />

        <div class="flex flex-col gap-1 bg-card border border-border p-3 rounded text-xs">
          <span class="font-bold text-foreground">Theme Notes:</span>
          <span class="text-muted-foreground text-[11px]">
            {THEME_OPTIONS.find((t) => t.value === controller.previewTheme)?.description || ''}
          </span>
        </div>

        <div class="flex items-center gap-2 mt-1">
          <Button
            variant="primary"
            size="sm"
            disabled={controller.activeTheme === controller.previewTheme}
            onclick={() => controller.applyActiveTheme()}
            class="font-bold text-xs touch-btn"
          >
            Apply Theme
          </Button>

          {#if controller.activeTheme !== controller.previewTheme}
            <Button
              variant="ghost"
              size="sm"
              onclick={() => controller.resetPreview()}
              class="text-xs touch-btn"
            >
              Reset
            </Button>
          {/if}
        </div>
      </div>

      <!-- Live Isolated Preview Box -->
      <div class="md:col-span-2 flex flex-col gap-2">
        <span class="text-xs font-bold text-muted-foreground uppercase tracking-wider">
          Live Component Preview ({controller.previewTheme})
        </span>

        <div
          data-theme={controller.previewTheme}
          class="surface-card p-4 rounded-lg border border-border bg-background text-foreground flex flex-col gap-3 transition-colors duration-200 shadow-card"
        >
          <!-- Mock Header with Live Indicator -->
          <div class="flex items-center justify-between p-2.5 surface-header rounded">
            <div class="flex items-center gap-2">
              <span class="font-extrabold text-sm text-primary tracking-wider uppercase">Pluvira App</span>
              <span class="flex items-center gap-1 text-[11px] font-bold text-primary bg-primary/10 px-2 py-0.5 rounded border border-primary/30">
                <span class="w-1.5 h-1.5 rounded-full bg-primary animate-pulse"></span>
                LIVE
              </span>
            </div>
            <Badge variant="primary">PRO EDITION</Badge>
          </div>

          <!-- Sample SegmentedControl -->
          <div class="w-full">
            <SegmentedControl
              options={sampleSegments}
              bind:value={sampleSegment}
            />
          </div>

          <!-- Sample Interactive Card with Form Controls -->
          <div class="bg-card border border-border p-3 rounded flex flex-col gap-3">
            <div class="flex items-center justify-between border-b border-border/40 pb-2">
              <div class="flex flex-col">
                <span class="font-bold text-foreground text-xs">Sample Channel Card</span>
                <span class="text-muted-foreground text-[11px]">Semantic design tokens with active border accent</span>
              </div>
              <Badge variant="success">Active</Badge>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 items-end">
              <Input label="Sample Text Input" value="Channel stream URL..." disabled={false} />
              <Select
                label="Stream Quality"
                value="1080p"
                options={[
                  { label: 'Full HD 1080p', value: '1080p' },
                  { label: '4K Ultra HD', value: '4k' }
                ]}
              />
            </div>

            <div class="flex items-center gap-2 flex-wrap pt-1">
              <Button variant="primary" size="sm">Primary</Button>
              <Button variant="secondary" size="sm">Secondary</Button>
              <Button variant="outline" size="sm">Outline</Button>
              <Button variant="danger" size="sm">Danger</Button>
              <Button variant="ghost" size="sm" disabled={true}>Disabled</Button>
            </div>
          </div>

          <!-- Sample Badges Row -->
          <div class="flex items-center gap-2 flex-wrap text-xs pt-1 border-t border-border">
            <Badge variant="primary">PRIMARY</Badge>
            <Badge variant="success">ONLINE</Badge>
            <Badge variant="warning">BACKUP</Badge>
            <Badge variant="error">OFFLINE</Badge>
            <Badge variant="muted">MUTED</Badge>
            <span class="text-border">|</span>
            <Badge variant="primary">MERGED +2</Badge>
            <Badge variant="warning">PROXY</Badge>
            <Badge variant="success">INC</Badge>
          </div>
        </div>
      </div>
    </div>
  </div>
</Card>
