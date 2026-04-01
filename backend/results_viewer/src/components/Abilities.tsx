import React, { useMemo } from "react";
import type { RunData } from "../types/run";
import { runColors } from "./Overview";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";

export function Abilities({ runs }: { runs: RunData[] }) {
  const stats = useMemo(() => {
    let rerollCount = 0;
    let fleeCount = 0;
    let fleeHpLoss = 0;
    let ddCount = 0;
    let ddSuccess = 0;

    runs.forEach((r) => {
      const rerolls = r.ability_reroll || [];
      const flees = r.ability_flee || [];
      const dds = r.ability_double_down || [];

      rerollCount += rerolls.length;
      fleeCount += flees.length;
      ddCount += dds.length;

      flees.forEach((f) => {
        // hp_delta is typically negative; take its absolute value for loss
        fleeHpLoss += Math.abs(f.hp_delta || 0);
      });

      dds.forEach((d) => {
        if (d.outcome === "correct") {
          ddSuccess++;
        }
      });
    });

    return {
      rerollCount,
      fleeCount,
      fleeHpAvg: fleeCount > 0 ? (fleeHpLoss / fleeCount).toFixed(1) : 0,
      ddCount,
      ddSuccessRate: ddCount > 0 ? ((ddSuccess / ddCount) * 100).toFixed(1) : 0,
    };
  }, [runs]);

  if (runs.length === 0) return <p className="text-slate-400">No runs loaded.</p>;

  const pieData = [
    { name: "Reroll", value: stats.rerollCount, color: "#3b82f6" },
    { name: "Flee", value: stats.fleeCount, color: "#ef4444" },
    { name: "Double Down", value: stats.ddCount, color: "#10b981" },
  ];

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold mb-4 text-slate-100">Abilities Summary</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 border border-blue-900/50 rounded bg-blue-900/20 shadow">
          <h3 className="text-blue-400 font-semibold mb-1">Reroll Usage</h3>
          <p className="text-3xl font-bold text-slate-100">{stats.rerollCount}</p>
        </div>
        <div className="p-4 border border-red-900/50 rounded bg-red-900/20 shadow">
          <h3 className="text-red-400 font-semibold mb-1">Flee Usage</h3>
          <p className="text-3xl font-bold text-slate-100">{stats.fleeCount}</p>
          <p className="text-sm text-slate-400 mt-1">Avg HP Loss: {stats.fleeHpAvg}</p>
        </div>
        <div className="p-4 border border-emerald-900/50 rounded bg-emerald-900/20 shadow">
          <h3 className="text-emerald-400 font-semibold mb-1">Double Down Usage</h3>
          <p className="text-3xl font-bold text-slate-100">{stats.ddCount}</p>
          <p className="text-sm text-slate-400 mt-1">Success Rate: {stats.ddSuccessRate}%</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="p-4 border border-slate-700 bg-slate-800/50 rounded shadow">
          <h3 className="font-semibold mb-4 text-slate-200">Ability Usage Breakdown</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                  itemStyle={{ color: '#f8fafc' }}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="p-4 border border-slate-700 bg-slate-800/50 rounded shadow">
          <h3 className="font-semibold mb-4 text-slate-200">Abilities per Run</h3>
          <div className="h-64 overflow-y-auto">
            {runs.map((r, i) => {
              const rId = r.full_run?.run_id?.substring(0, 8) ?? `Run ${i + 1}`;
              const rReroll = r.ability_reroll?.length || 0;
              const rFlee = r.ability_flee?.length || 0;
              const rDD = r.ability_double_down?.length || 0;

              return (
                <div key={i} className="mb-3 p-3 bg-slate-900/50 border border-slate-700 rounded text-sm flex justify-between items-center space-x-4">
                  <span className="font-mono text-slate-300 w-24 truncate" style={{ color: runColors[i % runColors.length] }}>{rId}</span>
                  <div className="flex w-full justify-around text-slate-400">
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500"></span>{rReroll} Reroll</span>
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500"></span>{rFlee} Flee</span>
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500"></span>{rDD} Double Down</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}