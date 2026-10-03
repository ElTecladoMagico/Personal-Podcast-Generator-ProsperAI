/** Wordmark with the ON AIR pilot light (the one warm accent of the design). */
export function Logo() {
  return (
    <span className="flex items-center gap-2 font-heading text-xl whitespace-nowrap">
      <span className="relative flex size-2.5" aria-hidden>
        <span className="absolute inline-flex size-full rounded-full bg-primary opacity-60 motion-safe:animate-ping" />
        <span className="relative inline-flex size-2.5 rounded-full bg-primary" />
      </span>
      Personal Podcast
    </span>
  )
}
