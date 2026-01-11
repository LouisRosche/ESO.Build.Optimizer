// ESO Classes
export type ESOClass =
  | 'Dragonknight'
  | 'Nightblade'
  | 'Sorcerer'
  | 'Templar'
  | 'Warden'
  | 'Necromancer'
  | 'Arcanist';

// Content Types
export type ContentType = 'dungeon' | 'trial' | 'arena' | 'overworld' | 'pvp';
export type Difficulty = 'normal' | 'veteran' | 'hardmode';

// Set Types
export type SetType = 'Dungeon' | 'Trial' | 'Overland' | 'Monster' | 'Craftable' | 'Mythic' | 'Arena' | 'PvP';
export type PVETier = 'S' | 'A' | 'B' | 'C' | 'F';

// Recommendation Categories
export type RecommendationCategory = 'gear' | 'skill' | 'execution' | 'build';

// Combat Run
export interface CombatRun {
  run_id: string;
  player_id: string;
  character_name: string;
  timestamp: string;
  content: ContentInfo;
  duration_sec: number;
  success: boolean;
  group_size: number;
  build_snapshot: BuildSnapshot;
  metrics: CombatMetrics;
  contribution_scores?: ContributionScores;
}

export interface ContentInfo {
  type: ContentType;
  name: string;
  difficulty: Difficulty;
}

export interface BuildSnapshot {
  class: ESOClass;
  subclass?: ESOClass;
  race: string;
  cp_level: number;
  sets: string[];
  skills_front: string[];
  skills_back: string[];
  champion_points?: ChampionPoints;
}

export interface ChampionPoints {
  warfare: Record<string, number>;
  fitness: Record<string, number>;
  craft: Record<string, number>;
}

export interface CombatMetrics {
  damage_done: number;
  dps: number;
  crit_rate: number;
  dot_uptime: BuffUptime[];
  healing_done: number;
  hps: number;
  overhealing: number;
  damage_taken: number;
  damage_blocked: number;
  damage_mitigated: number;
  buff_uptime: BuffUptime[];
  debuff_uptime: BuffUptime[];
  interrupts: number;
  synergies_used: number;
  synergies_provided: number;
  deaths: number;
  time_dead: number;
  magicka_spent: number;
  stamina_spent: number;
  ultimate_spent: number;
  potion_uses: number;
}

export interface BuffUptime {
  name: string;
  uptime: number;
}

export interface ContributionScores {
  damage_dealt: number;
  damage_taken: number;
  healing_done: number;
  buff_uptime: number;
  debuff_uptime: number;
  mechanic_execution: number;
  resource_efficiency: number;
}

// Run List Item (simplified)
export interface CombatRunListItem {
  run_id: string;
  character_name: string;
  content_name: string;
  content_type: ContentType;
  difficulty: Difficulty;
  timestamp: string;
  duration_sec: number;
  success: boolean;
  dps: number;
}

// Run Statistics
export interface RunStatistics {
  total_runs: number;
  successful_runs: number;
  average_dps: number;
  best_dps: number;
  total_play_time_sec: number;
  favorite_content: string | null;
  favorite_character: string | null;
}

// Recommendation
export interface Recommendation {
  recommendation_id: string;
  run_id: string;
  category: RecommendationCategory;
  priority: number;
  current_state: string;
  recommended_change: string;
  expected_improvement: string;
  reasoning: string;
  confidence: number;
}

export interface RecommendationsResponse {
  run_id: string;
  recommendations: Recommendation[];
  percentiles?: Record<string, number>;
  sample_size: number;
  confidence: 'low' | 'medium' | 'high';
}

// Gear Set
export interface GearSet {
  set_id: string;
  name: string;
  set_type: SetType;
  weight: string;
  location: string;
  dlc_required?: string;
  pve_tier?: PVETier;
  bonuses: Record<string, SetBonusEffect>;
  role_affinity?: RoleAffinity;
  tags?: string;
}

export interface SetBonusEffect {
  stat?: string;
  value?: number;
  effect?: string;
  uptime?: string;
  proc_condition?: string;
  buff_granted?: string;
  duration_sec?: number;
  cooldown_sec?: number;
}

export interface RoleAffinity {
  damage_dealt: number;
  buff_uptime: number;
  healing_done: number;
  damage_taken: number;
}

// Character
export interface Character {
  id: string;
  name: string;
  class: ESOClass;
  subclass?: ESOClass;
  race: string;
  cp_level: number;
  total_runs: number;
  average_dps: number;
  best_dps: number;
  last_played: string;
  favorite_content: string;
  current_sets: string[];
}

// Percentile Data Point
export interface PercentileDataPoint {
  date: string;
  percentile: number;
  dps: number;
}

// DPS Trend Data Point
export interface DPSTrendPoint {
  date: string;
  dps: number;
  content: string;
}

// Buff Analysis
export interface BuffAnalysis {
  name: string;
  average_uptime: number;
  target_uptime: number;
  importance: 'critical' | 'high' | 'medium' | 'low';
}
