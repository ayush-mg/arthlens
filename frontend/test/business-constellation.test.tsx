import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import BusinessConstellation from '../components/constellation/BusinessConstellation';

vi.mock('next/navigation', () => ({ useRouter: () => ({ push: vi.fn() }) }));

const workspaces = [{
  id: 'ws-201',
  name: 'Kanpur Leather Goods',
  legal_name: 'Kanpur Leather Pvt Ltd',
  industry: 'Leather & Footwear',
  state: 'Uttar Pradesh',
  district: 'Kanpur',
  is_active: true,
  created_at: new Date().toISOString(),
}];

describe('Workspace directory', () => {
  it('shows a create action when there are no workspaces', () => {
    const create = vi.fn();
    render(<BusinessConstellation workspaces={[]} onCreateWorkspace={create} />);
    expect(screen.getByTestId('workspace-directory-empty')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /create workspace/i }));
    expect(create).toHaveBeenCalledOnce();
  });

  it('shows a retry action when loading fails', () => {
    const retry = vi.fn();
    render(<BusinessConstellation workspaces={[]} error="Service unavailable" onRetry={retry} />);
    expect(screen.getByTestId('workspace-directory-error')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /retry connection/i }));
    expect(retry).toHaveBeenCalledOnce();
  });

  it('renders accessible workspace cards and selects the requested workspace', () => {
    const select = vi.fn();
    render(<BusinessConstellation workspaces={workspaces} onSelectWorkspace={select} />);
    expect(screen.getByRole('region', { name: /business workspaces/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /kanpur leather goods/i }));
    expect(select).toHaveBeenCalledWith(workspaces[0]);
    expect(screen.queryByText(/galaxy|constellation|starfield/i)).not.toBeInTheDocument();
  });
});
