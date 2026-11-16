'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import {
	ShieldCheck, KeyRound, LogIn, LogOut, RefreshCw,
	AlertCircle, CheckCircle2, User, Clock, Filter,
	Search, Code, ChevronDown, ChevronRight, Shield,
} from 'lucide-react';
import { businessApi } from '../../../../lib/business-api';
import { useToast } from '@/components/ui';

interface EventMeta {
	label: string;
	category: 'auth' | 'transaction' | 'system' | 'security';
	badgeClass: string;
	icon: React.ComponentType<{ className?: string }>;
}

function getEventMeta(action: string): EventMeta {
	switch (action) {
		case 'AUTH_LOGIN_SUCCESS':
			return {
				label: 'Successful Sign-In',
				category: 'auth',
				badgeClass: 'bg-[#2D7D52]/10 text-[#2D7D52] border-[#2D7D52]/30',
				icon: LogIn,
			};
		case 'AUTH_SESSION_REFRESHED':
			return {
				label: 'Session Active / Renewed',
				category: 'auth',
				badgeClass: 'bg-blue-50 text-blue-700 border-blue-200',
				icon: RefreshCw,
			};
		case 'AUTH_PASSWORD_RESET_REQUEST':
			return {
				label: 'Password Recovery Code Requested',
				category: 'security',
				badgeClass: 'bg-amber-50 text-amber-800 border-amber-300',
				icon: KeyRound,
			};
		case 'AUTH_PASSWORD_RESET_SUCCESS':
			return {
				label: 'Password Successfully Changed',
				category: 'security',
				badgeClass: 'bg-[#2D7D52]/10 text-[#2D7D52] border-[#2D7D52]/30',
				icon: CheckCircle2,
			};
		case 'AUTH_LOGIN_FAILURE':
			return {
				label: 'Failed Sign-In Attempt',
				category: 'security',
				badgeClass: 'bg-rose-50 text-rose-700 border-rose-300',
				icon: AlertCircle,
			};
		case 'AUTH_LOGOUT':
			return {
				label: 'User Signed Out',
				category: 'auth',
				badgeClass: 'bg-stone-100 text-stone-700 border-stone-300',
				icon: LogOut,
			};
		case 'AUTH_GOOGLE_SUCCESS':
		case 'AUTH_GOOGLE_SESSION':
			return {
				label: 'Google SSO Authentication',
				category: 'auth',
				badgeClass: 'bg-indigo-50 text-indigo-700 border-indigo-200',
				icon: User,
			};
		case 'AUTH_REGISTER_OTP_INITIATED':
			return {
				label: 'Registration Code Dispatched',
				category: 'auth',
				badgeClass: 'bg-amber-50 text-amber-700 border-amber-200',
				icon: KeyRound,
			};
		case 'AUTH_REGISTER_VERIFIED':
			return {
				label: 'New Account Verified & Activated',
				category: 'auth',
				badgeClass: 'bg-[#2D7D52]/10 text-[#2D7D52] border-[#2D7D52]/30',
				icon: CheckCircle2,
			};
		case 'AUTH_SEED_DEMO_ACCOUNT':
			return {
				label: 'Demo Account Initialized',
				category: 'system',
				badgeClass: 'bg-purple-50 text-purple-700 border-purple-200',
				icon: ShieldCheck,
			};
		case 'SALES_INVOICE_CREATED':
			return {
				label: 'Sales Invoice Issued',
				category: 'transaction',
				badgeClass: 'bg-[#2D7D52]/10 text-[#2D7D52] border-[#2D7D52]/30',
				icon: CheckCircle2,
			};
		case 'PURCHASE_BILL_RECORDED':
			return {
				label: 'Purchase Bill Logged',
				category: 'transaction',
				badgeClass: 'bg-purple-50 text-purple-700 border-purple-200',
				icon: CheckCircle2,
			};
		case 'PURCHASE_RETURN_POSTED':
			return {
				label: 'Purchase Return Posted',
				category: 'transaction',
				badgeClass: 'bg-amber-50 text-amber-700 border-amber-200',
				icon: RefreshCw,
			};
		case 'INVENTORY_COST_RECONCILIATION_COMPLETED':
			return {
				label: 'Inventory Cost Basis Reconciled',
				category: 'transaction',
				badgeClass: 'bg-[#2D7D52]/10 text-[#2D7D52] border-[#2D7D52]/30',
				icon: CheckCircle2,
			};
		case 'BUSINESS_MEMBER_ACTIVATED':
			return {
				label: 'Team Member Access Granted',
				category: 'auth',
				badgeClass: 'bg-[#2D7D52]/10 text-[#2D7D52] border-[#2D7D52]/30',
				icon: User,
			};
		case 'BUSINESS_MEMBER_ROLE_UPDATED':
			return {
				label: 'Team Member Role Updated',
				category: 'auth',
				badgeClass: 'bg-blue-50 text-blue-700 border-blue-200',
				icon: ShieldCheck,
			};
		default:
			return {
				label: action.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase()),
				category: 'system',
				badgeClass: 'bg-stone-100 text-[#231412] border-[#231412]/20',
				icon: Clock,
			};
	}
}

const HIDDEN_INTERNAL_PAYLOAD_KEYS = new Set(['access_jti', 'refresh_jti', 'prior_refresh_jti']);

function formatActorOrTarget(
	raw: string | null | undefined,
	currentUserId: string | null,
	currentUserEmail: string | null
): string {
	if (!raw) return 'System Engine';
	const clean = raw.startsWith('user:') ? raw.slice(5) : raw.startsWith('business:') ? raw.slice(9) : raw;
	if (currentUserId && clean === currentUserId) {
		return currentUserEmail ? `You (${currentUserEmail})` : 'You (Active Session)';
	}
	if (raw.startsWith('user:')) {
		return `User Account (${clean.slice(0, 8)}…)`;
	}
	if (raw.startsWith('business:')) {
		return `Workspace (${clean.slice(0, 8)}…)`;
	}
	if (raw.length === 36 && raw.includes('-')) {
		return `User (${raw.slice(0, 8)}…)`;
	}
	return raw;
}

function formatPayloadValue(key: string, val: any): string {
	if (key.toLowerCase().includes('exp') && typeof val === 'string' && val.includes('T')) {
		try {
			return new Date(val).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
		} catch {
			return val;
		}
	}
	if (typeof val === 'object' && val !== null) {
		return Array.isArray(val) ? val.join(', ') : JSON.stringify(val);
	}
	return String(val);
}

export default function AuditPage() {
	const { toast } = useToast();
	const businessId = useParams().id as string;
	const [events, setEvents] = useState<any[]>([]);
	const [filter, setFilter] = useState('');
	const [expandedRawRow, setExpandedRawRow] = useState<Record<string, boolean>>({});
	const [showTechnicalTokens, setShowTechnicalTokens] = useState(false);
	const [currentUserEmail, setCurrentUserEmail] = useState<string | null>(null);
	const [currentUserId, setCurrentUserId] = useState<string | null>(null);

	useEffect(() => {
		try {
			const token = window.localStorage.getItem('arthlens_token') || window.localStorage.getItem('token');
			if (token) {
				const parts = token.split('.');
				if (parts.length >= 2) {
					const payload = JSON.parse(atob(parts[1]));
					if (payload.sub) setCurrentUserId(payload.sub);
					if (payload.email) setCurrentUserEmail(payload.email);
				}
			}
		} catch {}
	}, []);

	useEffect(() => {
		businessApi.listActivity(businessId)
			.then(setEvents)
			.catch((error: Error) => toast.error(error.message));
	}, [businessId, toast]);

	const visible = events.filter((event) => {
		const meta = getEventMeta(event.action ?? '');
		const text = `${event.action ?? ''} ${meta.label} ${event.actor ?? ''} ${event.target ?? ''}`.toLowerCase();
		return text.includes(filter.toLowerCase());
	});

	const toggleRawRow = (rowKey: string) => {
		setExpandedRawRow((prev) => ({
			...prev,
			[rowKey]: !prev[rowKey],
		}));
	};

	return (
		<main className="mx-auto max-w-6xl space-y-6 p-5 md:p-8">
			{/* Page Header */}
			<header className="flex flex-wrap items-center justify-between gap-4 pb-2 border-b border-[#C8281E]/15">
				<div>
					<div className="flex items-center space-x-2">
						<Shield className="w-5 h-5 text-[#C8281E]" />
						<p className="text-xs font-mono font-bold uppercase tracking-widest text-[#C8281E]">Sovereign Governance</p>
					</div>
					<h1 className="mt-1 text-2xl font-bold text-[#231412]">Audit & Access Activity Trail</h1>
					<p className="mt-1 text-xs text-[#6E524D]">
						Immutable, cryptographically chained records of all security, authentication, and ledger activities across this workspace.
					</p>
				</div>
				<div className="flex items-center space-x-3">
					<button
						type="button"
						onClick={() => setShowTechnicalTokens(!showTechnicalTokens)}
						className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border border-[#231412]/20 bg-[#FAF7F2] hover:bg-white text-xs font-mono font-bold text-[#231412] shadow-xs transition-colors"
					>
						<Code className="w-3.5 h-3.5 text-[#6E524D]" />
						<span>{showTechnicalTokens ? 'Hide Developer Hashes' : 'Show Developer Hashes'}</span>
					</button>
				</div>
			</header>

			{/* Filter Search Input */}
			<div className="relative">
				<Search className="w-4 h-4 text-[#6E524D] absolute left-3.5 top-3.5 pointer-events-none" />
				<input
					value={filter}
					onChange={(e) => setFilter(e.target.value)}
					placeholder="Filter by event type, user, email, or action (e.g. Sign-In, Password Reset, Invoice)..."
					aria-label="Filter audit activity"
					className="w-full pl-10 pr-4 py-2.5 rounded-xl border-2 border-[#231412]/20 bg-white text-xs font-mono text-[#231412] focus:border-[#C8281E] focus:outline-none transition-colors shadow-xs"
				/>
			</div>

			{/* Events Table Container */}
			<section className="overflow-hidden rounded-2xl border border-[#C8281E]/18 bg-white/95 shadow-sm">
				<div className="flex items-center justify-between px-5 py-3.5 bg-[#FAF7F2] border-b border-[#C8281E]/12">
					<div className="flex items-center space-x-2 text-xs font-bold text-[#231412]">
						<Clock className="w-4 h-4 text-[#C8281E]" />
						<span>{visible.length} Recorded Activity Event{visible.length === 1 ? '' : 's'}</span>
					</div>
					<span className="text-[11px] font-mono text-[#6E524D]">Chronological Audit Log</span>
				</div>

				<div className="divide-y divide-[#231412]/10">
					{visible.map((event, index) => {
						const meta = getEventMeta(event.action ?? '');
						const IconComponent = meta.icon;
						const rowKey = event.id ?? `${event.timestamp}-${index}`;
						const isRawOpen = expandedRawRow[rowKey];

						const rawPayloadEntries = Object.entries(event.payload || {});
						const displayPayloadEntries = rawPayloadEntries.filter(
							([k]) => showTechnicalTokens || !HIDDEN_INTERNAL_PAYLOAD_KEYS.has(k)
						);

						return (
							<article key={rowKey} className="p-4.5 hover:bg-[#FAF7F2]/60 transition-colors space-y-2.5">
								<div className="grid gap-3 md:grid-cols-[180px_1fr_1.4fr] items-start">
									{/* Timestamp */}
									<div className="text-xs font-mono text-[#6E524D] pt-0.5">
										{event.timestamp ? (
											<div>
												<span className="font-bold text-[#231412]">
													{new Date(event.timestamp).toLocaleDateString([], {
														year: 'numeric',
														month: 'short',
														day: 'numeric',
													})}
												</span>
												<div className="text-[11px] text-[#9A7E78]">
													{new Date(event.timestamp).toLocaleTimeString([], {
														hour: '2-digit',
														minute: '2-digit',
														second: '2-digit',
													})}
												</div>
											</div>
										) : (
											'Timestamp Unavailable'
										)}
									</div>

									{/* Event Badge & Human Label */}
									<div className="space-y-1">
										<div className="flex items-center space-x-2 flex-wrap gap-y-1">
											<span
												className={`inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-lg border text-xs font-bold ${meta.badgeClass}`}
											>
												<IconComponent className="w-3.5 h-3.5" />
												<span>{meta.label}</span>
											</span>
										</div>
										<div className="text-xs font-mono text-[#6E524D] flex items-center space-x-1">
											<span>Actor:</span>
											<strong className="text-[#231412]">
												{formatActorOrTarget(event.actor, currentUserId, currentUserEmail)}
											</strong>
										</div>
									</div>

									{/* Target & Formatted Payload Badges */}
									<div className="space-y-1.5">
										<div className="text-xs font-mono text-[#231412] flex items-center space-x-1.5">
											<span className="text-[#6E524D]">Target:</span>
											<span className="font-bold">
												{formatActorOrTarget(event.target, currentUserId, currentUserEmail)}
											</span>
										</div>

										{/* Business Context Badges */}
										{displayPayloadEntries.length > 0 && (
											<div className="flex flex-wrap gap-1.5 pt-0.5">
												{displayPayloadEntries.map(([k, v]) => (
													<span
														key={k}
														className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-[#FAF7F2] border border-[#231412]/15 text-[10px] font-mono"
													>
														<span className="text-[#6E524D] uppercase font-bold">{k.replace(/_/g, ' ')}:</span>
														<span className="text-[#231412] font-semibold">
															{formatPayloadValue(k, v)}
														</span>
													</span>
												))}
											</div>
										)}

										{/* Toggle Raw JSON Inspector */}
										<div className="pt-1">
											<button
												type="button"
												onClick={() => toggleRawRow(rowKey)}
												className="inline-flex items-center space-x-1 text-[11px] font-mono text-[#9A7E78] hover:text-[#C8281E] transition-colors"
											>
												{isRawOpen ? (
													<>
														<ChevronDown className="w-3 h-3" />
														<span>Hide Raw Diagnostic Record</span>
													</>
												) : (
													<>
														<ChevronRight className="w-3 h-3" />
														<span>View Raw Diagnostic Record</span>
													</>
												)}
											</button>
										</div>
									</div>
								</div>

								{/* Collapsible Raw Diagnostic Inspector */}
								{isRawOpen && (
									<div className="mt-2 p-3 rounded-xl bg-[#231412] text-[#FAF7F2] font-mono text-[11px] space-y-1 overflow-x-auto shadow-inner">
										<div className="text-[10px] text-[#D4A359] uppercase font-bold tracking-wider">
											Raw Forensic Audit Payload ({event.action})
										</div>
										<pre className="text-white/90 whitespace-pre-wrap break-all">
											{JSON.stringify(
												{
													id: event.id,
													action: event.action,
													actor: event.actor,
													target: event.target,
													payload: event.payload,
													timestamp: event.timestamp,
													prev_hash: event.prev_hash,
												},
												null,
												2
											)}
										</pre>
									</div>
								)}
							</article>
						);
					})}

					{visible.length === 0 && (
						<div className="p-12 text-center text-xs font-mono text-[#6E524D] space-y-2">
							<Shield className="w-8 h-8 text-[#9A7E78] mx-auto opacity-40" />
							<p>No matching audit records found for current filter.</p>
						</div>
					)}
				</div>
			</section>
		</main>
	);
}
