import { X } from 'lucide-react'
import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'

/** One-of-many picker (keyboard accessible): tone, depth, length, frequency… */
export function Choice<T extends string | number>({ label, value, options, onChange }: {
  label: string
  value: T
  options: { value: T; label: string }[]
  onChange: (value: T) => void
}) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <ToggleGroup
        type="single"
        variant="outline"
        value={String(value)}
        onValueChange={(v) => v && onChange(options.find((o) => String(o.value) === v)!.value)}
        className="flex-wrap justify-start"
        aria-label={label}
      >
        {options.map((o) => (
          <ToggleGroupItem key={String(o.value)} value={String(o.value)} className="px-4 data-[state=on]:border-primary data-[state=on]:text-primary">
            {o.label}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
    </div>
  )
}

/** Free-text list: type, Enter to add, ✕ to remove (topics to avoid, trusted outlets). */
export function TagInput({ label, placeholder, values, onChange }: {
  label: string
  placeholder: string
  values: string[]
  onChange: (values: string[]) => void
}) {
  const [text, setText] = useState('')
  const add = () => {
    const clean = text.trim()
    if (clean && !values.some((v) => v.toLowerCase() === clean.toLowerCase())) onChange([...values, clean])
    setText('')
  }
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <Input value={text} placeholder={placeholder} onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), add())} onBlur={add} />
      {values.length > 0 && (
        <ul className="flex flex-wrap gap-2">
          {values.map((v) => (
            <li key={v} className="flex items-center gap-1 rounded-full border px-3 py-1 text-sm">
              {v}
              <button type="button" aria-label={`✕ ${v}`} onClick={() => onChange(values.filter((x) => x !== v))}
                className="rounded-full p-0.5 text-muted-foreground hover:text-foreground">
                <X className="size-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
