'use client';
import { MotionButton } from '@/components/ui/motion-button';
import { useToast } from '@/components/ui';


import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import {
  BookOpen,
  UserPlus,
  Truck,
  ArrowDownLeft,
  ArrowUpRight,
  FileSpreadsheet,
  PlusCircle,
  CheckCircle,
  Edit2,
} from 'lucide-react';
import {
  businessApi,
  Customer,
  Supplier,
  downloadAuthenticatedReport,
} from '../../../../lib/business-api';
import { formatINR } from '../../../../lib/money';

export default function KhataPartiesPage() {
  const { toast } = useToast();
  const params = useParams();
  const businessId = params.id as string;

  const [activeTab, setActiveTab] = useState<'CUSTOMERS' | 'SUPPLIERS'>('CUSTOMERS');
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);

  // Add Customer Modal
  const [showAddCustomer, setShowAddCustomer] = useState(false);
  const [custName, setCustName] = useState('');
  const [custPhone, setCustPhone] = useState('');
  const [custCreditLimit, setCustCreditLimit] = useState('');
  const [custCreditDays, setCustCreditDays] = useState('30');

  // Add Supplier Modal
  const [showAddSupplier, setShowAddSupplier] = useState(false);
  const [suppName, setSuppName] = useState('');
  const [suppPhone, setSuppPhone] = useState('');
  const [suppTermsDays, setSuppTermsDays] = useState('15');

  // Record Payment Modal
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [selectedParty, setSelectedParty] = useState<{ id: string; name: string; type: 'CUSTOMER' | 'SUPPLIER' } | null>(null);
  const [paymentAmount, setPaymentAmount] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('BANK_TRANSFER');

  // Edit Customer Modal
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null);
  const [editCustName, setEditCustName] = useState('');
  const [editCustPhone, setEditCustPhone] = useState('');
  const [editCustCreditLimit, setEditCustCreditLimit] = useState('');

  // Edit Supplier Modal
  const [editingSupplier, setEditingSupplier] = useState<Supplier | null>(null);
  const [editSuppName, setEditSuppName] = useState('');
  const [editSuppPhone, setEditSuppPhone] = useState('');
  const [editSuppContact, setEditSuppContact] = useState('');
  const [reconciliation, setReconciliation] = useState<any>(null);
  const [reconciling, setReconciling] = useState(false);

  const reconcilePartyBalances = async () => {
    setReconciling(true);
    try {
      const result = await businessApi.reconcileKhata(businessId, new Date().toISOString().slice(0, 10));
      setReconciliation(result);
      toast.success(result.is_reconciled ? 'Party ledgers reconcile to the general ledger' : 'Ledger variance found for review');
    } catch (error) { toast.error(`Ledger reconciliation failed: ${(error as Error).message}`); }
    finally { setReconciling(false); }
  };

  useEffect(() => {
    async function loadParties() {
      try {
        const [cList, sList] = await Promise.all([
          businessApi.listCustomers(businessId).catch(() => []),
          businessApi.listSuppliers(businessId).catch(() => []),
        ]);
        setCustomers(cList);
        setSuppliers(sList);
      } catch (err) {
        console.error('Failed to load Khata parties', err);
      } finally {
        setLoading(false);
      }
    }
    loadParties();
  }, [businessId]);

  const handleCreateCustomer = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const created = await businessApi.createCustomer(businessId, {
        name: custName,
        phone: custPhone,
        credit_limit_amount: custCreditLimit,
        credit_period_days: parseInt(custCreditDays, 10),
      });
      setCustomers([...customers, created]);
      setShowAddCustomer(false);
      setCustName('');
      setCustPhone('');
    } catch (err: any) {
      toast.error(`Failed to add customer: ${err.message}`);
    }
  };

  const handleCreateSupplier = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const created = await businessApi.createSupplier(businessId, {
        name: suppName,
        phone: suppPhone,
        payment_terms_days: parseInt(suppTermsDays, 10),
      });
      setSuppliers([...suppliers, created]);
      setShowAddSupplier(false);
      setSuppName('');
      setSuppPhone('');
    } catch (err: any) {
      toast.error(`Failed to add supplier: ${err.message}`);
    }
  };

  const handleRecordPayment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedParty) return;
    try {
      if (selectedParty.type === 'CUSTOMER') {
        // Record direct income from customer
        await businessApi.recordIncome(businessId, {
          source: `Customer Payment - ${selectedParty.name}`,
          category: 'SALES_COLLECTION',
          amount: paymentAmount,
          payment_method: paymentMethod,
          date: new Date().toISOString().split('T')[0],
        });
      } else {
        // Record direct expense to supplier
        await businessApi.recordExpense(businessId, {
          category: 'VENDOR_PAYMENT',
          payee: selectedParty.name,
          amount: paymentAmount,
          payment_method: paymentMethod,
          date: new Date().toISOString().split('T')[0],
          description: `Settlement to ${selectedParty.name}`,
        });
      }
      setShowPaymentModal(false);
      setPaymentAmount('');
      // Reload parties
      const [cList, sList] = await Promise.all([
        businessApi.listCustomers(businessId).catch(() => []),
        businessApi.listSuppliers(businessId).catch(() => []),
      ]);
      setCustomers(cList);
      setSuppliers(sList);
    } catch (err: any) {
      toast.error(`Payment record failed: ${err.message}`);
    }
  };

  const handleUpdateCustomer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingCustomer) return;
    try {
      const updated = await businessApi.updateCustomer(businessId, editingCustomer.id, {
        name: editCustName,
        phone: editCustPhone,
        credit_limit_amount: editCustCreditLimit || '0.00',
      });
      setCustomers((prev) => prev.map((c) => (c.id === editingCustomer.id ? { ...c, ...updated } : c)));
      setEditingCustomer(null);
      toast.success('Customer details updated');
    } catch (err: any) {
      toast.error(`Update failed: ${err.message}`);
    }
  };

  const handleUpdateSupplier = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingSupplier) return;
    try {
      const updated = await businessApi.updateSupplier(businessId, editingSupplier.id, {
        name: editSuppName,
        contact_person: editSuppContact,
        phone: editSuppPhone,
      });
      setSuppliers((prev) => prev.map((s) => (s.id === editingSupplier.id ? { ...s, ...updated } : s)));
      setEditingSupplier(null);
      toast.success('Supplier details updated');
    } catch (err: any) {
      toast.error(`Update failed: ${err.message}`);
    }
  };

  const formatCurrency = (val: number | string | undefined | null) => {
    if (val === undefined || val === null) return '₹0.00';
    return formatINR(val);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-2 border-b border-black/[0.08]/10">
        <div>
          <h1 className="text-2xl font-bold text-[#0D0F17]">Khata & Parties</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Credit limits, receivables, payables, and automated double-entry ledger audits.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <MotionButton type="button" onClick={() => void reconcilePartyBalances()} disabled={reconciling} className="px-3.5 py-2 rounded-none border border-black/[0.08]/15 bg-white text-[#0D0F17] text-xs font-semibold disabled:opacity-50">
            {reconciling ? 'Reconciling…' : 'Reconcile ledgers'}
          </MotionButton>
          {activeTab === 'CUSTOMERS' ? (
            <MotionButton
              onClick={() => setShowAddCustomer(true)}
              className="px-3.5 py-2 rounded-none bg-[#2B4EFF] text-[#0D0F17] text-xs font-semibold hover:bg-[#E9E8E2] transition-all shadow-sm flex items-center space-x-1.5"
            >
              <UserPlus className="w-4 h-4 text-[#F59E0B]" />
              <span>Add Customer</span>
            </MotionButton>
          ) : (
            <MotionButton
              onClick={() => setShowAddSupplier(true)}
              className="px-3.5 py-2 rounded-none bg-[#2B4EFF] text-[#0D0F17] text-xs font-semibold hover:bg-[#E9E8E2] transition-all shadow-sm flex items-center space-x-1.5"
            >
              <Truck className="w-4 h-4 text-[#F59E0B]" />
              <span>Add Supplier</span>
            </MotionButton>
          )}
        </div>
      </div>

      {reconciliation && <section className={`grid gap-3 rounded-none border p-4 md:grid-cols-3 ${reconciliation.is_reconciled ? 'border-[#10B981]/40 bg-[#10B981]/10' : 'border-[#F59E0B]/40 bg-[#F59E0B]/10'}`}>
        <div className="md:col-span-3"><h2 className="text-sm font-bold text-[#0D0F17]">Subledger reconciliation · {reconciliation.as_of_date}</h2><p className="text-xs text-slate-500">Status: {reconciliation.status}. The checker reports differences and does not post automatic adjustments.</p></div>
        {(['accounts_receivable', 'accounts_payable'] as const).map((key) => <div key={key} className="rounded-none bg-white p-3 text-xs"><div className="font-semibold text-[#0D0F17]">{key === 'accounts_receivable' ? 'Accounts receivable' : 'Accounts payable'}</div><div className="mt-1 text-slate-500">Subledger {formatINR(reconciliation[key].subledger_exact)} · GL {formatINR(reconciliation[key].general_ledger_exact)}</div><div className="mt-1 font-mono">Variance {formatINR(reconciliation[key].variance_exact)}</div></div>)}
      </section>}

      {/* Tabs */}
      <div className="flex items-center space-x-2 border-b border-black/[0.08]/10 pb-1">
        <MotionButton
          onClick={() => setActiveTab('CUSTOMERS')}
          className={`px-4 py-2 text-xs font-bold rounded-none transition-all flex items-center space-x-2 ${
            activeTab === 'CUSTOMERS'
              ? 'bg-[#2B4EFF] text-[#0D0F17]'
              : 'text-slate-500 hover:bg-white'
          }`}
        >
          <ArrowDownLeft className="w-4 h-4" />
          <span>Customers & Receivables ({customers.length})</span>
        </MotionButton>
        <MotionButton
          onClick={() => setActiveTab('SUPPLIERS')}
          className={`px-4 py-2 text-xs font-bold rounded-none transition-all flex items-center space-x-2 ${
            activeTab === 'SUPPLIERS'
              ? 'bg-[#2B4EFF] text-[#0D0F17]'
              : 'text-slate-500 hover:bg-white'
          }`}
        >
          <ArrowUpRight className="w-4 h-4" />
          <span>Suppliers & Payables ({suppliers.length})</span>
        </MotionButton>
      </div>

      {/* Content Table */}
      <div className="p-6 rounded-none bg-white border border-black/[0.08]/10 shadow-sm">
        {activeTab === 'CUSTOMERS' ? (
          customers.length === 0 ? (
            <div className="text-center py-12 text-sm text-slate-500">
              No customer khata accounts found. Add customers to monitor credit limits and dues.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-black/[0.08]/10 text-slate-500 uppercase">
                    <th className="py-3 px-4">Customer Name</th>
                    <th className="py-3 px-4">Phone</th>
                    <th className="py-3 px-4 text-right">Credit Limit</th>
                    <th className="py-3 px-4 text-center">Credit Period</th>
                    <th className="py-3 px-4 text-right">Outstanding Balance</th>
                    <th className="py-3 px-4 text-center">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#282623]/5">
                  {customers.map((c) => (
                    <tr key={c.id} className="hover:bg-white">
                      <td className="py-3 px-4 font-bold text-[#0D0F17]">{c.name}</td>
                      <td className="py-3 px-4 text-slate-500">{c.phone || '—'}</td>
                      <td className="py-3 px-4 text-right font-medium">{formatCurrency(c.credit_limit_amount)}</td>
                      <td className="py-3 px-4 text-center">{c.credit_period_days} Days</td>
                      <td className="py-3 px-4 text-right font-bold text-[#10B981]">
                        {formatCurrency(c.current_balance_amount)}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <div className="flex items-center justify-center space-x-2">
                          <MotionButton
                            onClick={() => {
                              setSelectedParty({ id: c.id, name: c.name, type: 'CUSTOMER' });
                              setShowPaymentModal(true);
                            }}
                            className="px-2.5 py-1 rounded-none bg-[#2B4EFF] text-[#0D0F17] text-[11px] font-semibold hover:bg-[#E9E8E2]"
                          >
                            Collect
                          </MotionButton>
                          <MotionButton
                            onClick={() => {
                              setEditingCustomer(c);
                              setEditCustName(c.name);
                              setEditCustPhone(c.phone || '');
                              setEditCustCreditLimit(c.credit_limit_amount?.toString() || '0');
                            }}
                            className="p-1 rounded-none text-slate-500 hover:text-[#0D0F17] hover:bg-[#E9E8E2]"
                            title="Edit Customer"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </MotionButton>
                          <MotionButton
                            type="button"
                            onClick={() => downloadAuthenticatedReport(
                              businessApi.getCustomerLedgerCsvUrl(businessId, c.id),
                              `customer-ledger-${c.id}.csv`,
                            ).catch((err: Error) => toast.error(`Ledger download failed: ${err.message}`))}
                            className="p-1 rounded-none text-slate-500 hover:text-[#0D0F17] hover:bg-[#E9E8E2]"
                            title="Download CSV Ledger"
                          >
                            <FileSpreadsheet className="w-4 h-4" />
                          </MotionButton>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        ) : (
          suppliers.length === 0 ? (
            <div className="text-center py-12 text-sm text-slate-500">
              No supplier khata accounts found. Add suppliers to manage payables and purchase credits.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-black/[0.08]/10 text-slate-500 uppercase">
                    <th className="py-3 px-4">Supplier Name</th>
                    <th className="py-3 px-4">Phone</th>
                    <th className="py-3 px-4 text-center">Terms (Days)</th>
                    <th className="py-3 px-4 text-right">Outstanding Payable</th>
                    <th className="py-3 px-4 text-center">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#282623]/5">
                  {suppliers.map((s) => (
                    <tr key={s.id} className="hover:bg-white">
                      <td className="py-3 px-4 font-bold text-[#0D0F17]">{s.name}</td>
                      <td className="py-3 px-4 text-slate-500">{s.phone || '—'}</td>
                      <td className="py-3 px-4 text-center">{s.payment_terms_days} Days</td>
                      <td className="py-3 px-4 text-right font-bold text-[#B76E4D]">
                        {formatCurrency(s.current_balance_amount)}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <div className="flex items-center justify-center space-x-2">
                          <MotionButton
                            onClick={() => {
                              setSelectedParty({ id: s.id, name: s.name, type: 'SUPPLIER' });
                              setShowPaymentModal(true);
                            }}
                            className="px-2.5 py-1 rounded-none bg-[#B76E4D] text-[#0D0F17] text-[11px] font-semibold hover:bg-[#9B5B3E]"
                          >
                            Pay
                          </MotionButton>
                          <MotionButton
                            onClick={() => {
                              setEditingSupplier(s);
                              setEditSuppName(s.name);
                              setEditSuppPhone(s.phone || '');
                              setEditSuppContact(s.contact_person || '');
                            }}
                            className="p-1 rounded-none text-slate-500 hover:text-[#0D0F17] hover:bg-[#E9E8E2]"
                            title="Edit Supplier"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </MotionButton>
                          <MotionButton
                            type="button"
                            onClick={() => downloadAuthenticatedReport(
                              businessApi.getSupplierLedgerCsvUrl(businessId, s.id),
                              `supplier-ledger-${s.id}.csv`,
                            ).catch((err: Error) => toast.error(`Ledger download failed: ${err.message}`))}
                            className="p-1 rounded-none text-slate-500 hover:text-[#0D0F17] hover:bg-[#E9E8E2]"
                            title="Download CSV Ledger"
                          >
                            <FileSpreadsheet className="w-4 h-4" />
                          </MotionButton>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}
      </div>

      {/* Add Customer Modal */}
      {showAddCustomer && (
        <div className="fixed inset-0 z-50 bg-[#231412]/30 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl shadow-2xl border border-[#C8281E]/20 max-w-md w-full p-6 animate-in zoom-in-95">
            <h3 className="text-base font-bold text-[#231412] mb-1">Add Customer Khata</h3>
            <p className="text-xs text-slate-500 mb-4">Register client for invoicing and credit management.</p>
            <form onSubmit={handleCreateCustomer} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1">Customer / Entity Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Royal Sweets & Bakers"
                  value={custName}
                  onChange={(e) => setCustName(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-none border border-black/[0.08]/15 focus:outline-none focus:border-[#2B4EFF]"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1">Phone Number</label>
                <input
                  type="text"
                  placeholder="+91 98765 43210"
                  value={custPhone}
                  onChange={(e) => setCustPhone(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-none border border-black/[0.08]/15 focus:outline-none focus:border-[#2B4EFF]"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-500 mb-1">Credit Limit (₹)</label>
                  <input
                    type="number"
                    value={custCreditLimit}
                    onChange={(e) => setCustCreditLimit(e.target.value)}
                    className="w-full text-xs px-3 py-2 rounded-none border border-black/[0.08]/15 focus:outline-none focus:border-[#2B4EFF]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-500 mb-1">Credit Days</label>
                  <input
                    type="number"
                    value={custCreditDays}
                    onChange={(e) => setCustCreditDays(e.target.value)}
                    className="w-full text-xs px-3 py-2 rounded-none border border-black/[0.08]/15 focus:outline-none focus:border-[#2B4EFF]"
                  />
                </div>
              </div>
              <div className="flex items-center justify-end space-x-2 pt-3 border-t border-black/[0.08]/10">
                <MotionButton
                  type="button"
                  onClick={() => setShowAddCustomer(false)}
                  className="px-3.5 py-1.5 text-xs text-slate-500"
                >
                  Cancel
                </MotionButton>
                <MotionButton
                  type="submit"
                  className="px-4 py-2 rounded-none bg-[#2B4EFF] text-[#0D0F17] text-xs font-bold hover:bg-[#E9E8E2]"
                >
                  Add Customer
                </MotionButton>
              </div>
            </form>
          </div>
        </div>
      )}

			{showAddSupplier&&(
				<div className="fixed inset-0 z-50 bg-[#231412]/30 backdrop-blur-sm flex items-center justify-center p-4">
					<div className="bg-white rounded-3xl shadow-2xl border border-[#C8281E]/20 max-w-md w-full p-6 animate-in zoom-in-95">
						<h3 className="text-base font-bold text-[#231412] mb-1">Add Supplier / Vendor</h3>
						<p className="text-xs text-[#231412]/60 mb-4">Register supplier for procurement and payables.</p>
						<form onSubmit={handleCreateSupplier} className="space-y-3">
							<div>
								<label className="block text-xs font-semibold text-[#231412]/70 mb-1">Supplier Company Name</label>
								<input
									type="text"
									required
									placeholder="e.g. Apex Flour Mills Ltd"
									value={suppName}
									onChange={(e)=>setSuppName(e.target.value)}
									className="w-full text-xs px-3 py-2 rounded-xl border border-[#C8281E]/20 focus:outline-none focus:border-[#C8281E]"
								/>
							</div>
							<div>
								<label className="block text-xs font-semibold text-[#231412]/70 mb-1">Phone</label>
								<input
									type="text"
									placeholder="+91 91234 56789"
									value={suppPhone}
									onChange={(e)=>setSuppPhone(e.target.value)}
									className="w-full text-xs px-3 py-2 rounded-xl border border-[#C8281E]/20 focus:outline-none focus:border-[#C8281E]"
								/>
							</div>
							<div>
								<label className="block text-xs font-semibold text-[#231412]/70 mb-1">Payment Terms (Days)</label>
								<input
									type="number"
									value={suppTermsDays}
									onChange={(e)=>setSuppTermsDays(e.target.value)}
									className="w-full text-xs px-3 py-2 rounded-xl border border-[#C8281E]/20 focus:outline-none focus:border-[#C8281E]"
								/>
							</div>
							<div className="flex items-center justify-end space-x-2 pt-3 border-t border-[#C8281E]/10">
								<MotionButton
									type="button"
									onClick={()=>setShowAddSupplier(false)}
									className="px-3.5 py-1.5 text-xs text-[#231412]/70 hover:text-[#231412]"
								>
									Cancel
								</MotionButton>
								<MotionButton
									type="submit"
									className="px-4 py-2 rounded-xl bg-[#C8281E] text-white text-xs font-bold hover:bg-[#A82018]"
								>
									Add Supplier
								</MotionButton>
							</div>
						</form>
					</div>
				</div>
			)}

			{showPaymentModal&&selectedParty&&(
				<div className="fixed inset-0 z-50 bg-[#231412]/30 backdrop-blur-sm flex items-center justify-center p-4">
					<div className="bg-white rounded-3xl shadow-2xl border border-[#C8281E]/20 max-w-md w-full p-6 animate-in zoom-in-95">
						<h3 className="text-base font-bold text-[#231412] mb-1">
							{selectedParty.type==='CUSTOMER'?'Record Collection':'Record Settlement'}
						</h3>
						<p className="text-xs text-[#231412]/60 mb-4">
							Party: <span className="font-semibold text-[#231412]">{selectedParty.name}</span>
						</p>
						<form onSubmit={handleRecordPayment} className="space-y-3">
							<div>
								<label className="block text-xs font-semibold text-[#231412]/70 mb-1">Amount (₹)</label>
								<input
									type="number"
									step="0.01"
									required
									placeholder="0.00"
									value={paymentAmount}
									onChange={(e)=>setPaymentAmount(e.target.value)}
									className="w-full text-xs px-3 py-2 rounded-xl border border-[#C8281E]/20 focus:outline-none focus:border-[#C8281E]"
								/>
							</div>
							<div>
								<label className="block text-xs font-semibold text-[#231412]/70 mb-1">Payment Channel</label>
								<select
									value={paymentMethod}
									onChange={(e)=>setPaymentMethod(e.target.value)}
									className="w-full text-xs px-3 py-2 rounded-xl border border-[#C8281E]/20 focus:outline-none focus:border-[#C8281E]"
								>
									<option value="BANK_TRANSFER">Bank Transfer (IMPS/NEFT)</option>
									<option value="UPI">UPI / QR Code</option>
									<option value="CASH">Cash in Hand</option>
									<option value="CHEQUE">Cheque</option>
								</select>
							</div>
							<div className="flex items-center justify-end space-x-2 pt-3 border-t border-[#C8281E]/10">
								<MotionButton
									type="button"
									onClick={()=>setShowPaymentModal(false)}
									className="px-3.5 py-1.5 text-xs text-[#231412]/70 hover:text-[#231412]"
								>
									Cancel
								</MotionButton>
								<MotionButton
									type="submit"
									className="px-4 py-2 rounded-xl bg-[#C8281E] text-white text-xs font-bold hover:bg-[#A82018]"
								>
									Post to Ledger
								</MotionButton>
							</div>
						</form>
					</div>
				</div>
			)}

			{editingCustomer&&(
				<div className="fixed inset-0 z-50 bg-[#231412]/30 backdrop-blur-sm flex items-center justify-center p-4">
					<div className="bg-white rounded-3xl shadow-2xl border border-[#C8281E]/20 max-w-md w-full p-6 animate-in zoom-in-95">
						<h3 className="text-base font-bold text-[#231412] mb-1">Edit Customer Khata</h3>
						<p className="text-xs text-[#231412]/60 mb-4">
							Update credit exposure limit and contact identifiers.
						</p>
						<form onSubmit={handleUpdateCustomer} className="space-y-3">
							<div>
								<label className="block text-xs font-semibold text-[#231412]/70 mb-1">Customer / Trade Name</label>
								<input
									type="text"
									required
									value={editCustName}
									onChange={(e)=>setEditCustName(e.target.value)}
									className="w-full text-xs px-3 py-2 rounded-xl border border-[#C8281E]/20 focus:outline-none focus:border-[#C8281E]"
								/>
							</div>
							<div>
								<label className="block text-xs font-semibold text-[#231412]/70 mb-1">Phone Number</label>
								<input
									type="text"
									value={editCustPhone}
									onChange={(e)=>setEditCustPhone(e.target.value)}
									className="w-full text-xs px-3 py-2 rounded-xl border border-[#C8281E]/20 focus:outline-none focus:border-[#C8281E]"
								/>
							</div>
							<div>
								<label className="block text-xs font-semibold text-[#231412]/70 mb-1">Credit Limit (₹)</label>
								<input
									type="number"
									step="0.01"
									value={editCustCreditLimit}
									onChange={(e)=>setEditCustCreditLimit(e.target.value)}
									className="w-full text-xs px-3 py-2 rounded-xl border border-[#C8281E]/20 focus:outline-none focus:border-[#C8281E]"
								/>
							</div>
							<div className="flex items-center justify-end space-x-2 pt-3 border-t border-[#C8281E]/10">
								<MotionButton
									type="button"
									onClick={()=>setEditingCustomer(null)}
									className="px-3.5 py-1.5 text-xs text-[#231412]/70 hover:text-[#231412]"
								>
									Cancel
								</MotionButton>
								<MotionButton
									type="submit"
									className="px-4 py-2 rounded-xl bg-[#C8281E] text-white text-xs font-bold hover:bg-[#A82018]"
								>
									Save Changes
								</MotionButton>
							</div>
						</form>
					</div>
				</div>
			)}

			{editingSupplier&&(
				<div className="fixed inset-0 z-50 bg-[#231412]/30 backdrop-blur-sm flex items-center justify-center p-4">
					<div className="bg-white rounded-3xl shadow-2xl border border-[#C8281E]/20 max-w-md w-full p-6 animate-in zoom-in-95">
						<h3 className="text-base font-bold text-[#231412] mb-1">Edit Supplier Profile</h3>
						<p className="text-xs text-[#231412]/60 mb-4">
							Update vendor contact person and operational identifiers.
						</p>
						<form onSubmit={handleUpdateSupplier} className="space-y-3">
							<div>
								<label className="block text-xs font-semibold text-[#231412]/70 mb-1">Supplier Company Name</label>
								<input
									type="text"
									required
									value={editSuppName}
									onChange={(e)=>setEditSuppName(e.target.value)}
									className="w-full text-xs px-3 py-2 rounded-xl border border-[#C8281E]/20 focus:outline-none focus:border-[#C8281E]"
								/>
							</div>
							<div>
								<label className="block text-xs font-semibold text-[#231412]/70 mb-1">Contact Person</label>
								<input
									type="text"
									value={editSuppContact}
									onChange={(e)=>setEditSuppContact(e.target.value)}
									className="w-full text-xs px-3 py-2 rounded-xl border border-[#C8281E]/20 focus:outline-none focus:border-[#C8281E]"
								/>
							</div>
							<div>
								<label className="block text-xs font-semibold text-[#231412]/70 mb-1">Phone Number</label>
								<input
									type="text"
									value={editSuppPhone}
									onChange={(e)=>setEditSuppPhone(e.target.value)}
									className="w-full text-xs px-3 py-2 rounded-xl border border-[#C8281E]/20 focus:outline-none focus:border-[#C8281E]"
								/>
							</div>
							<div className="flex items-center justify-end space-x-2 pt-3 border-t border-[#C8281E]/10">
								<MotionButton
									type="button"
									onClick={()=>setEditingSupplier(null)}
									className="px-3.5 py-1.5 text-xs text-[#231412]/70 hover:text-[#231412]"
								>
									Cancel
								</MotionButton>
								<MotionButton
									type="submit"
									className="px-4 py-2 rounded-xl bg-[#C8281E] text-white text-xs font-bold hover:bg-[#A82018]"
								>
									Save Changes
								</MotionButton>
							</div>
						</form>
					</div>
				</div>
			)}
    </div>
  );
}
