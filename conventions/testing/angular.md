# Angular Testing Conventions

## Test Structure

```
src/app/
├── core/
│   └── services/
│       ├── user.service.ts
│       └── user.service.spec.ts    # Tests alongside code
├── features/
│   └── user/
│       ├── components/
│       │   ├── user-profile.component.ts
│       │   └── user-profile.component.spec.ts
│       └── user.routes.spec.ts
└── shared/
    └── components/
        └── button/
            └── button.component.spec.ts
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test file | `{file}.spec.ts` | `user.service.spec.ts` |
| Test suite | `describe('{ClassName}')` | `describe('UserService')` |
| Test case | `it('should ...')` | `it('should return user')` |

## Test Framework

| Purpose | Tool | Notes |
|---------|------|-------|
| Framework | Jest or Jasmine | Jest preferred |
| Component testing | TestBed | Angular testing |
| HTTP mocking | HttpClientTestingModule | Built-in |
| E2E | Playwright | Modern E2E |

## Test Commands

| Action | Command |
|--------|---------|
| Run all | `ng test` |
| Watch | `ng test --watch` |
| Coverage | `ng test --code-coverage` |
| Headless | `ng test --browsers=ChromeHeadless` |
| E2E | `ng e2e` |

## Component Tests

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { UserProfileComponent } from './user-profile.component';
import { UserService } from '@core/services/user.service';

describe('UserProfileComponent', () => {
  let component: UserProfileComponent;
  let fixture: ComponentFixture<UserProfileComponent>;
  let mockUserService: jasmine.SpyObj<UserService>;

  beforeEach(async () => {
    mockUserService = jasmine.createSpyObj('UserService', ['fetchUser'], {
      user: signal({ id: '123', name: 'Test User' }),
      loading: signal(false),
      error: signal(null),
    });

    await TestBed.configureTestingModule({
      imports: [UserProfileComponent],
      providers: [
        { provide: UserService, useValue: mockUserService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(UserProfileComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should display user name', () => {
    fixture.componentRef.setInput('userId', '123');
    fixture.detectChanges();

    const element = fixture.nativeElement;
    expect(element.textContent).toContain('Test User');
  });

  it('should show loading spinner when loading', () => {
    (mockUserService.loading as any).set(true);
    fixture.componentRef.setInput('userId', '123');
    fixture.detectChanges();

    const spinner = fixture.nativeElement.querySelector('app-loading-spinner');
    expect(spinner).toBeTruthy();
  });

  it('should emit delete event', () => {
    fixture.componentRef.setInput('userId', '123');
    fixture.detectChanges();

    spyOn(component.delete, 'emit');

    const button = fixture.nativeElement.querySelector('button');
    button.click();

    expect(component.delete.emit).toHaveBeenCalled();
  });

  it('should show details when showDetails is true', () => {
    fixture.componentRef.setInput('userId', '123');
    fixture.componentRef.setInput('showDetails', true);
    fixture.detectChanges();

    const details = fixture.nativeElement.querySelector('app-user-details');
    expect(details).toBeTruthy();
  });
});
```

## Service Tests

```typescript
import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { UserService } from './user.service';

describe('UserService', () => {
  let service: UserService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [UserService]
    });

    service = TestBed.inject(UserService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should fetch user', async () => {
    const mockUser = { id: '123', name: 'Test User' };

    const fetchPromise = service.fetchUser('123');

    const req = httpMock.expectOne('/api/users/123');
    expect(req.request.method).toBe('GET');
    req.flush(mockUser);

    await fetchPromise;

    expect(service.user()).toEqual(mockUser);
    expect(service.loading()).toBe(false);
  });

  it('should handle fetch error', async () => {
    const fetchPromise = service.fetchUser('123');

    const req = httpMock.expectOne('/api/users/123');
    req.flush('Error', { status: 500, statusText: 'Server Error' });

    await fetchPromise;

    expect(service.error()).toBe('Failed to fetch user');
    expect(service.user()).toBeNull();
  });

  it('should set loading state during fetch', () => {
    service.fetchUser('123');

    expect(service.loading()).toBe(true);

    const req = httpMock.expectOne('/api/users/123');
    req.flush({ id: '123', name: 'Test' });
  });
});
```

## E2E Tests (Playwright)

```typescript
import { test, expect } from '@playwright/test';

test.describe('User Profile', () => {
  test.beforeEach(async ({ page }) => {
    // Mock API
    await page.route('/api/users/*', route => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({ id: '123', name: 'Test User' })
      });
    });
  });

  test('displays user profile', async ({ page }) => {
    await page.goto('/users/123');

    await expect(page.locator('h1')).toContainText('Test User');
  });

  test('shows loading state', async ({ page }) => {
    await page.route('/api/users/*', route => {
      // Delay response
      setTimeout(() => route.fulfill({ body: '{}' }), 1000);
    });

    await page.goto('/users/123');

    await expect(page.locator('app-loading-spinner')).toBeVisible();
  });

  test('handles delete action', async ({ page }) => {
    await page.goto('/users/123');

    await page.click('button:has-text("Delete")');

    // Verify confirmation dialog or redirect
    await expect(page).toHaveURL('/users');
  });
});
```

## Testing Utilities

```typescript
// testing/test-utils.ts
import { ComponentFixture } from '@angular/core/testing';

export function setInput<T>(
  fixture: ComponentFixture<T>,
  name: string,
  value: any
): void {
  fixture.componentRef.setInput(name, value);
  fixture.detectChanges();
}

export function query<T extends Element>(
  fixture: ComponentFixture<any>,
  selector: string
): T | null {
  return fixture.nativeElement.querySelector(selector);
}

export function queryAll<T extends Element>(
  fixture: ComponentFixture<any>,
  selector: string
): T[] {
  return Array.from(fixture.nativeElement.querySelectorAll(selector));
}
```

## Coverage Target

- Minimum: 80% line coverage
- Focus on services and component logic
- Use code coverage thresholds in angular.json
