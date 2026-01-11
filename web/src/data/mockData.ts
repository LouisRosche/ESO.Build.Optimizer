import type {
  CombatRunListItem,
  RunStatistics,
  Recommendation,
  Character,
  GearSet,
  DPSTrendPoint,
  PercentileDataPoint,
  BuffAnalysis,
  CombatRun,
} from '../types';

// Helper to generate dates
const daysAgo = (days: number): string => {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return date.toISOString();
};

// Mock Combat Runs
export const mockRuns: CombatRunListItem[] = [
  {
    run_id: 'run-001',
    character_name: 'Drakonis the Fierce',
    content_name: 'Veteran Lair of Maarselok',
    content_type: 'dungeon',
    difficulty: 'veteran',
    timestamp: daysAgo(0),
    duration_sec: 1847,
    success: true,
    dps: 78450,
  },
  {
    run_id: 'run-002',
    character_name: 'Drakonis the Fierce',
    content_name: 'Veteran Rockgrove',
    content_type: 'trial',
    difficulty: 'veteran',
    timestamp: daysAgo(1),
    duration_sec: 2835,
    success: true,
    dps: 82100,
  },
  {
    run_id: 'run-003',
    character_name: 'Shadowbane',
    content_name: 'Veteran Maelstrom Arena',
    content_type: 'arena',
    difficulty: 'veteran',
    timestamp: daysAgo(2),
    duration_sec: 1523,
    success: true,
    dps: 65200,
  },
  {
    run_id: 'run-004',
    character_name: 'Drakonis the Fierce',
    content_name: 'Veteran Lair of Maarselok',
    content_type: 'dungeon',
    difficulty: 'veteran',
    timestamp: daysAgo(3),
    duration_sec: 2102,
    success: false,
    dps: 71300,
  },
  {
    run_id: 'run-005',
    character_name: 'Frost Warden',
    content_name: 'Veteran Sunspire',
    content_type: 'trial',
    difficulty: 'hardmode',
    timestamp: daysAgo(4),
    duration_sec: 3456,
    success: true,
    dps: 89500,
  },
  {
    run_id: 'run-006',
    character_name: 'Shadowbane',
    content_name: 'Veteran Blackwood Prowl',
    content_type: 'dungeon',
    difficulty: 'veteran',
    timestamp: daysAgo(5),
    duration_sec: 1234,
    success: true,
    dps: 72100,
  },
  {
    run_id: 'run-007',
    character_name: 'Drakonis the Fierce',
    content_name: 'Veteran Dreadsail Reef',
    content_type: 'trial',
    difficulty: 'veteran',
    timestamp: daysAgo(6),
    duration_sec: 3890,
    success: true,
    dps: 85600,
  },
  {
    run_id: 'run-008',
    character_name: 'Arcane Scholar',
    content_name: 'Veteran Vateshran Hollows',
    content_type: 'arena',
    difficulty: 'veteran',
    timestamp: daysAgo(7),
    duration_sec: 1678,
    success: true,
    dps: 61400,
  },
];

// Mock Run Statistics
export const mockStatistics: RunStatistics = {
  total_runs: 156,
  successful_runs: 142,
  average_dps: 74850,
  best_dps: 98200,
  total_play_time_sec: 234567,
  favorite_content: 'Veteran Rockgrove',
  favorite_character: 'Drakonis the Fierce',
};

// Mock Recommendations
export const mockRecommendations: Recommendation[] = [
  {
    recommendation_id: 'rec-001',
    run_id: 'run-001',
    category: 'gear',
    priority: 1,
    current_state: 'Using Spriggan\'s Thorns (5pc)',
    recommended_change: 'Switch to Pillar of Nirn (5pc)',
    expected_improvement: '+8% DPS based on similar players',
    reasoning: 'Your penetration is already capped from group debuffs. Pillar of Nirn provides additional proc damage that scales better at your current gear level.',
    confidence: 0.85,
  },
  {
    recommendation_id: 'rec-002',
    run_id: 'run-001',
    category: 'execution',
    priority: 2,
    current_state: 'Major Brutality uptime: 72%',
    recommended_change: 'Improve buff uptime to 90%+',
    expected_improvement: '+5% DPS from consistent buffs',
    reasoning: 'Your Major Brutality uptime is below the 85th percentile. Focus on reapplying Rally or Momentum before it expires.',
    confidence: 0.78,
  },
  {
    recommendation_id: 'rec-003',
    run_id: 'run-001',
    category: 'skill',
    priority: 3,
    current_state: 'Using Flames of Oblivion',
    recommended_change: 'Consider Barbed Trap for Minor Force',
    expected_improvement: '+3% crit damage uptime',
    reasoning: 'Top performers in this content use Barbed Trap for reliable Minor Force uptime. Your current crit damage buff has gaps.',
    confidence: 0.72,
  },
  {
    recommendation_id: 'rec-004',
    run_id: 'run-002',
    category: 'build',
    priority: 1,
    current_state: 'No subclass abilities slotted',
    recommended_change: 'Add Bull Netch from Warden subclass',
    expected_improvement: '+4% sustained DPS from better resource management',
    reasoning: 'Your stamina drops below 30% frequently during extended fights. Bull Netch provides excellent sustain with minimal bar space.',
    confidence: 0.81,
  },
];

// Mock Characters
export const mockCharacters: Character[] = [
  {
    id: 'char-001',
    name: 'Drakonis the Fierce',
    class: 'Dragonknight',
    subclass: 'Warden',
    race: 'Dark Elf',
    cp_level: 2100,
    total_runs: 87,
    average_dps: 79200,
    best_dps: 98200,
    last_played: daysAgo(0),
    favorite_content: 'Veteran Rockgrove',
    current_sets: ['Bahsei\'s Mania', 'Kinras\'s Wrath', 'Kjalnar\'s Nightmare'],
  },
  {
    id: 'char-002',
    name: 'Shadowbane',
    class: 'Nightblade',
    race: 'Khajiit',
    cp_level: 2100,
    total_runs: 42,
    average_dps: 68500,
    best_dps: 82100,
    last_played: daysAgo(2),
    favorite_content: 'Veteran Maelstrom Arena',
    current_sets: ['Pillar of Nirn', 'Arms of Relequen', 'Selene'],
  },
  {
    id: 'char-003',
    name: 'Frost Warden',
    class: 'Warden',
    subclass: 'Templar',
    race: 'Nord',
    cp_level: 2100,
    total_runs: 23,
    average_dps: 85600,
    best_dps: 89500,
    last_played: daysAgo(4),
    favorite_content: 'Veteran Sunspire',
    current_sets: ['Bahsei\'s Mania', 'Aegis Caller', 'Maw of the Infernal'],
  },
  {
    id: 'char-004',
    name: 'Arcane Scholar',
    class: 'Arcanist',
    race: 'High Elf',
    cp_level: 1850,
    total_runs: 14,
    average_dps: 58900,
    best_dps: 67200,
    last_played: daysAgo(7),
    favorite_content: 'Veteran Vateshran Hollows',
    current_sets: ['Mother\'s Sorrow', 'Medusa', 'Slimecraw'],
  },
];

// Mock Gear Sets (for comparison)
export const mockGearSets: GearSet[] = [
  {
    set_id: 'set-kinras',
    name: 'Kinras\'s Wrath',
    set_type: 'Dungeon',
    weight: 'Light',
    location: 'Black Drake Villa',
    dlc_required: 'Flames of Ambition',
    pve_tier: 'S',
    bonuses: {
      '2': { stat: 'Weapon and Spell Damage', value: 129 },
      '3': { stat: 'Minor Force', uptime: 'always' },
      '4': { stat: 'Weapon and Spell Damage', value: 129 },
      '5': { effect: 'Major Berserk for 5s at 5 stacks', buff_granted: 'Major Berserk', duration_sec: 5 },
    },
    role_affinity: { damage_dealt: 0.95, buff_uptime: 0.7, healing_done: 0, damage_taken: 0 },
    tags: 'damage,berserk,stacking',
  },
  {
    set_id: 'set-bahsei',
    name: 'Bahsei\'s Mania',
    set_type: 'Trial',
    weight: 'Light',
    location: 'Rockgrove',
    dlc_required: 'Blackwood',
    pve_tier: 'S',
    bonuses: {
      '2': { stat: 'Magicka Recovery', value: 129 },
      '3': { stat: 'Max Magicka', value: 1096 },
      '4': { stat: 'Max Magicka', value: 1096 },
      '5': { effect: 'Up to 15% damage based on missing magicka' },
    },
    role_affinity: { damage_dealt: 0.98, buff_uptime: 0.3, healing_done: 0.1, damage_taken: 0 },
    tags: 'damage,sustain,magicka',
  },
  {
    set_id: 'set-pillar',
    name: 'Pillar of Nirn',
    set_type: 'Dungeon',
    weight: 'Medium',
    location: 'Falkreath Hold',
    dlc_required: 'Horns of the Reach',
    pve_tier: 'A',
    bonuses: {
      '2': { stat: 'Max Stamina', value: 1096 },
      '3': { stat: 'Weapon Damage', value: 129 },
      '4': { stat: 'Weapon Damage', value: 129 },
      '5': { effect: 'Proc deals bleed damage', proc_condition: 'direct_damage' },
    },
    role_affinity: { damage_dealt: 0.88, buff_uptime: 0.2, healing_done: 0, damage_taken: 0 },
    tags: 'damage,proc,bleed',
  },
  {
    set_id: 'set-relequen',
    name: 'Arms of Relequen',
    set_type: 'Trial',
    weight: 'Medium',
    location: 'Cloudrest',
    dlc_required: 'Summerset',
    pve_tier: 'S',
    bonuses: {
      '2': { stat: 'Weapon Damage', value: 129 },
      '3': { stat: 'Weapon Critical', value: 657 },
      '4': { stat: 'Weapon Critical', value: 657 },
      '5': { effect: 'Stacking physical damage DoT' },
    },
    role_affinity: { damage_dealt: 0.95, buff_uptime: 0.1, healing_done: 0, damage_taken: 0 },
    tags: 'damage,physical,stacking,dot',
  },
];

// Mock DPS Trend Data
export const mockDPSTrend: DPSTrendPoint[] = [
  { date: daysAgo(30), dps: 65000, content: 'Veteran Dungeons' },
  { date: daysAgo(27), dps: 68200, content: 'Veteran Trials' },
  { date: daysAgo(24), dps: 67800, content: 'Veteran Dungeons' },
  { date: daysAgo(21), dps: 71500, content: 'Veteran Trials' },
  { date: daysAgo(18), dps: 73200, content: 'Veteran Dungeons' },
  { date: daysAgo(15), dps: 72100, content: 'Arenas' },
  { date: daysAgo(12), dps: 76800, content: 'Veteran Trials' },
  { date: daysAgo(9), dps: 78450, content: 'Veteran Dungeons' },
  { date: daysAgo(6), dps: 82100, content: 'Veteran Trials' },
  { date: daysAgo(3), dps: 79500, content: 'Veteran Dungeons' },
  { date: daysAgo(0), dps: 85600, content: 'Veteran Trials' },
];

// Mock Percentile Trend Data
export const mockPercentileTrend: PercentileDataPoint[] = [
  { date: daysAgo(30), percentile: 52, dps: 65000 },
  { date: daysAgo(27), percentile: 58, dps: 68200 },
  { date: daysAgo(24), percentile: 55, dps: 67800 },
  { date: daysAgo(21), percentile: 63, dps: 71500 },
  { date: daysAgo(18), percentile: 67, dps: 73200 },
  { date: daysAgo(15), percentile: 64, dps: 72100 },
  { date: daysAgo(12), percentile: 72, dps: 76800 },
  { date: daysAgo(9), percentile: 76, dps: 78450 },
  { date: daysAgo(6), percentile: 81, dps: 82100 },
  { date: daysAgo(3), percentile: 78, dps: 79500 },
  { date: daysAgo(0), percentile: 85, dps: 85600 },
];

// Mock Buff Analysis
export const mockBuffAnalysis: BuffAnalysis[] = [
  { name: 'Major Brutality', average_uptime: 0.72, target_uptime: 0.95, importance: 'critical' },
  { name: 'Major Savagery', average_uptime: 0.88, target_uptime: 0.95, importance: 'critical' },
  { name: 'Minor Force', average_uptime: 0.65, target_uptime: 0.90, importance: 'high' },
  { name: 'Major Berserk', average_uptime: 0.45, target_uptime: 0.70, importance: 'high' },
  { name: 'Minor Berserk', average_uptime: 0.82, target_uptime: 0.90, importance: 'medium' },
  { name: 'Major Resolve', average_uptime: 0.91, target_uptime: 0.95, importance: 'medium' },
];

// Mock Full Combat Run (for detailed view)
export const mockDetailedRun: CombatRun = {
  run_id: 'run-001',
  player_id: 'user-001',
  character_name: 'Drakonis the Fierce',
  timestamp: daysAgo(0),
  content: {
    type: 'dungeon',
    name: 'Veteran Lair of Maarselok',
    difficulty: 'veteran',
  },
  duration_sec: 1847,
  success: true,
  group_size: 4,
  build_snapshot: {
    class: 'Dragonknight',
    subclass: 'Warden',
    race: 'Dark Elf',
    cp_level: 2100,
    sets: ['Bahsei\'s Mania', 'Kinras\'s Wrath', 'Kjalnar\'s Nightmare'],
    skills_front: ['Molten Whip', 'Flames of Oblivion', 'Burning Embers', 'Venomous Claw', 'Bull Netch', 'Standard of Might'],
    skills_back: ['Unstable Wall of Fire', 'Cauterize', 'Barbed Trap', 'Engulfing Flames', 'Netch', 'Flawless Dawnbreaker'],
  },
  metrics: {
    damage_done: 144882150,
    dps: 78450,
    crit_rate: 0.62,
    dot_uptime: [
      { name: 'Burning Embers', uptime: 0.89 },
      { name: 'Venomous Claw', uptime: 0.85 },
      { name: 'Unstable Wall', uptime: 0.91 },
    ],
    healing_done: 2456000,
    hps: 1330,
    overhealing: 890000,
    damage_taken: 8500000,
    damage_blocked: 1200000,
    damage_mitigated: 3400000,
    buff_uptime: [
      { name: 'Major Brutality', uptime: 0.72 },
      { name: 'Major Savagery', uptime: 0.88 },
      { name: 'Minor Force', uptime: 0.65 },
      { name: 'Major Berserk', uptime: 0.45 },
    ],
    debuff_uptime: [
      { name: 'Minor Breach', uptime: 0.92 },
      { name: 'Burning', uptime: 0.87 },
    ],
    interrupts: 8,
    synergies_used: 12,
    synergies_provided: 15,
    deaths: 0,
    time_dead: 0,
    magicka_spent: 456000,
    stamina_spent: 234000,
    ultimate_spent: 2400,
    potion_uses: 6,
  },
  contribution_scores: {
    damage_dealt: 0.78,
    damage_taken: 0.15,
    healing_done: 0.08,
    buff_uptime: 0.72,
    debuff_uptime: 0.85,
    mechanic_execution: 0.92,
    resource_efficiency: 0.68,
  },
};

// Mock content-type to color mapping
export const contentTypeColors: Record<string, string> = {
  dungeon: '#3b82f6',  // blue
  trial: '#a855f7',    // purple
  arena: '#22c55e',    // green
  overworld: '#f59e0b', // amber
  pvp: '#ef4444',      // red
};

// Helper function to format duration
export function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}

// Helper function to format DPS
export function formatDPS(dps: number): string {
  if (dps >= 1000000) {
    return `${(dps / 1000000).toFixed(2)}M`;
  }
  if (dps >= 1000) {
    return `${(dps / 1000).toFixed(1)}K`;
  }
  return dps.toString();
}

// Helper function to format date
export function formatDate(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// Helper function to get relative time
export function getRelativeTime(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffDays > 0) return `${diffDays}d ago`;
  if (diffHours > 0) return `${diffHours}h ago`;
  if (diffMins > 0) return `${diffMins}m ago`;
  return 'Just now';
}
