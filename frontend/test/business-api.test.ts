import { describe, it, expect, vi, beforeEach } from 'vitest';
import { businessApi } from '../lib/business-api';

function createMockResponse(data: any, status = 200, ok = true) {
  return {
    ok,
    status,
    headers: {
      get: (header: string) => (header.toLowerCase() === 'content-type' ? 'application/json' : null),
    },
    json: async () => data,
    text: async () => JSON.stringify(data),
  };
}

describe('Business API Client', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches workspaces and handles successful responses', async () => {
    const mockWorkspaces = [
      {
        id: 'biz-1',
        name: 'Varanasi Silk Emporium',
        industry: 'Textiles',
        currency: 'INR',
        cash_balance: 450000,
        burn_rate: 35000,
        runway_months: 12.8,
        health_score: 85,
        role: 'OWNER',
      },
    ];

    global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockWorkspaces) as any);

    const result = await businessApi.listWorkspaces();
    expect(result).toHaveLength(1);
    expect(result[0].name).toBe('Varanasi Silk Emporium');
    expect(result[0].industry).toBe('Textiles');
    expect(global.fetch).toHaveBeenCalledWith('/businesses', expect.any(Object));
    const requestOptions = vi.mocked(global.fetch).mock.calls[0][1];
    expect(requestOptions?.credentials).toBe('include');
    expect(new Headers(requestOptions?.headers).get('content-type')).toBe('application/json');
  });

  it('creates a workspace with json body', async () => {
    const newWorkspace = {
      id: 'biz-new',
      name: 'Kanpur Leather Works',
      industry: 'Manufacturing',
      currency: 'INR',
      cash_balance: 0,
      burn_rate: 0,
      runway_months: 0,
      health_score: 100,
      role: 'OWNER',
    };

    global.fetch = vi.fn().mockResolvedValue(createMockResponse(newWorkspace) as any);

    const result = await businessApi.createWorkspace({
      name: 'Kanpur Leather Works',
      industry: 'Manufacturing',
    });

    expect(result.id).toBe('biz-new');
    expect(result.name).toBe('Kanpur Leather Works');
    expect(global.fetch).toHaveBeenCalledWith('/businesses', expect.any(Object));
    const requestOptions = vi.mocked(global.fetch).mock.calls[0][1];
    expect(requestOptions?.method).toBe('POST');
    expect(requestOptions?.credentials).toBe('include');
    expect(new Headers(requestOptions?.headers).get('content-type')).toBe('application/json');
    expect(requestOptions?.body).toContain('Kanpur Leather Works');
  });

  it('throws descriptive error on API failure', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      createMockResponse({ detail: 'Access denied to this business workspace.' }, 403, false) as any,
    );

    await expect(businessApi.getWorkspace('unauthorized-biz')).rejects.toThrow(
      'Access denied to this business workspace.',
    );
  });

  it('queries health score', async () => {
    const mockHealth = {
      composite_score: 82,
      classification: 'HEALTHY',
      liquidity_score: 88,
      profitability_score: 75,
      efficiency_score: 84,
      solvency_score: 80,
      growth_stability_score: 80,
      strengths: ['Strong liquidity buffer'],
      vulnerabilities: [],
      priority_recommendations: ['Maintain current credit policy'],
    };

    global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockHealth) as any);

    const result = await businessApi.getHealthScore('biz-1');
    expect(result.composite_score).toBe(82);
    expect(result.classification).toBe('HEALTHY');
  });

  it('posts copilot investigation chat', async () => {
    const mockInvestigation = {
      query: 'What is my current runway?',
      plan_nodes: [],
      evidence_gathered: { cash: 450000, payables: 120000 },
      data_gaps: [],
      follow_up_questions: [],
      synthesis: 'Working capital is sufficient for the next 6 months.',
      recommended_actions: ['Reconcile pending supplier dues'],
    };

    global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockInvestigation) as any);

    const result = await businessApi.agentInvestigate('biz-1', 'What is my current runway?');
    expect(result.synthesis).toContain('Working capital is sufficient');
    expect(result.recommended_actions).toContain('Reconcile pending supplier dues');
  });

  it('archives and deletes workspace', async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce(createMockResponse({ status: 'ok', business_id: 'biz-1', is_archived: true }) as any)
      .mockResolvedValueOnce(createMockResponse({ status: 'ok', business_id: 'biz-1', deleted: true }) as any);

    const archResult = await businessApi.archiveWorkspace('biz-1', true);
    expect(archResult.is_archived).toBe(true);
    expect(global.fetch).toHaveBeenCalledWith('/businesses/biz-1/archive', expect.objectContaining({ method: 'POST' }));

    const delResult = await businessApi.deleteWorkspace('biz-1');
    expect(delResult.deleted).toBe(true);
    expect(global.fetch).toHaveBeenCalledWith('/businesses/biz-1', expect.objectContaining({ method: 'DELETE' }));
  });
});
