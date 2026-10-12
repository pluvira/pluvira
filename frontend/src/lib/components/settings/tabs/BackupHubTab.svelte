<script lang="ts">
  import type { SettingsController } from '../utils/SettingsController.svelte';
  import SegmentedControl, { type SegmentOption } from '../../ui/SegmentedControl.svelte';
  import BackupTab from './BackupTab.svelte';
  import HistoryTab from './HistoryTab.svelte';
  import { Archive, Activity } from '@lucide/svelte';
  import type { BackupSubTabKey } from '../utils/SettingsUtils';

  interface Props {
    controller: SettingsController;
    onimportsuccess?: () => void;
  }

  let { controller, onimportsuccess }: Props = $props();

  const backupSegments: SegmentOption<BackupSubTabKey>[] = [
    { value: 'backup', label: 'Backup & Restore', icon: Archive },
    { value: 'history', label: 'History & Logs', icon: Activity }
  ];
</script>

<div class="flex flex-col gap-4 w-full text-xs">
  <div class="w-full">
    <SegmentedControl
      options={backupSegments}
      bind:value={controller.backupSubTab}
      onchange={(sub) => controller.setSubSegment('backup', sub)}
      class="touch-btn"
    />
  </div>

  {#if controller.backupSubTab === 'backup'}
    <BackupTab {onimportsuccess} />
  {:else if controller.backupSubTab === 'history'}
    <HistoryTab {controller} />
  {/if}
</div>
