<script lang="ts">
	import '../app.css';
	import { toasts } from '$lib/components/notify';
	import Notification from '$lib/components/Notification.svelte';

	let { children } = $props();
</script>

<svelte:head>
	<title>WealthWatch</title>
</svelte:head>

{@render children()}

{#each $toasts as toast (toast.id)}
	<Notification message={toast.message} type={toast.type} onClose={() => toasts.update(t => t.filter(x => x.id !== toast.id))} />
{/each}
