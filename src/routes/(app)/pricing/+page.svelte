<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { listPlans, createOrder, type Plan } from '$lib/apis/billing';

	let plans: Plan[] = [];
	let loading = true;
	let creatingForPlan = '';
	let period: 'monthly' | 'yearly' = 'monthly';
	let payType: 'alipay' | 'wxpay' = 'alipay';

	onMount(async () => {
		try {
			plans = await listPlans();
		} catch (e: any) {
			toast.error(typeof e === 'string' ? e : '加载套餐失败');
		} finally {
			loading = false;
		}
	});

	const cny = (cents: number) => `¥${(cents / 100).toFixed(2)}`;

	async function upgrade(plan: Plan) {
		if (plan.monthly_price_cents <= 0) {
			toast.info('已是免费档位');
			return;
		}
		const token = localStorage.token;
		if (!token) {
			toast.error('请先登录');
			return;
		}
		creatingForPlan = plan.code;
		try {
			const { pay_url } = await createOrder(token, {
				plan_code: plan.code,
				period,
				pay_type: payType
			});
			window.location.href = pay_url;
		} catch (e: any) {
			toast.error(typeof e === 'string' ? e : '下单失败');
		} finally {
			creatingForPlan = '';
		}
	}
</script>

<div class="max-w-5xl mx-auto px-6 py-10">
	<h1 class="text-3xl font-semibold text-center">订阅套餐</h1>
	<p class="text-sm text-gray-500 text-center mt-2">选择适合你的方案，随时可升级或取消</p>

	<div class="mt-6 flex items-center justify-center gap-4 text-sm">
		<div class="flex bg-gray-100 dark:bg-gray-800 rounded-full p-1">
			<button
				class="px-4 py-1 rounded-full {period === 'monthly'
					? 'bg-white dark:bg-gray-700 font-medium'
					: 'text-gray-500'}"
				on:click={() => (period = 'monthly')}>月付</button
			>
			<button
				class="px-4 py-1 rounded-full {period === 'yearly'
					? 'bg-white dark:bg-gray-700 font-medium'
					: 'text-gray-500'}"
				on:click={() => (period = 'yearly')}>年付</button
			>
		</div>
		<div class="flex bg-gray-100 dark:bg-gray-800 rounded-full p-1">
			<button
				class="px-4 py-1 rounded-full {payType === 'alipay'
					? 'bg-white dark:bg-gray-700 font-medium'
					: 'text-gray-500'}"
				on:click={() => (payType = 'alipay')}>支付宝</button
			>
			<button
				class="px-4 py-1 rounded-full {payType === 'wxpay'
					? 'bg-white dark:bg-gray-700 font-medium'
					: 'text-gray-500'}"
				on:click={() => (payType = 'wxpay')}>微信支付</button
			>
		</div>
	</div>

	{#if loading}
		<div class="text-center mt-10 text-gray-500">加载中…</div>
	{:else}
		<div class="grid md:grid-cols-3 gap-5 mt-8">
			{#each plans as plan (plan.code)}
				{@const price = period === 'yearly' ? plan.yearly_price_cents ?? null : plan.monthly_price_cents}
				<div
					class="border border-gray-200 dark:border-gray-700 rounded-xl p-6 flex flex-col bg-white dark:bg-gray-900"
				>
					<h2 class="text-xl font-semibold">{plan.name}</h2>
					<p class="text-sm text-gray-500 mt-1 min-h-10">{plan.description ?? ''}</p>
					<div class="mt-4">
						{#if price === null || price === undefined}
							<span class="text-2xl font-semibold text-gray-400">不支持</span>
						{:else if price === 0}
							<span class="text-3xl font-semibold">免费</span>
						{:else}
							<span class="text-3xl font-semibold">{cny(price)}</span>
							<span class="text-sm text-gray-500"
								>/ {period === 'yearly' ? '年' : '月'}</span
							>
						{/if}
					</div>
					<ul class="mt-5 space-y-2 text-sm flex-1">
						<li>
							消息：{plan.monthly_msg_limit < 0 ? '不限' : `${plan.monthly_msg_limit} / 月`}
						</li>
						<li>
							Token：{plan.monthly_token_limit < 0
								? '不限'
								: `${(plan.monthly_token_limit / 10000).toFixed(0)} 万 / 月`}
						</li>
						{#if plan.features_json}
							{#each Object.entries(plan.features_json) as [k, v] (k)}
								<li class="text-gray-600 dark:text-gray-400">{k}: {String(v)}</li>
							{/each}
						{/if}
					</ul>
					<button
						class="mt-6 w-full rounded-full py-2 text-sm font-medium bg-gray-900 text-white dark:bg-white dark:text-gray-900 disabled:opacity-40"
						disabled={creatingForPlan === plan.code || price === null || price === 0}
						on:click={() => upgrade(plan)}
					>
						{creatingForPlan === plan.code
							? '跳转中…'
							: price === 0
								? '当前档位'
								: price === null
									? '不支持'
									: '立即升级'}
					</button>
				</div>
			{/each}
		</div>
	{/if}
</div>
