import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi, afterEach } from 'vitest';
import { ApprovalsSection } from '../ApprovalsSection';

vi.mock('../../hooks/useWorkspaceData', () => ({
  useApprovalsQueue: vi.fn()
}));

const { useApprovalsQueue } = await import('../../hooks/useWorkspaceData');
const mockUseApprovalsQueue = useApprovalsQueue as unknown as ReturnType<typeof vi.fn>;

const baseState = {
  data: null,
  status: 'idle',
  error: null,
  refresh: vi.fn(),
  setData: vi.fn(),
  updateStatus: vi.fn()
};

describe('ApprovalsSection', () => {
  beforeEach(() => {
    mockUseApprovalsQueue.mockReset();
    mockUseApprovalsQueue.mockReturnValue({ ...baseState });
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('shows loading indicator', () => {
    mockUseApprovalsQueue.mockReturnValue({ ...baseState, status: 'loading' });
    render(<ApprovalsSection />);
    expect(screen.getByText(/Loading approvals queue/i)).toBeInTheDocument();
  });

  it('shows error state with retry', () => {
    const refresh = vi.fn();
    mockUseApprovalsQueue.mockReturnValue({ ...baseState, status: 'error', error: 'boom', refresh });
    render(<ApprovalsSection />);
    expect(screen.getByText(/Unable to load approvals/i)).toBeInTheDocument();
    screen.getByRole('button', { name: /retry/i }).click();
    expect(refresh).toHaveBeenCalled();
  });

  it('renders approvals and handles approve action', async () => {
    const updateStatus = vi.fn().mockResolvedValue({ id: '1', status: 'Approved' });
    mockUseApprovalsQueue.mockReturnValue({
      ...baseState,
      status: 'success',
      updateStatus,
      data: [
        {
          id: '1',
          title: 'Invoice INV-1',
          vendor: 'Vendor A',
          amount: '$100',
          submitted: 'now',
          status: 'Pending'
        }
      ]
    });
    render(<ApprovalsSection />);
    screen.getByRole('button', { name: /approve/i }).click();
    await waitFor(() => expect(updateStatus).toHaveBeenCalled());
    expect(await screen.findByText(/Invoice approved/i)).toBeInTheDocument();
  });

  it('renders mutation error when update fails', async () => {
    const updateStatus = vi.fn().mockRejectedValue(new Error('nope'));
    mockUseApprovalsQueue.mockReturnValue({
      ...baseState,
      status: 'success',
      updateStatus,
      data: [
        {
          id: '1',
          title: 'Invoice INV-1',
          vendor: 'Vendor A',
          amount: '$100',
          submitted: 'now',
          status: 'Pending'
        }
      ]
    });
    render(<ApprovalsSection />);
    screen.getByRole('button', { name: /approve/i }).click();
    await waitFor(() => expect(updateStatus).toHaveBeenCalled());
    expect(await screen.findByText(/Failed to update approval/i)).toBeInTheDocument();
  });
});
