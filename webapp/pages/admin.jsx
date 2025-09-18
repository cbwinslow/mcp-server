import Layout from '../components/Layout';
import { useEffect, useState, useRef } from 'react';
import { apiPost, apiGet, apiStream } from '../lib/api';

export default function Admin() {
  const [units, setUnits] = useState([]);
  const [status, setStatus] = useState({});
  const [out, setOut] = useState('');
  const [kvKeys, setKvKeys] = useState([]);
  const [kvFilter, setKvFilter] = useState('');
  const [kvView, setKvView] = useState({ key: '', value: '' });
  const [ent, setEnt] = useState({ repos: true, files: false, chunks: false, embeddings: false });
  const [dryRun, setDryRun] = useState(true);
  const [limit, setLimit] = useState(1000);
  const [streaming, setStreaming] = useState(false);
  const [streamLog, setStreamLog] = useState('');
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const [lastSummary, setLastSummary] = useState(null);
  const [detailed, setDetailed] = useState(()=> (typeof window!=='undefined' && localStorage.getItem('admin_stream_detailed')==='1'));
  const [valReport, setValReport] = useState(null);
  const [logs, setLogs] = useState([]);
  const [logFilter, setLogFilter] = useState('');
  const [logsAuto, setLogsAuto] = useState(false);
  const [lastSeq, setLastSeq] = useState(0);
  const [reports, setReports] = useState([]);
  const [reportView, setReportView] = useState({ name: '', content: '' });
  const [logView, setLogView] = useState('json'); // 'json' | 'table'
  const logsBoxRef = useRef(null);
  const streamBoxRef = useRef(null);
  const [lastVal, setLastVal] = useState(null);

  useEffect(()=>{
    if (logsBoxRef.current) {
      logsBoxRef.current.scrollTop = logsBoxRef.current.scrollHeight;
    }
  }, [logs]);
  useEffect(()=>{
    if (streamBoxRef.current) {
      streamBoxRef.current.scrollTop = streamBoxRef.current.scrollHeight;
    }
  }, [streamLog]);

  function colorForEvent(ev) {
    if (!ev) return '#334155';
    if (ev.includes('error')) return '#dc2626';
    const map = {
      connectivity_test: '#0ea5e9',
      graph_test: '#22c55e',
      migration_v2_run: '#eab308',
      migration_v2_stream_start: '#a78bfa',
      services_action: '#f97316',
      settings_updated: '#2dd4bf',
    };
    return map[ev] || '#334155';
  }
  useEffect(()=>{
    let t;
    if (logsAuto) {
      t = setInterval(async ()=>{
        try {
          const r = await apiGet(`/admin/logs?limit=200&after_seq=${lastSeq}${logFilter?`&event=${encodeURIComponent(logFilter)}`:''}`);
          if (r.logs && r.logs.length) {
            setLogs(list => list.concat(r.logs));
            setLastSeq(r.max_seq || lastSeq);
          }
        } catch {}
      }, 5000);
    }
    return ()=> t && clearInterval(t);
  }, [logsAuto, lastSeq, logFilter]);

  useEffect(() => {
    (async () => {
      try {
        const s = await apiGet('/admin/settings');
        const allowed = s.settings?.admin?.allowed_units || [];
        setUnits(allowed);
        const st = await apiPost('/admin/services/status', { units: allowed });
        setStatus(st.services || {});
        try { const lv = await apiGet('/admin/validation/last'); setLastVal(lv); } catch {}
      } catch (e) {}
    })();
  }, []);

  async function act(u, action) {
    const r = await apiPost('/admin/services/action', { unit: u, action });
    const st = await apiPost('/admin/services/status', { units });
    setStatus(st.services || {});
  }
  async function restartAll() {
    for (const u of units) {
      try { await apiPost('/admin/services/action', { unit: u, action: 'restart' }); } catch (e) {}
    }
    const st = await apiPost('/admin/services/status', { units });
    setStatus(st.services || {});
  }
  async function initSchema() {
    const r = await apiPost('/admin/terminus/init-schema', {}); setOut(r.stdout || JSON.stringify(r));
  }
  async function migrate() {
    const r = await apiPost('/admin/migrate/pg-to-terminus', {}); setOut(r.stdout || JSON.stringify(r));
  }
  async function validate() {
    const r = await apiPost('/admin/validate', {});
    setOut(JSON.stringify(r, null, 2));
    setValReport(r.report || r);
  }

  return (
    <Layout active="/admin">
      <div className="grid">
        {units.map(u => (
          <div className="card" key={u}>
            <h3>{u}</h3>
            <div>Active: {status[u]?.active || status[u]?.error || 'unknown'}</div>
            <div className="row">
              <button className="btn" onClick={()=>act(u,'start')}>Start</button>
              <button className="btn secondary" onClick={()=>act(u,'stop')}>Stop</button>
              <button className="btn" onClick={()=>act(u,'restart')}>Restart</button>
            </div>
          </div>
        ))}
        <div className="card">
          <h3>Validation Status</h3>
          {lastVal && lastVal.latest ? (
            <>
              <div className="row">
                <span className="badge" style={{background:'#0ea5e9'}}>Latest: {lastVal.latest.score ?? 'N/A'}</span>
                {lastVal.previous && lastVal.previous.score != null && lastVal.latest.score != null && (
                  <span className="badge" style={{background: (lastVal.latest.score - lastVal.previous.score)>=0? '#22c55e':'#dc2626'}}>
                    Δ {((lastVal.latest.score - lastVal.previous.score)>=0? '+':'')}{(lastVal.latest.score - lastVal.previous.score)}
                  </span>
                )}
              </div>
              <small>Updated: {new Date(lastVal.latest.modified).toLocaleString()}</small>
            </>
          ) : (<div>No validation reports found.</div>)}
        </div>
      </div>
      <div className="card" style={{marginTop:16}}>
        <h3>Backends Admin</h3>
        <div className="row">
          <button className="btn" onClick={initSchema}>Init TerminusDB Schema</button>
          <button className="btn secondary" onClick={migrate}>Migrate Repos → TerminusDB</button>
          <button className="btn" onClick={validate}>Run Validation</button>
          <button className="btn secondary" onClick={restartAll}>Restart All Allowed Services</button>
          <button className="btn secondary" onClick={async()=>{ try { const r = await apiPost('/admin/seed/sample', { repos: 5, files_per_repo: 2, chunks_per_file: 2, dry_run: false }); alert(`Seeded: ${JSON.stringify(r.inserted||r)}`); } catch(e){ alert('Seed failed: '+e);} }}>Seed Sample Data</button>
          <button className="btn secondary" onClick={async()=>{ try { const r = await apiPost('/admin/seed/clear', {}); alert(`Cleared: ${JSON.stringify(r.deleted||r)}`); } catch(e){ alert('Clear failed: '+e);} }}>Clear Sample Data</button>
        </div>
        <pre className="monospace">{out}</pre>
      </div>

      <div className="card" style={{marginTop:16}}>
        <h3>Migration v2 (PG → TerminusDB)</h3>
        <div className="row" style={{gap:12}}>
          {['repos','files','chunks','embeddings'].map(k=> (
            <label key={k}><input type="checkbox" checked={ent[k]} onChange={e=> setEnt(v=>({...v, [k]: e.target.checked}))}/> {k}</label>
          ))}
          <label>Limit <input className="input" type="number" value={limit} onChange={e=>setLimit(Number(e.target.value))} /></label>
          <label>Dry-run <input type="checkbox" checked={dryRun} onChange={e=>setDryRun(e.target.checked)} /></label>
          <button className="btn" onClick={async ()=>{
            const entities = Object.keys(ent).filter(k=>ent[k]);
            try {
              const r = await apiPost('/admin/migrate/pg-to-terminus-v2', { entities, limit, dry_run: dryRun });
              setOut(JSON.stringify(r.summary || r, null, 2));
            } catch(e){ alert('Migration v2 failed: '+e); }
          }}>Run</button>
          <button className="btn secondary" disabled={streaming} onClick={async ()=>{
            const entities = Object.keys(ent).filter(k=>ent[k]).join(',');
            setStreamLog(''); setStreaming(true);
            setProgress({ done: 0, total: 0 });
            try {
              await apiStream(`/admin/migrate/pg-to-terminus-v2/stream?entities=${encodeURIComponent(entities)}&limit=${limit}&dry_run=${dryRun}`, (evt)=>{
                let line = '';
                if (detailed) {
                  line = JSON.stringify(evt);
                } else if (evt.phase === 'start') {
                  line = `Start: entities=${(evt.entities||[]).join(', ')} limit=${evt.limit} dry_run=${evt.dry_run}`;
                  const totals = (evt.totals||[]).reduce((a,b)=> a + (b.total||0), 0);
                  setProgress({ done: 0, total: totals });
                } else if (evt.phase === 'entity_done') {
                  const r = evt.result || {};
                  const mig = (r.migrated!=null) ? r.migrated : r.would_write;
                  const tot = (r.total!=null) ? `/${r.total}` : '';
                  line = `Done: ${evt.entity} -> ${mig}${tot}${r.dry_run? ' (dry-run)':''}`;
                  setProgress(p => ({ done: Math.min((p.done + (r.migrated||r.would_write||0)), (p.total||Infinity)), total: p.total }));
                } else if (evt.phase === 'done') {
                  const total = (evt.summary?.results||[]).reduce((a,b)=> a + (b.migrated||b.would_write||0), 0);
                  line = `All done. Total items: ${total}`;
                  setLastSummary(evt.summary || null);
                } else if (evt.phase === 'error') {
                  line = `ERROR: ${evt.entity}: ${evt.error}`;
                }
                setStreamLog(l => l + line + '\n');
                if (evt.phase === 'done') setStreaming(false);
              });
            } catch(e) { setStreamLog(l => l + `ERROR: ${e}\n`); setStreaming(false);} 
          }}>Run Live</button>
          <label style={{marginLeft:8}}><input type="checkbox" checked={detailed} onChange={e=>setDetailed(e.target.checked)} /> Detailed stream</label>
        </div>
        {progress.total > 0 && (
          <div style={{marginTop:8}}>
            <div style={{height:8, background:'#1f2937', borderRadius:4}}>
              <div style={{height:8, width: `${Math.min(100, Math.round(100*progress.done/progress.total))}%`, background:'#22c55e', borderRadius:4}}></div>
            </div>
            <div style={{fontSize:12, opacity:0.8, marginTop:4}}>{progress.done} / {progress.total} items</div>
          </div>
        )}
        <pre ref={streamBoxRef} className="monospace" style={{maxHeight:200, overflowY:'auto'}}>{streamLog}</pre>
        <div className="row" style={{gap:8}}>
          <button className="btn secondary" onClick={()=> setStreamLog('')}>Clear</button>
          <button className="btn secondary" disabled={!lastSummary} onClick={()=>{
            const blob = new Blob([JSON.stringify(lastSummary, null, 2)], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href = url; a.download = 'migration-summary.json'; a.click(); URL.revokeObjectURL(url);
          }}>Download Summary</button>
        </div>
      </div>
      {valReport && (
        <div className="card" style={{marginTop:16}}>
          <h3>Validation Results</h3>
          <div className="row" style={{justifyContent:'space-between'}}>
            <div>Score: <b>{valReport.score}</b></div>
            <div>
              <button className="btn secondary" onClick={()=>{
                const blob = new Blob([JSON.stringify(valReport, null, 2)], {type:'application/json'});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a'); a.href = url; a.download = 'validation-report.json'; a.click(); URL.revokeObjectURL(url);
              }}>Download JSON</button>
              <button className="btn secondary" style={{marginLeft:8}} onClick={()=>{
                const issues = valReport.issues || [];
                const header = ['type','entity','field','postgres','graph','count'];
                const rows = [header.join(',')].concat(issues.map(i=>[
                  i.type||'', i.entity||'', i.field||'', i.postgres??'', i.graph??'', i.count??''
                ].join(',')));
                const blob = new Blob([rows.join('\n')], {type:'text/csv'});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a'); a.href = url; a.download = 'validation-issues.csv'; a.click(); URL.revokeObjectURL(url);
              }}>Download CSV</button>
            </div>
          </div>
          <p style={{opacity:0.85, marginTop:8}}>{valReport.summary}</p>
          <div style={{overflowX:'auto', marginTop:8}}>
            <table className="monospace" style={{width:'100%'}}>
              <thead>
                <tr>
                  <th align="left">Type</th>
                  <th align="left">Entity</th>
                  <th align="left">Field</th>
                  <th align="right">Postgres</th>
                  <th align="right">Graph</th>
                  <th align="right">Count</th>
                </tr>
              </thead>
              <tbody>
                {(valReport.issues||[]).map((i,idx)=> (
                  <tr key={idx}>
                    <td>{i.type}</td>
                    <td>{i.entity||''}</td>
                    <td>{i.field||''}</td>
                    <td align="right">{i.postgres??''}</td>
                    <td align="right">{i.graph??''}</td>
                    <td align="right">{i.count??''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="card" style={{marginTop:16}}>
        <h3>Audit Logs</h3>
        <div className="row" style={{gap:8, flexWrap:'wrap'}}>
          {[ 'connectivity_test', 'graph_test', 'migration_v2_run', 'migration_v2_stream_start', 'services_action', 'settings_updated' ].map(ev => (
            <button key={ev} className="btn secondary" onClick={()=> setLogFilter(ev)}>{ev}</button>
          ))}
          <button className="btn secondary" onClick={()=> setLogFilter('')}>Clear Filter</button>
        </div>
        <div className="row">
          <input className="input" placeholder="Filter by event substring" value={logFilter} onChange={e=>setLogFilter(e.target.value)} />
          <label><input type="checkbox" checked={logsAuto} onChange={e=> setLogsAuto(e.target.checked)} /> Auto-refresh</label>
          <button className="btn" onClick={async()=>{
            try { const r = await apiGet(`/admin/logs?limit=250${logFilter?`&event=${encodeURIComponent(logFilter)}`:''}`); setLogs(r.logs||[]); setLastSeq(r.max_seq||0); }
            catch(e){ alert('Fetch logs failed: '+e); }
          }}>Refresh</button>
          <button className="btn secondary" onClick={()=>{
            const blob = new Blob([JSON.stringify(logs, null, 2)], {type:'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href = url; a.download = 'audit-logs.json'; a.click(); URL.revokeObjectURL(url);
          }}>Download JSON</button>
          <button className="btn secondary" onClick={()=>{
            const header = ['ts','seq','request_id','user_id','role','event','data'];
            const rows = [header.join(',')].concat(
              logs.map(e=> [e.ts, e.seq, e.request_id||'', e.user_id||'', e.role||'', e.event||'', JSON.stringify(e.data||{})].join(','))
            );
            const blob = new Blob([rows.join('\n')], {type:'text/csv'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href = url; a.download = 'audit-logs.csv'; a.click(); URL.revokeObjectURL(url);
          }}>Download CSV</button>
          <label style={{marginLeft:8}}>
            View:
            <select className="input" value={logView} onChange={e=>setLogView(e.target.value)}>
              <option value="json">JSON</option>
              <option value="table">Table</option>
            </select>
          </label>
        </div>
        {logView==='json' ? (
          <pre ref={logsBoxRef} className="monospace" style={{maxHeight:240, overflowY:'auto'}}>{JSON.stringify(logs, null, 2)}</pre>
        ) : (
          <div style={{overflowX:'auto'}}>
            <table className="monospace" style={{width:'100%'}}>
              <thead>
                <tr>
                  <th align="left">Time</th>
                  <th align="left">Event</th>
                  <th align="left">User</th>
                  <th align="left">Role</th>
                  <th align="left">ReqID</th>
                  <th align="left">Data</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((e,idx)=> (
                  <tr key={idx}>
                    <td>{e.ts}</td>
                    <td><span style={{background: colorForEvent(e.event), color:'#0b1220', padding:'2px 6px', borderRadius:6}}>{e.event}</span></td>
                    <td>{e.user_id||''}</td>
                    <td>{e.role||''}</td>
                    <td>{e.request_id||''}</td>
                    <td style={{maxWidth:420, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis'}}>{JSON.stringify(e.data||{})}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card" style={{marginTop:16}}>
        <h3>Validation Reports</h3>
        <div className="row">
          <button className="btn" onClick={async()=>{ try { const r = await apiGet('/admin/validation/reports?limit=10'); setReports(r.files||[]);} catch(e){ alert('List reports failed: '+e);} }}>Refresh</button>
        </div>
        <div className="row" style={{gap:16}}>
          <div style={{flex:1}}>
            <ul className="monospace" style={{maxHeight:200, overflowY:'auto', background:'#111', padding:8}}>
              {reports.map(f => (
                <li key={f.name} className="row" style={{justifyContent:'space-between'}}>
                  <span>{f.name} <small>({(f.size||0)} bytes)</small></span>
                  <span className="row">
                    <button className="btn secondary" onClick={async()=>{ try { const t = await apiGet(`/admin/validation/reports/${encodeURIComponent(f.name)}`); setReportView({ name: f.name, content: JSON.stringify(t, null, 2) }); } catch(e){ alert('Open failed: '+e); } }}>Open</button>
                    <button className="btn secondary" onClick={async()=>{
                      try {
                        const res = await fetch(`${API_BASE}/admin/validation/reports/${encodeURIComponent(f.name)}`, { headers: await (async()=>{ const h = {}; const t = localStorage.getItem('mcp_jwt'); if (t) h['Authorization'] = `Bearer ${t}`; return h; })() });
                        const blob = await res.blob();
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a'); a.href = url; a.download = f.name; a.click(); URL.revokeObjectURL(url);
                      } catch(e) { alert('Download failed: '+e); }
                    }}>Download</button>
                  </span>
                </li>
              ))}
            </ul>
          </div>
          <div style={{flex:2}}>
            <h4>{reportView.name}</h4>
            <pre className="monospace" style={{minHeight:180, maxHeight:240, overflowY:'auto'}}>{reportView.content}</pre>
          </div>
        </div>
      </div>

      <div className="card" style={{marginTop:16}}>
        <h3>Cloudflare KV (read-only viewer)</h3>
        <div className="row">
          <input className="input" placeholder="Prefix filter (optional)" value={kvFilter} onChange={e=>setKvFilter(e.target.value)} />
          <button className="btn" onClick={async ()=>{
            try {
              const res = await apiGet(`/admin/kv/list${kvFilter?`?prefix=${encodeURIComponent(kvFilter)}`:''}`);
              setKvKeys(res.keys || []);
            } catch(e) { alert('KV list failed: '+e); }
          }}>List Keys</button>
        </div>
        <div className="row" style={{gap:16}}>
          <div style={{flex:1}}>
            <ul className="monospace" style={{maxHeight:200,overflowY:'auto',background:'#111',padding:8}}>
              {kvKeys.map(k=> (
                <li key={k}><a href="#" onClick={async (e)=>{e.preventDefault(); try{ const r = await apiGet(`/admin/kv?keys=${encodeURIComponent(k)}`); setKvView({ key:k, value: r.values?.[k]||'' }); } catch(e){ alert('KV get failed: '+e); } }}>{k}</a></li>
              ))}
            </ul>
          </div>
          <div style={{flex:2}}>
            <h4>{kvView.key}</h4>
            <pre className="monospace" style={{minHeight:120}}>{kvView.value}</pre>
          </div>
        </div>
      </div>
    </Layout>
  );
}
