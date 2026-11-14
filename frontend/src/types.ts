export type Complaint = {
  source_id: string; source: 'demo' | 'nyc311'; created_at: string;
  complaint_type: string; descriptor: string; borough: string; status: string;
  latitude: number | null; longitude: number | null;
};
export type Page = { items: Complaint[]; total: number; page: number; page_size: number };
export type Stats = { total: number; open: number; closed: number; demo: number; by_category: {label:string;count:number}[]; by_borough: {label:string;count:number}[] };

export type Priority = Complaint & {
  score: number; band: 'high' | 'medium' | 'low'; age_days: number;
  age_points: number; category_points: number; category_rule: string; explanation: string;
};
export type PriorityPage = {items: Priority[]; total: number; as_of: string; methodology: string};

export type Assignment = {
  crew_id: string; crew_name: string; crew_skills: string[];
  source_id: string; complaint_type: string; borough: string;
  created_at: string; priority_score: number; service_group: string;
  distance_km: number; utility: number; reason: string;
};
export type AllocationMethod = {assigned_count:number; total_priority:number; total_distance_km:number; objective:number; assignments:Assignment[]};
export type AllocationResult = {
  as_of:string; crew_count:number; candidate_limit:number; unresolved_stored:number;
  unmapped_skipped:number; considered:number; eligible_requests:number;
  optimized:AllocationMethod; fifo:AllocationMethod; objective_gain:number; methodology:string;
};

export type AdminStatus = { enabled: boolean; requires_auth: boolean; authenticated: boolean };
