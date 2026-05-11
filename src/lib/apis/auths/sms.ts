import { WEBUI_API_BASE_URL } from '$lib/constants';

const SMS_BASE = `${WEBUI_API_BASE_URL}/auths/sms`;

async function jsonOrThrow(res: Response) {
	if (!res.ok) {
		const err = await res.json().catch(() => ({}));
		throw err?.detail ?? `Request failed: ${res.status}`;
	}
	return res.json();
}

export interface CaptchaResponse {
	token: string;
	image: string;
	expires_in: number;
}

export async function fetchCaptcha(): Promise<CaptchaResponse> {
	const res = await fetch(`${SMS_BASE}/captcha`, { method: 'GET' });
	return jsonOrThrow(res);
}

export async function sendSmsCode(payload: {
	phone: string;
	scene?: 'signin' | 'bind';
	captcha_token: string;
	captcha_answer: string;
}): Promise<{ success: boolean; expires_in: number }> {
	const res = await fetch(`${SMS_BASE}/send`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ scene: 'signin', ...payload })
	});
	return jsonOrThrow(res);
}

export async function smsSignin(phone: string, code: string) {
	const res = await fetch(`${SMS_BASE}/signin`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ phone, code })
	});
	return jsonOrThrow(res);
}

export async function smsBind(token: string, phone: string, code: string) {
	const res = await fetch(`${SMS_BASE}/bind`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ phone, code })
	});
	return jsonOrThrow(res);
}
