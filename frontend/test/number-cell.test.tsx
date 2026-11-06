import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { NumberCell } from '../components/NumberCell';

describe('NumberCell Component (Acceptance Criterion: Every displayed number opens its ledger record)', () => {
  it('opens ledger provenance record when clicked', () => {
    const handleOpenProvenance = vi.fn();

    render(
      <NumberCell
        quantityId="q-pop-120"
        definitionKey="population.total"
        value={5954391.0}
        unit="persons"
        kind="OBSERVED"
        qualityStatus="STALE"
        qualityColor="#F97316"
        asOf="2011-03-01"
        onOpenProvenance={handleOpenProvenance}
      />
    );

    // Verify displayed number and unit (formatted in en-IN locale)
    expect(screen.getByText('59,54,391')).toBeInTheDocument();
    expect(screen.getByText('persons')).toBeInTheDocument();
    expect(screen.getByText('population.total')).toBeInTheDocument();
    expect(screen.getByText('OBSERVED')).toBeInTheDocument();
    expect(screen.getByText('STALE')).toBeInTheDocument();

    // Click the number cell button
    const button = screen.getByRole('button', { name: /Inspect ledger provenance/i });
    fireEvent.click(button);

    // Assert that the ledger provenance handler was called with exact quantityId
    expect(handleOpenProvenance).toHaveBeenCalledTimes(1);
    expect(handleOpenProvenance).toHaveBeenCalledWith('q-pop-120');
  });

  it('never displays numeric zero for unavailable data (No silent zeroes invariant)', () => {
    const handleOpenProvenance = vi.fn();

    render(
      <NumberCell
        quantityId="q-soil-missing"
        definitionKey="agriculture.soil_fertility_index"
        value={null}
        unit="index_score"
        kind="OBSERVED"
        qualityStatus="UNAVAILABLE"
        qualityColor="#94A3B8"
        onOpenProvenance={handleOpenProvenance}
      />
    );

    // Value must be displayed as 'Unavailable', strictly NOT '0' or '0.0'
    expect(screen.getByText('Unavailable')).toBeInTheDocument();
    expect(screen.queryByText('0')).not.toBeInTheDocument();
    expect(screen.queryByText('0.0')).not.toBeInTheDocument();

    // Clicking unavailable metric also opens its ledger record to inspect the data gap
    const button = screen.getByRole('button');
    fireEvent.click(button);
    expect(handleOpenProvenance).toHaveBeenCalledWith('q-soil-missing');
  });
});
