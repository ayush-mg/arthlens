'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Compass,
  ArrowLeft,
  Users,
  Shield,
  UserCheck,
  UserX,
  RefreshCw,
  Search,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import {
  AdminUserRecord,
  activateUserAccount,
  deactivateUserAccount,
  fetchAdminUsers,
  getCurrentUser,
  updateUserRole,
  UserProfile,
} from '../../../lib/api';

export default function AdminUsersPage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [users, setUsers] = useState<AdminUserRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [busyUserId, setBusyUserId] = useState<string | null>(null);

  useEffect(() => {
    async function init() {
      try {
        const user = await getCurrentUser();
        setCurrentUser(user);
        if (!user || !user.roles.includes('ADMIN')) {
          router.push('/login');
          return;
        }
        await loadUsers();
      } catch (err) {
        router.push('/login');
      } finally {
        setLoading(false);
      }
    }
    init();
  }, [router]);

  const loadUsers = async () => {
    setActionError(null);
    try {
      const data = await fetchAdminUsers();
      setUsers(data);
    } catch (err: any) {
      setActionError(err.message || 'Failed to load user directory.');
    }
  };

  const handleRoleChange = async (userId: string, newRole: string) => {
    setBusyUserId(userId);
    setActionError(null);
    setActionSuccess(null);
    try {
      await updateUserRole(userId, newRole);
      setActionSuccess(`Updated role for user to ${newRole}`);
      await loadUsers();
    } catch (err: any) {
      setActionError(err.message || 'Failed to update user role.');
    } finally {
      setBusyUserId(null);
    }
  };

  const handleToggleActive = async (userId: string, currentlyActive: boolean) => {
    setBusyUserId(userId);
    setActionError(null);
    setActionSuccess(null);
    try {
      if (currentlyActive) {
        await deactivateUserAccount(userId);
        setActionSuccess('User account deactivated and active sessions revoked.');
      } else {
        await activateUserAccount(userId);
        setActionSuccess('User account reactivated.');
      }
      await loadUsers();
    } catch (err: any) {
      setActionError(err.message || 'Failed to change account status.');
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
    <div className="min-h-screen bg-editorial-ivory flex flex-col py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto w-full space-y-6">
        {/* Top Bar */}
        <div className="flex items-center justify-between border-b border-editorial-brass/30 pb-4">
          <div className="flex items-center space-x-3">
            <Link href="/" className="flex items-center space-x-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded border border-editorial-forest bg-editorial-forest/10 text-editorial-forest">
                <Compass className="h-4 w-4" />
              </div>
              <span className="font-serif font-black tracking-widest text-editorial-forest text-xl uppercase">
                ArthLens
              </span>
            </Link>
            <span className="text-editorial-brass">/</span>
            <span className="font-mono text-xs uppercase tracking-wider text-editorial-charcoal font-bold">
              User Directory & Role Governance
            </span>
          </div>

          <Link
            href="/app"
            className="inline-flex items-center space-x-1.5 rounded border border-editorial-brass/40 bg-editorial-paper px-3 py-1.5 font-mono text-xs font-bold text-editorial-charcoal hover:bg-editorial-ivory"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Return to Workspace</span>
          </Link>
        </div>

        {/* Content Box */}
        <div className="rounded-lg border border-editorial-brass/40 bg-editorial-paper shadow-editorial-md overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-editorial-brass/30 px-6 py-4 bg-editorial-ivory">
            <div className="flex items-center space-x-3">
              <div className="flex h-9 w-9 items-center justify-center rounded border border-editorial-forest bg-editorial-forest/10 text-editorial-forest">
                <Users className="h-5 w-5" />
              </div>
              <div>
                <h1 className="font-serif text-lg font-bold text-editorial-charcoal">
                  Registered Accounts Directory
                </h1>
                <p className="font-mono text-xs text-editorial-charcoal-light">
                  Manage roles, enforce administrative boundaries, and govern active session lifecycles
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={loadUsers}
              className="p-2 rounded border border-editorial-brass/30 hover:bg-editorial-paper text-editorial-charcoal cursor-pointer"
              title="Refresh directory"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>

          {/* Action Banners */}
          {actionError && (
            <div className="border-b border-editorial-copper/40 bg-editorial-copper/10 px-6 py-2.5 text-xs font-mono text-editorial-copper flex items-center space-x-2">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{actionError}</span>
            </div>
          )}
          {actionSuccess && (
            <div className="border-b border-editorial-forest/40 bg-editorial-forest/10 px-6 py-2.5 text-xs font-mono text-editorial-forest flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              <span>{actionSuccess}</span>
            </div>
          )}

          {/* Search */}
          <div className="p-4 border-b border-editorial-brass/20 bg-editorial-ivory/50 flex items-center space-x-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-editorial-charcoal-light" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Filter by email, name, or role..."
                className="w-full pl-9 pr-4 py-2 font-mono text-xs rounded border border-editorial-brass/40 bg-editorial-paper text-editorial-charcoal placeholder-editorial-charcoal-light/60 focus:border-editorial-copper focus:outline-none"
              />
            </div>
            <span className="font-mono text-xs text-editorial-charcoal-light">
              Showing {filteredUsers.length} of {users.length} accounts
            </span>
          </div>

          {/* Table */}
          <div className="overflow-x-auto p-6">
            <table className="w-full text-left font-mono text-xs border-collapse">
              <thead>
                <tr className="border-b border-editorial-brass/40 text-editorial-charcoal-light font-bold uppercase tracking-wider text-[11px]">
                  <th className="pb-3 pl-2">User Details</th>
                  <th className="pb-3">Assigned Role</th>
                  <th className="pb-3">Account Status</th>
                  <th className="pb-3 text-right pr-2">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-editorial-brass/10">
                {filteredUsers.map((u) => {
                  const isActive = u.quota_counters?.is_active !== false;
                  const primaryRole = u.roles[0] || 'ENTREPRENEUR';
                  const isCurrent = currentUser && u.id === currentUser.id;
                  const isBusy = busyUserId === u.id;

                  return (
                    <tr key={u.id} className="hover:bg-editorial-ivory/60 transition-colors">
                      <td className="py-3.5 pl-2">
                        <div className="font-bold text-editorial-charcoal flex items-center space-x-2">
                          <span>{u.quota_counters?.full_name || 'Standard User'}</span>
                          {isCurrent && (
                            <span className="rounded bg-editorial-forest/10 px-1.5 py-0.5 text-[9px] text-editorial-forest border border-editorial-forest/20 font-bold">
                              You
                            </span>
                          )}
                        </div>
                        <div className="text-editorial-charcoal-light text-[11px]">{u.email}</div>
                        <div className="text-[10px] text-editorial-charcoal-light/60 font-mono">
                          ID: {u.id.slice(0, 8)}... · Joined: {u.created_at ? new Date(u.created_at).toLocaleDateString() : 'N/A'}
                        </div>
                      </td>

                      <td className="py-3.5">
                        <select
                          value={primaryRole}
                          disabled={isBusy}
                          onChange={(e) => handleRoleChange(u.id, e.target.value)}
                          className="rounded border border-editorial-brass/40 bg-editorial-ivory px-2.5 py-1 text-xs font-bold text-editorial-charcoal focus:border-editorial-copper focus:outline-none cursor-pointer"
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
                              ? 'bg-editorial-forest/10 text-editorial-forest border border-editorial-forest/30'
                              : 'bg-editorial-copper/10 text-editorial-copper border border-editorial-copper/30'
                          }`}
                        >
                          <span className={`h-1.5 w-1.5 rounded-full ${isActive ? 'bg-editorial-forest' : 'bg-editorial-copper'}`} />
                          <span>{isActive ? 'ACTIVE' : 'DEACTIVATED'}</span>
                        </span>
                      </td>

                      <td className="py-3.5 text-right pr-2">
                        <button
                          type="button"
                          disabled={isBusy}
                          onClick={() => handleToggleActive(u.id, isActive)}
                          className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded font-mono text-[11px] font-bold border transition-colors cursor-pointer disabled:opacity-50 ${
                            isActive
                              ? 'border-editorial-copper/50 text-editorial-copper hover:bg-editorial-copper/10'
                              : 'border-editorial-forest/50 text-editorial-forest hover:bg-editorial-forest/10'
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
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="border-t border-editorial-brass/30 px-6 py-3 bg-editorial-ivory flex items-center justify-between font-mono text-xs text-editorial-charcoal-light">
            <div className="flex items-center space-x-1.5">
              <Shield className="h-4 w-4 text-editorial-brass" />
              <span>Anti-lockout invariant: The last active administrator cannot be demoted or deactivated.</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

