import Layout from '../components/Layout';
import { useEffect, useState } from 'react';
import { apiPost, apiGet } from '../lib/api';
import { listQueries, saveQuery, deleteQuery, exportAll, importAll } from '../lib/storage';
import GraphView from '../components/GraphView';
import dynamic from 'next/dynamic';
import useSWR from 'swr';
import { templates } from '../lib/templates';

export default function Graph() {
  const [backend, setBackend] = useState('terminusdb');
  const { data: insights, mutate } = useSWR(() => `/graph/insights?backend=${backend}`, apiGet);
  const [cypher, setCypher] = useState('MATCH (n) RETURN n LIMIT 5');
  const [result, setResult] = useState(null);
  const [mode, setMode] = useState('read');
  const [viz, setViz] = useState(null);
  const [schema, setSchema] = useState(null);
  const [queryName, setQueryName] = useState('');
  const [queries, setQueries] = useState([]);
  const [colorBy, setColorBy] = useState('label');
  const [search, setSearch] = useState('');
  const [cyRef, setCyRef] = useState(null);
  const [labelFilter, setLabelFilter] = useState('');
  const palette = ['#22c55e','#ef4444','#eab308','#06b6d4','#8b5cf6','#f472b6','#14b8a6'];
  const labels = Array.from(new Set((viz?.nodes||[]).map(n=>n.label||'Node')));
  const colorMap = Object.fromEntries(labels.map((l,i)=>[l, palette[i % palette.length]]));

  async function run() { const r = await apiPost('/graph/query', { query: cypher, mode, backend }); setResult(r); mutate(); }
  async function test() { const r = await apiGet(`/graph/test?backend=${backend}`); alert(JSON.stringify(r)); }
  const [cls, setCls] = useState('');
  async function loadViz() { const r = await apiGet(`/graph/sample?backend=${backend}${backend==='terminusdb'&&cls?`&cls=${encodeURIComponent(cls)}`:''}`); setViz(r.graph); }
  async function expand(id) {
    const r = await apiGet(`/graph/expand?backend=${backend}&node_id=${encodeURIComponent(id)}`);
    if (!viz) return;
    const ids = new Set(viz.nodes.map(n=>String(n.id)));
    const eid = new Set(viz.edges.map(e=>String(e.id)));
    const nodes = [...viz.nodes];
    const edges = [...viz.edges];
    for (const n of (r.graph?.nodes||[])) if (!ids.has(String(n.id))) { nodes.push(n); ids.add(String(n.id)); }
    for (const e of (r.graph?.edges||[])) if (!eid.has(String(e.id))) { edges.push(e); eid.add(String(e.id)); }
    setViz({ nodes, edges });
  }
  function refreshSaved() { setQueries(listQueries(backend)); }
  useEffect(()=>{ refreshSaved(); }, [backend]);
  function onSaveQuery() { if (!queryName) return alert('Name required'); saveQuery(backend, queryName, cypher); setQueryName(''); refreshSaved(); }
  function onDeleteQuery(name) { deleteQuery(backend, name); refreshSaved(); }
  function onRunSaved(q) { setCypher(q.query); }
  function onExportSaved() {
    const blob = new Blob([exportAll()], {type:'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'saved-queries.json'; a.click(); URL.revokeObjectURL(url);
  }
  async function onImportSaved(ev) {
    const f = ev.target.files?.[0]; if (!f) return;
    const txt = await f.text();
    if (!importAll(txt)) { alert('Import failed: invalid JSON'); return; }
    refreshSaved(); alert('Saved queries imported.');
  }

  return (
    <Layout active="/graph">
      <div className="grid">
        <div className="card">
          <h3>Insights</h3>
          <div className="row">
            <select className="input" value={backend} onChange={e=>setBackend(e.target.value)}>
              <option value="terminusdb">TerminusDB</option>
              <option value="neo4j">Neo4j</option>
              <option value="nebula">NebulaGraph</option>
            </select>
            <button className="btn secondary" onClick={test}>Test Connection</button>
            {backend==='terminusdb' && <input className="input" placeholder="Class (e.g., Repo)" value={cls} onChange={e=>setCls(e.target.value)} />}
            <button className="btn" onClick={loadViz}>Visualize</button>
          </div>
          <pre className="monospace">{JSON.stringify(insights, null, 2)}</pre>
        </div>
        <div className="card">
          <h3>Schema</h3>
          <div className="row"><button className="btn secondary" onClick={async()=>{ const r = await apiGet(`/graph/schema?backend=${backend}`); setSchema(r.schema); }}>Load Schema</button></div>
          <pre className="monospace">{JSON.stringify(schema, null, 2)}</pre>
        </div>
        <div className="card">
          <h3>Saved Queries</h3>
          <div className="row">
            <input className="input" placeholder="Name" value={queryName} onChange={e=>setQueryName(e.target.value)} />
            <button className="btn" onClick={onSaveQuery}>Save</button>
            <button className="btn secondary" onClick={onExportSaved}>Export All</button>
            <label className="btn secondary" style={{cursor:'pointer'}}>
              Import
              <input type="file" accept="application/json" style={{display:'none'}} onChange={onImportSaved} />
            </label>
          </div>
          <div className="section">
            {(queries||[]).length===0 && <div>No saved queries for {backend}.</div>}
            {(queries||[]).map(q=>(
              <div key={q.name} className="row" style={{justifyContent:'space-between'}}>
                <div><b>{q.name}</b></div>
                <div className="row">
                  <button className="btn secondary" onClick={()=>onRunSaved(q)}>Load</button>
                  <button className="btn" onClick={()=>onDeleteQuery(q.name)}>Delete</button>
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="card">
          <h3>Graph View</h3>
          {viz ? (
            <>
              <div className="row" style={{marginBottom:8}}>
                <select className="input" value={colorBy} onChange={e=>setColorBy(e.target.value)}>
                  <option value="label">Color by label</option>
                </select>
                <select className="input" value={labelFilter} onChange={e=>setLabelFilter(e.target.value)}>
                  <option value="">Filter: All labels</option>
                  {Array.from(new Set((viz?.nodes||[]).map(n=>n.label||'Node'))).map(l=> (
                    <option key={l} value={l}>{l}</option>
                  ))}
                </select>
                <input className="input" placeholder="Search node id/label" value={search} onChange={e=>setSearch(e.target.value)} />
                <button className="btn" onClick={()=>{
                  if (!cyRef) return;
                  const q = search.trim().toLowerCase();
                  if (!q) return;
                  const n = cyRef.nodes().filter(x=> x.id().toLowerCase().includes(q) || String(x.data('label')||'').toLowerCase().includes(q));
                  if (n.length>0) { cyRef.fit(n, 50); n.first().select(); }
                }}>Focus</button>
                <button className="btn secondary" onClick={()=>{ if (cyRef) {
                  const uri = cyRef.png({ full: true, bg: '#0b1220' });
                  const a = document.createElement('a'); a.href = uri; a.download = `graph-${backend}.png`; a.click();
                }}}>Export PNG</button>
                <button className="btn secondary" onClick={()=>{
                  const blob = new Blob([JSON.stringify(viz, null, 2)], {type:'application/json'});
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a'); a.href = url; a.download = `graph-${backend}.json`; a.click(); URL.revokeObjectURL(url);
                }}>Export JSON</button>
              </div>
              {labels.length>0 && (
                <div className="row" style={{gap:8, flexWrap:'wrap', margin:'6px 0 12px'}}>
                  {labels.map(l=> (
                    <span key={l} className="badge" style={{background: colorMap[l], color:'#0b1220', padding:'2px 6px', borderRadius:6}}>{l}</span>
                  ))}
                </div>
              )}
              <GraphView graph={viz} onNodeClick={expand} colorBy={colorBy} filterLabel={labelFilter} onReady={setCyRef} />
            </>
          ) : <div>Click Visualize to load a sample graph.</div>}
        </div>
        <div className="card">
          <h3>Cypher</h3>
          <textarea className="input" rows={8} value={cypher} onChange={e=>setCypher(e.target.value)} />
          <div className="row">
            <select className="input" value={mode} onChange={e=>setMode(e.target.value)}>
              <option value="read">read</option>
              <option value="write">write</option>
            </select>
            <select className="input" onChange={e=>{ const i = e.target.value; if (!i) return; const t = (templates[backend]||[])[Number(i)]; if (t) setCypher(t.query); e.target.value=''; }}>
              <option value="">Load template…</option>
              {(templates[backend]||[]).map((t,i)=> (<option key={i} value={i}>{t.name}</option>))}
            </select>
            <button className="btn" onClick={run}>Run</button>
          </div>
          <pre className="monospace">{JSON.stringify(result, null, 2)}</pre>
        </div>
      </div>
    </Layout>
  );
}
