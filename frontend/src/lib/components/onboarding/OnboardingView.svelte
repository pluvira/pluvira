<script lang="ts">
  import { OnboardingController } from './OnboardingController.svelte';
  import { StepOverview, StepSecurity, StepPrimarySource, StepEpgSource, StepCloudLink } from './steps';
  import ToastContainer from '../ui/ToastContainer.svelte';

  interface Props {
    oncomplete?: () => void;
    class?: string;
  }

  let { oncomplete, class: className }: Props = $props();

  const controller = new OnboardingController();

  const stepLabels = ['Overview & Privacy', 'Security', 'Media Source', 'EPG Guide', 'Cloud Pairing'];

  function handleComplete() {
    if (oncomplete) {
      oncomplete();
    }
  }
</script>

<div
  class="flex min-h-screen w-full flex-col items-center justify-center bg-background p-4 text-foreground sm:p-6 {className || ''}"
>
  <!-- Brand Header -->
  <div class="mb-4 flex flex-col items-center text-center">
    <div class="flex items-center gap-2.5">
      <img src="favicon.svg" alt="Pluvira Icon" class="max-h-6 w-auto object-contain"/>
      <h1 class="text-2xl font-black tracking-wider text-foreground uppercase">
        Pluvira
      </h1>
    </div>
  </div>

  <!-- Main Gateway Card -->
  <div class="surface-card w-full max-w-2xl rounded-xl border border-border/50 p-5 shadow-xl backdrop-blur-md sm:p-6">
    <!-- Visual Stepper Progress Bar -->
    <div class="mb-4 flex items-center justify-between border-b border-border/40 pb-3 text-xs font-semibold">
      {#each stepLabels as label, idx}
        {@const stepNum = idx + 1}
        {@const isActive = controller.currentStep === stepNum}
        {@const isPassed = controller.currentStep > stepNum}
        <div
          class="flex items-center gap-2 transition-colors {isActive
            ? 'font-bold text-primary'
            : isPassed
              ? 'text-foreground'
              : 'text-muted-foreground/60'}"
        >
          <span
            class="flex size-5 items-center justify-center rounded-full text-[10px] {isActive
              ? 'bg-primary font-bold text-primary-foreground'
              : isPassed
                ? 'bg-foreground/20 font-medium text-foreground'
                : 'bg-muted text-muted-foreground'}"
          >
            {stepNum}
          </span>
          <span class="hidden sm:inline">{label}</span>
        </div>
      {/each}
    </div>

    <!-- Active Step Content -->
    {#if controller.currentStep === 1}
      <StepOverview onnext={() => controller.nextStep()} />
    {:else if controller.currentStep === 2}
      <StepSecurity {controller} />
    {:else if controller.currentStep === 3}
      <StepPrimarySource {controller} />
    {:else if controller.currentStep === 4}
      <StepEpgSource {controller} />
    {:else if controller.currentStep === 5}
      <StepCloudLink {controller} onsuccess={handleComplete} />
    {/if}
  </div>

  <!-- Footer Disclaimer -->
  <div class="mt-4 text-center text-xs text-muted-foreground/40">
    Pluvira &copy; 2026 • Local-First Streaming Aggregator
  </div>

  <ToastContainer />
</div>
