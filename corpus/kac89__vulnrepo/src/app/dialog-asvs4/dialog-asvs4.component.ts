import { Component, OnInit, Inject, ChangeDetectionStrategy } from '@angular/core';
import { MatDialog, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { UntypedFormControl } from '@angular/forms';
import { DatePipe } from '@angular/common';
import { CurrentdateService } from '../currentdate.service';
import { CryptoUtilsService } from '../crypto-utils.service';

@Component({
  standalone: false,
  //imports: [],
  selector: 'app-dialog-asvs4',
  templateUrl: './dialog-asvs4.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrls: ['./dialog-asvs4.component.scss']
})
export class DialogAsvs4Component implements OnInit {
  selected = 'unsel';
  hide = true;
  text = '';
  selecteditems = [];
  allitems = [];
  unselected = [];
  pass = new UntypedFormControl();
  pass2 = new UntypedFormControl();
  // @ts-ignore
  constructor(public dialogRef: MatDialogRef<DialogAsvs4Component>, @Inject(MAT_DIALOG_DATA) public data: any, public datePipe: DatePipe,
  private currentdateService: CurrentdateService, private cryptoUtils: CryptoUtilsService) {

  }

  ngOnInit() {
    
    this.selecteditems = this.data[1];
    this.allitems = this.data[0];

    this.unselected = this.allitems.filter(x => !this.selecteditems.includes(x));

  }

  cancel(): void {
    this.dialogRef.close();
  }

  exportitems(): void {

    if (this.selected === 'checked') {

      // export checked
      this.exportvuln(this.selecteditems, this.pass.value, this.pass2.value);

    } else if (this.selected === 'unsel') {

      // export unselected
      this.exportvuln(this.unselected, this.pass.value, this.pass2.value);

    }
    
  }

  async exportvuln(data, pass, pass2) {

    if (pass !== pass2) {
      this.text = 'Password fields not match';
    } else {

      const toexport = data.map((res, key) => {
        const def = {
          title: 'ASVS requirement ' + res.Shortcode,
          poc: '',
          files: [],
          desc: res.Description,
          severity: 'Info',
          ref: 'https://github.com/OWASP/ASVS/raw/v5.0.0/5.0/OWASP_Application_Security_Verification_Standard_5.0.0_en.pdf',
          cvss: '',
          cvss_vector: '',
          cve: '',
          tags: [],
          bounty: [],
          date: this.currentdateService.getcurrentDate()
        };

        return def;
      });

        const json = JSON.stringify(toexport);
        // Encrypt
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




  }

  
}
