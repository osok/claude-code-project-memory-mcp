# Next.js Conventions

## Project Structure

```
project/
├── src/
│   ├── app/                    # App Router
│   │   ├── (auth)/             # Route group
│   │   │   ├── login/
│   │   │   └── register/
│   │   ├── api/                # API routes
│   │   │   └── users/
│   │   │       └── route.ts
│   │   ├── users/
│   │   │   ├── [id]/
│   │   │   │   └── page.tsx
│   │   │   └── page.tsx
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── globals.css
│   ├── components/
│   │   ├── ui/                 # Shared UI components
│   │   └── features/           # Feature components
│   ├── lib/
│   │   ├── actions/            # Server actions
│   │   ├── hooks/              # Custom hooks
│   │   └── utils/              # Utilities
│   ├── services/               # API services
│   └── types/
├── public/
├── next.config.js
└── package.json
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Component | PascalCase | `UserProfile.tsx` |
| Page | page.tsx | `app/users/page.tsx` |
| Layout | layout.tsx | `app/layout.tsx` |
| API route | route.ts | `app/api/users/route.ts` |
| Server action | camelCase | `createUser` |
| Hook | use + PascalCase | `useUser` |
| Utility | camelCase | `formatDate` |

## Approved Libraries

| Purpose | Library | Notes |
|---------|---------|-------|
| State | React hooks / Zustand | Zustand for global state |
| Data fetching | Server Components / SWR | Server Components preferred |
| Forms | React Hook Form + Zod | Form handling |
| Styling | Tailwind CSS | Utility-first |
| UI | shadcn/ui | Copy-paste components |
| Auth | NextAuth.js | Authentication |
| Database | Prisma | ORM |

## Build Commands

| Action | Command |
|--------|---------|
| Dev server | `npm run dev` |
| Build | `npm run build` |
| Start | `npm run start` |
| Lint | `npm run lint` |
| Test | `npm run test` |

## Server Components (Default)

```tsx
// app/users/[id]/page.tsx
import { notFound } from 'next/navigation';
import { getUser } from '@/services/users';
import { UserDetails } from '@/components/features/UserDetails';

interface Props {
  params: { id: string };
}

export default async function UserPage({ params }: Props) {
  const user = await getUser(params.id);

  if (!user) {
    notFound();
  }

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold">{user.name}</h1>
      <UserDetails user={user} />
    </div>
  );
}

// Generate metadata
export async function generateMetadata({ params }: Props) {
  const user = await getUser(params.id);
  return {
    title: user?.name ?? 'User Not Found',
  };
}
```

## Client Components

```tsx
// components/features/UserForm.tsx
'use client';

import { useState, useTransition } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { createUser } from '@/lib/actions/users';

const schema = z.object({
  name: z.string().min(1, 'Name is required'),
  email: z.string().email('Invalid email'),
});

type FormData = z.infer<typeof schema>;

export function UserForm() {
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = (data: FormData) => {
    startTransition(async () => {
      const result = await createUser(data);
      if (result.error) {
        setError(result.error);
      }
    });
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {error && <p className="text-red-500">{error}</p>}

      <div>
        <input {...register('name')} placeholder="Name" className="input" />
        {errors.name && <p className="text-red-500">{errors.name.message}</p>}
      </div>

      <div>
        <input {...register('email')} placeholder="Email" className="input" />
        {errors.email && <p className="text-red-500">{errors.email.message}</p>}
      </div>

      <button type="submit" disabled={isPending} className="btn">
        {isPending ? 'Creating...' : 'Create User'}
      </button>
    </form>
  );
}
```

## Server Actions

```typescript
// lib/actions/users.ts
'use server';

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { z } from 'zod';
import { prisma } from '@/lib/prisma';

const createUserSchema = z.object({
  name: z.string().min(1),
  email: z.string().email(),
});

export async function createUser(data: z.infer<typeof createUserSchema>) {
  const validated = createUserSchema.safeParse(data);

  if (!validated.success) {
    return { error: 'Invalid data' };
  }

  try {
    await prisma.user.create({ data: validated.data });
    revalidatePath('/users');
    redirect('/users');
  } catch (e) {
    return { error: 'Failed to create user' };
  }
}
```

## API Routes

```typescript
// app/api/users/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const page = parseInt(searchParams.get('page') ?? '1');

  const users = await prisma.user.findMany({
    skip: (page - 1) * 10,
    take: 10,
  });

  return NextResponse.json(users);
}

export async function POST(request: NextRequest) {
  const body = await request.json();

  const user = await prisma.user.create({ data: body });

  return NextResponse.json(user, { status: 201 });
}
```

## Code Style

- Use Server Components by default
- Add 'use client' only when needed (interactivity, hooks, browser APIs)
- Colocate data fetching with components
- Use Server Actions for mutations
- Prefer Tailwind for styling
- Use parallel routes for complex layouts
- Cache aggressively with proper revalidation
