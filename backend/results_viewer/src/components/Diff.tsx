import React, { useState } from "react";
import type { RunData } from "../types/run";
import { runColors } from "./Overview";

export function Diff({ runs }: { runs: RunData[] }) {
  const allRunIds = runs
    .map((r) => r.full_run?.run_id)
    .filter((id): id is string => Boolean(id));

  const [selectedId1, setSelectedId1] = useState<string>(allRunIds[0] || "");
  const [selectedId2, setSelectedId2] = useState<string>(
    allRunIds[1] || allRunIds[0] || ""
  );

  if (runs.length < 2) {
    return <p className="text-slate-400">Load at least 2 runs to see diffs.</p>;
  }

  const run1 = runs.find((r) => r.full_run?.run_id === selectedId1) || runs[0];
  const run2 = runs.find((r) => r.full_run?.run_id === selectedId2) || runs[1];

  // Helper index for color lookup
  const index1 = allRunIds.indexOf(selectedId1);
  const index2 = allRunIds.indexOf(selectedId2);

  return (
    <div className="space-y-4 h-full flex flex-col">
      <h2 className="text-xl font-semibold mb-4 text-slate-100">
        Differential View
      </h2>

      <div className="grid grid-cols-2 gap-4">
        {/* Dropdown 1 */}
        <div className="flex flex-col">
          <label className="text-sm font-semibold mb-1 text-slate-300">Run A</label>
          <select
            value={selectedId1}
            onChange={(e) => setSelectedId1(e.target.value)}
            className="p-2 border rounded bg-slate-800 border-slate-700 text-slate-200"
          >
            {allRunIds.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        </div>

        {/* Dropdown 2 */}
        <div className="flex flex-col">
          <label className="text-sm font-semibold mb-1 text-slate-300">Run B</label>
          <select
            value={selectedId2}
            onChange={(e) => setSelectedId2(e.target.value)}
            className="p-2 border rounded bg-slate-800 border-slate-700 text-slate-200"
          >
            {allRunIds.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 flex-1 mt-4">
        <div className={`flex flex-col border border-slate-700 rounded bg-slate-900 shadow overflow-hidden ${runColors[index1 % runColors.length] || runColors[0]}`}>
          <h3 className="font-bold border-b border-slate-800 m-2 p-2 bg-slate-800/50 rounded text-slate-200 truncate">
            {run1.full_run?.run_id ?? "Run A"}
          </h3>
          <div className="flex-1 overflow-auto p-4 max-h-[70vh]">
            <pre className="text-xs font-mono whitespace-pre text-slate-300">
              {JSON.stringify(run1, null, 2)}
            </pre>
          </div>
        </div>

        <div className={`flex flex-col border border-slate-700 rounded bg-slate-900 shadow overflow-hidden ${runColors[index2 % runColors.length] || runColors[1]}`}>
          <h3 className="font-bold border-b border-slate-800 m-2 p-2 bg-slate-800/50 rounded text-slate-200 truncate">
            {run2.full_run?.run_id ?? "Run B"}
          </h3>
          <div className="flex-1 overflow-auto p-4 max-h-[70vh]">
            <pre className="text-xs font-mono whitespace-pre text-slate-300">
              {JSON.stringify(run2, null, 2)}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}