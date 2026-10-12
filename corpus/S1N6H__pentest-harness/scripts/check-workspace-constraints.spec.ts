/** Experimental-package publication and dependency constraints. */

import { describe, expect, it } from 'vitest'
import {
  checkExperimentalDependencyIsolation,
  checkExperimentalManifest,
  type WorkspaceManifest,
} from './check-workspace-constraints.ts'

const experimental: WorkspaceManifest = {
  dir: 'packages/experimental/prototype',
  manifest: { name: '@pentest-harness/dsh-experimental-prototype', private: true },
}

describe('experimental workspace constraints', () => {
  it('requires the experimental package-name prefix', () => {
    expect(checkExperimentalManifest({
      ...experimental,
      manifest: { ...experimental.manifest, name: '@pentest-harness/dsh-prototype' },
    })).toEqual([
      '@pentest-harness/dsh-prototype: experimental package name must start with "@pentest-harness/dsh-experimental-"',
    ])
  })

  it('requires private manifests without publication metadata', () => {
    expect(checkExperimentalManifest(experimental)).toEqual([])
    expect(checkExperimentalManifest({
      ...experimental,
      manifest: { ...experimental.manifest, private: false, publishConfig: { access: 'public' } },
    })).toEqual([
      '@pentest-harness/dsh-experimental-prototype: experimental package must set "private": true',
      '@pentest-harness/dsh-experimental-prototype: experimental package must omit publishConfig',
    ])
  })

  it.each(['dependencies', 'optionalDependencies', 'peerDependencies'] as const)(
    'rejects release %s on an experimental package',
    (section) => {
      expect(checkExperimentalDependencyIsolation([experimental, {
        dir: 'packages/core/consumer',
        manifest: {
          name: '@pentest-harness/dsh-consumer',
          [section]: { '@pentest-harness/dsh-experimental-prototype': 'workspace:^' },
        },
      }])).toEqual([
        `@pentest-harness/dsh-consumer: ${section}.@pentest-harness/dsh-experimental-prototype must not reference an experimental package`,
      ])
    },
  )

  it('allows development and experimental consumers but rejects the Python release runtime', () => {
    const manifests: WorkspaceManifest[] = [experimental, {
      dir: 'packages/core/test-only',
      manifest: {
        name: '@pentest-harness/dsh-test-only',
        devDependencies: { '@pentest-harness/dsh-experimental-prototype': 'workspace:^' },
      },
    }, {
      dir: 'packages/experimental/consumer',
      manifest: {
        name: '@pentest-harness/dsh-experimental-consumer',
        dependencies: { '@pentest-harness/dsh-experimental-prototype': 'workspace:^' },
      },
    }, {
      dir: 'python/sdk-runtime',
      manifest: {
        name: '@pentest-harness/dsh-python-runtime',
        dependencies: { '@pentest-harness/dsh-experimental-prototype': 'workspace:^' },
      },
    }]

    expect(checkExperimentalDependencyIsolation(manifests)).toEqual([
      '@pentest-harness/dsh-python-runtime: dependencies.@pentest-harness/dsh-experimental-prototype must not reference an experimental package',
    ])
  })
})
