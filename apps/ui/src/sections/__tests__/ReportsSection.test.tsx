import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ReportsSection } from '../ReportsSection';

vi.mock('../../hooks/useWorkspaceData', () => ({
  useReportsLibrary: vi.fn()
}));

const { useReportsLibrary } = await import('../../hooks/useWorkspaceData');
const mockUseReportsLibrary = useReportsLibrary as unknown as ReturnType<typeof vi.fn>;

const baseState = {
  data: null,
  status: 'idle',
  error: null,
  refresh: vi.fn(),
  setData: vi.fn()
};

describe('ReportsSection', () => {
  beforeEach(() => {
    mockUseReportsLibrary.mockReset();
    mockUseReportsLibrary.mockReturnValue({ ...baseState });
  });

  it('renders loading state', () => {
    mockUseReportsLibrary.mockReturnValue({ ...baseState, status: 'loading' });
    render(<ReportsSection />);
    expect(screen.getByText(/Loading reports/i)).toBeInTheDocument();
  });

  it('renders error state', () => {
    const refresh = vi.fn();
    mockUseReportsLibrary.mockReturnValue({ ...baseState, status: 'error', error: 'boom', refresh });
    render(<ReportsSection />);
    expect(screen.getByText(/Unable to load reports/i)).toBeInTheDocument();
    screen.getByRole('button', { name: /retry/i }).click();
    expect(refresh).toHaveBeenCalled();
  });

  it('renders empty state', () => {
    mockUseReportsLibrary.mockReturnValue({ ...baseState, status: 'success', data: [] });
    render(<ReportsSection />);
    expect(screen.getByText(/No analytics reports/i)).toBeInTheDocument();
  });

  it('renders reports list', () => {
    mockUseReportsLibrary.mockReturnValue({
      ...baseState,
      status: 'success',
      data: [
        { id: '1', title: 'Monthly', description: 'Summary', updated: 'Today' }
      ]
    });
    render(<ReportsSection />);
    expect(screen.getByText(/Monthly/i)).toBeInTheDocument();
  });
});
