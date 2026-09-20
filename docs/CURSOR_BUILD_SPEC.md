# ChatNovel / Bengali Love-Story AI
## Build Specification for Cursor

**Document purpose:** Give Cursor a single source of truth for building an MVP of a text-only, chat-format storytelling app where readers silently observe fictional adult characters' conversations. The story engine automatically develops scenes, emotion, tension, conflict, climax and chapter arcs. Primary launch language: Bengali. Literary direction: original Bengali romantic fiction with themes of emotional restraint, longing, social pressure, pride, vulnerability and sacrifice associated with classic Bengali literature; do not reproduce or closely imitate any existing text.

---

## 1. Product definition

### Working product
A mobile-first reading experience that looks like a private chat thread between two or more fictional adult characters. The reader does not choose dialogue. They scroll and watch the story unfold as if they discovered a real conversation.

### Core promise
**"Read a love story as if you are secretly reading their chat."**

### Primary experience
1. Reader opens a story.
2. A chat screen shows messages between characters.
3. Messages arrive in short, readable beats.
4. The system inserts scene changes, time stamps, pauses, typing indicators and turning points when appropriate.
5. A hidden story state tracks character emotions, relationship dynamics, conflicts and unresolved plot threads.
6. Chapters end on emotional beats or cliffhangers.
7. The next chapter resumes with continuity.

### Initial audience
- Bengali readers interested in romance and literary storytelling.
- Young adults who already consume chat-fiction, web fiction, reels/short drama, and serialized stories.
- Readers who prefer short daily episodes over long books.

### Content boundary
All romantic characters in the MVP must be clearly adults (18+). Romance can include flirting, attraction, kissing, sensual tension and emotionally intimate situations, but intimate content must remain non-graphic. Do not generate sexual content involving minors or ambiguous ages. Avoid coercive sexual situations. If a story includes sensitive adult topics, keep treatment tasteful and non-graphic.

---

# 2. Product principles

1. **Story before spectacle.** Every new event must be motivated by character goals, established facts or an unresolved thread.
2. **Subtext over exposition.** Characters do not constantly state what they feel.
3. **Slow-burn pacing.** Attraction can develop through repeated interactions instead of instant declarations.
4. **Every scene changes something.** Emotion, information, trust, conflict, stakes or relationship status must move.
5. **Continuity is a hard requirement.** Previous facts cannot be contradicted without an explicit plot reason.
6. **The reader observes.** No branching choices are required for the core product.
7. **Modern UI, literary emotional depth.** The chat surface can feel contemporary while the Bengali writing carries classic emotional restraint.

---

# 3. System architecture

```text
Mobile/Web Client
      |
      v
FastAPI API Gateway
      |
      +-------------------------------+
      |                               |
      v                               v
Story Orchestrator               Auth / Billing
      |
      +------------------------------------------------------+
      |            |             |           |               |
      v            v             v           v               v
Story Bible   Scene Director  Emotion     Conflict      Continuity Memory
Service                      Engine      Engine          Service
      |            |             |           |               |
      +-------------------------+-----------+---------------+
                                |
                                v
                         Dialogue Generator
                                |
                                v
                           Safety Filter
                                |
                                v
                           Critic / Editor
                                |
                                v
                        State Update Service
                                |
                     +----------+----------+
                     |                     |
                     v                     v
               PostgreSQL              Vector Store
               story state             semantic memory
```

### Recommended stack
- **Backend:** Python + FastAPI
- **Database:** PostgreSQL
- **Cache / jobs:** Redis
- **Background jobs:** Celery / RQ / Arq (choose one)
- **Vector search:** pgvector first; dedicated vector DB later if needed
- **Object storage:** S3-compatible storage for covers/assets
- **LLM:** provider abstraction (`LLMProvider`) so model vendor can change without rewriting business logic
- **Auth:** email/OTP + Google/Apple sign-in later
- **Payments:** App Store / Google Play subscriptions for mobile; Stripe/Razorpay only where platform rules allow
- **Observability:** structured logs + OpenTelemetry-compatible tracing + error tracking
- **Frontend:** React Native, Flutter, or web-first React. Backend contract must remain platform agnostic.

---

# 4. Agent / AI responsibilities

Do not make every component an autonomous agent. Use deterministic services plus focused LLM calls. Only three components need agent-like planning behavior: Story Director, Character/Emotion reasoning, and Critic.

## Agent A — Story Bible Builder
**Purpose:** Create the canonical world and character specification before generation begins.

### Inputs
- User/admin story brief
- Genre
- Target chapter count
- Setting
- Character descriptions
- Literary direction

### Outputs
- Character profiles
- Relationships
- Goals/desires
- Fears
- Secrets
- Backstory
- Social context
- Locations
- Timeline anchors
- Story premise

### Hard rule
Story Bible facts are authoritative. Generated dialogue cannot silently overwrite them.

---

## Agent B — Chapter Planner
**Purpose:** Create a high-level narrative arc across chapters.

### Inputs
- Story Bible
- Desired chapter count
- Genre
- Target emotional arc

### Outputs
For each chapter:
- chapter objective
- emotional objective
- conflict
- reveal
- key scene(s)
- escalation target
- cliffhanger / resolution beat

### Example arc
```text
Ch 1: First meaningful encounter
Ch 2: Curiosity
Ch 3: Emotional connection
Ch 4: Social obstacle appears
Ch 5: Growing intimacy
Ch 6: Hidden conflict revealed
Ch 7: Misunderstanding / separation
Ch 8: Reconnection
Ch 9: Major choice
Ch 10: Climax
Ch 11: Consequence
Ch 12: Resolution
```

The planner must allow setbacks; tension should not increase monotonically.

---

## Agent C — Scene Director
**Purpose:** Decide what happens next without writing final dialogue.

### Inputs
- Current chapter plan
- Current story state
- Recent messages
- Open plot threads
- Character goals
- Current tension

### Outputs
```json
{
  "scene_goal": "Maya wants Arjun to understand that her family is pressuring her",
  "next_event": "Maya indirectly reveals a marriage proposal",
  "emotional_shift": {
    "maya_longing": 5,
    "maya_fear": 7,
    "arjun_fear": 9,
    "relationship_tension": 8
  },
  "reveal": true,
  "cliffhanger": true
}
```

### Rules
- Do not introduce random twists for novelty.
- Prefer consequences of established facts.
- Alternate intensity and relief.
- Avoid repeating the same conflict shape.
- Protect the chapter's purpose.

---

## Agent D — Emotion Engine
**Purpose:** Track emotional state as structured data, not vague prose.

### Per-character dimensions
Use a 0-100 scale:
- affection
- trust
- longing
- fear
- jealousy
- pride
- vulnerability
- frustration
- hope
- resentment

### Relationship dimensions
- attraction
- trust
- emotional intimacy
- conflict
- uncertainty
- commitment
- social pressure

### Rules
- Emotion values change only when evidence in the scene supports the change.
- A single message should not cause huge jumps unless it is a major reveal.
- Contradictory emotions are allowed.
- Emotion state is not a diagnosis; it is a fiction-writing control signal.

---

## Agent E — Conflict Engine
**Purpose:** Maintain a portfolio of internal and external obstacles.

### Internal conflicts
- fear of rejection
- pride
- insecurity
- guilt
- inability to communicate
- conflicting duties

### External conflicts
- family expectations
- class/social differences
- distance
- career decisions
- marriage pressure
- timing
- reputation
- misunderstandings caused by incomplete information

Each conflict has:
- severity
- active/inactive state
- involved characters
- evidence
- possible resolutions

---

## Agent F — Subtext Engine
**Purpose:** Generate what each character means beneath what they literally say.

### Output example
```json
{
  "speaker": "Maya",
  "literal_intent": "ask if Arjun is coming tomorrow",
  "hidden_intent": "test whether he will choose to see her",
  "fear": "he may avoid her",
  "desired_response": "reassurance"
}
```

Use this before dialogue generation. It is one of the most important quality layers.

---

## Agent G — Bengali Dialogue Generator
**Purpose:** Write the visible messages only.

### Style requirements
- Natural Bengali.
- Simple but emotionally resonant sentences.
- Controlled romantic expression.
- Strong subtext.
- Dignified conflict.
- Limited slang unless character profile calls for it.
- No generic translated-English Bengali.
- No repetitive "I miss you" / "I love you" loops.
- Dialogue must be original.

### Literary direction
Use broad qualities associated with classic Bengali romantic fiction: emotional restraint, longing, social and family pressures, moral conflict, pride, vulnerability, sacrifice, quiet acts of care, and psychologically believable characters. Do not reproduce or closely mimic identifiable passages or sentences from an existing author.

### Chat formatting
Visible events may include:
- message timestamps
- typing indicator
- read/unread behavior
- deleted-message marker
- pauses
- occasional system-style scene marker

Do not overuse interface gimmicks.

---

## Agent H — Memory / Continuity Agent
**Purpose:** Retrieve relevant facts before each scene and update memory afterward.

### Memory tiers
**Canonical memory:** Story Bible facts, immutable unless an explicit admin edit occurs.

**Event memory:** Important events with timestamps and chapter references.

**Semantic memory:** Embeddings for retrieving similar past events, themes and dialogue context.

**Ephemeral context:** Last N messages and current scene summary.

### Retrieval rules
Before a new scene, retrieve:
- involved character facts
- prior events involving the current conflict
- promises/commitments
- secrets known by each character
- relevant locations/objects
- last scene outcome

After each scene, write a structured summary and update only verified facts.

---

## Agent I — Critic / Editor
**Purpose:** Catch problems before content reaches readers.

### Checks
- continuity
- character voice
- natural Bengali
- pacing
- unnecessary repetition
- emotional logic
- plot consistency
- cliffhanger quality
- safety policy compliance
- age certainty
- excessive explicitness

### Output
```json
{
  "pass": false,
  "issues": [
    "Character referenced an event that did not occur",
    "Tension increased without causal trigger"
  ],
  "repair_instruction": "Rewrite messages 6-9 and keep the reveal implied."
}
```

Regenerate the scene when critical checks fail. Cap regeneration attempts (e.g. 2) to control cost.

---

# 5. Story generation pipeline

## First story creation
```text
Story brief
 -> Story Bible
 -> Chapter Planner
 -> Character voice profiles
 -> initial conflict graph
 -> initial emotional state
 -> save version 1
```

## Each scene / message batch
```text
Load story state
 -> retrieve memory
 -> Emotion analysis
 -> Conflict evaluation
 -> Scene Director selects next beat
 -> Subtext Engine
 -> Bengali Dialogue Generator
 -> Safety Filter
 -> Critic
 -> State Update
 -> Persist
 -> return visible messages
```

### Message batch sizing
Generate **3-10 chat messages per request**, depending on UI. Avoid generating an entire chapter in one call.

### Why batches?
- lowers perceived latency
- allows streaming
- makes story feel alive
- permits state updates between beats
- reduces hallucinated plot jumps

---

# 6. API design (FastAPI)

## Auth
`POST /v1/auth/register`
`POST /v1/auth/login`
`POST /v1/auth/refresh`

## Stories
`GET /v1/stories`
`GET /v1/stories/{story_id}`
`POST /v1/stories`
`GET /v1/stories/{story_id}/chapters`
`GET /v1/stories/{story_id}/chapters/{chapter_id}`

## Reading
`GET /v1/reading/{story_id}/state`
`POST /v1/reading/{story_id}/start`
`POST /v1/reading/{story_id}/ack`
`GET /v1/reading/{story_id}/next`

For streaming, support:
`GET /v1/stories/{story_id}/stream?chapter_id=...`
using Server-Sent Events (SSE) or WebSocket where justified.

### Suggested stream events
```text
event: message
{...}

event: typing
{...}

event: scene_marker
{...}

event: chapter_end
{...}

event: error
{...}
```

## Admin / content
`POST /v1/admin/stories`
`POST /v1/admin/stories/{story_id}/generate-outline`
`POST /v1/admin/stories/{story_id}/generate-chapter`
`POST /v1/admin/stories/{story_id}/regenerate-scene`
`GET /v1/admin/stories/{story_id}/state`

## Payments
`POST /v1/billing/checkout`
`POST /v1/billing/webhook`
`GET /v1/billing/me`

---

# 7. Data model

## users
- id
- email
- auth_provider
- language
- created_at

## stories
- id
- title
- slug
- language
- genre
- blurb
- cover_url
- status
- target_chapters
- age_rating
- created_at

## characters
- id
- story_id
- name
- age
- pronouns
- role
- personality_json
- speech_style_json
- goals_json
- fears_json
- secrets_json

## relationships
- id
- story_id
- character_a_id
- character_b_id
- state_json

## chapters
- id
- story_id
- chapter_number
- title
- outline_json
- status

## scenes
- id
- chapter_id
- sequence_number
- scene_state_json
- summary
- generated_at

## messages
- id
- scene_id
- character_id
- message_index
- body
- sent_at_story_time
- metadata_json

## character_emotions
- id
- scene_id
- character_id
- affection
- trust
- longing
- fear
- jealousy
- pride
- vulnerability
- frustration
- hope
- resentment

## plot_threads
- id
- story_id
- name
- description
- status
- stakes
- involved_characters
- last_touched_scene_id

## memories
- id
- story_id
- type
- content
- source_scene_id
- importance
- embedding

## reader_progress
- user_id
- story_id
- chapter_id
- last_message_id
- completion_percent
- last_read_at

## subscriptions
- user_id
- provider
- product_id
- status
- renewal_at

---

# 8. Prompt contracts

Every LLM call must use JSON schema / structured output where practical.

## Scene Director prompt skeleton
```text
SYSTEM:
You are the story director. Never write final dialogue.
Choose the next causally justified story beat.
Preserve canon and unresolved threads.
Increase or decrease tension only when justified.
Return the required JSON schema.

CONTEXT:
Story Bible: {story_bible}
Chapter plan: {chapter_plan}
Current state: {state}
Recent messages: {recent_messages}
Open threads: {plot_threads}

TASK:
Select the next scene beat.
```

## Dialogue prompt skeleton
```text
SYSTEM:
Write original Bengali dialogue for fictional adult characters.
Use the supplied character voice, emotional state and subtext.
Do not invent new backstory.
Do not resolve a conflict unless instructed by the scene director.
Use restrained romantic tension.
Keep intimate content non-graphic.
Return only chat messages.

INPUT:
Character profiles: {characters}
Scene objective: {scene_goal}
Subtext: {subtext}
Recent chat: {recent_messages}
Language: Bengali
```

## Critic prompt skeleton
```text
SYSTEM:
You are a strict fiction editor.
Evaluate continuity, voice, Bengali naturalness, causal plot logic,
emotional consistency, pacing and safety.
Return pass/fail plus repair instructions in JSON.
```

---

# 9. Chapter and tension controller

Use an explicit arc controller rather than relying only on the LLM.

### Example tension bands
- 0-20: calm / setup
- 21-40: curiosity
- 41-60: emotional involvement
- 61-75: meaningful conflict
- 76-90: high stakes
- 91-100: climax pressure

Do not force a target each scene. Use the band as a pacing guide.

### Tension can change through
- new information
- uncertainty
- proximity
- jealousy
- family pressure
- separation
- broken expectations
- confession
- revelation
- sacrifice

### Relief beats
Add moments of humor, ordinary domestic detail, tenderness or calm after intense scenes. This prevents emotional fatigue.

---

# 10. Example story state

```json
{
  "story_id": "story_001",
  "chapter": 4,
  "scene": 3,
  "time": "2026-09-20T23:42:00+05:30",
  "setting": "Kolkata, late-night chat",
  "characters": {
    "maya": {
      "age": 24,
      "affection": 78,
      "trust": 64,
      "longing": 89,
      "fear": 71,
      "pride": 62
    },
    "arjun": {
      "age": 26,
      "affection": 81,
      "trust": 58,
      "longing": 83,
      "fear": 77,
      "pride": 74
    }
  },
  "relationship": {
    "attraction": 74,
    "trust": 61,
    "conflict": 49,
    "social_pressure": 81
  },
  "open_threads": [
    "Maya's family is discussing a marriage proposal",
    "Arjun thinks Maya may choose her family",
    "Neither has directly confessed"
  ]
}
```

---

# 11. Safety and quality controls

Implement two layers:

### Pre-generation
- Confirm every character participating in romance has age >= 18.
- Reject ambiguous age statements.
- Classify requested intensity.
- Check banned / disallowed sexual content.

### Post-generation
- Safety classifier on generated text.
- If unsafe: do not show it; regenerate using a safe instruction or terminate the scene.
- Log safety decision without storing unnecessary sensitive reader data.

### Privacy
- Minimize reader data.
- Separate story state from account identity.
- Encrypt tokens/secrets.
- Do not use private reader content to train models by default.
- Provide delete-account/data functionality.

---

# 12. Caching and cost control

Do not call an LLM for every UI rendering.

Cache:
- story Bible
- chapter plan
- character profiles
- recent scene summary
- memory retrieval results

Generate scene batches in the background where appropriate.

Suggested cost strategy:
- cheap model: classification, emotion deltas, critic pre-checks
- stronger model: scene planning and final Bengali dialogue
- embeddings: async, only for durable memories

---

# 13. MVP scope

### Build first
1. One Bengali romance story.
2. Two adult main characters.
3. 10 chapters.
4. Text-only chat UI.
5. Story Bible.
6. Chapter Planner.
7. Scene Director.
8. Emotion Engine.
9. Subtext Engine.
10. Bengali Dialogue Generator.
11. Continuity memory.
12. Critic.
13. FastAPI endpoints.
14. PostgreSQL state storage.
15. SSE streaming.
16. Basic analytics.

### Do NOT build initially
- user-generated stories
- public social feed
- voice calls
- image generation
- complex recommendation system
- multiplayer
- branching choice game
- creator marketplace

Validate retention before expanding.

---

# 14. Reader UX

### Home
- Continue Reading
- New stories
- Trending
- Short stories
- Serialized romances

### Story screen
- Character names + avatars
- Chat bubbles
- timestamps only at meaningful intervals
- typing animation
- subtle chapter marker
- auto-scroll option
- pause/resume

### End of chapter
Show:
- chapter title
- small emotional line
- progress
- next chapter CTA
- notification opt-in

Example:
> **Chapter 5 complete**
> "কথাটা সে বলেনি। কিন্তু দুজনেই বুঝেছিল।"

Then:
> **আগামীকাল পরের অধ্যায় পড়বে?**

---

# 15. Analytics

Track:
- story_open
- first_message_read
- 30-second retention
- chapter_start
- chapter_complete
- daily_return
- notification_open
- story_follow
- subscription_view
- trial_start
- subscription_purchase
- churn
- messages_read_per_session
- average chapter completion
- cliffhanger-to-next-chapter conversion

North-star candidates for MVP:
**D7 reader retention + chapter completion rate + paid conversion.**

---

# 16. Monetization hypothesis

### Free
- first 1-2 chapters
- selected stories
- limited daily reading

### Premium
- full stories
- early chapters
- exclusive serialized stories
- unlimited reading
- premium literary collections

### Later
- creator subscriptions
- paid story unlocks
- audio versions
- premium author collections

Pricing should be tested, not assumed. Run experiments on annual vs monthly packaging.

---

# 17. Content strategy

Launch with 10-20 stories, not 1, if content production capacity permits. Each story should have a distinct hook:
- family-pressure romance
- college romance
- second-chance love
- long-distance relationship
- forbidden relationship
- workplace romance
- rainy Kolkata romance
- mystery + romance
- bittersweet literary romance
- modern adaptation-style original story

### Bengali literary positioning
Use emotionally rich, accessible Bengali. Avoid making every story archaic. The literary influence should be thematic and tonal, while vocabulary should remain comfortable for today's reader.

---

# 18. Business model

## Problem
Traditional digital fiction is usually static: read a chapter, leave, return later. Generic AI chat is interactive but often lacks narrative discipline, continuity and literary structure.

## Solution
A serialized chat-fiction platform where AI acts as the story room behind the scenes, maintaining characters, emotion, plot and chapter arcs while the reader experiences the output as a readable private conversation.

## Differentiation
- Chat-native fiction
- Continuous AI narrative engine
- Structured emotional state
- Automatic scene escalation
- Bengali-first literary romance
- Daily serialized reading habit

## Defensibility
1. Story-state orchestration and evaluation data.
2. Proprietary story-generation workflow.
3. Reader retention data and chapter completion signals.
4. Original IP / story catalog.
5. Creator ecosystem later.
6. Language and cultural quality in Bengali.

---

# 19. Business metrics and unit economics to test

Track:
- CAC
- ARPU
- trial-to-paid
- paid monthly retention
- annual plan mix
- LTV
- content cost per completed story
- LLM cost per active reader
- gross margin

Target hypotheses should be established through experiments rather than presented as facts.

Example internal model:
```text
Monthly active readers        = 100,000
Paid conversion hypothesis    = 3%
Paid users                    = 3,000
Average net subscription      = ₹150/month
Monthly net subscription rev  = ₹450,000
```

This is an illustrative scenario only, not a forecast.

---

# 20. Market context (2026)

Grand View Research estimates India's spiritual wellness app market at **USD 81.9M in 2025**, projected at **USD 94.2M in 2026** and **USD 263.4M by 2033**, with 15.83% CAGR from 2026-2033. This is the broader spiritual-wellness category and is **not** the addressable market for chat fiction. Source: https://www.grandviewresearch.com/horizon/outlook/spiritual-wellness-app-market/india

For the proposed fiction product, the most relevant market is digital fiction / serialized reading / entertainment, which should be researched separately before investment decisions.

---

# 21. Implementation order in Cursor

### Phase 1 — Backend skeleton
- FastAPI project
- config management
- PostgreSQL migrations
- Redis
- Pydantic schemas
- dependency injection
- authentication
- health endpoint

### Phase 2 — Story domain
- Story Bible CRUD
- characters
- relationships
- chapters
- scenes
- plot threads
- emotions
- memories

### Phase 3 — AI orchestration
- `StoryDirector`
- `EmotionEngine`
- `SubtextEngine`
- `DialogueGenerator`
- `ContinuityService`
- `Critic`
- `SafetyService`
- provider abstraction

### Phase 4 — Reader API
- next messages endpoint
- streaming
- progress tracking
- chapter completion

### Phase 5 — Frontend
- chat UI
- story list
- chapter reader
- progress

### Phase 6 — Analytics + payments
- events
- subscriptions
- paywall

### Phase 7 — Quality tuning
Create a test corpus of 100+ scenes and evaluate:
- continuity
- Bengali naturalness
- emotional consistency
- plot progression
- repetitive language
- safety

Do not optimize prompts using one or two manually inspected stories only.

---

# 22. Suggested Python module structure

```text
app/
  main.py
  config.py
  api/
    auth.py
    stories.py
    reading.py
    billing.py
    admin.py
  models/
    user.py
    story.py
    character.py
    chapter.py
    scene.py
    message.py
    emotion.py
    memory.py
    plot_thread.py
    subscription.py
  schemas/
  services/
    story_engine/
      orchestrator.py
      story_bible.py
      chapter_planner.py
      scene_director.py
      emotion_engine.py
      conflict_engine.py
      subtext_engine.py
      dialogue_generator.py
      continuity.py
      critic.py
      safety.py
    memory/
    billing/
    analytics/
  llm/
    base.py
    provider.py
    prompts/
  workers/
  tests/
```

---

# 23. Definition of done for MVP

The MVP is complete when:

- A new story can be created from a brief.
- A 10-chapter outline is generated and persisted.
- Each chapter can produce scenes with structured state.
- Characters retain facts across chapters.
- Emotion values update from events.
- The Scene Director selects the next event.
- Dialogue is generated in Bengali.
- Critic blocks inconsistent scenes.
- Safety checks prevent disallowed content.
- Reader can stream chat messages.
- Reader resumes at the last message.
- Metrics are emitted for reading behavior.
- A paywall can lock later chapters.

---

# 24. First test story

Use an original story with two adult characters, Maya (24) and Arjun (26), set in contemporary Kolkata.

Premise: They know each other through mutual friends. Their attraction grows, but family expectations and an impending marriage discussion create an external pressure. Neither initially says what they actually want.

Tone: emotionally restrained Bengali romance; modern chat behavior; gradual escalation; tasteful non-graphic sensual tension only; strong subtext.

The reader should feel that they are observing a real private conversation and progressively discovering the hidden story behind it.

**End of build specification.**
