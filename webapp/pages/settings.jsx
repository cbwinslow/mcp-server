import React, { useState, useEffect, useRef } from 'react';
import useSWR from 'swr';
import Layout from '../components/Layout';
import { apiGet, apiPut } from '../lib/api';

export default function Settings() {
  const { data, mutate } = useSWR('/admin/settings', apiGet);
  const [saving, setSaving] = useState(false);
  const [jwt, setJwt] = useState(typeof window !== 'undefined' ? localStorage.getItem('mcp_jwt') || '' : '');
  const [tab, setTab] = useState('platform');
  const [kv, setKv] = useState({ api: '', web: '' });
  const [conn, setConn] = useState(null);
  const baselineRef = useRef(null);
  const lastTest = (data?.settings?.admin?.last_test) || {};

  useEffect(()=>{
    if (data && data.settings && !baselineRef.current) {
      baselineRef.current = JSON.parse(JSON.stringify(data.settings));
    }
  }, [data]);

  if (!data) return <Layout active="/settings"><div>Loading...</div></Layout>;
  const settings = data.settings || {};

  function diffObjects(a, b, prefix='') {
    const changes = [];
    const keys = new Set([...Object.keys(a||{}), ...Object.keys(b||{})]);
    for (const k of keys) {
      const pa = a? a[k] : undefined;
      const pb = b? b[k] : undefined;
      const path = prefix? `${prefix}.${k}`: k;
      if (typeof pa === 'object' && pa && typeof pb === 'object' && pb) {
        changes.push(...diffObjects(pa, pb, path));
      } else if (JSON.stringify(pa) !== JSON.stringify(pb)) {
        changes.push({ path, from: pa, to: pb });
      }
    }
    return changes;
  }

  async function saveWithConfirm() {
    // Basic validation
    const urlish = s => /^https?:\/\//i.test(s||'');
    const s = settings;
    const errs = [];
    if (s.mcp_api?.database_url && !/^postgresql\+?\w*:\/\//i.test(s.mcp_api.database_url)) errs.push('DATABASE_URL must be a Postgres URL');
    if (s.mcp_api?.neo4j?.uri && !/^bolt(\+ssc|\+routing)?:\/\//i.test(s.mcp_api.neo4j.uri)) errs.push('Neo4j URI should start with bolt://');
    if (s.terminusdb?.server_url && !urlish(s.terminusdb.server_url)) errs.push('TerminusDB Server URL must be http(s)://');
    if (s.nebulagraph?.host && /\s/.test(s.nebulagraph.host)) errs.push('Nebula host has whitespace');
    if (errs.length) { alert('Fix validation errors before saving:\n- ' + errs.join('\n- ')); return; }

    const baseline = baselineRef.current || {};
    const changes = diffObjects(baseline, settings);
    if (changes.length === 0) { alert('No changes to save.'); return; }
    const preview = changes.map(c=> `- ${c.path}:\n    from: ${JSON.stringify(c.from)}\n    to:   ${JSON.stringify(c.to)}`).join('\n');
    if (!confirm(`Apply these changes?\n\n${preview}`)) return;
    setSaving(true);
    try {
      await apiPut('/admin/settings', { data: settings });
      await mutate();
      baselineRef.current = JSON.parse(JSON.stringify(settings));
      alert('Saved. Restart may be required to apply.');
    } catch (e) { alert(`Save failed: ${e}`); }
    finally { setSaving(false); }
  }

  function setValue(path, value) {
    const parts = path.split('.');
    const next = JSON.parse(JSON.stringify(settings));
    let cur = next;
    for (let i=0;i<parts.length-1;i++) cur = cur[parts[i]] = cur[parts[i]] || {};
    cur[parts[parts.length-1]] = value;
    data.settings = next;
    mutate({ ...data }, false);
  }

  function saveJwt() {
    localStorage.setItem('mcp_jwt', jwt || '');
    alert('JWT saved in browser');
  }

  return (
    <Layout active="/settings">
      <div className="tabs">
        {['platform','backends','pipeline','security'].map(t=>(
          <button key={t} className={`tab ${tab===t?'active':''}`} onClick={()=>setTab(t)}>{t.toUpperCase()}</button>
        ))}
      </div>
      {tab==='platform' && (
      <div className="grid">
        <div className="card">
          <h3 className="text-xl font-semibold mb-2">MCP API</h3>
          <label>Require Auth <input type="checkbox" checked={settings.mcp_api?.require_auth} onChange={e=>setValue('mcp_api.require_auth', e.target.checked)} /></label>
          <label>Allow Graph Writes <input type="checkbox" checked={settings.mcp_api?.allow_graph_writes} onChange={e=>setValue('mcp_api.allow_graph_writes', e.target.checked)} /></label>
          <label>DATABASE_URL <input className="input" value={settings.mcp_api?.database_url||''} onChange={e=>setValue('mcp_api.database_url', e.target.value)} /></label>
          <label>Neo4j URI <input className="input" value={settings.mcp_api?.neo4j?.uri||''} onChange={e=>setValue('mcp_api.neo4j.uri', e.target.value)} /></label>
          <label>Neo4j User <input className="input" value={settings.mcp_api?.neo4j?.user||''} onChange={e=>setValue('mcp_api.neo4j.user', e.target.value)} /></label>
          <label>Neo4j Password <input className="input" type="password" value={settings.mcp_api?.neo4j?.password||''} onChange={e=>setValue('mcp_api.neo4j.password', e.target.value)} /></label>
          <label>Crawl4AI URL <input className="input" value={settings.mcp_api?.crawl4ai_url||''} onChange={e=>setValue('mcp_api.crawl4ai_url', e.target.value)} /></label>
        </div>
        <div className="card">
          <h3 className="text-xl font-semibold mb-2">Graphiti</h3>
          <label>SSE URL <input className="input" value={settings.graphiti?.sse_url||''} onChange={e=>setValue('graphiti.sse_url', e.target.value)} /></label>
          <label>POST URL <input className="input" value={settings.graphiti?.post_url||''} onChange={e=>setValue('graphiti.post_url', e.target.value)} /></label>
          <label>Auth Header <input className="input" value={settings.graphiti?.auth||''} onChange={e=>setValue('graphiti.auth', e.target.value)} /></label>
          <label>Group ID <input className="input" value={settings.graphiti?.group_id||'default'} onChange={e=>setValue('graphiti.group_id', e.target.value)} /></label>
        </div>
        <div className="card">
          <h3 className="text-xl font-semibold mb-2">Connectivity</h3>
          <div className="row">
            <button className="btn" onClick={async ()=>{
              try{ const r = await apiGet('/admin/test/connectivity'); setConn(r.results||{}); }
              catch(e){ alert('Connectivity test failed: '+e); }
              await mutate();
            }}>Test All</button>
          </div>
          <div className="badges" style={{display:'flex', gap:12, marginTop:8}}>
            {['postgres','neo4j','terminusdb','nebulagraph','localai','api'].map(k=> (
              <span key={k} className="badge" title={conn?.[k]?.detail||''} style={{background: conn?.[k]?.ok? '#134e4a':'#7f1d1d', padding:'4px 8px', borderRadius:6}}>
                {k}: {conn?.[k]?.ok? 'OK':'ERR'}
                <small style={{marginLeft:6, opacity:0.8}}>
                  {lastTest?.[k]?.ts ? `(${new Date(lastTest[k].ts).toLocaleString()})` : ''}
                </small>
              </span>
            ))}
          </div>
        </div>
        <div className="card">
          <h3 className="text-xl font-semibold mb-2">Public URLs</h3>
          <div className="row">
            <label>API_BASE_URL <input className="input" value={kv.api} onChange={e=>setKv(v=>({...v, api:e.target.value}))} /></label>
            <label>WEB_BASE_URL <input className="input" value={kv.web} onChange={e=>setKv(v=>({...v, web:e.target.value}))} /></label>
          </div>
          <div className="row">
            <button className="btn" onClick={async ()=>{
              try {
                const res = await apiGet('/admin/kv?keys=API_BASE_URL,WEB_BASE_URL');
                const api = res.values?.API_BASE_URL || '';
                const web = res.values?.WEB_BASE_URL || '';
                setKv({ api, web });
                if (api) {
                  if (typeof window!== 'undefined') localStorage.setItem('apiBase', api);
                  alert('Loaded API/WEB base URLs from KV.');
                } else {
                  alert('KV did not return API_BASE_URL; check server KV settings.');
                }
              } catch (e) {
                alert('Failed to load from KV: '+ e);
              }
            }}>Load from KV</button>
            <button className="btn secondary" onClick={async ()=>{
              try {
                await apiPut('/admin/kv', { items: { API_BASE_URL: kv.api, WEB_BASE_URL: kv.web } });
                if (typeof window!== 'undefined' && kv.api) localStorage.setItem('apiBase', kv.api);
                alert('Saved API/WEB base URLs to KV.');
              } catch(e) { alert('Save to KV failed: '+e); }
            }}>Save to KV</button>
          </div>
        </div>
      </div>)}

      {tab==='backends' && (
      <div className="grid">
        <div className="card">
          <h3 className="text-xl font-semibold mb-2">Graph Backends</h3>
          <label>Default Backend
            <select className="input" value={settings.graph_backends?.default||'terminusdb'} onChange={e=>setValue('graph_backends.default', e.target.value)}>
              <option value="terminusdb">TerminusDB</option>
              <option value="neo4j">Neo4j</option>
              <option value="nebula">NebulaGraph</option>
            </select>
          </label>
          <label>Use Neo4j <input type="checkbox" checked={settings.graph_backends?.neo4j||false} onChange={e=>setValue('graph_backends.neo4j', e.target.checked)} /></label>
          <label>Use TerminusDB <input type="checkbox" checked={settings.graph_backends?.terminusdb||false} onChange={e=>setValue('graph_backends.terminusdb', e.target.checked)} /></label>
          <label>Use NebulaGraph <input type="checkbox" checked={settings.graph_backends?.nebulagraph||false} onChange={e=>setValue('graph_backends.nebulagraph', e.target.checked)} /></label>
        </div>
        <div className="card">
          <h4 className="text-lg font-semibold mb-2">TerminusDB</h4>
          <label>Server URL <input className="input" value={settings.terminusdb?.server_url||''} onChange={e=>setValue('terminusdb.server_url', e.target.value)} /></label>
          <label>DB <input className="input" value={settings.terminusdb?.db||''} onChange={e=>setValue('terminusdb.db', e.target.value)} /></label>
          <label>User <input className="input" value={settings.terminusdb?.user||''} onChange={e=>setValue('terminusdb.user', e.target.value)} /></label>
          <label>Password <input type="password" className="input" value={settings.terminusdb?.password||''} onChange={e=>setValue('terminusdb.password', e.target.value)} /></label>
          <label>Token <input className="input" value={settings.terminusdb?.token||''} onChange={e=>setValue('terminusdb.token', e.target.value)} /></label>
          <div className="row" style={{marginTop:8}}>
            <span title={lastTest?.terminusdb?.ok? 'OK':'Unknown/ERR'} style={{width:10,height:10,borderRadius:5,background: lastTest?.terminusdb?.ok? '#22c55e':'#64748b', display:'inline-block'}}></span>
            <button className="btn secondary" onClick={async()=>{ try{ const r = await apiGet('/graph/test?backend=terminusdb'); await mutate(); alert(`TerminusDB: ${r.ok}`);} catch(e){ alert('Test failed: '+e);} }}>Test</button>
            <small style={{marginLeft:8, opacity:0.8}}>{lastTest?.terminusdb?.ts ? `Last: ${new Date(lastTest.terminusdb.ts).toLocaleString()}` : ''}</small>
          </div>
        </div>
        <div className="card">
          <h4 className="text-lg font-semibold mb-2">NebulaGraph</h4>
          <label>Host <input className="input" value={settings.nebulagraph?.host||''} onChange={e=>setValue('nebulagraph.host', e.target.value)} /></label>
          <div className="row">
            <label>Port <input type="number" className="input" value={settings.nebulagraph?.port||9669} onChange={e=>setValue('nebulagraph.port', Number(e.target.value))} /></label>
            <label>Space <input className="input" value={settings.nebulagraph?.space||''} onChange={e=>setValue('nebulagraph.space', e.target.value)} /></label>
          </div>
          <div className="row">
            <label>User <input className="input" value={settings.nebulagraph?.user||''} onChange={e=>setValue('nebulagraph.user', e.target.value)} /></label>
            <label>Password <input type="password" className="input" value={settings.nebulagraph?.password||''} onChange={e=>setValue('nebulagraph.password', e.target.value)} /></label>
          </div>
          <div className="row" style={{marginTop:8}}>
            <span title={lastTest?.nebula?.ok? 'OK':'Unknown/ERR'} style={{width:10,height:10,borderRadius:5,background: lastTest?.nebula?.ok? '#22c55e':'#64748b', display:'inline-block'}}></span>
            <button className="btn secondary" onClick={async()=>{ try{ const r = await apiGet('/graph/test?backend=nebula'); await mutate(); alert(`Nebula: ${r.ok}`);} catch(e){ alert('Test failed: '+e);} }}>Test</button>
            <small style={{marginLeft:8, opacity:0.8}}>{lastTest?.nebula?.ts ? `Last: ${new Date(lastTest.nebula.ts).toLocaleString()}` : ''}</small>
          </div>
        </div>
        <div className="card">
          <h4 className="text-lg font-semibold mb-2">Neo4j</h4>
          <label>URI <input className="input" value={settings.mcp_api?.neo4j?.uri||''} onChange={e=>setValue('mcp_api.neo4j.uri', e.target.value)} /></label>
          <label>User <input className="input" value={settings.mcp_api?.neo4j?.user||''} onChange={e=>setValue('mcp_api.neo4j.user', e.target.value)} /></label>
          <label>Password <input type="password" className="input" value={settings.mcp_api?.neo4j?.password||''} onChange={e=>setValue('mcp_api.neo4j.password', e.target.value)} /></label>
          <div className="row" style={{marginTop:8}}>
            <span title={lastTest?.neo4j?.ok? 'OK':'Unknown/ERR'} style={{width:10,height:10,borderRadius:5,background: lastTest?.neo4j?.ok? '#22c55e':'#64748b', display:'inline-block'}}></span>
            <button className="btn secondary" onClick={async()=>{ try{ const r = await apiGet('/graph/test?backend=neo4j'); await mutate(); alert(`Neo4j: ${r.ok}`);} catch(e){ alert('Test failed: '+e);} }}>Test</button>
            <small style={{marginLeft:8, opacity:0.8}}>{lastTest?.neo4j?.ts ? `Last: ${new Date(lastTest.neo4j.ts).toLocaleString()}` : ''}</small>
          </div>
        </div>
      </div>)}

      {tab==='pipeline' && (
      <div className="grid">
        <div className="card">
          <h3 className="text-xl font-semibold mb-2">Crawl Pipeline</h3>
          <label>Targets (comma separated)
            <input className="input" value={(settings.crawl_pipeline?.targets||[]).join(', ')} onChange={e=>setValue('crawl_pipeline.targets', e.target.value.split(',').map(s=>s.trim()).filter(Boolean))} />
          </label>
          <div className="row">
            <label>Depth <input type="number" className="input" value={settings.crawl_pipeline?.depth||1} onChange={e=>setValue('crawl_pipeline.depth', Number(e.target.value))} /></label>
            <label>Max Pages <input type="number" className="input" value={settings.crawl_pipeline?.max_pages||3} onChange={e=>setValue('crawl_pipeline.max_pages', Number(e.target.value))} /></label>
          </div>
          <div className="row">
            <label>Batch by Domain <input type="checkbox" checked={settings.crawl_pipeline?.batch_by_domain||false} onChange={e=>setValue('crawl_pipeline.batch_by_domain', e.target.checked)} /></label>
            <label>Max Items <input type="number" className="input" value={settings.crawl_pipeline?.max_items||20} onChange={e=>setValue('crawl_pipeline.max_items', Number(e.target.value))} /></label>
            <label>Body Chars <input type="number" className="input" value={settings.crawl_pipeline?.body_chars||3000} onChange={e=>setValue('crawl_pipeline.body_chars', Number(e.target.value))} /></label>
          </div>
        </div>
      </div>)}

      {tab==='security' && (
      <div className="grid">
        <div className="card">
          <h3 className="text-xl font-semibold mb-2">Auth (Browser)</h3>
          <label>JWT <input className="input" value={jwt} onChange={e=>setJwt(e.target.value)} /></label>
          <button className="btn" onClick={saveJwt}>Save JWT</button>
        </div>
      </div>)}

      <div className="section">
        <button className="btn" onClick={saveWithConfirm} disabled={saving}>{saving? 'Saving...':'Save Settings'}</button>
      </div>
    </Layout>
  );
}
