<script lang="ts">
  import Badge from './Badge.svelte';
  import { getTierBadgeClass, getTierBadgeIcon } from '$lib/utils/tierBadge';
  import { Sparkles, ShieldCheck } from '@lucide/svelte';

  interface Props {
    status?: string | null;
    errorCode?: string | null;
    daysRemaining?: number | null;
    isTrial?: boolean;
    isPro?: boolean;
    tier?: string | null;
    displayName?: string | null;
    compactName?: string | null;
    compact?: boolean;
    badgeIcon?: string | null;
    badgeColor?: string | null;
    badgeTextColor?: string | null;
    class?: string;
  }

  let {
    status = null,
    errorCode = null,
    daysRemaining = null,
    isTrial = false,
    isPro = false,
    tier = null,
    displayName = null,
    compactName = null,
    compact = false,
    badgeIcon = null,
    badgeColor = null,
    badgeTextColor = null,
    class: className = ''
  }: Props = $props();

  let isGracePeriod = $derived(status === 'grace_period');
  let isExpiringSoon = $derived(status === 'expiring_soon');
  let isExpired = $derived(status === 'expired' || errorCode === 'LICENSE_EXPIRED');
  let isValid = $derived(status === 'valid' || (isPro && !isExpired && !isGracePeriod) || (tier === 'free' && !isExpired));
  let effectiveTierLabel = $derived.by(() => {
    if (compact) {
      if (compactName && compactName.trim()) return compactName.trim();
      if (tier && tier.trim() && tier.toLowerCase() !== 'core') return tier.trim().toUpperCase();
      return 'CORE';
    }
    if (displayName && displayName.trim()) return displayName.trim();
    if (tier === 'free') return 'Free Registered';
    if (tier && tier.trim() && tier.toLowerCase() !== 'core') return tier.trim().toUpperCase();
    return 'VALID';
  });

  let isHexColor = $derived(Boolean(badgeColor && badgeColor.trim().startsWith('#')));
  let dynamicBadgeClass = $derived(isHexColor ? '' : getTierBadgeClass(badgeColor));

  let IconComponent = $derived(getTierBadgeIcon(badgeIcon, tier));
</script>

{#if isTrial}
  <Badge variant="warning" class="inline-flex items-center gap-1.5 {className}">
    <Sparkles class="w-3.5 h-3.5 shrink-0" />
    <span>TRIAL {daysRemaining !== null && daysRemaining !== undefined ? `(${daysRemaining}d)` : ''}</span>
  </Badge>
{:else if isGracePeriod}
  <Badge
    variant="warning"
    class="inline-flex items-center gap-1.5 {className}"
    title="Pluvira is currently disconnected from the internet. Pro features remain active locally for up to 48 hours. Reconnect to restore remote WebRTC access and telemetry sync."
  >
    <ShieldCheck class="w-3.5 h-3.5 shrink-0" />
    <span>OFFLINE LEEWAY</span>
  </Badge>
{:else if isExpiringSoon}
  <Badge variant="warning" class="inline-flex items-center gap-1.5 {className}">
    <Sparkles class="w-3.5 h-3.5 shrink-0" />
    <span>EXPIRING {daysRemaining !== null && daysRemaining !== undefined ? `(${daysRemaining}d)` : ''}</span>
  </Badge>
{:else if isValid}
  {#if isHexColor}
    <span
      class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-bold border {className}"
      style="background-color: {badgeColor}20; color: {badgeTextColor || badgeColor}; border-color: {badgeColor}60;"
    >
      <IconComponent class="w-3.5 h-3.5 shrink-0" />
      <span>{effectiveTierLabel}</span>
    </span>
  {:else if badgeColor}
    <span
      class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-bold border {dynamicBadgeClass} {className}"
    >
      <IconComponent class="w-3.5 h-3.5 shrink-0" />
      <span>{effectiveTierLabel}</span>
    </span>
  {:else if tier === 'free'}
    <span
      class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-bold border border-sky-500/40 bg-sky-500/15 text-sky-400 {className}"
    >
      <IconComponent class="w-3.5 h-3.5 shrink-0" />
      <span>{effectiveTierLabel}</span>
    </span>
  {:else}
    <Badge variant="success" class="inline-flex items-center gap-1.5 {className}">
      <IconComponent class="w-3.5 h-3.5 shrink-0" />
      <span>{effectiveTierLabel}</span>
    </Badge>
  {/if}
{:else if isExpired}
  <Badge variant="error" class={className}>EXPIRED</Badge>
{:else if errorCode}
  <Badge variant="error" class={className}>{errorCode}</Badge>
{:else}
  <Badge variant="muted" class={className}>UNLICENSED</Badge>
{/if}
