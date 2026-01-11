/**
 * Shared ESO class color definitions
 * Used consistently across CharacterCard and Characters pages
 */

export const classColors: Record<string, string> = {
  Dragonknight: 'text-orange-400',
  Nightblade: 'text-purple-400',
  Sorcerer: 'text-blue-400',
  Templar: 'text-yellow-400',
  Warden: 'text-green-400',
  Necromancer: 'text-emerald-400',
  Arcanist: 'text-cyan-400',
};

/**
 * Get the Tailwind text color class for an ESO class
 * Returns a default gray color if class is not found
 */
export function getClassColor(className: string): string {
  return classColors[className] || 'text-gray-400';
}
