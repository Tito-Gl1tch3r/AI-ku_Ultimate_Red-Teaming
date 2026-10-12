import { Component, OnInit, ChangeDetectionStrategy } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { DialogAsvsResetComponent } from '../dialog-asvs-reset/dialog-asvs-reset.component';

interface TbhmItem {
  id: string;
  text: string;
}

interface TbhmSubsection {
  title: string;
  items: TbhmItem[];
}

interface TbhmSection {
  id: string;
  title: string;
  icon: string;
  items?: TbhmItem[];
  subsections?: TbhmSubsection[];
}

type CheckedFilter = 'all' | 'checked' | 'unchecked';

@Component({
  standalone: false,
  selector: 'app-tbhm',
  templateUrl: './tbhm.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrls: ['./tbhm.component.scss']
})
export class TbhmComponent implements OnInit {

  sections: TbhmSection[] = [
    {
      id: 'recon',
      title: 'App Recon & Analysis',
      icon: 'travel_explore',
      items: [
        { id: 'r1', text: 'Map visible content (Manually)' },
        { id: 'r2', text: 'Discover hidden & default content (Directory/File Bruteforce)' },
        { id: 'r3', text: 'Test for debug parameters' },
        { id: 'r4', text: 'Identify data entry points (Discover Dynamic Content in Burp Pro)' },
        { id: 'r5', text: 'Identify the technologies used (Wappalyzer or similar)' },
        { id: 'r6', text: 'Research existing vulnerabilities in technology (Google++)' },
        { id: 'r7', text: 'Gather wordlists for specific technology (Assetnote ones are excellent)' },
        { id: 'r8', text: 'Map the attack surface automatically (Spider)' },
        { id: 'r9', text: 'Identify all JavaScript files for later analysis (in your proxy)' },
      ]
    },
    {
      id: 'access',
      title: 'Test Handling of Access',
      icon: 'lock_open',
      subsections: [
        {
          title: 'Authentication',
          items: [
            { id: 'r10', text: 'Test password quality rules' },
            { id: 'r11', text: 'Test for username enumeration' },
            { id: 'r12', text: 'Test resilience to password guessing' },
            { id: 'r13', text: 'Test any account recovery function' },
            { id: 'r14', text: 'Test any "remember me" function' },
            { id: 'r15', text: 'Test any impersonation function' },
            { id: 'r16', text: 'Test username uniqueness' },
            { id: 'r17', text: 'Check for unsafe distribution of credentials' },
            { id: 'r18', text: 'Test for fail-open conditions' },
            { id: 'r19', text: 'Test any multi-stage mechanisms' },
          ]
        },
        {
          title: 'Session Handling',
          items: [
            { id: 'r20', text: 'Test tokens for meaning' },
            { id: 'r21', text: 'Test tokens for predictability' },
            { id: 'r22', text: 'Check for insecure transmission of tokens' },
            { id: 'r23', text: 'Check for disclosure of tokens in logs' },
            { id: 'r24', text: 'Check mapping of tokens to sessions' },
            { id: 'r25', text: 'Check session termination' },
            { id: 'r26', text: 'Check for session fixation' },
            { id: 'r27', text: 'Check for cross-site request forgery' },
            { id: 'r28', text: 'Check cookie scope' },
          ]
        },
        {
          title: 'Access Controls',
          items: [
            { id: 'r29', text: 'Understand the access control requirements' },
            { id: 'r30', text: 'Test effectiveness of controls, using multiple accounts if possible' },
            { id: 'r31', text: 'Test for insecure access control methods (request parameters, Referer header, etc)' },
          ]
        }
      ]
    },
    {
      id: 'input',
      title: 'Test Handling of Input',
      icon: 'bug_report',
      items: [
        { id: 'r32', text: 'Fuzz all request parameters' },
        { id: 'r33', text: 'Test for SQL injection' },
        { id: 'r34', text: 'Identify all reflected data' },
        { id: 'r35', text: 'Test for reflected XSS' },
        { id: 'r36', text: 'Test for HTTP header injection' },
        { id: 'r37', text: 'Test for arbitrary redirection' },
        { id: 'r38', text: 'Test for stored attacks' },
        { id: 'r39', text: 'Test for OS command injection' },
        { id: 'r40', text: 'Test for path traversal' },
        { id: 'r41', text: 'Test for script injection' },
        { id: 'r42', text: 'Test for file inclusion' },
        { id: 'r43', text: 'Test for SMTP injection' },
        { id: 'r44', text: 'Test for native software flaws (buffer overflow, integer bugs, format strings)' },
        { id: 'r45', text: 'Test for SOAP injection' },
        { id: 'r46', text: 'Test for LDAP injection' },
        { id: 'r47', text: 'Test for XPath injection' },
        { id: 'r48', text: 'Test for SSRF and HTTP redirects in all redirecting parameters' },
      ]
    },
    {
      id: 'logic',
      title: 'Test Application Logic',
      icon: 'account_tree',
      items: [
        { id: 'r49', text: 'Identify the logic attack surface' },
        { id: 'r50', text: 'Test transmission of data via the client' },
        { id: 'r51', text: 'Test for reliance on client-side input validation' },
        { id: 'r52', text: 'Test any thick-client components (Java, ActiveX, Flash)' },
        { id: 'r53', text: 'Test multi-stage processes for logic flaws' },
        { id: 'r54', text: 'Test handling of incomplete input' },
        { id: 'r55', text: 'Test trust boundaries' },
        { id: 'r56', text: 'Test transaction logic' },
      ]
    },
    {
      id: 'hosting',
      title: 'Assess Application Hosting',
      icon: 'dns',
      items: [
        { id: 'r57', text: 'Test segregation in shared infrastructures' },
        { id: 'r58', text: 'Test segregation between ASP-hosted applications' },
        { id: 'r59', text: 'Test for web server vulnerabilities' },
        { id: 'r60', text: 'Default credentials' },
        { id: 'r61', text: 'Default content' },
        { id: 'r62', text: 'Dangerous HTTP methods' },
        { id: 'r63', text: 'Proxy functionality' },
        { id: 'r64', text: 'Virtual hosting mis-configuration' },
        { id: 'r65', text: 'Bugs in web server software' },
      ]
    },
    {
      id: 'misc',
      title: 'Miscellaneous Tests',
      icon: 'more_horiz',
      items: [
        { id: 'r66', text: 'Check for DOM-based attacks' },
        { id: 'r67', text: 'Check for frame injection' },
        { id: 'r68', text: 'Check for local privacy vulnerabilities' },
        { id: 'r69', text: 'Persistent cookies' },
        { id: 'r70', text: 'Caching' },
        { id: 'r71', text: 'Sensitive data in URL parameters' },
        { id: 'r72', text: 'Forms with autocomplete enabled' },
        { id: 'r73', text: 'Follow up any information leakage' },
        { id: 'r74', text: 'Check for weak SSL ciphers' },
      ]
    }
  ];

  checked: { [id: string]: boolean } = {};
  notes: { [id: string]: string } = {};
  expandedNotes: Set<string> = new Set();
  searchQuery: string = '';
  checkedFilter: CheckedFilter = 'all';

  constructor(public dialog: MatDialog) {}

  ngOnInit() {
    try {
      const stored = JSON.parse(localStorage.getItem('tbhm') || '{}');
      const cleaned: { [id: string]: boolean } = {};
      for (const key of Object.keys(stored)) {
        if (stored[key] === true) cleaned[key] = true;
      }
      this.checked = cleaned;
    } catch {
      this.checked = {};
    }

    try {
      this.notes = JSON.parse(localStorage.getItem('tbhm-notes') || '{}');
    } catch {
      this.notes = {};
    }
  }

  allItems(): TbhmItem[] {
    const result: TbhmItem[] = [];
    for (const sec of this.sections) {
      result.push(...this.sectionItems(sec));
    }
    return result;
  }

  sectionItems(sec: TbhmSection): TbhmItem[] {
    const result: TbhmItem[] = [];
    if (sec.items) result.push(...sec.items);
    if (sec.subsections) {
      for (const sub of sec.subsections) result.push(...sub.items);
    }
    return result;
  }

  matchesItem(item: TbhmItem): boolean {
    if (this.searchQuery) {
      const q = this.searchQuery.toLowerCase();
      if (!item.text.toLowerCase().includes(q) && !item.id.toLowerCase().includes(q)) {
        return false;
      }
    }
    if (this.checkedFilter === 'checked') return !!this.checked[item.id];
    if (this.checkedFilter === 'unchecked') return !this.checked[item.id];
    return true;
  }

  filteredItems(items: TbhmItem[]): TbhmItem[] {
    return items.filter(i => this.matchesItem(i));
  }

  sectionHasFilteredItems(sec: TbhmSection): boolean {
    return this.sectionItems(sec).some(i => this.matchesItem(i));
  }

  totalItems(): number {
    return this.allItems().length;
  }

  selectedCount(): number {
    return this.allItems().filter(i => this.checked[i.id]).length;
  }

  filteredTotal(): number {
    return this.allItems().filter(i => this.matchesItem(i)).length;
  }

  percent(): number {
    const total = this.totalItems();
    if (!total) return 0;
    return (this.selectedCount() / total) * 100;
  }

  sectionChecked(sec: TbhmSection): number {
    return this.sectionItems(sec).filter(i => this.checked[i.id]).length;
  }

  sectionTotal(sec: TbhmSection): number {
    return this.sectionItems(sec).length;
  }

  sectionPercent(sec: TbhmSection): number {
    const total = this.sectionTotal(sec);
    if (!total) return 0;
    return (this.sectionChecked(sec) / total) * 100;
  }

  isAllSelectedSection(sec: TbhmSection): boolean {
    const items = this.sectionItems(sec);
    if (!items.length) return false;
    return items.every(i => this.checked[i.id]);
  }

  isAnySelectedSection(sec: TbhmSection): boolean {
    return this.sectionItems(sec).some(i => this.checked[i.id]);
  }

  toggleSection(sec: TbhmSection): void {
    const items = this.sectionItems(sec);
    if (!items.length) return;
    const all = this.isAllSelectedSection(sec);
    for (const item of items) {
      if (all) delete this.checked[item.id];
      else this.checked[item.id] = true;
    }
    this.persistChecked();
  }

  isAllSelectedSub(sub: TbhmSubsection): boolean {
    if (!sub.items.length) return false;
    return sub.items.every(i => this.checked[i.id]);
  }

  isAnySelectedSub(sub: TbhmSubsection): boolean {
    return sub.items.some(i => this.checked[i.id]);
  }

  toggleSub(sub: TbhmSubsection): void {
    const all = this.isAllSelectedSub(sub);
    for (const item of sub.items) {
      if (all) delete this.checked[item.id];
      else this.checked[item.id] = true;
    }
    this.persistChecked();
  }

  toggleItem(item: TbhmItem): void {
    if (this.checked[item.id]) delete this.checked[item.id];
    else this.checked[item.id] = true;
    this.persistChecked();
  }

  isChecked(id: string): boolean {
    return !!this.checked[id];
  }

  handleItemKey(event: KeyboardEvent, item: TbhmItem, preventDefault: boolean): void {
    if (event.target !== event.currentTarget) return;
    if (preventDefault) event.preventDefault();
    this.toggleItem(item);
  }

  private persistChecked(): void {
    if (Object.keys(this.checked).length > 0) {
      localStorage.setItem('tbhm', JSON.stringify(this.checked));
    } else {
      localStorage.removeItem('tbhm');
    }
  }

  private persistNotes(): void {
    if (Object.keys(this.notes).length > 0) {
      localStorage.setItem('tbhm-notes', JSON.stringify(this.notes));
    } else {
      localStorage.removeItem('tbhm-notes');
    }
  }

  onSearchChange(q: string): void {
    this.searchQuery = q || '';
  }

  onCheckedFilterChange(f: CheckedFilter): void {
    this.checkedFilter = f;
  }

  toggleNote(id: string): void {
    if (this.expandedNotes.has(id)) this.expandedNotes.delete(id);
    else this.expandedNotes.add(id);
  }

  isNoteOpen(id: string): boolean {
    return this.expandedNotes.has(id);
  }

  hasNote(id: string): boolean {
    const n = this.notes[id];
    return !!(n && n.trim().length);
  }

  updateNote(id: string, value: string): void {
    if (value && value.trim().length > 0) this.notes[id] = value;
    else delete this.notes[id];
    this.persistNotes();
  }

  anchorId(prefix: string): string {
    return 'tbhm-' + prefix;
  }

  resetselected(): void {
    const dialogRef = this.dialog.open(DialogAsvsResetComponent, {
      width: '420px',
      disableClose: false,
      data: {
        title: 'Reset TBHM checklist',
        bodyHtml: 'All selected checks <strong class="highlight">and notes</strong> will be removed from your local storage.'
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result === true) {
        this.checked = {};
        this.notes = {};
        this.expandedNotes.clear();
        localStorage.removeItem('tbhm');
        localStorage.removeItem('tbhm-notes');
      }
    });
  }
}
