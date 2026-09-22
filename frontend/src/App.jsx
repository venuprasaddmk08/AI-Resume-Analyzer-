import { useState } from "react";
import { Sparkles, Home } from "lucide-react";
import WelcomeScreen from "./components/WelcomeScreen";
import SeekerFlow from "./components/seeker/SeekerFlow";
import ProviderFlow from "./components/provider/ProviderFlow";
import "./App.css";

export default function App() {
  const [mode, setMode] = useState("welcome"); // welcome | seeker | provider

  return (
    <div className="app-shell">
      <header className="app-header">
        <button type="button" className="brand" onClick={() => setMode("welcome")}>
          <Sparkles size={20} />
          <span>Resume & Career Intelligence</span>
        </button>
        {mode !== "welcome" && (
          <>
            <p className="brand-tagline">Evidence-based job-fit analysis — not an official ATS score</p>
            <button type="button" className="home-link" onClick={() => setMode("welcome")}>
              <Home size={14} />
              <span>Home</span>
            </button>
          </>
        )}
      </header>

      <main className="app-main">
        {mode === "welcome" && <WelcomeScreen onSelectRole={setMode} />}
        {mode === "seeker" && <SeekerFlow />}
        {mode === "provider" && <ProviderFlow />}
      </main>
    </div>
  );
}
