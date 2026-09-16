export type ReviewStatus = 'not_started' | 'in_review' | 'approved' | 'needs_attention';
export type Finding = { id: string; category: string; severity: string; title: string; detail: string; evidence: string; document_id: string | null };
export type Document = { id: string; filename: string; document_type: string; content_hash: string; extracted_at: string };
export type Vendor = { id: string; name: string; website: string | null; owner: string | null; review_status: ReviewStatus; review_deadline: string | null; risk_score: number; document_count: number; finding_count: number };
export type VendorDetail = Vendor & { documents: Document[]; findings: Finding[] };
export type QAResponse = { answer: string; citations: { document_id: string; filename: string; quote: string }[]; event_id: string };
const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, { ...options, headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) } });
  if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || 'Request failed');
  return response.json();
}
export const api = {
  vendors: () => request<Vendor[]>('/api/vendors'),
  vendor: (id: string) => request<VendorDetail>(`/api/vendors/${id}`),
  createVendor: (name: string, owner: string) => request<Vendor>('/api/vendors', { method: 'POST', body: JSON.stringify({ name, owner }) }),
  updateVendor: (id: string, payload: Partial<Vendor>) => request<Vendor>(`/api/vendors/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  upload: async (id: string, file: File) => { const body = new FormData(); body.append('file', file); const response = await fetch(`${API}/api/vendors/${id}/documents`, { method: 'POST', body }); if (!response.ok) throw new Error('Upload failed'); return response.json(); },
  ask: (id: string, question: string) => request<QAResponse>(`/api/vendors/${id}/ask`, { method: 'POST', body: JSON.stringify({ question }) }),
};
