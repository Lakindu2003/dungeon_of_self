import { useMemo } from "react";
import type { ReactNode } from "react";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip, Legend, LineChart, Line, XAxis, YAxis, CartesianGrid, ReferenceDot } from "recharts";
import { AlertCircle } from "lucide-react";
import clsx from "clsx";
import { twMerge } from "tailwind-merge";
import type { RunData } from "../types/run";

export const runColors = [
  { className: 'text-blue-400', hex: '#60A5FA' },
  { className: 'text-amber-400', hex: '#FBBF24' },
  { className: 'text-rose-400', hex: '#FB7185' },
  { className: 'text-emerald-400', hex: '#34D399' },
  { className: 'text-purple-400', hex: '#A78BFA' },
];

function cn(...inputs: (string | undefined | null | false)[]) {
  return twMerge(clsx(inputs));
}

interface StatProps {
  label: string;
  getValue: (r: RunData) => string | number | ReactNode;
  runs: RunData[];
  showDelta?: boolean;
}

export function Overview({ runs }: { runs: RunData[] }) {
  // Radar data
  const radarData = useMemo(() => {
    if (!runs) return [];
    const cats = new Set<string>();
    runs.forEach(r => {
      if (r.category_accuracy) {
        Object.keys(r.category_accuracy).forEach(k => cats.add(k));
      }
    });

    return Array.from(cats).map(category => {
      const dp: Record<string, unknown> = { subject: category };
      runs.forEach((r, i) => {
        const acc = r.category_accuracy?.[category]?.accuracy ?? 0;
        dp[`Run ${i + 1}`] = acc * 100; // Store as percentage
      });
      return dp;
    });
  }, [runs]);

  // HP Burn-down data
  const hpData = useMemo(() => {
    if (!runs) return [];
    let mx = 0;
    runs.forEach(r => {
      const chambers = r.full_run?.final_state?.chamber_index ?? 0;
      if (chambers > mx) mx = chambers;
    });
    const maxChambers = mx;
    const dataPoints: Record<string, unknown>[] = [];
    
    for (let i = 0; i <= maxChambers; i++) {
      const point: Record<string, unknown> = { chamber: i };
      runs.forEach((r, idx) => {
        const events = r.full_run?.events || [];
        // Extract HP after events around this chamber or fallback to previous known
        const chamberEvents = events.filter(e => e.chamber_index === i && (e.event_type !== "question" && !e.event_type.includes("ability") || e.hp !== undefined));
        
        let hpVal = null;
        if (chamberEvents.length > 0) {
          // get the last event's hp in this chamber if available
          hpVal = [...chamberEvents].reverse().find(e => e.hp !== undefined)?.hp;
        }

        if (hpVal === null || hpVal === undefined) {
          // Find the last known HP prior to this chamber
          const pastEvents = events.filter(e => e.chamber_index < i && e.hp !== undefined);
          if (pastEvents.length > 0) {
            hpVal = pastEvents[pastEvents.length - 1].hp;
          } else {
            hpVal = 100; // starting HP
          }
        }
        point[`run${idx + 1}`] = hpVal ?? 100;
        
        // Find specific drops for annotations
        const wrongAnswers = r.incorrect_answers?.filter(ia => ia.chamber_index === i) || [];
        wrongAnswers.forEach(wa => {
           point[`run${idx + 1}_drop`] = hpVal; // reference point for tooltip or dot
           point[`run${idx + 1}_reason`] = wa.hp_lost > 20 ? 'Double Down Wrong (-40)' : 'Wrong Answer (-20)';
        });
      });
      dataPoints.push(point);
    }
    return dataPoints;
  }, [runs]);

  if (!runs || runs.length === 0) return <p className="text-slate-400">No runs loaded.</p>;

  // Detect overconfidence flag for each run
  const overconfidenceFlags = runs.map(run => {
    if (!run.full_run || !run.full_run.events || run.full_run.events.length === 0) return false;
    const firstEvent = run.full_run.events.find(e => e.chamber_index === 0 && e.event_type !== "start");
    if (!firstEvent) return false;
    return firstEvent.event_type === "ability_double_down" || firstEvent.event_type === "double_down";
  });

  const getAccuracy = (r: RunData) => {
    const c = r.full_run?.final_state?.correct_count ?? 0;
    const w = r.full_run?.final_state?.wrong_count ?? 0;
    const tot = c + w;
    return tot > 0 ? ((c / tot) * 100).toFixed(1) + '%' : '0%';
  };

  const getDeltaString = (v1: number, v2: number, postfix = '') => {
    const diff = v2 - v1;
    if (diff > 0) return <span className="text-emerald-400">+{diff.toFixed(postfix === '%' ? 1 : 0)}{postfix}</span>;
    if (diff < 0) return <span className="text-rose-400">{diff.toFixed(postfix === '%' ? 1 : 0)}{postfix}</span>;
    return <span className="text-slate-500">0{postfix}</span>;
  };

  const calculateDelta = (getValue: (r: RunData) => string | number | ReactNode) => {
    if (runs.length < 2) return null;
    const v1 = getValue(runs[0]);
    const v2 = getValue(runs[runs.length - 1]);
    
    // Attempt parse
    const n1 = parseFloat(String(v1).replace('%', ''));
    const n2 = parseFloat(String(v2).replace('%', ''));

    if (!isNaN(n1) && !isNaN(n2)) {
      const isPercent = String(v1).includes('%');
      return getDeltaString(n1, n2, isPercent ? '%' : '');
    }
    return <span className="text-slate-500">-</span>;
  };

  const StatRow = ({ label, getValue, runs, showDelta = true }: StatProps) => (
    <tr className="border-b border-slate-800/50 hover:bg-slate-800/20">
      <td className="py-3 px-4 font-medium text-slate-300">{label}</td>
      {runs.map((r, i) => (
        <td key={i} className={cn("py-3 px-4 text-center", runColors[i % runColors.length]?.className)}>
          {getValue(r)}
        </td>
      ))}
      {runs.length >= 2 && showDelta && (
        <td className="py-3 px-4 text-center font-mono text-sm bg-slate-800/10">
          {calculateDelta(getValue)}
        </td>
      )}
    </tr>
  );

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      
      {/* Notifications / Flags */}
      <div className="flex flex-col gap-2">
        {overconfidenceFlags.map((flag, idx) => flag && (
          <div key={idx} className="flex items-center gap-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 px-4 py-3 rounded-md shadow-sm">
            <AlertCircle className="w-5 h-5" />
            <p className="text-sm font-medium">
              Run {idx + 1}: Agent double-downed immediately without any performance history.
            </p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* STATS TABLE */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl flex flex-col">
          <div className="bg-slate-800/80 px-6 py-4 border-b border-slate-700/50">
            <h3 className="font-semibold text-lg text-slate-100">Stat Comparison</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-slate-400 bg-slate-900/50 uppercase border-b border-slate-700/50">
                <tr>
                  <th className="py-3 px-4 font-semibold">Metric</th>
                  {runs.map((_, i) => (
                    <th key={i} className="py-3 px-4 text-center font-semibold">Run {i + 1}</th>
                  ))}
                  {runs.length >= 2 && <th className="py-3 px-4 text-center font-semibold text-slate-500">Delta</th>}
                </tr>
              </thead>
              <tbody>
                <StatRow label="HP at Death / End" getValue={r => r.full_run?.final_state?.hp ?? 0} runs={runs} />
                <StatRow label="Rooms Visited" getValue={r => r.full_run?.final_state?.rooms_visited ?? 0} runs={runs} />
                <StatRow label="Correct Answers" getValue={r => r.full_run?.final_state?.correct_count ?? 0} runs={runs} />
                <StatRow label="Wrong Answers" getValue={r => r.full_run?.final_state?.wrong_count ?? 0} runs={runs} />
                <StatRow label="Accuracy" getValue={r => getAccuracy(r)} runs={runs} />
                <StatRow label="Skills Unlocked" getValue={r => r.full_run?.final_state?.skills_unlocked_count ?? 0} runs={runs} />
                <StatRow label="XP Earned" getValue={r => r.full_run?.final_state?.xp ?? 0} runs={runs} />
                <StatRow label="Double-Downs Used" getValue={r => r.full_run?.events?.filter(e => e.event_type === "ability_double_down" || e.event_type === "double_down").length ?? 0} runs={runs} />
                <StatRow label="Flees Used" getValue={r => r.full_run?.events?.filter(e => e.event_type === "ability_flee" || e.event_type === "flee").length ?? 0} runs={runs} />
                <StatRow label="Rerolls Used" getValue={r => r.full_run?.events?.filter(e => e.event_type === "ability_reroll" || e.event_type === "reroll").length ?? 0} runs={runs} />
              </tbody>
            </table>
          </div>
        </div>

        {/* RADAR CHART */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl p-6 flex flex-col items-center justify-center min-h-[400px]">
          <h3 className="font-semibold text-lg text-slate-100 self-start mb-2">Category Accuracy</h3>
          {radarData.length > 0 ? (
            <ResponsiveContainer width="100%" height={320}>
              <RadarChart cx="50%" cy="50%" outerRadius="75%" data={radarData}>
                <PolarGrid stroke="#334155" />
                <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: '#64748b' }} tickCount={6} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f8fafc' }} 
                  itemStyle={{ color: '#f8fafc' }}
                  formatter={(value: unknown) => {
                    const num = typeof value === 'number' ? value : parseFloat(String(value));
                    return [`${!isNaN(num) ? num.toFixed(1) : value}%`, 'Accuracy'];
                  }}
                />
                <Legend iconType="circle" />
                {runs.map((_, i) => (
                  <Radar 
                    key={i} 
                    name={`Run ${i + 1}`} 
                    dataKey={`Run ${i + 1}`} 
                    stroke={runColors[i % runColors.length].hex} 
                    fill={runColors[i % runColors.length].hex} 
                    fillOpacity={0.4} 
                  />
                ))}
              </RadarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-slate-500 my-auto">No category data available.</p>
          )}
        </div>
      </div>

      {/* HP BURN-DOWN LINE CHART */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl p-6 min-h-[400px]">
        <h3 className="font-semibold text-lg text-slate-100 mb-6">HP Burn-down Over Time</h3>
        {hpData.length > 0 ? (
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={hpData} margin={{ top: 20, right: 30, left: 10, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis 
                dataKey="chamber" 
                stroke="#64748b" 
                tick={{ fill: '#94a3b8' }}
                label={{ value: 'Chamber Index', position: 'bottom', fill: '#94a3b8' }}
              />
              <YAxis 
                domain={[0, 100]} 
                stroke="#64748b" 
                tick={{ fill: '#94a3b8' }} 
                label={{ value: 'Health Points (HP)', angle: -90, position: 'insideLeft', fill: '#94a3b8', dy: 40 }}
              />
              <Tooltip 
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f8fafc', borderRadius: '0.375rem' }} 
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    return (
                      <div className="bg-slate-900 border border-slate-700 p-3 rounded-md shadow-lg">
                        <p className="text-slate-300 font-semibold mb-2">Chamber {label}</p>
                        {payload.map((p: any, idx) => {
                          const dropReason = p.payload[`${p.dataKey}_reason`];
                          return (
                            <div key={idx} className="flex flex-col mb-1 text-sm">
                              <span style={{ color: p.color }} className="font-medium">
                                {p.name}: {p.value} HP
                              </span>
                              {dropReason && (
                                <span className="text-rose-400 text-xs mt-1 ml-2">⚠️ {dropReason as string}</span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Legend verticalAlign="top" height={36} iconType="circle" />
              {runs.map((_, i) => (
                <Line 
                  key={i} 
                  type="monotone" 
                  dataKey={`run${i + 1}`} 
                  name={`Run ${i + 1}`} 
                  stroke={runColors[i % runColors.length].hex} 
                  strokeWidth={3}
                  dot={(props) => {
                    const { cx, cy, payload, index } = props;
                    const dropReason = payload[`run${i + 1}_reason`];
                    if (dropReason) {
                      return <ReferenceDot key={`drop-${index}`} x={cx} y={cy} r={5} fill="#f43f5e" stroke="none" />;
                    }
                    if (index % 5 === 0) {
                      return <circle key={`dot-${index}`} cx={cx} cy={cy} r={2} fill={runColors[i % runColors.length].hex} />;
                    }
                    return <span key={`empty-${index}`}/>;
                  }}
                  activeDot={{ r: 6, strokeWidth: 0 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-slate-500 flex justify-center items-center h-[300px]">No HP progression data available.</p>
        )}
      </div>

    </div>
  );
}
