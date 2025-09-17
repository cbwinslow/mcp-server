import Link from 'next/link';
import { API_BASE } from '../lib/api';
import { useEffect, useState } from 'react';

export default function Layout({ active, children }) {
  const tabs = [
    { href: '/', label: 'Dashboard' },
    { href: '/settings', label: 'Settings' },
    { href: '/agents', label: 'Agents' },
    { href: '/graph', label: 'Graph' },
    { href: '/reports', label: 'Reports' },
    { href: '/chat', label: 'Chat' },
    { href: '/admin', label: 'Admin' },
  ];
  return (
    <>
      <header>
        <div className="container">
          <h1>MCP Platform Console</h1>
          <div style={{fontSize:12, opacity:0.8}}>API: {API_BASE} <button className="btn secondary" style={{marginLeft:8}} onClick={async ()=>{
            try{
              const r = await fetch(`${API_BASE}/admin/kv?keys=API_BASE_URL`, { headers: (typeof window!=='undefined' && localStorage.getItem('mcp_jwt'))? { Authorization: `Bearer ${localStorage.getItem('mcp_jwt')}` } : {} });
              const j = await r.json(); const v = j.values?.API_BASE_URL; if (v) { localStorage.setItem('apiBase', v); location.reload(); } else alert('KV missing API_BASE_URL');
            }catch(e){ alert('KV load failed: '+e); }
          }}>Use KV API</button></div>
          <div className="tabs">
            {tabs.map(t => (
              <Link key={t.href} href={t.href} className={`tab ${active===t.href? 'active':''}`}>{t.label}</Link>
            ))}
          </div>
        </div>
      </header>
      <main className="container">
        {children}
      </main>
    </>
  );
}
