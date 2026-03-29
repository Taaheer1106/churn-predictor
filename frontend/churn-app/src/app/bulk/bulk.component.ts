import { Component, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { ThemeService } from '../theme.service';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';

export interface BulkResult {
  row: number;
  churn_probability: number;
  risk_level: string;
}

@Component({
  selector: 'app-bulk',
  standalone: true,
  imports: [
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatTableModule,
    MatProgressSpinnerModule,
    MatIconModule,
  ],
  templateUrl: './bulk.component.html',
  styleUrl: './bulk.component.scss'
})
export class BulkComponent {

  results    = signal<BulkResult[]>([]);
  loading    = signal(false);
  errorMsg   = signal('');
  fileName   = signal('');

  displayedColumns = ['row', 'churn_probability', 'risk_level'];

  constructor(private http: HttpClient, public theme: ThemeService) {}

  // Called when user selects a CSV file
  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (!input.files?.length) return;

    const file = input.files[0];
    this.fileName.set(file.name);
    this.loading.set(true);
    this.results.set([]);
    this.errorMsg.set('');

    // Send file to Flask as multipart form data
    const formData = new FormData();
    formData.append('file', file);

    this.http.post<BulkResult[]>('https://churn-predictor-716z.onrender.com/predict/bulk', formData).subscribe({
      next: (data) => {
        this.results.set(data);
        this.loading.set(false);
      },
      error: () => {
        this.errorMsg.set('Failed to process file. Make sure it has the correct columns.');
        this.loading.set(false);
      }
    });
  }

  getRiskColor(risk: string): string {
    if (risk === 'Low')    return '#4caf50';
    if (risk === 'Medium') return '#ff9800';
    return '#f44336';
  }

  getHighCount()   { return this.results().filter(r => r.risk_level === 'High').length; }
  getMediumCount() { return this.results().filter(r => r.risk_level === 'Medium').length; }
  getLowCount()    { return this.results().filter(r => r.risk_level === 'Low').length; }

  // Download results as CSV
  downloadCSV() {
    const rows = this.results();
    const header = 'Row,Churn Probability (%),Risk Level\n';
    const csv = rows.map(r => `${r.row},${r.churn_probability},${r.risk_level}`).join('\n');
    const blob = new Blob([header + csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'churn_predictions.csv';
    a.click();
    URL.revokeObjectURL(url);
  }
}
