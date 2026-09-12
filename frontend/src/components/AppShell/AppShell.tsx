import { CircleHelp, ShieldCheck } from 'lucide-react';

type Page = 'home' | 'about' | 'team';
type Props = { children: React.ReactNode; onReset?: () => void; page?: Page; onNavigate?: (page: Page) => void };

export function AppShell({ children, onReset, page = 'home', onNavigate }: Props) {
  const go = (next: Page) => { if (next === 'home') onReset?.(); else onNavigate?.(next); };
  return <div className="app-shell">
    <header className="topbar">
      <div className="nav-inner">
        <div className="nav-zone nav-zone-left"><button className="brand button-quiet" onClick={() => go('home')} aria-label="Return to Ustad Assist home"><span className="brand-mark"><ShieldCheck size={19}/></span><span className="brand-name">Ustad Assist</span><span className="brand-sub">technical knowledge system</span></button></div>
        <nav className="primary-nav nav-zone-center" aria-label="Primary navigation"><button className={page === 'home' ? 'nav-link active' : 'nav-link'} onClick={() => go('home')}>Home</button><button className={page === 'about' ? 'nav-link active' : 'nav-link'} onClick={() => go('about')}>About</button><button className={page === 'team' ? 'nav-link active' : 'nav-link'} onClick={() => go('team')}>Project team</button></nav>
        <div className="header-meta nav-zone-right"><span className="header-status"><i className="live-dot"/>System ready</span><span className="mono header-version">MVP / 01</span></div>
      </div>
    </header>
    <main className="main">{children}</main>
    <footer className="footer"><div><strong>Ustad Assist</strong><span>Evidence-led technical troubleshooting for supported electrical equipment.</span></div><nav aria-label="Footer navigation"><button onClick={() => go('home')}>Home</button><button onClick={() => go('about')}>About</button><button onClick={() => go('team')}>Project team</button></nav><span className="footer-note"><CircleHelp size={13}/> Assist, don’t guess.</span></footer>
  </div>;
}
