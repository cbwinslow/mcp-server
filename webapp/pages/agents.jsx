import Layout from '../components/Layout';
import { useState } from 'react';
import { apiPost } from '../lib/api';

export default function Agents() {
  const [url, setUrl] = useState('https://fastapi.tiangolo.com/');
  const [out, setOut] = useState(null);

  async function crawl() {
    const r = await apiPost('/crawl', { url, depth: 1, max_pages: 3 }); setOut(r);
  }

  return (
    <Layout active="/agents">
      <div className="grid">
        <div className="card">
          <h3>Crawl</h3>
          <input className="input" value={url} onChange={e=>setUrl(e.target.value)} />
          <div className="row"><button className="btn" onClick={crawl}>Start Crawl</button></div>
        </div>
        <div className="card">
          <h3>Output</h3>
          <pre className="monospace">{JSON.stringify(out, null, 2)}</pre>
        </div>
      </div>
    </Layout>
  );
}

