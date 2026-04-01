import React, { useMemo, useState } from 'react';
import type { RunData } from '../types/run';
import { ChevronDown, ChevronRight, CheckCircle2, XCircle, ArrowUpDown } from 'lucide-react';

interface Props {
  runs: RunData[];
}

interface AnswerRow {
  id: string;
  runId: string;
  chamber: number;
  question: string;
  category: string;
  difficulty: number;
  guess: string;
  actualAnswer: string;
  isCorrect: boolean;
  thought: string;
  rawResponse: string;
  chatLog: any[];
}

type SortKey = 'runId' | 'chamber' | 'category' | 'difficulty' | 'isCorrect';

export function AnswerInspector({ runs }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('chamber');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  const [filterRun, setFilterRun] = useState('All');
  const [filterCategory, setFilterCategory] = useState('All');
  const [filterDifficulty, setFilterDifficulty] = useState('All');
  const [filterCorrectness, setFilterCorrectness] = useState('All');
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  const rows = useMemo(() => {
    const extracted: AnswerRow[] = [];

    runs.forEach(run => {
      const runId = run.full_run?.run_id || 'unknown';

      // 1. Extract from full_run.events
      run.full_run?.events?.forEach(event => {
        if (event.event_type === 'wrong_answer' || event.event_type === 'ability_double_down') {
          if (!event.question) return;

          const raw = event.raw_response || event.chat_log_for_question?.[event.chat_log_for_question.length - 1]?.content || event.chat_for_question?.[event.chat_for_question.length - 1]?.content || '';
          
          let thought = '';
          const thoughtMatch = raw.match(/<thought>([\s\S]*?)<\/thought>/);
          if (thoughtMatch) {
            thought = thoughtMatch[1];
          } else {
            const reasonMatch = raw.match(/<reason>([\s\S]*?)<\/reason>/);
            if (reasonMatch) thought = reasonMatch[1];
          }

          let guess = event.llm_answer || '';
          if (!guess) {
            const faMatch = raw.match(/<final_answer>([\s\S]*?)<\/final_answer>/);
            if (faMatch) guess = faMatch[1];
          }

          const isCorrect = event.event_type === 'wrong_answer' ? false : event.outcome === 'correct';

          extracted.push({
            id: event.task_id || `${runId}-${event.chamber_index}-${Math.random()}`,
            runId,
            chamber: event.chamber_index ?? 0,
            question: event.question,
            category: event.category || 'Unknown',
            difficulty: event.level ?? 1,
            guess: guess,
            actualAnswer: event.correct_answer || (isCorrect ? 'Correct (Double Down)' : 'Unknown'),
            isCorrect,
            thought,
            rawResponse: raw,
            chatLog: event.chat_log_for_question || event.chat_for_question || []
          });
        }
      });

      // 2. Extract from incorrect_answers (deduplicate by id)
      run.incorrect_answers?.forEach((ans: any) => {
        const id = ans.task_id || ans.question_id || `${runId}-${ans.chamber_index}-${Math.random()}`;
        if (!extracted.find(r => r.id === id && r.runId === runId)) {
          const raw = ans.raw_response || ans.chat_log_for_question?.[1]?.content || ans.chat_log_for_question?.[0]?.content || '';
          
          let thought = '';
          const thoughtMatch = raw.match(/<thought>([\s\S]*?)<\/thought>/);
          if (thoughtMatch) {
            thought = thoughtMatch[1];
          } else {
            const reasonMatch = raw.match(/<reason>([\s\S]*?)<\/reason>/);
            if (reasonMatch) thought = reasonMatch[1];
          }

          extracted.push({
            id,
            runId,
            chamber: ans.chamber_index ?? 0,
            question: ans.question || 'Unknown Question',
            category: ans.category || 'Unknown',
            difficulty: ans.level || ans.difficulty || 1,
            guess: ans.llm_answer || ans.model_answer || '',
            actualAnswer: ans.correct_answer || ans.expected_answer || '',
            isCorrect: false,
            thought,
            rawResponse: raw,
            chatLog: ans.chat_log_for_question || []
          });
        }
      });
    });

    return extracted;
  }, [runs]);

  // Unique options for filters
  const runsOptions = useMemo(() => ['All', ...new Set(rows.map(r => r.runId))], [rows]);
  const categoryOptions = useMemo(() => ['All', ...new Set(rows.map(r => r.category))], [rows]);
  const difficultyOptions = useMemo(() => ['All', ...new Set(rows.map(r => r.difficulty.toString()))], [rows]);

  const sortedAndFiltered = useMemo(() => {
    let filtered = rows;
    
    if (filterRun !== 'All') filtered = filtered.filter(r => r.runId === filterRun);
    if (filterCategory !== 'All') filtered = filtered.filter(r => r.category === filterCategory);
    if (filterDifficulty !== 'All') filtered = filtered.filter(r => r.difficulty.toString() === filterDifficulty);
    if (filterCorrectness !== 'All') {
      const isC = filterCorrectness === 'Correct';
      filtered = filtered.filter(r => r.isCorrect === isC);
    }

    return filtered.sort((a, b) => {
      let valA: any = a[sortKey];
      let valB: any = b[sortKey];

      if (sortKey === 'category' || sortKey === 'runId') {
        valA = valA.toString().toLowerCase();
        valB = valB.toString().toLowerCase();
      }

      if (valA < valB) return sortDir === 'asc' ? -1 : 1;
      if (valA > valB) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
  }, [rows, filterRun, filterCategory, filterDifficulty, filterCorrectness, sortKey, sortDir]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const toggleRow = (id: string) => {
    const next = new Set(expandedRows);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setExpandedRows(next);
  };

  const renderSortIcon = (key: SortKey) => {
    return (
      <ArrowUpDown 
        className={`inline-block ml-1 w-4 h-4 cursor-pointer transition-colors ${sortKey === key ? 'text-blue-400' : 'text-gray-500 hover:text-gray-300'}`} 
        onClick={() => handleSort(key)} 
      />
    );
  };

  return (
    <div className="flex flex-col space-y-4 p-4 text-gray-200">
      <div className="flex flex-wrap gap-4 bg-gray-900/50 p-4 rounded-lg border border-gray-800">
        <label className="flex flex-col gap-1 text-sm">
          Run:
          <select className="bg-gray-800 border border-gray-700 rounded p-1" value={filterRun} onChange={e => setFilterRun(e.target.value)}>
            {runsOptions.map(o => <option key={o} value={o}>{o}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Category:
          <select className="bg-gray-800 border border-gray-700 rounded p-1" value={filterCategory} onChange={e => setFilterCategory(e.target.value)}>
            {categoryOptions.map(o => <option key={o} value={o}>{o}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Difficulty:
          <select className="bg-gray-800 border border-gray-700 rounded p-1" value={filterDifficulty} onChange={e => setFilterDifficulty(e.target.value)}>
            {difficultyOptions.map(o => <option key={o} value={o}>{o}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Correctness:
          <select className="bg-gray-800 border border-gray-700 rounded p-1" value={filterCorrectness} onChange={e => setFilterCorrectness(e.target.value)}>
            <option value="All">All</option>
            <option value="Correct">Correct</option>
            <option value="Incorrect">Incorrect</option>
          </select>
        </label>
      </div>

      <div className="overflow-x-auto border border-gray-800 rounded-lg bg-gray-900/30">
        <table className="w-full text-left text-sm border-collapse">
          <thead className="bg-gray-900 border-b border-gray-800 text-gray-400">
            <tr>
              <th className="p-3 w-8"></th>
              <th className="p-3 whitespace-nowrap">Run {renderSortIcon('runId')}</th>
              <th className="p-3 whitespace-nowrap">Chamber {renderSortIcon('chamber')}</th>
              <th className="p-3">Question Summary</th>
              <th className="p-3 whitespace-nowrap">Category {renderSortIcon('category')}</th>
              <th className="p-3 whitespace-nowrap">Level {renderSortIcon('difficulty')}</th>
              <th className="p-3">Guess</th>
              <th className="p-3">Actual Answer</th>
              <th className="p-3 text-center whitespace-nowrap">Correct? {renderSortIcon('isCorrect')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {sortedAndFiltered.map(row => {
              const isExpanded = expandedRows.has(row.id);
              return (
                <React.Fragment key={row.id}>
                  <tr 
                    className="hover:bg-gray-800/50 cursor-pointer transition-colors"
                    onClick={() => toggleRow(row.id)}
                  >
                    <td className="p-3">
                      {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    </td>
                    <td className="p-3 font-mono text-xs text-gray-500">{row.runId.substring(0, 8)}</td>
                    <td className="p-3 text-center">{row.chamber}</td>
                    <td className="p-3 max-w-xs xl:max-w-md truncate" title={row.question}>{row.question}</td>
                    <td className="p-3 text-xs text-gray-400">{row.category}</td>
                    <td className="p-3 text-center">{row.difficulty}</td>
                    <td className="p-3 max-w-[150px] truncate text-orange-200">{row.guess}</td>
                    <td className="p-3 max-w-[150px] truncate text-green-300">{row.actualAnswer}</td>
                    <td className="p-3 flex justify-center">
                      {row.isCorrect 
                        ? <CheckCircle2 className="w-5 h-5 text-green-500" /> 
                        : <XCircle className="w-5 h-5 text-red-500" />}
                    </td>
                  </tr>
                  
                  {isExpanded && (
                    <tr className="bg-gray-800/30">
                      <td colSpan={9} className="p-4 border-l-4 border-blue-500/50">
                        <div className="flex flex-col gap-6">
                          
                          <div className="space-y-2">
                            <h4 className="text-sm font-semibold text-blue-400 uppercase tracking-widest">Internal Reasoning</h4>
                            {row.thought ? (
                              <div className="p-3 bg-gray-900 rounded font-mono text-xs whitespace-pre-wrap leading-relaxed text-gray-300 border border-gray-700/50">
                                {row.thought}
                              </div>
                            ) : (
                              <div className="text-xs text-gray-500 italic">No explicit reasoning tag found.</div>
                            )}
                          </div>

                          <div className="space-y-3">
                            <h4 className="text-sm font-semibold text-purple-400 uppercase tracking-widest">Prompt & Output Log</h4>
                            <div className="space-y-3">
                              {row.chatLog && row.chatLog.length > 0 ? (
                                row.chatLog.map((msg, i) => (
                                  <div key={i} className={`p-3 rounded text-xs font-mono whitespace-pre-wrap border ${msg.role === 'user' ? 'bg-blue-900/10 border-blue-900/30 text-blue-100' : 'bg-green-900/10 border-green-900/30 text-green-100'}`}>
                                    <div className="font-bold mb-1 opacity-70">[{msg.role.toUpperCase()}]</div>
                                    {msg.content}
                                  </div>
                                ))
                              ) : (
                                <div className="p-3 rounded text-xs font-mono whitespace-pre-wrap border bg-yellow-900/10 border-yellow-900/30 text-amber-200">
                                  <div className="font-bold mb-1 opacity-70">[RAW RESPONSE MODEL]</div>
                                  {row.rawResponse || 'No logs available.'}
                                </div>
                              )}
                            </div>
                          </div>

                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
            
            {sortedAndFiltered.length === 0 && (
              <tr>
                <td colSpan={9} className="p-8 text-center text-gray-500">
                  No answers found matching the selected filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
