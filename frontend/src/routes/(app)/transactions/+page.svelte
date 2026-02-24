<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { money, fmtDate } from '$lib/utils';
  import { notify } from '$lib/components/notify';
  import { categories, subCategories, loadCategories } from '$lib/stores/categories';
  import Modal from '$lib/components/Modal.svelte';
  import { Plus } from 'lucide-svelte';

  let txs: Array<Record<string, unknown>> = $state([]);
  let filterCat = $state('');
  let filterMonth = $state('');
  let showAdd = $state(false);
  let form = $state({ title: '', category_id: '', sub_category_id: '', amount: 0, date: new Date().toISOString().split('T')[0], merchant: '', notes: '' });

  let expenseCats = $derived($categories.filter(c => c.type === 'expense'));

  onMount(() => { loadTxs(); });

  async function loadTxs() {
    let url = '/budget/expenses';
    const params: string[] = [];
    if (filterCat) params.push('category_id=' + filterCat);
    if (filterMonth) { const [y, m] = filterMonth.split('-'); params.push('year=' + y, 'month=' + parseInt(m)); }
    if (params.length) url += '?' + params.join('&');
    try {
      const data = await api<Array<Record<string, unknown>>>(url);
      txs = Array.isArray(data) ? data : [];
    } catch { /* handled */ }
  }

  async function addTx(e: Event) {
    e.preventDefault();
    try {
      await api('/budget/expenses', { method: 'POST', body: JSON.stringify({
        ...form, category_id: parseInt(form.category_id), sub_category_id: parseInt(form.sub_category_id), amount: Number(form.amount)
      })});
      showAdd = false;
      notify('Transaction added', 'success');
      await loadTxs();
    } catch { /* handled */ }
  }

  async function importInfoCsv(e: Event) {
    const input = e.target as HTMLInputElement;
    if (!input.files?.length) return;
    const fd = new FormData();
    fd.append('file', input.files[0]);
    try {
      const res = await api<Record<string, number>>('/budget/import/categories-csv', { method: 'POST', body: fd, headers: {} });
      await loadCategories();
      notify(`Imported categories: ${res.created_categories || 0}, sub-categories: ${res.created_sub_categories || 0}`, 'success');
      input.value = '';
    } catch { /* handled */ }
  }

  async function importMonthlyCsvs(e: Event) {
    const input = e.target as HTMLInputElement;
    if (!input.files?.length) return;
    const fd = new FormData();
    for (const f of input.files) fd.append('files', f);
    try {
      const res = await api<Record<string, number>>('/budget/import/monthly-csv', { method: 'POST', body: fd, headers: {} });
      await loadCategories();
      await loadTxs();
      notify(`Imported transactions: ${res.created_budget_expenses || 0}`, 'success');
      input.value = '';
    } catch { /* handled */ }
  }

  let infoCsvInput: HTMLInputElement;
  let monthlyCsvInput: HTMLInputElement;
</script>

<div class="flex items-center justify-between mb-6">
  <div class="flex items-center space-x-3">
    <select bind:value={filterCat} onchange={() => loadTxs()} class="text-sm border rounded-lg px-3 py-2">
      <option value="">All Categories</option>
      {#each expenseCats as c}<option value={c.id}>{c.name}</option>{/each}
    </select>
    <input type="month" bind:value={filterMonth} onchange={() => loadTxs()} class="text-sm border rounded-lg px-3 py-2" />
  </div>
  <button onclick={() => { form = { title: '', category_id: String(expenseCats[0]?.id || ''), sub_category_id: String($subCategories[0]?.id || ''), amount: 0, date: new Date().toISOString().split('T')[0], merchant: '', notes: '' }; showAdd = true; }}
    class="bg-brand-600 text-white px-4 py-2 rounded-lg hover:bg-brand-700 text-sm font-medium flex items-center gap-2">
    <Plus size={16} /> Add Transaction
  </button>
</div>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
  <div class="bg-white rounded-xl shadow-sm border p-5">
    <h3 class="font-semibold text-gray-900">Import Categories</h3>
    <p class="text-sm text-gray-500 mt-1">Upload the FinancialDocs Info CSV to create categories and sub-categories.</p>
    <div class="mt-4 space-y-3">
      <input bind:this={infoCsvInput} type="file" accept=".csv,text/csv" class="w-full text-sm border rounded-lg px-3 py-2 bg-white" />
      <button onclick={() => infoCsvInput.files?.length && importInfoCsv({ target: infoCsvInput } as unknown as Event)}
        class="w-full bg-gray-900 text-white px-4 py-2.5 rounded-lg hover:bg-black text-sm font-medium">Import Info CSV</button>
    </div>
  </div>
  <div class="bg-white rounded-xl shadow-sm border p-5">
    <h3 class="font-semibold text-gray-900">Import Monthly Transactions</h3>
    <p class="text-sm text-gray-500 mt-1">Upload one or more monthly CSVs to create transactions.</p>
    <div class="mt-4 space-y-3">
      <input bind:this={monthlyCsvInput} type="file" accept=".csv,text/csv" multiple class="w-full text-sm border rounded-lg px-3 py-2 bg-white" />
      <button onclick={() => monthlyCsvInput.files?.length && importMonthlyCsvs({ target: monthlyCsvInput } as unknown as Event)}
        class="w-full bg-gray-900 text-white px-4 py-2.5 rounded-lg hover:bg-black text-sm font-medium">Import Monthly CSVs</button>
    </div>
  </div>
</div>

<div class="bg-white rounded-xl shadow-sm border overflow-hidden">
  <table class="min-w-full text-sm">
    <thead class="bg-gray-50 text-gray-500 uppercase text-xs">
      <tr>
        <th class="px-4 py-3 text-left">Date</th>
        <th class="px-4 py-3 text-left">Title</th>
        <th class="px-4 py-3 text-left">Merchant</th>
        <th class="px-4 py-3 text-left">Category</th>
        <th class="px-4 py-3 text-right">Amount</th>
      </tr>
    </thead>
    <tbody class="divide-y">
      {#each txs as t}
        <tr class="hover:bg-gray-50">
          <td class="px-4 py-3 text-gray-500">{fmtDate(t.date as string)}</td>
          <td class="px-4 py-3 font-medium">{t.title}</td>
          <td class="px-4 py-3 text-gray-500">{t.merchant || '-'}</td>
          <td class="px-4 py-3">
            <span class="text-xs bg-gray-100 px-2 py-1 rounded-full">
              {(t.category as Record<string, string>)?.name || ''}{(t.sub_category as Record<string, string>)?.name ? ' / ' + (t.sub_category as Record<string, string>).name : ''}
            </span>
          </td>
          <td class="px-4 py-3 text-right font-semibold text-red-600">-{money(t.amount as number)}</td>
        </tr>
      {:else}
        <tr><td colspan="5" class="px-4 py-8 text-center text-gray-400">No transactions found</td></tr>
      {/each}
    </tbody>
  </table>
</div>

<Modal title="Add Transaction" open={showAdd} onClose={() => showAdd = false}>
  <form onsubmit={addTx} class="space-y-4">
    <div><label class="block text-sm font-medium mb-1">Title</label><input bind:value={form.title} required class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
    <div class="grid grid-cols-2 gap-3">
      <div><label class="block text-sm font-medium mb-1">Category</label>
        <select bind:value={form.category_id} required class="w-full border rounded-lg px-3 py-2 text-sm">
          {#each expenseCats as c}<option value={c.id}>{c.name}</option>{/each}
        </select>
      </div>
      <div><label class="block text-sm font-medium mb-1">Sub-Category</label>
        <select bind:value={form.sub_category_id} required class="w-full border rounded-lg px-3 py-2 text-sm">
          {#each $subCategories as s}<option value={s.id}>{s.name}</option>{/each}
        </select>
      </div>
    </div>
    <div class="grid grid-cols-2 gap-3">
      <div><label class="block text-sm font-medium mb-1">Amount</label><input bind:value={form.amount} type="number" step="0.01" required class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
      <div><label class="block text-sm font-medium mb-1">Date</label><input bind:value={form.date} type="date" required class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
    </div>
    <div><label class="block text-sm font-medium mb-1">Merchant</label><input bind:value={form.merchant} class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
    <div><label class="block text-sm font-medium mb-1">Notes</label><textarea bind:value={form.notes} rows="2" class="w-full border rounded-lg px-3 py-2 text-sm"></textarea></div>
    <button type="submit" class="w-full bg-brand-600 text-white py-2.5 rounded-lg hover:bg-brand-700 font-medium">Save Transaction</button>
  </form>
</Modal>
