<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { getMyBilling, listMyOrders, type Plan, type Subscription, type UsageSummary, type Order } from '$lib/apis/billing';

	let plan: Plan | null = null;
	let subscription: Subscription | null = null;
	let usage: UsageSummary | null = null;
	let orders: Order[] = [];
	let loading = true;

	onMount(async () => {
		const token = localStorage.token;
		if (!token) {
			goto('/auth');
			return;
		}
		try {
			const [me, list] = await Promise.all([getMyBilling(token), listMyOrders(token)]);
			plan = me.plan;
			subscription = me.subscription;
			usage = me.usage;
			orders = list;
		} catch (e: any) {
			toast.error(typeof e === 'string' ? e : '加载失败');
		} finally {
			loading = false;
		}
	});

	const cny = (cents: number) => `¥${(cents / 100).toFixed(2)}`;
	const fmtDate = (epoch: number) =>
		new Date(epoch * 1000).toLocaleString('zh-CN', { hour12: false });
	const pct = (used: number, limit: number) => {
		if (limit < 0) return 0;
		if (limit === 0) return 100;
		return Math.min(100, Math.round((used / limit) * 100));
	};
</script>

<div class="max-w-3xl mx-auto px-6 py-10">
	<h1 class="text-3xl font-semibold">订阅与账单</h1>

	{#if loading}
		<div class="text-center mt-10 text-gray-500">加载中…</div>
	{:else}
		<section class="mt-8 border rounded-xl p-6 border-gray-200 dark:border-gray-700">
			<div class="flex items-center justify-between">
				<div>
					<div class="text-sm text-gray-500">当前套餐</div>
					<div class="text-2xl font-semibold mt-1">{plan?.name ?? '免费版'}</div>
				</div>
				<a
					href="/pricing"
					class="rounded-full px-4 py-2 text-sm bg-gray-900 text-white dark:bg-white dark:text-gray-900"
					>升级套餐</a
				>
			</div>
			{#if subscription}
				<div class="mt-4 text-sm text-gray-600 dark:text-gray-400">
					有效期至：{fmtDate(subscription.expires_at)}
				</div>
			{/if}
		</section>

		{#if usage && plan}
			<section class="mt-6 border rounded-xl p-6 border-gray-200 dark:border-gray-700">
				<h2 class="text-lg font-medium">本月用量</h2>
				<div class="mt-4 space-y-4 text-sm">
					<div>
						<div class="flex justify-between">
							<span>消息数</span>
							<span
								>{usage.messages} / {plan.monthly_msg_limit < 0
									? '不限'
									: plan.monthly_msg_limit}</span
							>
						</div>
						{#if plan.monthly_msg_limit >= 0}
							<div class="mt-1 h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
								<div
									class="h-full bg-gray-900 dark:bg-white"
									style="width: {pct(usage.messages, plan.monthly_msg_limit)}%"
								></div>
							</div>
						{/if}
					</div>
					<div>
						<div class="flex justify-between">
							<span>Token</span>
							<span
								>{usage.total_tokens.toLocaleString()} / {plan.monthly_token_limit < 0
									? '不限'
									: plan.monthly_token_limit.toLocaleString()}</span
							>
						</div>
						{#if plan.monthly_token_limit >= 0}
							<div class="mt-1 h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
								<div
									class="h-full bg-gray-900 dark:bg-white"
									style="width: {pct(usage.total_tokens, plan.monthly_token_limit)}%"
								></div>
							</div>
						{/if}
					</div>
				</div>
			</section>
		{/if}

		<section class="mt-6">
			<h2 class="text-lg font-medium">订单记录</h2>
			{#if orders.length === 0}
				<div class="mt-3 text-sm text-gray-500">暂无订单</div>
			{:else}
				<div class="mt-3 border rounded-xl divide-y border-gray-200 dark:border-gray-700">
					{#each orders as o (o.id)}
						<div class="px-4 py-3 flex items-center justify-between text-sm">
							<div>
								<div class="font-medium">{o.plan_code} · {o.period === 'yearly' ? '年付' : '月付'}</div>
								<div class="text-xs text-gray-500">{fmtDate(o.created_at)}</div>
							</div>
							<div class="text-right">
								<div>{cny(o.amount_cents)}</div>
								<div
									class="text-xs {o.status === 'paid'
										? 'text-green-600'
										: o.status === 'pending'
											? 'text-amber-600'
											: 'text-gray-400'}"
								>
									{o.status === 'paid'
										? '已支付'
										: o.status === 'pending'
											? '待支付'
											: o.status === 'expired'
												? '已超时'
												: o.status}
								</div>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</section>
	{/if}
</div>
