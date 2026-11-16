'use client';
import { MotionButton } from '@/components/ui/motion-button';

import { FormEvent, useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { businessApi, PurchaseRecord, Supplier } from '../../../../lib/business-api';
import { addMoney, formatINR } from '../../../../lib/money';
import { useToast } from '@/components/ui';

const emptyForm = { name: '', contact_person: '', phone: '', email: '', address: '', opening_balance: '0.00' };

export default function SuppliersPage() {
  const { toast } = useToast();
  const params = useParams();
  const businessId = params.id as string;
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [purchases, setPurchases] = useState<PurchaseRecord[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [editing, setEditing] = useState<Supplier | null>(null);
  const [ledger, setLedger] = useState<any | null>(null);
  const [selectedSupplier, setSelectedSupplier] = useState<Supplier | null>(null);
  const [returns, setReturns] = useState<Record<string, any[]>>({});

  const load = useCallback(async () => {
    const [supplierRows, purchaseRows] = await Promise.all([businessApi.listSuppliers(businessId), businessApi.listPurchases(businessId)]);
    setSuppliers(supplierRows);
    setPurchases(purchaseRows);
  }, [businessId]);
  useEffect(() => { load().catch((error: Error) => toast.error(error.message)); }, [load, toast]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    try {
      if (editing) {
        const updated = await businessApi.updateSupplier(businessId, editing.id, form);
        setSuppliers((items) => items.map((item) => item.id === updated.id ? updated : item));
      } else {
        const created = await businessApi.createSupplier(businessId, form);
        setSuppliers((items) => [created, ...items]);
      }
      setEditing(null);
      setForm(emptyForm);
      toast.success(editing ? 'Supplier updated' : 'Supplier created');
    } catch (error) { toast.error(`Supplier save failed: ${(error as Error).message}`); }
  };

  const openHistory = async (supplier: Supplier) => {
    setSelectedSupplier(supplier);
    try {
      const bills = purchases.filter((purchase) => purchase.supplier_id === supplier.id);
      const returnSets = await Promise.all(bills.map(async (purchase) => [purchase.id, await businessApi.listPurchaseReturns(businessId, purchase.id)] as const));
      setReturns(Object.fromEntries(returnSets));
    } catch (error) { toast.error(`Purchase history load failed: ${(error as Error).message}`); }
  };

  const totalPayables = suppliers.reduce((sum, supplier) => addMoney(sum, String(supplier.current_balance_amount ?? '0')), '0.00');

  return (
    <main className="mx-auto max-w-7xl space-y-6 p-5 md:p-8">
      <header className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-widest text-[#C8281E]">Khata · Procurement</p><h1 className="mt-1 text-2xl font-bold text-[#231412]">Suppliers</h1><p className="mt-1 text-sm text-[#6E524D]">Supplier balances, purchase bills and return history.</p></div><div className="rounded-2xl border border-[#C8281E]/15 bg-white/95 px-4 py-3 shadow-sm"><div className="text-xs uppercase text-[#9A7E78]">Open payables</div><div className="mt-1 font-bold tabular-nums text-[#231412]">{formatINR(totalPayables)}</div></div></header>

      <form onSubmit={submit} className="grid gap-3 rounded-2xl border border-[#C8281E]/15 bg-white/95 p-5 md:grid-cols-3 shadow-sm">
        <h2 className="md:col-span-3 text-sm font-bold text-[#231412]">{editing ? `Edit ${editing.name}` : 'Add supplier'}</h2>
        <input required aria-label="Supplier name" placeholder="Supplier name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="rounded-xl border border-[#C8281E]/20 bg-[#FAF7F2] p-2.5 text-sm text-[#231412]" />
        <input aria-label="Contact person" placeholder="Contact person" value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} className="rounded-xl border border-[#C8281E]/20 bg-[#FAF7F2] p-2.5 text-sm text-[#231412]" />
        <input aria-label="Phone" placeholder="Phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} className="rounded-xl border border-[#C8281E]/20 bg-[#FAF7F2] p-2.5 text-sm text-[#231412]" />
        <input aria-label="Email" type="email" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="rounded-xl border border-[#C8281E]/20 bg-[#FAF7F2] p-2.5 text-sm text-[#231412]" />
        <input aria-label="Address" placeholder="Address" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} className="rounded-xl border border-[#C8281E]/20 bg-[#FAF7F2] p-2.5 text-sm text-[#231412]" />
        {!editing && <input aria-label="Opening balance" inputMode="decimal" placeholder="Opening payable (₹)" value={form.opening_balance} onChange={(e) => setForm({ ...form, opening_balance: e.target.value })} className="rounded-xl border border-[#C8281E]/20 bg-[#FAF7F2] p-2.5 text-sm text-[#231412]" />}
        <div className="flex gap-2 md:col-span-3"><MotionButton className="rounded-xl bg-[#C8281E] px-4 py-2 text-sm font-semibold text-white hover:bg-[#A81E15] shadow-sm">{editing ? 'Save changes' : 'Create supplier'}</MotionButton>{editing && <MotionButton type="button" onClick={() => { setEditing(null); setForm(emptyForm); }} className="rounded-xl border border-[#C8281E]/20 px-4 py-2 text-sm text-[#6E524D]">Cancel</MotionButton>}</div>
      </form>

      <section className="overflow-hidden rounded-2xl border border-[#C8281E]/15 bg-white/95 shadow-sm"><div className="border-b border-[#C8281E]/12 p-4 text-sm font-bold text-[#231412]">{suppliers.length} suppliers</div><div className="divide-y divide-[#C8281E]/10">
        {suppliers.map((supplier) => <article key={supplier.id} className="grid gap-3 p-4 md:grid-cols-[1.5fr_1fr_auto] md:items-center"><div><div className="font-semibold text-[#231412]">{supplier.name}</div><div className="text-xs text-[#6E524D]">{supplier.contact_person || supplier.phone || 'No contact details'}</div></div><div><div className="text-xs uppercase text-[#9A7E78]">Payable balance</div><div className="font-semibold tabular-nums text-[#231412]">{formatINR(supplier.current_balance_amount)}</div></div><div className="flex gap-2"><MotionButton onClick={async () => { try { setLedger(await businessApi.getSupplierLedger(businessId, supplier.id)); } catch (error) { toast.error((error as Error).message); } }} className="rounded-xl border border-[#C8281E]/20 px-3 py-1.5 text-xs font-semibold text-[#231412] hover:bg-[#C8281E]/10 hover:text-[#C8281E]">Ledger</MotionButton><MotionButton onClick={() => openHistory(supplier)} className="rounded-xl border border-[#C8281E]/20 px-3 py-1.5 text-xs font-semibold text-[#231412] hover:bg-[#C8281E]/10 hover:text-[#C8281E]">Purchases & returns</MotionButton><MotionButton onClick={() => { setEditing(supplier); setForm({ name: supplier.name, contact_person: supplier.contact_person ?? '', phone: supplier.phone ?? '', email: supplier.email ?? '', address: supplier.address ?? '', opening_balance: '0.00' }); }} className="rounded-xl border border-[#C8281E]/20 px-3 py-1.5 text-xs font-semibold text-[#231412] hover:bg-[#C8281E]/10 hover:text-[#C8281E]">Edit</MotionButton></div></article>)}
        {!suppliers.length && <div className="p-8 text-center text-sm text-[#6E524D]">No suppliers recorded in this workspace.</div>}
      </div></section>

      {ledger && <div role="dialog" aria-modal="true" className="fixed inset-0 z-50 grid place-items-center bg-[#231412]/30 backdrop-blur-sm p-4"><section className="max-h-[85vh] w-full max-w-3xl overflow-auto rounded-3xl bg-white p-6 shadow-2xl border border-[#C8281E]/20"><div className="flex justify-between"><div><h2 className="font-bold text-[#231412]">{ledger.supplier_name} ledger · {formatINR(ledger.current_balance)}</h2></div><MotionButton onClick={() => setLedger(null)} className="rounded-xl border border-[#C8281E]/20 px-3 py-1 text-sm text-[#6E524D] hover:text-[#231412]">Close</MotionButton></div><div className="mt-4 divide-y divide-[#C8281E]/10">{(ledger.entries ?? []).map((entry: any, index: number) => <div key={`${entry.reference}-${index}`} className="grid grid-cols-[1fr_auto_auto] gap-3 py-2 text-sm text-[#231412]"><span>{entry.date} · {entry.type} · {entry.reference}</span><span className="tabular-nums">Dr {formatINR(entry.debit)}</span><span className="tabular-nums">Cr {formatINR(entry.credit)}</span></div>)}</div></section></div>}

      {selectedSupplier && <div role="dialog" aria-modal="true" className="fixed inset-0 z-50 grid place-items-center bg-[#231412]/30 backdrop-blur-sm p-4"><section className="max-h-[85vh] w-full max-w-4xl overflow-auto rounded-3xl bg-white p-6 shadow-2xl border border-[#C8281E]/20"><div className="flex items-center justify-between"><div><h2 className="font-bold text-[#231412]">{selectedSupplier.name} purchase history</h2><p className="text-xs text-[#6E524D]">Bills and posted purchase returns</p></div><MotionButton onClick={() => setSelectedSupplier(null)} className="rounded-xl border border-[#C8281E]/20 px-3 py-1 text-sm text-[#6E524D] hover:text-[#231412]">Close</MotionButton></div><div className="mt-4 space-y-3">{purchases.filter((purchase) => purchase.supplier_id === selectedSupplier.id).map((purchase) => <article key={purchase.id} className="rounded-2xl border border-[#C8281E]/15 bg-[#FAF7F2] p-4"><div className="flex flex-wrap justify-between gap-2 text-[#231412]"><span className="font-semibold">{purchase.purchase_order_number} · {purchase.purchase_date}</span><span className="tabular-nums font-bold">Bill {formatINR(purchase.total_amount)}</span></div><div className="mt-1 text-xs text-[#6E524D]">{purchase.status} · outstanding {formatINR(purchase.outstanding_amount)}</div>{(returns[purchase.id] ?? []).map((record) => <div key={record.purchase_return_id} className="mt-2 border-t border-[#C8281E]/12 pt-2 text-xs text-[#6E524D]">Return {record.return_date} · {formatINR(record.total_returned)} · {record.settlement_method}</div>)}</article>)}{!purchases.some((purchase) => purchase.supplier_id === selectedSupplier.id) && <p className="text-sm text-[#6E524D]">No purchase bills for this supplier.</p>}</div></section></div>}
    </main>
  );
}
