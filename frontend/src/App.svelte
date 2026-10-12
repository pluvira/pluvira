<script lang="ts">
  import { onMount } from 'svelte';
  import { AppController } from '$lib/components/layout/AppController.svelte';
  import Layout from '$lib/components/layout/Layout.svelte';
  import LoginView from '$lib/components/auth/LoginView.svelte';
  import LiveView from '$lib/components/live/LiveView.svelte';
  import ChannelsView from '$lib/components/channels/ChannelsView.svelte';
  import SettingsView from '$lib/components/settings/SettingsView.svelte';
  import AboutView from '$lib/components/about/AboutView.svelte';
  import SearchView from '$lib/components/search/SearchView.svelte';
  import { OnboardingView } from '$lib/components/onboarding';

  const controller = new AppController();

  let currentPath = $derived(controller.currentPath);
  let isRunning = $derived(controller.isRunning);

  let isBootstrapped = $derived(controller.isBootstrapped);
  let authEnabled = $derived(controller.authEnabled);
  let isPro = $derived(controller.isPro);
  let edition = $derived(controller.edition);
  let licenseDetails = $derived(controller.licenseDetails);
  let onboardingCompleted = $derived(controller.onboardingCompleted);

  function handleHashChange() {
    controller.handleHashChange();
  }

  function handleTriggerUpdate(mode: string) {
    controller.handleTriggerUpdate(mode);
  }

  function handleLogout() {
    controller.handleLogout();
  }

  function handleOnboardingComplete() {
    controller.handleOnboardingComplete();
  }

  let isAuthorized = $derived(controller.isAuthorized);

  onMount(() => {
    controller.init();
  });
</script>

<svelte:window onhashchange={handleHashChange} />

{#if !isBootstrapped}
  <div class="fixed inset-0 z-50 flex flex-col items-center justify-center bg-background text-foreground">
    <span class="spinner mb-3"></span>
    <span class="text-xs font-bold tracking-wider uppercase">Loading Pluvira...</span>
  </div>
{:else if !isAuthorized}
  <LoginView onsuccess={() => { window.location.hash = '#/'; window.location.reload(); }} />
{:else if !onboardingCompleted}
  <OnboardingView oncomplete={handleOnboardingComplete} />
{:else}
  <Layout
    {currentPath}
    {isRunning}
    {isPro}
    {edition}
    {licenseDetails}
    {authEnabled}
    onTriggerUpdate={handleTriggerUpdate}
    onlogout={handleLogout}
  >
    {#if currentPath.startsWith('#/live')}
      <LiveView />
    {:else if currentPath.startsWith('#/search')}
      <SearchView />
    {:else if currentPath.startsWith('#/channels')}
      <ChannelsView />
    {:else if currentPath.startsWith('#/settings')}
      <SettingsView />
    {:else if currentPath.startsWith('#/about')}
      <AboutView />
    {:else}
      <LiveView />
    {/if}
  </Layout>

{/if}
