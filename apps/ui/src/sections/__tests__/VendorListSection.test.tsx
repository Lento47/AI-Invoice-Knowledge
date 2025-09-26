import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { VendorListSection } from '../VendorListSection';

vi.mock('../../hooks/useWorkspaceData', () => ({
  useVendorDirectory: vi.fn()
}));

const { useVendorDirectory } = await import('../../hooks/useWorkspaceData');
const mockUseVendorDirectory = useVendorDirectory as unknown as ReturnType<typeof vi.fn>;

const baseState = {
  data: null,
  status: 'idle',
  error: null,
  refresh: vi.fn(),
  setData: vi.fn()
};

describe('VendorListSection', () => {
  beforeEach(() => {
    mockUseVendorDirectory.mockReset();
    mockUseVendorDirectory.mockReturnValue({ ...baseState });
  });

  it('renders loading indicator', () => {
    mockUseVendorDirectory.mockReturnValue({ ...baseState, status: 'loading' });
    render(<VendorListSection />);
    expect(screen.getByText(/Loading vendors/i)).toBeInTheDocument();
  });

  it('renders error state with retry', () => {
    const refresh = vi.fn();
    mockUseVendorDirectory.mockReturnValue({ ...baseState, status: 'error', error: 'boom', refresh });
    render(<VendorListSection />);
    expect(screen.getByText(/Unable to load vendors/i)).toBeInTheDocument();
    screen.getByRole('button', { name: /retry/i }).click();
    expect(refresh).toHaveBeenCalled();
  });

  it('renders empty state', () => {
    mockUseVendorDirectory.mockReturnValue({ ...baseState, status: 'success', data: [] });
    render(<VendorListSection />);
    expect(screen.getByText(/Vendor data has not been ingested/i)).toBeInTheDocument();
  });

  it('renders vendor rows', () => {
    mockUseVendorDirectory.mockReturnValue({
      ...baseState,
      status: 'success',
      data: [
        { id: '1', name: 'Vendor A', category: 'Cat', contact: 'a@example.com', status: 'Active' }
      ]
    });
    render(<VendorListSection />);
    expect(screen.getByText(/Vendor A/i)).toBeInTheDocument();
  });
});
