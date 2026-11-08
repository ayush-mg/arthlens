import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AgentConsole } from '../components/AgentConsole';
import {
  createAgentRun,
  fetchAgentRun,
  fetchAgentRunEvents,
  streamAgentRunEvents,
} from '../lib/api';

vi.mock('../lib/api', () => ({
  createAgentRun: vi.fn(),
  fetchAgentRun: vi.fn(),
  fetchAgentRunEvents: vi.fn(),
  startAgentRun: vi.fn(),
  streamAgentRunEvents: vi.fn(),
}));

vi.mock('../lib/audio', () => ({
  audioEngine: { playClick: vi.fn() },
}));

const persistedRun = {
  id: 'run-1',
  owner_id: 'user-1',
  objective: { territory: 'in:district:120' },
  state: 'CREATED',
  steps_used: 0,
  replans_used: 0,
  model_calls_used: 0,
  cost_usd: 0,
  created_at: '2026-11-07T10:00:00Z',
  updated_at: '2026-11-07T10:00:00Z',
};

describe('agent run console', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('displays the persisted state and does not invent worker events', async () => {
    vi.mocked(createAgentRun).mockResolvedValue(persistedRun);
    vi.mocked(fetchAgentRunEvents).mockResolvedValue({
      run_id: 'run-1',
      state: 'CREATED',
      events: [],
      next_sequence: 0,
    });

    render(
      <AgentConsole
        geoName="Prayagraj"
        geoId="in:district:120"
        isAuthenticated
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Create Run Record' }));

    await waitFor(() => expect(fetchAgentRunEvents).toHaveBeenCalledWith('run-1'));
    expect(await screen.findByText('State: CREATED')).toBeInTheDocument();
    expect(screen.getByText(/No lifecycle events have been recorded/)).toBeInTheDocument();
    expect(screen.getByText(/worker execution is not yet connected/i)).toBeInTheDocument();
    expect(screen.queryByText(/TERRITORY_GROUNDING/)).not.toBeInTheDocument();
    expect(screen.queryByText(/59,54,391/)).not.toBeInTheDocument();
  });

  it('surfaces run creation failures instead of reporting synthetic success', async () => {
    vi.mocked(createAgentRun).mockRejectedValue(new Error('Backend unavailable'));

    render(
      <AgentConsole
        geoName="Prayagraj"
        geoId="in:district:120"
        isAuthenticated
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Create Run Record' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Backend unavailable');
    expect(fetchAgentRunEvents).not.toHaveBeenCalled();
    expect(screen.queryByText(/State: CREATED/)).not.toBeInTheDocument();
  });

  it('refreshes state and event history from persisted API data', async () => {
    vi.mocked(createAgentRun).mockResolvedValue(persistedRun);
    vi.mocked(fetchAgentRunEvents)
      .mockResolvedValueOnce({
        run_id: 'run-1',
        state: 'CREATED',
        events: [],
        next_sequence: 0,
      })
      .mockResolvedValueOnce({
        run_id: 'run-1',
        state: 'INTERPRETING',
        events: [{
          seq: 1,
          type: 'RUN_ACCEPTED',
          payload: { from_state: 'CREATED', to_state: 'INTERPRETING' },
          at: '2026-11-07T10:01:00Z',
        }],
        next_sequence: 1,
      });
    vi.mocked(fetchAgentRun).mockResolvedValue({
      ...persistedRun,
      state: 'INTERPRETING',
    });

    render(
      <AgentConsole
        geoName="Prayagraj"
        geoId="in:district:120"
        isAuthenticated
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Create Run Record' }));
    await screen.findByText(/No lifecycle events have been recorded/);

    fireEvent.click(screen.getByRole('button', { name: 'Refresh' }));

    expect(await screen.findByText('State: INTERPRETING')).toBeInTheDocument();
    expect(await screen.findByText('Event 1: RUN_ACCEPTED')).toBeInTheDocument();
    expect(fetchAgentRun).toHaveBeenCalledWith('run-1');
    expect(fetchAgentRunEvents).toHaveBeenLastCalledWith('run-1');
  });

  it('renders only events delivered by the persisted event stream', async () => {
    vi.mocked(createAgentRun).mockResolvedValue(persistedRun);
    vi.mocked(fetchAgentRunEvents).mockResolvedValue({
      run_id: 'run-1',
      state: 'CREATED',
      events: [],
      next_sequence: 0,
    });
    vi.mocked(streamAgentRunEvents).mockImplementation(async (_id, _seq, onEvent) => {
      onEvent({
        seq: 1,
        type: 'RUN_ACCEPTED',
        payload: { from_state: 'CREATED', to_state: 'INTERPRETING' },
        at: '2026-11-07T10:01:00Z',
      });
    });
    vi.mocked(fetchAgentRun).mockResolvedValue({
      ...persistedRun,
      state: 'INTERPRETING',
    });

    render(
      <AgentConsole
        geoName="Prayagraj"
        geoId="in:district:120"
        isAuthenticated
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Create Run Record' }));
    await screen.findByText(/No lifecycle events have been recorded/);

    fireEvent.click(screen.getByRole('button', { name: 'Listen for live events' }));

    expect(await screen.findByText('Event 1: RUN_ACCEPTED')).toBeInTheDocument();
    expect(await screen.findByText('State: INTERPRETING')).toBeInTheDocument();
    expect(streamAgentRunEvents).toHaveBeenCalledWith(
      'run-1',
      0,
      expect.any(Function),
      expect.any(AbortSignal),
    );
  });
});
