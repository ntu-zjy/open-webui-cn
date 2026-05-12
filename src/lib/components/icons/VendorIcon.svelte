<script lang="ts">
	export let model: any = {};
	export let className: string = 'size-5';

	const VENDOR_RULES: { vendor: string; patterns: RegExp[] }[] = [
		{ vendor: 'openai', patterns: [/\bgpt-?/i, /\bo[134](?:-|\b)/i, /openai/i, /chatgpt/i] },
		{ vendor: 'anthropic', patterns: [/claude/i, /anthropic/i] },
		{ vendor: 'google', patterns: [/gemini/i, /palm/i, /bison/i, /^google/i] },
		{ vendor: 'deepseek', patterns: [/deepseek/i] },
		{ vendor: 'moonshot', patterns: [/kimi/i, /moonshot/i] },
		{ vendor: 'zhipu', patterns: [/glm/i, /chatglm/i, /zhipu/i] },
		{ vendor: 'meta', patterns: [/llama/i, /^meta-/i] },
		{ vendor: 'qwen', patterns: [/qwen/i, /tongyi/i, /通义/i] }
	];

	$: haystack = `${model?.id ?? ''} ${model?.name ?? ''}`.toLowerCase();
	$: vendor = VENDOR_RULES.find(({ patterns }) => patterns.some((p) => p.test(haystack)))?.vendor ?? 'openrouter';
</script>

<img
	src="/static/vendors/{vendor}.svg"
	alt={vendor}
	class={className}
	loading="lazy"
	on:error={(e) => {
		const img = e.currentTarget as HTMLImageElement;
		if (!img.dataset.fallback) {
			img.dataset.fallback = '1';
			img.src = '/static/favicon.png';
		}
	}}
/>
