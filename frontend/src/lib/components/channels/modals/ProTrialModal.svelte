<script lang="ts">
  import Dialog from '../../ui/Dialog.svelte';
  import Button from '../../ui/Button.svelte';
  import { Sparkles, Check, ShieldCheck, Zap, Layers } from '@lucide/svelte';

  interface Props {
    open?: boolean;
    onactivate?: () => Promise<boolean>;
    onactivated?: () => void;
    onclose?: () => void;
    class?: string;
  }

  let {
    open = $bindable(),
    onactivate,
    onactivated,
    onclose,
    class: className = ''
  }: Props = $props();

  let loading = $state(false);

  async function handleActivateTrial() {
    loading = true;
    try {
      if (onactivate) {
        const success = await onactivate();
        if (success) {
          open = false;
          onactivated?.();
        }
      } else {
        open = false;
        onactivated?.();
      }
    } catch {
      // Error reporting handled by controller
    } finally {
      loading = false;
    }
  }
</script>

<Dialog
  bind:open
  title="Activate 14-Day Free Pluvira Pro Trial (No credit card required)"
  {onclose}
  class="max-w-xl {className}"
>
  {#snippet footer()}
    <Button variant="ghost" size="sm" onclick={() => (open = false)} class="touch-btn">
      Maybe Later
    </Button>
    <Button
      variant="primary"
      size="sm"
      disabled={loading}
      onclick={handleActivateTrial}
      class="font-bold flex items-center gap-1.5 touch-btn"
    >
      <Sparkles class="w-4 h-4" />
      <span>{loading ? 'Activating...' : 'Activate 14-Day Free Trial'}</span>
    </Button>
  {/snippet}

  <div class="flex flex-col gap-4 text-xs">
    <div class="p-3.5 bg-primary/10 border border-primary/20 rounded-lg flex items-start gap-3">
      <ShieldCheck class="w-5 h-5 text-primary shrink-0 mt-0.5" />
      <div class="flex flex-col gap-1">
        <span class="font-bold text-foreground text-sm">Personal Free Tier Limit Reached</span>
        <p class="text-muted-foreground leading-relaxed">
          "My List" is capped at 25 channels in the Free Tier. Unlock unlimited curated channels, multi-stream failover, and high-performance native features instantly.
        </p>
      </div>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
      <div class="p-3 bg-card rounded-md border border-border/40 flex items-start gap-2.5">
        <Layers class="w-4 h-4 text-primary shrink-0 mt-0.5" />
        <div class="flex flex-col gap-0.5">
          <span class="font-bold text-foreground">Unlimited Channels</span>
          <span class="text-muted-foreground text-[11px]">Curate more than 25 channels in your personal playlists without restrictions.</span>
        </div>
      </div>

      <div class="p-3 bg-card rounded-md border border-border/40 flex items-start gap-2.5">
        <Zap class="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <div class="flex flex-col gap-0.5">
          <span class="font-bold text-foreground">7 Failover Stream Slots</span>
          <span class="text-muted-foreground text-[11px]">Expand each channel up to 7 ordered failover backups (Slot 0..6).</span>
        </div>
      </div>
    </div>

    <div class="overflow-x-auto rounded-md border border-border/30 bg-background/50">
      <table class="w-full text-left text-[11px]">
        <thead>
          <tr class="border-b border-border/30 bg-card/60 text-muted-foreground">
            <th class="p-2 font-semibold">Capability</th>
            <th class="p-2 font-semibold text-center">Free Core Edition</th>
            <th class="p-2 font-semibold text-center text-primary">Pro Edition</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border/20">
          <tr>
            <td class="p-2 font-medium text-foreground">EPG Update Speed (500k programmes)</td>
            <td class="p-2 text-center text-muted-foreground">~3 minutes</td>
            <td class="p-2 text-center font-bold text-primary">~3 seconds (Turbo)</td>
          </tr>
          <tr>
            <td class="p-2 font-medium text-foreground">Peak RAM Impact on NAS / Server</td>
            <td class="p-2 text-center text-muted-foreground">Up to 1.5 GB</td>
            <td class="p-2 text-center font-bold text-primary">~25 MB constant</td>
          </tr>
          <tr>
            <td class="p-2 font-medium text-foreground">Malformed XML & Encoding Recovery</td>
            <td class="p-2 text-center text-muted-foreground">Limited</td>
            <td class="p-2 text-center font-bold text-primary">Native Sanitizer</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="flex items-center gap-2 text-muted-foreground text-[11px]">
      <Check class="w-3.5 h-3.5 text-success shrink-0" />
      <span>No credit card required. Non-destructive: channels are never deleted after trial expires.</span>
    </div>
  </div>
</Dialog>
