import Layout from '../components/Layout';
import { useState } from 'react';

export default function Reports() {
  const [filter, setFilter] = useState('');
  // Placeholder: integrate with a reports API (politicians, etc.)
  const data = [];

  return (
    <Layout active="/reports">
      <div className="card">
        <h3>Reports (Politicians)</h3>
        <div className="row">
          <input className="input" placeholder="Filter" value={filter} onChange={e=>setFilter(e.target.value)} />
          <button className="btn secondary">Export PDF</button>
        </div>
        <div className="section">
          <pre className="monospace">{JSON.stringify(data, null, 2)}</pre>
        </div>
      </div>
    </Layout>
  );
}

