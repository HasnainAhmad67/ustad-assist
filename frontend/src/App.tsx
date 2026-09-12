import { useEffect, useState } from 'react';
import { AppShell } from './components/AppShell/AppShell';
import { LoadingState } from './components/LoadingState/LoadingState';
import { useTroubleshootFlow } from './hooks/useTroubleshootFlow';
import { About } from './screens/About';
import { Confirmation } from './screens/Confirmation';
import { ErrorState } from './screens/ErrorState';
import { ImageUpload } from './screens/ImageUpload';
import { InputForm } from './screens/InputForm';
import { Landing } from './screens/Landing';
import { Result } from './screens/Result';
import { Team } from './screens/Team';
import { Unsupported } from './screens/Unsupported';

type Page = 'home' | 'about' | 'team';

export default function App() {
  const flow = useTroubleshootFlow();
  const [page, setPage] = useState<Page>('home');
  const [mode, setMode] = useState<'manual' | 'image' | null>(null);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [lastManual, setLastManual] = useState<{ equipment_category: string; manufacturer: string; model: string; code: string; symptom: string } | null>(null);
  const [lastFile, setLastFile] = useState<File | null>(null);

  useEffect(() => {
    if (!flow.catalog && flow.state === 'idle' && !flow.error) flow.loadCatalog().catch(() => undefined);
  }, [flow.catalog, flow.state, flow.error, flow.loadCatalog]);

  const reset = () => { setPage('home'); setMode(null); setSelectedCategory(''); setLastManual(null); setLastFile(null); flow.reset(); };
  const navigate = (next: Page) => { setPage(next); setMode(null); };
  const manual = async (category = '') => { setPage('home'); setSelectedCategory(category); setMode('manual'); try { await flow.beginManual(); } catch { /* typed error state is rendered by the hook */ } };
  const image = async () => { setPage('home'); setMode('image'); flow.beginImage(); try { await flow.loadCatalog(); } catch { /* typed error state is rendered by the hook */ } };
  const submitManual = (data: typeof lastManual) => { if (!data) return; setLastManual(data); flow.submitTroubleshoot({ ...data, source: 'manual' }).catch(() => undefined); };
  const submitFile = (file: File) => { setLastFile(file); flow.submitImage(file).catch(() => undefined); };
  const retry = () => { if (lastManual) flow.submitTroubleshoot({ ...lastManual, source: 'manual' }).catch(() => undefined); else if (lastFile) flow.submitImage(lastFile).catch(() => undefined); else reset(); };

  let content: React.ReactNode;
  if (page === 'about') content = <About catalog={flow.catalog} onHome={reset} />;
  else if (page === 'team') content = <Team onHome={reset} />;
  else if (flow.state === 'retrieving') content = <LoadingState />;
  else if (flow.state === 'unsupported' && flow.vision?.status === 'image_unclear') content = <Unsupported kind="image_unclear" message={flow.vision.message} onImage={image} onManual={manual} />;
  else if (flow.state === 'unsupported' && flow.vision?.status === 'no_candidates') content = <Unsupported kind="no_candidates" message={flow.vision.message} onImage={image} onManual={manual} />;
  else if (flow.state === 'confirming' && flow.catalog) content = <Confirmation candidates={flow.candidates} catalog={flow.catalog} onConfirm={(request) => flow.submitTroubleshoot(request).catch(() => undefined)} onBack={() => flow.setState('identifying')} onRetry={() => { flow.beginImage(); setLastFile(null); }} />;
  else if (flow.state === 'result' || flow.state === 'unsupported') content = flow.result ? <Result response={flow.result} onReset={reset} onRetry={retry} /> : <ErrorState message="The backend returned no result payload." onRetry={retry} onReset={reset} />;
  else if (flow.state === 'error') content = <ErrorState message={flow.error?.message ?? 'The request could not be completed.'} onRetry={retry} onReset={reset} />;
  else if (mode === 'manual' && flow.catalog) content = <InputForm catalog={flow.catalog} initialCategory={selectedCategory} onBack={reset} onSubmit={submitManual} />;
  else if (mode === 'image') content = <ImageUpload onBack={reset} onSubmit={submitFile} onManual={manual} />;
  else content = <Landing catalog={flow.catalog} onManual={manual} onImage={image} />;

  return <AppShell page={page} onNavigate={navigate} onReset={reset}>{content}</AppShell>;
}
