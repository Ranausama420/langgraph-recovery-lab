import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Provider, useDispatch, useSelector } from "react-redux";
import { configureStore, createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import "./style.css";

const API_HEADERS = {
  "X-Tenant-Id": "acme",
  "X-User-Role": "operator",
  "Content-Type": "application/json",
};

async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { ...API_HEADERS, ...(options.headers || {}) } });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || "The PulseOps API is unavailable.");
  return payload;
}

const loadJobs = createAsyncThunk("jobs/load", () => api("/api/jobs/?page_size=100"));
const loadStats = createAsyncThunk("jobs/stats", () => api("/api/jobs/stats/"));
const createJob = createAsyncThunk("jobs/create", (data) => api("/api/jobs/", { method: "POST", body: JSON.stringify(data) }));
const retryJob = createAsyncThunk("jobs/retry", (id) => api(`/api/jobs/${id}/retry/`, { method: "POST" }));

const slice = createSlice({
  name: "jobs",
  initialState: { items: [], stats: null, loading: false, mutating: false, error: "" },
  reducers: { clearError: (state) => { state.error = ""; } },
  extraReducers: (builder) => {
    builder
      .addCase(loadJobs.pending, (state) => { state.loading = true; state.error = ""; })
      .addCase(loadJobs.fulfilled, (state, action) => { state.items = action.payload.results || action.payload; state.loading = false; })
      .addCase(loadJobs.rejected, (state, action) => { state.loading = false; state.error = action.error.message; })
      .addCase(loadStats.fulfilled, (state, action) => { state.stats = action.payload; })
      .addCase(loadStats.rejected, (state, action) => { state.error = action.error.message; })
      .addCase(createJob.pending, (state) => { state.mutating = true; state.error = ""; })
      .addCase(createJob.fulfilled, (state, action) => { state.mutating = false; state.items = [action.payload, ...state.items.filter((job) => job.id !== action.payload.id)]; })
      .addCase(createJob.rejected, (state, action) => { state.mutating = false; state.error = action.error.message; })
      .addCase(retryJob.pending, (state) => { state.mutating = true; state.error = ""; })
      .addCase(retryJob.fulfilled, (state, action) => { state.mutating = false; state.items = state.items.map((job) => job.id === action.payload.id ? action.payload : job); })
      .addCase(retryJob.rejected, (state, action) => { state.mutating = false; state.error = action.error.message; });
  },
});

const store = configureStore({ reducer: { jobs: slice.reducer } });

function App() {
  const dispatch = useDispatch();
  const { items, stats, loading, mutating, error } = useSelector((state) => state.jobs);
  const [tab, setTab] = useState("Overview");
  const [dark, setDark] = useState(false);
  const [selectedJob, setSelectedJob] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [timelineLoading, setTimelineLoading] = useState(false);

  const refresh = () => { dispatch(loadJobs()); dispatch(loadStats()); };
  useEffect(() => { refresh(); }, []);

  const openJob = async (job) => {
    setSelectedJob(job); setTimelineLoading(true);
    try { setTimeline(await api(`/api/jobs/${job.id}/timeline/`)); }
    catch (_) { dispatch(slice.actions.clearError()); }
    finally { setTimelineLoading(false); }
  };

  const submit = async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    try {
      await dispatch(createJob({ task: form.get("task"), tool: form.get("tool"), max_attempts: 3, idempotency_key: crypto.randomUUID() })).unwrap();
      event.target.reset(); refresh();
    } catch (_) { /* Redux stores the user-facing error. */ }
  };

  const retry = async (job) => {
    try { await dispatch(retryJob(job.id)).unwrap(); refresh(); }
    catch (_) { /* Redux stores the user-facing error. */ }
  };

  const computedStats = useMemo(() => ({
    total: stats?.total ?? items.length,
    completed: stats?.completed ?? items.filter((job) => job.status === "completed").length,
    dead_letter: stats?.dead_letter ?? items.filter((job) => job.status === "dead_letter").length,
  }), [items, stats]);
  const visibleJobs = tab === "Dead letter" ? items.filter((job) => job.status === "dead_letter") : items;

  return <div className={dark ? "shell dark" : "shell"}>
    <aside>
      <div className="brand"><span className="brandmark">✦</span><span>Pulse<span className="brandAccent">Ops</span></span></div>
      <p className="workspace">WORKSPACE</p>
      {[["Overview", "⌂"], ["Jobs", "▣"], ["Dead letter", "⚠"], ["Activity", "◷"]].map(([name, icon]) => <button key={name} className={tab === name ? "nav active" : "nav"} onClick={() => setTab(name)}>{icon} <span>{name === "Jobs" ? "All jobs" : name}</span>{name === "Jobs" && <em>{computedStats.total}</em>}{name === "Dead letter" && <em>{computedStats.dead_letter}</em>}</button>)}
      <div className="sideBottom"><button className="nav" onClick={() => setDark(!dark)}>{dark ? "☼" : "☾"}<span>{dark ? "Light mode" : "Dark mode"}</span></button><div className="profile"><div className="avatar">RU</div><div><b>Rana Usama</b><small>Operator · Acme</small></div><span>•••</span></div></div>
    </aside>
    <main>
      <header><div><p className="eyebrow">ACME / OPERATIONS</p><h1>{tab}</h1><p className="sub">A calm command center for reliable workflow execution.</p></div><div className="headerActions"><button className="outline" onClick={refresh}>↻ Refresh</button><span className="role">OPERATOR</span></div></header>
      {error && <div className="errorBanner" role="alert">{error}<button onClick={() => dispatch(slice.actions.clearError())}>Dismiss</button></div>}
      {tab === "Overview" || tab === "Jobs" || tab === "Dead letter" ? <>
        <section className="stats"><div><span className="statLabel">TOTAL JOBS</span><b>{computedStats.total}</b><small className="trend">↑ Live tenant data</small></div><div><span className="statLabel">COMPLETED</span><b>{computedStats.completed}</b><small className="trend good">Reliable runs</small></div><div><span className="statLabel">DEAD LETTER</span><b>{computedStats.dead_letter}</b><small className="trend warn">Needs attention</small></div></section>
        {tab === "Overview" && <section className="grid"><form className="card create" onSubmit={submit}><span className="cardKicker">NEW RUN</span><h2>Create a job</h2><p>Start a monitored workflow and watch every attempt.</p><input name="task" required placeholder="What should PulseOps run?"/><select name="tool"><option value="unstable_email">Unstable email · retry demo</option><option value="validation">Validation · dead letter demo</option><option value="report">Report · success demo</option></select><button className="primary" disabled={mutating}>{mutating ? "Running…" : "Create and run"}<span>→</span></button></form><JobList jobs={visibleJobs.slice(0, 6)} loading={loading} onOpen={openJob} onRetry={retry} onRefresh={refresh}/></section>}
        {tab !== "Overview" && <JobList jobs={visibleJobs} loading={loading} onOpen={openJob} onRetry={retry} onRefresh={refresh} full/>}
      </> : <section className="card placeholder"><span className="cardKicker">ACTIVITY</span><h2>Select a job to inspect its timeline.</h2><p>Every attempt, retry, and terminal state is recorded as an auditable workflow event.</p></section>}
    </main>
    {selectedJob && <div className="modalBackdrop" onClick={() => setSelectedJob(null)}><section className="modal" onClick={(event) => event.stopPropagation()}><button className="modalClose" onClick={() => setSelectedJob(null)}>×</button><span className="cardKicker">JOB DETAIL</span><h2>{selectedJob.task}</h2><p className="modalMeta">{selectedJob.tool} · {selectedJob.status} · attempt {selectedJob.current_attempt}</p><h3>Workflow timeline</h3>{timelineLoading ? <p className="empty">Loading timeline…</p> : <div className="timeline">{timeline.map((event) => <div className="timelineRow" key={event.id}><span></span><div><strong>{event.event.replaceAll("_", " ")}</strong><small>{new Date(event.created_at).toLocaleString()}</small></div></div>)}</div>}</section></div>}
  </div>;
}

function JobList({ jobs, loading, onOpen, onRetry, onRefresh, full = false }) {
  return <div className={`card jobsCard ${full ? "fullCard" : ""}`}><div className="cardHead"><div><span className="cardKicker">LIVE QUEUE</span><h2>{full ? "All jobs" : "Recent jobs"}</h2></div><button className="ghost" onClick={onRefresh}>Refresh</button></div>{loading ? <p className="empty">Loading queue…</p> : jobs.length ? jobs.map((job) => <article className="job" key={job.id}><button className="jobMain" onClick={() => onOpen(job)}><div className="jobIcon">{job.status === "completed" ? "✓" : job.status === "dead_letter" ? "!" : "↻"}</div><div className="jobInfo"><strong>{job.task}</strong><small>{job.tool} · attempt {job.current_attempt} · {job.status === "retrying" ? "retry scheduled" : "updated now"}</small></div></button><span className={`status ${job.status}`}>{job.status.replace("_", " ")}</span>{job.status === "dead_letter" && <button className="linkButton" onClick={() => onRetry(job)}>Retry</button>}</article>) : <p className="empty">No jobs match this view.</p>}</div>;
}

createRoot(document.getElementById("root")).render(<Provider store={store}><App/></Provider>);
