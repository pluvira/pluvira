<script lang="ts">
  import type { GlobalConfig, SchedulePayload } from '$lib/api/types';
  import type { SettingsController } from '../utils/SettingsController.svelte';
  import SegmentedControl, { type SegmentOption } from '../../ui/SegmentedControl.svelte';
  import SchedulerTab from './SchedulerTab.svelte';
  import NotificationsTab from './NotificationsTab.svelte';
  import { Clock, Bell } from '@lucide/svelte';
  import type { UpdatesSubTabKey } from '../utils/SettingsUtils';

  interface Props {
    config: GlobalConfig;
    schedule: SchedulePayload;
    controller: SettingsController;
  }

  let { config = $bindable(), schedule = $bindable(), controller }: Props = $props();

  const updatesSegments: SegmentOption<UpdatesSubTabKey>[] = [
    { value: 'scheduler', label: 'Scheduler', icon: Clock },
    { value: 'notifications', label: 'Notifications', icon: Bell }
  ];
</script>

<div class="flex flex-col gap-4 w-full text-xs">
  <div class="w-full">
    <SegmentedControl
      options={updatesSegments}
      bind:value={controller.updatesSubTab}
      onchange={(sub) => controller.setSubSegment('updates', sub)}
      class="touch-btn"
    />
  </div>

  {#if controller.updatesSubTab === 'scheduler'}
    <SchedulerTab {controller} bind:schedule />
  {:else if controller.updatesSubTab === 'notifications'}
    <NotificationsTab {controller} bind:config />
  {/if}
</div>
