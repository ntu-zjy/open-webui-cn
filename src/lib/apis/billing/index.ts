import { WEBUI_API_BASE_URL } from '$lib/constants';

const BASE = `${WEBUI_API_BASE_URL}/billing`;
const PAY = `${WEBUI_API_BASE_URL}/payments`;

async function jsonOrThrow(res: Response) {
	if (!res.ok) {
		const err = await res.json().catch(() => ({}));
		throw err?.detail ?? `Request failed: ${res.status}`;
	}
	return res.json();
}

function authHeaders(token: string) {
	return { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` };
}

export interface Plan {
	code: string;
	name: string;
	description?: string | null;
	monthly_price_cents: number;
	yearly_price_cents?: number | null;
	monthly_msg_limit: number;
	monthly_token_limit: number;
	allowed_model_pattern?: string | null;
	features_json?: Record<string, unknown> | null;
	display_order: number;
	active: boolean;
}

export interface Subscription {
	id: string;
	user_id: string;
	plan_code: string;
	status: string;
	started_at: number;
	expires_at: number;
	auto_renew: boolean;
}

export interface UsageSummary {
	prompt_tokens: number;
	completion_tokens: number;
	total_tokens: number;
	messages: number;
	cost_cents: number;
	window_start: number;
}

export interface Order {
	id: string;
	user_id: string;
	plan_code: string;
	period: 'monthly' | 'yearly';
	amount_cents: number;
	status: 'pending' | 'paid' | 'expired' | 'refunded';
	provider_pay_type?: string | null;
	paid_at?: number | null;
	expires_at: number;
	created_at: number;
}

export async function listPlans(): Promise<Plan[]> {
	const res = await fetch(`${BASE}/plans`, { method: 'GET' });
	return jsonOrThrow(res);
}

export async function getMyBilling(
	token: string
): Promise<{ plan: Plan | null; subscription: Subscription | null; usage: UsageSummary }> {
	const res = await fetch(`${BASE}/me`, { method: 'GET', headers: authHeaders(token) });
	return jsonOrThrow(res);
}

export async function createOrder(
	token: string,
	payload: { plan_code: string; period: 'monthly' | 'yearly'; pay_type: 'alipay' | 'wxpay' }
): Promise<{ order: Order; pay_url: string }> {
	const res = await fetch(`${PAY}/create`, {
		method: 'POST',
		headers: authHeaders(token),
		body: JSON.stringify(payload)
	});
	return jsonOrThrow(res);
}

export async function getOrder(token: string, orderId: string): Promise<Order> {
	const res = await fetch(`${PAY}/orders/${orderId}`, { method: 'GET', headers: authHeaders(token) });
	return jsonOrThrow(res);
}

export async function listMyOrders(token: string): Promise<Order[]> {
	const res = await fetch(`${PAY}/orders`, { method: 'GET', headers: authHeaders(token) });
	return jsonOrThrow(res);
}
