// src/components/Timeline.tsx
import React, { useMemo } from "react";
import type { RunData, Event } from "../types/run";
import { Circle, Check, X, Star, Diamond, ArrowRight, RefreshCcw, AlertTriangle } from "lucide-react";

const MAX_CHAMBERS = 20; // Default max, can be inferred from run data

type ParsedEvent = {
  id: string;
  type: string;
  chamber_index: number;
  hp: number;
  xp: number;
  raw_response?: string;
  active_tools?: string[];
  isCorrect?: boolean;
  skillId?: string;
};

// Helper to parse events
function parseTimelineEvents(events: Event[]): ParsedEvent[] {
  return events.map((ev, i) => {
    let type = ev.event_type;
    let isCorrect = undefined;

    // determine correct/wrong from answer event
    if (type === "answer") {
      isCorrect = ev.is_correct;
      type = isCorrect ? "correct_answer" : "wrong_answer";
    }

    if (type === "ability_double_down") {
      isCorrect = ev.is_correct;
      type = isCorrect ? "double_down_correct" : "double_down_wrong";
    }

    return {
      id: `${i}-${ev.event_type}`,
      type,
      chamber_index: ev.chamber_index,
      hp: ev.state?.hp ?? 0,
      xp: ev.state?.xp ?? 0,
      raw_response: ev.raw_response,
      active_tools: ev.active_tools || [],
      isCorrect,
      skillId: ev.skill_id || ev.unlocked_skill?.skill_id,
    };
  });
}

function swimlaneEvents(events: ParsedEvent[]) {
  // We want to group by chamber index to draw HP/XP step charts and place icons
  const byChamber = new Map<number, ParsedEvent[]>();
  events.forEach((ev) => {
    if (!byChamber.has(ev.chamber_index)) {
      byChamber.set(ev.chamber_index, []);
    }
    byChamber.get(ev.chamber_index)!.push(ev);
  });
  return byChamber;
}

export function Timeline({ runs }: { runs: RunData[] }) {
  if (runs.length === 0) return <p className="text-slate-400">No runs loaded.</p>;

  return (
    <div className="space-y-8 overflow-x-auto pb-4">
      <h2 className="text-xl font-semibold mb-4 text-slate-100">Timeline view</h2>
      
      <div className="flex flex-col gap-12 min-w-[800px]">
        {runs.map((r, i) => {
          if (!r.full_run) return null;
          
          const maxChamber = r.full_run.final_state?.max_chambers ?? MAX_CHAMBERS;
          const parsed = parseTimelineEvents(r.full_run.events);
          const chamberData = swimlaneEvents(parsed);
          
          // Compute points for step chart. Each chamber is a step.
          // Let's assume the width of each chamber is 60px
          const chamberWidth = 60;
          const height = 100; // max HP is expected to be ~100 or scale it
          
          let points = [];
          for (let c = 0; c <= maxChamber; c++) {
            const evts = chamberData.get(c) || [];
            // Last event in chamber defines ending HP/XP
            const lastStateEv = evts.slice().reverse().find(e => e.hp !== undefined);
            points.push({
              chamber: c,
              hp: lastStateEv ? lastStateEv.hp : (points[c-1]?.hp ?? 100),
              xp: lastStateEv ? lastStateEv.xp : (points[c-1]?.xp ?? 0),
              events: evts
            });
          }

          const maxHpObserved = Math.max(100, ...points.map(p => p.hp));
          const maxXpObserved = Math.max(100, ...points.map(p => p.xp));

          return (
            <div key={i} className="relative flex-1 p-4 border border-slate-700 bg-slate-900 rounded shadow">
               <h3 className="font-bold border-b border-slate-800 pb-2 mb-4 text-slate-300">
                   Run {r.full_run.run_id.substring(0, 8)} 
               </h3>
               
               <div className="relative mt-8" style={{ width: maxChamber * chamberWidth, height }}>
                  {/* Axis line */}
                  <div className="absolute bottom-0 left-0 w-full h-[1px] bg-slate-600"></div>

                  {/* Step chart lines overlay */}
                  <svg className="absolute inset-0 pointer-events-none" width={maxChamber * chamberWidth} height={height}>
                     {/* HP Step Line (Red) */}
                     <polyline
                        points={points.map((p, i) => `${i * chamberWidth},${height - (p.hp / maxHpObserved) * height}`).join(" ")}
                        fill="none"
                        stroke="rgba(239, 68, 68, 0.4)"
                        strokeWidth="2"
                     />
                     {/* XP Step Line (Blue) */}
                     <polyline
                        points={points.map((p, i) => `${i * chamberWidth},${height - (p.xp / maxXpObserved) * height}`).join(" ")}
                        fill="none"
                        stroke="rgba(59, 130, 246, 0.4)"
                        strokeWidth="2"
                        strokeDasharray="4,2"
                     />
                  </svg>

                  {/* Chamber Markers and Events */}
                  {points.map((p, idx) => {
                     const left = idx * chamberWidth;
                     return (
                       <div key={idx} className="absolute top-0 bottom-0" style={{ left, width: chamberWidth }}>
                           {/* X-axis tick */}
                           <div className="absolute bottom-[-20px] left-0 text-xs text-slate-500">{idx}</div>
                           
                           {/* Events rendering */}
                           <div className="absolute top-4 left-[-10px] w-6 flex flex-col items-center gap-1">
                             {p.events.map((ev, evIdx) => {
                               // Check for fake tool call
                               const isFakeTool = (ev.type.includes("answer") || ev.type.includes("strategy")) &&
                                 (ev.raw_response?.includes("<tool_code>") || ev.raw_response?.includes("import search")) &&
                                 (!ev.active_tools || ev.active_tools.length === 0);

                               let Icon = null;
                               let colorClass = "text-slate-400";
                               
                               switch (ev.type) {
                                  case "strategy_call": Icon = Circle; colorClass = "text-slate-500 fill-slate-500"; break;
                                  case "correct_answer": Icon = Check; colorClass = "text-green-500"; break;
                                  case "wrong_answer": Icon = X; colorClass = "text-red-500"; break;
                                  case "double_down_correct": Icon = Star; colorClass = "text-yellow-500 fill-yellow-500"; break;
                                  case "double_down_wrong": Icon = X; colorClass = "text-orange-500"; break;
                                  case "skill_unlock": Icon = Diamond; colorClass = "text-cyan-400 fill-cyan-400"; break;
                                  case "ability_flee": Icon = ArrowRight; colorClass = "text-yellow-400"; break;
                                  case "ability_reroll": Icon = RefreshCcw; colorClass = "text-purple-400"; break;
                               }

                               return (
                                 <div key={ev.id} className="relative z-10" title={`Chamber ${ev.chamber_index} - ${ev.type}`}>
                                   {isFakeTool && (
                                      <div className="absolute -top-2 -right-2 z-20" title="Fake tool attempt!">
                                        <AlertTriangle size={12} className="text-red-600 fill-current" />
                                      </div>
                                   )}
                                   {Icon && <Icon size={16} className={colorClass} />}
                                 </div>
                               );
                             })}
                           </div>

                           {/* Skill Unlock Vertical Lines */}
                           {p.events.filter(e => e.type === "skill_unlock").map((ev, evIdx) => (
                             <div key={`skill-${ev.id}`} className="absolute top-[-30px] bottom-0 left-0 border-l border-dashed border-cyan-500/50">
                               <div className="absolute -top-4 -left-10 w-20 text-center text-[10px] text-cyan-400 whitespace-nowrap">
                                 {ev.skillId}
                               </div>
                             </div>
                           ))}
                       </div>
                     );
                  })}
               </div>
               
               <div className="text-xs text-slate-500 mt-8 flex flex-wrap gap-4">
                  <span className="flex items-center gap-1"><span className="w-3 h-[2px] bg-red-500/40 inline-block"></span> HP </span>
                  <span className="flex items-center gap-1"><span className="w-3 h-[2px] bg-blue-500/40 inline-block border border-dashed border-blue-500/40"></span> XP </span>
               </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}