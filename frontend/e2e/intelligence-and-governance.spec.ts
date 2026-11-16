import { test, expect } from '@playwright/test';
import { apiBaseURL, archiveWorkspace, createWorkspaceSession, expectJsonStatus, isoDate } from './helpers';

const webBaseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000';

test.describe('Financial intelligence, decision history, scenarios, goals, and agent actions', () => {
  test('evaluates a real workspace and confirms an agent proposal before writing', async ({ request, page }) => {
    test.setTimeout(120000);
    const context = await createWorkspaceSession(request, 'intelligence');
    const { businessId, headers, token } = context;
    try {
      const pnl = await expectJsonStatus(await request.get(`${apiBaseURL}/businesses/${businessId}/analytics/pnl`, { headers }), 200);
      expect(pnl).toHaveProperty('provenance');

      const decision = await expectJsonStatus(await request.post(`${apiBaseURL}/businesses/${businessId}/decisions/evaluate`, {
        headers,
        data: {
          model_id: 'FINANCING_COMPARISON',
          inputs: {
            purchase_cost: '10000.00', monthly_operating_gain: '2500.00', available_cash: '5000.00',
            loan_interest_rate_pct: '12', loan_term_months: 12, lease_monthly_payment: '900.00',
            lease_term_months: 12, equity_injection: '5000.00', discount_rate_pct: '10',
          },
          save_evaluation: true,
        },
      }), 200);
      expect(decision.evaluation_id).toBeTruthy();
      const versions = await expectJsonStatus(await request.get(`${apiBaseURL}/businesses/${businessId}/decisions/${decision.evaluation_id}/versions`, { headers }), 200);
      expect(versions.length).toBeGreaterThan(0);

      const assumptions = {
        horizon_months: 12,
        initial_quantity: 100,
        monthly_volume_growth_rate: 0.02,
        selling_price: 100,
        variable_cost_per_unit: 55,
        fixed_monthly_operating_expenses: 1000,
        opening_cash: 10000,
      };
      const scenario = await expectJsonStatus(await request.post(`${apiBaseURL}/businesses/${businessId}/scenarios`, {
        headers, data: { name: `E2E scenario ${Date.now()}`, description: 'Acceptance journey', assumptions },
      }), 200);
      const revised = await expectJsonStatus(await request.post(`${apiBaseURL}/businesses/${businessId}/scenarios/${scenario.id}/versions`, {
        headers, data: { assumptions: { ...assumptions, selling_price: 105 } },
      }), 200);
      expect(revised.current_version).toBe(2);
      const comparison = await expectJsonStatus(await request.post(`${apiBaseURL}/businesses/${businessId}/scenarios/compare`, {
        headers,
        data: { version_ids: [scenario.latest_version.id, revised.latest_version.id] },
      }), 200);
      expect(comparison.versions).toHaveLength(2);
      const run = await expectJsonStatus(await request.post(`${apiBaseURL}/businesses/${businessId}/scenarios/${scenario.id}/runs`, {
        headers,
        data: { iterations: 30, random_seed: 731, distributions: {
          selling_price: { distribution: 'UNIFORM', min_val: 99, max_val: 101 },
        } },
      }), 200);
      const replay = await expectJsonStatus(await request.post(`${apiBaseURL}/businesses/${businessId}/scenarios/${scenario.id}/runs/${run.id}/replay`, { headers }), 200);
      expect(replay.replayed).toBe(true);

      const goal = await expectJsonStatus(await request.post(`${apiBaseURL}/businesses/${businessId}/goals`, {
        headers,
        data: { goal_type: 'REVENUE', title: 'E2E revenue plan', target_value: '10000.00', start_date: isoDate(), target_date: isoDate(120) },
      }), 201);
      const progress = await expectJsonStatus(await request.post(`${apiBaseURL}/businesses/${businessId}/goals/${goal.id}/evaluate`, { headers }), 200);
      expect(progress).toHaveProperty('evidence_items');

      const investigation = await expectJsonStatus(await request.post(`${apiBaseURL}/businesses/${businessId}/agent/investigate`, {
        headers, data: { query: 'Summarize the workspace financial snapshot and cite the records used.' },
      }), 200);
      expect(investigation.session_id).toBeTruthy();
      const proposal = await expectJsonStatus(await request.post(`${apiBaseURL}/businesses/${businessId}/agent/sessions/${investigation.session_id}/actions`, {
        headers,
        data: { action_type: 'CREATE_GOAL', payload: {
          goal_type: 'CASH_RESERVE', title: 'Confirmed agent cash goal', target_value: '3000.00',
          start_date: isoDate(), target_date: isoDate(90),
        } },
      }), 201);
      expect(proposal.status).toBe('PENDING_CONFIRMATION');
      const confirmed = await expectJsonStatus(await request.post(`${apiBaseURL}/businesses/${businessId}/agent/sessions/${investigation.session_id}/actions/${proposal.id}/confirm`, { headers }), 200);
      expect(confirmed.status).toBe('CONFIRMED');

      const report = await request.get(`${apiBaseURL}/businesses/${businessId}/reports/dossier.pdf`, { headers });
      expect(report.status()).toBe(200);
      expect((await report.body()).subarray(0, 5).toString()).toBe('%PDF-');

      await page.addInitScript((authToken) => localStorage.setItem('arthlens_token', authToken), token);
      await page.goto(`${webBaseURL}/workspaces/${businessId}/decisions`);
      await expect(page.getByRole('heading', { name: /decision/i }).first()).toBeVisible();
    } finally {
      await archiveWorkspace(request, token, businessId);
    }
  });
});
