import { Component, OnInit, ChangeDetectionStrategy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { MatTableDataSource } from '@angular/material/table';
import { SelectionModel } from '@angular/cdk/collections';
import { MatDialog } from '@angular/material/dialog';
import { DialogAsvsExportComponent } from '../dialog-asvs-export/dialog-asvs-export.component';
import { DialogAsvsResetComponent } from '../dialog-asvs-reset/dialog-asvs-reset.component';

export interface PeriodicElement {
  Shortcode: string;
  Description: string;
  L: string;
}

type CheckedFilter = 'all' | 'checked' | 'unchecked';

@Component({
    selector: 'app-asvs',
    templateUrl: './asvs.component.html',
    styleUrls: ['./asvs.component.scss'],
    changeDetection: ChangeDetectionStrategy.Eager,
    standalone: false
})
export class AsvsComponent implements OnInit {

  displayedColumns: string[] = ['select', 'Shortcode', 'Description', 'Level'];
  dataSource = new MatTableDataSource<PeriodicElement>();
  selection = new SelectionModel<PeriodicElement>(true, []);
  asvs: any;
  asvsdata: PeriodicElement[] = [];
  selectlevel: string = 'All';
  searchQuery: string = '';
  checkedFilter: CheckedFilter = 'all';
  notes: { [shortcode: string]: string } = {};
  expandedNotes: Set<string> = new Set();
  filteredItems: PeriodicElement[] = [];
  filteredBySubchapter: { [shortcode: string]: PeriodicElement[] } = {};
  filteredByChapter: { [shortcode: string]: PeriodicElement[] } = {};
  renderedData: any;
  private storedSelection: any[] = [];

  constructor(private http: HttpClient, public dialog: MatDialog) {
    try {
      this.storedSelection = JSON.parse(localStorage.getItem('asvs') || '[]');
    } catch {
      this.storedSelection = [];
    }

    const savedLevel = localStorage.getItem('asvs-level');
    if (savedLevel === 'All' || savedLevel === 'L1' || savedLevel === 'L2' || savedLevel === 'L3') {
      this.selectlevel = savedLevel;
    }

    try {
      this.notes = JSON.parse(localStorage.getItem('asvs-notes') || '{}');
    } catch {
      this.notes = {};
    }

    this.selection.changed.subscribe(() => {
      if (this.selection.selected.length > 0) {
        localStorage.setItem('asvs', JSON.stringify(this.selection.selected));
      } else {
        localStorage.removeItem('asvs');
      }
      this.recomputeFilters();
    });
  }

  replacespace(text: string): string {
    return text.replaceAll(' ', '-');
  }

  anchorId(prefix: string, name: string): string {
    return this.replacespace(prefix + '-' + name);
  }

  owaspUrl(shortcode: string): string {
    return `https://github.com/OWASP/ASVS/search?q=${encodeURIComponent(shortcode)}&type=code`;
  }

  openasvs4dialog(): void {
    this.dialog.open(DialogAsvsExportComponent, {
      width: '440px',
      disableClose: false,
      data: [this.filteredItems, this.selection.selected, this.notes]
    });
  }

  onLevelChange(level: string): void {
    this.selectlevel = level;
    localStorage.setItem('asvs-level', level);
    this.recomputeFilters();
  }

  onSearchChange(q: string): void {
    this.searchQuery = q || '';
    this.recomputeFilters();
  }

  onCheckedFilterChange(f: CheckedFilter): void {
    this.checkedFilter = f;
    this.recomputeFilters();
  }

  toggleNote(shortcode: string): void {
    if (this.expandedNotes.has(shortcode)) {
      this.expandedNotes.delete(shortcode);
    } else {
      this.expandedNotes.add(shortcode);
    }
  }

  isNoteOpen(shortcode: string): boolean {
    return this.expandedNotes.has(shortcode);
  }

  hasNote(shortcode: string): boolean {
    const n = this.notes[shortcode];
    return !!(n && n.trim().length);
  }

  updateNote(shortcode: string, value: string): void {
    if (value && value.trim().length > 0) {
      this.notes[shortcode] = value;
    } else {
      delete this.notes[shortcode];
    }
    if (Object.keys(this.notes).length > 0) {
      localStorage.setItem('asvs-notes', JSON.stringify(this.notes));
    } else {
      localStorage.removeItem('asvs-notes');
    }
  }

  private levelMatches(item: PeriodicElement): boolean {
    if (this.selectlevel === 'All') return true;
    if (this.selectlevel === 'L1') return item.L === '1';
    if (this.selectlevel === 'L2') return item.L === '1' || item.L === '2';
    if (this.selectlevel === 'L3') return item.L === '1' || item.L === '2' || item.L === '3';
    return true;
  }

  private matchesSearch(item: PeriodicElement): boolean {
    if (!this.searchQuery) return true;
    const q = this.searchQuery.toLowerCase();
    return item.Shortcode.toLowerCase().includes(q) ||
           item.Description.toLowerCase().includes(q);
  }

  private matchesCheckedFilter(item: PeriodicElement): boolean {
    if (this.checkedFilter === 'all') return true;
    const isSel = this.selection.isSelected(item);
    return this.checkedFilter === 'checked' ? isSel : !isSel;
  }

  private filterItem(item: PeriodicElement): boolean {
    return this.levelMatches(item) && this.matchesSearch(item) && this.matchesCheckedFilter(item);
  }

  recomputeFilters(): void {
    this.filteredItems = this.asvsdata.filter(i => this.filterItem(i));
    const subMap: { [k: string]: PeriodicElement[] } = {};
    const chapMap: { [k: string]: PeriodicElement[] } = {};
    if (this.asvs) {
      for (const chapter of this.asvs.Requirements) {
        const chapItems: PeriodicElement[] = [];
        for (const sub of chapter.Items || []) {
          const subItems = (sub.Items || []).filter((i: PeriodicElement) => this.filterItem(i));
          subMap[sub.Shortcode] = subItems;
          chapItems.push(...subItems);
        }
        chapMap[chapter.Shortcode] = chapItems;
      }
    }
    this.filteredBySubchapter = subMap;
    this.filteredByChapter = chapMap;
  }

  itemsForSub(shortcode: string): PeriodicElement[] {
    return this.filteredBySubchapter[shortcode] || [];
  }

  itemsForChapter(chapterShortcode: string): PeriodicElement[] {
    return this.filteredByChapter[chapterShortcode] || [];
  }

  totalCount(): number { return this.filteredItems.length; }

  checkedCount(): number {
    return this.filteredItems.filter(i => this.selection.isSelected(i)).length;
  }

  percent(): number {
    const total = this.totalCount();
    if (!total) return 0;
    return (this.checkedCount() / total) * 100;
  }

  isAllSelectedSub(shortcode: string): boolean {
    const items = this.itemsForSub(shortcode);
    if (!items.length) return false;
    return items.every(i => this.selection.isSelected(i));
  }

  isAnySelectedSub(shortcode: string): boolean {
    return this.itemsForSub(shortcode).some(i => this.selection.isSelected(i));
  }

  toggleSub(shortcode: string): void {
    const items = this.itemsForSub(shortcode);
    if (!items.length) return;
    if (this.isAllSelectedSub(shortcode)) {
      this.selection.deselect(...items);
    } else {
      this.selection.select(...items);
    }
  }

  isAllSelectedChapter(chapterShortcode: string): boolean {
    const items = this.itemsForChapter(chapterShortcode);
    if (!items.length) return false;
    return items.every(i => this.selection.isSelected(i));
  }

  isAnySelectedChapter(chapterShortcode: string): boolean {
    return this.itemsForChapter(chapterShortcode).some(i => this.selection.isSelected(i));
  }

  toggleChapter(chapterShortcode: string): void {
    const items = this.itemsForChapter(chapterShortcode);
    if (!items.length) return;
    if (this.isAllSelectedChapter(chapterShortcode)) {
      this.selection.deselect(...items);
    } else {
      this.selection.select(...items);
    }
  }

  chapterCheckedCount(chapterShortcode: string): number {
    return this.itemsForChapter(chapterShortcode).filter(i => this.selection.isSelected(i)).length;
  }

  chapterTotalCount(chapterShortcode: string): number {
    return this.itemsForChapter(chapterShortcode).length;
  }

  chapterPercent(chapterShortcode: string): number {
    const total = this.chapterTotalCount(chapterShortcode);
    if (!total) return 0;
    return (this.chapterCheckedCount(chapterShortcode) / total) * 100;
  }

  handleRowKey(event: KeyboardEvent, row: PeriodicElement, preventDefault: boolean): void {
    if (event.target !== event.currentTarget) return;
    if (preventDefault) event.preventDefault();
    this.selection.toggle(row);
  }

  private restoreSelection(): void {
    if (!Array.isArray(this.storedSelection) || !this.storedSelection.length) return;
    const codes = new Set(this.storedSelection.map((s: any) => s && s.Shortcode).filter(Boolean));
    const toSelect = this.asvsdata.filter(r => codes.has(r.Shortcode));
    if (toSelect.length) {
      this.selection.select(...toSelect);
    }
  }

  resetselected(): void {
    const dialogRef = this.dialog.open(DialogAsvsResetComponent, {
      width: '420px',
      disableClose: false
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result === true) {
        this.selection.clear();
        this.notes = {};
        this.expandedNotes.clear();
        localStorage.removeItem('asvs');
        localStorage.removeItem('asvs-notes');
      }
    });
  }

  ngOnInit(): void {
    this.dataSource.connect().subscribe(d => this.renderedData = d);
    this.http.get<any>('/assets/OWASP_Application_Security_Verification_Standard_5.0.0_en.json?v=' + +new Date()).subscribe(res => {
      this.asvs = res;

      for (const item of this.asvs.Requirements) {
        for (const subitem of item.Items) {
          this.asvsdata = this.asvsdata.concat(subitem.Items);
        }
      }

      this.dataSource.data = this.asvsdata;
      this.recomputeFilters();
      this.restoreSelection();
    });
  }
}
