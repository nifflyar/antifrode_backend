import type {
  LoginRequest,
  RegisterRequest,
  UserProfile,
  ListUsersResponse,
  UserListItem,
  UpdateUserRequest,
  DashboardSummary,
  RiskTrendResponse,
  RiskConcentrationResponse,
  PassengerListResponse,
  PassengerProfile,
  PassengerTransaction,
  RiskOverrideRequest,
  SuspiciousOperationsResponse,
  UploadListResponse,
  UploadResponse,
  ScoringRunResponse,
  ScoringStatusResponse,
  AuditLogsResponse,
  AuditLogItem,
  RiskBand,
} from "@/types/api";

const BASE = "/api";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (res.status === 401) {
    // Try refreshing token
    const refreshRes = await fetch(`${BASE}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });
    if (refreshRes.ok) {
      // Retry original request
      const retryRes = await fetch(`${BASE}${url}`, {
        ...options,
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...options.headers,
        },
      });
      if (retryRes.ok) {
        if (retryRes.status === 204) return undefined as T;
        return retryRes.json();
      }
    }
    // Refresh also failed — redirect to login
    if (typeof window !== "undefined" && !window.location.pathname.includes("/login")) {
      window.location.href = "/login";
    }
    throw new ApiError(401, "Not authenticated");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new ApiError(res.status, body.detail || "API Error");
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

async function requestRaw(url: string, options: RequestInit = {}): Promise<Response> {
  const res = await fetch(`${BASE}${url}`, {
    ...options,
    credentials: "include",
  });
  if (res.status === 401 && typeof window !== "undefined") {
    window.location.href = "/login";
  }
  return res;
}

// ============ Auth ============
export const auth = {
  login: (data: LoginRequest) =>
    request<{ success: boolean }>("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  register: (data: RegisterRequest) =>
    request<{ success: boolean }>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  logout: () =>
    request<{ success: boolean }>("/auth/logout", { method: "POST" }),
  refresh: () =>
    request<{ success: boolean }>("/auth/refresh", { method: "POST" }),
};

// ============ Users ============
export const users = {
  me: () => request<UserProfile>("/users/me"),
  list: (limit = 20, offset = 0) =>
    request<ListUsersResponse>(`/users?limit=${limit}&offset=${offset}`),
  getById: (id: number) => request<UserListItem>(`/users/${id}`),
  update: (id: number, data: UpdateUserRequest) =>
    request<UserListItem>(`/users/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (id: number) =>
    request<void>(`/users/${id}`, { method: "DELETE" }),
};

// ============ Dashboard ============
export const dashboard = {
  summary: () => request<DashboardSummary>("/dashboard/summary"),
  riskTrend: (dateFrom?: string, dateTo?: string) => {
    const params = new URLSearchParams();
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo.includes("T") ? dateTo : `${dateTo}T23:59:59`);
    const qs = params.toString();
    return request<RiskTrendResponse>(`/dashboard/risk-trend${qs ? `?${qs}` : ""}`);
  },
  riskConcentration: (dimensionType: string) =>
    request<RiskConcentrationResponse>(
      `/dashboard/risk-concentration?dimension_type=${dimensionType}`
    ),
};

// ============ Passengers ============
export const passengers = {
  list: (params: { risk_band?: RiskBand; search?: string; limit?: number; offset?: number }) => {
    const qs = new URLSearchParams();
    if (params.risk_band) qs.set("risk_band", params.risk_band);
    if (params.search) qs.set("search", params.search);
    qs.set("limit", String(params.limit ?? 50));
    qs.set("offset", String(params.offset ?? 0));
    return request<PassengerListResponse>(`/passengers?${qs.toString()}`);
  },
  getById: (id: string | number) => request<PassengerProfile>(`/passengers/${id}`),
  transactions: (id: string | number, limit = 50, offset = 0) =>
    request<PassengerTransaction[]>(
      `/passengers/${id}/transactions?limit=${limit}&offset=${offset}`
    ),
  overrideRisk: (id: string | number, data: RiskOverrideRequest) =>
    request<{ status: string }>(`/passengers/${id}/override`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

// ============ Operations ============
export const operations = {
  suspicious: (params: {
    train_no?: string;
    cashdesk?: string;
    terminal?: string;
    date_from?: string;
    date_to?: string;
    limit?: number;
    offset?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params.train_no) qs.set("train_no", params.train_no);
    if (params.cashdesk) qs.set("cashdesk", params.cashdesk);
    if (params.terminal) qs.set("terminal", params.terminal);
    if (params.date_from) qs.set("date_from", params.date_from);
    if (params.date_to) qs.set("date_to", params.date_to.includes("T") ? params.date_to : `${params.date_to}T23:59:59`);
    qs.set("limit", String(params.limit ?? 100));
    qs.set("offset", String(params.offset ?? 0));
    return request<SuspiciousOperationsResponse>(
      `/operations/suspicious?${qs.toString()}`
    );
  },
};

// ============ Uploads ============
export const uploads = {
  list: (limit = 20, offset = 0) =>
    request<UploadListResponse>(`/uploads?limit=${limit}&offset=${offset}`),
  getById: (id: number) => request<UploadResponse>(`/uploads/${id}`),
  uploadExcel: async (file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${BASE}/uploads/excel`, {
      method: "POST",
      body: formData,
      credentials: "include",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Upload failed" }));
      throw new ApiError(res.status, err.detail);
    }
    return res.json();
  },
};

// ============ Scoring ============
export const scoring = {
  run: (uploadId: number) =>
    request<ScoringRunResponse>("/scoring/run", {
      method: "POST",
      body: JSON.stringify({ upload_id: uploadId }),
    }),
  status: (jobId: string) =>
    request<ScoringStatusResponse>(`/scoring/status/${jobId}`),
};

// ============ Reports ============
export const reports = {
  suspiciousExcel: (params?: {
    train_no?: string;
    cashdesk?: string;
    terminal?: string;
    date_from?: string;
    date_to?: string;
  }) => {
    const qs = new URLSearchParams();
    if (params?.train_no) qs.set("train_no", params.train_no);
    if (params?.cashdesk) qs.set("cashdesk", params.cashdesk);
    if (params?.terminal) qs.set("terminal", params.terminal);
    if (params?.date_from) qs.set("date_from", params.date_from);
    if (params?.date_to) qs.set("date_to", params.date_to.includes("T") ? params.date_to : `${params.date_to}T23:59:59`);
    const query = qs.toString();
    return requestRaw(`/reports/operations/suspicious/excel${query ? `?${query}` : ""}`);
  },
  concentrationExcel: () =>
    requestRaw("/reports/risk-concentration/excel"),
  passengerPdf: (passengerId: number) =>
    requestRaw(`/reports/passengers/${passengerId}/pdf`),
};

// ============ Audit ============
export const audit = {
  list: (params?: {
    action?: string;
    user_id?: number;
    entity_type?: string;
    entity_id?: string;
    limit?: number;
    offset?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params?.action) qs.set("action", params.action);
    if (params?.user_id) qs.set("user_id", String(params.user_id));
    if (params?.entity_type) qs.set("entity_type", params.entity_type);
    if (params?.entity_id) qs.set("entity_id", params.entity_id);
    qs.set("limit", String(params?.limit ?? 100));
    qs.set("offset", String(params?.offset ?? 0));
    return request<AuditLogsResponse>(`/audit-logs?${qs.toString()}`);
  },
  getById: (id: string) => request<AuditLogItem>(`/audit-logs/${id}`),
};

// ============ Health ============
export const health = {
  check: () => request<{ status: string }>("/health/"),
};
