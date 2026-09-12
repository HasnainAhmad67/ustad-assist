You are a senior product design engineer and frontend architect with 15+
years of experience building premium, enterprise-grade B2B/industrial
software UIs (visual/interaction quality comparable to Linear, Stripe
Dashboard, Vercel, and Palantir Foundry).

I could only attach ONE file to this conversation, so I attached my
complete backend source code (a FastAPI project, currently a ZIP/pasted
codebase). Everything else — product requirements and the frozen frontend
architecture — is written directly below in this prompt. Treat this prompt
text as equally authoritative as the attached file. Read the attached
backend code FULLY before writing anything, especially:
- app/schemas.py — this is the exact API request/response contract
- app/routes/*.py — the 3 endpoints: GET /api/catalog,
  POST /api/vision/extract, POST /api/troubleshoot
- app/main.py — CORS is already configured to allow http://localhost:5173

================================================================
PRODUCT CONTEXT (condensed PRD)
================================================================

Product: Ustad Assist — an AI-powered technical troubleshooting copilot
for technicians working on Solar Inverters and UPS systems.

Core principle: "Assist, Don't Guess." Never invent technical information.
Every answer must be grounded, cited, and safety-checked before display.

Two input paths that converge into one result flow:
1. P0 (primary): technician selects equipment category → manufacturer →
   exact model → enters an error/alarm code → submits.
2. P1 (secondary): technician uploads a photo of the equipment's
   nameplate/display → backend Vision/OCR returns detection candidates →
   technician MUST explicitly confirm or edit (never auto-trusted) →
   confirmed data is submitted through the exact same flow as P0.

Required UI states (every one needs a real, designed treatment — not a
placeholder):
- Landing / equipment category selection
- Input form (manufacturer → model → error code, populated from
  GET /api/catalog, never hardcoded)
- Image upload (drag-drop + file picker)
- Image unclear (blurry/dark/glare — offer "upload clearer image" or
  "enter manually")
- Detection confirmation (show detected equipment/manufacturer/model/code
  with Confirm/Edit — if multiple candidates detected, list them, do NOT
  silently pick one)
- Analysis/loading state (must show meaningful progress, not a frozen
  spinner)
- Result screen — must show, in this order: Equipment → Detected issue →
  What it means → Possible causes → Recommended checks (safe checks vs.
  technician-only checks CLEARLY labeled separately) → Safety warning →
  Source citation (manual title, version, section, page, official link)
  → Next action / escalation guidance
- Unsupported equipment state (equipment_not_supported)
- Issue not verified state (issue_not_verified)
- API/generic error state (visually calm, distinct from the safety
  escalation state — an API hiccup should never look like "the
  equipment is on fire")
- Safety escalation state — must be immediately, visually distinguishable
  from every other card on the page. This is a hard requirement, not a
  style preference.

The result screen's `status` field from the API response drives which of
these states renders — the frontend must branch on that typed field only,
never re-derive trust/safety logic client-side, never string-match
response text.

================================================================
DESIGN DIRECTION — MOST IMPORTANT PART OF THIS BRIEF
================================================================

I want this to look like it was designed by a world-class product design
team at an international enterprise software company, then handed to
engineering as a pixel-perfect Figma file. Concretely:

- Visual language: restrained, low-saturation, industrial-professional —
  engineering/blueprint aesthetic. NOT a generic SaaS gradient/purple
  AI-startup look. No glassmorphism, no neon, no decorative gradients, no
  "AI sparkle" motion.
- Typography: one clean sans-serif for UI text (Inter or IBM Plex Sans) +
  a monospace/tabular variant specifically for error codes, model
  numbers, and page references (technicians scan these fast — they must
  read exactly right).
- Spacing: strict 4/8px grid, applied with rigid, obsessive consistency —
  this is what makes it read as "professional," more than color choice.
- Cards & surfaces: subtle 1px borders, flat elevation — NOT drop shadows
  (shadows read as "consumer app").
- Color: 1-2 neutral bases (off-white/near-black, not pure white/black),
  one deep desaturated primary, and exactly 3 reserved semantic colors:
  verified/success, caution/technician-only, escalation/danger. Status
  must never rely on color alone — always pair with icon + text label.
- Icons: one consistent outline icon set (Lucide or Phosphor), used
  sparingly, only where meaningful.
- Motion: minimal, purely functional (transitions, loading feedback) —
  nothing decorative.
- Source Citation card must look like a real reference/spec-sheet block
  (bordered, labeled "Source"), not a small gray footer line.
- Every screen must communicate, in this order: Trust → Evidence → Action.

================================================================
FROZEN FRONTEND ARCHITECTURE — DO NOT DEVIATE WITHOUT FLAGGING IT
================================================================

Stack: React + Vite + TypeScript. Plain CSS using design tokens (CSS
custom properties in tokens.css). Do NOT introduce Tailwind, styled-
components, or a UI kit (MUI/Chakra/AntD) unless you explain why you
believe it's necessary and I approve it first.

frontend/
  src/
    screens/
      Landing.tsx
      InputForm.tsx
      ImageUpload.tsx
      Confirmation.tsx
      Result.tsx
      Unsupported.tsx
      ErrorState.tsx
    components/
      ResultCard/
      SourceCitationCard/
      SafetyCard/
      ModelSelector/
      LoadingState/
      AppShell/
    services/
      api.ts              <- ONLY file allowed to call the backend
    hooks/
      useTroubleshootFlow.ts   <- state machine:
        idle → identifying → confirming → retrieving →
        result | unsupported | error
    styles/
      tokens.css
      global.css
    types/
      api.ts               <- mirrors backend app/schemas.py exactly
    App.tsx
    main.tsx
  index.html
  vite.config.ts
  package.json

Component rules:
- screens/* never call fetch directly — always through services/api.ts.
- components/* are presentational only — no fetching, no flow state,
  data comes via props only.
- SafetyCard and SourceCitationCard must be reusable — importable from
  Result AND from Confirmation/Unsupported wherever a partial safety
  note is needed (e.g. a "technician-only" badge before a full result
  exists).

================================================================
HARD CONSTRAINTS — DO NOT VIOLATE
================================================================

1. I am on a limited free-trial credit budget. DO NOT run builds, DO NOT
   start dev servers, DO NOT run npm install, DO NOT execute or deploy
   anything, DO NOT test-run code in a sandbox. ONLY write and output
   code as text. I will copy it into my own VS Code and run it myself.
2. DO NOT modify, rewrite, or suggest changes to the attached backend
   code. Treat it as a frozen, working dependency — only consume its API
   contract exactly as defined in its schemas.py.
3. DO NOT invent new API endpoints, new response fields, or new backend
   behavior. If something you need isn't present in the attached
   schemas.py, STOP and tell me explicitly instead of guessing/inventing
   it.
4. DO NOT deviate from the folder structure above unless you have a
   genuine technical reason — if so, STOP and explain the reason before
   proceeding, don't silently restructure.
5. Every UI state listed above needs a real, designed treatment — not a
   TODO or placeholder.

================================================================
PROCESS — WORK STEP BY STEP, WAIT FOR MY "continue" BETWEEN STEPS
================================================================

Do not generate all the code in one dump. Work in this exact order. After
each step, STOP and output only what that step asks for. I will reply
"continue" before you move to the next step.

STEP 1 — Confirm understanding (NO CODE)
Summarize back to me: the 3 API endpoints and their exact request/response
shapes (pulled directly from the attached schemas.py), the full screen
list, and the state machine transitions. This proves you've read the
attached file before writing any code.

STEP 2 — Design tokens + folder scaffold
Output the complete frontend/ folder tree, then the full code for
src/styles/tokens.css and src/styles/global.css only. Explain your
specific color/type/spacing choices in 3-4 sentences, tied to the design
direction above.

STEP 3 — API layer
Output complete code for src/types/api.ts (mirroring the attached
schemas.py field-for-field) and src/services/api.ts (typed fetch wrappers
for the 3 endpoints only).

STEP 4 — State machine
Output complete code for src/hooks/useTroubleshootFlow.ts implementing the
state machine above.

STEP 5 — Shared components
Output complete code for AppShell, ResultCard, SourceCitationCard,
SafetyCard, ModelSelector, LoadingState — one at a time, each as its own
complete file(s) (component + scoped CSS if needed).

STEP 6 — Screens (P0 first)
Output Landing.tsx, InputForm.tsx, loading-state handling, Result.tsx,
Unsupported.tsx, ErrorState.tsx — complete, working files consuming the
components/hooks from Steps 3-5.

STEP 7 — Screens (P1)
Output ImageUpload.tsx and Confirmation.tsx, wired to converge into the
same flow as Step 6.

STEP 8 — Wiring
Output App.tsx, main.tsx, vite.config.ts, package.json, and index.html.

================================================================
OUTPUT FORMAT RULES
================================================================

- Every file: full path as a heading, then the complete file content in
  one code block. No partial snippets, no "// ... rest stays the same."
- Minimal prose between files — a 1-2 line note per file is enough.
- Do not restate this prompt or the PRD back to me except in Step 1.
- If anything here conflicts with the attached schemas.py, flag it
  explicitly and ask which is the source of truth — do not silently pick
  one.

Begin with STEP 1 now.
