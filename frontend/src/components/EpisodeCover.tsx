import { coverSeed } from '@/lib/episodes'
import { cn } from '@/lib/utils'

// Hues of the design palette (docs/design.md): on air, amber, teal, blue, mauve.
const HUES = [35, 75, 195, 255, 320]

/** A cover that is unique per episode and costs nothing: gradients picked from its id. */
export function EpisodeCover({ id, topics, className }: { id: string; topics: string[]; className?: string }) {
  const seed = coverSeed(id)
  const pick = (n: number) => HUES[(seed >>> (n * 3)) % HUES.length]
  const at = (n: number) => 15 + ((seed >>> (n * 5)) % 70)
  const background = [
    `radial-gradient(circle at ${at(1)}% ${at(2)}%, oklch(0.72 0.17 ${pick(1)}) 0%, transparent 55%)`,
    `radial-gradient(circle at ${at(3)}% ${at(4)}%, oklch(0.62 0.15 ${pick(2)}) 0%, transparent 60%)`,
    `radial-gradient(circle at ${at(5)}% ${at(6)}%, oklch(0.55 0.12 ${pick(3)}) 0%, transparent 65%)`,
    'oklch(0.2 0.02 255)',
  ].join(', ')
  const initials = topics
    .slice(0, 2)
    .map((t) => t.trim()[0]?.toUpperCase())
    .join('')

  return (
    <div className={cn('relative aspect-square overflow-hidden rounded-xl [container-type:inline-size]', className)} style={{ background }} aria-hidden>
      <svg className="absolute inset-0 size-full opacity-25 mix-blend-overlay">
        <filter id={`grain-${seed}`}>
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed={seed % 1000} />
        </filter>
        <rect width="100%" height="100%" filter={`url(#grain-${seed})`} />
      </svg>
      <span className="absolute bottom-2 left-3 font-heading text-[clamp(1.5rem,22cqw,4rem)] leading-none text-white/90">
        {initials}
      </span>
    </div>
  )
}
