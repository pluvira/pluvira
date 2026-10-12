<script lang="ts">
  import Badge from '../../ui/Badge.svelte';
  import Button from '../../ui/Button.svelte';
  import Input from '../../ui/Input.svelte';
  import Select from '../../ui/Select.svelte';
  import { STREAM_PRESETS, type OnboardingController } from '../OnboardingController.svelte';
  import { Info, ArrowRight, ArrowLeft } from '@lucide/svelte';

  interface Props {
    controller: OnboardingController;
    class?: string;
  }

  let { controller, class: className }: Props = $props();

  const presetOptions = STREAM_PRESETS.map((p) => ({
    label: p.label,
    value: p.key
  }));

  function handlePresetChange(e: Event) {
    const target = e.target as HTMLSelectElement;
    if (target) {
      controller.selectPreset(target.value);
    }
  }
</script>

<div class="flex flex-col gap-3.5 {className || ''}">
  <div class="flex items-center gap-2">
    <Badge variant="primary">IPTV Playlist</Badge>
    <h3 class="text-base font-bold text-foreground">Configure Initial Source</h3>
  </div>

  <div class="flex flex-col gap-2.5">
    <Select
      id="onboarding-preset-select"
      label="Public Streams Preset"
      options={presetOptions}
      value={controller.selectedPresetKey}
      onchange={handlePresetChange}
      disabled={controller.loading}
    />

    <Input
      id="onboarding-source-name"
      label="Source Name"
      placeholder="e.g. Public Channels IT"
      bind:value={controller.sourceName}
      disabled={controller.loading}
    />

    <Input
      id="onboarding-m3u-url"
      label="M3U Playlist URL"
      placeholder="https://example.com/playlist.m3u"
      bind:value={controller.m3uUrl}
      disabled={controller.loading}
    />


    <div class="surface-card flex items-start gap-2 rounded-lg border border-border/40 p-2.5 text-xs text-muted-foreground">
      <Info class="mt-0.5 size-3.5 shrink-0 text-primary" />
      <span>Public feeds from iptv-org are subject to broadcaster availability.</span>
    </div>

  </div>

  <div class="mt-1 flex items-center justify-between">
    <Button variant="outline" onclick={() => controller.prevStep()} disabled={controller.loading} class="gap-1.5">
      <ArrowLeft class="size-4" />
      <span>Back</span>
    </Button>

    <div class="flex items-center gap-2">
      <Button variant="ghost" onclick={() => controller.skipSourceStep()} disabled={controller.loading}>
        Skip for Now
      </Button>

      <Button
        variant="primary"
        onclick={() => controller.saveSourceAndContinue()}
        disabled={controller.loading}
        class="gap-1.5"
      >
        <span>Add & Continue</span>
        <ArrowRight class="size-4" />
      </Button>
    </div>
  </div>
</div>
