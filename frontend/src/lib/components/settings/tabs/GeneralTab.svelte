<script lang="ts">
  import type { GlobalConfig } from '$lib/api/types';
  import type { SettingsController } from '../utils/SettingsController.svelte';
  import SegmentedControl, { type SegmentOption } from '../../ui/SegmentedControl.svelte';
  import {
    GeneralSystemSection,
    GeneralAdvancedSection,
    GeneralSecuritySection,
    GeneralDiagnosticsSection,
    ThemePreviewSelector
  } from '../sections';
  import { Sliders, SlidersHorizontal, Palette } from '@lucide/svelte';
  import type { GeneralSubTabKey } from '../utils/SettingsUtils';

  interface Props {
    config: GlobalConfig;
    controller: SettingsController;
  }

  let { config = $bindable(), controller }: Props = $props();

  const generalSegments: SegmentOption<GeneralSubTabKey>[] = [
    { value: 'system', label: 'System', icon: Sliders },
    { value: 'advanced', label: 'Advanced', icon: SlidersHorizontal },
    { value: 'theme', label: 'Theme', icon: Palette }
  ];
</script>

<div class="flex flex-col gap-4 w-full text-xs">
  <div class="w-full">
    <SegmentedControl
      options={generalSegments}
      bind:value={controller.generalSubTab}
      onchange={(sub) => controller.setSubSegment('general', sub)}
      class="touch-btn"
    />
  </div>

  {#if controller.generalSubTab === 'system'}
    <GeneralSecuritySection {controller} bind:config />
    <GeneralSystemSection {controller} bind:config />
    <GeneralDiagnosticsSection {controller} bind:config />
  {:else if controller.generalSubTab === 'advanced'}
    <GeneralAdvancedSection {controller} bind:config />
  {:else if controller.generalSubTab === 'theme'}
    <ThemePreviewSelector />
  {/if}
</div>
