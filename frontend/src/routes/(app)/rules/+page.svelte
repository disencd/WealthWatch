<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { notify } from '$lib/components/notify';
  import { categories } from '$lib/stores/categories';
  import Modal from '$lib/components/Modal.svelte';
  import { Plus } from 'lucide-svelte';

  let rules: Array<Record<string, unknown>> = $state([]);
  let showAdd = $state(false);
  let form = $state({ merchant_pattern: '', min_amount: '', max_amount: '', category_id: '' });

  let expenseCats = $derived($categories.filter(c => c.type === 'expense'));

  onMount(() => { loadRules(); });

  async function loadRules() {
    try {
      const data = await api<Array<Record<string, unknown>>>('/rules');
      rules = Array.isArray(data) ? data : [];
    } catch { /* handled */ }
  }

  async function addRule(e: Event) {
    e.preventDefault();
    const body: Record<string, unknown> = { merchant_pattern: form.merchant_pattern, category_id: parseInt(form.category_id) };
    if (form.min_amount) body.min_amount = parseFloat(form.min_amount);
    if (form.max_amount) body.max_amount = parseFloat(form.max_amount);
    try {
      await api('/rules', { method: 'POST', body: JSON.stringify(body) });
      showAdd = false;
      notify('Rule created', 'success');
      await loadRules();
    } catch { /* handled */ }
  }

  async function deleteRule(id: number) {
    if (!confirm('Delete this rule?')) return;
    try {
      await api('/rules/' + id, { method: 'DELETE' });
      notify('Deleted', 'success');
      await loadRules();
    } catch { /* handled */ }
  }
</script>

<div class="flex items-center justify-between mb-6">
  <p class="text-sm text-gray-500">Set up if-then rules to automatically categorize transactions by merchant or amount.</p>
  <button onclick={() => { form = { merchant_pattern: '', min_amount: '', max_amount: '', category_id: String(expenseCats[0]?.id || '') }; showAdd = true; }}
    class="bg-brand-600 text-white px-4 py-2 rounded-lg hover:bg-brand-700 text-sm font-medium flex items-center gap-2">
    <Plus size={16} /> Add Rule
  </button>
</div>

<div class="space-y-3">
  {#each rules as r}
    <div class="bg-white rounded-xl shadow-sm border p-5 flex items-center justify-between">
      <div>
        <p class="text-sm"><span class="font-medium">IF</span> merchant matches "<span class="text-brand-600 font-semibold">{r.merchant_pattern}</span>"
          {#if r.min_amount != null} AND amount &gt;= ${r.min_amount}{/if}
          {#if r.max_amount != null} AND amount &lt;= ${r.max_amount}{/if}
        </p>
        <p class="text-sm mt-1"><span class="font-medium">THEN</span> categorize as
          <span class="bg-brand-100 text-brand-700 px-2 py-0.5 rounded text-xs font-medium">
            {(r.category as Record<string, string>)?.name || ''}{(r.sub_category as Record<string, string>)?.name ? ' / ' + (r.sub_category as Record<string, string>).name : ''}
          </span>
        </p>
      </div>
      <button onclick={() => deleteRule(r.id as number)} class="text-red-500 hover:underline text-xs">Delete</button>
    </div>
  {:else}
    <p class="text-gray-400 text-center py-8">No rules defined.</p>
  {/each}
</div>

<Modal title="Add Auto-Categorization Rule" open={showAdd} onClose={() => showAdd = false}>
  <form onsubmit={addRule} class="space-y-4">
    <div><label class="block text-sm font-medium mb-1">Merchant Pattern (contains)</label><input bind:value={form.merchant_pattern} required class="w-full border rounded-lg px-3 py-2 text-sm" placeholder="e.g. Starbucks" /></div>
    <div class="grid grid-cols-2 gap-3">
      <div><label class="block text-sm font-medium mb-1">Min Amount (optional)</label><input bind:value={form.min_amount} type="number" step="0.01" class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
      <div><label class="block text-sm font-medium mb-1">Max Amount (optional)</label><input bind:value={form.max_amount} type="number" step="0.01" class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
    </div>
    <div><label class="block text-sm font-medium mb-1">Assign to Category</label>
      <select bind:value={form.category_id} required class="w-full border rounded-lg px-3 py-2 text-sm">
        {#each expenseCats as c}<option value={c.id}>{c.name}</option>{/each}
      </select>
    </div>
    <button type="submit" class="w-full bg-brand-600 text-white py-2.5 rounded-lg hover:bg-brand-700 font-medium">Save Rule</button>
  </form>
</Modal>
