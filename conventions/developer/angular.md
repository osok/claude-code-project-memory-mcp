# Angular Conventions

## Project Structure

```
project/
├── src/
│   ├── app/
│   │   ├── core/              # Singleton services, guards, interceptors
│   │   │   ├── services/
│   │   │   ├── guards/
│   │   │   └── interceptors/
│   │   ├── shared/            # Shared components, directives, pipes
│   │   │   ├── components/
│   │   │   ├── directives/
│   │   │   └── pipes/
│   │   ├── features/          # Feature modules
│   │   │   └── user/
│   │   │       ├── components/
│   │   │       ├── services/
│   │   │       ├── user.routes.ts
│   │   │       └── user.component.ts
│   │   ├── app.component.ts
│   │   ├── app.config.ts
│   │   └── app.routes.ts
│   ├── assets/
│   ├── environments/
│   └── main.ts
├── angular.json
└── package.json
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Component | kebab-case file, PascalCase class | `user-profile.component.ts`, `UserProfileComponent` |
| Service | kebab-case file | `user.service.ts`, `UserService` |
| Directive | kebab-case file | `highlight.directive.ts` |
| Pipe | kebab-case file | `date-format.pipe.ts` |
| Module | kebab-case file | `user.module.ts` |
| Interface | PascalCase, I prefix optional | `User` or `IUser` |
| Selector | app- prefix | `app-user-profile` |

## Approved Libraries

| Purpose | Library | Notes |
|---------|---------|-------|
| State management | NgRx or Signals | Signals for simple, NgRx for complex |
| HTTP | HttpClient | Built-in |
| Forms | Reactive Forms | Built-in |
| UI | Angular Material or PrimeNG | Pick one |
| Testing | Jasmine + Karma or Jest | Jest gaining popularity |
| E2E | Playwright | Replaces Protractor |

## Build Commands

| Action | Command |
|--------|---------|
| Dev server | `ng serve` |
| Build | `ng build` |
| Build prod | `ng build --configuration production` |
| Test | `ng test` |
| E2E | `ng e2e` |
| Lint | `ng lint` |
| Generate | `ng generate component {name}` |

## Component Structure (Standalone)

```typescript
// user-profile.component.ts
import { Component, input, output, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { UserService } from '@core/services/user.service';
import { User } from '@core/models/user.model';

@Component({
  selector: 'app-user-profile',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="user-profile">
      @if (loading()) {
        <app-loading-spinner />
      } @else if (error()) {
        <app-error-message [message]="error()" />
      } @else {
        <h1>{{ userName() }}</h1>
        @if (showDetails()) {
          <app-user-details [user]="user()" />
        }
        <button (click)="onDelete()">Delete</button>
      }
    </div>
  `,
  styleUrl: './user-profile.component.scss'
})
export class UserProfileComponent {
  private userService = inject(UserService);

  // Inputs
  userId = input.required<string>();
  showDetails = input(false);

  // Outputs
  delete = output<void>();

  // State (Signals)
  user = this.userService.user;
  loading = this.userService.loading;
  error = this.userService.error;

  // Computed
  userName = computed(() => this.user()?.name ?? 'Guest');

  onDelete() {
    this.delete.emit();
  }
}
```

## Services

```typescript
// user.service.ts
import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { User } from '@core/models/user.model';

@Injectable({ providedIn: 'root' })
export class UserService {
  private http = inject(HttpClient);

  // State
  private _user = signal<User | null>(null);
  private _loading = signal(false);
  private _error = signal<string | null>(null);

  // Public readonly signals
  user = this._user.asReadonly();
  loading = this._loading.asReadonly();
  error = this._error.asReadonly();

  // Computed
  isAuthenticated = computed(() => !!this._user());

  async fetchUser(id: string): Promise<void> {
    this._loading.set(true);
    this._error.set(null);

    try {
      const user = await this.http.get<User>(`/api/users/${id}`).toPromise();
      this._user.set(user);
    } catch (e) {
      this._error.set('Failed to fetch user');
    } finally {
      this._loading.set(false);
    }
  }
}
```

## Code Style

- Use standalone components (Angular 17+)
- Use signals for state management
- Use `inject()` function over constructor injection
- Use new control flow syntax (`@if`, `@for`, `@switch`)
- Keep components small and focused
- Use OnPush change detection
- Lazy load feature modules
- Use typed forms
- Prefer observables with async pipe in templates
