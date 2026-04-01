import { useState } from "react";
import "./App.css";
import "./index.css";
import { loadRunsFromFiles } from "./lib/loader";
import type { RunData } from "./types/run";
import { Overview } from "./components/Overview";
import { Timeline } from "./components/Timeline";
import { AnswerInspector } from "./components/AnswerInspector";
import { SkillTree } from "./components/SkillTree";
import { Abilities } from "./components/Abilities";
import { SelfAwareness } from "./components/SelfAwareness";
import { Diff } from "./components/Diff";

function App() {
  const [activeTab, setActiveTab] = useState("Overview");
  const [runs, setRuns] = useState<RunData[]>([]);
  
  const tabs = [
    "Overview",
    "Timeline",
    "Answer Inspector",
    "Skill Tree",
    "Abilities",
    "Self-Awareness",
    "Diff"
  ];

  return (
    <div className="h-screen w-screen flex flex-col bg-[#0f172a] text-slate-50">
      {/* Top Bar for File Upload */}
      <header className="h-14 border-b border-slate-700 bg-slate-800 flex items-center px-4 justify-between shrink-0 shadow-sm">
        <h1 className="font-bold text-lg text-blue-400">Dungeon of Self - Results Viewer</h1>
        <div className="flex items-center gap-4">
          <label className="text-sm font-medium px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded cursor-pointer transition-colors border border-blue-500 hover:border-blue-400">
            Load Run JSONs
            <input 
              type="file" 
              className="hidden" 
              multiple 
              accept=".json, .zip" 
              onChange={async (e) => {
                const files = e.target.files;
                if (!files || files.length === 0) return;
                const newRuns = await loadRunsFromFiles(files);
                if (newRuns.length > 0) {
                  setRuns((prev) => {
                    const combined = [...prev, ...newRuns];
                    return combined.slice(-3); // max 3
                  });
                  setActiveTab("Overview");
                }
              }} 
            />
          </label>
        </div>
      </header>
      
      {/* Main Content Area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-56 border-r border-slate-700 bg-slate-800/50 flex flex-col p-2 shrink-0">
          <nav className="flex flex-col gap-1">
            {tabs.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`text-left px-3 py-2 rounded text-sm transition-colors ${
                  activeTab === tab
                    ? "bg-blue-600 text-white font-medium"
                    : "text-slate-300 hover:bg-slate-700 hover:text-white"
                }`}
              >
                {tab}
              </button>
            ))}
          </nav>
        </aside>

        {/* View Content Workspace */}
        <main className="flex-1 bg-slate-900 overflow-auto p-6">
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 shadow-xl min-h-[500px]">
            <div className="text-slate-400">
              {activeTab === "Overview" && <Overview runs={runs} />}
              {activeTab === "Timeline" && <Timeline runs={runs} />}
              {activeTab === "Answer Inspector" && <AnswerInspector runs={runs} />}
              {activeTab === "Skill Tree" && <SkillTree runs={runs} />}
              {activeTab === "Abilities" && <Abilities runs={runs} />}
              {activeTab === "Self-Awareness" && <SelfAwareness runs={runs} />}
              {activeTab === "Diff" && <Diff runs={runs} />}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
