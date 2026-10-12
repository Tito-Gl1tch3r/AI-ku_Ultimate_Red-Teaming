import { Component, Inject, Optional, ChangeDetectionStrategy } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import DOMPurify from 'dompurify';

interface ResetDialogData {
  title?: string;
  bodyHtml?: string;
}

@Component({
  selector: 'app-dialog-asvs-reset',
  templateUrl: './dialog-asvs-reset.component.html',
  styleUrls: ['./dialog-asvs-reset.component.scss'],
  changeDetection: ChangeDetectionStrategy.Eager,
  standalone: false
})
export class DialogAsvsResetComponent {
  title: string;
  bodyHtml: string;

  constructor(
    public dialogRef: MatDialogRef<DialogAsvsResetComponent>,
    @Optional() @Inject(MAT_DIALOG_DATA) data: ResetDialogData
  ) {
    this.title = data?.title || 'Reset ASVS checklist';
    const rawBody = data?.bodyHtml
      || 'All selected requirements <strong class="highlight">and notes</strong> will be removed from your local storage.';
    this.bodyHtml = DOMPurify.sanitize(rawBody);
  }

  cancel(): void {
    this.dialogRef.close(false);
  }

  confirm(): void {
    this.dialogRef.close(true);
  }
}
