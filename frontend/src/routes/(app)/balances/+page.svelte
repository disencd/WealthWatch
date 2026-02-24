<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { money } from '$lib/utils';

  let balances: Array<Record<string, unknown>> = $state([]);

  onMount(async () => {
    try {
      const data = await api<Record<string, unknown>>('/balances');
      balances = (data.balances || []) as Array<Record<string, unknown>>;
    } catch { /* handled */ }
  });
</script>

<div class="bg-white rounded-xl shadow-sm border">
  {#each balances as b}
    <div class="p-4 border-b last:border-b-0 flex justify-between items-center">
      <div><h4 class="font-medium">User {b.user_id}</h4></div>
      <div class="text-right">
        <p class="text-lg font-bold {(b.amount as number) > 0 ? 'text-green-600' : 'text-red-600'}">
          {(b.amount as number) > 0 ? '+' : ''}{money(Math.abs(b.amount as number))}
        </p>
        <p class="text-xs text-gray-500">{(b.amount as number) > 0 ? 'owes you' : 'you owe'}</p>
      </div>
    </div>
  {:else}
    <p class="text-gray-400 text-center py-8">No balances to show.</p>
  {/each}
</div>
