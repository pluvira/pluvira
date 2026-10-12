<script lang="ts">
  import { onMount } from 'svelte';
  import { SettingsController } from './utils/SettingsController.svelte';
  import { MACRO_SETTINGS_TABS, type MacroSettingsTabKey } from './utils/SettingsUtils';
  import SegmentedControl, { type SegmentOption } from '../ui/SegmentedControl.svelte';
  import GeneralTab from './tabs/GeneralTab.svelte';
  import SourcesTab from './tabs/SourcesTab.svelte';
  import UpdatesTab from './tabs/UpdatesTab.svelte';
  import BackupHubTab from './tabs/BackupHubTab.svelte';
  import { Save } from '@lucide/svelte';

  const controller = new SettingsController();

  const macroTabOptions: SegmentOption<MacroSettingsTabKey>[] = MACRO_SETTINGS_TABS.map((tab) => ({
    value: tab.key,
    label: tab.label,
    icon: tab.icon
  }));

  function refreshData() {
    controller.loadSettings();
  }

  function handleSave() {
    controller.saveSettings();
  }

  onMount(() => {
    refreshData();
  });
</script>

<div class="flex flex-col gap-6 w-full relative pb-20">

  <div class="w-full overflow-x-auto scrollbar-none scroll-smooth pb-1">
    <SegmentedControl
      options={macroTabOptions}
      value={controller.activeMacroTab}
      onchange={(val) => controller.setMacroTab(val)}
      class="w-full sm:w-auto"
    />
  </div>

  {#if controller.loading}
    <div class="state-empty !rounded-t-none">
      <span class="spinner mr-3"></span>
      <span class="text-sm font-bold">Loading configuration settings...</span>
    </div>
  {:else}
    {#if controller.activeMacroTab === 'general'}
      <GeneralTab {controller} bind:config={controller.config} />
    {:else if controller.activeMacroTab === 'sources'}
      <SourcesTab {controller} bind:config={controller.config} expandSource={controller.expandSource} />
    {:else if controller.activeMacroTab === 'updates'}
      <UpdatesTab {controller} bind:config={controller.config} bind:schedule={controller.schedule} />
    {:else if controller.activeMacroTab === 'backup'}
      <BackupHubTab {controller} onimportsuccess={refreshData} />
    {/if}
  {/if}

  <!-- Floating Round Save CTA Button (visible only when isDirty or saving) -->
  {#if controller.isDirty || controller.saving}
    <div class="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 z-40 animate-fade-in">
      <button
        type="button"
        disabled={controller.saving}
        onclick={handleSave}
        class="w-12 h-12 rounded-full bg-primary hover:opacity-90 active:opacity-80 text-primary-foreground flex items-center justify-center shadow-elevated cursor-pointer transition-transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed touch-btn"
        title="Save Configuration Changes"
        aria-label="Save Configuration Changes"
      >
        {#if controller.saving}
          <span class="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
        {:else}
          <Save class="w-5 h-5" />
        {/if}
      </button>
    </div>
  {/if}
</div>
