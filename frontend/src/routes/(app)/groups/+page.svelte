<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { notify } from '$lib/components/notify';
  import Modal from '$lib/components/Modal.svelte';
  import { Plus, Users } from 'lucide-svelte';

  let groups: Array<Record<string, unknown>> = $state([]);
  let showAdd = $state(false);
  let form = $state({ name: '', description: '' });

  onMount(() => { loadGroups(); });

  async function loadGroups() {
    try {
      const data = await api<Array<Record<string, unknown>>>('/groups');
      groups = Array.isArray(data) ? data : [];
    } catch { /* handled */ }
  }

  async function addGroup(e: Event) {
    e.preventDefault();
    try {
      await api('/groups', { method: 'POST', body: JSON.stringify(form) });
      showAdd = false;
      notify('Group created', 'success');
      await loadGroups();
    } catch { /* handled */ }
  }
</script>

<div class="flex justify-between items-center mb-6">
  <div></div>
  <button onclick={() => { form = { name: '', description: '' }; showAdd = true; }}
    class="bg-brand-600 text-white px-4 py-2 rounded-lg hover:bg-brand-700 text-sm font-medium flex items-center gap-2">
    <Plus size={16} /> Add Group
  </button>
</div>

<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
  {#each groups as g}
    {@const members = (g.members || []) as Array<Record<string, string>>}
    <div class="bg-white rounded-xl shadow-sm border p-5">
      <div class="flex items-center justify-between mb-3">
        <h3 class="font-semibold">{g.name}</h3>
        <div class="w-8 h-8 bg-brand-100 rounded-lg flex items-center justify-center">
          <Users size={14} class="text-brand-600" />
        </div>
      </div>
      <p class="text-sm text-gray-500 mb-3">{g.description || 'No description'}</p>
      <div class="flex items-center justify-between">
        <div class="flex -space-x-2">
          {#each members.slice(0, 4) as m}
            <div class="w-7 h-7 bg-brand-500 rounded-full flex items-center justify-center text-white text-xs font-medium border-2 border-white">
              {(m.first_name || '?')[0]}{(m.last_name || '?')[0]}
            </div>
          {/each}
          {#if members.length > 4}
            <div class="w-7 h-7 bg-gray-200 rounded-full flex items-center justify-center text-gray-600 text-xs font-medium border-2 border-white">
              +{members.length - 4}
            </div>
          {/if}
        </div>
        <span class="text-xs text-gray-400">{members.length} members</span>
      </div>
    </div>
  {:else}
    <p class="text-gray-400 text-center py-8 col-span-full">No groups yet.</p>
  {/each}
</div>

<Modal title="Create Group" open={showAdd} onClose={() => showAdd = false}>
  <form onsubmit={addGroup} class="space-y-4">
    <div><label class="block text-sm font-medium mb-1">Name</label><input bind:value={form.name} required class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
    <div><label class="block text-sm font-medium mb-1">Description</label><textarea bind:value={form.description} rows="2" class="w-full border rounded-lg px-3 py-2 text-sm"></textarea></div>
    <button type="submit" class="w-full bg-brand-600 text-white py-2.5 rounded-lg hover:bg-brand-700 font-medium">Create Group</button>
  </form>
</Modal>
