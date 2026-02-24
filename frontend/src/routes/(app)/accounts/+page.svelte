<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { money, typeLabel } from '$lib/utils';
  import { notify } from '$lib/components/notify';
  import Modal from '$lib/components/Modal.svelte';
  import { Plus } from 'lucide-svelte';

  interface Account {
    id: number; institution_name: string; account_name: string; account_type: string;
    ownership: string; balance: number; is_asset: boolean;
  }

  let accounts: Account[] = $state([]);
  let filterOwnership = $state('');
  let showAdd = $state(false);
  let showEdit = $state(false);
  let editId = $state(0);

  let form = $state({ institution_name: '', account_name: '', account_type: 'checking', ownership: 'ours', balance: 0 });
  let editForm = $state({ account_name: '', balance: 0, ownership: 'ours' });

  onMount(() => { loadAccounts(); });

  async function loadAccounts() {
    let url = '/accounts';
    if (filterOwnership) url += '?ownership=' + filterOwnership;
    try {
      const data = await api<Account[]>(url);
      accounts = Array.isArray(data) ? data : [];
    } catch { /* handled */ }
  }

  async function addAccount(e: Event) {
    e.preventDefault();
    try {
      await api('/accounts', { method: 'POST', body: JSON.stringify({ ...form, balance: Number(form.balance) }) });
      showAdd = false;
      notify('Account added', 'success');
      await loadAccounts();
    } catch { /* handled */ }
  }

  async function openEdit(id: number) {
    try {
      const a = await api<Account>('/accounts/' + id);
      editId = id;
      editForm = { account_name: a.account_name, balance: a.balance, ownership: a.ownership };
      showEdit = true;
    } catch { /* handled */ }
  }

  async function saveEdit(e: Event) {
    e.preventDefault();
    try {
      await api('/accounts/' + editId, { method: 'PUT', body: JSON.stringify({ ...editForm, balance: Number(editForm.balance) }) });
      showEdit = false;
      notify('Updated', 'success');
      await loadAccounts();
    } catch { /* handled */ }
  }

  async function deleteAccount(id: number) {
    if (!confirm('Delete this account?')) return;
    try {
      await api('/accounts/' + id, { method: 'DELETE' });
      notify('Deleted', 'success');
      await loadAccounts();
    } catch { /* handled */ }
  }
</script>

<div class="flex items-center justify-between mb-6">
  <select bind:value={filterOwnership} onchange={() => loadAccounts()} class="text-sm border rounded-lg px-3 py-2">
    <option value="">All Ownership</option>
    <option value="yours">Yours</option>
    <option value="mine">Mine</option>
    <option value="ours">Ours</option>
  </select>
  <button onclick={() => { form = { institution_name: '', account_name: '', account_type: 'checking', ownership: 'ours', balance: 0 }; showAdd = true; }}
    class="bg-brand-600 text-white px-4 py-2 rounded-lg hover:bg-brand-700 text-sm font-medium flex items-center gap-2">
    <Plus size={16} /> Add Account
  </button>
</div>

<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
  {#each accounts as a (a.id)}
    <div class="bg-white rounded-xl shadow-sm border p-5 ownership-{a.ownership}">
      <div class="flex items-center justify-between mb-3">
        <span class="text-xs font-medium px-2 py-1 rounded-full {a.is_asset ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}">{a.is_asset ? 'Asset' : 'Liability'}</span>
        <span class="text-xs text-gray-400 uppercase">{a.ownership}</span>
      </div>
      <h4 class="font-semibold">{a.account_name}</h4>
      <p class="text-sm text-gray-500">{a.institution_name} &middot; {typeLabel(a.account_type)}</p>
      <p class="text-2xl font-bold mt-3 {a.is_asset ? 'text-green-600' : 'text-red-600'}">{money(a.balance)}</p>
      <div class="flex space-x-2 mt-3">
        <button onclick={() => openEdit(a.id)} class="text-xs text-brand-600 hover:underline">Edit</button>
        <button onclick={() => deleteAccount(a.id)} class="text-xs text-red-500 hover:underline">Delete</button>
      </div>
    </div>
  {:else}
    <p class="text-gray-400 text-center py-8 col-span-full">No accounts yet. Add your first account to get started.</p>
  {/each}
</div>

<Modal title="Add Account" open={showAdd} onClose={() => showAdd = false}>
  <form onsubmit={addAccount} class="space-y-4">
    <div><label class="block text-sm font-medium mb-1">Institution Name</label><input bind:value={form.institution_name} required class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
    <div><label class="block text-sm font-medium mb-1">Account Name</label><input bind:value={form.account_name} required class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
    <div class="grid grid-cols-2 gap-3">
      <div><label class="block text-sm font-medium mb-1">Type</label>
        <select bind:value={form.account_type} class="w-full border rounded-lg px-3 py-2 text-sm">
          <option value="checking">Checking</option><option value="savings">Savings</option><option value="credit_card">Credit Card</option>
          <option value="investment">Investment</option><option value="loan">Loan</option><option value="mortgage">Mortgage</option>
          <option value="real_estate">Real Estate</option><option value="other">Other</option>
        </select>
      </div>
      <div><label class="block text-sm font-medium mb-1">Ownership</label>
        <select bind:value={form.ownership} class="w-full border rounded-lg px-3 py-2 text-sm">
          <option value="ours">Ours (Joint)</option><option value="yours">Yours</option><option value="mine">Mine</option>
        </select>
      </div>
    </div>
    <div><label class="block text-sm font-medium mb-1">Balance</label><input bind:value={form.balance} type="number" step="0.01" required class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
    <button type="submit" class="w-full bg-brand-600 text-white py-2.5 rounded-lg hover:bg-brand-700 font-medium">Add Account</button>
  </form>
</Modal>

<Modal title="Edit Account" open={showEdit} onClose={() => showEdit = false}>
  <form onsubmit={saveEdit} class="space-y-4">
    <div><label class="block text-sm font-medium mb-1">Account Name</label><input bind:value={editForm.account_name} class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
    <div><label class="block text-sm font-medium mb-1">Balance</label><input bind:value={editForm.balance} type="number" step="0.01" class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
    <div><label class="block text-sm font-medium mb-1">Ownership</label>
      <select bind:value={editForm.ownership} class="w-full border rounded-lg px-3 py-2 text-sm">
        <option value="ours">Ours</option><option value="yours">Yours</option><option value="mine">Mine</option>
      </select>
    </div>
    <button type="submit" class="w-full bg-brand-600 text-white py-2.5 rounded-lg hover:bg-brand-700 font-medium">Save</button>
  </form>
</Modal>
