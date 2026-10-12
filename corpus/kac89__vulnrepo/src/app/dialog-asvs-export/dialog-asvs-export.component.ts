import { Component, OnInit, Inject, ChangeDetectionStrategy } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { UntypedFormControl } from '@angular/forms';
import { DatePipe } from '@angular/common';
import { MatSnackBar } from '@angular/material/snack-bar';
import { CurrentdateService } from '../currentdate.service';
import { CryptoUtilsService } from '../crypto-utils.service';
import { KeyVaultService } from '../key-vault.service';
import { IndexeddbService } from '../indexeddb.service';

type ExportSubset = 'checked' | 'unsel';
type ExportDestination = 'file' | 'report';

interface UnlockedReport {
  report_id: string;
  report_name: string;
  report_createdate: any;
  orderKey: any;
}

@Component({
  selector: 'app-dialog-asvs-export',
  templateUrl: './dialog-asvs-export.component.html',
  styleUrls: ['./dialog-asvs-export.component.scss'],
  changeDetection: ChangeDetectionStrategy.Eager,
  standalone: false
})
export class DialogAsvsExportComponent implements OnInit {
  selected: ExportSubset = 'unsel';
  destination: ExportDestination = 'file';
  hide = true;
  text = '';
  saving = false;
  loadingReports = true;
  selecteditems: any[] = [];
  allitems: any[] = [];
  unselected: any[] = [];
  notes: { [shortcode: string]: string } = {};
  unlockedReports: UnlockedReport[] = [];
  selectedReportId = '';
  pass = new UntypedFormControl();
  pass2 = new UntypedFormControl();

  // @ts-ignore
  constructor(
    public dialogRef: MatDialogRef<DialogAsvsExportComponent>,
    @Inject(MAT_DIALOG_DATA) public data: any,
    public datePipe: DatePipe,
    private currentdateService: CurrentdateService,
    private cryptoUtils: CryptoUtilsService,
    private keyVault: KeyVaultService,
    private indexeddbService: IndexeddbService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.selecteditems = this.data[1];
    this.allitems = this.data[0];
    this.notes = this.data[2] || {};
    this.unselected = this.allitems.filter(x => !this.selecteditems.includes(x));
    this.loadUnlockedReports();
  }

  private async loadUnlockedReports(): Promise<void> {
    const ids = this.keyVault.openReportIds();
    const results: UnlockedReport[] = [];
    for (const id of ids) {
      try {
        const meta = await this.indexeddbService.checkifreportexist(id);
        if (!meta) continue;
        const keyInfo = await this.indexeddbService.getkeybyReportID(id);
        if (!keyInfo || keyInfo.NotFound === 'NOOK') continue;
        results.push({
          report_id: meta.report_id,
          report_name: meta.report_name,
          report_createdate: meta.report_createdate,
          orderKey: keyInfo.key
        });
      } catch {
        // ignore one bad record
      }
    }
    this.unlockedReports = results;
    this.loadingReports = false;
    if (results.length && !this.selectedReportId) {
      this.selectedReportId = results[0].report_id;
    }
    if (!results.length && this.destination === 'report') {
      this.destination = 'file';
    }
  }

  setDestination(d: ExportDestination): void {
    if (d === 'report' && !this.unlockedReports.length) return;
    this.destination = d;
    this.text = '';
  }

  get sourceItems(): any[] {
    return this.selected === 'checked' ? this.selecteditems : this.unselected;
  }

  private buildIssues(data: any[]): any[] {
    const now = this.currentdateService.getcurrentDate();
    return data.map((res) => ({
      title: 'ASVS requirement ' + res.Shortcode,
      poc: this.notes[res.Shortcode] || '',
      files: [],
      desc: res.Description,
      severity: 'Info',
      ref: 'https://github.com/OWASP/ASVS/raw/v5.0.0/5.0/OWASP_Application_Security_Verification_Standard_5.0.0_en.pdf',
      cvss: '',
      cvss_vector: '',
      cve: '',
      tags: [],
      bounty: [],
      date: now
    }));
  }

  cancel(): void {
    this.dialogRef.close();
  }

  primaryAction(): void {
    if (this.saving) return;
    this.text = '';
    if (this.destination === 'file') {
      this.exportToFile();
    } else {
      this.appendToReport();
    }
  }

  private async exportToFile(): Promise<void> {
    const pass = this.pass.value;
    const pass2 = this.pass2.value;
    if (!pass || !pass2) {
      this.text = 'Encryption key is required';
      return;
    }
    if (pass !== pass2) {
      this.text = 'Password fields not match';
      return;
    }

    const toexport = this.buildIssues(this.sourceItems);
    const json = JSON.stringify(toexport);
    const ciphertext = await this.cryptoUtils.encrypt(json, pass);

    const element = document.createElement('a');
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(ciphertext));
    element.setAttribute('download', 'Vulnrepo asvs export.vuln');
    element.style.display = 'none';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);

    this.dialogRef.close();
  }

  private async appendToReport(): Promise<void> {
    if (!this.selectedReportId) {
      this.text = 'Select a report';
      return;
    }
    const rep = this.unlockedReports.find(r => r.report_id === this.selectedReportId);
    if (!rep) {
      this.text = 'Selected report is no longer available';
      return;
    }
    const pass = this.keyVault.get(this.selectedReportId);
    if (!pass) {
      this.text = 'Report key not available — please reopen the report';
      return;
    }

    const items = this.sourceItems;
    if (!items.length) {
      this.text = 'No requirements to add';
      return;
    }

    this.saving = true;
    try {
      const meta = await this.indexeddbService.checkifreportexist(this.selectedReportId);
      if (!meta || !meta.encrypted_data) {
        this.text = 'Report not found in local storage';
        return;
      }

      const plaintext = await this.cryptoUtils.decrypt(meta.encrypted_data.toString(), pass);
      const report = JSON.parse(plaintext);

      if (!Array.isArray(report.report_vulns)) report.report_vulns = [];
      if (!Array.isArray(report.report_changelog)) report.report_changelog = [];
      if (typeof report.report_version !== 'number') report.report_version = 0;

      report.report_version = report.report_version + 1;

      const issues = this.buildIssues(items);
      issues.forEach(i => report.report_vulns.push(i));

      report.report_changelog.push({
        date: Date.now(),
        desc: 'Added ' + issues.length + ' ASVS requirement' + (issues.length === 1 ? '' : 's'),
        version: report.report_version
      });

      const result = await this.indexeddbService.prepareupdatereport(
        report,
        pass,
        rep.report_id,
        rep.report_name,
        rep.report_createdate,
        rep.orderKey
      );

      if (!result) {
        this.text = 'Save failed';
        return;
      }

      this.snackBar.open(
        `Added ${issues.length} requirement${issues.length === 1 ? '' : 's'} to "${rep.report_name}"`,
        'OK',
        { duration: 3500, panelClass: ['notify-snackbar-success'] }
      );
      this.dialogRef.close({ added: issues.length, reportId: rep.report_id });
    } catch (err) {
      console.error(err);
      this.text = 'Failed to update report';
    } finally {
      this.saving = false;
    }
  }

  // Kept for any external caller still using the old name
  exportitems(): void {
    this.primaryAction();
  }
}
