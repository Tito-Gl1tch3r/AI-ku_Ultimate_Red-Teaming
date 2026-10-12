import { PentestLogo } from '@pentest-harness/dsh-client-ui-primitives'
import type { HeroBrandMarkOwnerProps } from '@pentest-harness/dsh-client-ui-conversation/client'
import type { SidebarBrandMarkOwnerProps } from '@pentest-harness/dsh-client-ui-sidebar/client'

type OfficialBrandMarkProps = HeroBrandMarkOwnerProps & SidebarBrandMarkOwnerProps

/**
 * Render the official mark with the presentation requested by its host surface.
 * @param props - Host-supplied mark presentation.
 * @returns the pentest logo mark.
 */
export function OfficialBrandMark({ size, className }: OfficialBrandMarkProps) {
  return <PentestLogo size={size} className={className} />
}

/**
 * Render the official name artwork without its independently slotted mark.
 * The product banner (harness.jpg) carries the full "Pentest Harness"
 * wordmark at 2:1, so the name slot renders the banner at a prominent
 * lockup size instead of drawn type.
 * @returns the banner image sized to the sidebar brand-name row.
 */
export function OfficialBrandName() {
  return <PentestLogo banner size={40} />
}

