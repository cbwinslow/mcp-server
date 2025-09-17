import Layout from '../components/Layout';
import { useState } from 'react';
import { apiPost } from '../lib/api';

export default function Chat() {
  const [q, setQ] = useState('');
  const [log, setLog] = useState([]);

  async function ask() {
    const r = await apiPost('/search', { query: q, top_k: 5, hybrid: true, collection: 'mcp_chunks' });
    setLog(l => [...l, { role: 'user', text: q }, { role: 'assistant', text: (r.results?.[0]?.text||'No match') }]);
    setQ('');
  }

  return (
    <Layout active="/chat">
      <div className="card">
        <h3>Assistant</h3>
        <div className="section">
          <textarea className="input" rows={4} value={q} onChange={e=>setQ(e.target.value)} placeholder="Ask about your data..." />
          <div className="row"><button className="btn" onClick={ask}>Ask</button></div>
        </div>
        <div className="section">
          {log.map((m,i)=>(
            <div key={i} className="row" style={{alignItems:'flex-start'}}>
              <div className="card" style={{flex:1, background:m.role==='user'? '#1f2937':'#0f172a'}}>
                <b>{m.role}</b>
                <div>{m.text}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Layout>
  );
}

