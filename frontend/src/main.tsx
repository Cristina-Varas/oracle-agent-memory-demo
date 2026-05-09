import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Archive,
  BookOpen,
  Bot,
  Check,
  CircleAlert,
  Database,
  ExternalLink,
  Home,
  Loader2,
  MessageSquareText,
  Plus,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Trash2,
} from "lucide-react";
import {
  ChatResponse,
  ModelConfig,
  MemoryRecord,
  UsedMemory,
  chatWithMemory,
  createMemory,
  deleteMemory,
  getCategories,
  getHealth,
  getModelConfig,
  listMemories,
  searchMemories,
  testChatModel,
  updateChatModel,
} from "./api";
import "./styles.css";

type View = "home" | "add" | "search" | "chat" | "manage" | "models";
type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  sources?: UsedMemory[];
};

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
  const [view, setView] = useState<View>("home");
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
            active={view === "home"}
            icon={<Home size={18} />}
            label="Home"
            onClick={() => setView("home")}
          />
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
          <NavButton
            active={view === "models"}
            icon={<SlidersHorizontal size={18} />}
            label="Models"
            onClick={() => setView("models")}
          />
        </nav>

        <div className={`status-pill ${apiStatus}`}>
          <span />
          {apiStatus === "checking" ? "Checking API" : apiStatus === "ok" ? "API online" : "API offline"}
        </div>
      </aside>

      <main className="workspace">
        {view === "home" && <HomeView onNavigate={setView} />}
        {view === "add" && <AddMemoryView categories={categories} />}
        {view === "search" && <SearchView categories={categories} />}
        {view === "chat" && <ChatView categories={categories} />}
        {view === "manage" && <ManageView />}
        {view === "models" && <ModelsView />}
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

function HomeView({ onNavigate }: { onNavigate: (view: View) => void }) {
  return (
    <section className="home-page">
      <header className="home-title">
        <div className="home-logo">
          <Database size={28} />
        </div>
        <div>
          <p className="eyebrow">Oracle Agent Memory Workspace</p>
          <h2>Persistent memory for AI agents</h2>
        </div>
      </header>

      <section className="home-hero">
        <div>
          <span className="home-pill">Oracle Agent Memory</span>
          <h3>Capture project knowledge once. Retrieve it when the agent needs context.</h3>
          <p>
            This workspace stores structured, long-term memory for customer engagements,
            architecture decisions, technical issues, demos and follow-up actions. The chat
            experience is read-only: it retrieves saved memory, grounds the answer with
            sources, and never writes new memory automatically.
          </p>
        </div>
        <div className="home-hero-actions">
          <button className="primary-button" onClick={() => onNavigate("add")}>
            <Plus size={18} />
            Add Memory
          </button>
          <button className="secondary-button" onClick={() => onNavigate("chat")}>
            <MessageSquareText size={18} />
            Chat
          </button>
        </div>
      </section>

      <section className="home-info-grid">
        <article className="home-info-card">
          <h3>What is Oracle Agent Memory?</h3>
          <p>
            Oracle Agent Memory provides a persistent memory layer for AI agents. Instead of
            starting from scratch in every interaction, an agent can store, retrieve and reuse
            knowledge across sessions and workflows.
          </p>
          <p>
            In this demo, memory is persisted in Oracle Autonomous Database, indexed with OCI
            Generative AI embeddings, and retrieved semantically through Oracle Agent Memory.
          </p>
        </article>
        <article className="home-info-card">
          <h3>What can you do here?</h3>
          <ul>
            <li>Store customer, project and platform memories.</li>
            <li>Search knowledge with semantic retrieval and filters.</li>
            <li>Ask natural language questions over saved memory.</li>
            <li>Review sources used by each answer.</li>
            <li>Manage and delete memory records explicitly.</li>
          </ul>
        </article>
      </section>

      <section className="home-card-grid">
        <button className="home-nav-card" onClick={() => onNavigate("add")}>
          <Plus size={19} />
          <span>Add Memory</span>
          <p>Capture decisions, notes, issues and next steps.</p>
        </button>
        <button className="home-nav-card" onClick={() => onNavigate("search")}>
          <Search size={19} />
          <span>Search Memories</span>
          <p>Find relevant knowledge across categories and projects.</p>
        </button>
        <button className="home-nav-card" onClick={() => onNavigate("chat")}>
          <Bot size={19} />
          <span>Chat with Memory</span>
          <p>Ask questions grounded in stored memories.</p>
        </button>
        <button className="home-nav-card" onClick={() => onNavigate("manage")}>
          <Archive size={19} />
          <span>Manage Memories</span>
          <p>Review recent memory records and delete them when needed.</p>
        </button>
        <button className="home-nav-card" onClick={() => onNavigate("models")}>
          <SlidersHorizontal size={19} />
          <span>Models</span>
          <p>Review OCI GenAI settings and switch the active chat LLM.</p>
        </button>
      </section>

      <section className="home-docs">
        <div>
          <p className="eyebrow">Official Oracle resources</p>
          <h3>Documentation and product links</h3>
        </div>
        <div className="doc-link-row">
          <a
            className="doc-link"
            href="https://docs.oracle.com/en/database/oracle/agent-memory/"
            target="_blank"
            rel="noreferrer"
          >
            <BookOpen size={18} />
            Oracle Agent Memory docs
            <ExternalLink size={15} />
          </a>
          <a
            className="doc-link"
            href="https://www.oracle.com/artificial-intelligence/ai-agent-memory/"
            target="_blank"
            rel="noreferrer"
          >
            <Database size={18} />
            Product overview
            <ExternalLink size={15} />
          </a>
          <a
            className="doc-link"
            href="https://docs.oracle.com/en/database/oracle/agent-memory/26.4/agmea/run-locally.html"
            target="_blank"
            rel="noreferrer"
          >
            <BookOpen size={18} />
            Run locally guide
            <ExternalLink size={15} />
          </a>
        </div>
      </section>
    </section>
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
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "Ask me about saved memories. I will answer from the memory store and show the sources I used.",
    },
  ]);
  const [state, setState] = useState<AsyncState>({ status: "idle" });
  const [modelConfig, setModelConfig] = useState<ModelConfig | null>(null);
  const latestSources = [...messages].reverse().find((message) => message.sources?.length)?.sources ?? [];

  useEffect(() => {
    getModelConfig()
      .then(setModelConfig)
      .catch(() => setModelConfig(null));
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const nextQuestion = question.trim();
    if (!nextQuestion) return;

    setState({ status: "loading" });
    setQuestion("");
    setMessages((current) => [...current, { role: "user", content: nextQuestion }]);
    try {
      const next = await chatWithMemory({
        question: nextQuestion,
        category: cleanOptional(category),
        customer_project: cleanOptional(project),
      });
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: toPlainAnswer(next.answer),
          sources: next.used_memories,
        },
      ]);
      setState({ status: "success", message: `${next.used_memories.length} source(s)` });
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: getErrorMessage(error),
        },
      ]);
      setState({ status: "error", message: getErrorMessage(error) });
    }
  }

  return (
    <section className="view-grid chat-page">
      <header className="view-header">
        <div>
          <p className="eyebrow">Conversational read only</p>
          <h2>Chat with Memory</h2>
        </div>
        <div className="chat-header-actions">
          <div className="active-model-pill">
            <SlidersHorizontal size={15} />
            {modelConfig?.active_chat_model_id ?? "Model loading"}
          </div>
          <StateBadge state={state} />
        </div>
      </header>

      <div className="conversation-shell">
        <section className="conversation-panel">
          <div className="chat-filters">
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
          </div>
          <div className="message-list">
            {messages.map((message, index) => (
              <ChatBubble key={`${message.role}-${index}`} message={message} />
            ))}
            {state.status === "loading" && (
              <div className="message-row assistant">
                <div className="avatar">
                  <Bot size={17} />
                </div>
                <div className="message-bubble assistant-bubble">
                  <Loader2 size={17} className="spin" />
                  Thinking with memory...
                </div>
              </div>
            )}
          </div>
          <form className="conversation-composer" onSubmit={submit}>
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask about your saved memories"
              required
            />
            <button className="primary-button" disabled={state.status === "loading"}>
              {state.status === "loading" ? <Loader2 size={18} className="spin" /> : <MessageSquareText size={18} />}
              Send
            </button>
          </form>
        </section>

        <aside className="source-panel">
          <div className="source-panel-header">
            <h3>Sources</h3>
            <span>{latestSources.length}</span>
          </div>
          <UsedMemoryList records={latestSources} />
        </aside>
      </div>
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

function ModelsView() {
  const [config, setConfig] = useState<ModelConfig | null>(null);
  const [selectedModelId, setSelectedModelId] = useState("");
  const [provider, setProvider] = useState("cohere");
  const [customModelId, setCustomModelId] = useState("");
  const [useCustom, setUseCustom] = useState(false);
  const [validateModel, setValidateModel] = useState(true);
  const [state, setState] = useState<AsyncState>({ status: "idle" });
  const [testState, setTestState] = useState<AsyncState>({ status: "idle" });

  function selectedCandidate() {
    return {
      modelId: useCustom ? customModelId.trim() : selectedModelId,
      provider,
    };
  }

  async function load() {
    setState({ status: "loading" });
    try {
      const next = await getModelConfig();
      setConfig(next);
      setSelectedModelId(next.active_chat_model_id);
      setProvider(next.active_chat_provider);
      setState({ status: "success", message: "Model config loaded" });
    } catch (error) {
      setState({ status: "error", message: getErrorMessage(error) });
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const { modelId, provider: selectedProvider } = selectedCandidate();
    if (!modelId) {
      setState({ status: "error", message: "Choose or enter a model ID" });
      return;
    }

    setState({ status: "loading" });
    try {
      const next = await updateChatModel({
        model_id: modelId,
        provider: selectedProvider,
        validate: validateModel,
      });
      setConfig(next);
      setSelectedModelId(next.active_chat_model_id);
      setProvider(next.active_chat_provider);
      setUseCustom(false);
      setCustomModelId("");
      setState({ status: "success", message: `Active model: ${next.active_chat_model_id}` });
    } catch (error) {
      setState({ status: "error", message: getErrorMessage(error) });
    }
  }

  async function testSelectedModel() {
    const { modelId, provider: selectedProvider } = selectedCandidate();
    if (!modelId) {
      setTestState({ status: "error", message: "Choose or enter a model ID" });
      return;
    }

    setTestState({ status: "loading" });
    try {
      const result = await testChatModel({
        model_id: modelId,
        provider: selectedProvider,
      });
      setTestState({ status: "success", message: result.message });
    } catch (error) {
      setTestState({ status: "error", message: getErrorMessage(error) });
    }
  }

  return (
    <section className="view-grid models-page">
      <header className="view-header">
        <div>
          <p className="eyebrow">OCI Generative AI</p>
          <h2>Models</h2>
        </div>
        <StateBadge state={state} />
      </header>

      <section className="model-summary-grid">
        <article className="model-summary-card">
          <span>Active chat model</span>
          <strong>{config?.active_chat_model_id ?? "Loading"}</strong>
          <p>Used by Chat with Memory and the /chat API endpoint.</p>
        </article>
        <article className="model-summary-card">
          <span>Embedding model</span>
          <strong>{config?.embedding_model_id ?? "Loading"}</strong>
          <p>
            Fixed at {config?.embedding_dimensions ?? 1024} dimensions for the current vector schema.
          </p>
        </article>
      </section>

      <form className="model-settings" onSubmit={submit}>
        <div className="model-settings-header">
          <div>
            <h3>Switch chat LLM</h3>
            <p>
              Changing the chat model affects future answers only. Stored memories and embeddings are not rewritten.
            </p>
          </div>
          <button type="button" className="secondary-button" onClick={load}>
            <RefreshCw size={18} />
            Refresh
          </button>
        </div>
        <StateBadge state={testState} />

        <div className="model-option-list">
          {config?.chat_model_options.map((option) => (
            <label
              className={`model-option ${!useCustom && selectedModelId === option.model_id ? "selected" : ""}`}
              key={option.model_id}
            >
              <input
                type="radio"
                name="chat-model"
                checked={!useCustom && selectedModelId === option.model_id}
                onChange={() => {
                  setUseCustom(false);
                  setSelectedModelId(option.model_id);
                  setProvider(option.provider);
                }}
              />
              <div>
                <strong>{option.label}</strong>
                <code>{option.model_id}</code>
                <p>{option.description}</p>
              </div>
            </label>
          ))}
        </div>

        <label className={`model-option custom ${useCustom ? "selected" : ""}`}>
          <input
            type="radio"
            name="chat-model"
            checked={useCustom}
            onChange={() => setUseCustom(true)}
          />
          <div className="custom-model-fields">
            <strong>Custom OCI chat model</strong>
            <div className="field-row two">
              <Field label="Model ID">
                <input
                  value={customModelId}
                  onChange={(event) => {
                    setUseCustom(true);
                    setCustomModelId(event.target.value);
                  }}
                  placeholder="cohere.command-a-03-2025"
                />
              </Field>
              <Field label="Provider">
                <input value={provider} onChange={(event) => setProvider(event.target.value)} />
              </Field>
            </div>
          </div>
        </label>

        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={validateModel}
            onChange={(event) => setValidateModel(event.target.checked)}
          />
          Validate model with OCI before saving
        </label>

        <div className="action-row">
          <button
            className="secondary-button"
            disabled={testState.status === "loading" || state.status === "loading"}
            onClick={testSelectedModel}
            type="button"
          >
            {testState.status === "loading" ? <Loader2 size={18} className="spin" /> : <Check size={18} />}
            Test Model
          </button>
          <button className="primary-button" disabled={state.status === "loading"}>
            {state.status === "loading" ? <Loader2 size={18} className="spin" /> : <SlidersHorizontal size={18} />}
            Save Active Model
          </button>
        </div>
      </form>
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

function UsedMemoryList({ records }: { records: UsedMemory[] }) {
  if (!records.length) {
    return <div className="empty-state">No sources</div>;
  }

  return (
    <div className="memory-list compact">
      {records.map((record, index) => (
        <article className="memory-card" key={`${record.title}-${index}`}>
          <div className="memory-card-top">
            <div>
              <h3>{record.title}</h3>
              <p>{record.category}</p>
            </div>
          </div>
          <p className="memory-content">{record.content_preview}</p>
          <div className="meta-row">
            {record.customer_project && <span>{record.customer_project}</span>}
            {record.source && <span>{record.source}</span>}
            {record.score !== null && <span>Score {record.score.toFixed(3)}</span>}
          </div>
        </article>
      ))}
    </div>
  );
}

function ChatBubble({ message }: { message: ChatMessage }) {
  return (
    <div className={`message-row ${message.role}`}>
      <div className="avatar">
        {message.role === "assistant" ? <Bot size={17} /> : <span>{userInitial()}</span>}
      </div>
      <div className={`message-bubble ${message.role}-bubble`}>
        <p>{message.content}</p>
        {!!message.sources?.length && (
          <div className="message-source-count">{message.sources.length} source(s)</div>
        )}
      </div>
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

function toPlainAnswer(value: string) {
  return value
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/^\s*[-*]\s+/gm, "")
    .replace(/^\s*\d+\.\s+/gm, "")
    .trim();
}

function userInitial() {
  return "C";
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
