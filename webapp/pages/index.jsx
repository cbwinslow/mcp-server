import Layout from '../components/Layout';
import useSWR from 'swr';
import { apiGet } from '../lib/api';

export default function Home() {
  const { data: status } = useSWR('/status', apiGet, { refreshInterval: 5000 });
  const { data: insights } = useSWR('/graph/insights', apiGet);
  return (
    <Layout active="/">
      <div className="grid">
        <div className="card"><h3>Status</h3><pre className="monospace">{JSON.stringify(status, null, 2)}</pre></div>
        <div className="card"><h3>Graph Insights</h3><pre className="monospace">{JSON.stringify(insights, null, 2)}</pre></div>
      </div>
    </Layout>
  );
}

