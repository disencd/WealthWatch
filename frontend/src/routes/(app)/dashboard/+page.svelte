<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { money, pct, fmtDate, monthNames, typeLabel } from '$lib/utils';
  import Chart from 'chart.js/auto';

  let netWorth: Record<string, unknown> = $state({});
  let savings: Record<string, unknown> = $state({});
  let trends: Array<Record<string, unknown>> = $state([]);
  let upcoming: Array<Record<string, unknown>> = $state([]);
  let recentTx: Array<Record<string, unknown>> = $state([]);

  let spendingCanvas: HTMLCanvasElement;
  let allocationCanvas: HTMLCanvasElement;
  let charts: Chart[] = [];

  onMount(async () => {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth() + 1;

    const [nw, sav, tr, up, txs] = await Promise.all([
      api<Record<string, unknown>>('/networth/summary').catch(() => ({})),
      api<Record<string, unknown>>(`/reports/savings-rate?year=${year}&month=${month}`).catch(() => ({})),
      api<Array<Record<string, unknown>>>('/reports/spending-trends?months=6').catch(() => []),
      api<Array<Record<string, unknown>>>('/recurring/upcoming').catch(() => []),
      api<Array<Record<string, unknown>>>('/budget/expenses').catch(() => []),
    ]);

    netWorth = nw || {};
    savings = sav || {};
    trends = Array.isArray(tr) ? tr : [];
    upcoming = Array.isArray(up) ? up : [];
    recentTx = Array.isArray(txs) ? txs.slice(0, 5) : [];

    renderSpendingChart();
    renderAllocationChart();

    return () => charts.forEach(c => c.destroy());
  });

  function renderSpendingChart() {
    if (!spendingCanvas || !trends.length) return;
    const c = new Chart(spendingCanvas, {
      type: 'bar',
      data: {
        labels: trends.map(d => monthNames[((d.month as number) || 1) - 1] + ' ' + (d.year || '')),
        datasets: [{ label: 'Spending', data: trends.map(d => d.total_spent as number), backgroundColor: 'rgba(99,102,241,0.7)', borderRadius: 6 }]
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { callback: v => '$' + v } } } }
    });
    charts.push(c);
  }

  function renderAllocationChart() {
    if (!allocationCanvas) return;
    const byType = (netWorth.assets_by_type || {}) as Record<string, number>;
    const labels = Object.keys(byType).map(k => typeLabel(k));
    const values = Object.values(byType);
    const colors = ['#6366f1','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#f97316','#ec4899'];
    if (!labels.length) { labels.push('No data'); values.push(1); }
    const c = new Chart(allocationCanvas, {
      type: 'doughnut',
      data: { labels, datasets: [{ data: values, backgroundColor: colors.slice(0, labels.length) }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right', labels: { boxWidth: 12, padding: 8, font: { size: 11 } } } } }
    });
    charts.push(c);
  }
</script>

<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5 mb-8">
  <div class="stat-card bg-white rounded-xl shadow-sm border p-5">
    <div class="flex items-center justify-between">
      <div>
        <p class="text-sm text-gray-500">Net Worth</p>
        <p class="text-2xl font-bold mt-1">{money(netWorth.net_worth as number)}</p>
      </div>
      <div class="w-10 h-10 bg-brand-100 rounded-lg flex items-center justify-center text-brand-600">
        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><circle cx="10" cy="10" r="8"/></svg>
      </div>
    </div>
  </div>
  <div class="stat-card bg-white rounded-xl shadow-sm border p-5">
    <div class="flex items-center justify-between">
      <div>
        <p class="text-sm text-gray-500">Total Assets</p>
        <p class="text-2xl font-bold mt-1 text-green-600">{money(netWorth.total_assets as number)}</p>
      </div>
      <div class="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center text-green-600">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/></svg>
      </div>
    </div>
  </div>
  <div class="stat-card bg-white rounded-xl shadow-sm border p-5">
    <div class="flex items-center justify-between">
      <div>
        <p class="text-sm text-gray-500">Total Liabilities</p>
        <p class="text-2xl font-bold mt-1 text-red-600">{money(netWorth.total_liabilities as number)}</p>
      </div>
      <div class="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center text-red-600">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 17h8m0 0v-8m0 8l-8-8-4 4-6-6"/></svg>
      </div>
    </div>
  </div>
  <div class="stat-card bg-white rounded-xl shadow-sm border p-5">
    <div class="flex items-center justify-between">
      <div>
        <p class="text-sm text-gray-500">Savings Rate</p>
        <p class="text-2xl font-bold mt-1 text-brand-600">{pct(savings.savings_rate as number)}</p>
      </div>
      <div class="w-10 h-10 bg-brand-100 rounded-lg flex items-center justify-center text-brand-600">
        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path d="M10 2a4 4 0 00-4 4v1H5a2 2 0 00-2 2v8a2 2 0 002 2h10a2 2 0 002-2V9a2 2 0 00-2-2h-1V6a4 4 0 00-4-4z"/></svg>
      </div>
    </div>
  </div>
</div>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
  <div class="bg-white rounded-xl shadow-sm border p-5">
    <h3 class="font-semibold text-gray-900 mb-4">Spending Trends</h3>
    <div class="chart-container"><canvas bind:this={spendingCanvas}></canvas></div>
  </div>
  <div class="bg-white rounded-xl shadow-sm border p-5">
    <h3 class="font-semibold text-gray-900 mb-4">Asset Allocation</h3>
    <div class="chart-container"><canvas bind:this={allocationCanvas}></canvas></div>
  </div>
</div>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
  <div class="bg-white rounded-xl shadow-sm border p-5">
    <h3 class="font-semibold text-gray-900 mb-4">Upcoming Bills</h3>
    <div class="space-y-3">
      {#if upcoming.length}
        {#each upcoming.slice(0, 5) as r}
          <div class="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
            <div>
              <p class="font-medium text-sm">{r.merchant}</p>
              <p class="text-xs text-gray-500">{fmtDate(r.next_due_date as string)}</p>
            </div>
            <span class="font-semibold text-sm">{money(r.amount as number)}</span>
          </div>
        {/each}
      {:else}
        <p class="text-gray-400 text-sm text-center py-4">No upcoming bills</p>
      {/if}
    </div>
  </div>
  <div class="bg-white rounded-xl shadow-sm border p-5">
    <h3 class="font-semibold text-gray-900 mb-4">Recent Transactions</h3>
    <div class="space-y-3">
      {#if recentTx.length}
        {#each recentTx as t}
          <div class="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
            <div>
              <p class="font-medium text-sm">{t.title}</p>
              <p class="text-xs text-gray-500">{fmtDate(t.date as string)}{t.merchant ? ' - ' + t.merchant : ''}</p>
            </div>
            <span class="font-semibold text-sm text-red-600">-{money(t.amount as number)}</span>
          </div>
        {/each}
      {:else}
        <p class="text-gray-400 text-sm text-center py-4">No recent transactions</p>
      {/if}
    </div>
  </div>
</div>
