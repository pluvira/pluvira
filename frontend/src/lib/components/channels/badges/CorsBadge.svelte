<script lang="ts">
  import Badge from '../../ui/Badge.svelte';

  interface Props {
    corsSupported?: boolean;
    needsProxy?: boolean;
    class?: string;
  }

  let {
    corsSupported = false,
    needsProxy = false,
    class: className = ''
  }: Props = $props();

  let variant = $derived<'success' | 'warning' | 'muted'>(
    corsSupported ? 'success' : needsProxy ? 'warning' : 'muted'
  );
  let labelText = $derived(
    corsSupported ? 'CORS' : needsProxy ? 'PROXY' : '-'
  );
  let tooltipText = $derived(
    corsSupported
      ? 'CORS Supported Natively'
      : needsProxy
        ? 'Requires Server Proxy for Web Playback'
        : 'CORS Status Unchecked'
  );
</script>

<div title={tooltipText} class="inline-flex shrink-0 {className}">
  <Badge {variant}>
    {labelText}
  </Badge>
</div>
