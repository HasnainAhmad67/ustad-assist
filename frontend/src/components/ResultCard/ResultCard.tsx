import { AlertTriangle, BookOpen, CheckCircle2, ClipboardCheck, Wrench } from 'lucide-react';
import type { EvidenceOut, GroundedAnswerOut, SafetyOut } from '../../types/api';
import { SafetyCard } from '../SafetyCard/SafetyCard';
import { SourceCitationCard } from '../SourceCitationCard/SourceCitationCard';

type Props = { evidence: EvidenceOut; answer?: GroundedAnswerOut | null; safety?: SafetyOut | null };
export function ResultCard({ evidence, answer, safety }: Props) {
  const unstated = 'Not stated in manual';
  const causes = answer?.cause_explanations?.length ? answer.cause_explanations : evidence.possible_causes;
  const safe = answer?.safe_check_guidance?.length ? answer.safe_check_guidance : evidence.safe_user_checks;
  const tech = answer?.technician_only_guidance?.length ? answer.technician_only_guidance : evidence.technician_only_checks;
  const renderItems = (items: string[]) => (items.length ? items : [unstated]).map((item, i) => <li key={`${item}-${i}`}>{item}</li>);

  return <div className="result-stack">
    <section className={`card result-hero ${safety?.escalate ? 'escalate' : ''}`}><div className="result-head"><div><p className="eyebrow">Verified result</p><h2 className="result-title">{answer?.issue_summary || evidence.issue_title}</h2><p className="result-meta"><span className="mono">{evidence.manufacturer} / {evidence.model}</span> · code <span className="mono">{evidence.code}</span></p></div><span className="status-pill status-success"><CheckCircle2 size={13}/>evidence-backed</span></div></section>
    <section className="card card-pad"><div className="section-title"><BookOpen size={17}/><h3>What it means</h3></div><p className="lede">{answer?.meaning_explanation || evidence.meaning || unstated}</p></section>
    <section className="card card-pad"><div className="section-title"><AlertTriangle size={17}/><h3>Possible causes</h3></div><ul className="list">{renderItems(causes)}</ul></section>
    <section className="card card-pad"><div className="section-title"><ClipboardCheck size={17}/><h3>Recommended checks</h3></div><div className="check-grid"><div className="check-panel check-safe"><h3><CheckCircle2 size={16}/>Safe checks</h3><ul className="list">{renderItems(safe)}</ul></div><div className="check-panel check-tech"><h3><Wrench size={16}/>Technician-only checks</h3><ul className="list">{renderItems(tech)}</ul></div></div></section>
    <section className="card card-pad"><p className="eyebrow">Documented troubleshooting steps</p><ul className="list">{renderItems(evidence.troubleshooting_steps)}</ul></section>
    <SafetyCard safety={safety}/><SourceCitationCard source={evidence.source}/>
    {evidence.detailed_note && <section className="card card-pad"><p className="eyebrow">Detailed note about this error</p><p>{evidence.detailed_note}</p></section>}
    <section className="card card-pad"><p className="eyebrow">Next action</p><h3>{answer?.next_action || 'Follow the documented checks and escalate if the condition persists.'}</h3><p className="helper">If the observed condition differs from this evidence, stop and seek qualified support rather than guessing.</p></section>
  </div>;
}
