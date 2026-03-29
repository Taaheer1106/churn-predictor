// ─────────────────────────────────────────────
// predict.service.ts
// This service is responsible for sending customer
// data to the Flask API and returning the result
// ─────────────────────────────────────────────

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';   // Built-in Angular tool to make HTTP requests
import { Observable } from 'rxjs';                   // Represents a future value (like a Promise)

// PredictionResult defines the shape of the response we expect from Flask
export interface PredictionResult {
  churn_probability: number;   // e.g. 73.4
  risk_level: string;          // 'Low', 'Medium', or 'High'
  explanation: string;         // GPT-generated plain English explanation
}

// @Injectable makes this service available throughout the app
@Injectable({
  providedIn: 'root'
})
export class PredictService {

  // The Flask API URL — change this to your Heroku URL when deploying
  private apiUrl = 'http://127.0.0.1:5000';

  // HttpClient is injected automatically by Angular — we use it to make API calls
  constructor(private http: HttpClient) {}

  // predict() sends customer data to Flask and returns the prediction
  // Observable<PredictionResult> means: "this will eventually return a PredictionResult"
  predict(customerData: any): Observable<PredictionResult> {
    return this.http.post<PredictionResult>(`${this.apiUrl}/predict`, customerData);
  }

  deleteRecord(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/history/${id}`);
  }

  clearHistory(): Observable<any> {
    return this.http.delete(`${this.apiUrl}/history`);
  }
}
