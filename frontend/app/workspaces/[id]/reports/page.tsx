'use client';
import { MotionButton } from '@/components/ui/motion-button';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { businessApi, Customer, SalesInvoice, Supplier, downloadAuthenticatedReport } from '../../../../lib/business-api';
import { useToast } from '@/components/ui';

export default function ReportsPage() {
  const { toast } = useToast();
  const businessId = useParams().id as string;
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [invoices, setInvoices] = useState<SalesInvoice[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState('');
  const [selectedSupplier, setSelectedSupplier] = useState('');
  const [selectedInvoice, setSelectedInvoice] = useState('');
  useEffect(() => {
    Promise.all([businessApi.listCustomers(businessId), businessApi.listSuppliers(businessId), businessApi.listInvoices(businessId)])
      .then(([customersResult, suppliersResult, invoiceResult]) => { setCustomers(customersResult); setSuppliers(suppliersResult); setInvoices(invoiceResult); })
      .catch((error: Error) => toast.error(`Report choices could not be loaded: ${error.message}`));
  }, [businessId, toast]);

  const download = (path: string, filename: string) => downloadAuthenticatedReport(path, filename).catch((error: Error) => toast.error(`Download failed: ${error.message}`));
  return <main className="mx-auto max-w-5xl space-y-6 p-5 md:p-8"><header><p className="text-xs font-semibold uppercase tracking-widest text-[#10B981]">Reporting</p><h1 className="mt-1 text-2xl font-bold text-[#0D0F17]">Reports & exports</h1><p className="mt-1 text-sm text-slate-500">Downloads are fetched with the active authenticated session.</p></header>
    <section className="grid gap-4 md:grid-cols-2"><article className="rounded-none border bg-white p-5"><h2 className="font-bold text-[#0D0F17]">Executive dossier</h2><p className="mt-1 text-sm text-slate-500">Workspace financial and operational summary.</p><MotionButton onClick={() => download(businessApi.getDossierPdfUrl(businessId), 'arthlens-dossier.pdf')} className="mt-4 rounded-none bg-[#2B4EFF] px-4 py-2 text-sm font-semibold text-[#0D0F17]">Download PDF</MotionButton></article>
      <article className="rounded-none border bg-white p-5"><h2 className="font-bold text-[#0D0F17]">General ledger</h2><p className="mt-1 text-sm text-slate-500">Posted journal entries as CSV.</p><MotionButton onClick={() => download(businessApi.getGeneralLedgerCsvUrl(businessId), 'arthlens-general-ledger.csv')} className="mt-4 rounded-none border px-4 py-2 text-sm font-semibold">Download CSV</MotionButton></article>
      <article className="space-y-3 rounded-none border bg-white p-5"><h2 className="font-bold text-[#0D0F17]">Party ledger statement</h2><select value={selectedCustomer} onChange={(e) => { setSelectedCustomer(e.target.value); setSelectedSupplier(''); }} aria-label="Select party" className="w-full rounded-none border p-2 text-sm"><option value="">Select customer or supplier</option><optgroup label="Customers">{customers.map((item) => <option key={item.id} value={`customer:${item.id}`}>{item.name}</option>)}</optgroup><optgroup label="Suppliers">{suppliers.map((item) => <option key={item.id} value={`supplier:${item.id}`}>{item.name}</option>)}</optgroup></select><MotionButton disabled={!selectedCustomer} onClick={() => { const [type, id] = selectedCustomer.split(':'); const path = type === 'customer' ? businessApi.getCustomerLedgerCsvUrl(businessId, id) : businessApi.getSupplierLedgerCsvUrl(businessId, id); download(path, `${type}-ledger.csv`); }} className="rounded-none border px-4 py-2 text-sm font-semibold disabled:opacity-50">Download CSV</MotionButton></article>
      <article className="space-y-3 rounded-none border bg-white p-5"><h2 className="font-bold text-[#0D0F17]">Printable sales invoice</h2><select value={selectedInvoice} onChange={(e) => setSelectedInvoice(e.target.value)} aria-label="Select invoice" className="w-full rounded-none border p-2 text-sm"><option value="">Select invoice</option>{invoices.map((invoice) => <option key={invoice.id} value={invoice.id}>{invoice.invoice_number} · {invoice.invoice_date}</option>)}</select><MotionButton disabled={!selectedInvoice} onClick={() => download(`/businesses/${businessId}/invoices/${selectedInvoice}/pdf`, 'sales-invoice.pdf')} className="rounded-none border px-4 py-2 text-sm font-semibold disabled:opacity-50">Download PDF</MotionButton></article>
    </section>
  </main>;
}
