import { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from "recharts";
import type { RunData } from "../types/run";
import { runColors } from "./Overview";

export function SelfAwareness({ runs }: { runs: RunData[] }) {
  const { chartData, runSummaries } = useMemo(() => {
    let maxChamber = 0;
    const allData: Record<number, any> = {};

    const runSummaries = runs.map((run, i) => {
      const runKey = `run${i}`;
      const summary = {
        id: run.full_run?.run_id?.substring(0, 8) ?? `Run ${i + 1}`,
        beliefCounts: {} as Record<string, number>,
        realityAcc: run.category_accuracy || {},
        changes: [] as any[],
        runKey
      };

      if (!run.full_run) return summary;

      let currentScore = 0;

      const eventsByChamber = new Map<number, any[]>();
      for (const e of run.full_run.events) {
        if (!eventsByChamber.has(e.chamber_index)) {
          eventsByChamber.set(e.chamber_index, []);
        }
        eventsByChamber.get(e.chamber_index)!.push(e);
      }

      const chambers = Array.from(eventsByChamber.keys());
      if (chambers.length > 0) {
        maxChamber = Math.max(maxChamber, ...chambers);
      }

      for (let c = 0; c <= (chambers.length > 0 ? Math.max(...chambers) : 0); c++) {
        const evs = eventsByChamber.get(c) || [];

        let scoreDelta = 0;
        let changeReason = "";
        let category = "Unknown";
        let doorCats: Record<string, string> = {};

        const finalStrategy = evs.slice().reverse().find(e =>
          e.event_type === "strategy_call" &&
          (e.response.includes("<action>choose_door</action>") ||
            e.response.includes("<action>double_down</action>"))
        );

        if (finalStrategy) {
          const lines = finalStrategy.prompt.split("\n");
          lines.forEach((l: string) => {
            const m = l.match(/Door ([A-D]):.*?Categories: (.*)/);
            if (m) doorCats[m[1]] = m[2].trim();
          });

          const actionMatch = finalStrategy.response.match(/<action>(.*?)<\/action>/);
          const targetMatch = finalStrategy.response.match(/<target>(.*?)<\/target>/);
          const action = actionMatch ? actionMatch[1] : null;
          const target = targetMatch ? targetMatch[1] : null;

          if (target && doorCats[target]) {
            category = doorCats[target];
            summary.beliefCounts[category] = (summary.beliefCounts[category] || 0) + 1;
          }

          const isWrong = evs.some(
            e =>
              e.event_type === "wrong_answer" ||
              (e.event_type === "ability_double_down" && e.outcome === "wrong")
          );
          const isDoubleDown = action === "double_down";

          if (isWrong) {
            scoreDelta = isDoubleDown ? -2 : -1;
            changeReason = `Failed ${isDoubleDown ? "Double Down" : "door"} on ${category}`;
          } else {
            scoreDelta = isDoubleDown ? +2 : +1;
            changeReason = `Succeeded ${isDoubleDown ? "Double Down" : "door"} on ${category}`;
          }
        }

        currentScore += scoreDelta;

        if (!allData[c]) allData[c] = { chamber: c };
        allData[c][`${runKey}_score`] = currentScore;
        allData[c][`${runKey}_change`] = changeReason;
        allData[c][`${runKey}_delta`] = scoreDelta;

        if (scoreDelta !== 0) {
          summary.changes.push({ chamber: c, delta: scoreDelta, reason: changeReason, category });
        }
      }

      for (let c = 0; c <= Math.max(...chambers, 0); c++) {
        if (!allData[c]) allData[c] = { chamber: c };
        if (allData[c][`${runKey}_score`] === undefined) {
          let prevScore = 0;
          for (let pc = c - 1; pc >= 0; pc--) {
            if (allData[pc] && allData[pc][`${runKey}_score`] !== undefined) {
              prevScore = allData[pc][`${runKey}_score`];
              break;
            }
          }
          allData[c][`${runKey}_score`] = prevScore;
        }
      }

      return summary;
    });

    for (let c = 0; c <= maxChamber; c++) {
      if (!allData[c]) allData[c] = { chamber: c };
      runSummaries.forEach((summary) => {
        if (allData[c][`${summary.runKey}_score`] === undefined) {
          let prevScore = 0;
          for (let pc = c - 1; pc >= 0; pc--) {
            if (allData[pc] && allData[pc][`${summary.runKey}_score`] !== undefined) {
              prevScore = allData[pc][`${summary.runKey}_score`];
              break;
            }
          }
          allData[c][`${summary.runKey}_score`] = prevScore;
        }
      });
    }

    const dataArray = Object.values(allData).sort((a, b) => a.chamber - b.chamber);

    return { chartData: dataArray, runSummaries };
  }, [runs]);

  if (runs.length === 0) return <p className="text-slate-400">No runs loaded.</p>;

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-xl font-semibold mb-2 text-slate-100">Self-Awareness Progress</h2>
        <p className="text-slate-400 mb-6 text-sm">
          A heuristic score based on the entity's ability to accurately evaluate its own competence.
          Correctly choosing or doubling down on a category increases the score (+1/+2), while
          failing decreases it (-1/-2).
        </p>

        <div className="bg-slate-900 border border-slate-700 rounded-lg p-4 shadow-sm w-full">
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="chamber" stroke="#94A3B8" label={{ value: 'Chamber Index', position: 'insideBottom', offset: -10, fill: '#94A3B8' }} />
              <YAxis stroke="#94A3B8" label={{ value: 'Self-Awareness Score', angle: -90, position: 'insideLeft', offset: 0, fill: '#94A3B8' }} />
              <Tooltip
                contentStyle={{ backgroundColor: "#0F172A", borderColor: "#334155", color: "#F8FAFC" }}
                itemStyle={{ color: "#E2E8F0" }}
                labelStyle={{ color: "#94A3B8", marginBottom: "4px" }}
                formatter={(value: any, name: string | undefined, props: any) => {
                  const safeName = String(name || '');
                  const runIndex = parseInt(safeName.replace('run', ''));
                  const delta = props.payload[`${safeName}_delta`];
                  const reason = props.payload[`${safeName}_change`];
                  return [
                    <span key={safeName} className="flex flex-col">
                      <span>Score: <strong>{value}</strong></span>
                      {delta !== undefined && delta !== 0 && (
                        <span className={`text-xs ${delta > 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                          ({delta > 0 ? '+' : ''}{delta}) {reason}
                        </span>
                      )}
                    </span>,
                    runs[runIndex]?.full_run?.run_id?.substring(0, 8) ?? `Run ${runIndex + 1}`
                  ];
                }}
              />
              <Legend />
              {runSummaries.map((summary, i) => (
                <Line
                  key={summary.id}
                  type="monotone"
                  dataKey={`${summary.runKey}_score`}
                  name={summary.id}
                  stroke={runColors[i % runColors.length].hex}
                  strokeWidth={3}
                  activeDot={{ r: 6 }}
                  dot={(props) => {
                    const { cx, cy, payload, index } = props;
                    const delta = payload[`${summary.runKey}_delta`];
                    if (delta !== undefined && delta !== 0) {
                      return <circle key={`${summary.runKey}-${index}`} cx={cx} cy={cy} r={4} fill={runColors[i % runColors.length].hex} stroke="#0f172a" strokeWidth={2} />;
                    }
                    return <span key={`${summary.runKey}-${index}`} />;
                  }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="space-y-4">
        <h2 className="text-xl font-semibold mb-4 text-slate-100">Belief vs Reality (Per Run)</h2>
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {runSummaries.map((summary, i) => {
            const beliefSorted = Object.entries(summary.beliefCounts).sort((a, b) => b[1] - a[1]);
            const realitySorted = Object.entries(summary.realityAcc).sort((a, b) => {
              const accB = (b[1] as any).total > 0 ? ((b[1] as any).correct / (b[1] as any).total) : 0;
              const accA = (a[1] as any).total > 0 ? ((a[1] as any).correct / (a[1] as any).total) : 0;
              return accB - accA;
            });

            return (
              <div key={summary.id} className={`p-4 border border-slate-700 bg-slate-900 rounded-lg shadow-sm w-full ${runColors[i % runColors.length].className}`}>
                <h3 className="font-bold border-b border-slate-800 pb-2 mb-4 bg-slate-800/30 px-3 py-2 rounded">
                  Run {summary.id}
                </h3>
                <div className="flex flex-col md:flex-row gap-6 px-2 text-sm text-slate-300">
                  <div className="flex-1 space-y-2 relative">
                    <h4 className="font-semibold text-slate-200 uppercase tracking-widest text-xs border-b border-slate-700 pb-1">Belief (Chosen Categories)</h4>
                    {beliefSorted.length > 0 ? (
                      <ul className="space-y-1 mt-2">
                        {beliefSorted.map(([cat, count]) => (
                          <li key={cat} className="flex justify-between items-center group">
                            <span className="truncate pr-2 group-hover:text-slate-100 transition-colors" title={cat}>{cat}</span>
                            <span className="text-slate-400 font-mono text-xs py-0.5 px-2 bg-slate-800 rounded min-w-[3rem] text-center shrink-0">
                              {count}x
                            </span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-slate-500 italic">No doors chosen</p>
                    )}
                  </div>
                  <div className="flex-1 space-y-2 relative">
                    <h4 className="font-semibold text-slate-200 uppercase tracking-widest text-xs border-b border-slate-700 pb-1">Reality (Actual Accuracy)</h4>
                    {realitySorted.length > 0 ? (
                      <ul className="space-y-1 mt-2">
                        {realitySorted.map(([cat, stats]) => {
                          const s = stats as any;
                          const acc = s.total > 0 ? Math.round((s.correct / s.total) * 100) : 0;
                          return (
                            <li key={cat} className="flex justify-between items-center group">
                              <span className="truncate pr-2 group-hover:text-slate-100 transition-colors" title={cat}>{cat}</span>
                              <span className="text-slate-400 font-mono text-xs py-0.5 px-2 bg-slate-800 rounded min-w-[4.5rem] text-center shrink-0">
                                {acc}% <span className="text-slate-500 opacity-70 ml-1">({s.correct}/{s.total})</span>
                              </span>
                            </li>
                          );
                        })}
                      </ul>
                    ) : (
                      <p className="text-slate-500 italic">No accuracy data</p>
                    )}
                  </div>
                </div>
                
                {summary.changes.length > 0 && (
                  <div className="mt-6 border-t border-slate-800 pt-4">
                    <h4 className="font-semibold text-slate-200 uppercase tracking-widest text-xs mb-3">Key Self-Awareness Events</h4>
                    <div className="max-h-40 overflow-y-auto pr-2 space-y-2 text-sm custom-scrollbar">
                      {summary.changes.map((ch, idx) => (
                        <div key={idx} className="flex items-start gap-3">
                          <div className={`mt-1.5 w-1.5 h-1.5 rounded-full flex-shrink-0 ${ch.delta > 0 ? 'bg-emerald-400' : 'bg-rose-400'}`} />
                          <div className="flex-1 leading-snug">
                            <span className="text-slate-500 font-mono text-xs mr-2 whitespace-nowrap">[Lvl {ch.chamber}]</span>
                            <span className={`font-mono mr-2 ${ch.delta > 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {ch.delta > 0 ? '+' : ''}{ch.delta}
                            </span>
                            <span className="text-slate-300">{ch.reason}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
