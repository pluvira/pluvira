<script lang="ts">
  import ChannelDetailsModal from './ChannelDetailsModal.svelte';
  import EditMetadataModal from './EditMetadataModal.svelte';
  import EditLogoModal from './EditLogoModal.svelte';
  import EditFieldModal from './EditFieldModal.svelte';
  import EpgMappingModal from './EpgMappingModal.svelte';
  import DeepLinkTestModal from './DeepLinkTestModal.svelte';
  import ChannelMergeSheet from './ChannelMergeSheet.svelte';
  import type { ChannelItem, ChannelRewritePayload } from '$lib/api/types';

  interface Props {
    channel?: ChannelItem | null;
    showDetailsModal?: boolean;
    showEditModal?: boolean;
    showLogoModal?: boolean;
    showFieldModal?: boolean;
    showScannerModal?: boolean;
    showMappingModal?: boolean;
    showMergeSheet?: boolean;
    selectedMergeChannel?: ChannelItem | null;
    field?: ChannelRewritePayload['field'];
    fieldLabel?: string;
    ontoggleinclusion?: (channel: ChannelItem) => void;
    onplaystream?: (channel: ChannelItem) => void;
    onopenfailover?: (channel: ChannelItem) => void;
    onsaved?: () => void;
  }

  let {
    channel = null,
    showDetailsModal = $bindable(),
    showEditModal = $bindable(),
    showLogoModal = $bindable(),
    showFieldModal = $bindable(),
    showScannerModal = $bindable(),
    showMappingModal = $bindable(),
    showMergeSheet = $bindable(),
    selectedMergeChannel = null,
    field = $bindable(),
    fieldLabel = $bindable(),
    ontoggleinclusion,
    onplaystream,
    onopenfailover,
    onsaved
  }: Props = $props();

  function handleOpenField(f: ChannelRewritePayload['field'], label: string) {
    field = f;
    fieldLabel = label;
    showFieldModal = true;
  }
</script>

<ChannelDetailsModal
  {channel}
  bind:open={showDetailsModal}
  {ontoggleinclusion}
  ontestlink={() => (showScannerModal = true)}
  oneditmapping={() => (showMappingModal = true)}
  oneditname={() => handleOpenField('name', 'Channel Name')}
  oneditlogo={() => (showLogoModal = true)}
  onediturl={() => handleOpenField('url', 'Stream URL')}
  onedituseragent={() => handleOpenField('user_agent', 'User-Agent')}
  oneditmetadata={() => (showEditModal = true)}
  {onplaystream}
  onopenfailover={onopenfailover ? (ch) => onopenfailover(ch) : () => { showMergeSheet = true; }}
/>

<EditMetadataModal {channel} bind:open={showEditModal} {onsaved} />
<EditLogoModal {channel} bind:open={showLogoModal} {onsaved} />
<EditFieldModal
  {channel}
  {field}
  {fieldLabel}
  bind:open={showFieldModal}
  {onsaved}
/>
<DeepLinkTestModal {channel} bind:open={showScannerModal} {onsaved} />
<EpgMappingModal {channel} bind:open={showMappingModal} {onsaved} />
<ChannelMergeSheet
  channel={selectedMergeChannel || channel}
  bind:open={showMergeSheet}
  {onsaved}
/>
