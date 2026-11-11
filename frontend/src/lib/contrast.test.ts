/**
 * WCAG contrast check of the design tokens in index.css for both themes:
 * text >= 4.5:1, chart marks/graphics >= 3:1 against background and card surfaces.
 */
/// <reference types="node" />
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

// Read the stylesheet from disk (Vitest doesn't process CSS in unit tests; cwd = frontend/).
const css = readFileSync(resolve(process.cwd(), 'src/index.css'), 'utf8')

function block(selector: string): Record<string, string> {
  const start = css.indexOf(`${selector} {`)
  const body = css.slice(start, css.indexOf('}', start))
  const out: Record<string, string> = {}
  for (const m of body.matchAll(/--([\w-]+):\s*(#[0-9a-fA-F]{6})/g)) out[m[1]!] = m[2]!
  return out
}

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((c) =>
    c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
  return 0.2126 * r! + 0.7152 * g! + 0.0722 * b!
}

export function contrast(a: string, b: string): number {
  const [l1, l2] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (l1! + 0.05) / (l2! + 0.05)
}

const TEXT = ['foreground', 'muted-foreground', 'destructive', 'success', 'primary']
const GRAPHICS = ['chart-income', 'chart-expense', 'chart-savings', 'chart-rate', 'chart-1', 'chart-2',
  'chart-3', 'chart-4', 'chart-5', 'chart-6', 'chart-other', 'chart-axis']

describe.each([':root', '.dark'])('%s tokens', (selector) => {
  const t = block(selector)
  const surfaces = ['background', 'card']

  test.each(TEXT)('text token %s meets 4.5:1', (name) => {
    for (const s of surfaces) expect(contrast(t[name]!, t[s]!)).toBeGreaterThanOrEqual(4.5)
  })

  test.each(GRAPHICS)('chart token %s meets 3:1', (name) => {
    for (const s of surfaces) expect(contrast(t[name]!, t[s]!)).toBeGreaterThanOrEqual(3)
  })

  test('primary button text is readable', () => {
    expect(contrast(t['primary']!, t['primary-foreground']!)).toBeGreaterThanOrEqual(4.5)
  })
})
