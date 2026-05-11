<script lang="ts">
	import { getContext, onMount, createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { fetchCaptcha, sendSmsCode, smsSignin } from '$lib/apis/auths/sms';

	const i18n = getContext('i18n') as any;
	const dispatch = createEventDispatcher();

	let phone = '';
	let code = '';
	let captchaAnswer = '';
	let captchaToken = '';
	let captchaImage = '';
	let captchaLoading = false;

	let sending = false;
	let submitting = false;
	let countdown = 0;
	let countdownTimer: ReturnType<typeof setInterval> | null = null;

	const isValidPhone = (v: string) => /^1[3-9]\d{9}$/.test(v.trim());

	async function refreshCaptcha() {
		captchaLoading = true;
		try {
			const r = await fetchCaptcha();
			captchaToken = r.token;
			captchaImage = r.image;
			captchaAnswer = '';
		} catch (e: any) {
			toast.error(typeof e === 'string' ? e : '获取验证码失败');
		} finally {
			captchaLoading = false;
		}
	}

	async function sendCode() {
		if (!isValidPhone(phone)) {
			toast.error('请输入正确的手机号');
			return;
		}
		if (!captchaToken || !captchaAnswer) {
			toast.error('请输入图形验证码');
			return;
		}
		sending = true;
		try {
			await sendSmsCode({
				phone: phone.trim(),
				captcha_token: captchaToken,
				captcha_answer: captchaAnswer
			});
			toast.success('验证码已发送');
			countdown = 60;
			countdownTimer = setInterval(() => {
				countdown -= 1;
				if (countdown <= 0 && countdownTimer) {
					clearInterval(countdownTimer);
					countdownTimer = null;
				}
			}, 1000);
		} catch (e: any) {
			toast.error(typeof e === 'string' ? e : '发送失败');
			refreshCaptcha();
		} finally {
			sending = false;
		}
	}

	async function submit() {
		if (!isValidPhone(phone)) {
			toast.error('请输入正确的手机号');
			return;
		}
		if (!/^\d{6}$/.test(code)) {
			toast.error('请输入 6 位短信验证码');
			return;
		}
		submitting = true;
		try {
			const session = await smsSignin(phone.trim(), code);
			dispatch('success', session);
		} catch (e: any) {
			toast.error(typeof e === 'string' ? e : '登录失败');
		} finally {
			submitting = false;
		}
	}

	onMount(() => {
		refreshCaptcha();
		return () => {
			if (countdownTimer) clearInterval(countdownTimer);
		};
	});
</script>

<form
	class="flex flex-col gap-3"
	on:submit={(e) => {
		e.preventDefault();
		submit();
	}}
>
	<div>
		<label for="phone" class="text-sm font-medium text-left mb-1 block">手机号</label>
		<input
			id="phone"
			bind:value={phone}
			type="tel"
			inputmode="numeric"
			autocomplete="tel"
			maxlength="11"
			placeholder="请输入大陆 11 位手机号"
			class="my-0.5 w-full text-sm outline-hidden bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-600"
			required
		/>
	</div>

	<div>
		<label for="captcha" class="text-sm font-medium text-left mb-1 block">图形验证码</label>
		<div class="flex gap-2 items-center">
			<input
				id="captcha"
				bind:value={captchaAnswer}
				type="text"
				autocomplete="off"
				maxlength="6"
				placeholder="请输入图片中字符"
				class="flex-1 my-0.5 text-sm outline-hidden bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-600"
				required
			/>
			<button
				type="button"
				class="shrink-0 rounded bg-gray-50 dark:bg-gray-800 px-1 py-0.5"
				on:click={refreshCaptcha}
				disabled={captchaLoading}
				title="点击刷新"
			>
				{#if captchaImage}
					<img src={captchaImage} alt="captcha" class="h-10 w-32 object-contain" />
				{:else}
					<div class="h-10 w-32 flex items-center justify-center text-xs text-gray-400">
						加载中…
					</div>
				{/if}
			</button>
		</div>
	</div>

	<div>
		<label for="code" class="text-sm font-medium text-left mb-1 block">短信验证码</label>
		<div class="flex gap-2 items-center">
			<input
				id="code"
				bind:value={code}
				type="text"
				inputmode="numeric"
				autocomplete="one-time-code"
				maxlength="6"
				placeholder="6 位验证码"
				class="flex-1 my-0.5 text-sm outline-hidden bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-600"
				required
			/>
			<button
				type="button"
				class="shrink-0 text-sm rounded-full px-4 py-2 bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 disabled:opacity-50"
				on:click={sendCode}
				disabled={sending || countdown > 0 || !isValidPhone(phone)}
			>
				{#if countdown > 0}
					{countdown}s
				{:else if sending}
					发送中
				{:else}
					获取验证码
				{/if}
			</button>
		</div>
	</div>

	<button
		type="submit"
		class="mt-2 bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5"
		disabled={submitting}
	>
		{submitting ? '登录中…' : '登录 / 注册'}
	</button>

	<p class="mt-1 text-xs text-gray-500 text-center">
		未注册的手机号将自动创建新账号
	</p>
</form>
