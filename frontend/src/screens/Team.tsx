import { ArrowRight, Linkedin, UsersRound } from 'lucide-react';

type Props = { onHome: () => void };
type Profile = { initials: string; name: string; role: string; contribution: string; featured?: boolean; linkedin?: string };

const profiles: Profile[] = [
  { initials: 'TL', name: 'Team leader profile', role: 'Team leader', contribution: 'Product direction, technical vision, and project coordination.', featured: true },
  { initials: '01', name: 'Team member 01', role: 'Engineering contribution', contribution: 'Project contribution and role details can be added here.' },
  { initials: '02', name: 'Team member 02', role: 'Engineering contribution', contribution: 'Project contribution and role details can be added here.' },
  { initials: '03', name: 'Team member 03', role: 'Engineering contribution', contribution: 'Project contribution and role details can be added here.' },
  { initials: '04', name: 'Team member 04', role: 'Engineering contribution', contribution: 'Project contribution and role details can be added here.' },
  { initials: '05', name: 'Team member 05', role: 'Engineering contribution', contribution: 'Project contribution and role details can be added here.' },
];

export function Team({ onHome }: Props) {
  return <div className="info-page team-page">
    <section className="info-hero"><div><p className="eyebrow">Project team</p><h1>The people building a more dependable troubleshooting workflow.</h1><p className="lede">Ustad Assist brings together product thinking, engineering discipline, and a strong respect for safety-critical technical information.</p></div><div className="info-hero-mark"><UsersRound size={32}/><span>Six-person project team</span></div></section>
    <section className="team-grid">{profiles.map((profile) => <article className={profile.featured ? 'team-card featured' : 'team-card'} key={profile.initials}><div className="avatar">{profile.initials}</div><div className="team-copy"><span className="team-role">{profile.role}</span><h2>{profile.name}</h2><p>{profile.contribution}</p>{profile.linkedin && <a className="linkedin-link" href={profile.linkedin} target="_blank" rel="noreferrer"><Linkedin size={14}/> LinkedIn</a>}</div>{profile.featured && <span className="featured-label">Featured profile</span>}</article>)}</section>
    <section className="team-note"><p className="eyebrow">Profile data</p><p>These profile slots intentionally avoid invented personal information. Replace the placeholder names, roles, photos, and LinkedIn links with the project team’s approved details when available.</p></section>
    <section className="closing-cta"><div><p className="eyebrow">Build with clarity</p><h2>Meet the workflow behind the product.</h2><p>Return to the supported equipment catalog to explore Ustad Assist.</p></div><button className="button button-primary" onClick={onHome}>Go to home <ArrowRight size={16}/></button></section>
  </div>;
}
