import React, { useState } from 'react';
import { Plus, X, ArrowUp } from 'lucide-react';
import { OPERATIONS, newStep } from '../lib/operations';

// Lets the user build an ordered chain of operations. Styling comes from the page via class props.
const OperationBuilder = ({ steps, onChange, inputClass = '', labelClass = '', stepClass = '', buttonClass = '' }) => {
  const [toAdd, setToAdd] = useState('resize');

  const update = (id, name, value) =>
    onChange(steps.map((s) => (s.id === id ? { ...s, params: { ...s.params, [name]: value } } : s)));
  const remove = (id) => onChange(steps.filter((s) => s.id !== id));
  const moveUp = (index) => {
    const next = [...steps];
    [next[index - 1], next[index]] = [next[index], next[index - 1]];
    onChange(next);
  };

  return (
    <div className="space-y-3">
      {steps.map((step, index) => {
        const def = OPERATIONS[step.type];
        return (
          <div key={step.id} className={stepClass}>
            <div className="flex items-center justify-between mb-2">
              <span className={labelClass}>{index + 1}. {def.label}</span>
              <div className="flex gap-2">
                {index > 0 && (
                  <button type="button" onClick={() => moveUp(index)} aria-label="Move up" className="opacity-60 hover:opacity-100">
                    <ArrowUp size={16} />
                  </button>
                )}
                <button type="button" onClick={() => remove(step.id)} aria-label="Remove" className="opacity-60 hover:opacity-100">
                  <X size={16} />
                </button>
              </div>
            </div>
            {def.fields.length > 0 && (
              <div className="grid grid-cols-2 gap-2">
                {def.fields.map((field) => (
                  <label key={field.name} className={`flex flex-col gap-1 text-xs ${field.kind === 'text' ? 'col-span-2' : ''}`}>
                    <span className="opacity-70">{field.label}</span>
                    {field.kind === 'select' ? (
                      <select value={step.params[field.name]} onChange={(e) => update(step.id, field.name, e.target.value)} className={inputClass}>
                        {field.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                      </select>
                    ) : field.kind === 'checkbox' ? (
                      <input type="checkbox" checked={step.params[field.name]} onChange={(e) => update(step.id, field.name, e.target.checked)} className="w-4 h-4" />
                    ) : (
                      <input
                        type={field.kind}
                        value={step.params[field.name]}
                        min={field.min}
                        max={field.max}
                        step={field.step}
                        required
                        onChange={(e) => update(step.id, field.name, e.target.value)}
                        className={inputClass}
                      />
                    )}
                  </label>
                ))}
              </div>
            )}
          </div>
        );
      })}

      <div className="flex gap-2">
        <select value={toAdd} onChange={(e) => setToAdd(e.target.value)} className={`flex-1 ${inputClass}`}>
          {Object.entries(OPERATIONS).map(([type, def]) => <option key={type} value={type}>{def.label}</option>)}
        </select>
        <button type="button" onClick={() => onChange([...steps, newStep(toAdd)])} className={`flex items-center gap-1 ${buttonClass}`}>
          <Plus size={16} /> Add step
        </button>
      </div>
    </div>
  );
};

export default OperationBuilder;
