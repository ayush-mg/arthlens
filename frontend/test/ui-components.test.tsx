import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardFooter,
  Input,
  Select,
  Badge,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  Modal,
  Drawer,
  Tabs,
  Skeleton,
} from '../components/ui';

describe('Liquid-Glass UI Component Library', () => {
  it('renders Button with variants, sizes and handles click', () => {
    const handleClick = vi.fn();
    render(
      <Button variant="brass" size="lg" onClick={handleClick}>
        Confirm Action
      </Button>
    );
    const btn = screen.getByRole('button', { name: /Confirm Action/i });
    expect(btn).toBeInTheDocument();
    fireEvent.click(btn);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('renders Card hierarchy with header, title, content and footer', () => {
    render(
      <Card variant="glass">
        <CardHeader>
          <CardTitle>Financial Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <p>Net profit is ₹1,20,000.</p>
        </CardContent>
        <CardFooter>
          <span>Audited</span>
        </CardFooter>
      </Card>
    );
    expect(screen.getByText('Financial Summary')).toBeInTheDocument();
    expect(screen.getByText('Net profit is ₹1,20,000.')).toBeInTheDocument();
    expect(screen.getByText('Audited')).toBeInTheDocument();
  });

  it('renders Input and Select with label, error and helper text', () => {
    render(
      <div>
        <Input label="Invoice Number" placeholder="INV-001" helperText="Auto-generated number" />
        <Select
          label="Category"
          options={[
            { label: 'Machinery', value: 'machinery' },
            { label: 'Raw Materials', value: 'raw' },
          ]}
        />
      </div>
    );
    expect(screen.getByLabelText(/Invoice Number/i)).toBeInTheDocument();
    expect(screen.getByText('Auto-generated number')).toBeInTheDocument();
    expect(screen.getByLabelText(/Category/i)).toBeInTheDocument();
  });

  it('renders Badge with status colors and dots', () => {
    render(
      <div>
        <Badge variant="success" dot>Operational</Badge>
        <Badge variant="warning">Needs Attention</Badge>
      </div>
    );
    expect(screen.getByText('Operational')).toBeInTheDocument();
    expect(screen.getByText('Needs Attention')).toBeInTheDocument();
  });

  it('renders Table structure with cells and rows', () => {
    render(
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>SKU</TableHead>
            <TableHead>Price</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell>SKU-101</TableCell>
            <TableCell>₹500</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );
    expect(screen.getByText('SKU')).toBeInTheDocument();
    expect(screen.getByText('SKU-101')).toBeInTheDocument();
    expect(screen.getByText('₹500')).toBeInTheDocument();
  });

  it('renders Modal and Drawer with close triggers', () => {
    const handleCloseModal = vi.fn();
    const handleCloseDrawer = vi.fn();

    const { rerender } = render(
      <div>
        <Modal isOpen={true} onClose={handleCloseModal} title="Confirm Transaction">
          <p>Modal body content</p>
        </Modal>
        <Drawer isOpen={true} onClose={handleCloseDrawer} title="Evidence Drawer">
          <p>Drawer body content</p>
        </Drawer>
      </div>
    );

    expect(screen.getByText('Confirm Transaction')).toBeInTheDocument();
    expect(screen.getByText('Evidence Drawer')).toBeInTheDocument();

    const closeBtns = screen.getAllByRole('button', { name: /Close/i });
    fireEvent.click(closeBtns[0]);
    expect(handleCloseModal).toHaveBeenCalledTimes(1);

    fireEvent.click(closeBtns[1]);
    expect(handleCloseDrawer).toHaveBeenCalledTimes(1);
  });

  it('renders Tabs and handles tab switching', () => {
    const handleChange = vi.fn();
    const items = [
      { id: 'all', label: 'All Entries', count: 12 },
      { id: 'pending', label: 'Pending', count: 3 },
    ];

    render(<Tabs items={items} activeId="all" onChange={handleChange} />);
    expect(screen.getByText('All Entries')).toBeInTheDocument();
    expect(screen.getByText('Pending')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Pending'));
    expect(handleChange).toHaveBeenCalledWith('pending');
  });

  it('renders Skeleton loaders without crashing', () => {
    render(<Skeleton className="w-24 h-6" />);
  });
});
