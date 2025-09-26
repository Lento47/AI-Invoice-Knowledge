import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type {
  ApprovalEntry,
  DashboardPayload,
  InvoicePayload,
  ReportEntry,
  VendorEntry
} from '../lib/api';
import {
  ApiError,
  getApprovals,
  getDashboard,
  getInvoice,
  getReports,
  getVendors,
  normaliseErrorDetail,
  submitApprovalDecision
} from '../lib/api';

type QueryStatus = 'idle' | 'loading' | 'success' | 'error';

type ApiQueryState<T> = {
  data: T | null;
  status: QueryStatus;
  error: string | null;
  refresh: () => Promise<T | null>;
  setData: (updater: T | null | ((previous: T | null) => T | null)) => void;
};

type Fetcher<T> = (signal?: AbortSignal) => Promise<T>;

const useApiQuery = <T,>(fetcher: Fetcher<T>): ApiQueryState<T> => {
  const [data, setData] = useState<T | null>(null);
  const [status, setStatus] = useState<QueryStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  const refresh = useCallback(async (): Promise<T | null> => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setStatus('loading');
    setError(null);
    try {
      const result = await fetcher(controller.signal);
      setData(result);
      setStatus('success');
      return result;
    } catch (cause) {
      const message =
        cause instanceof ApiError
          ? cause.message
          : normaliseErrorDetail(cause instanceof Error ? cause.message : cause);
      setError(message);
      setStatus('error');
      return null;
    }
  }, [fetcher]);

  useEffect(() => {
    void refresh();
    return () => {
      controllerRef.current?.abort();
    };
  }, [refresh]);

  return useMemo(
    () => ({
      data,
      status,
      error,
      refresh,
      setData: (updater) => {
        setData((current) =>
          typeof updater === 'function' ? (updater as (previous: T | null) => T | null)(current) : updater
        );
      }
    }),
    [data, status, error, refresh]
  );
};

export const useDashboardData = () => useApiQuery(useCallback((signal?: AbortSignal) => getDashboard(signal), []));

export const useInvoiceData = () => useApiQuery(useCallback((signal?: AbortSignal) => getInvoice(signal), []));

export const useVendorDirectory = () => useApiQuery(useCallback((signal?: AbortSignal) => getVendors(signal), []));

export const useReportsLibrary = () => useApiQuery(useCallback((signal?: AbortSignal) => getReports(signal), []));

export const useApprovalsQueue = () => {
  const query = useApiQuery<ApprovalEntry[]>(useCallback((signal?: AbortSignal) => getApprovals(signal), []));

  const updateStatus = useCallback(
    async (id: string, status: 'Approved' | 'Rejected') => {
      const previous = query.data ? [...query.data] : null;
      query.setData((current) =>
        current?.map((item) => (item.id === id ? { ...item, status } : item)) ?? current
      );
      try {
        const result = await submitApprovalDecision(id, status);
        query.setData((current) =>
          current?.map((item) => (item.id === result.id ? { ...item, status: result.status } : item)) ?? current
        );
        return result;
      } catch (error) {
        query.setData(previous ?? null);
        throw error;
      }
    },
    [query]
  );

  return {
    ...query,
    updateStatus
  };
};

export type DashboardQuery = ReturnType<typeof useDashboardData> & { data: DashboardPayload | null };
export type InvoiceQuery = ReturnType<typeof useInvoiceData> & { data: InvoicePayload | null };
export type VendorQuery = ReturnType<typeof useVendorDirectory> & { data: VendorEntry[] | null };
export type ReportsQuery = ReturnType<typeof useReportsLibrary> & { data: ReportEntry[] | null };
export type ApprovalsQuery = ReturnType<typeof useApprovalsQueue> & { data: ApprovalEntry[] | null };
