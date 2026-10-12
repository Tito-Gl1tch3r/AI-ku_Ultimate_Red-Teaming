import { Card } from 'client/components/Form/Card';
import Row, { ListRow } from 'client/components/Form/Row';

const cardStyles = `
  small {
    display: block;
    margin-top: 0.75rem;
    opacity: 0.5;
  }
`;

const titles: Record<string, string> = {
  issue: 'Allowed CAs',
  issuewild: 'Allowed CAs for Wildcards',
  iodef: 'Violation Reports',
  contactemail: 'Contact Email',
  contactphone: 'Contact Phone',
};

// Group record values by tag, with the known tags first
const groupByTag = (records: any[]) => {
  const groups: Record<string, string[]> = { issue: [], issuewild: [], iodef: [] };
  for (const { tag, value, critical } of records) {
    groups[tag] = [...(groups[tag] || []), critical ? `${value} (critical)` : value];
  }
  return Object.entries(groups).filter(([, values]) => values.length);
};

const CaaRecordsCard = (props: { data: any; title: string; actionButtons: any }): JSX.Element => {
  const { domain, records = [] } = props.data;
  return (
    <Card heading={props.title} actionButtons={props.actionButtons} styles={cardStyles}>
      <Row lbl="Domain" val={domain} />
      {groupByTag(records).map(([tag, values]) => (
        <ListRow key={tag} title={titles[tag] || tag} list={values} />
      ))}
      {!records.length && (
        <>
          <Row lbl="CAA Records" val="❌ None" />
          <small>Without CAA records, any certificate authority can issue for this domain</small>
        </>
      )}
    </Card>
  );
};

export default CaaRecordsCard;
