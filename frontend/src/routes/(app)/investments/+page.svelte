<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { money, pct } from '$lib/utils';
  import { notify } from '$lib/components/notify';
  import Modal from '$lib/components/Modal.svelte';
  import { Plus } from 'lucide-svelte';

  interface Holding {
    id: number; symbol: string; name: string; quantity: number;
    current_price: number; current_value: number; cost_basis: number;
    gain_loss: number; gain_loss_percent: number;
  }

  let portfolio: Record<string, unknown> = $state({});
  let holdings: Holding[] = $state([]);
  let showAdd = $state(false);
  let form = $state({ account_id: 0, symbol: '', investment_type: 'stock', name: '', quantity: 0, cost_basis: 0, current_price: 0 });

  onMount(() => { loadData(); });

  async function loadData() {
    const [p, h] = await Promise.all([
      api<Record<string, unknown>>('/investments/portfolio'),
      api<Holding[]>('/investments'),
    ]);
    portfolio = p || {};
    holdings = Array.isArray(h) ? h : [];
  }

  async function addHolding(e: Event) {
    e.preventDefault();
    try {
      await api('/investments', { method: 'POST', body: JSON.stringify({
        ...form, account_id: Number(form.account_id), quantity: Number(form.quantity),
        cost_basis: Number(form.cost_basis), current_price: Number(form.current_price)
      })});
      showAdd = false;
      notify('Holding added', 'success');
      await loadData();
    } catch { /* handled */ }
  }

  async function deleteHolding(id: number) {
    if (!confirm('Delete this holding?')) return;
    try {
      await api('/investments/' + id, { method: 'DELETE' });
      notify('Deleted', 'success');
      await loadData();
    } catch { /* handled */ }
  }

  let gl = $derived((portfolio.total_gain_loss as number) || 0);
  let glPct = $derived((portfolio.total_gain_loss_pct as number) || 0);
</script>

<div class="grid grid-cols-1 md:grid-cols-4 gap-5 mb-6">
  <div class="bg-white rounded-xl shadow-sm border p-5">
    <p class="text-sm text-gray-500">Portfolio Value</p>
    <p class="text-2xl font-bold mt-1">{money(portfolio.total_value as number)}</p>
  </div>
  <div class="bg-white rounded-xl shadow-sm border p-5">
    <p class="text-sm text-gray-500">Cost Basis</p>
    <p class="text-2xl font-bold mt-1 text-gray-600">{money(portfolio.total_cost_basis as number)}</p>
  </div>
  <div class="bg-white rounded-xl shadow-sm border p-5">
    <p class="text-sm text-gray-500">Total Gain/Loss</p>
    <p class="text-2xl font-bold mt-1 {gl >= 0 ? 'text-green-600' : 'text-red-600'}">{gl >= 0 ? '+' : ''}{money(gl)}</p>
  </div>
  <div class="bg-white rounded-xl shadow-sm border p-5">
    <p class="text-sm text-gray-500">Return</p>
    <p class="text-2xl font-bold mt-1 {glPct >= 0 ? 'text-green-600' : 'text-red-600'}">{glPct >= 0 ? '+' : ''}{pct(glPct)}</p>
  </div>
</div>

<div class="flex items-center justify-between mb-4">
  <h3 class="font-semibold">Holdings</h3>
  <button onclick={() => { form = { account_id: 0, symbol: '', investment_type: 'stock', name: '', quantity: 0, cost_basis: 0, current_price: 0 }; showAdd = true; }}
    class="bg-brand-600 text-white px-4 py-2 rounded-lg hover:bg-brand-700 text-sm font-medium flex items-center gap-2">
    <Plus size={16} /> Add Holding
  </button>
</div>

<div class="bg-white rounded-xl shadow-sm border overflow-hidden">
  <table class="min-w-full text-sm">
    <thead class="bg-gray-50 text-gray-500 uppercase text-xs">
      <tr>
        <th class="px-4 py-3 text-left">Symbol</th>
        <th class="px-4 py-3 text-left">Name</th>
        <th class="px-4 py-3 text-right">Qty</th>
        <th class="px-4 py-3 text-right">Price</th>
        <th class="px-4 py-3 text-right">Value</th>
        <th class="px-4 py-3 text-right">Gain/Loss</th>
        <th class="px-4 py-3 text-right">Actions</th>
      </tr>
    </thead>
    <tbody class="divide-y">
      {#each holdings as h (h.id)}
        <tr>
          <td class="px-4 py-3 font-semibold">{h.symbol}</td>
          <td class="px-4 py-3">{h.name}</td>
          <td class="px-4 py-3 text-right">{h.quantity}</td>
          <td class="px-4 py-3 text-right">{money(h.current_price)}</td>
          <td class="px-4 py-3 text-right font-medium">{money(h.current_value)}</td>
          <td class="px-4 py-3 text-right {h.gain_loss >= 0 ? 'text-green-600' : 'text-red-600'}">
            {h.gain_loss >= 0 ? '+' : ''}{money(h.gain_loss)} ({pct(h.gain_loss_percent)})
          </td>
          <td class="px-4 py-3 text-right">
            <button onclick={() => deleteHolding(h.id)} class="text-red-500 hover:underline text-xs">Delete</button>
          </td>
        </tr>
      {:else}
        <tr><td colspan="7" class="px-4 py-8 text-center text-gray-400">No holdings yet</td></tr>
      {/each}
    </tbody>
  </table>
</div>

<Modal title="Add Holding" open={showAdd} onClose={() => showAdd = false}>
  <form onsubmit={addHolding} class="space-y-4">
    <div><label class="block text-sm font-medium mb-1">Account ID</label><input bind:value={form.account_id} type="number" required class="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Investment account ID" /></div>
    <div class="grid grid-cols-2 gap-3">
      <div><label class="block text-sm font-medium mb-1">Symbol</label><input bind:value={form.symbol} required class="w-full border rounded-lg px-3 py-2 text-sm" placeholder="AAPL" /></div>
      <div><label class="block text-sm font-medium mb-1">Type</label>
        <select bind:value={form.investment_type} class="w-full border rounded-lg px-3 py-2 text-sm">
          <option value="stock">Stock</option><option value="etf">ETF</option><option value="mutual_fund">Mutual Fund</option>
          <option value="bond">Bond</option><option value="crypto">Crypto</option><option value="other">Other</option>
        </select>
      </div>
    </div>
    <div><label class="block text-sm font-medium mb-1">Name</label><input bind:value={form.name} required class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
    <div class="grid grid-cols-3 gap-3">
      <div><label class="block text-sm font-medium mb-1">Quantity</label><input bind:value={form.quantity} type="number" step="0.0001" required class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
      <div><label class="block text-sm font-medium mb-1">Cost Basis</label><input bind:value={form.cost_basis} type="number" step="0.01" required class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
      <div><label class="block text-sm font-medium mb-1">Current Price</label><input bind:value={form.current_price} type="number" step="0.01" required class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
    </div>
    <button type="submit" class="w-full bg-brand-600 text-white py-2.5 rounded-lg hover:bg-brand-700 font-medium">Add Holding</button>
  </form>
</Modal>
