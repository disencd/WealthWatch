<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { isAuthenticated } from '$lib/stores/auth';

  onMount(() => {
    if (isAuthenticated()) goto('/dashboard', { replaceState: true });
    else goto('/login', { replaceState: true });
  });
</script>
