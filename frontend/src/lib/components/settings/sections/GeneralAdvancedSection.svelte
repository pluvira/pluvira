<script lang="ts">
  import type { GlobalConfig } from '$lib/api/types';
  import type { SettingsController } from '../utils/SettingsController.svelte';
  import Card from '../../ui/Card.svelte';
  import Input from '../../ui/Input.svelte';
  import Select from '../../ui/Select.svelte';
  import { formatNewlineList } from '$lib/utils/stringUtils';

  interface Props {
    config: GlobalConfig;
    controller?: SettingsController;
  }

  let { config = $bindable(), controller }: Props = $props();

  const isDev = Boolean((import.meta as any).env?.DEV);
</script>

<div class="flex flex-col gap-6 w-full text-xs">
  <!-- System Language & Regional Locales (Development Only) -->
  {#if isDev}
    <Card title="System Language & Regional Locales (Development Only)">
      <div class="flex flex-col gap-2 w-full">
        <span class="text-xs text-muted-foreground">
          Select system primary language for EPG stop-words dictionaries and regional date formatting:
        </span>
        <div class="w-full sm:w-80">
          <Select
            label="System Primary Language"
            bind:value={config.settings.language}
            options={[
              { label: 'Italiano (IT)', value: 'it' },
              { label: 'English (EN)', value: 'en' },
              { label: 'Español (ES)', value: 'es' },
              { label: 'Français (FR)', value: 'fr' },
              { label: 'Deutsch (DE)', value: 'de' },
              { label: 'Português (PT)', value: 'pt' }
            ]}
          />
        </div>
      </div>
    </Card>
  {/if}

  <!-- Polite Scanner Options -->
  <Card title="Polite Scanner Options">
    <div class="flex flex-col gap-2 w-full">
      <span class="text-xs text-muted-foreground font-bold uppercase tracking-wider">Polite Scanner (Anti-Ban Delays)</span>
      {#if config.settings.link_test_settings}
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full sm:w-80">
          <Input type="number" label="Min Delay (s)" bind:value={config.settings.link_test_settings.min_delay} />
          <Input type="number" label="Max Delay (s)" bind:value={config.settings.link_test_settings.max_delay} />
        </div>
      {/if}
    </div>
  </Card>

  <!-- UI Responsiveness & Search Debounce -->
  <Card title="UI Responsiveness & Search Debounce">
    <div class="flex flex-col gap-2 w-full">
      <span class="text-xs text-muted-foreground mb-2">Configure the delay in milliseconds before text search inputs execute filtering to prevent UI lag.</span>
      <div class="w-full sm:w-64">
        <Input type="number" label="Search Debounce Delay (ms)" bind:value={config.settings.search_debounce_ms} />
      </div>
    </div>
  </Card>

  <!-- EPG Intelligent Search Custom Stop-Words -->
  <Card title="EPG Intelligent Search Custom Stop-Words">
    <div class="flex flex-col gap-2 w-full">
      <span class="text-xs text-muted-foreground">
        Specify custom words to ignore during intelligent EPG programme searches. Enter one word per line:
      </span>
      <textarea
        value={formatNewlineList(config.settings.custom_stopwords)}
        oninput={(e) => controller?.updateCustomStopwords((e.target as HTMLTextAreaElement).value)}
        rows={4}
        placeholder="e.g. special&#10;live&#10;repeat"
        class="textarea-base"
      ></textarea>
    </div>
  </Card>

  <!-- EPG Intelligent Search Methodologies (A, B, C, D) -->
  <Card title="EPG Intelligent Search Methodologies (A, B, C, D)">
    <div class="flex flex-col gap-3 w-full">
      <span class="text-xs text-muted-foreground">Select active intelligent search methodologies for EPG programme filtering:</span>

      {#if config.settings.search_methods}
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-card border border-border/30 p-3 rounded">
          <label class="flex items-center gap-2 cursor-pointer text-foreground font-bold">
            <input type="checkbox" bind:checked={config.settings.search_methods.method_a} class="rounded text-primary" />
            <span>Method A: Relevance Scoring (Title 100pt > Partial 50pt > Desc 20pt)</span>
          </label>

          <label class="flex items-center gap-2 cursor-pointer text-foreground font-bold">
            <input type="checkbox" bind:checked={config.settings.search_methods.method_b} class="rounded text-primary" />
            <span>Method B: Tokenization & Multi-term Stop-Words Removal</span>
          </label>

          <label class="flex items-center gap-2 cursor-pointer text-foreground font-bold">
            <input type="checkbox" bind:checked={config.settings.search_methods.method_c} class="rounded text-primary" />
            <span>Method C: Diacritics/Accents Stripping & Whole-Word Boundary Match</span>
          </label>

          <label class="flex items-center gap-2 cursor-pointer text-foreground font-bold">
            <input type="checkbox" bind:checked={config.settings.search_methods.method_d} class="rounded text-primary" />
            <span>Method D: Time-Aware Boost (Live +30pt, Upcoming +15pt)</span>
          </label>
        </div>
      {/if}
    </div>
  </Card>
</div>
