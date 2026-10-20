import React, { useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { DndContext, KeyboardSensor, PointerSensor, closestCenter, useSensor, useSensors } from '@dnd-kit/core';
import { SortableContext, arrayMove, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { restrictToVerticalAxis } from '@dnd-kit/modifiers';
import { CSS } from '@dnd-kit/utilities';
import { ChevronDown, GripVertical, Plus, X } from 'lucide-react';
import clsx from 'clsx';
import { OPERATIONS, describeStep, newStep } from '../lib/operations';

const Field = ({ field, value, onChange }) => {
  if (field.kind === 'select') {
    return (
      <select value={value} onChange={(e) => onChange(e.target.value)} className="input">
        {field.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    );
  }
  if (field.kind === 'checkbox') {
    return (
      <input
        type="checkbox"
        checked={value}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 rounded border-line accent-[rgb(var(--accent))]"
      />
    );
  }
  return (
    <input
      type={field.kind}
      value={value}
      min={field.min}
      max={field.max}
      step={field.step}
      required
      onChange={(e) => onChange(e.target.value)}
      className="input"
    />
  );
};

const StepRow = ({ step, index, expanded, onToggle, onUpdate, onRemove }) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: step.id });
  const def = OPERATIONS[step.type];
  const hasFields = def.fields.length > 0;

  return (
    <motion.li
      ref={setNodeRef}
      layout="position"
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, height: 0 }}
      style={{ transform: CSS.Translate.toString(transform), transition }}
      className={clsx('bg-surface border border-line rounded-xl', isDragging && 'relative z-10 shadow-lg')}
    >
      <div className="flex items-center gap-2 px-2 py-2">
        <button
          type="button"
          className="p-1 text-muted hover:text-fg cursor-grab active:cursor-grabbing touch-none"
          aria-label={`Drag to reorder ${def.label}`}
          {...attributes}
          {...listeners}
        >
          <GripVertical size={16} />
        </button>
        <span className="w-5 text-xs tabular-nums text-muted">{index + 1}</span>
        <button
          type="button"
          onClick={hasFields ? onToggle : undefined}
          className={clsx('flex-1 flex items-center gap-2 text-left text-sm min-w-0', !hasFields && 'cursor-default')}
          aria-expanded={hasFields ? expanded : undefined}
        >
          <span className="font-medium">{def.label}</span>
          <span className="text-muted truncate">{describeStep(step)}</span>
          {hasFields && (
            <ChevronDown size={14} className={clsx('ml-auto text-muted transition-transform', expanded && 'rotate-180')} />
          )}
        </button>
        <button type="button" onClick={onRemove} aria-label={`Remove ${def.label}`} className="p-1 text-muted hover:text-danger">
          <X size={16} />
        </button>
      </div>

      <AnimatePresence initial={false}>
        {expanded && hasFields && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            <div className="grid grid-cols-2 gap-3 px-4 pb-4 pt-1">
              {def.fields.map((field) => (
                <label
                  key={field.name}
                  className={clsx(
                    'flex gap-1.5',
                    field.kind === 'checkbox' ? 'flex-row-reverse items-center justify-end self-end pb-2' : 'flex-col',
                    field.kind === 'text' && 'col-span-2'
                  )}
                >
                  <span className="label">{field.label}</span>
                  <Field field={field} value={step.params[field.name]} onChange={(v) => onUpdate(field.name, v)} />
                </label>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.li>
  );
};

// Ordered, drag-to-reorder list of operations. Steps run top to bottom.
const OperationBuilder = ({ steps, onChange }) => {
  const [expandedId, setExpandedId] = useState(null);
  const [adding, setAdding] = useState(false);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const update = (id, name, value) =>
    onChange(steps.map((s) => (s.id === id ? { ...s, params: { ...s.params, [name]: value } } : s)));
  const remove = (id) => onChange(steps.filter((s) => s.id !== id));
  const add = (type) => {
    const step = newStep(type);
    onChange([...steps, step]);
    setExpandedId(OPERATIONS[type].fields.length ? step.id : null);
    setAdding(false);
  };
  const onDragEnd = ({ active, over }) => {
    if (!over || active.id === over.id) return;
    const from = steps.findIndex((s) => s.id === active.id);
    const to = steps.findIndex((s) => s.id === over.id);
    onChange(arrayMove(steps, from, to));
  };

  return (
    <div className="space-y-2">
      <DndContext sensors={sensors} collisionDetection={closestCenter} modifiers={[restrictToVerticalAxis]} onDragEnd={onDragEnd}>
        <SortableContext items={steps.map((s) => s.id)} strategy={verticalListSortingStrategy}>
          <ul className="space-y-2">
            <AnimatePresence initial={false}>
              {steps.map((step, index) => (
                <StepRow
                  key={step.id}
                  step={step}
                  index={index}
                  expanded={expandedId === step.id}
                  onToggle={() => setExpandedId(expandedId === step.id ? null : step.id)}
                  onUpdate={(name, value) => update(step.id, name, value)}
                  onRemove={() => remove(step.id)}
                />
              ))}
            </AnimatePresence>
          </ul>
        </SortableContext>
      </DndContext>

      {adding ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-wrap gap-1.5 p-2 border border-dashed border-line rounded-xl"
        >
          {Object.entries(OPERATIONS).map(([type, def]) => (
            <button
              key={type}
              type="button"
              onClick={() => add(type)}
              className="px-3 py-1.5 rounded-full text-xs bg-subtle text-fg hover:bg-accent hover:text-accent-fg transition-colors"
            >
              {def.label}
            </button>
          ))}
          <button type="button" onClick={() => setAdding(false)} className="px-3 py-1.5 text-xs text-muted hover:text-fg">
            Cancel
          </button>
        </motion.div>
      ) : (
        <button
          type="button"
          onClick={() => setAdding(true)}
          className="w-full flex items-center justify-center gap-1.5 py-2.5 rounded-xl border border-dashed border-line text-sm text-muted hover:text-fg hover:border-muted transition-colors"
        >
          <Plus size={14} /> Add step
        </button>
      )}
    </div>
  );
};

export default OperationBuilder;
