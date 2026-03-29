import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

// App is the root shell — it just holds the router outlet
// The actual pages (PredictComponent, HistoryComponent) are loaded via routing

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  template: '<router-outlet></router-outlet>',
})
export class App {}
