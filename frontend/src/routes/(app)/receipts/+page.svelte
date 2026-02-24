<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { money, fmtDate } from '$lib/utils';
  import { notify } from '$lib/components/notify';
  import Modal from '$lib/components/Modal.svelte';
  import { Upload } from 'lucide-svelte';

  let receipts: Array<Record<string, unknown>> = $state([]);
  let showAdd = $state(false);
  let fileInput: HTMLInputElement;
  let form = $state({ merchant: '', amount: '', date: '', notes: '' });

  onMount(() => { loadReceipts(); });

  async function loadReceipts() {
    try {
      const data = await api<Array<Record<string, unknown>>>('/receipts');
      receipts = Array.isArray(data) ? data : [];
    } catch { /* handled */ }
  }

  async function uploadReceipt(e: Event) {
    e.preventDefault();
    if (!fileInput?.files?.length) return;
    const fd = new FormData();
    fd.append('file', fileInput.files[0]);
    if (form.merchant) fd.append('merchant', form.merchant);
    if (form.amount) fd.append('amount', form.amount);
    if (form.date) fd.append('date', form.date);
    if (form.notes) fd.append('notes', form.notes);
    try {
      await api('/receipts', { method: 'POST', body: fd, headers: {} });
      showAdd = false;
      notify('Receipt uploaded', 'success');
      await loadReceipts();
    } catch { /* handled */ }
  }

  async function deleteReceipt(id: number) {
    if (!confirm('Delete this receipt?')) return;
    try {
      await api('/receipts/' + id, { method: 'DELETE' });
      notify('Deleted', 'success');
      await loadReceipts();
    } catch { /* handled */ }
  }
</script>

<div class="flex justify-between items-center mb-6">
  <p class="text-sm text-gray-500">Upload and manage receipts for tax or warranty purposes.</p>
  <button onclick={() => { form = { merchant: '', amount: '', date: '', notes: '' }; showAdd = true; }}
    class="bg-brand-600 text-white px-4 py-2 rounded-lg hover:bg-brand-700 text-sm font-medium flex items-center gap-2">
    <Upload size={16} /> Upload Receipt
  </button>
</div>

<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
  {#each receipts as r}
    <div class="bg-white rounded-xl shadow-sm border p-5">
      <div class="flex items-center space-x-3 mb-3">
        <div class="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center text-gray-500">
          <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z"/></svg>
        </div>
        <div>
          <p class="font-medium text-sm">{r.file_name}</p>
          <p class="text-xs text-gray-400">{r.merchant || 'No merchant'}{r.amount ? ' · ' + money(r.amount as number) : ''}</p>
        </div>
      </div>
      {#if r.notes}<p class="text-sm text-gray-500 mb-2">{r.notes}</p>{/if}
      <div class="flex justify-between items-center">
        <span class="text-xs text-gray-400">{fmtDate(r.created_at as string)}</span>
        <button onclick={() => deleteReceipt(r.id as number)} class="text-xs text-red-500 hover:underline">Delete</button>
      </div>
    </div>
  {:else}
    <p class="text-gray-400 text-center py-8 col-span-full">No receipts uploaded yet.</p>
  {/each}
</div>

<Modal title="Upload Receipt" open={showAdd} onClose={() => showAdd = false}>
  <form onsubmit={uploadReceipt} class="space-y-4">
    <div><label class="block text-sm font-medium mb-1">File</label><input bind:this={fileInput} type="file" accept="image/*,.pdf" required class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
    <div class="grid grid-cols-2 gap-3">
      <div><label class="block text-sm font-medium mb-1">Merchant</label><input bind:value={form.merchant} class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
      <div><label class="block text-sm font-medium mb-1">Amount</label><input bind:value={form.amount} type="number" step="0.01" class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
    </div>
    <div><label class="block text-sm font-medium mb-1">Date</label><input bind:value={form.date} type="date" class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
    <div><label class="block text-sm font-medium mb-1">Notes</label><textarea bind:value={form.notes} rows="2" class="w-full border rounded-lg px-3 py-2 text-sm"></textarea></div>
    <button type="submit" class="w-full bg-brand-600 text-white py-2.5 rounded-lg hover:bg-brand-700 font-medium">Upload</button>
  </form>
</Modal>
