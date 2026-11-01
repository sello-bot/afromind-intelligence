"use client";

import type { FormEvent } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowUp,
  BrainCircuit,
  ChevronLeft,
  MessageSquarePlus,
  Plus,
  Sparkles,
  Trash2,
  Zap,
  Command,
  PanelLeftClose,
  X,
} from "lucide-react";

type Conversation = {
  id: string;
  title: string;
  created_at: string;
};

type Message = {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
};

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const OWNER_KEY = "luna_owner_id";

function getOwnerId() {
  if (typeof window === "undefined") return "";

  let id = localStorage.getItem(OWNER_KEY);

  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(OWNER_KEY, id);
  }

  return id;
}

const suggestions = [
  {
    icon: BrainCircuit,
    title: "Explore an idea",
    description: "Think through a complex problem",
    prompt: "Help me explore and develop an idea.",
  },
  {
    icon: Command,
    title: "Write some code",
    description: "Build, debug and understand code",
    prompt: "Help me write or debug some code.",
  },
  {
    icon: Activity,
    title: "Analyse data",
    description: "Discover patterns and insights",
    prompt: "Help me analyse a dataset and discover insights.",
  },
  {
    icon: Zap,
    title: "Automate a task",
    description: "Design a smarter workflow",
    prompt: "Help me design an automated workflow.",
  },
];

export default function Home() {
  const [ownerId, setOwnerId] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [activeId, setActiveId] = useState("");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setOwnerId(getOwnerId());
  }, []);

  useEffect(() => {
    if (!ownerId) return;

    fetch(
      `${API}/api/conversations?owner_id=${encodeURIComponent(ownerId)}`
    )
      .then((response) => {
        if (!response.ok) throw new Error("Unable to load conversations");
        return response.json();
      })
      .then(setConversations)
      .catch(() =>
        setError("Cannot reach Afromind Intelligence. Check that the backend is running.")
      );
  }, [ownerId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function openConversation(id: string) {
    try {
      setError("");

      const response = await fetch(
        `${API}/api/conversations/${id}?owner_id=${encodeURIComponent(ownerId)}`
      );

      if (!response.ok) throw new Error("Could not open this conversation.");

      setMessages(await response.json());
      setActiveId(id);
      setSidebarOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to open conversation.");
    }
  }

  function newChat() {
    setActiveId("");
    setMessages([]);
    setInput("");
    setError("");
    setSidebarOpen(false);
    textareaRef.current?.focus();
  }

  async function removeConversation(id: string) {
    try {
      const response = await fetch(
        `${API}/api/conversations/${id}?owner_id=${encodeURIComponent(ownerId)}`,
        { method: "DELETE" }
      );

      if (!response.ok) throw new Error("Could not delete conversation.");

      setConversations((items) => items.filter((item) => item.id !== id));

      if (activeId === id) {
        setActiveId("");
        setMessages([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete conversation.");
    }
  }

  async function sendMessage(event: FormEvent) {
    event.preventDefault();

    const text = input.trim();

    if (!text || loading || !ownerId) return;

    setInput("");
    setError("");
    setLoading(true);

    const tempUser: Message = {
      id: crypto.randomUUID(),
      conversation_id: activeId,
      role: "user",
      content: text,
    };

    const tempAssistant: Message = {
      id: crypto.randomUUID(),
      conversation_id: activeId,
      role: "assistant",
      content: "",
    };

    setMessages((current) => [...current, tempUser, tempAssistant]);

    try {
      const response = await fetch(`${API}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          owner_id: ownerId,
          conversation_id: activeId || null,
          message: text,
          model: null,
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error(await response.text());
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let buffer = "";
      let assistantText = "";
      let conversationId = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const event of events) {
          const dataLine = event
            .split("\n")
            .find((line) => line.startsWith("data: "));

          if (!dataLine) continue;

          const data = JSON.parse(dataLine.slice(6));

          if (data.token) {
            assistantText += data.token;

            setMessages((current) =>
              current.map((message) =>
                message.id === tempAssistant.id
                  ? { ...message, content: assistantText }
                  : message
              )
            );
          }

          if (data.conversation_id) {
            conversationId = data.conversation_id;
          }

          if (data.error) {
            throw new Error(data.error);
          }
        }
      }

      if (conversationId) setActiveId(conversationId);

      const list = await fetch(
        `${API}/api/conversations?owner_id=${encodeURIComponent(ownerId)}`
      );

      if (list.ok) setConversations(await list.json());

      if (!assistantText) {
        throw new Error("LUNA returned an empty response. Check the AI provider.");
      }
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Something went wrong.";

      setError(message);

      setMessages((current) =>
        current.filter((item) => item.id !== tempAssistant.id)
      );
    } finally {
      setLoading(false);
    }
  }

  const hasMessages = messages.length > 0;

  return (
    <main className="relative flex h-[100dvh] overflow-hidden bg-[#080507] text-[#F5F1F2] selection:bg-[#FF1744]/30">
      {/* Ambient background */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-64 left-[35%] h-[550px] w-[550px] rounded-full bg-[#B00020]/[0.09] blur-[140px]" />
        <div className="absolute bottom-[-300px] right-[10%] h-[500px] w-[500px] rounded-full bg-[#FF1744]/[0.05] blur-[140px]" />
      </div>

      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <button
          aria-label="Close sidebar"
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 z-30 bg-black/70 backdrop-blur-sm md:hidden"
        />
      )}

      {/* Sidebar */}
      <aside
        className={`${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        } fixed inset-y-0 left-0 z-40 flex w-[280px] shrink-0 flex-col border-r border-white/[0.07] bg-[#0D090C] transition-transform duration-300 md:relative md:translate-x-0 ${
          sidebarOpen ? "md:flex" : "md:hidden"
        }`}
      >
        <div className="flex h-[82px] items-center justify-between border-b border-white/[0.06] px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-[#FF1744]/30 bg-[#FF1744]/[0.09] text-[#FF385C] shadow-[0_0_25px_rgba(255,23,68,0.13)]">
              <BrainCircuit size={24} />
            </div>

            <div>
              <div className="text-[15px] font-semibold tracking-wide">
                AFROMIND
              </div>
              <div className="text-[10px] font-semibold uppercase tracking-[0.25em] text-[#FF385C]">
                Intelligence
              </div>
            </div>
          </div>

          <button
            onClick={() => setSidebarOpen(false)}
            className="rounded-lg p-2 text-white/40 hover:bg-white/5 hover:text-white md:hidden"
            aria-label="Close navigation"
          >
            <X size={18} />
          </button>
        </div>

        <div className="px-4 pt-6">
          <button
            onClick={newChat}
            className="group flex w-full items-center gap-3 rounded-xl border border-[#FF1744]/30 bg-gradient-to-r from-[#FF1744]/15 to-[#B00020]/[0.04] px-4 py-3.5 text-sm font-medium text-white transition hover:border-[#FF1744]/60 hover:shadow-[0_0_25px_rgba(255,23,68,0.10)]"
          >
            <MessageSquarePlus size={18} className="text-[#FF385C]" />
            New conversation
            <Plus size={16} className="ml-auto text-white/40 transition group-hover:text-[#FF385C]" />
          </button>
        </div>

        <div className="mb-3 mt-9 flex items-center justify-between px-6">
          <span className="text-[10px] font-semibold uppercase tracking-[0.22em] text-white/35">
            Your conversations
          </span>
          <span className="text-[10px] text-white/25">
            {conversations.length}
          </span>
        </div>

        <div className="flex-1 space-y-1 overflow-y-auto px-3">
          {conversations.map((conversation) => (
            <div
              key={conversation.id}
              className={`group flex items-center gap-2 rounded-lg border px-3 py-2.5 transition ${
                activeId === conversation.id
                  ? "border-[#FF1744]/20 bg-[#FF1744]/[0.08]"
                  : "border-transparent hover:bg-white/[0.035]"
              }`}
            >
              <button
                onClick={() => openConversation(conversation.id)}
                className="min-w-0 flex-1 truncate text-left text-xs text-white/65 transition hover:text-white"
              >
                {conversation.title}
              </button>

              <button
                onClick={() => removeConversation(conversation.id)}
                aria-label="Delete conversation"
                className="shrink-0 text-white/20 opacity-0 transition hover:text-[#FF385C] group-hover:opacity-100"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}

          {conversations.length === 0 && (
            <div className="px-3 py-5 text-xs leading-6 text-white/30">
              Your conversations will appear here when you start talking to LUNA.
            </div>
          )}
        </div>

        {/* Sidebar identity */}
        <div className="border-t border-white/[0.07] p-4">
          <div className="rounded-xl border border-[#FF1744]/15 bg-[#FF1744]/[0.045] p-4">
            <div className="flex items-center gap-2 text-[#FF385C]">
              <Zap size={16} />
              <span className="text-xs font-semibold">Afromind Agents</span>
            </div>
            <p className="mt-2 text-[11px] leading-5 text-white/40">
              Intelligence that moves beyond conversation.
            </p>
            <div className="mt-3 text-[10px] font-medium uppercase tracking-wider text-[#FF385C]/80">
              The Execution Layer
            </div>
          </div>

          <div className="mt-4 flex items-center gap-3 px-1">
            <div className="flex h-9 w-9 items-center justify-center rounded-full border border-[#FF1744]/30 bg-[#FF1744]/10 text-xs font-semibold text-[#FF526D]">
              SK
            </div>
            <div>
              <div className="text-xs font-medium text-white/85">
                Afromind Workspace
              </div>
              <div className="mt-0.5 text-[10px] text-white/35">
                LUNA AI · The Intelligence
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main workspace */}
      <section className="relative z-10 flex min-w-0 flex-1 flex-col">
        {/* Top navigation */}
        <header className="flex h-[76px] shrink-0 items-center justify-between border-b border-white/[0.07] bg-[#0A0709]/75 px-4 backdrop-blur-xl md:px-8">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              aria-label="Toggle sidebar"
              className="rounded-lg border border-white/[0.08] p-2.5 text-white/50 transition hover:border-[#FF1744]/30 hover:text-white"
            >
              {sidebarOpen ? (
                <PanelLeftClose size={17} />
              ) : (
                <ChevronLeft size={17} />
              )}
            </button>

            <div>
              <div className="text-sm font-semibold tracking-wide">
                LUNA AI
              </div>
              <div className="mt-0.5 text-[10px] text-white/35">
                Afromind Intelligence
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.025] px-3 py-2 sm:flex">
              <span className="h-1.5 w-1.5 rounded-full bg-[#FF385C] shadow-[0_0_9px_#FF1744]" />
              <span className="text-[10px] text-white/55">
                AI workspace
              </span>
            </div>

            <div className="rounded-lg border border-[#FF1744]/20 bg-[#FF1744]/[0.07] px-3 py-2 text-[10px] font-semibold tracking-wide text-[#FF526D]">
              QUANTUM RED
            </div>
          </div>
        </header>

        {/* Chat area */}
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto flex min-h-full w-full max-w-5xl flex-col px-4 pb-8 pt-8 md:px-10 md:pt-12">
            {!hasMessages ? (
              <div className="flex flex-1 flex-col justify-center pb-8">
                {/* Welcome section */}
                <div className="relative mb-10 overflow-hidden rounded-3xl border border-[#FF1744]/15 bg-gradient-to-br from-[#19090F] via-[#10090D] to-[#0A0709] p-6 shadow-[0_20px_80px_rgba(0,0,0,0.25)] md:p-10">
                  <div className="pointer-events-none absolute -right-20 -top-28 h-72 w-72 rounded-full border border-[#FF1744]/10 shadow-[0_0_100px_rgba(255,23,68,0.10)]" />
                  <div className="pointer-events-none absolute right-10 top-10 h-40 w-40 rounded-full bg-[#FF1744]/[0.08] blur-[70px]" />

                  <div className="relative z-10 max-w-2xl">
                    <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-[#FF1744]/25 bg-[#FF1744]/[0.08] px-3 py-1.5">
                      <Sparkles size={13} className="text-[#FF526D]" />
                      <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#FF526D]">
                        The Intelligence Layer
                      </span>
                    </div>

                    <h1 className="text-3xl font-semibold leading-tight tracking-tight text-white md:text-5xl">
                      Think beyond.
                      <br />
                      <span className="bg-gradient-to-r from-[#FF385C] via-[#FF1744] to-[#B00020] bg-clip-text text-transparent">
                        Build what's next.
                      </span>
                    </h1>

                    <p className="mt-5 max-w-lg text-sm leading-7 text-white/50 md:text-base">
                      Meet LUNA AI, your intelligent workspace for ideas,
                      research, development and discovery — powered by
                      Afromind Intelligence.
                    </p>

                    <div className="mt-8 flex flex-wrap items-center gap-3">
                      <div className="flex items-center gap-2 text-[10px] text-white/40">
                        <span className="h-1.5 w-1.5 rounded-full bg-[#FF385C]" />
                        Intelligence
                      </div>
                      <span className="text-white/15">/</span>
                      <div className="flex items-center gap-2 text-[10px] text-white/40">
                        <span className="h-1.5 w-1.5 rounded-full bg-[#FF385C]" />
                        Creativity
                      </div>
                      <span className="text-white/15">/</span>
                      <div className="flex items-center gap-2 text-[10px] text-white/40">
                        <span className="h-1.5 w-1.5 rounded-full bg-[#FF385C]" />
                        Execution
                      </div>
                    </div>
                  </div>

                  <div className="pointer-events-none absolute bottom-[-50px] right-[-35px] hidden h-64 w-64 items-center justify-center md:flex">
                    <div className="absolute h-52 w-52 rounded-full border border-[#FF1744]/10" />
                    <div className="absolute h-40 w-40 rounded-full border border-[#FF1744]/15" />
                    <div className="absolute h-28 w-28 rounded-full border border-[#FF1744]/20" />
                    <div className="flex h-20 w-20 items-center justify-center rounded-3xl border border-[#FF1744]/35 bg-[#FF1744]/10 text-[#FF385C] shadow-[0_0_65px_rgba(255,23,68,0.2)]">
                      <BrainCircuit size={37} />
                    </div>
                  </div>
                </div>

                {/* Suggestions */}
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <div className="text-sm font-semibold text-white/85">
                      Where should we begin?
                    </div>
                    <div className="mt-1 text-xs text-white/35">
                      Choose a starting point or ask LUNA anything.
                    </div>
                  </div>
                  <span className="hidden text-[10px] uppercase tracking-wider text-white/25 sm:block">
                    Suggested prompts
                  </span>
                </div>

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {suggestions.map((item) => {
                    const Icon = item.icon;

                    return (
                      <button
                        key={item.title}
                        onClick={() => {
                          setInput(item.prompt);
                          textareaRef.current?.focus();
                        }}
                        className="group flex items-start gap-4 rounded-2xl border border-white/[0.08] bg-white/[0.02] p-4 text-left transition duration-200 hover:-translate-y-0.5 hover:border-[#FF1744]/35 hover:bg-[#FF1744]/[0.045]"
                      >
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-[#FF1744]/20 bg-[#FF1744]/[0.08] text-[#FF526D] transition group-hover:border-[#FF1744]/40 group-hover:shadow-[0_0_20px_rgba(255,23,68,0.12)]">
                          <Icon size={18} />
                        </div>

                        <div>
                          <div className="text-sm font-medium text-white/85">
                            {item.title}
                          </div>
                          <div className="mt-1 text-xs leading-5 text-white/35">
                            {item.description}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="space-y-8 py-5">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex gap-3 md:gap-4 ${
                      message.role === "user"
                        ? "justify-end"
                        : "justify-start"
                    }`}
                  >
                    {message.role === "assistant" && (
                      <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-[#FF1744]/25 bg-[#FF1744]/[0.09] text-[#FF526D] shadow-[0_0_20px_rgba(255,23,68,0.08)]">
                        <Sparkles size={17} />
                      </div>
                    )}

                   <div
  className={`max-w-[88%] text-sm leading-7 md:max-w-[80%] ${
    message.role === "user"
      ? "whitespace-pre-wrap rounded-2xl rounded-br-md border border-[#FF1744]/20 bg-[#FF1744]/[0.12] px-4 py-3 text-white/90"
      : "rounded-2xl border border-white/[0.06] bg-white/[0.025] px-4 py-3 text-white/80 md:px-5"
  }`}
>
  {message.role === "assistant" && message.content ? (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeHighlight]}
      components={{
        h1: ({ children }) => (
          <h1 className="mb-4 mt-5 text-xl font-bold text-white">
            {children}
          </h1>
        ),
        h2: ({ children }) => (
          <h2 className="mb-3 mt-5 text-lg font-bold text-white">
            {children}
          </h2>
        ),
        h3: ({ children }) => (
          <h3 className="mb-2 mt-4 text-base font-semibold text-white">
            {children}
          </h3>
        ),
        p: ({ children }) => (
          <p className="mb-3 leading-7 last:mb-0">{children}</p>
        ),
        strong: ({ children }) => (
          <strong className="font-bold text-white">{children}</strong>
        ),
        ul: ({ children }) => (
          <ul className="mb-4 ml-5 list-disc space-y-2">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="mb-4 ml-5 list-decimal space-y-2">{children}</ol>
        ),
        li: ({ children }) => <li className="pl-1">{children}</li>,
        blockquote: ({ children }) => (
          <blockquote className="my-4 border-l-2 border-[#FF1744] pl-4 text-white/60">
            {children}
          </blockquote>
        ),
        a: ({ children, href }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[#FF526D] underline underline-offset-4 hover:text-white"
          >
            {children}
          </a>
        ),
        pre: ({ children }) => (
          <pre className="my-4 overflow-x-auto rounded-xl border border-white/10 bg-[#080507] p-4 text-xs leading-6">
            {children}
          </pre>
        ),
        code: ({ children, className }) => (
          <code
            className={`${className || ""} rounded bg-white/[0.07] px-1.5 py-0.5 font-mono text-[0.9em] text-[#FF8294]`}
          >
            {children}
          </code>
        ),
      }}
    >
      {message.content}
    </ReactMarkdown>
  ) : (
    message.content ||
    (loading && message.role === "assistant" ? (
      <span className="animate-pulse text-[#FF526D]">
        LUNA is thinking...
      </span>
    ) : null)
  )}
</div> 
                  </div>
                ))}

                <div ref={bottomRef} />
              </div>
            )}

            {error && (
              <div className="mt-5 rounded-xl border border-[#FF1744]/25 bg-[#FF1744]/[0.07] p-4 text-xs leading-6 text-[#FF8294]">
                {error}
              </div>
            )}
          </div>
        </div>

        {/* Message composer */}
        <div className="shrink-0 border-t border-white/[0.05] bg-[#080507]/85 px-4 pb-4 pt-4 backdrop-blur-xl md:px-8 md:pb-6">
          <form onSubmit={sendMessage} className="mx-auto max-w-4xl">
            <div className="rounded-2xl border border-white/[0.12] bg-[#120B0F] p-3 shadow-[0_12px_55px_rgba(0,0,0,0.35)] transition duration-200 focus-within:border-[#FF1744]/55 focus-within:shadow-[0_0_35px_rgba(255,23,68,0.08)]">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    sendMessage(event as unknown as FormEvent);
                  }
                }}
                placeholder="Ask LUNA AI anything..."
                rows={2}
                className="max-h-40 w-full resize-none bg-transparent px-2 py-2 text-sm leading-6 text-white outline-none placeholder:text-white/30"
              />

              <div className="flex items-center justify-between border-t border-white/[0.05] px-1 pt-3">
                <div className="flex items-center gap-2 text-[10px] text-white/30">
                  <Sparkles size={12} className="text-[#FF526D]" />
                  <span className="hidden sm:inline">
                    Intelligence, built for what's next.
                  </span>
                  <span className="sm:hidden">LUNA AI</span>
                </div>

                <button
                  disabled={!input.trim() || loading}
                  type="submit"
                  aria-label="Send message"
                  className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-[#FF385C] to-[#B00020] text-white shadow-[0_0_22px_rgba(255,23,68,0.25)] transition hover:brightness-110 hover:shadow-[0_0_30px_rgba(255,23,68,0.4)] disabled:cursor-not-allowed disabled:opacity-30"
                >
                  <ArrowUp size={19} />
                </button>
              </div>
            </div>
          </form>

          <p className="mt-3 text-center text-[9px] tracking-wide text-white/20">
            AFROMIND INTELLIGENCE · LUNA AI · THE INTELLIGENCE
          </p>
        </div>
      </section>
    </main>
  );
}
