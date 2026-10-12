import { Card } from 'client/components/Form/Card';
import Row from 'client/components/Form/Row';
import { SEVERITIES, type Severity } from 'client/analysis/types';
import { HEADERS, checkHeader, hasFrameAncestors } from 'client/analysis/rules/http-security';

const cardStyles = `
  span.lbl { flex: none !important; }
  span.val { flex: 1; text-align: right; }
`;

const ICONS: Record<Severity, string> = {
  critical: '❌',
  issue: '❌',
  warning: '⚠️',
  info: 'ⓘ',
  pass: '✅',
};

// A header's value, marked with its worst finding
const showHeader = (d: any, key: string) => {
  const severities = checkHeader(d, key).map((finding) => finding.severity);
  const icon = ICONS[SEVERITIES.find((s) => severities.includes(s)) || 'pass'];
  if (d[key]) return `${icon} ${d[key]}`;
  return `${icon} ${key === 'xFrameOptions' && hasFrameAncestors(d) ? 'Via CSP' : 'No'}`;
};

const HttpSecurityCard = (props: { data: any; title: string; actionButtons: any }): JSX.Element => {
  const d = props.data;
  return (
    <Card heading={props.title} actionButtons={props.actionButtons} styles={cardStyles}>
      {Object.entries(HEADERS).map(
        ([key, label]) =>
          (d[key] || key !== 'xXSSProtection') && (
            <Row key={key} lbl={label} val={showHeader(d, key)} />
          ),
      )}
    </Card>
  );
};

export default HttpSecurityCard;
