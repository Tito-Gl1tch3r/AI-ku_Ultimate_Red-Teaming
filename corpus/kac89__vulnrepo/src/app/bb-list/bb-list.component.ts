import { Component, OnInit, ViewChild, ChangeDetectionStrategy } from '@angular/core';
import {MatTableDataSource} from '@angular/material/table';
import { HttpClient } from '@angular/common/http';
import {MatPaginator} from '@angular/material/paginator';

@Component({
  selector: 'app-bb-list',
  standalone: false,
  templateUrl: './bb-list.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './bb-list.component.scss'
})
export class BbListComponent implements OnInit  {
  static readonly DOMAIN_PREVIEW = 6;

  ELEMENT_DATA:any = [];
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  displayedColumns: string[] = ['name', 'bounty', 'domains'];
  dataSource = new MatTableDataSource(this.ELEMENT_DATA);
  isLoading = true;
  expandedDomains = new Set<string>();

  constructor(private http: HttpClient) {
  }

  ngOnInit() {

    this.http.get<any>('/assets/chaos-bugbounty-list.json?v=' + + new Date()).subscribe({
      next: res => {
        if (res && res['programs']) {
          this.dataSource = new MatTableDataSource(res['programs']);
          this.dataSource.paginator = this.paginator;
        }
        this.isLoading = false;
      },
      error: () => { this.isLoading = false; }
    });

  }

  applyFilter(event: Event) {
    const filterValue = (event.target as HTMLInputElement).value;
    this.dataSource.filter = filterValue.trim().toLowerCase();
  }

  clearFilter(input: HTMLInputElement) {
    input.value = '';
    this.dataSource.filter = '';
    input.focus();
  }

  avatarHue(name: string): number {
    let h = 0;
    const n = name || '';
    for (let i = 0; i < n.length; i++) {
      h = (h * 31 + n.charCodeAt(i)) >>> 0;
    }
    return h % 360;
  }

  domainsPreview(domains: string[] = [], name: string): string[] {
    if (this.expandedDomains.has(name) || domains.length <= BbListComponent.DOMAIN_PREVIEW) {
      return domains;
    }
    return domains.slice(0, BbListComponent.DOMAIN_PREVIEW);
  }

  canToggle(domains: string[] = []): boolean {
    return (domains?.length || 0) > BbListComponent.DOMAIN_PREVIEW;
  }

  remainingDomains(domains: string[] = []): number {
    return Math.max(0, domains.length - BbListComponent.DOMAIN_PREVIEW);
  }

  toggleDomains(name: string) {
    if (this.expandedDomains.has(name)) {
      this.expandedDomains.delete(name);
    } else {
      this.expandedDomains.add(name);
    }
  }
}
