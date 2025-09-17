from src.settings.global_settings import SettingsStore, DEFAULTS

def test_settings_default_merge(tmp_path):
  s = SettingsStore(path=tmp_path / 'gs.json')
  data = s.read()
  assert 'mcp_api' in data and 'graph_backends' in data
  # write partial and ensure merge
  merged = s.write({'mcp_api': {'require_auth': True}})
  assert merged['mcp_api']['require_auth'] is True
  # other defaults persist
  assert 'graph_backends' in merged and merged['graph_backends']['default']

