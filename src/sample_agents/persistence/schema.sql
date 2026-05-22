CREATE TABLE IF NOT EXISTS agent_threads (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  thread_id TEXT NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(thread_id) REFERENCES agent_threads(id)
);

CREATE TABLE IF NOT EXISTS message_attachments (
  id TEXT PRIMARY KEY,
  thread_id TEXT NOT NULL,
  message_id TEXT,
  original_filename TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  storage_uri TEXT NOT NULL,
  agent_file_path TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(thread_id) REFERENCES agent_threads(id),
  FOREIGN KEY(message_id) REFERENCES messages(id)
);

CREATE TABLE IF NOT EXISTS agent_runs (
  id TEXT PRIMARY KEY,
  thread_id TEXT NOT NULL,
  triggering_message_id TEXT,
  status TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  error_message TEXT,
  model_provider TEXT,
  model_name TEXT,
  FOREIGN KEY(thread_id) REFERENCES agent_threads(id)
);

CREATE TABLE IF NOT EXISTS tool_calls (
  id TEXT PRIMARY KEY,
  agent_run_id TEXT NOT NULL,
  tool_name TEXT NOT NULL,
  input_summary TEXT NOT NULL,
  output_summary TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(agent_run_id) REFERENCES agent_runs(id)
);

CREATE TABLE IF NOT EXISTS approvals (
  id TEXT PRIMARY KEY,
  thread_id TEXT NOT NULL,
  agent_run_id TEXT,
  requested_action TEXT NOT NULL,
  preview TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  decided_at TEXT,
  FOREIGN KEY(thread_id) REFERENCES agent_threads(id)
);

CREATE INDEX IF NOT EXISTS idx_messages_thread_created ON messages(thread_id, created_at);
CREATE INDEX IF NOT EXISTS idx_attachments_thread ON message_attachments(thread_id);
CREATE INDEX IF NOT EXISTS idx_runs_thread_started ON agent_runs(thread_id, started_at);
CREATE INDEX IF NOT EXISTS idx_approvals_thread_status ON approvals(thread_id, status);
