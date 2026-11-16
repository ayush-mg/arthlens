'use client';
import { MotionButton } from '@/components/ui/motion-button';

import { FormEvent, useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { businessApi } from '../../../../lib/business-api';
import { useToast } from '@/components/ui';

export default function MembersPage() {
  const { toast } = useToast();
  const businessId = useParams().id as string;
  const [members, setMembers] = useState<any[]>([]);
  const [userId, setUserId] = useState('');
  const [role, setRole] = useState('MANAGER');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => setMembers(await businessApi.listMembers(businessId)), [businessId]);
  useEffect(() => { load().catch((error: Error) => toast.error(error.message)); }, [load, toast]);

  const add = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true);
    try {
      await businessApi.addMember(businessId, { user_id: userId.trim(), role });
      setUserId(''); await load(); toast.success('Member added to workspace');
    } catch (error) { toast.error(`Member could not be added: ${(error as Error).message}`); }
    finally { setBusy(false); }
  };

  const remove = async (member: any) => {
    try { await businessApi.removeMember(businessId, member.user_id); await load(); toast.success('Member removed'); }
    catch (error) { toast.error(`Member could not be removed: ${(error as Error).message}`); }
  };

  const changeRole = async (member: any, nextRole: string) => {
    try {
      await businessApi.updateMemberRole(businessId, member.user_id, nextRole);
      await load();
      toast.success('Workspace role updated');
    } catch (error) { toast.error(`Role could not be updated: ${(error as Error).message}`); }
  };

  return <main className="mx-auto max-w-5xl space-y-6 p-5 md:p-8">
    <header><p className="text-xs font-semibold uppercase tracking-widest text-[#10B981]">Workspace access</p><h1 className="mt-1 text-2xl font-bold text-[#0D0F17]">Members & roles</h1><p className="mt-1 text-sm text-slate-500">Membership changes are recorded by the workspace service.</p></header>
    <form onSubmit={add} className="grid gap-3 rounded-none border border-black/[0.08]/10 bg-white p-4 md:grid-cols-[1fr_200px_auto]">
      <input required value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="User ID" aria-label="User ID" className="rounded-none border p-2 text-sm" />
      <select value={role} onChange={(e) => setRole(e.target.value)} aria-label="Workspace role" className="rounded-none border p-2 text-sm"><option>ADMIN</option><option>MANAGER</option><option>ACCOUNTANT</option><option>ANALYST</option><option>VIEWER</option></select>
      <MotionButton disabled={busy} className="rounded-none bg-[#2B4EFF] px-4 py-2 text-sm font-semibold text-[#0D0F17] disabled:opacity-50">{busy ? 'Adding…' : 'Add member'}</MotionButton>
    </form>
    <section className="overflow-hidden rounded-none border border-black/[0.08]/10 bg-white"><div className="border-b p-4 text-sm font-bold text-[#0D0F17]">{members.length} members</div><div className="divide-y divide-[#282623]/5">
      {members.map((member) => <article key={member.user_id} className="flex flex-wrap items-center justify-between gap-3 p-4"><div><div className="font-semibold text-[#0D0F17]">{member.name || member.email || member.user_id}</div><div className="text-xs text-slate-500">{member.user_id}{!member.is_active && ' · inactive'}</div></div><div className="flex items-center gap-3">{member.role === 'OWNER' ? <span className="rounded-none bg-[#10B981]/10 px-3 py-1 text-xs font-semibold text-[#10B981]">OWNER</span> : member.is_active ? <select aria-label={`Role for ${member.user_id}`} value={member.role} onChange={(event) => void changeRole(member, event.target.value)} className="rounded-none border px-2 py-1 text-xs"><option>ADMIN</option><option>MANAGER</option><option>ACCOUNTANT</option><option>ANALYST</option><option>VIEWER</option></select> : <span className="rounded-none bg-[#E9E8E2] px-3 py-1 text-xs">{member.role}</span>}{member.role !== 'OWNER' && member.is_active && <MotionButton onClick={() => remove(member)} className="rounded-none border px-3 py-1 text-xs">Remove</MotionButton>}</div></article>)}
      {!members.length && <div className="p-8 text-center text-sm text-slate-500">No members returned.</div>}
    </div></section>
    <p className="text-xs text-slate-500">Workspace owner role is protected. ADMIN can manage workspace operations; ANALYST has read access for review.</p>
  </main>;
}
