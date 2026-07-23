CREATE TABLE account_analytics_snapshots (
  id TEXT PRIMARY KEY,
  sync_job_id TEXT NOT NULL,
  account_id TEXT NOT NULL,
  scope TEXT NOT NULL,
  source_url TEXT NOT NULL,
  captured_at TEXT NOT NULL,
  period_label TEXT,
  availability TEXT NOT NULL
    CHECK(availability IN ('available','unavailable','partial')),
  unavailable_reason TEXT,
  metrics_json TEXT NOT NULL,
  sections_json TEXT NOT NULL,
  missing_reason_json TEXT NOT NULL,
  parser_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(sync_job_id, scope)
);

CREATE INDEX idx_account_analytics_account_scope_time
  ON account_analytics_snapshots(account_id, scope, captured_at DESC);
CREATE INDEX idx_account_analytics_job
  ON account_analytics_snapshots(sync_job_id);
