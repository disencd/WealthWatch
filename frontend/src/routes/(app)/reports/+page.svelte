<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { money, monthNames } from '$lib/utils';
  import Chart from 'chart.js/auto';

  let merchants: Array<Record<string, unknown>> = $state([]);
  let chartCanvas: HTMLCanvasElement;
  let chart: Chart | null = null;

  onMount(async () => {
    const [trends, m] = await Promise.all([
      api<Array<Record<string, unknown>>>('/reports/spending-trends?months=12').catch(() => []),
      api<Array<Record<string, unknown>>>('/reports/spending-by-merchant?limit=10').catch(() => []),
    ]);
    merchants = Array.isArray(m) ? m : [];
    const data = Array.isArray(trends) ? trends : [];

    if (chartCanvas && data.length) {
      chart = new Chart(chartCanvas, {
        type: 'bar',
        data: {
          labels: data.map(d => monthNames[((d.month as number) || 1) - 1] + ' ' + (d.year || '')),
          datasets: [{ label: 'Spending', data: data.map(d => d.total_spent as number), backgroundColor: 'rgba(99,102,241,0.7)', borderRadius: 6 }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { callback: v => '$' + v } } } }
      });
    }

    return () => chart?.destroy();
  });
</script>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
  <div class="bg-white rounded-xl shadow-sm border p-5">
    <h3 class="font-semibold text-gray-900 mb-4">Monthly Spending</h3>
    <div style="height:300px"><canvas bind:this={chartCanvas}></canvas></div>
  </div>
  <div class="bg-white rounded-xl shadow-sm border p-5">
    <h3 class="font-semibold text-gray-900 mb-4">Top Merchants</h3>
    <div class="space-y-3">
      {#each merchants as m, i}
        <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
          <div class="flex items-center space-x-3">
            <span class="text-xs font-bold text-gray-400 w-5">#{i + 1}</span>
            <div>
              <p class="font-medium text-sm">{m.merchant}</p>
              <p class="text-xs text-gray-400">{m.count} transactions</p>
            </div>
          </div>
          <span class="font-semibold text-sm">{money(m.total_spent as number)}</span>
        </div>
      {:else}
        <p class="text-gray-400 text-center py-8">No merchant data available.</p>
      {/each}
    </div>
  </div>
</div>
