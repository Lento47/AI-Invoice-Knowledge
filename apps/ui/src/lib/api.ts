export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(status: number, message: string, payload: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
  }
}

const STORAGE_KEY = 'ai-invoice-portal.credentials';

type StoredCredentials = {
  apiKey?: string;
  licenseToken?: string;
};

const readCredentials = (): StoredCredentials => {
  if (typeof window === 'undefined' || !window.localStorage) {
    return {};
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as StoredCredentials;
    return {
      apiKey: parsed.apiKey?.trim() || undefined,
      licenseToken: parsed.licenseToken?.trim() || undefined
    };
  } catch {
    return {};
  }
};

export const normaliseErrorDetail = (detail: unknown): string => {
  if (detail == null) return 'Unexpected error.';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => normaliseErrorDetail(item)).filter(Boolean).join('\n');
  }
  if (typeof detail === 'object') {
    if ('detail' in detail) {
      return normaliseErrorDetail((detail as Record<string, unknown>).detail);
    }
    if ('message' in detail) {
      return normaliseErrorDetail((detail as Record<string, unknown>).message);
    }
    if ('msg' in detail) {
      const payload = detail as { loc?: Array<string | number>; msg: unknown };
      const prefix = Array.isArray(payload.loc) ? `${payload.loc.join('.')}: ` : '';
      return `${prefix}${payload.msg}`;
    }
    try {
      return JSON.stringify(detail, null, 2);
    } catch {
      return String(detail);
    }
  }
  return String(detail);
};

export const buildUrl = (path: string): string => {
  const rawBase = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '';
  const trimmedPath = path.trim();

  let effectiveBase = rawBase.trim();

  if (!effectiveBase) {
    const rawAppBase = (import.meta.env.BASE_URL as string | undefined) ?? '';
    const appBase = rawAppBase.trim();
    if (appBase && appBase !== '/') {
      effectiveBase = appBase;
    }
  }

  if (!effectiveBase) {
    const normalisedRelativePath = trimmedPath.replace(/^\/+/, '');
    if (!normalisedRelativePath) {
      return '/';
    }
    return `/${normalisedRelativePath}`;
  }

  const normalisedBase = effectiveBase.replace(/\/+$/, '');
  const normalisedPath = trimmedPath.replace(/^\/+/, '');

  if (!normalisedPath) {
    return normalisedBase || '/';
  }

  return `${normalisedBase}/${normalisedPath}`;
};

type RequestOptions = {
  method?: string;
  headers?: Record<string, string>;
  json?: unknown;
  body?: BodyInit | null;
  signal?: AbortSignal;
};

const request = async <T>(path: string, options: RequestOptions = {}): Promise<T> => {
  const { apiKey, licenseToken } = readCredentials();
  const headers = new Headers(options.headers);
  headers.set('Accept', 'application/json');
  if (apiKey) headers.set('X-API-Key', apiKey);
  if (licenseToken) headers.set('X-License', licenseToken);

  let body = options.body ?? null;
  if (options.json !== undefined) {
    headers.set('Content-Type', 'application/json');
    body = JSON.stringify(options.json);
  }

  const response = await fetch(buildUrl(path), {
    method: options.method ?? (body ? 'POST' : 'GET'),
    headers,
    body,
    signal: options.signal
  });

  if (!response.ok) {
    let payload: unknown = null;
    try {
      const text = await response.text();
      if (text) {
        try {
          payload = JSON.parse(text);
        } catch {
          payload = text;
        }
      }
    } catch {
      payload = null;
    }
    const message = normaliseErrorDetail(payload ?? response.statusText);
    throw new ApiError(response.status, message, payload);
  }

  const contentType = response.headers.get('Content-Type') ?? '';
  if (contentType.includes('application/json')) {
    return (await response.json()) as T;
  }
  return (await response.text()) as unknown as T;
};

export type DashboardPayload = {
  cards: Array<{ label: string; value: string; delta: string; trend: 'up' | 'down' | 'neutral' }>;
  cash_flow: Array<{ day: string; value: number }>;
};

export type InvoicePayload = {
  summary: {
    id: string;
    vendor: string;
    issued_on: string;
    due_on: string;
    amount: string;
    status: string;
    reference: string;
    notes?: string | null;
  };
  line_items: Array<{ id: string; description: string; quantity: number; unit_cost: string; amount: string }>;
};

export type VendorEntry = {
  id: string;
  name: string;
  category: string;
  contact: string;
  status: string;
};

export type ReportEntry = {
  id: string;
  title: string;
  description: string;
  updated: string;
};

export type ApprovalEntry = {
  id: string;
  title: string;
  vendor: string;
  amount: string;
  submitted: string;
  status: 'Pending' | 'Approved' | 'Rejected';
};

export const getDashboard = (signal?: AbortSignal) => request<DashboardPayload>('/workspace/dashboard', { signal });
export const getInvoice = (signal?: AbortSignal) => request<InvoicePayload>('/workspace/invoice', { signal });
export const getVendors = (signal?: AbortSignal) => request<VendorEntry[]>('/workspace/vendors', { signal });
export const getReports = (signal?: AbortSignal) => request<ReportEntry[]>('/workspace/reports', { signal });
export const getApprovals = (signal?: AbortSignal) => request<ApprovalEntry[]>('/workspace/approvals', { signal });

export const submitApprovalDecision = (
  id: string,
  status: 'Approved' | 'Rejected',
  signal?: AbortSignal
) => request<ApprovalEntry>(`/workspace/approvals/${id}`, { method: 'POST', json: { status }, signal });

export const extractInvoice = (file: File, signal?: AbortSignal) => {
  const formData = new FormData();
  formData.append('file', file);
  return request('/invoices/extract', { method: 'POST', body: formData, signal });
};

export const classifyInvoice = (text: string, signal?: AbortSignal) =>
  request('/invoices/classify', { method: 'POST', json: { text }, signal });

export const predictInvoice = (features: Record<string, unknown>, signal?: AbortSignal) =>
  request('/invoices/predict', { method: 'POST', json: { features }, signal });

export const apiClient = {
  getDashboard,
  getInvoice,
  getVendors,
  getReports,
  getApprovals,
  submitApprovalDecision,
  extractInvoice,
  classifyInvoice,
  predictInvoice
};
