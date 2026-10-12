import { describe, expect, it } from 'vitest'
import {
  parseIssueLocation,
  buildIssueRoute,
  isGeneralInformationLocation,
  resolveFindingForLocation
} from '@/services/audit-qa-navigation'

describe('audit-qa-navigation', () => {
  it('parses finding locations, discarding any field suffix', () => {
    expect(parseIssueLocation('finding:SQL Injection/description')).toEqual({
      type: 'finding',
      findingId: null,
      findingTitle: 'SQL Injection'
    })
  })

  it('parses finding locations with an embedded finding id', () => {
    expect(parseIssueLocation('finding:507f1f77bcf86cd799439011::SQL Injection/description')).toEqual({
      type: 'finding',
      findingId: '507f1f77bcf86cd799439011',
      findingTitle: 'SQL Injection'
    })
  })

  it('parses finding locations with a custom field label suffix the same way', () => {
    expect(parseIssueLocation('finding:507f1f77bcf86cd799439011::SQL Injection/Business Impact')).toEqual({
      type: 'finding',
      findingId: '507f1f77bcf86cd799439011',
      findingTitle: 'SQL Injection'
    })
  })

  it('parses a finding location with no field suffix at all', () => {
    expect(parseIssueLocation('finding:507f1f77bcf86cd799439011::SQL Injection')).toEqual({
      type: 'finding',
      findingId: '507f1f77bcf86cd799439011',
      findingTitle: 'SQL Injection'
    })
  })

  it('builds finding routes', () => {
    const parsed = parseIssueLocation('finding:SQL Injection/description')
    const route = buildIssueRoute('audit-1', parsed, {
      findings: [{ _id: 'finding-1', title: 'SQL Injection' }]
    })

    expect(route).toEqual({ path: '/audits/audit-1/findings/finding-1' })
  })

  it('resolves duplicate-titled findings by embedded id instead of the first title match', () => {
    const parsed = parseIssueLocation('finding:507f1f77bcf86cd799439012::SQL Injection/description')
    const route = buildIssueRoute('audit-1', parsed, {
      findings: [
        { _id: '507f1f77bcf86cd799439011', title: 'SQL Injection' },
        { _id: '507f1f77bcf86cd799439012', title: 'SQL Injection' }
      ]
    })

    expect(route).toEqual({ path: '/audits/audit-1/findings/507f1f77bcf86cd799439012' })
  })

  it('falls back to title matching when the embedded id no longer resolves', () => {
    const parsed = parseIssueLocation('finding:507f1f77bcf86cd799439099::SQL Injection/description')
    const route = buildIssueRoute('audit-1', parsed, {
      findings: [{ _id: 'finding-1', title: 'SQL Injection' }]
    })

    expect(route).toEqual({ path: '/audits/audit-1/findings/finding-1' })
  })

  it('falls back to the general page when a finding no longer exists', () => {
    const parsed = parseIssueLocation('finding:Deleted finding/description')
    const route = buildIssueRoute('audit-1', parsed, { findings: [] })

    expect(route).toEqual({ path: '/audits/audit-1/general' })
  })

  it('builds section routes from section names', () => {
    const parsed = parseIssueLocation('section:Executive Summary')
    const route = buildIssueRoute('audit-1', parsed, {
      sections: [{ _id: 'section-1', name: 'Executive Summary' }]
    })

    expect(route).toEqual({ path: '/audits/audit-1/sections/section-1' })
  })

  it('builds the general/network page routes', () => {
    expect(buildIssueRoute('audit-1', parseIssueLocation('general'))).toEqual({ path: '/audits/audit-1/general' })
    expect(buildIssueRoute('audit-1', parseIssueLocation('network'))).toEqual({ path: '/audits/audit-1/network' })
  })

  it('groups general information field paths together', () => {
    expect(isGeneralInformationLocation('general')).toBe(true)
    expect(isGeneralInformationLocation('general/Business Impact')).toBe(true)
    expect(isGeneralInformationLocation('field:client')).toBe(true)
    expect(isGeneralInformationLocation('field path: client')).toBe(true)
    expect(isGeneralInformationLocation('field path: finding.references')).toBe(false)
    expect(isGeneralInformationLocation('field:category')).toBe(false)
    expect(isGeneralInformationLocation('section:Executive Summary')).toBe(false)
    expect(parseIssueLocation('field:client')).toEqual({
      type: 'page',
      page: 'general'
    })
  })

  it('resolves a finding by embedded id, ignoring a stale/corrupted title', () => {
    const parsed = parseIssueLocation('finding:507f1f77bcf86cd799439011::SQL Injection/Business Impact')
    const finding = resolveFindingForLocation(parsed, [
      { _id: '507f1f77bcf86cd799439011', title: 'SQL Injection' }
    ])

    expect(finding).toEqual({ _id: '507f1f77bcf86cd799439011', title: 'SQL Injection' })
  })

  it('resolveFindingForLocation returns null for non-finding locations', () => {
    expect(resolveFindingForLocation(parseIssueLocation('general'), [{ _id: '1', title: 'x' }])).toBe(null)
    expect(resolveFindingForLocation(parseIssueLocation('section:Executive Summary'), [{ _id: '1', title: 'x' }])).toBe(null)
  })
})
