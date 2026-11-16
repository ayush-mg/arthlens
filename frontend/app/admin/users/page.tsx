'use client';
import { MotionButton } from '@/components/ui/motion-button';
import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
	Users, Shield, AlertTriangle, CheckCircle2,
	UserCheck, UserX, Search, RefreshCw, ArrowLeft,
} from 'lucide-react';
import {
	fetchAdminUsers,updateUserRole,deactivateUserAccount,activateUserAccount,
	getCurrentUser,UserProfile,AdminUserRecord,
} from '../../../lib/api';
import { ArthLensBrandMark } from '../../../components/motion/ArthLensBrandMark';
import { SpotlightCard } from '../../../components/motion/SpotlightCard';

export default function AdminUsersPage() {
	const [users,setUsers]=useState<AdminUserRecord[]>([]);
	const [currentUser,setCurrentUser]=useState<UserProfile|null>(null);
	const [loading,setLoading]=useState(true);
	const [error,setError]=useState<string|null>(null);
	const [searchTerm,setSearchTerm]=useState('');
	const [actionError,setActionError]=useState<string|null>(null);
	const [actionSuccess,setActionSuccess]=useState<string|null>(null);
	const [busyUserId,setBusyUserId]=useState<string|null>(null);

	const loadUsers=async()=>{
		setLoading(true);
		setError(null);
		try {
			const [userList,me]=await Promise.all([
				fetchAdminUsers(),
				getCurrentUser(),
			]);
			setUsers(userList);
			setCurrentUser(me);
		} catch (err:any) {
			setError(err.message||'Failed to load user registry.');
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		loadUsers();
	}, []);

	const handleRoleChange = async (userId: string, newRole: string) => {
		setActionError(null);
		setActionSuccess(null);
		setBusyUserId(userId);
		try {
			await updateUserRole(userId, newRole);
			setActionSuccess(`Role for ${userId.slice(0, 8)} updated to ${newRole}.`);
			await loadUsers();
		} catch (err: any) {
			setActionError(err.message || 'Failed to update user role.');
		} finally {
			setBusyUserId(null);
		}
	};

	const handleToggleActive=async(userId:string,currentStatus:boolean)=>{
		setActionError(null);
		setActionSuccess(null);
		setBusyUserId(userId);
		try {
			if (currentStatus) {
				await deactivateUserAccount(userId);
			} else {
				await activateUserAccount(userId);
			}
			setActionSuccess(`Account ${userId.slice(0,8)} ${!currentStatus?'activated':'deactivated'}.`);
			await loadUsers();
		} catch (err:any) {
			setActionError(err.message||'Failed to toggle account status.');
		} finally {
			setBusyUserId(null);
		}
	};

	const filteredUsers = users.filter((u) => {
		const q = searchTerm.toLowerCase();
		const fullName = u.quota_counters?.full_name?.toLowerCase() || '';
		const email = u.email.toLowerCase();
		const roles = u.roles.join(' ').toLowerCase();
		return email.includes(q) || fullName.includes(q) || roles.includes(q);
	});

	return (
		<div className="admin-users-shell min-h-screen bg-[#FAF7F2] text-[#231412] flex flex-col py-8 px-4 sm:px-6 lg:px-8">
			<div className="max-w-6xl mx-auto w-full space-y-6">
				<div className="flex items-center justify-between border-b border-[#C8281E]/15 pb-4">
					<div className="flex items-center space-x-3">
						<Link href="/" className="flex items-center space-x-2.5">
							<ArthLensBrandMark compact />
						</Link>
						<span className="text-[#C8281E]">/</span>
						<span className="font-mono text-xs uppercase tracking-wider text-[#231412] font-bold">
							User Directory & Role Governance
						</span>
					</div>

					<Link
						href="/workspaces"
						className="inline-flex items-center space-x-1.5 rounded-xl border border-[#C8281E]/20 bg-white px-3.5 py-1.5 font-mono text-xs font-bold text-[#231412] hover:bg-[#C8281E]/10 hover:text-[#C8281E] shadow-sm transition-all"
					>
						<ArrowLeft className="h-3.5 w-3.5" />
						<span>Return to Workspaces</span>
					</Link>
				</div>

				<SpotlightCard className="rounded-2xl border border-[#C8281E]/18 bg-white/95 overflow-hidden shadow-xl">
					<div className="flex items-center justify-between border-b border-[#C8281E]/15 px-6 py-4 bg-[#FAF7F2]">
						<div className="flex items-center space-x-3">
							<div className="flex h-9 w-9 items-center justify-center rounded-xl border border-[#C8281E]/30 bg-[#C8281E]/10 text-[#C8281E]">
								<Users className="h-5 w-5" />
							</div>
							<div>
								<h1 className="text-lg font-bold text-[#231412]">
									Registered Accounts Directory
								</h1>
								<p className="font-mono text-xs text-[#6E524D]">
									Manage roles, enforce administrative boundaries, and govern active session lifecycles
								</p>
							</div>
						</div>
						<MotionButton
							type="button"
							onClick={loadUsers}
							className="p-2 rounded-xl border border-[#C8281E]/20 hover:bg-[#C8281E]/10 text-[#6E524D] hover:text-[#C8281E] cursor-pointer transition-colors"
							title="Refresh directory"
						>
							<RefreshCw className={'h-4 w-4 ' + (loading ? 'animate-spin' : '')} />
						</MotionButton>
					</div>

					{actionError && (
						<div className="border-b border-rose-200 bg-rose-50 px-6 py-2.5 text-xs text-rose-700 flex items-center space-x-2">
							<AlertTriangle className="h-4 w-4 shrink-0" />
							<span>{actionError}</span>
						</div>
					)}
					{actionSuccess && (
						<div className="border-b border-[#2D7D52]/20 bg-[#2D7D52]/10 px-6 py-2.5 text-xs text-[#2D7D52] flex items-center space-x-2">
							<CheckCircle2 className="h-4 w-4 shrink-0" />
							<span>{actionSuccess}</span>
						</div>
					)}

					<div className="p-4 border-b border-[#C8281E]/12 bg-white flex items-center space-x-3">
						<div className="relative flex-1">
							<Search className="absolute left-3 top-2.5 h-4 w-4 text-[#9A7E78]" />
							<input
								type="text"
								value={searchTerm}
								onChange={(e) => setSearchTerm(e.target.value)}
								placeholder="Filter by email, name, or role..."
								className="w-full pl-9 pr-4 py-2 font-mono text-xs rounded-xl border border-[#C8281E]/20 bg-[#FAF7F2] text-[#231412] placeholder-[#9A7E78] focus:border-[#C8281E] focus:outline-none"
							/>
						</div>
						<span className="font-mono text-xs text-[#6E524D]">
							Showing {filteredUsers.length} of {users.length} accounts
						</span>
					</div>

					<div className="overflow-x-auto p-6">
						<table className="w-full text-left font-mono text-xs border-collapse">
							<thead>
								<tr className="border-b border-[#C8281E]/15 text-[#6E524D] font-bold uppercase tracking-wider text-[11px]">
									<th className="pb-3 pl-2">User Details</th>
									<th className="pb-3">Assigned Role</th>
									<th className="pb-3">Account Status</th>
									<th className="pb-3 text-right pr-2">Actions</th>
								</tr>
							</thead>
							<tbody className="divide-y divide-[#C8281E]/10">
								{filteredUsers.map((u) => {
									const isActive = u.quota_counters?.is_active !== false;
									const primaryRole = u.roles[0] || 'ENTREPRENEUR';
									const isCurrent = currentUser && u.id === currentUser.id;
									const isBusy = busyUserId === u.id;

									return (
										<tr key={u.id} className="hover:bg-[#C8281E]/[0.03] transition-colors">
											<td className="py-3.5 pl-2">
												<div className="font-bold text-[#231412] flex items-center space-x-2">
													<span>{u.quota_counters?.full_name || 'Standard User'}</span>
													{isCurrent && (
														<span className="rounded bg-[#2D7D52]/10 px-1.5 py-0.5 text-[9px] text-[#2D7D52] border border-[#2D7D52]/20 font-bold">
															You
														</span>
													)}
												</div>
												<div className="text-[#6E524D] text-[11px]">{u.email}</div>
												<div className="text-[10px] text-[#9A7E78] font-mono">
													ID: {u.id.slice(0, 8)}... · Joined: {u.created_at ? new Date(u.created_at).toLocaleDateString() : 'N/A'}
												</div>
											</td>

											<td className="py-3.5">
												<select
													value={primaryRole}
													disabled={isBusy}
													onChange={(e) => handleRoleChange(u.id, e.target.value)}
													className="rounded-xl border border-[#C8281E]/20 bg-white px-2.5 py-1 text-xs font-bold text-[#231412] focus:border-[#C8281E] focus:outline-none cursor-pointer"
												>
													<option value="ENTREPRENEUR">ENTREPRENEUR</option>
													<option value="STEWARD">STEWARD</option>
													<option value="ADMIN">ADMIN</option>
												</select>
											</td>

											<td className="py-3.5">
												<span
													className={`inline-flex items-center space-x-1.5 rounded-full px-2.5 py-0.5 text-[10px] font-bold ${
														isActive
															? 'bg-[#2D7D52]/10 text-[#2D7D52] border border-[#2D7D52]/30'
															: 'bg-[#C8281E]/10 text-[#C8281E] border border-[#C8281E]/30'
													}`}
												>
													<span className={`h-1.5 w-1.5 rounded-full ${isActive ? 'bg-[#2D7D52]' : 'bg-[#C8281E]'}`} />
													<span>{isActive ? 'ACTIVE' : 'DEACTIVATED'}</span>
												</span>
											</td>

											<td className="py-3.5 text-right pr-2">
												<MotionButton
													type="button"
													disabled={isBusy}
													onClick={() => handleToggleActive(u.id, isActive)}
													className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded-xl font-mono text-[11px] font-bold border transition-colors cursor-pointer disabled:opacity-50 ${
														isActive
															? 'border-[#C8281E]/40 text-[#C8281E] hover:bg-[#C8281E]/10'
															: 'border-[#2D7D52]/40 text-[#2D7D52] hover:bg-[#2D7D52]/10'
													}`}
												>
													{isActive ? (
														<>
															<UserX className="h-3.5 w-3.5" />
															<span>Deactivate</span>
														</>
													) : (
														<>
															<UserCheck className="h-3.5 w-3.5" />
															<span>Activate</span>
														</>
													)}
												</MotionButton>
											</td>
										</tr>
									);
								})}
							</tbody>
						</table>
					</div>

					<div className="border-t border-[#C8281E]/15 px-6 py-3 bg-[#FAF7F2] flex items-center justify-between font-mono text-xs text-[#6E524D]">
						<div className="flex items-center space-x-1.5">
							<Shield className="h-4 w-4 text-[#D4A359]" />
							<span>Anti-lockout invariant: The last active administrator cannot be demoted or deactivated.</span>
						</div>
					</div>
				</SpotlightCard>
			</div>
		</div>
	);
}