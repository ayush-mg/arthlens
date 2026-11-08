import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { PolicyWorkspace } from '../components/PolicyWorkspace';
import { ScenarioLaboratory } from '../components/ScenarioLaboratory';
import { branchScenario, compareScenarios, createScenario, deleteScenario, fetchMyScenarios, fetchPolicyRules, updateScenario } from '../lib/api';

vi.mock('../lib/api', () => ({
  branchScenario: vi.fn(),
  compareScenarios: vi.fn(),
  createScenario: vi.fn(),
  deleteScenario: vi.fn(),
  fetchMyScenarios: vi.fn(),
  fetchPolicyRules: vi.fn(),
  updateScenario: vi.fn(),
}));

vi.mock('../lib/audio', () => ({
  audioEngine: { playClick: vi.fn() },
}));

describe('scenario and policy workspaces', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('loads persisted scenarios and uses backend IDs for branching', async () => {
    vi.mocked(fetchMyScenarios).mockResolvedValue([
      {
        id: 'scenario-1',
        name: 'User scenario',
        owner_id: 'user-1',
        scenario: { capital: 300000, geo_id: 'in:district:120' },
      },
    ]);
    vi.mocked(branchScenario).mockResolvedValue({
      id: 'scenario-2',
      name: 'User scenario (Branch)',
      owner_id: 'user-1',
      parent_id: 'scenario-1',
    });

    render(
      <ScenarioLaboratory
        geoName="Prayagraj"
        geoId="in:district:120"
        userId="user-1"
        isAuthenticated
      />,
    );

    await waitFor(() => expect(screen.getAllByText('User scenario')).toHaveLength(2));
    fireEvent.click(screen.getByRole('button', { name: 'Branch' }));

    await waitFor(() => expect(screen.getAllByText('User scenario (Branch)').length).toBeGreaterThanOrEqual(2));
    expect(branchScenario).toHaveBeenCalledWith('scenario-1', 'User scenario (Branch)');
    expect(screen.queryByText(/Target Margin/)).not.toBeInTheDocument();
  });

  it('edits, compares and deletes persisted scenarios through the API', async () => {
    const first = {
      id: 'scenario-1', name: 'Left scenario', owner_id: 'user-1',
      scenario: { capital: 300000, geo_id: 'in:district:120' },
    };
    const second = {
      id: 'scenario-2', name: 'Right scenario', owner_id: 'user-1',
      scenario: { capital: 400000, geo_id: 'in:district:120' },
    };
    vi.mocked(fetchMyScenarios).mockResolvedValue([first, second]);
    vi.mocked(updateScenario).mockResolvedValue({ ...first, name: 'Edited scenario', scenario: { ...first.scenario, capital: 350000 } });
    vi.mocked(compareScenarios).mockResolvedValue({
      id: 'comparison-1', status: 'INSUFFICIENT_DATA', left_scenario_id: 'scenario-1',
      right_scenario_id: 'scenario-2', metrics: {}, unavailable_metrics: {},
    });
    vi.mocked(deleteScenario).mockResolvedValue(undefined);
    vi.stubGlobal('confirm', vi.fn(() => true));

    render(
      <ScenarioLaboratory geoName="Prayagraj" geoId="in:district:120" userId="user-1" isAuthenticated />,
    );

    const nameField = await screen.findByLabelText('Scenario name');
    fireEvent.change(nameField, { target: { value: 'Edited scenario' } });
    fireEvent.change(screen.getByLabelText('Capital assumption (₹)'), { target: { value: '350000' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save edits' }));
    await waitFor(() => expect(updateScenario).toHaveBeenCalledWith(
      'scenario-1',
      'Edited scenario',
      { capital: 350000, geo_id: 'in:district:120' },
    ));

    fireEvent.click(screen.getByRole('button', { name: 'Compare persisted results' }));
    await waitFor(() => expect(compareScenarios).toHaveBeenCalledWith('scenario-1', 'scenario-2'));

    fireEvent.click(screen.getByRole('button', { name: 'Delete Edited scenario' }));
    await waitFor(() => expect(deleteScenario).toHaveBeenCalledWith('scenario-1'));
  });

  it('does not present a failed scenario save as a successful local record', async () => {
    vi.mocked(fetchMyScenarios).mockResolvedValue([]);
    vi.mocked(createScenario).mockRejectedValue(new Error('Backend unavailable'));

    render(
      <ScenarioLaboratory
        geoName="Prayagraj"
        geoId="in:district:120"
        userId="user-1"
        isAuthenticated
      />,
    );

    fireEvent.change(await screen.findByPlaceholderText('e.g., Kirana Retail Grocery in Naini'), {
      target: { value: 'New business scenario' },
    });
    fireEvent.change(screen.getByLabelText('Capital assumption (INR, entered by you)'), {
      target: { value: '250000' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Initialize Scenario Branch' }));

    expect(await screen.findByText('Backend unavailable')).toBeInTheDocument();
    expect(screen.queryByText('New business scenario')).not.toBeInTheDocument();
  });

  it('requires an explicit capital assumption before saving a scenario', async () => {
    vi.mocked(fetchMyScenarios).mockResolvedValue([]);

    render(
      <ScenarioLaboratory
        geoName="Prayagraj"
        geoId="in:district:120"
        userId="user-1"
        isAuthenticated
      />,
    );

    fireEvent.change(await screen.findByPlaceholderText('e.g., Kirana Retail Grocery in Naini'), {
      target: { value: 'New business scenario' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Initialize Scenario Branch' }));

    expect(await screen.findByText('Enter a positive whole-rupee capital assumption.')).toBeInTheDocument();
    expect(createScenario).not.toHaveBeenCalled();
  });

  it('shows no eligibility evaluation when no backend rule versions exist', async () => {
    vi.mocked(fetchPolicyRules).mockResolvedValue([]);

    render(
      <PolicyWorkspace
        geoName="Prayagraj"
        geoId="in:district:120"
        role="ENTREPRENEUR"
        isAuthenticated
      />,
    );

    await waitFor(() => expect(fetchPolicyRules).toHaveBeenCalledWith('PMFME'));
    expect(await screen.findByText(/No rule versions are registered/)).toBeInTheDocument();
    expect(screen.getByText('NOT AN ELIGIBILITY DECISION')).toBeInTheDocument();
    expect(screen.queryByText(/35% of eligible project cost/)).not.toBeInTheDocument();
    expect(screen.queryByText('TRUE')).not.toBeInTheDocument();
  });
});
