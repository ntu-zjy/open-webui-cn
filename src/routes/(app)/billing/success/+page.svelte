<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { toast } from 'svelte-sonner';
	import { getOrder, type Order } from '$lib/apis/billing';

	let orderId = '';
	let order: Order | null = null;
	let pollTimer: ReturnType<typeof setInterval> | null = null;
	let elapsed = 0;

	async function poll() {
		const token = localStorage.token;
		if (!token || !orderId) return;
		try {
			order = await getOrder(token, orderId);
			if (order?.status === 'paid') {
				toast.success('支付成功，订阅已激活');
				if (pollTimer) clearInterval(pollTimer);
				setTimeout(() => goto('/billing'), 1500);
			}
		} catch (e) {
			// silently ignore transient errors during polling
		}
	}

	onMount(() => {
		orderId = $page.url.searchParams.get('order_id') ?? '';
		if (!orderId) {
			goto('/billing');
			return;
		}
		poll();
		pollTimer = setInterval(() => {
			elapsed += 2;
			if (elapsed > 120) {
				if (pollTimer) clearInterval(pollTimer);
				return;
			}
			poll();
		}, 2000);
	});

	onDestroy(() => {
		if (pollTimer) clearInterval(pollTimer);
	});
</script>

<div class="max-w-md mx-auto py-20 text-center">
	{#if order?.status === 'paid'}
		<div class="text-5xl">✅</div>
		<h1 class="mt-4 text-2xl font-semibold">支付成功</h1>
		<p class="mt-2 text-sm text-gray-500">订阅已激活，正在跳转…</p>
	{:else if order?.status === 'expired'}
		<div class="text-5xl">⌛</div>
		<h1 class="mt-4 text-2xl font-semibold">订单已超时</h1>
		<a href="/pricing" class="mt-3 text-sm underline">重新下单</a>
	{:else}
		<div class="text-5xl">⏳</div>
		<h1 class="mt-4 text-2xl font-semibold">等待支付结果…</h1>
		<p class="mt-2 text-sm text-gray-500">支付完成后系统将自动激活订阅，请不要关闭页面</p>
		<a href="/billing" class="mt-6 inline-block text-sm underline">查看账单</a>
	{/if}
</div>
