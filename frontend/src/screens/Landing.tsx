import { ArrowRight, Camera, ClipboardList, Cpu, FileCheck2, Gauge, ShieldCheck, Zap } from 'lucide-react';
import type { CatalogResponse } from '../types/api';

type Props = {
  catalog: CatalogResponse | null;
  onManual: (category?: string) => void;
  onImage: () => void;
};

function EquipmentIcon({ category }: { category: string }) {
  const label = category.toLowerCase();
  if (label.includes('ups')) return <Gauge size={24} strokeWidth={1.7} />;
  if (label.includes('solar') || label.includes('inverter')) return <Zap size={24} strokeWidth={1.7} />;
  return <Cpu size={24} strokeWidth={1.7} />;
}

export function Landing({ catalog, onManual, onImage }: Props) {
  return (
    <>
      <section className="landing-hero">
        <div className="hero-copy">
          <p className="eyebrow">Technical troubleshooting / evidence first</p>
          <h1>Technical troubleshooting,<br /><span>grounded in verified manuals.</span></h1>
          <p className="lede">Identify supported electrical equipment, retrieve source-backed guidance, and act with a clear safety boundary.</p>
          <div className="hero-actions">
            <button className="button button-primary" onClick={() => onManual()}><ClipboardList size={16} /> Start with equipment</button>
            <button className="button button-secondary" onClick={onImage}><Camera size={16} /> Use an image</button>
          </div>
        </div>
        <div className="hero-proof">
          <div className="proof-icon"><ShieldCheck size={22} /></div>
          <p className="eyebrow">Trust model</p>
          <strong>Assist, don’t guess.</strong>
          <p>Guidance is shown only when the backend returns verified evidence and a structured safety decision.</p>
          <div className="proof-rule" />
          <span><FileCheck2 size={14} /> Manufacturer manuals</span>
          <span><ShieldCheck size={14} /> Safety checked</span>
        </div>
      </section>

      <section className="equipment-section">
        <div className="section-heading-row">
          <div><p className="eyebrow">Supported equipment</p><h2>Select what you are working on</h2><p className="section-helper">Choose a category to continue to manufacturer and exact model.</p></div>
          <span className="catalog-count mono">{catalog ? `${catalog.total_supported_models} verified models` : 'Loading catalog'}</span>
        </div>
        {catalog ? (
          <div className="equipment-grid">
            {catalog.categories.map((category) => (
              <button className="equipment-card" key={category.equipment_category} onClick={() => onManual(category.equipment_category)}>
                <div className="equipment-topline"><span className="equipment-icon"><EquipmentIcon category={category.equipment_category} /></span><span className="status-pill status-success"><ShieldCheck size={12} /> supported</span></div>
                <div><h3>{category.equipment_category}</h3><p>{category.manufacturers.length} manufacturer{category.manufacturers.length === 1 ? '' : 's'} · {category.manufacturers.reduce((total, item) => total + item.models.length, 0)} exact models</p></div>
                <span className="equipment-cta">Select equipment <ArrowRight size={15} /></span>
              </button>
            ))}
          </div>
        ) : (
          <div className="catalog-skeleton"><div /><div /></div>
        )}
      </section>

      <section className="workflow-strip">
        <div><p className="eyebrow">How it works</p><h3>From identity to safe action.</h3></div>
        <div className="workflow-steps"><span><b>01</b> Identify</span><i /><span><b>02</b> Confirm</span><i /><span><b>03</b> Retrieve</span><i /><span><b>04</b> Act safely</span></div>
      </section>
    </>
  );
}
