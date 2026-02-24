<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { money, fmtDate } from '$lib/utils';
  import { notify } from '$lib/components/notify';
  import { categories } from '$lib/stores/categories';
  import Modal from '$lib/components/Modal.svelte';
  import { Plus } from 'lucide-svelte';

  let items: Array<Record<string, unknown>> = $state([]);
  let showAdd = $state(false);
  let form = $state({ merchant: '', amount: 0, frequency: 'monthly', next_due_date: '', category_id: '' });

  let expenseCats = $derived($categories.filter(c => c.type === 'expense'));

  onMount(() => { loadRecurring(); });

  async function loadRecurring() {
    try {
      const data = await api<Array<Record<string, unknown>>>('/recurring');
      items = Array.isArray(data) ? data : [];
    } catch { /* handled */ }
  }

  async function addRecurring(e: Event) {
    e.preventDefault();
    const body: Record<string, unknown> = { merchant: form.merchant, amount: Number(form.amount), frequency: form.frequency, next_due_date: form.next_due_date };
    if (form.category_id) body.category_id = parseInt(form.category_id);
    try {
      await api('/recurring', { method: 'POST', body: JSON.stringify(body) });
      showAdd = false;
      notify('Added', 'success');
      await loadRecurring();
    } catch { /* handled */ }
  }

  async function deleteRecurring(id: number) {
    if (!confirm('Remove this recurring bill?')) return;
    try {
      await api('/recurring/' + id, { method: 'DELETE' });
      notify('Removed', 'success');
      await loadRecurring();
    } catch { /* handled */ }
  }
</script>

<div class="flex items-center justify-between mb-6">
  <div></div>
  <button onclick={() => { form = { merchant: '', amount: 0, frequency: 'monthly', next_due_date: '', category_id: '' }; showAdd = true; }}
    class="bg-brand-600 text-white px-4 py-2 rounded-lg hover:bg-brand-700 text-sm font-medium flex items-center gap-2">
    <Plus size={16} /> Add Subscription
  </button>
</div>

<div class="space-y-3">
  {#each items as r}
    <div class="bg-white rounded-xl shadow-sm border p-5 flex items-center justify-between">
      <div>
        <h4 class="font-semibold">{r.merchant}</h4>
        <p class="text-sm text-gray-500">{r.frequency} &middot; Next: {fmtDate(r.next_due_date as string)}</p>
        {#if (r.category as Record<string, string>)?.name}
          <span class="text-xs bg-gray-100 px-2 py-0.5 rounded-full">{(r.category as Record<string, string>).name}</span>
        {/if}
      </div>
      <div class="text-right">
        <p class="text-lg font-bold">{money(r.amount as number)}</p>
        <button onclick={() => deleteRecurring(r.id as number)} class="text-xs text-red-500 hover:underline mt-1">Remove</button>
      </div>
    </div>
  {:else}
    <p class="text-gray-400 text-center py-8">No recurring bills tracked.</p>
  {/each}
</div>

<Modal title="Add Recurring Bill" open={showAdd} onClose={() => showAdd = false}>
  <form onsubmit={addRecurring} class="space-y-4">
    <div><label class="block text-sm font-medium mb-1">Merchant / Name</label><input bind:value={form.merchant} required class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
    <div class="grid grid-cols-2 gap-3">
      <div><label class="block text-sm font-medium mb-1">Amount</label><input bind:value={form.amount} type="number" step="0.01" required class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
      <div><label class="block text-sm font-medium mb-1">Frequency</label>
        <select bind:value={form.frequency} class="w-full border rounded-lg px-3 py-2 text-sm">
          <option value="monthly">Monthly</option><option value="weekly">Weekly</option><option value="yearly">Yearly</option><option value="quarterly">Quarterly</option>
        </select>
      </div>
    </div>
    <div class="grid grid-cols-2 gap-3">
      <div><label class="block text-sm font-medium mb-1">Next Due Date</label><input bind:value={form.next_due_date} type="date" required class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
      <div><label class="block text-sm font-medium mb-1">Category</label>
        <select bind:value={form.category_id} class="w-full border rounded-lg px-3 py-2 text-sm">
          <option value="">None</option>
          {#each expenseCats as c}<option value={c.id}>{c.name}</option>{/each}
        </select>
      </div>
    </div>
    <button type="submit" class="w-full bg-brand-600 text-white py-2.5 rounded-lg hover:bg-brand-700 font-medium">Save</button>
  </form>
</Modal>
