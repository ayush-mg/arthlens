'use client';
import { MotionButton } from '@/components/ui/motion-button';

import React, { useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { FileDown, Landmark, Receipt, Wallet } from 'lucide-react';
import { useToast } from '@/components/ui';
import { businessApi, downloadAuthenticatedReport } from '../../../../lib/business-api';
import { formatINR } from '../../../../lib/money';

type CashRecord = { id: string; category: string; amount: string | number; date: string; description?: string };
type JournalLine = { account_code: string; account_name: string; debit: string | number; credit: string | number };
type JournalEntry = {
  id: string; entry_number: string; entry_date: string; reference_type: string;
  description: string; total_debits: string | number; lines: JournalLine[];
};
type TransactionRow = { id: string; date: string; entry_number: string; reference_type: string; description: string; amount_exact: string; currency: string };

const inputClass = 'w-full rounded-none border border-black/[0.08]/15 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2EB872]/40';

export default function FinancePage() {
  const { toast } = useToast();
  const params = useParams();
  const businessId = params.id as string;
  const [income, setIncome] = useState<CashRecord[]>([]);
  const [expenses, setExpenses] = useState<CashRecord[]>([]);
  const [journals, setJournals] = useState<JournalEntry[]>([]);
  const [transactions, setTransactions] = useState<TransactionRow[]>([]);
  const [transactionQuery, setTransactionQuery] = useState('');
  const [transactionType, setTransactionType] = useState('');
  const [transactionStart, setTransactionStart] = useState('');
  const [transactionEnd, setTransactionEnd] = useState('');
  const [trialBalance, setTrialBalance] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [incomeAmount, setIncomeAmount] = useState('');
  const [incomeCategory, setIncomeCategory] = useState('OTHER');
  const [incomeDescription, setIncomeDescription] = useState('');
  const [expenseAmount, setExpenseAmount] = useState('');
  const [expenseCategory, setExpenseCategory] = useState('OPERATING');
  const [expenseDescription, setExpenseDescription] = useState('');
  const today = new Date().toISOString().slice(0, 10);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [incomeRows, expenseRows, journalRows, balance, transactionResult] = await Promise.all([
        businessApi.listIncome(businessId),
        businessApi.listExpenses(businessId),
        businessApi.getJournalEntries(businessId),
        businessApi.getTrialBalance(businessId, today),
        businessApi.searchTransactions(businessId),
      ]);
      setIncome(incomeRows);
      setExpenses(expenseRows);
      setJournals(journalRows);
      setTrialBalance(balance);
      setTransactions(transactionResult.transactions ?? []);
    } catch (error) {
      toast.error(`Finance data could not be loaded: ${(error as Error).message}`);
    } finally {
      setLoading(false);
    }
  }, [businessId, today, toast]);

  useEffect(() => { void loadData(); }, [loadData]);

  const submitIncome = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      await businessApi.recordIncome(businessId, {
        source: incomeDescription.trim(), category: incomeCategory, amount: incomeAmount,
        payment_method: 'BANK_TRANSFER', date: today,
      });
      setIncomeAmount('');
      setIncomeDescription('');
      toast.success('Income recorded');
      await loadData();
    } catch (error) {
      toast.error(`Income could not be recorded: ${(error as Error).message}`);
    } finally {
      setSaving(false);
    }
  };

  const submitExpense = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      await businessApi.recordExpense(businessId, {
        category: expenseCategory, amount: expenseAmount, payment_method: 'BANK_TRANSFER',
        date: today, description: expenseDescription.trim(),
      });
      setExpenseAmount('');
      setExpenseDescription('');
      toast.success('Expense recorded');
      await loadData();
    } catch (error) {
      toast.error(`Expense could not be recorded: ${(error as Error).message}`);
    } finally {
      setSaving(false);
    }
  };

  const applyTransactionFilters = async (event: React.FormEvent) => {
    event.preventDefault();
    try {
      const result = await businessApi.searchTransactions(businessId, {
        query: transactionQuery.trim(), reference_type: transactionType,
        start_date: transactionStart, end_date: transactionEnd,
      });
      setTransactions(result.transactions ?? []);
    } catch (error) { toast.error(`Transactions could not be loaded: ${(error as Error).message}`); }
  };

  return (
    <main className="mx-auto max-w-7xl space-y-6">
      <header className="flex flex-col gap-3 border-b border-black/[0.08]/10 pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#0D0F17]">Finance & General Ledger</h1>
          <p className="mt-1 text-sm text-slate-500">Record cash activity and inspect the journal entries behind each posting.</p>
        </div>
        <MotionButton
          type="button"
          onClick={() => downloadAuthenticatedReport(
            businessApi.getGeneralLedgerCsvUrl(businessId), `general-ledger-${businessId}.csv`,
          ).catch((error: Error) => toast.error(`Export failed: ${error.message}`))}
          className="inline-flex items-center gap-2 rounded-none bg-[#2B4EFF] px-4 py-2 text-sm font-semibold text-[#0D0F17] hover:bg-[#E9E8E2]"
        >
          <FileDown className="h-4 w-4" /> Export General Ledger
        </MotionButton>
      </header>

      <section className="grid gap-4 md:grid-cols-3">
        <article className="rounded-none border border-black/[0.08]/10 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500"><Wallet className="h-4 w-4" /> Posted journal entries</div>
          <div className="mt-3 text-2xl font-bold tabular-nums text-[#0D0F17]">{journals.length}</div>
        </article>
        <article className="rounded-none border border-black/[0.08]/10 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500"><Landmark className="h-4 w-4" /> Trial balance</div>
          <div className={`mt-3 text-lg font-bold ${trialBalance?.is_balanced ? 'text-[#10B981]' : 'text-[#F59E0B]'}`}>
            {loading ? 'Loading…' : trialBalance?.is_balanced ? 'Balanced' : 'Needs review'}
          </div>
        </article>
        <article className="rounded-none border border-black/[0.08]/10 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500"><Receipt className="h-4 w-4" /> Source records</div>
          <div className="mt-3 text-2xl font-bold tabular-nums text-[#0D0F17]">{income.length + expenses.length}</div>
        </article>
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <form onSubmit={submitIncome} className="space-y-4 rounded-none border border-black/[0.08]/10 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-bold text-[#0D0F17]">Record income</h2>
          <label className="block text-xs font-semibold text-slate-500">Category
            <select className={`${inputClass} mt-1`} value={incomeCategory} onChange={(event) => setIncomeCategory(event.target.value)}>
              <option value="OTHER">Other income</option><option value="SALES_COLLECTION">Sales collection</option>
              <option value="INTEREST">Interest</option><option value="RENTAL">Rental income</option>
            </select>
          </label>
          <label className="block text-xs font-semibold text-slate-500">Description
            <input required className={`${inputClass} mt-1`} value={incomeDescription} onChange={(event) => setIncomeDescription(event.target.value)} />
          </label>
          <label className="block text-xs font-semibold text-slate-500">Amount (₹)
            <input required min="0.01" step="0.01" type="number" className={`${inputClass} mt-1 tabular-nums`} value={incomeAmount} onChange={(event) => setIncomeAmount(event.target.value)} />
          </label>
          <MotionButton disabled={saving} className="rounded-none bg-[#10B981] px-4 py-2 text-sm font-semibold text-[#0D0F17] disabled:opacity-60">Record income</MotionButton>
        </form>

        <form onSubmit={submitExpense} className="space-y-4 rounded-none border border-black/[0.08]/10 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-bold text-[#0D0F17]">Record expense</h2>
          <label className="block text-xs font-semibold text-slate-500">Category
            <select className={`${inputClass} mt-1`} value={expenseCategory} onChange={(event) => setExpenseCategory(event.target.value)}>
              <option value="OPERATING">Operating</option><option value="ADMINISTRATIVE">Administrative</option>
              <option value="MARKETING">Marketing</option><option value="UTILITIES">Utilities</option>
              <option value="SALARIES">Salaries</option><option value="INTEREST">Interest</option><option value="OTHER">Other</option>
            </select>
          </label>
          <label className="block text-xs font-semibold text-slate-500">Description
            <input required className={`${inputClass} mt-1`} value={expenseDescription} onChange={(event) => setExpenseDescription(event.target.value)} />
          </label>
          <label className="block text-xs font-semibold text-slate-500">Amount (₹)
            <input required min="0.01" step="0.01" type="number" className={`${inputClass} mt-1 tabular-nums`} value={expenseAmount} onChange={(event) => setExpenseAmount(event.target.value)} />
          </label>
          <MotionButton disabled={saving} className="rounded-none bg-[#F59E0B] px-4 py-2 text-sm font-semibold text-[#0D0F17] disabled:opacity-60">Record expense</MotionButton>
        </form>
      </section>

      <section className="grid gap-5 xl:grid-cols-2">
        <div className="overflow-hidden rounded-none border border-black/[0.08]/10 bg-white shadow-sm">
          <div className="border-b border-black/[0.08]/10 p-4"><h2 className="font-bold text-[#0D0F17]">Income & expenses</h2></div>
          <div className="max-h-[520px] overflow-auto">
            {[...income.map((row) => ({ ...row, record_type: 'Income' })), ...expenses.map((row) => ({ ...row, record_type: 'Expense' }))]
              .sort((left, right) => right.date.localeCompare(left.date)).map((row) => (
                <div key={`${row.record_type}-${row.id}`} className="flex items-center justify-between gap-4 border-b border-black/[0.08]/5 px-4 py-3 last:border-0">
                  <div><div className="text-sm font-semibold text-[#0D0F17]">{row.description || row.category}</div><div className="text-xs text-slate-500">{row.date} · {row.record_type} · {row.category}</div></div>
                  <div className={`whitespace-nowrap text-sm font-bold tabular-nums ${row.record_type === 'Income' ? 'text-[#10B981]' : 'text-[#F59E0B]'}`}>{formatINR(row.amount)}</div>
                </div>
              ))}
            {!loading && income.length + expenses.length === 0 && <div className="p-6 text-sm text-slate-500">No income or expense records yet.</div>}
          </div>
        </div>

        <div className="overflow-hidden rounded-none border border-black/[0.08]/10 bg-white shadow-sm">
          <div className="border-b border-black/[0.08]/10 p-4"><h2 className="font-bold text-[#0D0F17]">General journal</h2></div>
          <div className="max-h-[520px] overflow-auto">
            {journals.map((entry) => (
              <details key={entry.id} className="border-b border-black/[0.08]/5 px-4 py-3 last:border-0">
                <summary className="cursor-pointer list-none">
                  <div className="flex items-start justify-between gap-3">
                    <div><div className="text-sm font-semibold text-[#0D0F17]">{entry.description}</div><div className="mt-1 text-xs text-slate-500">{entry.entry_number} · {entry.entry_date} · {entry.reference_type}</div></div>
                    <div className="whitespace-nowrap text-sm font-bold tabular-nums text-[#0D0F17]">{formatINR(entry.total_debits)}</div>
                  </div>
                </summary>
                <div className="mt-3 space-y-2 rounded-none bg-[#F7F7F2] p-3">
                  {entry.lines.map((line, index) => <div key={`${line.account_code}-${index}`} className="grid grid-cols-[1fr_auto_auto] gap-3 text-xs">
                    <span className="text-slate-500">{line.account_code} · {line.account_name}</span><span className="tabular-nums">Dr {formatINR(line.debit)}</span><span className="tabular-nums">Cr {formatINR(line.credit)}</span>
                  </div>)}
                </div>
              </details>
            ))}
            {!loading && journals.length === 0 && <div className="p-6 text-sm text-slate-500">No journal entries found.</div>}
          </div>
        </div>
      </section>

      <section className="overflow-hidden rounded-none border border-black/[0.08]/10 bg-white shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-black/[0.08]/10 p-4">
          <div><h2 className="font-bold text-[#0D0F17]">Transaction explorer</h2><p className="text-xs text-slate-500">Searches posted journal records with exact ledger amounts.</p></div>
          <MotionButton type="button" onClick={() => downloadAuthenticatedReport(
            businessApi.getTransactionsCsvUrl(businessId, { query: transactionQuery.trim(), reference_type: transactionType, start_date: transactionStart, end_date: transactionEnd }),
            `transactions-${businessId}.csv`,
          ).catch((error: Error) => toast.error(`Export failed: ${error.message}`))} className="inline-flex items-center gap-2 rounded-none border px-3 py-2 text-xs font-semibold"><FileDown className="h-4 w-4" /> Export filtered CSV</MotionButton>
        </div>
        <form onSubmit={applyTransactionFilters} className="grid gap-2 border-b border-black/[0.08]/10 p-4 sm:grid-cols-2 lg:grid-cols-5">
          <input value={transactionQuery} onChange={(event) => setTransactionQuery(event.target.value)} placeholder="Search description, reference or entry" aria-label="Search transactions" className={inputClass} />
          <input value={transactionType} onChange={(event) => setTransactionType(event.target.value)} placeholder="Reference type" aria-label="Filter transaction type" className={inputClass} />
          <input type="date" value={transactionStart} onChange={(event) => setTransactionStart(event.target.value)} aria-label="Transaction start date" className={inputClass} />
          <input type="date" value={transactionEnd} onChange={(event) => setTransactionEnd(event.target.value)} aria-label="Transaction end date" className={inputClass} />
          <MotionButton className="rounded-none bg-[#2B4EFF] px-3 py-2 text-xs font-semibold text-[#0D0F17]">Apply filters</MotionButton>
        </form>
        <div className="max-h-[440px] overflow-auto">
          {transactions.map((row) => <div key={row.id} className="flex flex-wrap items-center justify-between gap-3 border-b border-black/[0.08]/5 px-4 py-3 last:border-0"><div><div className="text-sm font-semibold text-[#0D0F17]">{row.description}</div><div className="text-xs text-slate-500">{row.date} · {row.entry_number} · {row.reference_type}</div></div><div className="whitespace-nowrap text-sm font-bold tabular-nums">{formatINR(row.amount_exact)}</div></div>)}
          {!loading && transactions.length === 0 && <div className="p-6 text-sm text-slate-500">No transactions match these filters.</div>}
        </div>
      </section>

      <p className="text-xs text-slate-500">Amounts are entered as fixed decimal strings and posted by the backend ledger. Date: {today}.</p>
    </main>
  );
}
