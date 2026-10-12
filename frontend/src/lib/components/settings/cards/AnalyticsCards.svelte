<script lang="ts">
  import Card from '../../ui/Card.svelte';
  import Badge from '../../ui/Badge.svelte';
  import Button from '../../ui/Button.svelte';
  import { formatGlobalStats } from '../utils/DashboardUtils';
  import { AlertTriangle, Clock, ShieldAlert } from '@lucide/svelte';
  import { toastStore } from '$lib/stores/toastStore';
  import { licenseStore } from '$lib/stores/licenseStore';
  import { isChannelsQuotaExceeded, BSL_MAX_CHANNELS } from '$lib/utils/bslUtils';
  import type { LicenseDetails } from '$lib/api/types';

  interface Props {
    rawStats?: Record<string, unknown>;
    licenseDetails?: LicenseDetails | null;
    class?: string;
  }

  let { rawStats = {}, licenseDetails = null, class: className = '' }: Props = $props();

  let stats = $derived(formatGlobalStats(rawStats));
  let isExpiringSoon = $derived(licenseDetails?.license_status === 'expiring_soon');
  let isExpired = $derived(licenseDetails?.license_status === 'expired' || licenseDetails?.error_code === 'LICENSE_EXPIRED');
  let hasActiveChannels = $derived(stats.totalChannels > 0);
  let isPro = $derived($licenseStore.isPro || licenseDetails?.license_status === 'valid');
  let isBslChannelLimitReached = $derived(isChannelsQuotaExceeded(stats.totalChannels, isPro));
</script>

<div class="flex flex-col gap-4 w-full {className}">
  {#if isExpired}
    <div class="banner-error">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div class="flex items-center gap-3">
          <ShieldAlert class="text-destructive w-5 h-5 shrink-0" />
          <div class="flex flex-col">
            <span class="font-bold text-destructive-foreground text-sm">Pro License Expired</span>
            <span class="text-xs text-destructive-foreground/80">
              Your Pro license has expired. The system has automatically fallen back to the open-source Core edition.
            </span>
          </div>
        </div>
        <Button
          variant="primary"
          size="sm"
          onclick={() => toastStore.info('Pluvira Pro: Visit pluvira.com to purchase or renew a license.')}
          class="!py-1 text-xs shrink-0 font-bold"
        >
          RENEW LICENSE
        </Button>
      </div>
    </div>
  {/if}

  {#if isExpiringSoon}
    <div class="banner-warning">
      <div class="flex items-center gap-3">
        <Clock class="text-primary w-5 h-5 shrink-0" />
        <div class="flex flex-col">
          <span class="font-bold text-foreground text-sm">Pro License Expiring Soon</span>
          <span class="text-xs text-muted-foreground">
            Your Pluvira Pro license expires in {licenseDetails?.days_remaining ?? 0} days. Renew to ensure continuous Pro engine features.
          </span>
        </div>
      </div>
      <Button
        variant="outline"
        size="sm"
        onclick={() => toastStore.info('Pluvira Pro: Visit the official website to purchase or renew a license.')}
        class="!border-primary/50 !text-primary hover:!bg-primary/10 text-xs"
      >
        RENEW LICENSE
      </Button>
    </div>
  {/if}

  {#if !hasActiveChannels}
    <div class="banner-warning">
      <div class="flex items-center gap-3">
        <AlertTriangle class="text-primary w-5 h-5 shrink-0" />
        <div class="flex flex-col">
          <span class="font-bold text-foreground text-sm">No Active Sources Detected</span>
          <span class="text-xs text-muted-foreground">All IPTV sources are currently disabled or empty. Enable a source below or configure Settings.</span>
        </div>
      </div>
      <a href="#/settings">
        <Button variant="outline" size="sm" class="!border-primary/50 !text-primary hover:!bg-primary/10 text-xs">
          GO TO CONFIG
        </Button>
      </a>
    </div>
  {/if}

  {#if !isPro && isBslChannelLimitReached}
    <div class="banner-warning">
      <div class="flex items-center gap-3">
        <AlertTriangle class="text-primary w-5 h-5 shrink-0" />
        <div class="flex flex-col">
          <span class="font-bold text-foreground text-sm">BSL 1.1 Free Tier Limit Reached ({stats.totalChannels}/{BSL_MAX_CHANNELS} Channels)</span>
          <span class="text-xs text-muted-foreground">
            The Personal Free Tier is limited to {BSL_MAX_CHANNELS} channels and 2 active playlists. Upgrade to Pluvira Pro for unlimited channels and native Rust performance.
          </span>
        </div>
      </div>
      <Button
        variant="outline"
        size="sm"
        onclick={() => toastStore.info('Pluvira Pro: Activate a 14-day free trial or visit pluvira.com to subscribe.')}
        class="!border-primary/50 !text-primary hover:!bg-primary/10 text-xs shrink-0"
      >
        UPGRADE TO PRO
      </Button>
    </div>
  {/if}

  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 w-full">
    <Card class="border-l-4 !border-l-primary flex flex-col justify-between">
      <span class="text-caps-label">Total Channels</span>
      <span class="text-3xl font-extrabold text-foreground my-2">{stats.totalChannels}</span>
      <div class="flex items-center gap-2">
        <Badge variant="success">INC: {stats.totalIncluded}</Badge>
        <Badge variant="error">EXC: {stats.totalExcluded}</Badge>
      </div>
    </Card>

    <Card class="border-l-4 !border-l-primary/60 flex flex-col justify-between">
      <span class="text-caps-label">EPG Coverage (Included)</span>
      <span class="text-3xl font-extrabold text-primary my-2">{stats.epgCoveragePct.toFixed(1)}%</span>
      <span class="text-xs text-muted-foreground">Calculated on {stats.totalIncluded} included channels</span>
    </Card>

    <Card class="border-l-4 !border-l-primary flex flex-col justify-between">
      <span class="text-caps-label">Link Health (Included)</span>
      <span class="text-3xl font-extrabold text-primary my-2">{stats.linkHealthPct.toFixed(1)}%</span>
      <div class="flex items-center gap-1.5 flex-wrap">
        <Badge variant="success">OK: {stats.onlineCount}</Badge>
        <Badge variant="error">KO: {stats.offlineCount}</Badge>
        <Badge variant="muted">-: {stats.uncheckedCount}</Badge>
      </div>
    </Card>

    <Card class="border-l-4 !border-l-primary/40 flex flex-col justify-between">
      <span class="text-caps-label mb-1">Top Groups</span>
      {#if stats.topGroups.length > 0}
        <div class="flex flex-wrap gap-1 max-h-20 overflow-y-auto pr-1">
          {#each stats.topGroups as [grpName, count] (grpName)}
            <Badge variant="warning">{grpName}: {count}</Badge>
          {/each}
        </div>
      {:else}
        <span class="text-xs text-muted-foreground italic my-2">No groups available</span>
      {/if}
    </Card>
  </div>
</div>
