import { useEffect, useMemo, useState } from "react";

const languages = [
  { id: "python", label: "Python", mark: "Py", note: "Readable & concise" },
  { id: "java", label: "Java", mark: "J", note: "Strongly typed" },
  { id: "cpp", label: "C++", mark: "C++", note: "STL & performance" },
  { id: "c", label: "C", mark: "C", note: "Memory & pointers" },
];

const levels = [
  { id: "beginner", label: "Beginner", detail: "Start from the fundamentals" },
  { id: "intermediate", label: "Intermediate", detail: "I know the basics" },
  { id: "advanced", label: "Advanced", detail: "Go deep into the details" },
];

function Icon({ name, size = 18 }) {
  const paths = {
    book: <><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21.5z"/><path d="M4 5.5v16M8 7h8M8 11h8"/></>,
    code: <><path d="m8 7-5 5 5 5M16 7l5 5-5 5M14 4l-4 16"/></>,
    play: <path d="m8 5 12 7-12 7z" fill="currentColor" stroke="none"/>,
    arrow: <><path d="M5 12h14M13 6l6 6-6 6"/></>,
    check: <path d="m5 12 4 4L19 6"/>,
    spark: <><path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="m19 16 .8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z"/></>,
    search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
    chevron: <path d="m9 18 6-6-6-6"/>,
    bulb: <><path d="M9 18h6M10 22h4M8 14a6 6 0 1 1 8 0c-.8.7-1 1.3-1 2H9c0-.7-.2-1.3-1-2z"/></>,
    layers: <><path d="m12 3 9 5-9 5-9-5z"/><path d="m3 12 9 5 9-5M3 16l9 5 9-5"/></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

function StepLabel({ number, title, active, complete }) {
  return <div className={`step-label ${active ? "active" : ""} ${complete ? "complete" : ""}`}>
    <span className="step-number">{complete ? <Icon name="check" size={13}/> : number}</span>
    <span>{title}</span>
  </div>;
}

function LevelPicker({ title, subtitle, value, onChange, icon }) {
  return <section className="setting-block">
    <div className="setting-heading">
      <div className="setting-icon"><Icon name={icon} size={17}/></div>
      <div><h3>{title}</h3><p>{subtitle}</p></div>
    </div>
    <div className="level-grid">
      {levels.map((level, index) => <button key={level.id} type="button" onClick={() => onChange(level.id)} className={`level-option ${value === level.id ? "selected" : ""}`}>
        <span className="level-top"><span className="level-dot">{index + 1}</span>{value === level.id && <Icon name="check" size={15}/>}</span>
        <strong>{level.label}</strong>
        <small>{level.detail}</small>
      </button>)}
    </div>
  </section>;
}

export default function App() {
  const [problemNumber, setProblemNumber] = useState("1");
  const [problem, setProblem] = useState(null);
  const [lookupState, setLookupState] = useState("idle");
  const [language, setLanguage] = useState("python");
  const [dsaLevel, setDsaLevel] = useState("beginner");
  const [programmingLevel, setProgrammingLevel] = useState("beginner");
  const [intent, setIntent] = useState("solve");
  const [sessionReady, setSessionReady] = useState(false);
  const [sessionResult, setSessionResult] = useState(null);
  const [sessionLoading, setSessionLoading] = useState(false);
  const [sessionError, setSessionError] = useState("");
  const [apiOnline, setApiOnline] = useState(null);

  const selectedLanguage = useMemo(() => languages.find((item) => item.id === language), [language]);

  useEffect(() => {
    fetch("/health")
      .then((response) => { if (!response.ok) throw new Error("API unavailable"); return response.json(); })
      .then(() => setApiOnline(true))
      .catch(() => setApiOnline(false));
  }, []);

  async function lookupProblem(event) {
    event.preventDefault();
    setSessionReady(false);
    setSessionError("");
    setProblem(null);
    const value = problemNumber.trim();
    if (!/^[1-9][0-9]{0,5}$/.test(value)) {
      setLookupState("invalid");
      return;
    }
    setLookupState("loading");
    try {
      const response = await fetch(`/api/problems/${value}`, {
        headers: { Accept: "application/json" },
      });
      const responseText = await response.text();
      let payload = {};
      try {
        payload = responseText ? JSON.parse(responseText) : {};
      } catch {
        throw new Error(`The API returned an unreadable response (HTTP ${response.status}). Check the backend terminal.`);
      }
      if (!response.ok) {
        const detail = payload.detail || {};
        const states = {
          PROBLEM_NOT_FOUND: "not_found",
          PREMIUM_PROBLEM: "premium",
          SOURCE_RATE_LIMITED: "rate_limited",
          SOURCE_UNAVAILABLE: "source_error",
          INVALID_PROBLEM_NUMBER: "invalid",
        };
        setLookupState(states[detail.code] || "source_error");
        setSessionError(detail.message || "Could not retrieve this problem.");
        return;
      }
      if (!payload.title || !payload.statement_text || !payload.canonical_url) {
        setLookupState("source_error");
        setSessionError("The source returned incomplete problem details. Please try again.");
        return;
      }
      setProblem(payload);
      setLookupState("found");
    } catch (error) {
      setLookupState("network_error");
      setSessionError(error instanceof Error
        ? error.message
        : "Cannot reach the Didactics API. Check that the backend is running on port 8000 and restart the Vite dev server.");
    }
  }

  async function startSession() {
    if (!problem || sessionLoading) return;
    setSessionError(""); setSessionResult(null); setSessionReady(false); setSessionLoading(true);
    try {
      const response = await fetch("/api/sessions/generate", {
        method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ problem_number: Number(problem.problem_number), language, dsa_proficiency: dsaLevel, programming_proficiency: programmingLevel, intent }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail?.message || "Could not start the learning workflow.");
      setSessionResult(payload);
      setSessionReady(payload.status === "completed" || payload.status === "needs_review");
      if (payload.status === "failed") setSessionError(payload.error || "Workflow failed. Inspect out/runs and out/logs.");
    } catch (error) {
      setSessionError(error instanceof Error ? error.message : "Workflow failed. Check the backend terminal and out/logs/didactics.log.");
    } finally { setSessionLoading(false); }
  }

  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="#" aria-label="Didactics home">
        <span className="brand-mark"><span/><span/><span/><span/></span>
        <span className="brand-name">didactics<span className="brand-period">.</span></span>
      </a>
      <div className="workspace-label">WORKSPACE</div>
      <button className="side-link selected"><span className="side-link-icon"><Icon name="spark" size={17}/></span>New learning session</button>
      <div className="sidebar-rule"/>
      <div className="workspace-label">YOUR LEARNING</div>
      <div className="side-muted"><Icon name="book" size={16}/> Learning library</div>
      <div className="side-muted"><Icon name="layers" size={16}/> Saved concepts</div>
      <div className="sidebar-bottom">
        <div className="sidebar-tip">
          <div className="tip-icon"><Icon name="bulb" size={17}/></div>
          <strong>Learn, don’t memorise.</strong>
          <p>Build intuition one visual step at a time.</p>
        </div>
        <div className="profile-row"><div className="avatar">D</div><div><strong>Guest learner</strong><small>Personal workspace</small></div><span className="profile-menu">···</span></div>
      </div>
    </aside>

    <main className="main-area">
      <header className="topbar">
        <div className="breadcrumb"><span>Workspace</span><Icon name="chevron" size={13}/><strong>New session</strong></div>
        <div className="topbar-right"><span className="system-status"><i className={apiOnline === false ? "offline" : ""}/>{apiOnline === null ? "Checking API" : apiOnline ? "API connected" : "API offline"}</span><button className="help-button" aria-label="Help">?</button></div>
      </header>

      <div className="content-wrap">
        <div className="eyebrow"><span className="eyebrow-line"/> YOUR PERSONAL ALGORITHM TUTOR</div>
        <div className="hero-row">
          <div><h1>Understand the logic.<br/><em>See it come to life.</em></h1><p className="hero-copy">One problem at a time. A learning path shaped around<br className="desktop-break"/> how you think, code, and grow.</p></div>
          <div className="hero-art" aria-hidden="true">
            <div className="orbit orbit-one"/><div className="orbit orbit-two"/>
            <div className="art-core"><span className="core-bracket">{"{ }"}</span><span className="core-dot"/></div>
            <span className="float-chip chip-a">01 <b>TRACE</b></span><span className="float-chip chip-b"><span/> VISUALIZE</span><span className="float-chip chip-c">O(n)</span>
          </div>
        </div>

        <div className="journey">
          <StepLabel number="01" title="The problem" active={!problem} complete={!!problem}/>
          <span className="journey-line"/>
          <StepLabel number="02" title="Your level" active={!!problem}/>
          <span className="journey-line"/>
          <StepLabel number="03" title="Learning path" active={!!problem}/>
        </div>

        <div className="workspace-grid">
          <div className="form-column">
            <section className="panel problem-panel">
              <div className="panel-heading"><div><span className="section-kicker">STEP 01 / START HERE</span><h2>Which problem are we solving?</h2><p>Just enter the LeetCode question number. We’ll take it from there.</p></div><div className="heading-symbol"><Icon name="search" size={20}/></div></div>
              <form className="problem-form" onSubmit={lookupProblem}>
                <label htmlFor="problem-number">LEETCODE PROBLEM NUMBER</label>
                <div className="input-row"><div className="input-prefix">#</div><input id="problem-number" type="text" inputMode="numeric" pattern="[0-9]*" value={problemNumber} onChange={(event) => {setProblemNumber(event.target.value); setLookupState("idle"); setProblem(null); setSessionReady(false); setSessionError("");}} placeholder="e.g. 1"/><button className="primary-button" type="submit">Find problem <Icon name="arrow" size={16}/></button></div>
                <div className="input-hint"><span className="hint-dot"/> Try <button type="button" onClick={() => {setProblemNumber("1");setLookupState("idle");setProblem(null);}}>#1 Two Sum</button> to look it up from LeetCode</div>
                {lookupState === "invalid" && <p className="inline-error">Enter a positive whole-number problem ID (digits only).</p>}
                {lookupState === "loading" && <p className="lookup-loading">Connecting to LeetCode and validating problem details…</p>}
                {["not_found","premium","rate_limited","source_error","network_error"].includes(lookupState) && <p className="inline-error">{sessionError}</p>}
              </form>
              {problem && <div className="problem-result">
                <div className="result-top"><span className="result-check"><Icon name="check" size={13}/></span><span>PROBLEM FOUND <b>· SOURCE DATA VALIDATED</b></span><button type="button" onClick={() => {setProblem(null);setLookupState("idle");setSessionReady(false);}}>Change</button></div>
                <div className="problem-title-row"><div><div className="problem-number">LEETCODE #{problem.problem_number}</div><h3>{problem.title}</h3></div><span className={`difficulty ${problem.difficulty.toLowerCase()}`}>{problem.difficulty}</span></div>
                <div className="problem-statement source-statement" dangerouslySetInnerHTML={{ __html: problem.statement_html }} />
                <div className="topic-row">{(problem.topic_tags || []).map(topic => <span key={topic}>{topic}</span>)}</div>
                {(problem.examples?.length > 0 || problem.sample_test_case) && <div className="source-examples"><span>EXAMPLES FROM SOURCE</span>{(problem.examples?.length ? problem.examples : [problem.sample_test_case]).map((example, index) => <pre key={index}>{example}</pre>)}</div>}
                {problem.constraints?.length > 0 && <div className="source-examples"><span>CONSTRAINTS</span>{problem.constraints.map((item, index) => <pre key={index}>{item}</pre>)}</div>}
                <a className="canonical-link" href={problem.canonical_url} target="_blank" rel="noreferrer">Open canonical LeetCode problem <Icon name="arrow" size={13}/></a>
              </div>}
            </section>

            <section className={`panel personalize-panel ${problem ? "" : "panel-muted"}`}>
              <div className="panel-heading compact"><div><span className="section-kicker">STEP 02 / MAKE IT YOURS</span><h2>How do you like to learn?</h2><p>Two separate skill levels help us pitch every explanation just right.</p></div><span className="optional-tag">PERSONALIZED</span></div>
              <div className="setting-block language-block">
                <div className="setting-heading"><div className="setting-icon"><Icon name="code" size={17}/></div><div><h3>Programming language</h3><p>We’ll write every example in your language.</p></div></div>
                <div className="language-grid">
                  {languages.map(item => <button type="button" key={item.id} onClick={() => setLanguage(item.id)} className={`language-option ${language === item.id ? "selected" : ""}`}><span className={`language-mark ${item.id}`}>{item.mark}</span><span className="language-meta"><strong>{item.label}</strong><small>{item.note}</small></span>{language === item.id && <span className="selected-check"><Icon name="check" size={12}/></span>}</button>)}
                </div>
              </div>
              <div className="settings-divider"/>
              <LevelPicker title="DSA proficiency" subtitle="How comfortable are you with data structures & algorithms?" value={dsaLevel} onChange={setDsaLevel} icon="layers"/>
              <div className="settings-divider"/>
              <LevelPicker title="Programming proficiency" subtitle="How comfortable are you writing code in general?" value={programmingLevel} onChange={setProgrammingLevel} icon="code"/>
              {programmingLevel === "beginner" && <div className="syntax-note"><span className="syntax-spark"><Icon name="spark" size={15}/></span><p><strong>We’ll explain the syntax, too.</strong> Your lesson will break down declarations, loops, conditions, functions, and the {selectedLanguage.label} constructs used in the solution.</p></div>}
            </section>

            <section className={`panel intent-panel ${problem ? "" : "panel-muted"}`}>
              <div className="panel-heading compact"><div><span className="section-kicker">STEP 03 / PICK YOUR PATH</span><h2>What would you like to do?</h2><p>Choose the kind of help you need right now.</p></div></div>
              <div className="intent-grid">
                <button type="button" className={`intent-card ${intent === "solve" ? "selected" : ""}`} onClick={() => setIntent("solve")}>
                  <span className="intent-icon solve"><Icon name="code" size={20}/></span><span className="intent-radio">{intent === "solve" && <i/>}</span><strong>Teach me to solve it</strong><p>Build intuition, explore the approach, walk through code, and understand complexity.</p><span className="intent-footer">SOLUTION WALKTHROUGH <Icon name="arrow" size={14}/></span>
                </button>
                <button type="button" className={`intent-card ${intent === "prerequisites" ? "selected" : ""}`} onClick={() => setIntent("prerequisites")}>
                  <span className="intent-icon prereq"><Icon name="book" size={20}/></span><span className="intent-radio">{intent === "prerequisites" && <i/>}</span><strong>Teach me the basics first</strong><p>Discover the concepts you need, learn them step by step, then return to the problem.</p><span className="intent-footer">PREREQUISITE PATH <Icon name="arrow" size={14}/></span>
                </button>
              </div>
              <button className="launch-button" type="button" disabled={!problem || sessionLoading} onClick={startSession}><span><Icon name="spark" size={17}/> {sessionLoading ? "Building your lesson…" : "Build my learning session"}</span><Icon name="arrow" size={17}/></button>
              {!problem && <p className="launch-hint">Find a problem above to unlock your personalized session.</p>}
              {sessionError && !["not_found","premium","rate_limited","source_error","network_error"].includes(lookupState) && <p className="inline-error">{sessionError}</p>}
              {sessionResult && <div className="session-confirmation workflow-result">
                <span><Icon name="check" size={16}/></span><div>
                  <strong>{sessionResult.status === "completed" ? "Six-agent lesson generated." : sessionResult.status === "needs_review" ? "Lesson generated — media needs review." : "Workflow failed."}</strong>
                  <p>Run {sessionResult.run_id} · {sessionResult.completed_stages?.length || 0}/6 stages completed</p>
                  {sessionResult.media?.video_path && <p><a href={"/artifacts/" + sessionResult.media.video_path.replaceAll(String.fromCharCode(92), "/").split("/out/").pop()} target="_blank" rel="noreferrer">Open generated video</a></p>}
                  {sessionResult.media?.audio_path && <p><a href={"/artifacts/" + sessionResult.media.audio_path.replaceAll(String.fromCharCode(92), "/").split("/out/").pop()} target="_blank" rel="noreferrer">Open narration audio</a></p>}
                  {intent === "solve" && sessionResult.solution_portfolio?.approaches?.map((item) => <div key={item.variant_id} className="workflow-approach"><strong>{item.algorithm_name} · {item.variant_id}</strong><pre>{item.code}</pre><small>{item.time_complexity_claim} time · {item.space_complexity_claim} space</small></div>)}
                  {sessionResult.complexity_report?.analyses?.map((item) => <div key={item.variant_id} className="workflow-approach"><strong>{item.variant_id}: {item.time_complexity} time / {item.space_complexity} space</strong><ul>{item.time_derivation.map((line, index) => <li key={index}>{line}</li>)}</ul><small>Space derivation: {item.space_derivation.join(" ")}</small></div>)}
                  {sessionResult.artifacts?.run_dir && <small>Checkpoints and logs: {sessionResult.artifacts.run_dir}</small>}
                  {sessionResult.warnings?.map((warning, index) => <p className="inline-error" key={index}>{warning}</p>)}
                </div></div>}{sessionReady && <div className="session-confirmation"><span><Icon name="check" size={16}/></span><div><strong>Your learner configuration is validated.</strong><p>{problem.title} · {selectedLanguage.label} · {dsaLevel} DSA · {programmingLevel} programming</p><small>{programmingLevel === "beginner" ? "Syntax explanations enabled." : "Programming explanations adapted to your level."} Problem confirmation is complete.</small></div></div>}
            </section>
          </div>

          <aside className="preview-column">
            <div className="preview-card">
              <div className="preview-top"><span className="preview-label">YOUR SESSION PREVIEW</span><span className="preview-live"><i/> LIVE SETUP</span></div>
              <div className="preview-visual">
                <div className="visual-grid"/>
                <div className="visual-code"><span className="code-muted">01</span> <b>for</b> (i = 0; i &lt; n; i++) {"{"}<br/><span className="code-muted">02</span> &nbsp; <b>if</b> (found) {"{"}<br/><span className="code-muted">03</span> &nbsp;&nbsp; <em>return</em> answer;<br/><span className="code-muted">04</span> &nbsp; {"}"}<br/><span className="code-muted">05</span> {"}"}</div>
                <div className="visual-orbit"><span className="orbit-node node-one">i</span><span className="orbit-node node-two">j</span><span className="orbit-node node-three"><Icon name="check" size={12}/></span></div>
                <div className="visual-caption"><span className="caption-dot"/> VISUAL TRACE PREVIEW</div>
              </div>
              <div className="preview-content">
                <div className="preview-problem"><span>PROBLEM</span><strong>{problem ? `#${problem.problem_number} · ${problem.title}` : "Waiting for a problem"}</strong></div>
                <div className="preview-divider"/>
                <div className="preview-row"><span>Language</span><strong><i className={`mini-language ${language}`}>{selectedLanguage.mark}</i>{selectedLanguage.label}</strong></div>
                <div className="preview-row"><span>DSA level</span><strong className="capitalize">{dsaLevel}</strong></div>
                <div className="preview-row"><span>Code level</span><strong className="capitalize">{programmingLevel}</strong></div>
                <div className="preview-row"><span>Learning goal</span><strong>{intent === "solve" ? "Solve the problem" : "Learn prerequisites"}</strong></div>
                <div className="preview-divider"/>
                <div className="preview-includes"><span>YOUR SESSION INCLUDES</span><div><Icon name="check" size={14}/> Tailored explanations</div><div><Icon name="check" size={14}/> {programmingLevel === "beginner" ? "Step-by-step syntax guide" : "Language-specific code"}</div><div><Icon name="check" size={14}/> Interactive algorithm animation</div><div><Icon name="check" size={14}/> Complexity & key takeaways</div></div>
              </div>
            </div>
            <div className="promise-card"><div className="promise-icon"><Icon name="spark" size={18}/></div><div><strong>Made for your learning curve.</strong><p>Not just the answer. The understanding behind it.</p></div></div>
            <div className="privacy-note"><span className="privacy-lock">◈</span> Your skill settings shape this session, not your identity.</div>
          </aside>
        </div>
        <footer className="page-footer"><span>© 2026 DIDACTICS</span><span>THINK CLEARLY. CODE CONFIDENTLY.</span><span>BUILT FOR THE CURIOUS <b>✳</b></span></footer>
      </div>
    </main>
  </div>;
}
