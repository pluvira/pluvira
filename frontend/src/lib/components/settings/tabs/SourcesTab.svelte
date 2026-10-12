<script lang="ts">
  import type { GlobalConfig } from '$lib/api/types';
  import type { SettingsController } from '../utils/SettingsController.svelte';
  import SegmentedControl, { type SegmentOption } from '../../ui/SegmentedControl.svelte';
  import PlaylistsTab from './PlaylistsTab.svelte';
  import IptvSourcesTab from './IptvSourcesTab.svelte';
  import EpgSourcesTab from './EpgSourcesTab.svelte';
  import { GlobalRewritesSection } from '../sections';
  import { ListMusic, Tv, Calendar, FileCode } from '@lucide/svelte';
  import type { SourcesSubTabKey } from '../utils/SettingsUtils';

  interface Props {
    config: GlobalConfig;
    controller: SettingsController;
    expandSource?: string | null;
  }

  let { config = $bindable(), controller, expandSource = null }: Props = $props();

  const sourcesSegments: SegmentOption<SourcesSubTabKey>[] = [
    { value: 'playlists', label: 'Curated Lists', icon: ListMusic },
    { value: 'iptv', label: 'IPTV Playlists', icon: Tv },
    { value: 'epg', label: 'EPG Guides', icon: Calendar },
    { value: 'rewrites', label: 'Rewrites & Overrides', icon: FileCode }
  ];
</script>

<div class="flex flex-col gap-4 w-full text-xs">
  <div class="w-full">
    <SegmentedControl
      options={sourcesSegments}
      bind:value={controller.sourcesSubTab}
      onchange={(sub) => controller.setSubSegment('sources', sub)}
      class="touch-btn"
    />
  </div>

  {#if controller.sourcesSubTab === 'playlists'}
    <PlaylistsTab />
  {:else if controller.sourcesSubTab === 'iptv'}
    <IptvSourcesTab {controller} bind:config {expandSource} />
  {:else if controller.sourcesSubTab === 'epg'}
    <EpgSourcesTab {controller} bind:config {expandSource} />
  {:else if controller.sourcesSubTab === 'rewrites'}
    <GlobalRewritesSection {controller} bind:config />
  {/if}
</div>
