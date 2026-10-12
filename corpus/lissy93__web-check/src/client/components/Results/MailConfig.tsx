import { Card } from 'client/components/Form/Card';
import Row, { Details } from 'client/components/Form/Row';
import Heading from 'client/components/Form/Heading';
import colors from 'client/styles/colors';
import {
  checkSpf,
  checkDmarc,
  checkDkim,
  checkMtaSts,
  findRecords,
  mxHosts,
  sendsNoMail,
  type MailData,
} from 'client/analysis/rules/mail-config';

const cardStyles = `summary { margin: 0.5rem 0; }`;

const dkimStatus = (d: MailData) => {
  if (!d.dkim?.length) return sendsNoMail(d) ? 'Not needed' : 'Not found';
  return checkDkim(d).severity !== 'issue';
};

// MTA-STS as a tick or cross, or its mode when not enforced yet
const mtaStsStatus = (d: MailData) => {
  if (!d.mtaSts) return 'Not set up';
  const { severity } = checkMtaSts(d)!;
  return severity === 'info' ? `Mode: ${d.mtaSts.mode}` : severity === 'pass';
};

const MailConfigCard = (props: { data: any; title: string; actionButtons: any }): JSX.Element => {
  const mailServer = props.data;
  const txt = mailServer.txtRecords || [];
  const senders = (findRecords(txt, 'v=spf1')[0] || '')
    .split(' ')
    .map((term) => term.split('include:')[1])
    .filter(Boolean);
  return (
    <Card heading={props.title} actionButtons={props.actionButtons} styles={cardStyles}>
      <Heading as="h3" color={colors.primary} size="small">
        Mail Security Checklist
      </Heading>
      <Row lbl="SPF" val={checkSpf(mailServer).severity === 'pass'} />
      <Row lbl="DKIM" val={dkimStatus(mailServer)} />
      <Row lbl="DMARC" val={checkDmarc(mailServer).severity === 'pass'} />
      <Row lbl="BIMI" val={findRecords(txt, 'v=BIMI1').length > 0 || 'Not set up'} />
      {mxHosts(mailServer).length > 0 && (
        <>
          <Row lbl="MTA-STS" val={mtaStsStatus(mailServer)} />
          <Row lbl="TLS-RPT" val={findRecords(txt, 'v=TLSRPTv1').length > 0 || 'Not set up'} />
          <Row lbl="DANE" val={mailServer.dane?.length > 0 || 'Not set up'} />
        </>
      )}

      {mailServer.mxRecords?.length > 0 && (
        <Heading as="h3" color={colors.primary} size="small">
          MX Records
        </Heading>
      )}
      {mailServer.mxRecords?.map((record: any, index: number) => (
        <Row lbl="" val="" key={index}>
          <span>{record.exchange || 'Null MX, accepts no mail'}</span>
          <span>{record.exchange && `Priority: ${record.priority}`}</span>
        </Row>
      ))}
      {mailServer.mailServices?.length > 0 && (
        <Heading as="h3" color={colors.primary} size="small">
          External Mail Services
        </Heading>
      )}
      {mailServer.mailServices?.map((service: any, index: number) => (
        <Row lbl={service.provider} title={service.value} val="" key={index} />
      ))}

      {senders.length > 0 && (
        <Heading as="h3" color={colors.primary} size="small">
          Authorised Senders
        </Heading>
      )}
      {senders.map((sender) => (
        <Row lbl="" val="" key={sender}>
          <span>{sender}</span>
        </Row>
      ))}

      {txt.length > 0 && (
        <Details>
          <summary>
            <Heading as="h3" color={colors.primary} size="small" inline>
              Mail-related TXT Records ({txt.length})
            </Heading>
          </summary>
          {txt.map((record: string[], index: number) => (
            <Row lbl="" val="" key={index}>
              <span>{record.join('')}</span>
            </Row>
          ))}
        </Details>
      )}
    </Card>
  );
};

export default MailConfigCard;
