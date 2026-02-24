<script lang="ts">
  import { onMount } from 'svelte';

  let { message, type = 'info', onClose }: { message: string; type?: 'info' | 'success' | 'error'; onClose: () => void } = $props();

  onMount(() => {
    const timer = setTimeout(onClose, 3000);
    return () => clearTimeout(timer);
  });

  const colorClass = $derived(
    type === 'success' ? 'bg-green-500 text-white' :
    type === 'error' ? 'bg-red-500 text-white' :
    'bg-brand-500 text-white'
  );
</script>

<div class="fixed top-4 right-4 px-4 py-3 rounded-xl shadow-lg z-[100] text-sm font-medium {colorClass}">
  {message}
</div>
