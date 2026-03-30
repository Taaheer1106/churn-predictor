import { Component, signal } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDividerModule } from '@angular/material/divider';
import { PredictService, PredictionResult } from '../predict.service';
import { ThemeService } from '../theme.service';
import jsPDF from 'jspdf';

@Component({
  selector: 'app-predict',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatDividerModule,
  ],
  templateUrl: './predict.component.html',
  styleUrl: './predict.component.scss'
})
export class PredictComponent {

  form: FormGroup;

  // Signals — Angular automatically updates the UI when these change
  result    = signal<PredictionResult | null>(null);
  loading   = signal(false);
  errorMsg  = signal('');

  constructor(private fb: FormBuilder, private predictService: PredictService, public theme: ThemeService) {
    this.form = this.fb.group({
      customer_name:    [''],
      gender:           ['', Validators.required],
      SeniorCitizen:    ['', Validators.required],
      Partner:          ['', Validators.required],
      Dependents:       ['', Validators.required],
      tenure:           ['', [Validators.required, Validators.min(0)]],
      PhoneService:     ['', Validators.required],
      MultipleLines:    ['', Validators.required],
      InternetService:  ['', Validators.required],
      OnlineSecurity:   ['', Validators.required],
      OnlineBackup:     ['', Validators.required],
      DeviceProtection: ['', Validators.required],
      TechSupport:      ['', Validators.required],
      StreamingTV:      ['', Validators.required],
      StreamingMovies:  ['', Validators.required],
      Contract:         ['', Validators.required],
      PaperlessBilling: ['', Validators.required],
      PaymentMethod:    ['', Validators.required],
      MonthlyCharges:   ['', [Validators.required, Validators.min(0)]],
      TotalCharges:     ['', [Validators.required, Validators.min(0)]],
    });
  }

  onSubmit() {
    if (this.form.invalid) return;

    this.loading.set(true);
    this.result.set(null);
    this.errorMsg.set('');

    this.predictService.predict(this.form.value).subscribe({
      next: (data) => {
        this.result.set(data);
        this.loading.set(false);
      },
      error: () => {
        this.errorMsg.set('Failed to connect to the prediction server. Make sure Flask is running.');
        this.loading.set(false);
      }
    });
  }

  downloadPDF() {
    const r = this.result();
    if (!r) return;

    const doc = new jsPDF();
    const date = new Date().toLocaleString();

    // ── Header ──────────────────────────────────
    doc.setFillColor(26, 35, 126);
    doc.rect(0, 0, 210, 40, 'F');
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(22);
    doc.setFont('helvetica', 'bold');
    doc.text('Customer Churn Prediction Report', 14, 18);
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.text(`Generated: ${date}`, 14, 30);

    // ── Risk color ──────────────────────────────
    const riskColor: [number, number, number] =
      r.risk_level === 'Low'    ? [76, 175, 80] :
      r.risk_level === 'Medium' ? [255, 152, 0] :
                                  [244, 67, 54];

    // ── Prediction Summary ───────────────────────
    doc.setTextColor(0, 0, 0);
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.text('Prediction Summary', 14, 55);

    doc.setDrawColor(230, 230, 230);
    doc.line(14, 58, 196, 58);

    // Probability box
    doc.setFillColor(...riskColor);
    doc.roundedRect(14, 63, 85, 35, 4, 4, 'F');
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(28);
    doc.setFont('helvetica', 'bold');
    doc.text(`${r.churn_probability}%`, 56, 82, { align: 'center' });
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.text('Churn Probability', 56, 92, { align: 'center' });

    // Risk level box
    doc.setFillColor(245, 245, 245);
    doc.roundedRect(109, 63, 85, 35, 4, 4, 'F');
    doc.setTextColor(...riskColor);
    doc.setFontSize(20);
    doc.setFont('helvetica', 'bold');
    doc.text(`${r.risk_level} Risk`, 151, 82, { align: 'center' });
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(150, 150, 150);
    doc.text('Risk Level', 151, 92, { align: 'center' });

    // ── Customer Details ─────────────────────────
    doc.setTextColor(0, 0, 0);
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.text('Customer Details', 14, 115);
    doc.line(14, 118, 196, 118);

    const form = this.form.value;
    const contractMap: Record<number, string> = { 0: 'Month-to-month', 1: 'One year', 2: 'Two year' };
    const internetMap: Record<number, string> = { 0: 'DSL', 1: 'Fiber optic', 2: 'No' };

    const details = [
      ['Tenure',           `${form.tenure} months`],
      ['Contract',         contractMap[form.Contract] ?? form.Contract],
      ['Internet Service', internetMap[form.InternetService] ?? form.InternetService],
      ['Monthly Charges',  `$${form.MonthlyCharges}`],
      ['Total Charges',    `$${form.TotalCharges}`],
      ['Senior Citizen',   form.SeniorCitizen === 1 ? 'Yes' : 'No'],
      ['Partner',          form.Partner === 1 ? 'Yes' : 'No'],
      ['Tech Support',     form.TechSupport === 2 ? 'Yes' : 'No'],
      ['Online Security',  form.OnlineSecurity === 2 ? 'Yes' : 'No'],
    ];

    doc.setFontSize(11);
    let y = 128;
    details.forEach(([label, value], i) => {
      if (i % 2 === 0) doc.setFillColor(250, 250, 255);
      else             doc.setFillColor(255, 255, 255);
      doc.rect(14, y - 5, 182, 10, 'F');
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(80, 80, 80);
      doc.text(label, 18, y);
      doc.setFont('helvetica', 'normal');
      doc.setTextColor(0, 0, 0);
      doc.text(String(value), 100, y);
      y += 10;
    });

    // ── AI Explanation ───────────────────────────
    doc.setTextColor(0, 0, 0);
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.text('AI Analysis', 14, y + 10);
    doc.line(14, y + 13, 196, y + 13);

    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(60, 60, 60);
    const lines = doc.splitTextToSize(r.explanation, 178);
    doc.text(lines, 14, y + 22);

    // ── Footer ───────────────────────────────────
    doc.setFillColor(26, 35, 126);
    doc.rect(0, 280, 210, 17, 'F');
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(9);
    doc.text('Generated by Customer Churn Predictor — Powered by Random Forest + Groq AI', 105, 290, { align: 'center' });

    const name = (this.form.value.customer_name || '').trim().replace(/\s+/g, '_') || 'customer';
    const fileName = `churn_report_${name}.pdf`;

    const blob = doc.output('blob');
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  getRiskColor(): string {
    const r = this.result();
    if (!r) return '';
    if (r.risk_level === 'Low')    return '#4caf50';
    if (r.risk_level === 'Medium') return '#ff9800';
    return '#f44336';
  }
}
