import Layout from '../components/Layout';
import useSWR from 'swr';
import { apiGet } from '../lib/api';

export default function Home() {
  const { data: status } = useSWR('/status', apiGet, { refreshInterval: 5000 });
  const { data: insights } = useSWR('/graph/insights', apiGet);
  const { data: lastVal } = useSWR('/admin/validation/last', apiGet);

  const overall = status?.overall || 'unknown';
  const sBadge = (ok) => ({ background: ok? '#134e4a' : '#7f1d1d', padding:'4px 8px', borderRadius:6});

  const latestScore = lastVal?.latest?.score ?? null;
  const prevScore = lastVal?.previous?.score ?? null;
  const delta = (latestScore!=null && prevScore!=null) ? (latestScore - prevScore) : null;
  const deltaColor = delta!=null ? (delta>=0? '#22c55e':'#dc2626') : '#334155';

  return (
    <Layout active="/">
      <div className="grid">
        <div className="card">
          <h3>System Overview</h3>
          <div className="row" style={{gap:12, flexWrap:'wrap'}}>
            <span className="badge" style={{background: overall==='healthy'? '#22c55e' : (overall==='degraded'? '#eab308' : '#7f1d1d')}}>
              Overall: {overall}
            </span>
            <span className="badge" style={sBadge(!!status?.database && status?.database?.status!=='error')}>DB</span>
            <span className="badge" style={sBadge(true)}>API</span>
            {latestScore!=null && (
              <span className="badge" style={{background:'#0ea5e9'}}>Validation: {latestScore}</span>
            )}
            {delta!=null && (
              <span className="badge" style={{background: deltaColor}}>Δ {delta>=0? '+' : ''}{delta}</span>
            )}
          </div>
          <div style={{marginTop:8}}>
            <small>Repos: {status?.database?.tables? (status.database.tables.length): '—'}</small>
          </div>
        </div>

        <div className="card">
          <h3>Graph Insights</h3>
          <pre className="monospace">{JSON.stringify(insights, null, 2)}</pre>
        </div>

        <div className="card">
          <h3>Raw Status</h3>
          <pre className="monospace">{JSON.stringify(status, null, 2)}</pre>
        </div>
      </div>
    </Layout>
  );
}
