import {
  ArrowUp,
  Bot,
  FileText,
  Link2,
  Loader2,
  Moon,
  Paperclip,
  RefreshCw,
  SlidersHorizontal,
  Sparkles,
  Sun,
  Trash2,
  User,
  X,
} from "lucide-react";
import { type DragEvent, type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const API_BASE = (import.meta.env.VITE_BACKEND_URL ?? "").replace(/\/$/, "");

type ThemeMode = "system" | "light" | "dark";

type CaseRow = {
  unk?: string;
  spc?: string;
  project_name?: string;
  employee?: string;
  technology?: string;
  grade?: string;
  source?: string;
  demand?: string;
  commentary?: string;
  expert_analyze?: string;
  readiness?: string;
  date?: string;
  sheet?: string;
};

type CaseOptionsResponse = {
  items: CaseRow[];
  filters: Record<string, string[]>;
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  files?: string[];
  links?: string[];
  resource_context?: string;
};

type ChatResponse = {
  answer: string;
  resource_context?: string;
};

const filterFields: Array<[keyof CaseRow, string]> = [
  ["project_name", "Проект"],
  ["employee", "Сотрудник"],
  ["technology", "Технология"],
  ["grade", "Грейд"],
  ["source", "Источник"],
  ["date", "Дата"],
];

function getId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function extractLinks(text: string) {
  return Array.from(new Set(text.match(/https?:\/\/[^\s<>()"']+/gi)?.map((url) => url.replace(/[.,;:!?)]}]+$/, "")) ?? []));
}

function normalize(value: unknown) {
  return String(value ?? "").trim();
}

function filterCases(cases: CaseRow[], filters: Record<string, string>) {
  return cases.filter((item) =>
    Object.entries(filters).every(([field, value]) => !value || normalize(item[field as keyof CaseRow]) === value),
  );
}

function uniqueValues(cases: CaseRow[], field: keyof CaseRow) {
  return Array.from(new Set(cases.map((item) => normalize(item[field])).filter(Boolean))).sort((a, b) =>
    a.localeCompare(b, "ru", { sensitivity: "base" }),
  );
}

function selectedContext(filters: Record<string, string>) {
  return Object.fromEntries(Object.entries(filters).filter(([, value]) => Boolean(value)));
}

function MessageContent({ text }: { text: string }) {
  return (
    <div className="message-text">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
    </div>
  );
}

function ThemeIcon({ mode }: { mode: ThemeMode }) {
  if (mode === "light") return <Sun size={16} />;
  if (mode === "dark") return <Moon size={16} />;
  return <Sparkles size={16} />;
}

export function App() {
  const [theme, setTheme] = useState<ThemeMode>(() => (localStorage.getItem("theme") as ThemeMode | null) ?? "system");
  const [caseOptions, setCaseOptions] = useState<CaseOptionsResponse>({ items: [], filters: {} });
  const [casesLoading, setCasesLoading] = useState(true);
  const [casesError, setCasesError] = useState("");
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [isDraggingFiles, setIsDraggingFiles] = useState(false);
  const [sending, setSending] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const dragDepthRef = useRef(0);

  const cases = caseOptions.items;
  const activeFilters = useMemo(() => Object.fromEntries(Object.entries(filters).filter(([, value]) => value)), [filters]);
  const matchingCases = useMemo(() => filterCases(cases, activeFilters), [cases, activeFilters]);

  useEffect(() => {
    localStorage.setItem("theme", theme);
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    void loadCases();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [history, sending]);

  useEffect(() => {
    const element = textareaRef.current;
    if (!element) return;
    element.style.height = "0px";
    element.style.height = `${Math.min(element.scrollHeight, 180)}px`;
  }, [draft]);

  async function loadCases() {
    setCasesLoading(true);
    setCasesError("");
    try {
      const response = await fetch(`${API_BASE}/api/v1/cases/options?limit=2000`);
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      setCaseOptions((await response.json()) as CaseOptionsResponse);
    } catch (error) {
      setCasesError(error instanceof Error ? error.message : "Не удалось загрузить кейсы");
    } finally {
      setCasesLoading(false);
    }
  }

  function updateFilter(field: string, value: string) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  function clearChat() {
    setHistory([]);
    setDraft("");
    setFiles([]);
  }

  function addFiles(incomingFiles: FileList | File[]) {
    const nextFiles = Array.from(incomingFiles);
    if (!nextFiles.length) return;

    setFiles((current) => {
      const knownFiles = new Set(current.map((file) => `${file.name}-${file.size}-${file.lastModified}`));
      const uniqueFiles = nextFiles.filter((file) => {
        const key = `${file.name}-${file.size}-${file.lastModified}`;
        if (knownFiles.has(key)) return false;
        knownFiles.add(key);
        return true;
      });
      return [...current, ...uniqueFiles];
    });
  }

  function removeFile(name: string, lastModified: number) {
    setFiles((current) => current.filter((file) => file.name !== name || file.lastModified !== lastModified));
  }

  function hasDraggedFiles(event: DragEvent) {
    return Array.from(event.dataTransfer.types).includes("Files");
  }

  function handleDragEnter(event: DragEvent<HTMLElement>) {
    if (!hasDraggedFiles(event)) return;
    event.preventDefault();
    dragDepthRef.current += 1;
    setIsDraggingFiles(true);
  }

  function handleDragOver(event: DragEvent<HTMLElement>) {
    if (!hasDraggedFiles(event)) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
  }

  function handleDragLeave(event: DragEvent<HTMLElement>) {
    if (!hasDraggedFiles(event)) return;
    event.preventDefault();
    dragDepthRef.current = Math.max(0, dragDepthRef.current - 1);
    if (dragDepthRef.current === 0) {
      setIsDraggingFiles(false);
    }
  }

  function handleDrop(event: DragEvent<HTMLElement>) {
    if (!hasDraggedFiles(event)) return;
    event.preventDefault();
    dragDepthRef.current = 0;
    setIsDraggingFiles(false);
    addFiles(event.dataTransfer.files);
  }

  async function sendMessage(event?: FormEvent) {
    event?.preventDefault();
    const content = draft.trim();
    if ((!content && files.length === 0) || sending) return;

    const userMessage: ChatMessage = {
      id: getId(),
      role: "user",
      content: content || "Проанализируй прикрепленные файлы.",
      files: files.map((file) => file.name),
      links: extractLinks(content),
    };
    const nextHistory = [...history, userMessage];

    setHistory(nextHistory);
    setDraft("");
    setFiles([]);
    setSending(true);

    try {
      const payload = new FormData();
      payload.append(
        "messages",
        JSON.stringify(
          nextHistory.slice(-20).map((message) => ({
            role: message.role,
            content: message.content,
            resource_context: message.resource_context ?? "",
          })),
        ),
      );
      payload.append("context", JSON.stringify(selectedContext(activeFilters), null, 2));
      files.forEach((file) => payload.append("files", file));

      const response = await fetch(`${API_BASE}/api/v1/chat/multipart`, {
        method: "POST",
        body: payload,
      });
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      const data = (await response.json()) as ChatResponse;
      const enrichedHistory = nextHistory.map((message) =>
        message.id === userMessage.id ? { ...message, resource_context: data.resource_context ?? "" } : message,
      );
      setHistory([
        ...enrichedHistory,
        {
          id: getId(),
          role: "assistant",
          content: data.answer,
        },
      ]);
    } catch (error) {
      setHistory([
        ...nextHistory,
        {
          id: getId(),
          role: "assistant",
          content: `Ошибка обращения к backend: ${error instanceof Error ? error.message : "неизвестная ошибка"}`,
        },
      ]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? "open" : ""}`}>
        <div className="sidebar-header">
          <div>
            <div className="eyebrow">Rejects Analyzer</div>
            <h1>Анализ отказов</h1>
          </div>
          <button className="icon-button mobile-only" type="button" onClick={() => setSidebarOpen(false)} title="Закрыть">
            <X size={18} />
          </button>
        </div>

        <div className="status-card">
          <div>
            <span>Кейсов</span>
            <strong>{cases.length}</strong>
          </div>
          <div>
            <span>Подходит</span>
            <strong>{matchingCases.length}</strong>
          </div>
        </div>

        <button className="secondary-button" type="button" onClick={loadCases} disabled={casesLoading}>
          {casesLoading ? <Loader2 className="spin" size={16} /> : <RefreshCw size={16} />}
          Обновить таблицу
        </button>

        {casesError ? <div className="error-banner">{casesError}</div> : null}

        <div className="filters">
          {filterFields.map(([field, label]) => {
            const withoutCurrent = Object.fromEntries(
              Object.entries(activeFilters).filter(([name]) => name !== field),
            );
            const availableCases = filterCases(cases, withoutCurrent);
            const options = Object.keys(withoutCurrent).length
              ? uniqueValues(availableCases, field)
              : caseOptions.filters[field] ?? uniqueValues(availableCases, field);

            return (
              <label className="field" key={field}>
                <span>{label}</span>
                <select value={filters[field] ?? ""} onChange={(event) => updateFilter(field, event.target.value)}>
                  <option value="">Все</option>
                  {options.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>
            );
          })}
        </div>

        <div className="sidebar-footer">
          <label className="field">
            <span>Тема</span>
            <div className="theme-control">
              {(["system", "light", "dark"] as ThemeMode[]).map((mode) => (
                <button
                  className={theme === mode ? "theme-active" : ""}
                  key={mode}
                  type="button"
                  onClick={() => setTheme(mode)}
                  title={mode === "system" ? "Системная" : mode === "light" ? "Светлая" : "Темная"}
                >
                  <ThemeIcon mode={mode} />
                  <span>{mode === "system" ? "System" : mode === "light" ? "Light" : "Dark"}</span>
                </button>
              ))}
            </div>
          </label>
        </div>
      </aside>

      <main
        className={`chat-shell ${isDraggingFiles ? "drag-active" : ""}`}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <header className="topbar">
          <button className="icon-button mobile-only" type="button" onClick={() => setSidebarOpen(true)} title="Фильтры">
            <SlidersHorizontal size={18} />
          </button>
          <button className="icon-button" type="button" onClick={clearChat} title="Очистить чат">
            <Trash2 size={18} />
          </button>
        </header>

        <section className="messages">
          {history.length === 0 ? (
            <div className="empty-state">
              <div className="empty-mark">
                <Bot size={30} />
              </div>
              <h2>Чат по отказам интервью</h2>
              <p>Выберите кейс в фильтрах, задайте вопрос, прикрепите файл или вставьте ссылку в сообщение.</p>
              <div className="quick-prompts">
                {[
                  "Суммаризируй причины отказов по выбранному проекту",
                  "Найди повторяющиеся паттерны по грейдам",
                  "Сравни кейс с похожими отказами",
                ].map((prompt) => (
                  <button key={prompt} type="button" onClick={() => setDraft(prompt)}>
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            history.map((message) => (
              <article className={`message ${message.role}`} key={message.id}>
                <div className="avatar">{message.role === "user" ? <User size={17} /> : <Bot size={17} />}</div>
                <div className="bubble">
                  <MessageContent text={message.content} />
                  {message.files?.length || message.links?.length ? (
                    <div className="chips">
                      {message.files?.map((file) => (
                        <span className="chip" key={file}>
                          <FileText size={14} />
                          {file}
                        </span>
                      ))}
                      {message.links?.map((link) => (
                        <span className="chip" key={link}>
                          <Link2 size={14} />
                          {link}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>
              </article>
            ))
          )}

          {sending ? (
            <article className="message assistant">
              <div className="avatar">
                <Bot size={17} />
              </div>
              <div className="bubble typing">
                <Loader2 className="spin" size={16} />
                Анализирую
              </div>
            </article>
          ) : null}
          <div ref={bottomRef} />
        </section>

        <form className="composer" onSubmit={sendMessage}>
          {isDraggingFiles ? (
            <div className="drop-target">
              <Paperclip size={18} />
              Отпустите файл, чтобы прикрепить его к сообщению
            </div>
          ) : null}

          {files.length ? (
            <div className="attachment-row">
              {files.map((file) => (
                <button
                  className="attachment"
                  key={`${file.name}-${file.lastModified}`}
                  type="button"
                  onClick={() => removeFile(file.name, file.lastModified)}
                  title="Убрать файл"
                >
                  <FileText size={14} />
                  <span>{file.name}</span>
                  <X size={14} />
                </button>
              ))}
            </div>
          ) : null}

          <div className="composer-box">
            <button
              className="icon-button"
              type="button"
              onClick={() => fileInputRef.current?.click()}
              title="Прикрепить файл"
            >
              <Paperclip size={19} />
            </button>
            <textarea
              ref={textareaRef}
              rows={1}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void sendMessage();
                }
              }}
              placeholder="Задайте ваш вопрос"
            />
            <button className="send-button" type="submit" disabled={sending || (!draft.trim() && files.length === 0)}>
              {sending ? <Loader2 className="spin" size={18} /> : <ArrowUp size={18} />}
            </button>
            <input
              className="file-input"
              ref={fileInputRef}
              type="file"
              multiple
              onChange={(event) => {
                addFiles(event.target.files ?? []);
                event.currentTarget.value = "";
              }}
            />
          </div>
        </form>
      </main>
    </div>
  );
}
