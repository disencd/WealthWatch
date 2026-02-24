<script lang="ts">
  import { goto } from '$app/navigation';
  import { api } from '$lib/api';
  import { token, currentUser } from '$lib/stores/auth';
  import { BarChart3 } from 'lucide-svelte';
  import { notify } from '$lib/components/notify';

  let first_name = $state('');
  let last_name = $state('');
  let email = $state('');
  let password = $state('');
  let loading = $state(false);

  async function handleRegister(e: Event) {
    e.preventDefault();
    loading = true;
    try {
      const data = await api<{ token: string; user: Record<string, unknown> }>('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ first_name, last_name, email, password })
      });
      token.set(data.token);
      currentUser.set(data.user);
      goto('/dashboard');
    } catch (err: unknown) {
      notify((err as Error).message || 'Registration failed', 'error');
    } finally {
      loading = false;
    }
  }
</script>

<div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-600 to-brand-800">
  <div class="bg-white shadow-2xl rounded-2xl p-8 w-full max-w-md">
    <div class="text-center mb-8">
      <div class="inline-flex items-center justify-center w-14 h-14 bg-brand-100 rounded-xl mb-4">
        <BarChart3 size={28} class="text-brand-600" />
      </div>
      <h1 class="text-2xl font-bold text-gray-900">Join WealthWatch</h1>
      <p class="text-gray-500 text-sm mt-1">Start tracking your finances today</p>
    </div>
    <form onsubmit={handleRegister}>
      <div class="grid grid-cols-2 gap-3 mb-4">
        <div>
          <label for="fname" class="block text-sm font-medium text-gray-700 mb-1">First Name</label>
          <input type="text" id="fname" bind:value={first_name} required
            class="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500" />
        </div>
        <div>
          <label for="lname" class="block text-sm font-medium text-gray-700 mb-1">Last Name</label>
          <input type="text" id="lname" bind:value={last_name} required
            class="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500" />
        </div>
      </div>
      <div class="mb-4">
        <label for="email" class="block text-sm font-medium text-gray-700 mb-1">Email</label>
        <input type="email" id="email" bind:value={email} required
          class="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500" />
      </div>
      <div class="mb-6">
        <label for="password" class="block text-sm font-medium text-gray-700 mb-1">Password</label>
        <input type="password" id="password" bind:value={password} required minlength="6"
          class="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500" />
      </div>
      <button type="submit" disabled={loading}
        class="w-full bg-brand-600 text-white py-2.5 px-4 rounded-lg hover:bg-brand-700 font-medium transition disabled:opacity-50">
        {loading ? 'Creating...' : 'Create Account'}
      </button>
    </form>
    <div class="mt-5 text-center">
      <a href="/login" class="text-brand-600 hover:text-brand-800 text-sm font-medium">Already have an account? Sign in</a>
    </div>
  </div>
</div>
