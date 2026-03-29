import { Routes } from '@angular/router';
import { PredictComponent } from './predict/predict.component';
import { HistoryComponent } from './history/history.component';
import { BulkComponent } from './bulk/bulk.component';

export const routes: Routes = [
  { path: '',        component: PredictComponent },
  { path: 'history', component: HistoryComponent },
  { path: 'bulk',    component: BulkComponent },
];
