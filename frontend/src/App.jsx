import { useEffect, useMemo, useRef, useState } from "react";
import { api, clearToken, getToken, setTokens } from "./api";

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

export default function App() {
  const [token, setToken] = useState(getToken());
  const [view, setView] = useState(token ? "home" : "login");
  const [story, setStory] = useState(null);

  if (!token || view === "login") {
    return (
      <Auth
        onAuthed={(t) => {
          setTokens(t);
          setToken(t.access_token);
          setView("home");
        }}
      />
    );
  }

  if (view === "reader" && story) {
    return (
      <Reader
        story={story}
        onBack={() => {
          setView("home");
          setStory(null);
        }}
        onLogout={() => {
          clearToken();
          setToken(null);
          setView("login");
        }}
      />
    );
  }

  return (
    <Home
      onOpen={(s) => {
        setStory(s);
        setView("reader");
      }}
      onLogout={() => {
        clearToken();
        setToken(null);
        setView("login");
      }}
    />
  );
}

function Auth({ onAuthed }) {
  const [email, setEmail] = useState("demo@chatnovel.local");
  const [password, setPassword] = useState("demo1234");
  const [mode, setMode] = useState("login");
  const [err, setErr] = useState("");

  async function submit(e) {
    e.preventDefault();
    setErr("");
    try {
      const data = mode === "login" ? await api.login(email, password) : await api.register(email, password);
      onAuthed(data);
    } catch (e2) {
      setErr(String(e2.message || e2));
    }
  }

  return (
    <div className="shell auth-shell">
      <header className="brand">
        <p className="eyebrow">Bengali chat fiction</p>
        <h1>ChatNovel</h1>
        <p className="tagline">গোপন চ্যাটের মতো করে একটা প্রেমের গল্প পড়ো।</p>
      </header>
      <form className="card form" onSubmit={submit}>
        <label>
          ইমেল
          <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
        </label>
        <label>
          পাসওয়ার্ড
          <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required />
        </label>
        {err && <p className="error">{err}</p>}
        <button type="submit">{mode === "login" ? "ঢুকুন" : "অ্যাকাউন্ট খুলুন"}</button>
        <button type="button" className="linkish" onClick={() => setMode(mode === "login" ? "register" : "login")}>
          {mode === "login" ? "নতুন পাঠক? নিবন্ধন" : "আগে থেকে আছেন? লগইন"}
        </button>
        <p className="hint">ডেমো: demo@chatnovel.local / demo1234</p>
      </form>
    </div>
  );
}

function Home({ onOpen, onLogout }) {
  const [stories, setStories] = useState([]);
  const [billing, setBilling] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    Promise.all([api.stories(), api.billing()])
      .then(([s, b]) => {
        setStories(s);
        setBilling(b);
      })
      .catch((e) => setErr(e.message));
  }, []);

  const cont = stories.find((s) => s.continue_chapter_id);

  return (
    <div className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">ChatNovel</p>
          <h1>যা পড়ে শেষ হয় না</h1>
        </div>
        <button className="ghost" onClick={onLogout}>
          বেরোন
        </button>
      </header>

      {billing?.premium && <p className="pill">প্রিমিয়াম চালু</p>}
      {err && <p className="error">{err}</p>}

      {cont && (
        <section>
          <h2>পড়ে চলুন</h2>
          <StoryCard story={cont} cta="আবার খুলুন" onOpen={onOpen} />
        </section>
      )}

      <section>
        <h2>সিরিয়ালাইজড রোমান্স</h2>
        <div className="grid">
          {stories.map((s) => (
            <StoryCard key={s.id} story={s} onOpen={onOpen} />
          ))}
        </div>
      </section>
    </div>
  );
}

function StoryCard({ story, onOpen, cta }) {
  return (
    <article className="card story-card">
      <div className="cover" aria-hidden="true">
        <span>যা</span>
      </div>
      <div>
        <p className="eyebrow">{story.genre} · {story.age_rating}</p>
        <h3>{story.title}</h3>
        <p>{story.blurb}</p>
        <p className="meta">{story.characters.map((c) => `${c.name}, ${c.age}`).join(" · ")}</p>
        <button onClick={() => onOpen(story)}>{cta || "চ্যাট খুলুন"}</button>
      </div>
    </article>
  );
}

function Reader({ story, onBack, onLogout }) {
  const [chapters, setChapters] = useState([]);
  const [chapterId, setChapterId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [typing, setTyping] = useState(null);
  const [paused, setPaused] = useState(false);
  const [status, setStatus] = useState("loading");
  const [end, setEnd] = useState(null);
  const [paywall, setPaywall] = useState(false);
  const pausedRef = useRef(false);
  const threadRef = useRef(null);
  const playing = useRef(false);

  const chapter = useMemo(() => chapters.find((c) => c.id === chapterId), [chapters, chapterId]);
  const leads = story.characters || [];

  useEffect(() => {
    pausedRef.current = paused;
  }, [paused]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [chs, state] = await Promise.all([api.chapters(story.id), api.start(story.id)]);
      if (cancelled) return;
      setChapters(chs);
      const startId = state.chapter_id || chs[0]?.id;
      setChapterId(startId);
      api.track("story_open", { story_id: story.id });
    })().catch((e) => setStatus(e.message));
    return () => {
      cancelled = true;
    };
  }, [story.id]);

  useEffect(() => {
    if (!chapterId || playing.current) return;
    playChapter(chapterId, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chapterId]);

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, typing]);

  async function playChapter(id, reset) {
    playing.current = true;
    if (reset) {
      setMessages([]);
      setEnd(null);
      setPaywall(false);
    }
    setStatus("playing");
    let after = reset ? null : messages.at(-1)?.id;
    try {
      while (true) {
        while (pausedRef.current) await sleep(200);
        const batch = await api.next(story.id, id, after);
        if (batch.paywalled) {
          setPaywall(true);
          setStatus("paywall");
          break;
        }
        if (batch.chapter_complete && (!batch.messages || batch.messages.length === 0)) {
          setEnd(batch);
          setStatus("ended");
          api.track("chapter_complete", { story_id: story.id, chapter_id: id });
          break;
        }
        for (const m of batch.messages) {
          while (pausedRef.current) await sleep(200);
          if (m.kind === "text") {
            setTyping(m.speaker);
            await sleep(650);
            setTyping(null);
          }
          setMessages((prev) => [...prev, m]);
          after = m.id;
          await api.ack(story.id, m.id).catch(() => {});
          await sleep(m.kind === "scene_marker" ? 400 : 900);
        }
        if (batch.chapter_complete) {
          setEnd(batch);
          setStatus("ended");
          api.track("chapter_complete", { story_id: story.id, chapter_id: id });
          break;
        }
        if (!batch.messages?.length) break;
      }
    } catch (e) {
      setStatus(e.message);
    } finally {
      playing.current = false;
    }
  }

  async function subscribe() {
    await api.checkout();
    setPaywall(false);
    playChapter(chapterId, false);
  }

  function nextChapter() {
    if (!end?.next_chapter_id) {
      onBack();
      return;
    }
    playing.current = false;
    setChapterId(end.next_chapter_id);
  }

  const leftName = leads[0]?.name || "Maya";

  return (
    <div className="reader">
      <header className="chat-head">
        <button className="ghost" onClick={onBack}>
          ←
        </button>
        <div className="avatars">
          {leads.map((c) => (
            <span key={c.id} className="ava" style={{ background: `hsl(${c.avatar_hue} 40% 28%)` }}>
              {c.name[0]}
            </span>
          ))}
        </div>
        <div className="who">
          <strong>{leads.map((c) => c.name).join(" · ")}</strong>
          <span>
            অধ্যায় {chapter?.chapter_number || "—"} · {chapter?.title || story.title}
          </span>
        </div>
        <button className="ghost" onClick={() => setPaused((p) => !p)}>
          {paused ? "চালাও" : "থামো"}
        </button>
      </header>

      <div className="thread" ref={threadRef}>
        {messages.map((m) =>
          m.kind === "scene_marker" ? (
            <p key={m.id} className="marker">
              {m.body}
            </p>
          ) : m.kind === "deleted" ? (
            <div key={m.id} className={`bubble ${m.speaker === leftName ? "left" : "right"} deleted`}>
              {m.body}
            </div>
          ) : (
            <div key={m.id} className={`row ${m.speaker === leftName ? "left" : "right"}`}>
              <div className="bubble">
                <span className="who-line">{m.speaker}</span>
                {m.body}
              </div>
            </div>
          )
        )}
        {typing && (
          <div className={`row ${typing === leftName ? "left" : "right"}`}>
            <div className="bubble typing">
              <i />
              <i />
              <i />
            </div>
          </div>
        )}

        {end && (
          <div className="chapter-end card">
            <p className="eyebrow">অধ্যায় {chapter?.chapter_number} শেষ</p>
            <h2>{chapter?.title}</h2>
            <p className="closing">“{end.closing_line || chapter?.closing_line}”</p>
            <button onClick={nextChapter}>{end.next_chapter_id ? "পরের অধ্যায়" : "গল্পের তালিকা"}</button>
            {end.next_chapter_id && <p className="hint">আগামীকাল পরের অধ্যায় পড়বে?</p>}
          </div>
        )}

        {paywall && (
          <div className="chapter-end card paywall">
            <h2>এখান থেকে প্রিমিয়াম</h2>
            <p>প্রথম দুই অধ্যায় উপহার। বাকি গল্পটা ধীরে, পুরোপুরি পড়তে সাবস্ক্রাইব করুন।</p>
            <button onClick={subscribe}>প্রিমিয়াম খুলুন (ডেমো)</button>
            <button className="ghost" onClick={onBack}>
              ফিরে যান
            </button>
          </div>
        )}
      </div>
      <button className="sr-logout" onClick={onLogout}>
        লগআউট
      </button>
    </div>
  );
}
