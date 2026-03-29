import { Injectable, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class ThemeService {

  // Signal — true = dark mode, false = light mode
  // Read from localStorage so preference is remembered across sessions
  isDark = signal<boolean>(localStorage.getItem('theme') === 'dark');

  constructor() {
    // Apply theme on startup
    this.applyTheme(this.isDark());
  }

  toggle() {
    const next = !this.isDark();
    this.isDark.set(next);
    localStorage.setItem('theme', next ? 'dark' : 'light');
    this.applyTheme(next);
  }

  private applyTheme(dark: boolean) {
    // Add/remove 'dark-mode' class on <body>
    // All dark styles are triggered by this class in styles.scss
    document.body.classList.toggle('dark-mode', dark);
  }
}
