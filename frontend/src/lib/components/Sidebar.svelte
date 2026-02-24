<script lang="ts">
  import { page } from '$app/stores';
  import { logout, currentUser } from '$lib/stores/auth';
  import {
    LayoutDashboard, Coins, Landmark, PieChart, Receipt, PiggyBank,
    RefreshCw, Wand2, BarChart3, Shuffle, Split, Users, Scale,
    Camera, Heart, LogOut
  } from 'lucide-svelte';

  const sections = [
    {
      label: 'Overview',
      items: [
        { href: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
        { href: '/networth', icon: Coins, label: 'Net Worth' },
      ]
    },
    {
      label: 'Finance',
      items: [
        { href: '/accounts', icon: Landmark, label: 'Accounts' },
        { href: '/investments', icon: PieChart, label: 'Investments' },
        { href: '/transactions', icon: Receipt, label: 'Transactions' },
        { href: '/budgets', icon: PiggyBank, label: 'Budgets' },
      ]
    },
    {
      label: 'Automation',
      items: [
        { href: '/recurring', icon: RefreshCw, label: 'Recurring Bills' },
        { href: '/rules', icon: Wand2, label: 'Auto Rules' },
      ]
    },
    {
      label: 'Reports',
      items: [
        { href: '/reports', icon: BarChart3, label: 'Spending Trends' },
        { href: '/cashflow', icon: Shuffle, label: 'Cash Flow' },
      ]
    },
    {
      label: 'Sharing',
      items: [
        { href: '/expenses', icon: Split, label: 'Split Expenses' },
        { href: '/groups', icon: Users, label: 'Groups' },
        { href: '/balances', icon: Scale, label: 'Balances' },
      ]
    },
    {
      label: 'More',
      items: [
        { href: '/receipts', icon: Camera, label: 'Receipts' },
        { href: '/family', icon: Heart, label: 'Family / Partner' },
      ]
    }
  ];

  let pathname = $derived($page.url.pathname);
</script>

<aside class="w-64 bg-white border-r border-gray-200 flex flex-col fixed h-full z-30">
  <div class="p-5 border-b border-gray-100">
    <div class="flex items-center space-x-3">
      <div class="w-9 h-9 bg-brand-600 rounded-lg flex items-center justify-center">
        <BarChart3 size={16} class="text-white" />
      </div>
      <span class="text-lg font-bold text-gray-900">WealthWatch</span>
    </div>
  </div>

  <nav class="flex-1 p-3 space-y-1 overflow-y-auto">
    {#each sections as section}
      <p class="px-3 pt-5 pb-1 text-xs font-semibold text-gray-400 uppercase tracking-wider first:pt-3">{section.label}</p>
      {#each section.items as item}
        <a
          href={item.href}
          class="sidebar-link w-full flex items-center px-3 py-2.5 rounded-lg text-sm text-gray-700"
          class:active={pathname === item.href}
        >
          <span class="w-5 mr-3 flex justify-center">
            <item.icon size={16} />
          </span>
          {item.label}
        </a>
      {/each}
    {/each}
  </nav>

  <div class="p-3 border-t border-gray-100">
    <button onclick={() => logout()} class="w-full flex items-center px-3 py-2.5 rounded-lg text-sm text-red-600 hover:bg-red-50">
      <span class="w-5 mr-3 flex justify-center"><LogOut size={16} /></span>
      Sign Out
    </button>
  </div>
</aside>
