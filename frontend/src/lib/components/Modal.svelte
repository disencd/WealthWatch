<script lang="ts">
  import { X } from 'lucide-svelte';
  import type { Snippet } from 'svelte';

  let { title, open = false, onClose, children }: {
    title: string;
    open: boolean;
    onClose: () => void;
    children: Snippet;
  } = $props();
</script>

{#if open}
<div class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" role="dialog">
  <div class="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
    <div class="flex items-center justify-between p-5 border-b">
      <h3 class="text-lg font-semibold text-gray-900">{title}</h3>
      <button onclick={onClose} class="text-gray-400 hover:text-gray-600">
        <X size={20} />
      </button>
    </div>
    <div class="p-5">
      {@render children()}
    </div>
  </div>
</div>
{/if}
