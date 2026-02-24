export function money(n: number | null | undefined): string {
  return '$' + Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function pct(n: number | null | undefined): string {
  return Number(n || 0).toFixed(1) + '%';
}

export function fmtDate(d: string | null | undefined): string {
  if (!d) return '';
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export function typeLabel(t: string): string {
  const m: Record<string, string> = {
    checking: 'Checking', savings: 'Savings', credit_card: 'Credit Card',
    investment: 'Investment', loan: 'Loan', mortgage: 'Mortgage',
    real_estate: 'Real Estate', other: 'Other'
  };
  return m[t] || t;
}

export const monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
