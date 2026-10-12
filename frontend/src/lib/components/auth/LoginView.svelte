<script lang="ts">
  import { LoginController } from './LoginController.svelte';
  import Card from '../ui/Card.svelte';
  import Input from '../ui/Input.svelte';
  import Button from '../ui/Button.svelte';

  interface Props {
    onsuccess?: () => void;
    class?: string;
  }

  let { onsuccess, class: className = '' }: Props = $props();

  const controller = new LoginController();

  async function handleSubmit(e: Event) {
    e.preventDefault();
    const ok = await controller.handleLogin();
    if (ok && onsuccess) {
      onsuccess();
    }
  }
</script>

<div class="fixed inset-0 z-50 flex items-center justify-center bg-background p-4 select-none {className}">
  <form onsubmit={handleSubmit} class="w-full max-w-sm">
    <Card class="flex flex-col gap-6 p-6 !shadow-elevated">
      <div class="flex flex-col items-center gap-1.5 border-b border-border/30 pb-4">
        <span class="text-primary text-3xl font-extrabold tracking-wider uppercase">Pluvira</span>
        <span class="text-xs text-muted-foreground">Sign in to manage your playlists and EPG guides</span>
      </div>

      {#if controller.errorMessage}
        <div class="banner-error">
          {controller.errorMessage}
        </div>
      {/if}

      <div class="flex flex-col gap-4">
        <Input
          label="Username"
          bind:value={controller.username}
          placeholder="Enter admin username"
          disabled={controller.loading}
          id="login-username-input"
        />

        <Input
          type="password"
          label="Password"
          bind:value={controller.password}
          placeholder="Enter password"
          disabled={controller.loading}
          id="login-password-input"
        />
      </div>

      <Button
        type="submit"
        variant="primary"
        disabled={controller.loading}
        class="w-full font-bold h-[40px] uppercase text-xs tracking-wider"
      >
        {controller.loading ? 'Signing in...' : 'Sign In'}
      </Button>
    </Card>
  </form>
</div>
