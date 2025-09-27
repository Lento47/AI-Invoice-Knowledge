export const kpiCards = [
  {
    label: 'Pending Approvals',
    value: 8,
    delta: '+2 vs last week',
    trend: 'up'
  },
  {
    label: 'Invoices Processed',
    value: 142,
    delta: '+12% efficiency',
    trend: 'up'
  },
  {
    label: 'Average Cycle Time',
    value: '2.4d',
    delta: '-0.6d this month',
    trend: 'down'
  },
  {
    label: 'Exceptions',
    value: 3,
    delta: '2 high priority',
    trend: 'neutral'
  }
];

export const cashFlowSeries = [
  { day: 'Mon', value: 12 },
  { day: 'Tue', value: 18 },
  { day: 'Wed', value: 15 },
  { day: 'Thu', value: 22 },
  { day: 'Fri', value: 26 },
  { day: 'Sat', value: 21 },
  { day: 'Sun', value: 24 }
];

export const invoiceSummary = {
  id: 'INV-2098',
  vendor: 'Pura Vida Supplies',
  issuedOn: '2025-05-02',
  dueOn: '2025-05-16',
  amount: '$4,860.00',
  status: 'Awaiting Approval',
  reference: 'PO-6635',
  notes: 'Expedited shipping requested'
};

export const invoiceLineItems = [
  {
    id: '1',
    description: 'Thermal paper rolls',
    quantity: 120,
    unitCost: '$12.50',
    amount: '$1,500.00'
  },
  {
    id: '2',
    description: 'Receipt printers',
    quantity: 15,
    unitCost: '$120.00',
    amount: '$1,800.00'
  },
  {
    id: '3',
    description: 'POS tablets (Wi-Fi)',
    quantity: 6,
    unitCost: '$220.00',
    amount: '$1,320.00'
  },
  {
    id: '4',
    description: 'Custom cabling kit',
    quantity: 6,
    unitCost: '$40.00',
    amount: '$240.00'
  }
];

export const vendors = [
  {
    id: 'v-01',
    name: 'Pura Vida Supplies',
    category: 'Hardware',
    contact: 'andrea@puravida.cr',
    status: 'Active'
  },
  {
    id: 'v-02',
    name: 'San José Stationers',
    category: 'Office Supplies',
    contact: 'ventas@sanjose.co.cr',
    status: 'Active'
  },
  {
    id: 'v-03',
    name: 'CloudCafe Roasters',
    category: 'Hospitality',
    contact: 'orders@cloudcafe.cr',
    status: 'On Hold'
  },
  {
    id: 'v-04',
    name: 'Montezuma Analytics',
    category: 'Consulting',
    contact: 'sofia@montezuma.io',
    status: 'Active'
  },
  {
    id: 'v-05',
    name: 'Tamarindo Creative',
    category: 'Design',
    contact: 'hola@tamarindocreative.cr',
    status: 'Prospect'
  }
];

export const reports = [
  {
    id: 'r-01',
    title: 'Monthly Spend Overview',
    description: 'Summary of paid vs outstanding invoices by department.',
    updated: 'Updated 2 days ago'
  },
  {
    id: 'r-02',
    title: 'Aging Report',
    description: 'Breakdown of invoices by 0-30, 31-60, 61-90, and 90+ days.',
    updated: 'Updated yesterday'
  },
  {
    id: 'r-03',
    title: 'Vendor Performance',
    description: 'Delivery, accuracy, and SLA insights by supplier.',
    updated: 'Updated 4 days ago'
  }
];

export const approvals = [
  {
    id: 'a-01',
    title: 'Invoice INV-2098',
    vendor: 'Pura Vida Supplies',
    amount: '$4,860.00',
    submitted: '2h ago',
    status: 'Pending'
  },
  {
    id: 'a-02',
    title: 'Purchase Request PR-447',
    vendor: 'CloudCafe Roasters',
    amount: '$980.00',
    submitted: '5h ago',
    status: 'Pending'
  },
  {
    id: 'a-03',
    title: 'Contract Renewal CT-032',
    vendor: 'Montezuma Analytics',
    amount: '$12,400.00',
    submitted: 'Yesterday',
    status: 'Pending'
  }
];

export const settingToggles = [
  {
    id: 'notifications',
    label: 'Email me daily approval summaries',
    description: 'Receive a short digest every morning at 8:00 am.'
  },
  {
    id: 'autoAssign',
    label: 'Auto-assign invoices under $1,000',
    description: 'Automatically route small invoices to fast-track queue.'
  },
  {
    id: 'reminders',
    label: 'Enable due date reminders',
    description: 'Send heads-up notifications 3 days before an invoice is due.'
  }
];

export const accentSwatches = [
  { id: 'indigo', label: 'Indigo Core', value: '#3F51B5' },
  { id: 'flagBlue', label: 'Catalina Blue', value: '#002B7F' },
  { id: 'flagRed', label: 'Philippine Red', value: '#CE1126' },
  { id: 'rainforest', label: 'Rainforest Green', value: '#3C8D0D' }
];
