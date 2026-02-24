<script lang="ts">
  import { api } from '$lib/api';
  import { money } from '$lib/utils';

  const now = new Date();
  let monthVal = $state(now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0'));
  let incLinks: Array<Record<string, unknown>> = $state([]);
  let expLinks: Array<Record<string, unknown>> = $state([]);
  let totalIn = $state(0);
  let totalOut = $state(0);
  let loaded = $state(false);

  async function loadCashFlow() {
    if (!monthVal) return;
    const [year, month] = monthVal.split('-');
    try {
      const data = await api<Record<string, unknown>>(`/reports/cashflow-sankey?year=${year}&month=${parseInt(month)}`);
      const links = ((data.links || []) as Array<Record<string, unknown>>).filter(l => (l.value as number) > 0);
      incLinks = links.filter(l => l.target === 'income');
      expLinks = links.filter(l => l.source === 'expenses');
      totalIn = incLinks.reduce((s, l) => s + (l.value as number), 0);
      totalOut = expLinks.reduce((s, l) => s + (l.value as number), 0);
      loaded = true;
    } catch { /* handled */ }
  }
</script>

<div class="flex items-center space-x-3 mb-6">
  <input type="month" bind:value={monthVal} class="text-sm border rounded-lg px-3 py-2" />
  <button onclick={loadCashFlow} class="bg-brand-600 text-white px-4 py-2 rounded-lg hover:bg-brand-700 text-sm font-medium">Load</button>
</div>

<div class="bg-white rounded-xl shadow-sm border p-5">
  <h3 class="font-semibold text-gray-900 mb-4">Cash Flow Diagram</h3>
  {#if loaded && (incLinks.length || expLinks.length)}
    <div class="space-y-4">
      <div class="p-4 bg-green-50 rounded-xl">
        <p class="text-sm font-medium text-green-800 mb-2">Income Sources &rarr; Total: {money(totalIn)}</p>
        {#each incLinks as l}
          {@const pctVal = totalIn > 0 ? ((l.value as number) / totalIn) * 100 : 0}
          <div class="mb-2">
            <div class="flex justify-between text-sm mb-1">
              <span>{(l.source as string).replace('inc_', '')}</span>
              <span class="font-medium">{money(l.value as number)}</span>
            </div>
            <div class="w-full bg-green-100 rounded-full h-2">
              <div class="bg-green-500 h-2 rounded-full" style="width:{pctVal}%"></div>
            </div>
          </div>
        {/each}
      </div>

      <div class="text-center py-2 text-gray-300 text-2xl">&darr;</div>

      <div class="p-4 bg-red-50 rounded-xl">
        <p class="text-sm font-medium text-red-800 mb-2">Expenses &rarr; Total: {money(totalOut)}</p>
        {#each expLinks as l}
          {@const pctVal = totalOut > 0 ? ((l.value as number) / totalOut) * 100 : 0}
          <div class="mb-2">
            <div class="flex justify-between text-sm mb-1">
              <span>{(l.target as string).replace('exp_', '')}</span>
              <span class="font-medium">{money(l.value as number)}</span>
            </div>
            <div class="w-full bg-red-100 rounded-full h-2">
              <div class="bg-red-500 h-2 rounded-full" style="width:{pctVal}%"></div>
            </div>
          </div>
        {/each}
      </div>

      {#if true}
        {@const net = totalIn - totalOut}
        <div class="p-4 bg-gray-50 rounded-xl flex justify-between items-center">
          <span class="font-medium">Net Cash Flow</span>
          <span class="text-lg font-bold {net >= 0 ? 'text-green-600' : 'text-red-600'}">{net >= 0 ? '+' : ''}{money(net)}</span>
        </div>
      {/if}
    </div>
  {:else if loaded}
    <p class="text-gray-400 text-center py-16">No cash flow data for this month.</p>
  {:else}
    <p class="text-gray-400 text-center py-16">Select a month and click Load to view cash flow.</p>
  {/if}
</div>
