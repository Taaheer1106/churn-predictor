import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { HttpClient } from '@angular/common/http';

// App is the root shell — it just holds the router outlet
// The actual pages (PredictComponent, HistoryComponent) are loaded via routing

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  template: '<router-outlet></router-outlet>',
})
export class App {
  constructor() {
    // Ping the backend on app load so Render wakes up before the user hits Predict
    inject(HttpClient).get('https://churn-predictor-716z.onrender.com/health').subscribe();
  }
}
