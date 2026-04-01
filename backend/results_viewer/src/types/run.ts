export interface State {
  run_id: string;
  chamber_index: number;
  max_chambers: number;
  total_chambers: number;
  hp: number;
  xp: number;
  skill_points: number;
  xp_next_threshold: number;
  active_skills: string[];
  abilities_remaining: {
    reroll: number;
    flee: number;
    double_down: number;
  };
  correct_count: number;
  wrong_count: number;
  rooms_visited: number;
  skills_unlocked_count: number;
  status: string;
  double_down_active: boolean;
}

export interface Event {
  timestamp: string;
  event_type: string;
  chamber_index: number;
  [key: string]: any;
}

export interface FullRun {
  run_id: string;
  final_state: State;
  events: Event[];
}

export interface SkillUnlock {
  skill_id: string;
  skill_name: string;
  sp_cost: number;
  xp_at_time: number;
  hp_at_time: number;
  chamber_index: number;
  reason: string;
  raw_response: string;
  chat_history_snippet?: any[];
}

export interface SkillSummary {
  skill_id: string;
  skill_name: string;
  chamber_index: number;
  reason: string;
}

export interface IncorrectAnswer {
  chamber_index: number;
  question_id: string;
  category: string;
  difficulty: number;
  options: any;
  correct_answer: string;
  model_answer: string;
  model_reasoning: string;
  hp_lost: number;
  is_fatal: boolean;
}

export interface CategoryAccuracy {
  [category: string]: {
    correct: number;
    wrong: number;
    total: number;
    accuracy: number;
  };
}

export interface AbilityUsage {
  chamber_index: number;
  timestamp: string;
  [key: string]: any;
}

export interface RunData {
  full_run: FullRun | null;
  skill_unlocks: SkillUnlock[] | null;
  skills_summary: SkillSummary[] | null;
  incorrect_answers: IncorrectAnswer[] | null;
  category_accuracy: CategoryAccuracy | null;
  ability_reroll?: AbilityUsage[] | null;
  ability_flee?: AbilityUsage[] | null;
  ability_double_down?: AbilityUsage[] | null;
}
