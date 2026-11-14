import type { Page, Stats, PriorityPage, AllocationResult, AdminStatus } from './types';

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error((body as {detail?:string}).detail || `Request failed (${response.status})`);
  return body as T;
}
export function getComplaints(params: URLSearchParams) { return json<Page>(`/api/complaints?${params}`); }
export function getStats(params: URLSearchParams) { return json<Stats>(`/api/stats?${params}`); }
export function import311() { return json<{fetched:number;accepted:number;inserted:number}>(`/api/ingest?limit=500`, {method:'POST', headers:{'X-CityOS-Request':'1'}}); }

export function getPriorities(params: URLSearchParams) { return json<PriorityPage>(`/api/priorities?${params}`); }

export function getAllocation(params: URLSearchParams) { return json<AllocationResult>(`/api/allocation?${params}`); }

export function getAdminStatus() { return json<AdminStatus>('/api/admin/status', {cache:'no-store'}); }
export function loginAdmin(password: string) { return json<{authenticated:boolean}>('/api/admin/login', {
  method:'POST', headers:{'Content-Type':'application/json', 'X-CityOS-Request':'1'},
  credentials:'same-origin', body:JSON.stringify({password})
}); }
export function logoutAdmin() { return json<{authenticated:boolean}>('/api/admin/logout', {
  method:'POST', headers:{'X-CityOS-Request':'1'}, credentials:'same-origin'
}); }
