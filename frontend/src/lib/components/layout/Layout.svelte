<script lang="ts">
  import type { Snippet } from 'svelte';
  import Navbar from './Navbar.svelte';
  import Sidebar from './Sidebar.svelte';
  import SystemBanner from './SystemBanner.svelte';
  import ToastContainer from '../ui/ToastContainer.svelte';
  import { TerminalModal } from '../settings/modals';
  import type { EditionType, LicenseDetails } from '$lib/api/types';

  interface Props {
    currentPath?: string;
    isRunning?: boolean;
    authEnabled?: boolean;
    isPro?: boolean;
    edition?: EditionType;
    licenseDetails?: LicenseDetails | null;
    onTriggerUpdate?: (mode: string) => void;
    onlogout?: () => void;
    children?: Snippet;
  }

  let {
    currentPath = '#/',
    isRunning = false,
    authEnabled = true,
    isPro = false,
    edition = 'core',
    licenseDetails = null,
    onTriggerUpdate,
    onlogout,
    children
  }: Props = $props();

  let sidebarOpen = $state(false);
  let showTerminalModal = $state(false);

  function toggleSidebar() {
    sidebarOpen = !sidebarOpen;
  }

  function handleTriggerUpdate(mode: string) {
    showTerminalModal = true;
    if (onTriggerUpdate) {
      onTriggerUpdate(mode);
    }
  }

  function openTerminal() {
    showTerminalModal = true;
  }
</script>

<div class="h-screen max-h-screen flex flex-col bg-background text-foreground font-sans antialiased overflow-hidden">
  <Navbar {isPro} {toggleSidebar} {isRunning} onOpenTerminal={openTerminal} />
  <SystemBanner />

  <div class="flex flex-1 overflow-hidden min-h-0 relative">
    <Sidebar {currentPath} bind:isOpen={sidebarOpen} {authEnabled} {isRunning} {isPro} {edition} {licenseDetails} {onlogout} onTriggerUpdate={handleTriggerUpdate} onOpenTerminal={openTerminal} />

    <main class="flex-1 overflow-y-auto p-2 sm:p-4 md:p-6 w-full min-w-0">
      {#if children}
        {@render children()}
      {/if}
    </main>
  </div>

  <ToastContainer />
  <TerminalModal bind:open={showTerminalModal} onclose={() => { showTerminalModal = false; }} />
</div>
