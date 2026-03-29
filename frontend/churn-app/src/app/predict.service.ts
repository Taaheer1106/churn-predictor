// ─────────────────────────────────────────────
// predict.service.ts
// This service is responsible for sending customer
// data to the Flask API and returning the result
// ─────────────────────────────────────────────

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { UserService } from './user.service';

export interface PredictionResult {
  churn_probability: number;
  risk_level: string;
  explanation: string;
}

@Injectable({ providedIn: 'root' })
export class PredictService {

  private apiUrl = 'https://churn-predictor-716z.onrender.com';

  constructor(private http: HttpClient, private userService: UserService) {}

  predict(customerData: any): Observable<PredictionResult> {
    const payload = { ...customerData, user_id: this.userService.getUserId() };
    return this.http.post<PredictionResult>(`${this.apiUrl}/predict`, payload);
  }

  getHistory(): Observable<any[]> {
    const uid = this.userService.getUserId();
    return this.http.get<any[]>(`${this.apiUrl}/history?user_id=${uid}`);
  }

  deleteRecord(id: number): Observable<any> {
    const uid = this.userService.getUserId();
    return this.http.delete(`${this.apiUrl}/history/${id}?user_id=${uid}`);
  }

  clearHistory(): Observable<any> {
    const uid = this.userService.getUserId();
    return this.http.delete(`${this.apiUrl}/history?user_id=${uid}`);
  }
}
