import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Archive,
  Bot,
  Check,
  CircleAlert,
  Database,
  Loader2,
  MessageSquareText,
  Plus,
  RefreshCw,
  Search,
  Trash2,
} from "lucide-react";
import {
  ChatResponse,
  MemoryRecord,
  chatWithMemory,
  createMemory,
  deleteMemory,
  getCategories,
  getHealth,
  listMemories,
  searchMemories,
} from "./api";
import "./styles.css";

type View = "add" | "search" | "chat" | "manage";

const fallbackCategories = [
  "Customer Engagement",
  "Internal Notes",
  "Platform / Product",
  "Technical Issue",
  "Demo / PoC",
  "Architecture",
  "Follow-up / Next Steps",
];

function parseTags(value: string) {
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function cleanOptional(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : undefined;
}

function App() {
  const [view, setView] = useState<View>("add");
  const [categories, setCategories] = useState(fallbackCategories);
  const [apiStatus, setApiStatus] = useState<"checking" | "ok" | "down">("checking");

  useEffect(() => {
    getHealth()
      .then(() => setApiStatus("ok"))
      .catch(() => setApiStatus("down"));
    getCategories()
      .then((response) => setCategories(response.categories))
      .catch(() => setCategories(fallbackCategories));
  }, []);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Database size={22} />
          </div>
          <div>
            <h1>Oracle Agent Memory</h1>
            <p>Memory console</p>
          </div>
        </div>

        <nav className="nav-stack" aria-label="Main navigation">
          <NavButton
            active={view === "add"}
            icon={<Plus size={18} />}
            label="Add Memory"
            onClick={() => setView("add")}
          />
          <NavButton
            active={view === "search"}
            icon={<Search size={18} />}
            label="Search"
            onClick={() => setView("search")}
          />
          <NavButton
            active={view === "chat"}
            icon={<Bot size={18} />}
            label="Chat"
            onClick={() => setView("chat")}
          />
          <NavButton
            active={view === "manage"}
            icon={<Archive size={18} />}
            label="Manage"
            onClick={() => setView("manage")}
          />
        </nav>

        <div className={`status-pill ${apiStatus}`}>
          <span />
          {apiStatus === "checking" ? "Checking API" : apiStatus === "ok" ? "API online" : "API offline"}
        </div>
      </aside>

      <main className="workspace">
        {view === "add" && <AddMemoryView categories={categories} />}
        {view === "search" && <SearchView categories={categories} />}
        {view === "chat" && <ChatView categories={categories} />}
        {view === "manage" && <ManageView />}
      </main>
    </div>
  );
}

function NavButton({
  active,
  icon,
  label,
  onClick,
}: {
  active: boolean;
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button className={`nav-button ${active ? "active" : ""}`} onClick={onClick}>
      {icon}
      <span>{label}</span>
    </button>
  );
}

function AddMemoryView({ categories }: { categories: string[] }) {
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState(categories[0]);
  const [project, setProject] = useState("");
  const [tags, setTags] = useState("");
  const [source, setSource] = useState("");
  const [content, setContent] = useState("");
  const [state, setState] = useState<AsyncState>({ status: "idle" });

  useEffect(() => {
    if (!categories.includes(category)) setCategory(categories[0]);
  }, [categories, category]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setState({ status: "loading" });
    try {
      const response = await createMemory({
        title,
        content,
        category,
        customer_project: cleanOptional(project),
        tags: parseTags(tags),
        source: cleanOptional(source),
      });
      setState({ status: "success", message: `Created ${response.memory_id}` });
      setTitle("");
      setProject("");
      setTags("");
      setSource("");
      setContent("");
    } catch (error) {
      setState({ status: "error", message: getErrorMessage(error) });
    }
  }

  return (
    <section className="view-grid add-grid">
      <header className="view-header">
        <div>
          <p className="eyebrow">Create</p>
          <h2>Add Memory</h2>
        </div>
        <StateBadge state={state} />
      </header>

      <form className="form-surface" onSubmit={submit}>
        <div className="field-row two">
          <Field label="Title">
            <input value={title} onChange={(event) => setTitle(event.target.value)} required />
          </Field>
          <Field label="Category">
            <select value={category} onChange={(event) => setCategory(event.target.value)}>
              {categories.map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </Field>
        </div>
        <div className="field-row three">
          <Field label="Customer / Project">
            <input value={project} onChange={(event) => setProject(event.target.value)} />
          </Field>
          <Field label="Tags">
            <input value={tags} onChange={(event) => setTags(event.target.value)} placeholder="renewal, exadata" />
          </Field>
          <Field label="Source">
            <input value={source} onChange={(event) => setSource(event.target.value)} placeholder="meeting, email" />
          </Field>
        </div>
        <Field label="Memory">
          <textarea value={content} onChange={(event) => setContent(event.target.value)} required />
        </Field>
        <div className="action-row">
          <button className="primary-button" disabled={state.status === "loading"}>
            {state.status === "loading" ? <Loader2 size={18} className="spin" /> : <Plus size={18} />}
            Add Memory
          </button>
        </div>
      </form>
    </section>
  );
}

function SearchView({ categories }: { categories: string[] }) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [project, setProject] = useState("");
  const [tags, setTags] = useState("");
  const [limit, setLimit] = useState(10);
  const [results, setResults] = useState<MemoryRecord[]>([]);
  const [state, setState] = useState<AsyncState>({ status: "idle" });

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setState({ status: "loading" });
    try {
      const records = await searchMemories({
        query,
        category: cleanOptional(category),
        customer_project: cleanOptional(project),
        tags: parseTags(tags),
        limit,
      });
      setResults(records);
      setState({ status: "success", message: `${records.length} result(s)` });
    } catch (error) {
      setState({ status: "error", message: getErrorMessage(error) });
    }
  }

  return (
    <section className="view-grid">
      <header className="view-header">
        <div>
          <p className="eyebrow">Retrieve</p>
          <h2>Search Memories</h2>
        </div>
        <StateBadge state={state} />
      </header>
      <form className="filter-bar" onSubmit={submit}>
        <Field label="Query">
          <input value={query} onChange={(event) => setQuery(event.target.value)} required />
        </Field>
        <Field label="Category">
          <select value={category} onChange={(event) => setCategory(event.target.value)}>
            <option value="">Any</option>
            {categories.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </Field>
        <Field label="Project">
          <input value={project} onChange={(event) => setProject(event.target.value)} />
        </Field>
        <Field label="Tags">
          <input value={tags} onChange={(event) => setTags(event.target.value)} />
        </Field>
        <Field label="Limit">
          <input
            type="number"
            min={1}
            max={50}
            value={limit}
            onChange={(event) => setLimit(Number(event.target.value))}
          />
        </Field>
        <button className="icon-button label-button" title="Search">
          <Search size={18} />
          Search
        </button>
      </form>
      <MemoryList records={results} />
    </section>
  );
}

function ChatView({ categories }: { categories: string[] }) {
  const [question, setQuestion] = useState("");
  const [category, setCategory] = useState("");
  const [project, setProject] = useState("");
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [state, setState] = useState<AsyncState>({ status: "idle" });

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setState({ status: "loading" });
    try {
      const next = await chatWithMemory({
        question,
        category: cleanOptional(category),
        customer_project: cleanOptional(project),
      });
      setResponse(next);
      setState({ status: "success", message: `${next.sources.length} source(s)` });
    } catch (error) {
      setState({ status: "error", message: getErrorMessage(error) });
    }
  }

  return (
    <section className="view-grid chat-grid">
      <header className="view-header">
        <div>
          <p className="eyebrow">Read only</p>
          <h2>Chat with Memory</h2>
        </div>
        <StateBadge state={state} />
      </header>
      <form className="chat-composer" onSubmit={submit}>
        <textarea value={question} onChange={(event) => setQuestion(event.target.value)} required />
        <div className="field-row three">
          <Field label="Category">
            <select value={category} onChange={(event) => setCategory(event.target.value)}>
              <option value="">Any</option>
              {categories.map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </Field>
          <Field label="Project">
            <input value={project} onChange={(event) => setProject(event.target.value)} />
          </Field>
          <div className="submit-cell">
            <button className="primary-button" disabled={state.status === "loading"}>
              {state.status === "loading" ? <Loader2 size={18} className="spin" /> : <MessageSquareText size={18} />}
              Ask
            </button>
          </div>
        </div>
      </form>
      {response && (
        <div className="chat-output">
          <section className="answer-panel">
            <h3>Answer</h3>
            <p>{response.answer}</p>
          </section>
          <section>
            <h3>Sources</h3>
            <MemoryList records={response.sources} compact />
          </section>
        </div>
      )}
    </section>
  );
}

function ManageView() {
  const [limit, setLimit] = useState(50);
  const [records, setRecords] = useState<MemoryRecord[]>([]);
  const [selected, setSelected] = useState<MemoryRecord | null>(null);
  const [state, setState] = useState<AsyncState>({ status: "idle" });

  async function load() {
    setState({ status: "loading" });
    try {
      const next = await listMemories(limit);
      setRecords(next);
      setState({ status: "success", message: `${next.length} memory record(s)` });
    } catch (error) {
      setState({ status: "error", message: getErrorMessage(error) });
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function remove(memoryId: string) {
    setState({ status: "loading" });
    try {
      await deleteMemory(memoryId);
      setSelected(null);
      await load();
    } catch (error) {
      setState({ status: "error", message: getErrorMessage(error) });
    }
  }

  return (
    <section className="view-grid">
      <header className="view-header">
        <div>
          <p className="eyebrow">Library</p>
          <h2>Manage Memories</h2>
        </div>
        <StateBadge state={state} />
      </header>

      <div className="toolbar">
        <Field label="Rows">
          <input
            type="number"
            min={1}
            max={200}
            value={limit}
            onChange={(event) => setLimit(Number(event.target.value))}
          />
        </Field>
        <button className="icon-button label-button" title="Refresh" onClick={load}>
          <RefreshCw size={18} />
          Refresh
        </button>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Category</th>
              <th>Project</th>
              <th>Tags</th>
              <th>Created</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {records.map((record) => (
              <tr key={record.memory_id} onClick={() => setSelected(record)}>
                <td>{record.title}</td>
                <td>{record.category}</td>
                <td>{record.customer_project ?? ""}</td>
                <td>{record.tags.join(", ")}</td>
                <td>{formatDate(record.created_at)}</td>
                <td>
                  <button
                    className="icon-button"
                    title="Delete"
                    onClick={(event) => {
                      event.stopPropagation();
                      setSelected(record);
                    }}
                  >
                    <Trash2 size={17} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && (
        <div className="modal-backdrop" onClick={() => setSelected(null)}>
          <div className="modal" onClick={(event) => event.stopPropagation()}>
            <MemoryCard record={selected} />
            <div className="modal-actions">
              <button className="secondary-button" onClick={() => setSelected(null)}>
                Close
              </button>
              <button className="danger-button" onClick={() => remove(selected.memory_id)}>
                <Trash2 size={18} />
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

type AsyncState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; message?: string }
  | { status: "error"; message?: string };

function StateBadge({ state }: { state: AsyncState }) {
  if (state.status === "idle") return null;
  if (state.status === "loading") {
    return (
      <div className="feedback neutral">
        <Loader2 size={16} className="spin" />
        Loading
      </div>
    );
  }
  if (state.status === "error") {
    return (
      <div className="feedback error">
        <CircleAlert size={16} />
        {state.message}
      </div>
    );
  }
  return (
    <div className="feedback success">
      <Check size={16} />
      {state.message ?? "Done"}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}

function MemoryList({ records, compact = false }: { records: MemoryRecord[]; compact?: boolean }) {
  const content = useMemo(() => records, [records]);
  if (!content.length) {
    return <div className="empty-state">No records</div>;
  }

  return (
    <div className={`memory-list ${compact ? "compact" : ""}`}>
      {content.map((record) => (
        <MemoryCard key={record.memory_id} record={record} />
      ))}
    </div>
  );
}

function MemoryCard({ record }: { record: MemoryRecord }) {
  return (
    <article className="memory-card">
      <div className="memory-card-top">
        <div>
          <h3>{record.title}</h3>
          <p>{record.category}</p>
        </div>
        <code>{record.memory_id}</code>
      </div>
      <p className="memory-content">{record.content}</p>
      <div className="meta-row">
        {record.customer_project && <span>{record.customer_project}</span>}
        {record.source && <span>{record.source}</span>}
        {record.created_at && <span>{formatDate(record.created_at)}</span>}
      </div>
      {!!record.tags.length && (
        <div className="tag-row">
          {record.tags.map((tag) => (
            <span key={tag}>{tag}</span>
          ))}
        </div>
      )}
    </article>
  );
}

function formatDate(value: string | null) {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Unexpected error";
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
