<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { money, fmtDate, typeLabel } from '$lib/utils';
  import { notify } from '$lib/components/notify';
  import Chart from 'chart.js/auto';

  let summary: Record<string, unknown> = $state({});
  let history: Array<Record<string, unknown>> = $state([]);
  let chartCanvas: HTMLCanvasElement;
  let chart: Chart | null = null;

  onMount(async () => {
    await loadData();
    return () => chart?.destroy();
  });

  async function loadData() {
    const [s, h] = await Promise.all([
      api<Record<string, unknown>>('/networth/summary'),
      api<Array<Record<string, unknown>>>('/networth/history'),
    ]);
    summary = s || {};
    history = Array.isArray(h) ? h : [];
    renderChart();
  }

  function renderChart() {
    if (!chartCanvas) return;
    chart?.destroy();
    chart = new Chart(chartCanvas, {
      type: 'line',
      data: {
        labels: history.map(h => fmtDate(h.date as string)),
        datasets: [
          { label: 'Net Worth', data: history.map(h => h.net_worth as number), borderColor: '#6366f1', backgroundColor: 'rgba(99,102,241,0.1)', fill: true, tension: 0.3 },
          { label: 'Assets', data: history.map(h => h.total_assets as number), borderColor: '#10b981', borderDash: [5,5], tension: 0.3 },
          { label: 'Liabilities', data: history.map(h => h.total_liabilities as number), borderColor: '#ef4444', borderDash: [5,5], tension: 0.3 }
        ]
      },
      options: { responsive: true, maintainAspectRatio: false, scales: { y: { ticks: { callback: v => '$' + v } } } }
    });
  }

  async function takeSnapshot() {
    try {
      await api('/networth/snapshot', { method: 'POST' });
      notify('Snapshot saved', 'success');
      await loadData();
    } catch { /* handled */ }
  }
</script>

<div class="grid grid-cols-1 md:grid-cols-3 gap-5 mb-6">
  <div class="bg-white rounded-xl shadow-sm border p-5">
    <p class="text-sm text-gray-500">Net Worth</p>
    <p class="text-3xl font-bold mt-1">{money(summary.net_worth as number)}</p>
  </div>
  <div class="bg-white rounded-xl shadow-sm border p-5">
    <p class="text-sm text-gray-500">Assets</p>
    <p class="text-3xl font-bold mt-1 text-green-600">{money(summary.total_assets as number)}</p>
  </div>
  <div class="bg-white rounded-xl shadow-sm border p-5">
    <p class="text-sm text-gray-500">Liabilities</p>
    <p class="text-3xl font-bold mt-1 text-red-600">{money(summary.total_liabilities as number)}</p>
  </div>
</div>

<div class="bg-white rounded-xl shadow-sm border p-5 mb-6">
  <div class="flex items-center justify-between mb-4">
    <h3 class="font-semibold text-gray-900">Net Worth Over Time</h3>
    <button onclick={takeSnapshot} class="text-sm bg-brand-600 text-white px-3 py-1.5 rounded-lg hover:bg-brand-700">Take Snapshot</button>
  </div>
  <div style="height:300px"><canvas bind:this={chartCanvas}></canvas></div>
</div>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
  <div class="bg-white rounded-xl shadow-sm border p-5">
    <h3 class="font-semibold text-gray-900 mb-4">Assets Breakdown</h3>
    <div class="space-y-2">
      {#each Object.entries((summary.assets_by_type || {}) as Record<string, number>) as [type, amount]}
        <div class="flex justify-between p-2 bg-green-50 rounded">
          <span class="text-sm">{typeLabel(type)}</span>
          <span class="font-medium text-sm">{money(amount)}</span>
        </div>
      {:else}
        <p class="text-gray-400 text-sm text-center py-2">No assets yet</p>
      {/each}
    </div>
  </div>
  <div class="bg-white rounded-xl shadow-sm border p-5">
    <h3 class="font-semibold text-gray-900 mb-4">Liabilities Breakdown</h3>
    <div class="space-y-2">
      {#each Object.entries((summary.liabilities_by_type || {}) as Record<string, number>) as [type, amount]}
        <div class="flex justify-between p-2 bg-red-50 rounded">
          <span class="text-sm">{typeLabel(type)}</span>
          <span class="font-medium text-sm">{money(amount)}</span>
        </div>
      {:else}
        <p class="text-gray-400 text-sm text-center py-2">No liabilities yet</p>
      {/each}
    </div>
  </div>
</div>
