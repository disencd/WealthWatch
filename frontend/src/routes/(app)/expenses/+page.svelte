<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { money, fmtDate } from '$lib/utils';
  import { notify } from '$lib/components/notify';
  import { categories } from '$lib/stores/categories';
  import { currentUser } from '$lib/stores/auth';
  import Modal from '$lib/components/Modal.svelte';
  import { Plus } from 'lucide-svelte';

  let expenses: Array<Record<string, unknown>> = $state([]);
  let showAdd = $state(false);
  let form = $state({ title: '', amount: 0, category: '', description: '', split_with: '' });

  let expenseCats = $derived($categories.filter(c => c.type === 'expense'));

  onMount(() => { loadExpenses(); });

  async function loadExpenses() {
    try {
      const data = await api<Array<Record<string, unknown>>>('/expenses');
      expenses = Array.isArray(data) ? data : [];
    } catch { /* handled */ }
  }

  async function addExpense(e: Event) {
    e.preventDefault();
    const amount = Number(form.amount);
    const splitWith = form.split_with ? form.split_with.split(',').map(id => parseInt(id.trim())).filter(Boolean) : [];
    const user = $currentUser as Record<string, unknown>;
    const splitAmount = amount / (splitWith.length + 1);
    const splits = [{ user_id: user.id, amount: splitAmount }];
    splitWith.forEach(uid => splits.push({ user_id: uid, amount: splitAmount }));
    try {
      await api('/expenses', { method: 'POST', body: JSON.stringify({
        title: form.title, amount, description: form.description, category: form.category,
        date: new Date().toISOString(), splits
      })});
      showAdd = false;
      notify('Expense added', 'success');
      await loadExpenses();
    } catch { /* handled */ }
  }
</script>

<div class="flex justify-between items-center mb-6">
  <div></div>
  <button onclick={() => { form = { title: '', amount: 0, category: '', description: '', split_with: '' }; showAdd = true; }}
    class="bg-brand-600 text-white px-4 py-2 rounded-lg hover:bg-brand-700 text-sm font-medium flex items-center gap-2">
    <Plus size={16} /> Add Expense
  </button>
</div>

<div class="bg-white rounded-xl shadow-sm border">
  {#each expenses as expense}
    <div class="p-4 border-b last:border-b-0">
      <div class="flex justify-between items-start">
        <div>
          <h4 class="font-semibold">{expense.title}</h4>
          <p class="text-sm text-gray-500 mt-1">
            Paid by {(expense.payer as Record<string, string>)?.first_name || '?'} {(expense.payer as Record<string, string>)?.last_name || ''} &middot; {fmtDate(expense.date as string)}
          </p>
          <div class="mt-2 flex flex-wrap gap-1">
            {#each ((expense.splits || []) as Array<Record<string, unknown>>) as s}
              <span class="text-xs bg-gray-100 px-2 py-1 rounded-full">
                {(s.user as Record<string, string>)?.first_name || 'User ' + s.user_id}: {money(s.amount as number)}
              </span>
            {/each}
          </div>
        </div>
        <p class="text-xl font-bold">{money(expense.amount as number)}</p>
      </div>
    </div>
  {:else}
    <p class="text-gray-400 text-center py-8">No split expenses.</p>
  {/each}
</div>

<Modal title="Add Split Expense" open={showAdd} onClose={() => showAdd = false}>
  <form onsubmit={addExpense} class="space-y-4">
    <div><label class="block text-sm font-medium mb-1">Title</label><input bind:value={form.title} required class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
    <div class="grid grid-cols-2 gap-3">
      <div><label class="block text-sm font-medium mb-1">Amount</label><input bind:value={form.amount} type="number" step="0.01" required class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
      <div><label class="block text-sm font-medium mb-1">Category</label>
        <select bind:value={form.category} class="w-full border rounded-lg px-3 py-2 text-sm">
          <option value="">None</option>
          {#each expenseCats as c}<option value={c.name}>{c.name}</option>{/each}
        </select>
      </div>
    </div>
    <div><label class="block text-sm font-medium mb-1">Description</label><textarea bind:value={form.description} rows="2" class="w-full border rounded-lg px-3 py-2 text-sm"></textarea></div>
    <div><label class="block text-sm font-medium mb-1">Split With (User IDs, comma-separated)</label><input bind:value={form.split_with} placeholder="e.g. 2,3" class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
    <button type="submit" class="w-full bg-brand-600 text-white py-2.5 rounded-lg hover:bg-brand-700 font-medium">Add Expense</button>
  </form>
</Modal>
