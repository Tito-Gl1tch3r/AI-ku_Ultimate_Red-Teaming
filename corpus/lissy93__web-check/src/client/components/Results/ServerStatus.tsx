import colors from 'client/styles/colors';
import { Card } from 'client/components/Form/Card';
import Row from 'client/components/Form/Row';

const cardStyles = `
span.val {
  &.up { color: ${colors.success}; }
  &.down { color: ${colors.danger}; }
}
`;

const STEPS = [
  ['dns', 'DNS Lookup'],
  ['connect', 'TCP Connect'],
  ['tls', 'TLS Handshake'],
  ['wait', 'Server Response'],
  ['download', 'Download'],
];

const ServerStatusCard = (props: { data: any; title: string; actionButtons: any }): JSX.Element => {
  const serverStatus = props.data;
  return (
    <Card heading={props.title.toString()} actionButtons={props.actionButtons} styles={cardStyles}>
      <Row lbl="" val="">
        <span className="lbl">Is Up?</span>
        {serverStatus.isUp ? (
          <span className="val up">✅ Online</span>
        ) : (
          <span className="val down">❌ Offline</span>
        )}
      </Row>
      <Row lbl="Status Code" val={serverStatus.responseCode} />
      {serverStatus.responseTime && (
        <Row lbl="Response Time" val={`${Math.round(serverStatus.responseTime)}ms`} />
      )}
      {STEPS.map(
        ([key, label]) =>
          serverStatus.timings?.[key] > 0 && (
            <Row key={key} lbl={label} val={`${serverStatus.timings[key]}ms`} />
          ),
      )}
    </Card>
  );
};

export default ServerStatusCard;
