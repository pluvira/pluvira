<script lang="ts">
  import Badge from '../../ui/Badge.svelte';
  import Button from '../../ui/Button.svelte';
  import { HardDrive, ShieldCheck, Lock, Layers, ArrowRight } from '@lucide/svelte';

  interface Props {
    onnext?: () => void;
    class?: string;
  }

  let { onnext, class: className }: Props = $props();
</script>

<div class="flex flex-col gap-3.5 {className || ''}">
  <div class="flex items-center gap-2">
    <Badge variant="primary">Local-First • Zero-PII • BSL 1.1</Badge>
    <h3 class="text-base font-bold text-foreground">Self-Hosted Media Engine</h3>
  </div>

  <div class="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
    <div class="surface-card flex flex-col gap-2 rounded-lg border border-border/50 p-3.5">
      <div class="flex items-center gap-2 text-primary">
        <HardDrive class="size-4 shrink-0" />
        <span class="text-xs font-semibold uppercase">Local-First Storage</span>
      </div>
      <p class="text-xs leading-normal text-muted-foreground">
        Processed in RAM disk (<code class="text-foreground">/dev/shm</code>) and SQLite WAL. Zero viewing telemetry.
      </p>
    </div>

    <div class="surface-card flex flex-col gap-2 rounded-lg border border-border/50 p-3.5">
      <div class="flex items-center gap-2 text-primary">
        <ShieldCheck class="size-4 shrink-0" />
        <span class="text-xs font-semibold uppercase">Zero-PII Identity</span>
      </div>
      <p class="text-xs leading-normal text-muted-foreground">
        No emails or passwords. Identity managed via anonymous 12-char UID and Passkeys.
      </p>
    </div>

    <div class="surface-card flex flex-col gap-2 rounded-lg border border-border/50 p-3.5">
      <div class="flex items-center gap-2 text-primary">
        <Lock class="size-4 shrink-0" />
        <span class="text-xs font-semibold uppercase">E2EE Backup</span>
      </div>
      <p class="text-xs leading-normal text-muted-foreground">
        Client-side AES-256-GCM encryption. Cloud operates strictly as an opaque blind conduit.
      </p>
    </div>

    <div class="surface-card flex flex-col gap-2 rounded-lg border border-border/50 p-3.5">
      <div class="flex items-center gap-2 text-primary">
        <Layers class="size-4 shrink-0" />
        <span class="text-xs font-semibold uppercase">Personal Free Tier</span>
      </div>
      <p class="text-xs leading-normal text-muted-foreground">
        Up to 2 sources, 2,500 channels, 25 in "My List", and 2 failover slots per channel.
      </p>
    </div>
  </div>

  <div class="mt-1 flex items-center justify-end">
    <Button variant="primary" onclick={onnext} class="gap-2">
      <span>Get Started</span>
      <ArrowRight class="size-4" />
    </Button>
  </div>
</div>
