import {
  ArrowRight,
  BookOpenCheck,
  Camera,
  CheckCircle2,
  CircuitBoard,
  FileCheck2,
  LockKeyhole,
  SearchCheck,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Upload,
} from 'lucide-react';
import type { CatalogResponse } from '../types/api';

type Props = { catalog: CatalogResponse | null; onHome: () => void };

export function About({ catalog, onHome }: Props) {
  const models = catalog?.total_supported_models;
  const categories = catalog?.categories ?? [];
  const manufacturerCount = categories.reduce((total, item) => total + item.manufacturers.length, 0);

  return <div className="info-page about-documentation">
    <section className="info-hero about-doc-hero">
      <div><p className="eyebrow">About Ustad Assist / Product brief</p><h1>A safety-first copilot for turning equipment faults into clear next actions.</h1><p className="lede">Ustad Assist is an AI-powered technical troubleshooting copilot for technicians working with Solar Inverters and UPS systems. It combines exact equipment identity, verified manufacturer documentation, structured retrieval, and explicit safety boundaries in one focused workflow.</p></div>
      <div className="info-hero-mark"><CircuitBoard size={32}/><span>Evidence-led technical knowledge system</span></div>
    </section>

    <nav className="about-commandbar" aria-label="About page sections"><div className="commandbar-status"><span className="commandbar-pulse" /> SYSTEM BRIEF <b>v1.0</b></div><div className="commandbar-links"><a href="#about-section-01">Overview</a><a href="#about-section-04">Workflow</a><a href="#about-section-05">Architecture</a><a href="#about-section-06">Safety</a><a href="#about-section-08">Limitations</a></div><span className="commandbar-meta mono">LIVE / EVIDENCE-LED</span></nav>

    <section className="about-doc-intro"><div><p className="eyebrow">01 / Executive summary</p><h2>Assist, don’t guess.</h2></div><div><p>Ustad Assist accepts an error code, alarm or warning, an equipment image, and an optional symptom description. It identifies or confirms the equipment and model, retrieves relevant information from verified official manufacturer manuals, and presents a structured result.</p><p>The result can include the issue meaning, possible causes, safe checks, technician-only checks, safety warnings, manual and page references, and a next action or escalation path. The system does not replace qualified technicians, guarantee a diagnosis, control equipment automatically, or invent technical information when evidence is unavailable.</p></div></section>

    <section className="about-doc-metrics"><Metric value={models ? String(models) : '—'} label="catalog models" detail="loaded from the live backend" /><Metric value={manufacturerCount ? String(manufacturerCount) : '—'} label="manufacturer groups" detail="derived from the verified catalog" /><Metric value="02" label="input paths" detail="manual and confirmed image flow" /><Metric value="01" label="core principle" detail="assist, don’t guess" /></section>

    <DocSection index="02" eyebrow="Problem statement" title="Technical faults are time-sensitive and context-heavy.">
      <p>Technicians working with Solar Inverters and UPS systems often depend on long PDF manuals, printed documentation, senior technicians, distributor support, previous experience, generic internet searches, videos, and trial-and-error. Under field conditions, that combination can make the right answer slow to find and unsafe assumptions easy to make.</p>
      <div className="about-doc-columns"><DocCard title="Manual complexity" text="Manuals are often long, English-heavy, engineering-oriented, and difficult to search quickly while equipment is active or a site is under pressure." /><DocCard title="Error-code ambiguity" text="The same-looking code can mean different things across manufacturers and models. A code is never interpreted independently from equipment category, manufacturer, and exact model." /><DocCard title="Safety risk" text="High voltage, DC power, electrical isolation, fire risk, battery hazards, energized wiring, and internal servicing all require a cautious boundary." /></div>
    </DocSection>

    <DocSection index="03" eyebrow="Product vision" title="A trusted troubleshooting copilot for technicians.">
      <p>The initial product focuses on Solar Inverters and UPS systems because these categories combine frequent field faults, model-specific documentation, and meaningful electrical safety risks. The longer-term vision is a reusable evidence-and-safety workflow that can expand without weakening the evidence standard.</p>
      <div className="about-roadmap"><RoadmapStep number="NOW" title="Solar Inverters + UPS" text="The current MVP scope and live verified catalog." active /><RoadmapStep number="NEXT" title="Generators, motors, and pumps" text="Potential future categories after evidence and safety workflows are extended." /><RoadmapStep number="LATER" title="HVAC and industrial equipment" text="Future expansion is not part of the current 48-hour MVP." /></div>
    </DocSection>

    <DocSection index="04" eyebrow="How the product works" title="Two input paths. One controlled result flow.">
      <div className="about-flow about-flow-3d"><Flow icon={<CircuitBoard/>} index="01" title="Identify" text="Select category, manufacturer, and exact model from the live catalog." /><Flow icon={<FileCheck2/>} index="02" title="Specify" text="Choose a model-specific verified error or enter the displayed code manually." /><Flow icon={<Camera/>} index="P1" title="Capture" text="Alternatively upload a nameplate or display image for backend vision extraction." /><Flow icon={<LockKeyhole/>} index="03" title="Confirm" text="Image candidates are never trusted automatically; the technician must confirm or edit every field." /><Flow icon={<SearchCheck/>} index="04" title="Retrieve" text="Exact code retrieval runs first; semantic fallback remains scoped to the confirmed model." /><Flow icon={<ShieldCheck/>} index="05" title="Act safely" text="Review meaning, checks, source citation, safety treatment, and next action." /></div>
    </DocSection>

    <section className="about-doc-split"><article className="info-panel"><p className="eyebrow">P0 / Primary path</p><h2>Manual identification</h2><p>The technician selects an equipment category, manufacturer, exact model, and error or alarm code. This is the most controlled path because identity is explicitly supplied by the user and model-specific error options come from the live catalog.</p><div className="mini-list"><span><CheckCircle2 size={15}/> Category → manufacturer → model</span><span><CheckCircle2 size={15}/> Verified error selection or manual code</span><span><CheckCircle2 size={15}/> Optional symptom context</span></div></article><article className="info-panel accent-panel"><p className="eyebrow">P1 / Secondary path</p><h2>Image-assisted identification</h2><p>The technician uploads a nameplate or display image. Vision/OCR returns candidates as an input aid only. Multiple candidates are shown when present, and a human must confirm or edit the detected equipment before troubleshooting begins.</p><div className="mini-list"><span><Upload size={15}/> Drag-and-drop or file picker</span><span><CheckCircle2 size={15}/> Human confirmation required</span><span><ShieldAlert size={15}/> No silent model selection</span></div></article></section>

    <DocSection index="05" eyebrow="Evidence architecture" title="The answer is only as strong as its traceability.">
      <p>Ustad Assist treats the verified knowledge base as the source of truth. The backend loads and normalizes records into a canonical shape so downstream retrieval does not depend on manufacturer-specific raw field names.</p>
      <div className="architecture-grid"><ArchCard icon={<BookOpenCheck/>} title="Verified records" text="Only records marked verified are eligible to become troubleshooting evidence." /><ArchCard icon={<SearchCheck/>} title="Exact-first retrieval" text="The requested category, manufacturer, model, code, and symptom are used to find the most specific evidence." /><ArchCard icon={<CircuitBoard/>} title="Scoped fallback" text="When exact matching misses, semantic search is restricted to the confirmed manufacturer and model—not the full dataset." /><ArchCard icon={<FileCheck2/>} title="Source citation" text="The result carries manual title, document number, page or section information, and an official source link." /></div>
    </DocSection>

    <section className="safety-band about-safety-doc"><div className="safety-band-icon"><ShieldAlert size={23}/></div><div><p className="eyebrow">06 / Safety by design</p><h2>Safety is a deterministic decision, not a decorative warning.</h2><p>Evidence text and generated text are evaluated for hazards such as fire or smoke, electrical hazards, battery hazards, repeated trips, and technician-only procedures. Safe user checks and technician-only checks remain visibly separated. If escalation is required, the interface prioritizes stopping and contacting qualified support over producing more instructions.</p></div></section>

    <DocSection index="07" eyebrow="AI assistance" title="Useful interpretation with explicit boundaries.">
      <div className="about-doc-columns"><DocCard title="What AI does" text="AI can explain retrieved manual evidence in clearer language, organize the result, and help a technician understand the documented next action." /><DocCard title="What AI does not do" text="It does not create a source, override the backend safety decision, silently trust an image candidate, or fill missing manual facts with general technical guesses." /><DocCard title="When grounding is unavailable" text="The verified manual evidence can still be presented through an evidence-only fallback. This keeps the application useful without pretending that unavailable generation was successful." /></div>
    </DocSection>

    <DocSection index="08" eyebrow="Current scope and limitations" title="Focused coverage, not invented coverage.">
      <div className="limitation-list"><Limitation title="Catalog scope" text="The current product is limited to the models and records loaded in the verified dataset. Unsupported equipment is clearly separated from issue-not-verified results." /><Limitation title="Model specificity" text="A code is not portable across manufacturers or models. Family-level documentation is exposed only within its documented model scope." /><Limitation title="Evidence limits" text="If the official documentation does not state a cause or check, the interface shows that it is not stated rather than inventing a procedure." /><Limitation title="Professional responsibility" text="Ustad Assist is an assistive information system. Qualified technicians remain responsible for site conditions, isolation procedures, diagnosis, repair, and final decisions." /></div>
    </DocSection>

    <section className="info-section supported-summary"><div><p className="eyebrow">Live coverage</p><h2>Current backend catalog</h2><p className="section-helper">This summary is loaded from the backend at runtime{models ? ` and currently lists ${models} exact models` : ''}.</p></div><div className="supported-chips">{categories.map((item) => <span key={item.equipment_category}>{item.equipment_category}</span>)}</div></section>
    <section className="closing-cta"><div><p className="eyebrow">The Ustad Assist principle</p><h2>Assist, don’t guess.</h2><p>Start with the equipment you are working on and let verified evidence shape the next action.</p></div><button className="button button-primary" onClick={onHome}>Explore supported equipment <ArrowRight size={16}/></button></section>
  </div>;
}

function Metric({ value, label, detail }: { value: string; label: string; detail: string }) { return <div className="about-doc-metric"><strong>{value}</strong><span>{label}</span><small>{detail}</small></div>; }
function DocSection({ index, eyebrow, title, children }: { index: string; eyebrow: string; title: string; children: React.ReactNode }) { return <section id={`about-section-${index}`} className="about-doc-section"><div className="about-doc-section-head"><span className="about-doc-index">{index}</span><div><p className="eyebrow">{eyebrow}</p><h2>{title}</h2></div></div><div className="about-doc-section-body">{children}</div></section>; }
function DocCard({ title, text }: { title: string; text: string }) { return <article className="about-doc-card"><h3>{title}</h3><p>{text}</p></article>; }
function RoadmapStep({ number, title, text, active = false }: { number: string; title: string; text: string; active?: boolean }) { return <div className={`about-roadmap-step ${active ? 'active' : ''}`}><span>{number}</span><div><h3>{title}</h3><p>{text}</p></div></div>; }
function ArchCard({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) { return <article className="architecture-card"><span className="flow-icon">{icon}</span><h3>{title}</h3><p>{text}</p></article>; }
function Limitation({ title, text }: { title: string; text: string }) { return <div className="limitation-item"><Sparkles size={16}/><div><h3>{title}</h3><p>{text}</p></div></div>; }
function Flow({ icon, index, title, text }: { icon: React.ReactNode; index: string; title: string; text: string }) { return <div className="flow-card"><span className="flow-icon">{icon}</span><span className="flow-index mono">{index}</span><h3>{title}</h3><p>{text}</p></div>; }
