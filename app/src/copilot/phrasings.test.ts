// The rule parser (the copilot's fallback when the LLM is off) scored on the same eval set as the LLM:
// server/tests/phrasings.json. Prints its accuracy and holds a floor so the fallback cannot quietly get worse.

import { readFileSync } from 'node:fs'
import { expect, test } from 'vitest'
import { parseRules, resolve, type UnderstandContext } from './understand'
import type { Intent } from './whatIf'

interface Case {
  text: string
  intent: Intent
  minutes?: number | null
  targets?: (string | null)[]
  clarify?: boolean
  style: string
}

const data = JSON.parse(readFileSync(new URL('../../../server/tests/phrasings.json', import.meta.url), 'utf-8')) as { context: UnderstandContext; cases: Case[] }

test('rule parser on the eval set', () => {
  const rows = data.cases.map((c) => {
    const rules = parseRules(c.text, data.context)
    const r = resolve(c.text, rules, data.context, rules)
    const intentOk = r.intent === c.intent
    const minutesOk = c.intent === 'extend_stay' ? r.minutes === (c.minutes ?? null) : true
    const placeOk = c.clarify ? r.kind === 'clarify' : c.targets ? r.kind === 'ask' && c.targets.includes(r.targetId) : true
    return { c, r, ok: intentOk && minutesOk && placeOk, intentOk }
  })
  const ok = rows.filter((x) => x.ok).length
  const intents = rows.filter((x) => x.intentOk).length
  const misses = rows.filter((x) => !x.ok).map((x) => `  [${x.c.style}] "${x.c.text}" → ${JSON.stringify(x.r)}`)
  console.log(`rules: fully correct ${ok}/${rows.length}, intent ${intents}/${rows.length}\n${misses.join('\n')}`)
  // Floors from the first measurement (see the PR); raise them when the rules improve.
  expect(intents / rows.length).toBeGreaterThanOrEqual(0.9)
  expect(ok / rows.length).toBeGreaterThanOrEqual(0.85)
  // The ambiguous ridge always gets a clarifying question from the rules.
  for (const x of rows.filter((y) => y.c.clarify)) expect(x.r.kind).toBe('clarify')
})
