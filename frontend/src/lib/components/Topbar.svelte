<script lang="ts">
  import { currentUser } from '$lib/stores/auth';
  import { page } from '$app/stores';

  const pageTitles: Record<string, string> = {
    '/dashboard': 'Dashboard',
    '/networth': 'Net Worth',
    '/accounts': 'Accounts',
    '/investments': 'Investments',
    '/transactions': 'Transactions',
    '/budgets': 'Budgets',
    '/recurring': 'Recurring Bills',
    '/rules': 'Auto Rules',
    '/reports': 'Spending Trends',
    '/cashflow': 'Cash Flow',
    '/expenses': 'Split Expenses',
    '/groups': 'Groups',
    '/balances': 'Balances',
    '/receipts': 'Receipts',
    '/family': 'Family / Partner'
  };

  let title = $derived(pageTitles[$page.url.pathname] || 'WealthWatch');
  let user = $derived($currentUser as Record<string, string> | null);
  let initials = $derived(
    user ? (user.first_name?.[0] || '') + (user.last_name?.[0] || '') : ''
  );
</script>

<header class="bg-white border-b border-gray-200 sticky top-0 z-20">
  <div class="flex items-center justify-between px-6 h-16">
    <h2 class="text-lg font-semibold text-gray-900">{title}</h2>
    <div class="flex items-center space-x-4">
      {#if user}
        <span class="text-sm text-gray-500">Welcome, <span class="font-medium text-gray-700">{user.first_name}</span></span>
        <div class="w-8 h-8 bg-brand-100 text-brand-700 rounded-full flex items-center justify-center text-sm font-bold">
          {initials}
        </div>
      {/if}
    </div>
  </div>
</header>
