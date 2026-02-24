<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { money, pct } from '$lib/utils';
  import { notify } from '$lib/components/notify';
  import { categories } from '$lib/stores/categories';
  import Modal from '$lib/components/Modal.svelte';
  import { Plus } from 'lucide-svelte';

  let budgets: Array<Record<string, unknown>> = $state([]);
  let catSpending: Record<number, number> = $state({});
  let showAdd = $state(false);
  const now = new Date();
  let form = $state({ category_id: '', period: 'monthly', year: now.getFullYear(), month: now.getMonth() + 1, amount: 0 });

  let expenseCats = $derived($categories.filter(c => c.type === 'expense'));

  onMount(() => { loadBudgets(); });

  async function loadBudgets() {
    const [b, summary] = await Promise.all([
      api<Array<Record<string, unknown>>>(`/budget/budgets?year=${now.getFullYear()}&month=${now.getMonth() + 1}`),
      api<Record<string, unknown>>(`/budget/summary/monthly?year=${now.getFullYear()}&month=${now.getMonth() + 1}`).catch(() => ({})),
    ]);
    budgets = Array.isArray(b) ? b : [];
    const spending: Record<number, number> = {};
    ((summary?.by_category || []) as Array<Record<string, unknown>>).forEach((c: Record<string, unknown>) => {
      spending[c.category_id as number] = c.total_amount as number;
    });
    catSpending = spending;
  }

  async function addBudget(e: Event) {
    e.preventDefault();
    try {
      await api('/budget/budgets', { method: 'POST', body: JSON.stringify({
        ...form, category_id: parseInt(form.category_id), year: Number(form.year), month: Number(form.month), amount: Number(form.amount)
      })});
      showAdd = false;
      notify('Budget created', 'success');
      await loadBudgets();
    } catch { /* handled */ }
  }
</script>

<div class="flex items-center justify-between mb-6">
  <h3 class="font-semibold">Monthly Budget Overview</h3>
  <button onclick={() => { form = { category_id: String(expenseCats[0]?.id || ''), period: 'monthly', year: now.getFullYear(), month: now.getMonth() + 1, amount: 0 }; showAdd = true; }}
    class="bg-brand-600 text-white px-4 py-2 rounded-lg hover:bg-brand-700 text-sm font-medium flex items-center gap-2">
    <Plus size={16} /> Set Budget
  </button>
</div>

<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
  {#each budgets as b}
    {@const spent = catSpending[(b.category_id as number)] || 0}
    {@const pctVal = (b.amount as number) > 0 ? Math.min((spent / (b.amount as number)) * 100, 100) : 0}
    {@const over = spent > (b.amount as number)}
    <div class="bg-white rounded-xl shadow-sm border p-5">
      <div class="flex justify-between items-center mb-2">
        <span class="font-medium">{(b.category as Record<string, string>)?.name || 'Budget'}{(b.sub_category as Record<string, string>)?.name ? ' / ' + (b.sub_category as Record<string, string>).name : ''}</span>
        <span class="text-xs {over ? 'text-red-600' : 'text-gray-500'}">{money(spent)} / {money(b.amount as number)}</span>
      </div>
      <div class="w-full bg-gray-100 rounded-full h-2.5">
        <div class="h-2.5 rounded-full {over ? 'bg-red-500' : 'bg-brand-500'}" style="width:{pctVal}%"></div>
      </div>
      <p class="text-xs text-gray-400 mt-2">{b.period} &middot; {pct(pctVal)} used</p>
    </div>
  {:else}
    <p class="text-gray-400 text-center py-8 col-span-full">No budgets set for this month.</p>
  {/each}
</div>

<Modal title="Set Budget" open={showAdd} onClose={() => showAdd = false}>
  <form onsubmit={addBudget} class="space-y-4">
    <div><label class="block text-sm font-medium mb-1">Category</label>
      <select bind:value={form.category_id} required class="w-full border rounded-lg px-3 py-2 text-sm">
        {#each expenseCats as c}<option value={c.id}>{c.name}</option>{/each}
      </select>
    </div>
    <div class="grid grid-cols-3 gap-3">
      <div><label class="block text-sm font-medium mb-1">Period</label>
        <select bind:value={form.period} class="w-full border rounded-lg px-3 py-2 text-sm">
          <option value="monthly">Monthly</option><option value="yearly">Yearly</option>
        </select>
      </div>
      <div><label class="block text-sm font-medium mb-1">Year</label><input bind:value={form.year} type="number" required class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
      <div><label class="block text-sm font-medium mb-1">Month</label><input bind:value={form.month} type="number" min="1" max="12" class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
    </div>
    <div><label class="block text-sm font-medium mb-1">Amount</label><input bind:value={form.amount} type="number" step="0.01" required class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
    <button type="submit" class="w-full bg-brand-600 text-white py-2.5 rounded-lg hover:bg-brand-700 font-medium">Save Budget</button>
  </form>
</Modal>
