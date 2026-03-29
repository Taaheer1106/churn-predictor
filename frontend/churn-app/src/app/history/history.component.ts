import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink } from '@angular/router';
import { ThemeService } from '../theme.service';
import { PredictService } from '../predict.service';

export interface HistoryRecord {
  id: number;
  customer_name: string | null;
  tenure: number;
  contract: number;
  monthly_charges: number;
  total_charges: number;
  churn_probability: number;
  risk_level: string;
  explanation: string;
  created_at: string;
}

@Component({
  selector: 'app-history',
  standalone: true,
  imports: [
    FormsModule,
    MatCardModule,
    MatTableModule,
    MatChipsModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatFormFieldModule,
    MatIconModule,
    RouterLink,
  ],
  templateUrl: './history.component.html',
  styleUrl: './history.component.scss'
})
export class HistoryComponent implements OnInit {

  records: HistoryRecord[] = [];
  filteredRecords: HistoryRecord[] = [];
  loading = true;
  errorMessage = '';

  // Filter state
  selectedRiskFilter = 'All';
  riskOptions = ['All', 'High', 'Medium', 'Low'];

  // Columns to show in the table
  displayedColumns = [
    'customer_name', 'id', 'created_at', 'tenure', 'contract',
    'monthly_charges', 'churn_probability', 'risk_level', 'actions'
  ];

  constructor(
    private http: HttpClient,
    private cdr: ChangeDetectorRef,
    private predictService: PredictService,
    public theme: ThemeService
  ) {}

  ngOnInit() {
    this.http.get<HistoryRecord[]>('https://churn-predictor-716z.onrender.com/history').subscribe({
      next: (data) => {
        this.records = data;
        this.filteredRecords = data;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.errorMessage = 'Could not load history. Make sure Flask is running.';
        this.loading = false;
        this.cdr.detectChanges();
      }
    });
  }

  // Filter table by selected risk level
  applyFilter() {
    if (this.selectedRiskFilter === 'All') {
      this.filteredRecords = this.records;
    } else {
      this.filteredRecords = this.records.filter(
        r => r.risk_level === this.selectedRiskFilter
      );
    }
  }

  // Delete a single prediction row
  deleteRecord(id: number) {
    if (!confirm('Delete this prediction?')) return;
    this.predictService.deleteRecord(id).subscribe({
      next: () => {
        this.records = this.records.filter(r => r.id !== id);
        this.applyFilter();
        this.cdr.detectChanges();
      },
      error: () => alert('Failed to delete record.')
    });
  }

  // Clear all predictions
  clearAll() {
    if (!confirm('Delete ALL prediction history? This cannot be undone.')) return;
    this.predictService.clearHistory().subscribe({
      next: () => {
        this.records = [];
        this.filteredRecords = [];
        this.cdr.detectChanges();
      },
      error: () => alert('Failed to clear history.')
    });
  }

  getContractLabel(val: number): string {
    return { 0: 'Month-to-month', 1: 'One year', 2: 'Two year' }[val] ?? 'Unknown';
  }

  getRiskColor(risk: string): string {
    if (risk === 'Low')    return '#4caf50';
    if (risk === 'Medium') return '#ff9800';
    return '#f44336';
  }

  getCountByRisk(risk: string): number {
    return this.records.filter(r => r.risk_level === risk).length;
  }
}
