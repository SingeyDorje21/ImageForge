// Catalog of image operations the API accepts. Field defaults are what a new step starts with.
const POSITIONS = [
  { value: 'bottom_right', label: 'Bottom right' },
  { value: 'bottom_left', label: 'Bottom left' },
  { value: 'top_right', label: 'Top right' },
  { value: 'top_left', label: 'Top left' },
  { value: 'center', label: 'Center' },
];

export const OPERATIONS = {
  resize: {
    label: 'Resize',
    fields: [
      { name: 'width', label: 'Width', kind: 'number', default: 400, min: 1, max: 10000 },
      { name: 'height', label: 'Height', kind: 'number', default: 400, min: 1, max: 10000 },
    ],
  },
  crop: {
    label: 'Crop',
    fields: [
      { name: 'left', label: 'Left', kind: 'number', default: 0, min: 0, max: 10000 },
      { name: 'top', label: 'Top', kind: 'number', default: 0, min: 0, max: 10000 },
      { name: 'width', label: 'Width', kind: 'number', default: 400, min: 1, max: 10000 },
      { name: 'height', label: 'Height', kind: 'number', default: 400, min: 1, max: 10000 },
    ],
  },
  rotate: {
    label: 'Rotate',
    fields: [
      { name: 'degrees', label: 'Degrees (CCW)', kind: 'number', default: 90, min: -360, max: 360 },
      { name: 'expand', label: 'Expand canvas', kind: 'checkbox', default: true },
    ],
  },
  flip: {
    label: 'Flip',
    fields: [
      {
        name: 'direction', label: 'Direction', kind: 'select', default: 'horizontal',
        options: [{ value: 'horizontal', label: 'Horizontal' }, { value: 'vertical', label: 'Vertical' }],
      },
    ],
  },
  grayscale: { label: 'Grayscale', fields: [] },
  blur: {
    label: 'Blur',
    fields: [{ name: 'radius', label: 'Radius', kind: 'number', default: 2, min: 0.1, max: 100, step: 0.1 }],
  },
  sharpen: {
    label: 'Sharpen',
    fields: [
      { name: 'radius', label: 'Radius', kind: 'number', default: 2, min: 0.1, max: 100, step: 0.1 },
      { name: 'percent', label: 'Strength %', kind: 'number', default: 150, min: 1, max: 500 },
    ],
  },
  watermark: {
    label: 'Watermark',
    fields: [
      { name: 'text', label: 'Text', kind: 'text', default: 'ImageForge' },
      { name: 'position', label: 'Position', kind: 'select', default: 'bottom_right', options: POSITIONS },
      { name: 'opacity', label: 'Opacity', kind: 'number', default: 0.5, min: 0, max: 1, step: 0.05 },
      { name: 'font_size', label: 'Font size', kind: 'number', default: 24, min: 8, max: 500 },
    ],
  },
  quality: {
    label: 'Quality',
    fields: [{ name: 'quality', label: 'Quality (1-100)', kind: 'number', default: 80, min: 1, max: 100 }],
  },
  strip_exif: { label: 'Strip EXIF', fields: [] },
  format_convert: {
    label: 'Convert format',
    fields: [
      {
        name: 'target_format', label: 'Format', kind: 'select', default: 'webp',
        options: [{ value: 'webp', label: 'WebP' }, { value: 'png', label: 'PNG' }, { value: 'jpg', label: 'JPG' }],
      },
    ],
  },
};

let nextId = 1;

export const newStep = (type) => ({
  id: nextId++,
  type,
  params: Object.fromEntries(OPERATIONS[type].fields.map((f) => [f.name, f.default])),
});

// Turn builder steps into the JSON the API expects, with numbers as numbers.
export const toPayload = (steps) =>
  steps.map(({ type, params }) => {
    const op = { type };
    for (const field of OPERATIONS[type].fields) {
      const value = params[field.name];
      op[field.name] = field.kind === 'number' ? Number(value) : value;
    }
    return op;
  });

// One-click starting points for the step list. Each entry is [type, param overrides].
export const PRESETS = [
  {
    name: 'Web optimized',
    steps: [['resize', { width: 1600, height: 1600 }], ['strip_exif', {}], ['quality', { quality: 80 }], ['format_convert', { target_format: 'webp' }]],
  },
  {
    name: 'Thumbnail',
    steps: [['resize', { width: 300, height: 300 }], ['format_convert', { target_format: 'webp' }]],
  },
  {
    name: 'Strip metadata',
    steps: [['strip_exif', {}]],
  },
  {
    name: 'Black & white',
    steps: [['grayscale', {}], ['sharpen', {}]],
  },
];

export const presetSteps = (preset) =>
  preset.steps.map(([type, overrides]) => {
    const step = newStep(type);
    return { ...step, params: { ...step.params, ...overrides } };
  });

// Short human summary of a step's settings, shown on collapsed rows.
export const describeStep = ({ type, params }) => {
  switch (type) {
    case 'resize': return `${params.width} × ${params.height}`;
    case 'crop': return `${params.width} × ${params.height} at ${params.left}, ${params.top}`;
    case 'rotate': return `${params.degrees}°`;
    case 'flip': return params.direction;
    case 'blur': return `radius ${params.radius}`;
    case 'sharpen': return `${params.percent}%`;
    case 'watermark': return `“${params.text}”`;
    case 'quality': return `${params.quality}`;
    case 'format_convert': return params.target_format.toUpperCase();
    default: return '';
  }
};
