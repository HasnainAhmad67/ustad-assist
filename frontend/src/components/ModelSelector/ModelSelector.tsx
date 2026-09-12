import { useEffect, useMemo, useState } from 'react';
import type { CatalogResponse } from '../../types/api';

type Props = {
  catalog: CatalogResponse;
  category: string;
  manufacturer: string;
  model: string;
  onCategory: (value: string) => void;
  onManufacturer: (value: string) => void;
  onModel: (value: string) => void;
};

const displayCategory = (value: string) => value.replace(/[_-]+/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());

export function ModelSelector({ catalog, category, manufacturer, model, onCategory, onManufacturer, onModel }: Props) {
  const [manufacturerManual, setManufacturerManual] = useState(false);
  const [modelManual, setModelManual] = useState(false);
  const [manufacturerSearch, setManufacturerSearch] = useState(manufacturer);
  const [modelSearch, setModelSearch] = useState(model);

  const categoryData = catalog.categories.find((item) => item.equipment_category === category);
  const manufacturerData = categoryData?.manufacturers.find((item) => item.manufacturer === manufacturer);
  const manufacturers = categoryData?.manufacturers ?? [];
  const models = manufacturerData?.models ?? [];
  const filteredManufacturers = useMemo(() => manufacturers.filter((item) => item.manufacturer.toLowerCase().includes(manufacturerSearch.toLowerCase())), [manufacturers, manufacturerSearch]);
  const filteredModels = useMemo(() => models.filter((item) => [item.model, ...item.model_aliases].some((value) => value.toLowerCase().includes(modelSearch.toLowerCase()))), [models, modelSearch]);

  useEffect(() => { setManufacturerSearch(manufacturer); }, [manufacturer]);
  useEffect(() => { setModelSearch(model); }, [model]);

  const changeCategory = (value: string) => {
    setManufacturerManual(false);
    setModelManual(false);
    setManufacturerSearch('');
    setModelSearch('');
    onCategory(value);
    onManufacturer('');
    onModel('');
  };

  const changeManufacturer = (value: string) => {
    setModelManual(false);
    setManufacturerSearch(value);
    setModelSearch('');
    onManufacturer(value);
    onModel('');
  };

  const toggleManufacturerManual = () => {
    const next = !manufacturerManual;
    setManufacturerManual(next);
    setModelManual(false);
    setManufacturerSearch('');
    setModelSearch('');
    onManufacturer('');
    onModel('');
  };

  const toggleModelManual = () => {
    const next = !modelManual;
    setModelManual(next);
    setModelSearch('');
    onModel('');
  };

  return <>
    <div className="field full">
      <label htmlFor="equipment_category">Equipment category</label>
      <select id="equipment_category" className="select" value={category} onChange={(event) => changeCategory(event.target.value)}>
        <option value="">Select category</option>
        {catalog.categories.map((item) => <option key={item.equipment_category} value={item.equipment_category}>{displayCategory(item.equipment_category)}</option>)}
      </select>
      <small>{catalog.categories.length} verified categor{catalog.categories.length === 1 ? 'y' : 'ies'} in the live catalog.</small>
    </div>

    <div className="field">
      <div className="field-label-row"><label htmlFor="manufacturer">Manufacturer</label><span className={manufacturerManual ? 'entry-badge manual' : 'entry-badge verified'}>{manufacturerManual ? 'Manual entry' : 'Verified catalog'}</span></div>
      {!manufacturerManual ? <>
        <input id="manufacturer" className="input searchable-input" list="manufacturer-options" placeholder="Search manufacturer…" value={manufacturerSearch} disabled={!category} onChange={(event) => { const value = event.target.value; const exact = manufacturers.find((item) => item.manufacturer.toLowerCase() === value.trim().toLowerCase()); changeManufacturer(exact?.manufacturer ?? ''); setManufacturerSearch(value); }} />
        <datalist id="manufacturer-options">{filteredManufacturers.map((item) => <option key={item.manufacturer} value={item.manufacturer} />)}</datalist>
        <small>{category ? `${manufacturers.length} verified manufacturer${manufacturers.length === 1 ? '' : 's'} available` : 'Select a category first.'}</small>
      </> : <>
        <input id="manufacturer" className="input" placeholder="Enter manufacturer name" value={manufacturer} onChange={(event) => onManufacturer(event.target.value)} />
        <small className="manual-help">Not checked against the verified catalog.</small>
      </>}
      <button type="button" className="link-button" onClick={toggleManufacturerManual}>{manufacturerManual ? '← Use verified catalog' : '+ Manufacturer not listed? Enter manually'}</button>
    </div>

    <div className="field">
      <div className="field-label-row"><label htmlFor="model">Exact model</label><span className={modelManual ? 'entry-badge manual' : 'entry-badge verified'}>{modelManual ? 'Manual entry' : 'Verified catalog'}</span></div>
      {!modelManual ? <>
        <input id="model" className="input searchable-input mono" list="model-options" placeholder={manufacturerManual ? 'Select a verified manufacturer first' : 'Search exact model…'} value={modelSearch} disabled={!manufacturer || manufacturerManual} onChange={(event) => { const value = event.target.value; const exact = models.find((item) => item.model.toLowerCase() === value.trim().toLowerCase()); onModel(exact?.model ?? ''); setModelSearch(value); }} />
        <datalist id="model-options">{filteredModels.map((item) => <option key={item.model} value={item.model}>{item.model_aliases.length ? `Alias: ${item.model_aliases.join(', ')}` : ''}</option>)}</datalist>
        <small>{manufacturerManual ? 'Choose manual model entry below.' : manufacturer ? `${models.length} verified model${models.length === 1 ? '' : 's'} available` : 'Select a verified manufacturer first.'}</small>
      </> : <>
        <input id="model" className="input mono" placeholder="Enter exact model" value={model} onChange={(event) => onModel(event.target.value)} />
        <small className="manual-help">Not checked against the verified catalog.</small>
      </>}
      <button type="button" className="link-button" onClick={toggleModelManual}>{modelManual ? '← Use verified catalog' : '+ Model not listed? Enter manually'}</button>
    </div>
  </>;
}
