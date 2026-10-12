import type { Analyzer } from '../types';
import { daysUntil } from '../helpers';

// A field's value, matching its name in any case, and ignoring numbers added to repeats
const getField = (fields: Record<string, string> = {}, name: string) =>
  Object.entries(fields).find(([key]) => key.toLowerCase().replace(/\d+$/, '') === name)?.[1];

// Flag a missing security.txt, or one missing the Contact and Expires fields it needs
const securityTxt: Analyzer = (d) => {
  if (!d.isPresent) {
    return [
      {
        severity: 'warning',
        title: 'No security.txt published',
        detail: 'Add /.well-known/security.txt with disclosure contact info',
      },
    ];
  }
  const out: ReturnType<Analyzer> = [{ severity: 'pass', title: 'security.txt found' }];
  if (!getField(d.fields, 'contact')) {
    out.push({
      severity: 'issue',
      title: 'security.txt has no Contact field',
      detail: 'Contact is required, as it tells researchers how to report a vulnerability',
    });
  }
  const days = daysUntil(getField(d.fields, 'expires'));
  if (days === null) {
    out.push({
      severity: 'warning',
      title: 'security.txt has no valid Expires date',
      detail: 'Expires is required. Set it under a year ahead, like 2027-01-01T00:00:00Z',
    });
  } else if (days < 0) {
    out.push({
      severity: 'warning',
      title: `security.txt expired ${-days} day(s) ago`,
      detail: 'Researchers treat an expired file as out of date, so review it and move Expires on',
    });
  } else if (days > 366) {
    out.push({
      severity: 'info',
      title: 'security.txt expires over a year ahead',
      detail: 'Keep Expires under a year ahead, so the file gets reviewed regularly',
    });
  }
  if (!d.isPgpSigned) {
    out.push({
      severity: 'info',
      title: 'security.txt not PGP signed',
      detail: 'Sign the file to let researchers verify authenticity',
    });
  }
  return out;
};

export default securityTxt;
