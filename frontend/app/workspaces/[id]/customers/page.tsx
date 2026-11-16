'use client';
import { MotionButton } from '@/components/ui/motion-button';

import { FormEvent, useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { businessApi, Customer } from '../../../../lib/business-api';
import { addMoney, formatINR, toMinorUnits } from '../../../../lib/money';
import { useToast } from '@/components/ui';

const emptyForm = { name: '', phone: '', email: '', address: '', credit_limit: '', opening_balance: '0.00' };

export default function CustomersPage() {
  const { toast } = useToast();
  const params = useParams();
  const businessId = params.id as string;
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [editing, setEditing] = useState<Customer | null>(null);
  const [ledger, setLedger] = useState<any | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => setCustomers(await businessApi.listCustomers(businessId)), [businessId]);
  useEffect(() => { load().catch((error: Error) => toast.error(error.message)); }, [load, toast]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    try {
      if (editing) {
        const updated = await businessApi.updateCustomer(businessId, editing.id, {
          ...form,
          credit_limit_amount: form.credit_limit,
        });
        setCustomers((items) => items.map((item) => item.id === updated.id ? updated : item));
      } else {
        const created = await businessApi.createCustomer(businessId, {
          ...form,
          credit_limit: form.credit_limit || '0.00',
          opening_balance: form.opening_balance || '0.00',
        });
        setCustomers((items) => [created, ...items]);
      }
      setEditing(null);
      setForm(emptyForm);
      toast.success(editing ? 'Customer updated' : 'Customer created');
    } catch (error) {
      toast.error(`Customer save failed: ${(error as Error).message}`);
    } finally { setBusy(false); }
  };

  const edit = (customer: Customer) => {
    setEditing(customer);
    setForm({
      name: customer.name,
      phone: customer.phone ?? '',
      email: customer.email ?? '',
      address: customer.address ?? '',
      credit_limit: String(customer.credit_limit_amount ?? '0.00'),
      opening_balance: '0.00',
    });
  };

  const openLedger = async (customer: Customer) => {
    try { setLedger(await businessApi.getCustomerLedger(businessId, customer.id)); }
    catch (error) { toast.error(`Ledger load failed: ${(error as Error).message}`); }
  };

  const totalReceivable = customers.reduce((sum, customer) => addMoney(sum, String(customer.current_balance_amount ?? '0')), '0.00');

  return (
    <main className="mx-auto max-w-7xl space-y-6 p-5 md:p-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div><p className="text-xs font-semibold uppercase tracking-widest text-[#C8281E]">Khata · Parties</p><h1 className="mt-1 text-2xl font-bold text-[#231412]">Customers</h1><p className="mt-1 text-sm text-[#6E524D]">Credit limits, receivables and source ledger entries.</p></div>
        <div className="rounded-2xl border border-[#C8281E]/15 bg-white/95 px-4 py-3 shadow-sm"><div className="text-xs uppercase text-[#9A7E78]">Open receivables</div><div className="mt-1 font-bold tabular-nums text-[#231412]">{formatINR(totalReceivable)}</div></div>
      </header>

      <form onSubmit={submit} className="grid gap-3 rounded-2xl border border-[#C8281E]/15 bg-white/95 p-5 md:grid-cols-3 shadow-sm">
        <h2 className="md:col-span-3 text-sm font-bold text-[#231412]">{editing ? `Edit ${editing.name}` : 'Add customer'}</h2>
        <input required aria-label="Customer name" placeholder="Customer name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="rounded-xl border border-[#C8281E]/20 bg-[#FAF7F2] p-2.5 text-sm text-[#231412]" />
        <input aria-label="Phone" placeholder="Phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} className="rounded-xl border border-[#C8281E]/20 bg-[#FAF7F2] p-2.5 text-sm text-[#231412]" />
        <input aria-label="Email" placeholder="Email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="rounded-xl border border-[#C8281E]/20 bg-[#FAF7F2] p-2.5 text-sm text-[#231412]" />
        <input aria-label="Address" placeholder="Address" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} className="rounded-xl border border-[#C8281E]/20 bg-[#FAF7F2] p-2.5 text-sm text-[#231412] md:col-span-1" />
        <input aria-label="Credit limit" placeholder="Credit limit (₹)" inputMode="decimal" value={form.credit_limit} onChange={(e) => setForm({ ...form, credit_limit: e.target.value })} className="rounded-xl border border-[#C8281E]/20 bg-[#FAF7F2] p-2.5 text-sm text-[#231412]" />
        {!editing && <input aria-label="Opening balance" placeholder="Opening receivable (₹)" inputMode="decimal" value={form.opening_balance} onChange={(e) => setForm({ ...form, opening_balance: e.target.value })} className="rounded-xl border border-[#C8281E]/20 bg-[#FAF7F2] p-2.5 text-sm text-[#231412]" />}
        <div className="flex gap-2 md:col-span-3"><MotionButton disabled={busy} className="rounded-xl bg-[#C8281E] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50 hover:bg-[#A81E15] shadow-sm">{busy ? 'Saving…' : editing ? 'Save changes' : 'Create customer'}</MotionButton>{editing && <MotionButton type="button" onClick={() => { setEditing(null); setForm(emptyForm); }} className="rounded-xl border border-[#C8281E]/20 px-4 py-2 text-sm text-[#6E524D]">Cancel</MotionButton>}</div>
      </form>

      <section className="overflow-hidden rounded-2xl border border-[#C8281E]/15 bg-white/95 shadow-sm">
        <div className="border-b border-[#C8281E]/12 p-4 text-sm font-bold text-[#231412]">{customers.length} customers</div>
        <div className="divide-y divide-[#C8281E]/10">
          {customers.map((customer) => {
            const limit = toMinorUnits(String(customer.credit_limit_amount ?? '0'));
            const balance = toMinorUnits(String(customer.current_balance_amount ?? '0'));
            const utilization = limit > 0n ? Math.max(0, Math.min(100, Number((balance * 10000n) / limit) / 100)) : 0;
            return <article key={customer.id} className="grid gap-3 p-4 md:grid-cols-[1.5fr_1fr_1fr_auto] md:items-center">
              <div><div className="font-semibold text-[#231412]">{customer.name}</div><div className="text-xs text-[#6E524D]">{customer.phone || customer.email || 'No contact details'}</div></div>
              <div><div className="text-xs uppercase text-[#9A7E78]">Receivable</div><div className="font-semibold tabular-nums text-[#231412]">{formatINR(customer.current_balance_amount)}</div></div>
              <div><div className="flex justify-between text-xs text-[#6E524D]"><span>Credit use</span><span>{limit > 0n ? `${utilization.toFixed(1)}%` : 'No limit'}</span></div><div className="mt-1 h-1.5 overflow-hidden rounded-full bg-[#FAF7F2]"><div className="h-full bg-[#C8281E]" style={{ width: `${utilization}%` }} /></div><div className="mt-1 text-[11px] text-[#9A7E78]">Limit {formatINR(customer.credit_limit_amount)}</div></div>
              <div className="flex gap-2"><MotionButton onClick={() => openLedger(customer)} className="rounded-xl border border-[#C8281E]/20 px-3 py-1.5 text-xs font-semibold text-[#231412] hover:bg-[#C8281E]/10 hover:text-[#C8281E]">Ledger</MotionButton><MotionButton onClick={() => edit(customer)} className="rounded-xl border border-[#C8281E]/20 px-3 py-1.5 text-xs font-semibold text-[#231412] hover:bg-[#C8281E]/10 hover:text-[#C8281E]">Edit</MotionButton></div>
            </article>;
          })}
          {!customers.length && <div className="p-8 text-center text-sm text-[#6E524D]">No customers recorded in this workspace.</div>}
        </div>
      </section>

      {ledger && <div role="dialog" aria-modal="true" className="fixed inset-0 z-50 grid place-items-center bg-[#231412]/30 backdrop-blur-sm p-4"><section className="max-h-[85vh] w-full max-w-3xl overflow-auto rounded-3xl bg-white p-6 shadow-2xl border border-[#C8281E]/20"><div className="flex justify-between"><div><h2 className="font-bold text-[#231412]">{ledger.customer_name} ledger</h2><p className="text-sm text-[#6E524D]">Current balance {formatINR(ledger.current_balance)}</p></div><MotionButton onClick={() => setLedger(null)} className="rounded-xl border border-[#C8281E]/20 px-3 py-1 text-sm text-[#6E524D] hover:text-[#231412]">Close</MotionButton></div><div className="mt-4 divide-y divide-[#C8281E]/10">{(ledger.entries ?? []).map((entry: any, index: number) => <div key={`${entry.reference}-${index}`} className="grid grid-cols-[1fr_auto_auto] gap-3 py-2 text-sm text-[#231412]"><span>{entry.date} · {entry.type} · {entry.reference}</span><span className="tabular-nums">Dr {formatINR(entry.debit)}</span><span className="tabular-nums">Cr {formatINR(entry.credit)}</span></div>)}{!(ledger.entries ?? []).length && <p className="py-4 text-sm text-[#6E524D]">No ledger entries yet.</p>}</div></section></div>}
    </main>
  );
}
