import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { DashboardSection } from '../DashboardSection';

vi.mock('../../hooks/useWorkspaceData', () => ({
  useDashboardData: vi.fn()
}));

const { useDashboardData } = await import('../../hooks/useWorkspaceData');
const mockUseDashboardData = useDashboardData as unknown as ReturnType<typeof vi.fn>;

const baseState = {
  data: null,
  status: 'idle',
  error: null,
  refresh: vi.fn(),
  setData: vi.fn()
};

describe('DashboardSection', () => {
  beforeEach(() => {
    mockUseDashboardData.mockReset();
    mockUseDashboardData.mockReturnValue({ ...baseState });
  });

  it('renders loading state', () => {
    mockUseDashboardData.mockReturnValue({ ...baseState, status: 'loading' });
    render(<DashboardSection />);
    expect(screen.getByText(/Loading analytics/i)).toBeInTheDocument();
  });

  it('renders error state with retry', () => {
    const refresh = vi.fn();
    mockUseDashboardData.mockReturnValue({ ...baseState, status: 'error', error: 'boom', refresh });
    render(<DashboardSection />);
    expect(screen.getByText(/Failed to load analytics/i)).toBeInTheDocument();
    screen.getByRole('button', { name: /retry/i }).click();
    expect(refresh).toHaveBeenCalled();
  });

  it('renders dashboard cards when data is available', () => {
    mockUseDashboardData.mockReturnValue({
      ...baseState,
      status: 'success',
      data: {
        cards: [
          { label: 'Pending Approvals', value: '8', delta: '+2', trend: 'up' as const }
        ],
        cash_flow: [
          { day: 'Mon', value: 10 }
        ]
      }
    });
    render(<DashboardSection />);
    expect(screen.getByText('Pending Approvals')).toBeInTheDocument();
  });
});
