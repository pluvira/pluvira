<script lang="ts">
  import Badge from '../../ui/Badge.svelte';
  import Button from '../../ui/Button.svelte';
  import Input from '../../ui/Input.svelte';
  import Select from '../../ui/Select.svelte';
  import { EPG_PRESETS, type OnboardingController } from '../OnboardingController.svelte';
  import { Info, ArrowRight, ArrowLeft } from '@lucide/svelte';

  interface Props {
    controller: OnboardingController;
    class?: string;
  }

  let { controller, class: className }: Props = $props();

  const presetOptions = EPG_PRESETS.map((p) => ({
    label: p.label,
    value: p.key
  }));

  function handlePresetChange(e: Event) {
    const target = e.target as HTMLSelectElement;
    if (target) {
      controller.selectEpgPreset(target.value);
    }
  }
</script>

<div class="flex flex-col gap-3.5 {className || ''}">
  <div class="flex items-center gap-2">
    <Badge variant="primary">EPG Guide</Badge>
    <h3 class="text-base font-bold text-foreground">Configure EPG Guide Source</h3>
  </div>

  <div class="flex flex-col gap-2.5">
    <Select
      id="onboarding-epg-preset-select"
      label="epgshare01 Presets"
      options={presetOptions}
      value={controller.selectedEpgPresetKey}
      onchange={handlePresetChange}
      disabled={controller.loading}
    />

    <Input
      id="onboarding-epg-source-name"
      label="EPG Source Name"
      placeholder="e.g. EPG IT (epgshare01)"
      bind:value={controller.epgSourceName}
      disabled={controller.loading}
    />

    <Input
      id="onboarding-epg-guide-url"
      label="XMLTV Guide URL (.xml / .xml.gz)"
      placeholder="https://epgshare01.online/epgshare01/epg_ripper_IT1.xml.gz"
      bind:value={controller.epgGuideUrl}
      disabled={controller.loading}
    />

    <div class="surface-card flex items-start gap-2 rounded-lg border border-border/40 p-2.5 text-xs text-muted-foreground">
      <Info class="mt-0.5 size-3.5 shrink-0 text-primary" />
      <span>Curated XMLTV feeds provided by epgshare01. Remote URL only, raw guide pasting is not supported.</span>
    </div>
  </div>

  <div class="mt-1 flex items-center justify-between">
    <Button variant="outline" onclick={() => controller.prevStep()} disabled={controller.loading} class="gap-1.5">
      <ArrowLeft class="size-4" />
      <span>Back</span>
    </Button>

    <div class="flex items-center gap-2">
      <Button variant="ghost" onclick={() => controller.skipEpgStep()} disabled={controller.loading}>
        Skip for Now
      </Button>

      <Button
        variant="primary"
        onclick={() => controller.saveEpgAndContinue()}
        disabled={controller.loading}
        class="gap-1.5"
      >
        <span>Add & Continue</span>
        <ArrowRight class="size-4" />
      </Button>
    </div>
  </div>
</div>
