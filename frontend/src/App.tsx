import { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, ArrowDownRight, ArrowRight, ArrowUpRight, BarChart3, Building2, CheckCircle2, CircleAlert, Clock3, Database, ExternalLink, Filter, GitBranch, Layers3, LoaderCircle, MapPin, RefreshCw, Search, ShieldCheck, ListOrdered, Route, Users } from 'lucide-react';
import MapView from './MapView';
import AdminControls from './AdminControls';
import { getComplaints, getStats, getPriorities, getAllocation, import311 } from './api';
import type { Complaint, Stats, PriorityPage, AllocationResult } from './types';

const BOROUGHS = ['ALL', 'MANHATTAN', 'BROOKLYN', 'QUEENS', 'BRONX', 'STATEN ISLAND'];
const STATUSES = ['ALL', 'Open', 'Closed', 'In Progress'];
const shortDate = (d: string) => new Date(d).toLocaleDateString('en-US', {month:'short', day:'numeric', year:'numeric'});
const fmt = (n: number) => new Intl.NumberFormat('en-US').format(n);
function badgeStatus(status: string) {
  const closed = ['closed','resolved'].includes(status.toLowerCase());
  return <span className={`status ${closed ? 'status-closed' : 'status-open'}`}><span className="status-dot"/>{status}</span>;
}
function metricChange(label: string) {return <span className="metric-detail">{label}</span>;}

function DataTable({items, loading}: {items: Complaint[]; loading: boolean}) {
  return <div className="table-scroll">
    <table className="data-table"><thead><tr><th>REQUEST / ISSUE</th><th>BOROUGH</th><th>DATE REPORTED</th><th>STATUS</th><th>DATA</th></tr></thead>
      <tbody>
        {items.map(c => <tr key={c.source_id}><td><div className="issue-name">{c.complaint_type}</div><div className="issue-desc">{c.descriptor || 'No additional detail'} · #{c.source_id}</div></td>
          <td>{c.borough.toLowerCase().replace(/\b\w/g, ch => ch.toUpperCase())}</td><td>{shortDate(c.created_at)}</td><td>{badgeStatus(c.status)}</td>
          <td><span className={`source-pill ${c.source === 'demo' ? 'source-demo' : 'source-real'}`}>{c.source === 'demo' ? 'DEMO' : 'NYC 311'}</span></td></tr>)}
        {items.length === 0 && <tr><td className="empty-row" colSpan={5}>{loading ? 'Loading service requests…' : 'No matching requests. Adjust your filters.'}</td></tr>}
      </tbody>
    </table>
  </div>;
}

export default function App() {
  const [borough, setBorough] = useState('ALL');
  const [status, setStatus] = useState('ALL');
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [items, setItems] = useState<Complaint[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [version, setVersion] = useState(0);
  const [activeView, setActiveView] = useState<'overview' | 'requests' | 'priorities' | 'allocation'>('overview');
  const [priorities, setPriorities] = useState<PriorityPage | null>(null);
  const [includeDemo, setIncludeDemo] = useState(false);
  const [crewCount, setCrewCount] = useState(8);
  const [candidateLimit, setCandidateLimit] = useState(60);
  const [allocation, setAllocation] = useState<AllocationResult | null>(null);
  const [page, setPage] = useState(1);

  useEffect(() => {const timer = setTimeout(() => { setQuery(search); setPage(1); }, 300); return () => clearTimeout(timer);}, [search]);
  const filterQuery = useMemo(() => {const p = new URLSearchParams(); if (borough !== 'ALL') p.set('borough', borough); if (status !== 'ALL') p.set('status', status); if (query.trim()) p.set('q',query.trim()); return p;}, [borough,status,query]);
  useEffect(() => {let active = true; setLoading(true); setError(''); const params = new URLSearchParams(filterQuery); params.set('page',String(page)); params.set('page_size','100');
    const priorityParams = new URLSearchParams(filterQuery); priorityParams.delete('status'); priorityParams.set('limit','10');
    if (includeDemo) priorityParams.set('include_demo','true');
    const allocationParams = new URLSearchParams(priorityParams);
    allocationParams.delete('limit');
    allocationParams.set('crew_count',String(crewCount));
    allocationParams.set('candidate_limit',String(candidateLimit));
    Promise.all([getComplaints(params), getStats(filterQuery), getPriorities(priorityParams), getAllocation(allocationParams)]).then(([list, stats, ranks, alloc]) => {
      if(!active) return; setItems(list.items); setTotal(list.total); setStats(stats); setPriorities(ranks); setAllocation(alloc);
    }).catch(err => {if(active) setError(err instanceof Error ? err.message : 'Unable to reach API');}).finally(() => {if(active) setLoading(false);});
    return () => {active = false;};
  }, [filterQuery, page, version, includeDemo, crewCount, candidateLimit]);

  const sync = useCallback(async () => {setSyncing(true); setNotice(''); setError(''); try {const r = await import311(); setNotice(`NYC 311 sync complete: ${fmt(r.inserted)} new records added (${fmt(r.fetched)} fetched).`); setPage(1); setVersion(v => v+1);} catch (e) {setError(e instanceof Error ? e.message : 'Import failed');} finally {setSyncing(false);}}, []);
  const counts = stats || {total:0,open:0,closed:0,demo:0,by_category:[],by_borough:[]};
  const maxCategory = Math.max(1,...counts.by_category.map(x=>x.count));
  const sampleOnly = counts.total > 0 && counts.demo === counts.total;
  const hasReal = counts.total > counts.demo;

  return <div className="shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-icon"><Layers3 size={22} strokeWidth={2.1}/></div><div><span className="brand-name">cityos<span className="brand-suffix">/</span></span><span className="brand-caption">OPERATIONS INTELLIGENCE</span></div></div>
      <div className="workspace-label">WORKSPACE</div>
      <nav className="side-nav">
        <button className={`nav-link ${activeView==='overview'?'active':''}`} onClick={()=>setActiveView('overview')}><BarChart3 size={17}/> Overview <span className="nav-chevron">›</span></button>
        <button className={`nav-link ${activeView==='requests'?'active':''}`} onClick={()=>{setActiveView('requests'); document.getElementById('requests')?.scrollIntoView({behavior:'smooth'});}}><Database size={17}/> Service requests</button>
        <button className={`nav-link ${activeView==='priorities'?'active':''}`} onClick={()=>{setActiveView('priorities'); document.getElementById('priorities')?.scrollIntoView({behavior:'smooth'});}}><ListOrdered size={17}/> Priority queue</button>
        <button className={`nav-link ${activeView==='allocation'?'active':''}`} onClick={()=>{setActiveView('allocation'); document.getElementById('allocation')?.scrollIntoView({behavior:'smooth'});}}><Route size={17}/> Crew allocation</button>
      </nav>
      <div className="workspace-label lower-label">DATA SOURCES</div>
      <div className="sidebar-source"><span className={`source-indicator ${hasReal?'live':''}`}/><div><b>NYC Open Data</b><small>{hasReal ? 'Public 311 records loaded' : 'Demo records loaded'}</small></div></div>
      <div className="sidebar-bottom"><div className="sidebar-tip"><ShieldCheck size={17}/><p><strong>Designed for decisions</strong><span>Build visibility before automation.</span></p></div><div className="version">CITYOS / MVP 0.4.0</div></div>
    </aside>
    <main className="main">
      <header className="topbar"><div className="breadcrumbs">Workspace <span>/</span> <b>Service operations</b></div><div className="topbar-right"><span className="topbar-status"><span className="mini-dot"/> {sampleOnly?'Demo workspace':hasReal?'NYC 311 connected':'Loading data'}</span><div className="avatar">CO</div></div></header>
      <div className="content">
        <div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/> CITY OPERATIONS / NEW YORK</div><h1>Service intelligence<span className="heading-dot">.</span></h1><p className="subtitle">A clearer view of the requests, patterns, and priorities shaping a city.</p></div>
          <AdminControls onSync={sync} syncing={syncing}/>
        </div>
        {error && <div className="alert alert-error"><CircleAlert size={18}/><span>{error}</span><button onClick={()=>setError('')}>Dismiss</button></div>}
        {notice && <div className="alert alert-success"><CheckCircle2 size={18}/><span>{notice}</span><button onClick={()=>setNotice('')}>Dismiss</button></div>}
        <div className="data-notice"><div className="notice-icon"><Database size={17}/></div><span>{sampleOnly ? <><strong>Demo environment.</strong> These records are fictional examples. {'Log in as admin to refresh public data, or wait for the next server refresh.'}</> : <><strong>Data provenance:</strong> {fmt(counts.demo)} demo records, {fmt(counts.total-counts.demo)} imported NYC 311 records in the current filter. Demo records are always labeled.</>}</span><a href="https://data.cityofnewyork.us/d/erm2-nwe9" target="_blank" rel="noreferrer">Dataset <ExternalLink size={13}/></a></div>
        <div className="section-row"><h2>At a glance</h2><div className="refreshed"><Clock3 size={14}/> Stored records · not live dispatch data</div></div>
        <div className="metric-grid">
          <div className="metric-card"><div className="metric-top"><span>Total requests</span><div className="icon-soft green"><Layers3 size={17}/></div></div><div className="metric-number">{fmt(counts.total)}</div>{metricChange('Matching current filters')}<div className="metric-accent"/></div>
          <div className="metric-card"><div className="metric-top"><span>Unresolved</span><div className="icon-soft orange"><CircleAlert size={17}/></div></div><div className="metric-number">{fmt(counts.open)}</div>{metricChange(counts.total?`${Math.round(100*counts.open/counts.total)}% of filtered requests`:'No requests') }<div className="metric-accent warm"/></div>
          <div className="metric-card"><div className="metric-top"><span>Closed</span><div className="icon-soft blue"><CheckCircle2 size={17}/></div></div><div className="metric-number">{fmt(counts.closed)}</div>{metricChange(counts.total?`${Math.round(100*counts.closed/counts.total)}% of filtered requests`:'No requests')}<div className="metric-accent cool"/></div>
          <div className="metric-card"><div className="metric-top"><span>Active boroughs</span><div className="icon-soft purple"><Building2 size={17}/></div></div><div className="metric-number">{counts.by_borough.length}</div>{metricChange('With matching requests')}<div className="metric-accent violet"/></div>
        </div>
        <div className="main-grid">
          <section className="panel map-panel"><div className="panel-heading"><div><div className="panel-eyebrow">GEOGRAPHIC OVERVIEW</div><h3>Request distribution</h3></div><span className="subtle-chip"><MapPin size={13}/> NYC</span></div><div className="map-container"><MapView items={items}/><div className="map-legend"><span><i className="legend-dot unresolved"/> Unresolved</span><span><i className="legend-dot resolved"/> Closed</span></div></div><div className="panel-foot">Showing mapped locations for up to 100 records on this page. <span>{fmt(items.filter(c=>c.latitude!==null&&c.longitude!==null).length)} points visible</span></div></section>
          <section className="panel trends-panel"><div className="panel-heading"><div><div className="panel-eyebrow">CATEGORY BREAKDOWN</div><h3>Top request types</h3></div><div className="tiny-icon"><Activity size={18}/></div></div>
            <div className="bar-list">{counts.by_category.map((cat,i)=><div className="bar-item" key={cat.label}><div className="bar-row"><span className="bar-index">{String(i+1).padStart(2,'0')}</span><span className="bar-name" title={cat.label}>{cat.label}</span><span className="bar-count">{fmt(cat.count)}</span></div><div className="bar-track"><div className="bar-fill" style={{width:`${100*cat.count/maxCategory}%`}}/></div></div>)}{!counts.by_category.length&&<p className="no-categories">No requests found.</p>}</div>
            <div className="panel-foot muted">Counts reflect current filters, not citywide totals. <ArrowUpRight size={15}/></div></section>
        </div>
        <section className="panel priority-panel" id="priorities" aria-label="Prototype priority queue">
          <div className="panel-heading priority-heading">
            <div><div className="panel-eyebrow">EXPLAINABLE DECISION SUPPORT / PROTOTYPE</div><h3>Priority queue <span className="inline-count">{fmt(priorities?.total ?? 0)} unresolved</span></h3></div>
            <label className="demo-toggle"><input type="checkbox" checked={includeDemo} onChange={e=>setIncludeDemo(e.target.checked)}/> Include fictional demo data</label>
          </div>
          <div className="priority-disclaimer"><ShieldCheck size={17}/><span><strong>Experimental ranking, not emergency triage.</strong> Weights are student-defined and do not represent NYC policy or actual safety severity. Rankings use the borough and text filters above but always show unresolved requests, regardless of the status filter. The list uses records stored in CityOS, not all NYC requests.</span></div>
          <div className="priority-list">
            {priorities?.items.map((c,index) => <div className="priority-item" key={c.source_id}>
              <div className="priority-rank">{String(index+1).padStart(2,'0')}</div>
              <div className="priority-main"><div className="priority-item-title">{c.complaint_type} <span className={`priority-band priority-${c.band}`}>{c.band.toUpperCase()}</span></div>
                <div className="priority-meta">{c.borough} · {c.age_days} days since report · {c.status} · <span className={c.source === 'demo' ? 'priority-demo' : ''}>{c.source === 'demo' ? 'DEMO' : 'NYC 311'}</span></div>
                <details className="priority-details"><summary>Why this score?</summary><p>{c.explanation}</p><p>Category: {c.category_points} + age: {c.age_points} = <strong>{c.score} points</strong>.</p></details>
              </div>
              <div className="priority-score"><strong>{c.score}<small>/100</small></strong><span>REVIEW SCORE</span></div>
            </div>)}
            {priorities && priorities.items.length === 0 && <div className="priority-empty">{loading ? 'Loading rankings…' : 'No matching unresolved NYC 311 records. Sync more records or enable the demo toggle.'}</div>}
            {!priorities && <div className="priority-empty">Loading rankings…</div>}
          </div>
          <div className="priority-footer"><span>Rule: category points (20–60) + reported-age points (5/day, max 40). Higher scores appear first.</span><span>{priorities?.as_of ? `Calculated as of ${priorities.as_of} UTC` : ''}</span></div>
        </section>
        <section className="panel allocation-panel" id="allocation" aria-label="Fictional crew allocation simulation">
          <div className="panel-heading allocation-heading">
            <div><div className="panel-eyebrow">OPTIMIZATION LAB / EDUCATIONAL SIMULATION</div><h3>Crew allocation <span className="inline-count">matching vs. FIFO</span></h3></div>
            <div className="allocation-controls">
              <label>CREWS <select aria-label="Fictional crew count" value={crewCount} onChange={e=>setCrewCount(Number(e.target.value))}><option value={4}>4</option><option value={6}>6</option><option value={8}>8</option></select></label>
              <label>CANDIDATES <select aria-label="Candidate pool size" value={candidateLimit} onChange={e=>setCandidateLimit(Number(e.target.value))}><option value={30}>30</option><option value={60}>60</option><option value={100}>100</option></select></label>
            </div>
          </div>
          <div className="priority-disclaimer"><ShieldCheck size={17}/><span><strong>Scenario planning only.</strong> The crews, skills, locations and one-job capacity are completely fictional. These are stored NYC 311 reports (unless demo is enabled), not verified dispatch work orders. Distance means straight-line kilometers, not driving distance. No crews are actually dispatched.</span></div>
          {allocation ? <>
            <div className="allocation-context"><Users size={15}/> {allocation.crew_count} fictional crews · {allocation.considered} highest-ranked geocoded requests considered · {allocation.eligible_requests} have at least one eligible crew · {allocation.unmapped_skipped} without coordinates skipped</div>
            <div className="allocation-compare">
              <div className="allocation-result-card">
                <div className="allocation-result-label">OPTIMIZED MATCHING</div>
                <strong>{allocation.optimized.objective.toFixed(1)}</strong>
                <span>objective points (higher is better)</span>
                <div className="allocation-result-detail">{allocation.optimized.assigned_count} assigned · {allocation.optimized.total_priority} priority points · {allocation.optimized.total_distance_km.toFixed(1)} km</div>
              </div>
              <div className="allocation-result-card secondary">
                <div className="allocation-result-label">FIFO BASELINE</div>
                <strong>{allocation.fifo.objective.toFixed(1)}</strong>
                <span>objective points</span>
                <div className="allocation-result-detail">{allocation.fifo.assigned_count} assigned · {allocation.fifo.total_priority} priority points · {allocation.fifo.total_distance_km.toFixed(1)} km</div>
              </div>
            </div>
            <div className="allocation-gain"><BarChart3 size={16}/><b>{allocation.objective_gain >= 0 ? '+' : ''}{allocation.objective_gain.toFixed(1)} objective points</b> compared with FIFO on the same pool. Objective = sum(priority score − straight-line distance in km).</div>
            <div className="allocation-list-heading">RECOMMENDED FICTIONAL ASSIGNMENTS</div>
            <div className="allocation-list">
              {allocation.optimized.assignments.map(a=><div className="allocation-item" key={a.crew_id}>
                <div className="allocation-crew"><span className="allocation-crew-dot"/><b>{a.crew_name}</b><small>{a.crew_id} · {a.service_group}</small></div>
                <div className="allocation-issue"><b>{a.complaint_type}</b><span>{a.borough} · request #{a.source_id} · score {a.priority_score}</span><details className="priority-details"><summary>Why assigned?</summary><p>{a.reason}</p></details></div>
                <div className="allocation-distance"><b>{a.distance_km.toFixed(1)} km</b><small>straight-line</small></div>
              </div>)}
              {allocation.optimized.assignments.length===0 && <div className="priority-empty">No eligible matching requests for this fictional crew setup. Try syncing more data, selecting more crews, or enabling demo entries.</div>}
            </div>
            <div className="priority-footer"><span>Exact maximum-weight matching (dynamic programming) vs oldest-first nearest-eligible FIFO. Both operate on the same top-scored request pool.</span><span>As of {allocation.as_of} UTC</span></div>
          </> : <div className="priority-empty">Loading allocation comparison…</div>}
        </section>
        <section className="panel requests-panel" id="requests"><div className="panel-heading request-heading"><div><div className="panel-eyebrow">SERVICE REQUEST EXPLORER</div><h3>Recent requests <span className="inline-count">{fmt(total)}</span></h3></div><span className="subtle-chip"><Filter size={13}/> Filter records</span></div>
          <div className="filters"><label className="search-wrap"><Search size={17}/><input type="search" aria-label="Search complaints" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search complaint type or detail…"/></label>
            <label className="select-wrap"><span>BOROUGH</span><select aria-label="Filter by borough" value={borough} onChange={e=>{setBorough(e.target.value);setPage(1);}}>{BOROUGHS.map(b=><option key={b} value={b}>{b==='ALL'?'All boroughs':b}</option>)}</select></label>
            <label className="select-wrap"><span>STATUS</span><select aria-label="Filter by status" value={status} onChange={e=>{setStatus(e.target.value);setPage(1);}}>{STATUSES.map(s=><option key={s} value={s}>{s==='ALL'?'All statuses':s}</option>)}</select></label>
          </div>
          <DataTable items={items} loading={loading}/>
          <div className="table-footer"><span>{total===0? '0 results' : `Showing ${(page-1)*100+1}–${Math.min(page*100,total)} of ${fmt(total)} requests`}</span><div className="pagination"><button disabled={page===1||loading} onClick={()=>setPage(p=>p-1)}>Previous</button><span>Page {page}</span><button disabled={page*100>=total||loading} onClick={()=>setPage(p=>p+1)}>Next <ArrowRight size={14}/></button></div></div>
        </section>
        <footer className="footer"><div><span className="footer-brand">cityos/</span> A student-built operational intelligence prototype. Not affiliated with NYC 311.</div><div><GitBranch size={14}/> Full-stack MVP · Data before decisions</div></footer>
      </div>
    </main>
  </div>;
}
