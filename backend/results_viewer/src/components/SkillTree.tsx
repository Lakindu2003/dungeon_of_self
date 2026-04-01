import React from "react";
import type { RunData } from "../types/run";
import { runColors } from "./Overview";
import { Zap, ArrowRight, LockOpen } from "lucide-react";

export function SkillTree({ runs }: { runs: RunData[] }) {
  if (runs.length === 0) return <p className="text-slate-400">No runs loaded.</p>;

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold mb-4 text-slate-100 flex items-center gap-2">
        <Zap className="w-6 h-6 text-yellow-400" />
        Skill Tree
      </h2>
      <div className="flex flex-col gap-6">
        {runs.map((r, i) => {
          const runId = r.full_run?.run_id?.substring(0, 8) ?? `Run ${i + 1}`;
          const borderColorClass = runColors[i % runColors.length];
          const unlocks = r.skill_unlocks || [];

          return (
            <div key={i} className={`p-4 border-l-4 bg-slate-900 shadow ${borderColorClass} rounded-r-lg`}>
              <h3 className="font-bold border-b border-slate-800 pb-2 mb-4 bg-slate-800/50 px-3 py-1 rounded w-fit">
                Run {runId}
              </h3>
              
              {unlocks.length === 0 ? (
                <p className="text-sm text-slate-500 italic">No skills unlocked in this run.</p>
              ) : (
                <div className="flex flex-col gap-4">
                  {unlocks.map((skill, idx) => (
                    <div key={idx} className="flex items-start gap-4 rel text-sm">
                      <div className="flex flex-col items-center gap-1 z-10 pt-1">
                        <div className={`p-2 rounded-full bg-slate-800 border shadow-md ${borderColorClass.replace('border-l-4', 'border')}`}>
                           <LockOpen className="w-4 h-4 text-slate-300" />
                        </div>
                        {idx !== unlocks.length - 1 && (
                          <div className="w-0.5 h-full min-h-8 bg-slate-700 rounded my-1" />
                        )}
                      </div>
                      
                      <div className="bg-slate-800/80 p-3 rounded-lg border border-slate-700 flex-1 hover:border-slate-500 transition-colors">
                        <div className="flex justify-between items-center mb-1">
                          <span className="font-semibold text-slate-200">
                             {skill.skill_name || skill.skill_id}
                          </span>
                          <span className="text-xs font-mono text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                            Chamber #{skill.chamber_index}
                          </span>
                        </div>
                        {skill.reason && (
                          <p className="text-slate-400 mt-2 text-xs leading-relaxed italic border-l-2 border-slate-600 pl-2">
                            "{skill.reason}"
                          </p>
                        )}
                        <div className="mt-2 text-xs flex gap-3 text-slate-500">
                          {skill.sp_cost !== undefined && <span>SP Cost: {skill.sp_cost}</span>}
                          {skill.xp_at_time !== undefined && <span>XP: {skill.xp_at_time}</span>}
                          {skill.hp_at_time !== undefined && <span>HP: {skill.hp_at_time}</span>}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}