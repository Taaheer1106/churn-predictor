import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class UserService {

  private readonly KEY = 'churn_user_id';

  getUserId(): string {
    let id = localStorage.getItem(this.KEY);
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem(this.KEY, id);
    }
    return id;
  }
}
