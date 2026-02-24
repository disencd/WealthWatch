<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { notify } from '$lib/components/notify';
  import Modal from '$lib/components/Modal.svelte';
  import { UserPlus } from 'lucide-svelte';

  let members: Array<Record<string, unknown>> = $state([]);
  let showInvite = $state(false);
  let form = $state({ email: '', role: 'admin' });

  onMount(() => { loadFamily(); });

  async function loadFamily() {
    try {
      const data = await api<Array<Record<string, unknown>>>('/families/members');
      members = Array.isArray(data) ? data : [];
    } catch { /* handled */ }
  }

  async function invite(e: Event) {
    e.preventDefault();
    try {
      await api('/families/members', { method: 'POST', body: JSON.stringify(form) });
      showInvite = false;
      notify('Partner added!', 'success');
      await loadFamily();
    } catch { /* handled */ }
  }
</script>

<div class="bg-white rounded-xl shadow-sm border p-6 mb-6">
  <h3 class="font-semibold text-gray-900 mb-2">Shared Access</h3>
  <p class="text-sm text-gray-500 mb-4">Invite your partner to view and manage your household finances. Each person has their own login with a shared view.</p>
  <button onclick={() => { form = { email: '', role: 'admin' }; showInvite = true; }}
    class="bg-brand-600 text-white px-4 py-2 rounded-lg hover:bg-brand-700 text-sm font-medium flex items-center gap-2">
    <UserPlus size={16} /> Invite Partner
  </button>
</div>

<div class="bg-white rounded-xl shadow-sm border p-6">
  <h3 class="font-semibold text-gray-900 mb-4">Family Members</h3>
  <div class="space-y-3">
    {#each members as m}
      {@const user = (m.user || {}) as Record<string, string>}
      <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
        <div class="flex items-center space-x-3">
          <div class="w-9 h-9 bg-brand-100 rounded-full flex items-center justify-center text-brand-700 font-bold text-sm">
            {(user.first_name || '?')[0]}{(user.last_name || '?')[0]}
          </div>
          <div>
            <p class="font-medium text-sm">{user.first_name || ''} {user.last_name || ''}</p>
            <p class="text-xs text-gray-500">{user.email || ''}</p>
          </div>
        </div>
        <span class="text-xs font-medium px-2 py-1 rounded-full bg-brand-100 text-brand-700">{m.role}</span>
      </div>
    {:else}
      <p class="text-gray-400 text-center py-4">No members yet</p>
    {/each}
  </div>
</div>

<Modal title="Invite Partner" open={showInvite} onClose={() => showInvite = false}>
  <form onsubmit={invite} class="space-y-4">
    <p class="text-sm text-gray-500">Your partner must already have a WealthWatch account. Enter their email below to add them to your family.</p>
    <div><label class="block text-sm font-medium mb-1">Partner Email</label><input bind:value={form.email} type="email" required class="w-full border rounded-lg px-3 py-2 text-sm" /></div>
    <div><label class="block text-sm font-medium mb-1">Role</label>
      <select bind:value={form.role} class="w-full border rounded-lg px-3 py-2 text-sm">
        <option value="admin">Admin</option><option value="member">Member</option>
      </select>
    </div>
    <button type="submit" class="w-full bg-brand-600 text-white py-2.5 rounded-lg hover:bg-brand-700 font-medium">Send Invite</button>
  </form>
</Modal>
