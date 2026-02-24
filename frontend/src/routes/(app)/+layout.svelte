<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { isAuthenticated, token, currentUser } from '$lib/stores/auth';
  import { loadCategories } from '$lib/stores/categories';
  import { api } from '$lib/api';
  import Sidebar from '$lib/components/Sidebar.svelte';
  import Topbar from '$lib/components/Topbar.svelte';

  let { children } = $props();
  let ready = $state(false);

  onMount(async () => {
    if (!isAuthenticated()) {
      goto('/login', { replaceState: true });
      return;
    }
    try {
      const user = await api<Record<string, unknown>>('/auth/profile');
      currentUser.set(user);
      await loadCategories();
      ready = true;
    } catch {
      goto('/login', { replaceState: true });
    }
  });
</script>

{#if ready}
<div class="flex min-h-screen bg-gray-50 text-gray-800">
  <Sidebar />
  <div class="flex-1 ml-64">
    <Topbar />
    <main class="p-6">
      {@render children()}
    </main>
  </div>
</div>
{:else}
<div class="min-h-screen flex items-center justify-center bg-gray-50">
  <div class="animate-pulse text-gray-400">Loading...</div>
</div>
{/if}
