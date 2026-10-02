const COLORS = ['var(--chart-1)', 'var(--chart-3)']

/** Each host keeps one colour across avatars and transcript. */
export const hostColor = (speaker: number) => COLORS[speaker % COLORS.length]
