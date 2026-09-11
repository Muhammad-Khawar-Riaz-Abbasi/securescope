import { useState } from "react";
import { CheckCircle2, Eye, EyeOff, LockKeyhole, ShieldCheck, Sparkles } from "lucide-react";

type Finding = { code: string; severity: string; title: string; detail: string };
type Result = {
  score: number; label: string; entropy_bits: number; length: number;
  breached: boolean; breach_count: number; findings: Finding[];
};

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export default function App() {
  const [password, setPassword] = useState("");
  const [context, setContext] = useState("");
  const [visible, setVisible] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function analyze() {
    if (!password) return;
    setLoading(true); setError("");
    try {
      const response = await fetch(`${API_URL}/api/analyze`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password, context: context.split(",").map((item) => item.trim()).filter(Boolean) }),
      });
      if (!response.ok) throw new Error("The analysis service is unavailable.");
      setResult(await response.json());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Analysis failed.");
    } finally { setLoading(false); }
  }

  return <main>
    <nav><div className="brand"><ShieldCheck size={22} /> SecureScope</div><span className="privacy"><LockKeyhole size={15} /> Privacy-first by design</span></nav>
    <section className="hero">
      <div className="eyebrow"><Sparkles size={15} /> PERSONAL SECURITY WORKBENCH</div>
      <h1>Know your password’s risk.<br /><em>Keep it private.</em></h1>
      <p className="lede">A transparent security check for passwords you own. We analyze risk, check breach exposure with k-anonymity, and give you a clear path to safer account security.</p>
    </section>
    <section className="workspace">
      <div className="panel">
        <div className="panel-heading"><div><span className="step">01</span><h2>Analyze a password</h2></div><span className="local">Runs securely</span></div>
        <label htmlFor="password">Password</label>
        <div className="input-wrap"><input id="password" type={visible ? "text" : "password"} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Enter a password you own" autoComplete="off" /><button aria-label="Toggle password visibility" onClick={() => setVisible(!visible)}>{visible ? <EyeOff size={19} /> : <Eye size={19} />}</button></div>
        <label htmlFor="context">Optional context <span>comma-separated</span></label>
        <input id="context" value={context} onChange={(event) => setContext(event.target.value)} placeholder="name, username, birth year..." />
        <button className="primary" disabled={!password || loading} onClick={analyze}>{loading ? "Analyzing..." : "Run private analysis"} <span>→</span></button>
        {error && <p className="error">{error}</p>}
        <p className="microcopy"><LockKeyhole size={13} /> Never stored. Never used to log in. Only a hash fragment is used for breach checking.</p>
      </div>
      <div className="panel result-panel">
        {!result ? <div className="empty"><div className="empty-icon"><ShieldCheck size={28} /></div><h2>Your security snapshot</h2><p>Run an analysis to see an explainable score and the most important actions to take.</p></div> :
          <><div className="panel-heading"><div><span className="step">02</span><h2>Security snapshot</h2></div><span className={`badge ${result.label}`}>{result.label}</span></div>
          <div className="score-row"><div className="score">{result.score}<small>/100</small></div><div><strong>{result.breached ? "Action required" : "Your password profile"}</strong><p>{result.breached ? `Seen ${result.breach_count.toLocaleString()} times in known breaches.` : `${result.entropy_bits} bits estimated entropy · ${result.length} characters`}</p></div></div>
          <div className="meter"><div style={{ width: `${result.score}%` }} /></div>
          <div className="findings">{result.findings.length ? result.findings.map((finding) => <div className={`finding ${finding.severity}`} key={finding.code}><CheckCircle2 size={18} /><div><strong>{finding.title}</strong><p>{finding.detail}</p></div></div>) : <div className="finding positive"><CheckCircle2 size={18} /><div><strong>No obvious risk patterns found</strong><p>Use a password manager and keep this password unique.</p></div></div>}</div></>}
      </div>
    </section>
    <section className="checklist"><div><span className="step">03</span><h2>Finish the security job</h2></div><div className="checks"><span>Enable MFA</span><span>Review active sessions</span><span>Secure recovery email</span><span>Remove unknown apps</span></div></section>
    <footer>Built for responsible security education <span>·</span> SecureScope does not access social accounts</footer>
  </main>;
}
