import { ArrowLeft, ArrowRight } from 'lucide-react';
import { useState } from 'react';
import type { CatalogResponse } from '../types/api';
import { ModelSelector } from '../components/ModelSelector/ModelSelector';

type Props = {
  catalog: CatalogResponse;
  initialCategory?: string;
  onBack: () => void;
  onSubmit: (data: { equipment_category: string; manufacturer: string; model: string; code: string; symptom: string }) => void;
};

export function InputForm({ catalog, initialCategory = '', onBack, onSubmit }: Props) {
  const [category, setCategory] = useState(initialCategory);
  const [manufacturer, setManufacturer] = useState('');
  const [model, setModel] = useState('');
  const [code, setCode] = useState('');
  const [symptom, setSymptom] = useState('');
  const valid = Boolean(category && manufacturer && model && code.trim());

  return <>
    <div className="stepper"><span className="step active"><i>1</i> Identify</span><span className="step-line"/><span className="step"><i>2</i> Retrieve</span><span className="step-line"/><span className="step"><i>3</i> Act</span></div>
    <section className="card card-pad form-card">
      <div className="page-heading"><div><p className="eyebrow">Manual identification</p><h2>What are you working on?</h2><p className="helper">Select from the live verified catalog. The exact model matters.</p></div><span className="mono helper">{catalog.total_supported_models} models supported</span></div>
      <div className="form-grid">
        <ModelSelector catalog={catalog} category={category} manufacturer={manufacturer} model={model} onCategory={setCategory} onManufacturer={setManufacturer} onModel={setModel}/>
        <div className="field"><label htmlFor="code">Error / alarm code</label><input id="code" className="input mono" placeholder="e.g. E-021" value={code} onChange={(e) => setCode(e.target.value)} /><small>Enter the code exactly as displayed.</small></div>
        <div className="field full"><label htmlFor="symptom">Observed symptom <span className="helper">(optional)</span></label><textarea id="symptom" className="textarea" placeholder="Anything else the technician observed…" value={symptom} onChange={(e) => setSymptom(e.target.value)} /></div>
      </div>
      <div className="form-actions"><button className="button button-secondary" onClick={onBack}><ArrowLeft size={15}/>Back</button><button className="button button-primary" disabled={!valid} onClick={() => onSubmit({ equipment_category: category, manufacturer, model, code: code.trim(), symptom: symptom.trim() })}>Retrieve verified guidance <ArrowRight size={15}/></button></div>
    </section>
  </>;
}
