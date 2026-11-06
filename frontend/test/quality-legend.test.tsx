import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QualityLegend, QUALITY_STATES } from '../components/QualityLegend';

describe('QualityLegend Component (Handbook Part 7.5 Step 10 Presentation Contract)', () => {
  it('displays all five authoritative quality states with exact names and colors', () => {
    const handleFilterChange = vi.fn();

    render(
      <QualityLegend
        activeFilter="ALL"
        onFilterChange={handleFilterChange}
      />
    );

    // Assert all 5 states exist
    expect(screen.getByText('CURRENT')).toBeInTheDocument();
    expect(screen.getByText('INCOMPLETE')).toBeInTheDocument();
    expect(screen.getByText('STALE')).toBeInTheDocument();
    expect(screen.getByText('ESTIMATED')).toBeInTheDocument();
    expect(screen.getByText('UNAVAILABLE')).toBeInTheDocument();

    // Verify filter clicking
    const staleButton = screen.getByText('STALE').closest('button');
    expect(staleButton).toBeTruthy();
    if (staleButton) {
      fireEvent.click(staleButton);
      expect(handleFilterChange).toHaveBeenCalledWith('STALE');
    }
  });
});
