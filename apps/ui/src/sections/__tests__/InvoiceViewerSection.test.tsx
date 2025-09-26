import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { InvoiceViewerSection } from '../InvoiceViewerSection';

vi.mock('../../hooks/useWorkspaceData', () => ({
  useInvoiceData: vi.fn()
}));

const { useInvoiceData } = await import('../../hooks/useWorkspaceData');
const mockUseInvoiceData = useInvoiceData as unknown as ReturnType<typeof vi.fn>;

const baseState = {
  data: null,
  status: 'idle',
  error: null,
  refresh: vi.fn(),
  setData: vi.fn()
};

describe('InvoiceViewerSection', () => {
  beforeEach(() => {
    mockUseInvoiceData.mockReset();
    mockUseInvoiceData.mockReturnValue({ ...baseState });
  });

  it('shows loading indicator', () => {
    mockUseInvoiceData.mockReturnValue({ ...baseState, status: 'loading' });
    render(<InvoiceViewerSection />);
    expect(screen.getByText(/Fetching invoice details/i)).toBeInTheDocument();
  });

  it('renders error state', () => {
    const refresh = vi.fn();
    mockUseInvoiceData.mockReturnValue({ ...baseState, status: 'error', error: 'boom', refresh });
    render(<InvoiceViewerSection />);
    expect(screen.getByText(/Unable to load invoice/i)).toBeInTheDocument();
    screen.getByRole('button', { name: /retry/i }).click();
    expect(refresh).toHaveBeenCalled();
  });

  it('renders invoice summary and line items', () => {
    mockUseInvoiceData.mockReturnValue({
      ...baseState,
      status: 'success',
      data: {
        summary: {
          id: 'INV-1',
          vendor: 'Test Vendor',
          issued_on: '2024-01-01',
          due_on: '2024-01-15',
          amount: '$100',
          status: 'Pending',
          reference: 'PO-1',
          notes: 'Hello'
        },
        line_items: [
          { id: '1', description: 'Item', quantity: 1, unit_cost: '$100', amount: '$100' }
        ]
      }
    });
    render(<InvoiceViewerSection />);
    expect(screen.getByText(/Test Vendor/i)).toBeInTheDocument();
    expect(screen.getByText(/Item/i)).toBeInTheDocument();
  });

  it('renders empty line item message', () => {
    mockUseInvoiceData.mockReturnValue({
      ...baseState,
      status: 'success',
      data: {
        summary: {
          id: 'INV-1',
          vendor: 'Test Vendor',
          issued_on: '2024-01-01',
          due_on: '2024-01-15',
          amount: '$100',
          status: 'Pending',
          reference: 'PO-1',
          notes: null
        },
        line_items: []
      }
    });
    render(<InvoiceViewerSection />);
    expect(screen.getByText(/No line items/i)).toBeInTheDocument();
  });
});
