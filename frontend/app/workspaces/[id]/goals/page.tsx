'use client';
import { MotionButton } from '@/components/ui/motion-button';

import { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import { Goal, businessApi } from '../../../../lib/business-api';
import { formatINR } from '../../../../lib/money';
import { useToast } from '@/components/ui';

export default function GoalsPage() {
  const { toast } = useToast();
  const businessId = useParams().id as string;
  const [goals, setGoals] = useState<Goal[]>([]);
  const [activeGoalId, setActiveGoalId] = useState('');
  const [milestones, setMilestones] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [tasks, setTasks] = useState<any[]>([]);
  const [members, setMembers] = useState<any[]>([]);
  const [progress, setProgress] = useState<any>(null);
  const [title, setTitle] = useState('');
  const [goalType, setGoalType] = useState('REVENUE');
  const [target, setTarget] = useState('');
  const [targetDate, setTargetDate] = useState('');
  const [editingTitle, setEditingTitle] = useState('');
  const [editingTarget, setEditingTarget] = useState('');
  const [editingTargetDate, setEditingTargetDate] = useState('');
  const [milestoneTitle, setMilestoneTitle] = useState('');
  const [milestoneValue, setMilestoneValue] = useState('');
  const [milestoneDate, setMilestoneDate] = useState('');
  const [planTitle, setPlanTitle] = useState('');
  const [taskTitle, setTaskTitle] = useState('');
  const [taskPlanId, setTaskPlanId] = useState('');
  const [taskAssignee, setTaskAssignee] = useState('');
  const [taskImpact, setTaskImpact] = useState('');
  const [taskDueDate, setTaskDueDate] = useState('');

  const loadGoals = useCallback(async () => {
    setGoals(await businessApi.listGoals(businessId));
  }, [businessId]);

  const loadGoalDetails = useCallback(async (goalId: string) => {
    if (!goalId) return;
    try {
      const [milestoneRows, planRows, taskRows, snapshot] = await Promise.all([
        businessApi.listGoalMilestones(businessId, goalId),
        businessApi.listGoalPlans(businessId, goalId),
        businessApi.listGoalTasks(businessId, goalId),
        businessApi.evaluateGoalProgress(businessId, goalId),
      ]);
      setMilestones(milestoneRows);
      setPlans(planRows);
      setTasks(taskRows);
      setProgress(snapshot);
      setGoals((current) => current.map((goal) => goal.id === goalId ? {
        ...goal,
        current_amount: snapshot.actual_value,
        current_amount_exact: snapshot.actual_value,
        progress_pct: Number(goal.target_amount_exact ? Number(snapshot.actual_value) / Number(goal.target_amount_exact) * 100 : 0),
        status: (goal.status === 'CANCELLED' || snapshot.status === 'CANCELLED') ? 'CANCELLED' : snapshot.status,
      } : goal));
      setTaskPlanId((current) => planRows.some((plan) => plan.id === current) ? current : planRows[0]?.id || '');
    } catch (error) {
      toast.error(`Goal planning data could not be loaded: ${(error as Error).message}`);
    }
  }, [businessId, toast]);

  useEffect(() => {
    Promise.all([loadGoals(), businessApi.listMembers(businessId).then(setMembers)])
      .catch((error: Error) => toast.error(error.message));
  }, [businessId, loadGoals, toast]);

  useEffect(() => { if (activeGoalId) void loadGoalDetails(activeGoalId); }, [activeGoalId, loadGoalDetails]);

  const create = async (event: FormEvent) => {
    event.preventDefault();
    try {
      const startDate = new Date().toISOString().slice(0, 10);
      const goal = await businessApi.createGoal(businessId, {
        title: title.trim(), goal_type: goalType, target_amount: target.trim(), start_date: startDate, target_date: targetDate,
      });
      setGoals((items) => [goal, ...items]);
      setTitle(''); setTarget('');
      setActiveGoalId(goal.id);
      toast.success('Goal created');
    } catch (error) { toast.error(`Goal creation failed: ${(error as Error).message}`); }
  };

  async function createMilestone(event: FormEvent) {
    event.preventDefault();
    if (!activeGoalId) return;
    try {
      const milestone = await businessApi.createGoalMilestone(businessId, activeGoalId, {
        title: milestoneTitle.trim(), target_date: milestoneDate, target_value: milestoneValue.trim(),
      });
      setMilestones((items) => [...items, milestone].sort((a, b) => a.target_date.localeCompare(b.target_date)));
      setMilestoneTitle(''); setMilestoneValue(''); setMilestoneDate('');
      toast.success('Milestone added');
      await loadGoalDetails(activeGoalId);
    } catch (error) { toast.error(`Milestone could not be added: ${(error as Error).message}`); }
  }

  async function createPlan(event: FormEvent) {
    event.preventDefault();
    if (!activeGoalId) return;
    try {
      const plan = await businessApi.createGoalPlan(businessId, activeGoalId, { title: planTitle.trim() });
      setPlans((items) => [plan, ...items]); setTaskPlanId(plan.id); setPlanTitle('');
      toast.success('Action plan created');
    } catch (error) { toast.error(`Action plan could not be created: ${(error as Error).message}`); }
  }

  async function createTask(event: FormEvent) {
    event.preventDefault();
    if (!activeGoalId || !taskPlanId) return;
    try {
      const task = await businessApi.createGoalTask(businessId, activeGoalId, {
        plan_id: taskPlanId, title: taskTitle.trim(), assigned_member_id: taskAssignee || null,
        expected_financial_impact: taskImpact.trim(), due_date: taskDueDate || null,
      });
      setTasks((items) => [task, ...items]); setTaskTitle(''); setTaskImpact(''); setTaskDueDate('');
      toast.success('Action task created');
    } catch (error) { toast.error(`Action task could not be created: ${(error as Error).message}`); }
  }

  async function updateTaskStatus(taskId: string, status: string) {
    if (!activeGoalId) return;
    try {
      const updated = await businessApi.updateGoalTask(businessId, activeGoalId, taskId, { status });
      setTasks((items) => items.map((task) => task.id === taskId ? updated : task));
    } catch (error) { toast.error(`Task could not be updated: ${(error as Error).message}`); }
  }

  async function updateGoal(event: FormEvent) {
    event.preventDefault();
    if (!activeGoal) return;
    try {
      const updated = await businessApi.updateGoal(businessId, activeGoal.id, {
        title: editingTitle.trim(), target_value: editingTarget.trim(), target_date: editingTargetDate,
      });
      setGoals((items) => items.map((goal) => goal.id === updated.id ? updated : goal));
      toast.success('Goal details updated');
    } catch (error) { toast.error(`Goal could not be updated: ${(error as Error).message}`); }
  }

  async function cancelGoal() {
    if (!activeGoal) return;
    try {
      const cancelled = await businessApi.cancelGoal(businessId, activeGoal.id);
      setGoals((items) => items.map((goal) => goal.id === cancelled.id ? { ...goal, ...cancelled, status: 'CANCELLED' } : goal));
      setProgress((prev: any) => prev ? { ...prev, status: 'CANCELLED' } : null);
      toast.success('Goal cancelled. Its evidence and history remain available.');
    } catch (error) { toast.error(`Goal could not be cancelled: ${(error as Error).message}`); }
  }

  async function refreshProgress(goalId: string) {
    try {
      setActiveGoalId(goalId);
      const snapshot = await businessApi.evaluateGoalProgress(businessId, goalId);
      setProgress(snapshot);
      setGoals((items) => items.map((goal) => goal.id === goalId ? {
        ...goal, current_amount: snapshot.actual_value, current_amount_exact: snapshot.actual_value,
        progress_pct: Number(goal.target_amount_exact ? Number(snapshot.actual_value) / Number(goal.target_amount_exact) * 100 : 0),
        status: (goal.status === 'CANCELLED' || snapshot.status === 'CANCELLED') ? 'CANCELLED' : snapshot.status,
      } : goal));
      toast.success('Actuals recomputed from workspace records');
    } catch (error) { toast.error(`Progress evaluation failed: ${(error as Error).message}`); }
  }

  const activeGoal = goals.find((goal) => goal.id === activeGoalId);
  const editingGoalId = useRef('');
  useEffect(() => {
    if (!activeGoal || editingGoalId.current === activeGoal.id) return;
    editingGoalId.current = activeGoal.id;
    setEditingTitle(activeGoal.title);
    setEditingTarget(String(activeGoal.target_amount_exact ?? activeGoal.target_amount));
    setEditingTargetDate(activeGoal.target_date);
  }, [activeGoal]);
  return <main className="mx-auto max-w-7xl space-y-6 p-5 md:p-8">
    <header><p className="text-xs font-semibold uppercase tracking-widest text-[#10B981]">Planning</p><h1 className="mt-1 text-2xl font-bold text-[#0D0F17]">Goals & action plans</h1><p className="mt-1 text-sm text-slate-500">Track targets against ledger results, set dated milestones, and assign follow-up tasks.</p></header>
    <form onSubmit={create} className="grid gap-3 rounded-none border border-black/[0.08]/10 bg-white p-4 md:grid-cols-4">
      <input required value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Goal title" aria-label="Goal title" className="rounded-none border p-2 text-sm" />
      <select value={goalType} onChange={(e) => setGoalType(e.target.value)} aria-label="Goal type" className="rounded-none border p-2 text-sm"><option value="REVENUE">Revenue</option><option value="PROFIT">Profit</option><option value="DEBT_REDUCTION">Debt reduction</option><option value="CASH_RESERVE">Cash reserve</option><option value="WORKING_CAPITAL">Working capital</option></select>
      <input required inputMode="decimal" value={target} onChange={(e) => setTarget(e.target.value)} placeholder="Target amount" aria-label="Target amount" className="rounded-none border p-2 text-sm" />
      <input required type="date" value={targetDate} onChange={(e) => setTargetDate(e.target.value)} aria-label="Target date" className="rounded-none border p-2 text-sm" />
      <MotionButton className="rounded-none bg-[#2B4EFF] px-4 py-2 text-sm font-semibold text-[#0D0F17] md:col-span-4 md:justify-self-start">Create goal</MotionButton>
    </form>
    <section className="grid gap-4 md:grid-cols-2">
      {goals.map((goal) => <article key={goal.id} className={`rounded-none border bg-white p-5 ${activeGoalId === goal.id ? 'border-black/[0.08]' : 'border-black/[0.08]/10'} ${goal.status === 'CANCELLED' ? 'opacity-75 bg-slate-50' : ''}`}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <span className={`text-[10px] font-semibold uppercase tracking-wider ${goal.status === 'CANCELLED' ? 'text-[#C8281E] font-bold' : 'text-slate-500'}`}>
              {goal.goal_type} · {goal.status}
            </span>
            <h2 className={`mt-1 font-bold ${goal.status === 'CANCELLED' ? 'text-slate-500 line-through' : 'text-[#0D0F17]'}`}>
              {goal.title}
            </h2>
          </div>
          <div>
            <MotionButton
              onClick={() => {
                setActiveGoalId(goal.id);
                void refreshProgress(goal.id);
              }}
              className={`rounded-none border px-3 py-1.5 text-xs font-semibold transition-colors ${
                activeGoalId === goal.id ? 'bg-[#231412] text-white border-[#231412]' : 'hover:bg-slate-50'
              }`}
            >
              {activeGoalId === goal.id ? 'Managing' : 'Manage'}
            </MotionButton>
          </div>
        </div>
        <div className="mt-4 flex justify-between text-sm"><span>Actual {formatINR(goal.current_amount_exact ?? goal.current_amount)}</span><span>Target {formatINR(goal.target_amount_exact ?? goal.target_amount)}</span></div>
        <div className="mt-2 h-2 overflow-hidden rounded-none bg-[#E9E8E2]"><div className="h-full bg-[#10B981]" style={{ width: `${Math.max(0, Math.min(100, Number(goal.progress_pct || 0)))}%` }} /></div>
        <div className="mt-2 flex justify-between text-xs text-slate-500"><span>{Number(goal.progress_pct || 0).toFixed(1)}% of target</span><span>Due {goal.target_date}</span></div>
      </article>)}
      {!goals.length && <div className="rounded-none border border-dashed p-8 text-center text-sm text-slate-500 md:col-span-2">No goals have been created for this workspace.</div>}
    </section>

    {activeGoal && <section className="space-y-5 rounded-none border border-black/[0.08]/10 bg-white p-5 shadow-sm">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-[#0D0F17]">{activeGoal.title}</h2>
          <p className="text-xs text-slate-500">Actual versus plan · {progress?.as_of_date ?? 'evaluation pending'}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`rounded-none px-3 py-1 text-xs font-bold ${
            activeGoal.status === 'CANCELLED' ? 'bg-[#C8281E]/10 text-[#C8281E]' :
            progress?.status === 'ACHIEVED' ? 'bg-[#10B981]/10 text-[#10B981]' :
            progress?.status === 'BEHIND' ? 'bg-[#2B4EFF]/10 text-[#2B4EFF]' :
            progress?.status === 'AT_RISK' ? 'bg-[#F59E0B]/10 text-[#F59E0B]' :
            'bg-[#F59E0B]/10 text-[#F59E0B]'
          }`}>
            {activeGoal.status === 'CANCELLED' ? 'CANCELLED' : (progress?.status ?? activeGoal.status)}
          </span>
          {activeGoal.status !== 'CANCELLED' && (
            <MotionButton
              type="button"
              onClick={cancelGoal}
              className="rounded-none border border-[#C8281E]/40 px-3 py-1.5 text-xs font-semibold text-[#C8281E] hover:bg-[#C8281E]/10 transition-colors"
            >
              Cancel goal
            </MotionButton>
          )}
        </div>
      </header>
      {activeGoal.status !== 'CANCELLED' && <form onSubmit={updateGoal} className="grid gap-2 rounded-none bg-white p-4 md:grid-cols-[1fr_1fr_180px_auto]"><input required value={editingTitle} onChange={(event) => setEditingTitle(event.target.value)} aria-label="Edit goal title" className="rounded-none border bg-white p-2 text-xs" /><input required inputMode="decimal" value={editingTarget} onChange={(event) => setEditingTarget(event.target.value)} aria-label="Edit goal target amount" className="rounded-none border bg-white p-2 text-xs" /><input required type="date" value={editingTargetDate} onChange={(event) => setEditingTargetDate(event.target.value)} aria-label="Edit goal target date" className="rounded-none border bg-white p-2 text-xs" /><MotionButton className="rounded-none bg-[#2B4EFF] px-3 py-2 text-xs font-semibold text-[#0D0F17]">Save changes</MotionButton></form>}
      {progress && <div className="grid gap-3 sm:grid-cols-3"><div className="rounded-none bg-white p-4"><div className="text-xs text-slate-500">Planned</div><div className="mt-1 font-semibold">{formatINR(progress.planned_value)}</div></div><div className="rounded-none bg-white p-4"><div className="text-xs text-slate-500">Actual</div><div className="mt-1 font-semibold">{formatINR(progress.actual_value)}</div></div><div className="rounded-none bg-white p-4"><div className="text-xs text-slate-500">Variance</div><div className="mt-1 font-semibold">{formatINR(progress.deviation_value)}</div></div><div className="rounded-none border border-black/[0.08]/10 p-4 sm:col-span-3"><h3 className="text-sm font-semibold text-[#0D0F17]">Evidence backed explanation</h3><p className="mt-1 text-sm">{progress.explanation?.summary}</p><p className="mt-1 text-xs text-slate-500">Formula: {progress.explanation?.formula}</p>{progress.explanation?.drivers?.operating_expense_categories && <div className="mt-3 flex flex-wrap gap-2">{Object.entries(progress.explanation.drivers.operating_expense_categories).map(([category, amount]) => <span key={category} className="rounded-none bg-white px-2 py-1 text-xs">{category}: {formatINR(String(amount))}</span>)}</div>}<div className="mt-3 text-xs text-slate-500">Evidence records: {progress.evidence_items?.length ?? 0} · Data quality warnings: {progress.explanation?.drivers?.data_quality_warnings?.length ?? 0}</div></div></div>}

      {progress?.explanation?.deviation_analysis && <div className="rounded-none border border-black/[0.08]/10 bg-white p-4"><h3 className="text-sm font-semibold text-[#0D0F17]">Profit movement drivers · prior equal-length period</h3><p className="mt-1 text-[11px] text-slate-500">{progress.explanation.deviation_analysis.attribution_warning}</p><div className="mt-3 space-y-2">{progress.explanation.deviation_analysis.leading_drivers.map((driver: any) => <div key={driver.driver} className="flex flex-wrap items-center justify-between gap-2 border-b border-black/[0.08]/5 pb-2 text-xs"><span>{driver.driver}</span><span className="font-mono font-semibold">{formatINR(driver.profit_impact)} · {driver.profit_impact_percent_of_prior_metric ? driver.profit_impact_percent_of_prior_metric + '% of prior metric' : 'no prior base'}</span></div>)}</div><div className="mt-2 text-[11px] text-slate-500">Period profit change: {formatINR(progress.explanation.deviation_analysis.period_over_period_net_profit_change)} · Goal gap: {formatINR(progress.explanation.deviation_analysis.current_vs_plan_gap)}</div></div>}

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="space-y-3 rounded-none border border-black/[0.08]/10 p-4"><h3 className="font-semibold text-[#0D0F17]">Milestones</h3><form onSubmit={createMilestone} className="grid gap-2 sm:grid-cols-3"><input required value={milestoneTitle} onChange={(e) => setMilestoneTitle(e.target.value)} placeholder="Milestone" className="rounded-none border p-2 text-xs" /><input required type="date" value={milestoneDate} onChange={(e) => setMilestoneDate(e.target.value)} className="rounded-none border p-2 text-xs" /><input required inputMode="decimal" value={milestoneValue} onChange={(e) => setMilestoneValue(e.target.value)} placeholder="Target value" className="rounded-none border p-2 text-xs" /><MotionButton className="rounded-none bg-[#2B4EFF] px-3 py-2 text-xs font-semibold text-[#0D0F17] sm:col-span-3">Add milestone</MotionButton></form><div className="space-y-2">{milestones.map((milestone) => <div key={milestone.id} className="flex items-center justify-between rounded-none bg-white p-3 text-xs"><span><b>{milestone.title}</b> · {milestone.target_date} · {formatINR(milestone.target_value)}</span><MotionButton onClick={async () => { try { await businessApi.deleteGoalMilestone(businessId, activeGoal.id, milestone.id); setMilestones((items) => items.filter((item) => item.id !== milestone.id)); await loadGoalDetails(activeGoal.id); } catch (error) { toast.error((error as Error).message); } }} className="text-[#2B4EFF] underline">Remove</MotionButton></div>)}</div><p className="text-[11px] text-slate-500">Milestones interpolate the planned trajectory between dated targets.</p></div>

        <div className="space-y-3 rounded-none border border-black/[0.08]/10 p-4"><h3 className="font-semibold text-[#0D0F17]">Action plans</h3><form onSubmit={createPlan} className="flex gap-2"><input required value={planTitle} onChange={(e) => setPlanTitle(e.target.value)} placeholder="Action plan title" className="min-w-0 flex-1 rounded-none border p-2 text-xs" /><MotionButton className="rounded-none bg-[#2B4EFF] px-3 py-2 text-xs font-semibold text-[#0D0F17]">Create plan</MotionButton></form><div className="space-y-2">{plans.map((plan) => <div key={plan.id} className="rounded-none bg-white p-3 text-xs"><b>{plan.title}</b><span className="ml-2 text-slate-500">{plan.task_count ?? 0} tasks</span></div>)}</div>
          <h4 className="pt-2 text-sm font-semibold text-[#0D0F17]">Assigned tasks</h4><form onSubmit={createTask} className="grid gap-2 sm:grid-cols-2"><input required value={taskTitle} onChange={(e) => setTaskTitle(e.target.value)} placeholder="Task title" className="rounded-none border p-2 text-xs" /><select required value={taskPlanId} onChange={(e) => setTaskPlanId(e.target.value)} className="rounded-none border p-2 text-xs"><option value="">Choose plan</option>{plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.title}</option>)}</select><select value={taskAssignee} onChange={(e) => setTaskAssignee(e.target.value)} className="rounded-none border p-2 text-xs"><option value="">Unassigned</option>{members.map((member) => <option key={member.user_id ?? member.id} value={member.user_id ?? member.id}>{member.email ?? member.name ?? member.user_id ?? member.id}</option>)}</select><input type="date" value={taskDueDate} onChange={(e) => setTaskDueDate(e.target.value)} className="rounded-none border p-2 text-xs" /><input required inputMode="decimal" value={taskImpact} onChange={(e) => setTaskImpact(e.target.value)} placeholder="Expected financial impact" className="rounded-none border p-2 text-xs" /><MotionButton disabled={!plans.length} className="rounded-none bg-[#2B4EFF] px-3 py-2 text-xs font-semibold text-[#0D0F17] disabled:opacity-50">Add task</MotionButton></form>
          <div className="space-y-2">{tasks.map((task) => <div key={task.id} className="flex flex-wrap items-center justify-between gap-2 rounded-none border p-3 text-xs"><span><b>{task.title}</b><span className="ml-2 text-slate-500">{task.assigned_member_id ? (members.find((member) => (member.user_id ?? member.id) === task.assigned_member_id)?.email ?? 'Assigned') : 'Unassigned'} · Impact {formatINR(task.expected_financial_impact)}</span></span><select aria-label={`Status for ${task.title}`} value={task.status} onChange={(event) => void updateTaskStatus(task.id, event.target.value)} className="rounded-none border px-2 py-1"><option>TODO</option><option>IN_PROGRESS</option><option>COMPLETED</option><option>BLOCKED</option></select></div>)}</div>
        </div>
      </div>
    </section>}
  </main>;
}
