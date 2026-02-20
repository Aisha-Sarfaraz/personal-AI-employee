---
name: verify-nextjs-16-patterns
description: Validate Next.js code patterns against Next.js 16 best practices using Context7 MCP documentation
version: 1.0.0
agent: nextjs-frontend-architect
reusability: high
---

# Verify Next.js 16 Patterns

## Purpose

Validate Next.js code patterns, file structures, and API usage against Next.js 16 App Router best practices to prevent deprecated patterns and enforce current conventions. This skill enforces Context7 MCP usage to ensure validation relies on up-to-date documentation rather than stale internal knowledge.

## When to Use

- Before implementing any Next.js 16 frontend feature
- During code review of Next.js components or pages
- When migrating from pages/ directory to app/ directory
- After detecting potential deprecated pattern usage
- When architectural decisions about routing or data fetching are needed

## Inputs

- **Code snippet** (TypeScript/JSX code to validate)
- **File path** (e.g., `app/dashboard/page.tsx`, `middleware.ts`)
- **Pattern name** (e.g., "data fetching", "metadata generation", "dynamic routes")
- **Context7 query** (optional: specific documentation topic to verify against)

## Outputs

- **Validation report** with compliance status:
  - ✅ **COMPLIANT**: Code follows Next.js 16 best practices
  - ❌ **DEPRECATED**: Code uses deprecated Next.js patterns
  - ⚠️ **WARNING**: Code works but has potential issues or non-optimal patterns
- **Violation details** with line numbers and specific issues
- **Replacement recommendations** with code examples
- **Migration guidance** for deprecated patterns
- **Context7 documentation references** (links to official Next.js docs)

## Validation Workflow

### Step 1: Context7 Documentation Verification

**Query Latest Next.js 16 Best Practices:**

Before validating any code, query Context7 MCP for the most recent Next.js 16 documentation on the specific pattern being validated.

```typescript
// Example: Validate data fetching pattern
// First, query Context7 for current data fetching best practices

const context7Query = {
  libraryId: "/vercel/next.js/v16.1.0",
  query: "Next.js 16 Server Component data fetching with fetch() API caching strategies"
}

// Context7 returns current documentation:
// - Use async/await fetch() in Server Components
// - cache: 'force-cache' | 'no-store'
// - next: { revalidate: number }
// - getServerSideProps is DEPRECATED
```

**Validation Rule:**
- **MUST** query Context7 before validating any pattern
- **DO NOT** rely on internal knowledge for Next.js APIs
- **MUST** compare code against Context7 documentation results

### Step 2: File Path & Naming Convention Validation

**Validate File Structure:**

```typescript
// Validation: Check if file path follows Next.js 16 conventions

const filePathValidation = {
  // ✅ COMPLIANT: App Router conventions
  "app/dashboard/page.tsx": "COMPLIANT",
  "app/dashboard/layout.tsx": "COMPLIANT",
  "app/dashboard/loading.tsx": "COMPLIANT",
  "app/dashboard/error.tsx": "COMPLIANT",
  "app/dashboard/not-found.tsx": "COMPLIANT",
  "app/api/tasks/route.tsx": "COMPLIANT",
  "proxy.ts": "COMPLIANT (Next.js 16 renamed middleware to proxy)",

  // ❌ DEPRECATED: pages/ directory
  "pages/dashboard.tsx": "DEPRECATED - Use app/dashboard/page.tsx",
  "pages/api/tasks.ts": "DEPRECATED - Use app/api/tasks/route.ts",
  "middleware.ts": "DEPRECATED - Use proxy.ts in Next.js 16+",

  // ❌ DEPRECATED: Special files
  "pages/_app.tsx": "DEPRECATED - Use app/layout.tsx",
  "pages/_document.tsx": "DEPRECATED - Use app/layout.tsx with metadata",
}
```

**Validation Steps:**
1. Extract file path from input
2. Check if path starts with `app/` (COMPLIANT) or `pages/` (DEPRECATED)
3. Validate file naming conventions (page.tsx, layout.tsx, etc.)
4. Flag middleware.ts → should be proxy.ts in Next.js 16+

### Step 3: API Pattern Detection

**Detect Deprecated Data Fetching APIs:**

```typescript
// ❌ DEPRECATED: Old data fetching methods
const deprecatedPatterns = [
  {
    // Pattern 1: getServerSideProps (pages/ directory only)
    pattern: /export\s+async\s+function\s+getServerSideProps/,
    severity: "CRITICAL",
    message: "getServerSideProps is deprecated in Next.js 16",
    replacement: `
// ❌ DEPRECATED:
export async function getServerSideProps(context) {
  const res = await fetch('https://api.example.com/data')
  const data = await res.json()
  return { props: { data } }
}

// ✅ CURRENT (Next.js 16):
// Use async Server Component with fetch()
async function Page() {
  const res = await fetch('https://api.example.com/data', {
    cache: 'no-store' // Equivalent to getServerSideProps (no caching)
  })
  const data = await res.json()
  return <div>{data.title}</div>
}
    `
  },
  {
    // Pattern 2: getStaticProps
    pattern: /export\s+async\s+function\s+getStaticProps/,
    severity: "CRITICAL",
    message: "getStaticProps is deprecated in Next.js 16",
    replacement: `
// ❌ DEPRECATED:
export async function getStaticProps() {
  const res = await fetch('https://api.example.com/data')
  const data = await res.json()
  return { props: { data }, revalidate: 60 }
}

// ✅ CURRENT (Next.js 16):
async function Page() {
  const res = await fetch('https://api.example.com/data', {
    next: { revalidate: 60 } // ISR with 60 second revalidation
  })
  const data = await res.json()
  return <div>{data.title}</div>
}
    `
  },
  {
    // Pattern 3: getStaticPaths
    pattern: /export\s+async\s+function\s+getStaticPaths/,
    severity: "CRITICAL",
    message: "getStaticPaths is deprecated in Next.js 16",
    replacement: `
// ❌ DEPRECATED:
export async function getStaticPaths() {
  const paths = [{ params: { id: '1' } }, { params: { id: '2' } }]
  return { paths, fallback: false }
}

// ✅ CURRENT (Next.js 16):
// Use generateStaticParams in app/ directory
export async function generateStaticParams() {
  const posts = await fetch('https://api.example.com/posts').then(res => res.json())
  return posts.map((post) => ({ id: post.id }))
}

// Dynamic route: app/posts/[id]/page.tsx
async function Page({ params }: { params: { id: string } }) {
  const post = await fetch(\`https://api.example.com/posts/\${params.id}\`)
  return <div>{post.title}</div>
}
    `
  },
  {
    // Pattern 4: getInitialProps
    pattern: /getInitialProps/,
    severity: "CRITICAL",
    message: "getInitialProps is deprecated in Next.js 16",
    replacement: "Use async Server Components with fetch() in app/ directory"
  }
]
```

**Validation Steps:**
1. Parse code snippet for deprecated API patterns
2. Extract line numbers where violations occur
3. Match against deprecatedPatterns registry
4. Generate replacement code examples

### Step 4: App Router Convention Validation

**Validate Current Next.js 16 Patterns:**

```typescript
// ✅ COMPLIANT: Next.js 16 App Router patterns

// 1. Server Component data fetching
async function TasksPage() {
  const res = await fetch('https://api.example.com/tasks', {
    cache: 'force-cache' // Static generation (default)
    // OR: cache: 'no-store' // Dynamic rendering (no cache)
    // OR: next: { revalidate: 60 } // ISR (revalidate every 60s)
  })
  const tasks = await res.json()
  return <TaskList tasks={tasks} />
}

// 2. generateMetadata for dynamic SEO
export async function generateMetadata({ params }) {
  const task = await fetch(`https://api.example.com/tasks/${params.id}`).then(res => res.json())
  return {
    title: task.title,
    description: task.description,
  }
}

// 3. generateStaticParams for dynamic routes
export async function generateStaticParams() {
  const tasks = await fetch('https://api.example.com/tasks').then(res => res.json())
  return tasks.map((task) => ({ id: task.id }))
}

// 4. Client Component with 'use client' directive
'use client'
import { useState } from 'react'

export function TaskForm() {
  const [title, setTitle] = useState('')
  return <form>...</form>
}

// 5. Route Handler (API routes)
// app/api/tasks/route.ts
export async function GET(request: Request) {
  const tasks = await fetchTasksFromDB()
  return Response.json(tasks)
}

export async function POST(request: Request) {
  const body = await request.json()
  const task = await createTask(body)
  return Response.json(task, { status: 201 })
}
```

**Validation Checklist:**
- [ ] Server Components use async/await fetch() with correct cache strategy
- [ ] Dynamic routes use generateStaticParams (not getStaticPaths)
- [ ] Metadata uses generateMetadata function (not getStaticProps)
- [ ] Client interactivity uses 'use client' directive
- [ ] File naming follows conventions (page.tsx, layout.tsx, etc.)
- [ ] No pages/ directory usage
- [ ] proxy.ts used instead of middleware.ts

### Step 5: Generate Validation Report

**Report Template:**

```markdown
## Next.js 16 Pattern Validation Report

**File:** `app/dashboard/page.tsx`
**Pattern:** Data fetching
**Validation Date:** 2026-01-07

---

### ✅ Compliant Patterns (2)

1. **Server Component async data fetching**
   - Location: Line 5-10
   - Pattern: `async function Page() { const res = await fetch(...) }`
   - Status: ✅ COMPLIANT with Next.js 16 Server Components
   - Context7 Reference: [Next.js 16 Data Fetching](https://nextjs.org/docs/app/building-your-application/data-fetching)

2. **generateMetadata usage**
   - Location: Line 15-20
   - Pattern: `export async function generateMetadata({ params })`
   - Status: ✅ COMPLIANT with Next.js 16 metadata API
   - Context7 Reference: [Next.js 16 Metadata](https://nextjs.org/docs/app/api-reference/functions/generate-metadata)

---

### ❌ Deprecated Patterns (1)

1. **CRITICAL: getServerSideProps usage**
   - Location: Line 35-40
   - Pattern: `export async function getServerSideProps(context) { ... }`
   - Status: ❌ DEPRECATED in Next.js 16
   - Issue: getServerSideProps only works in pages/ directory (deprecated)
   - Severity: CRITICAL (blocks migration to app/ directory)

   **Replacement:**
   ```typescript
   // ❌ Remove this:
   export async function getServerSideProps(context) {
     const res = await fetch('https://api.example.com/data')
     const data = await res.json()
     return { props: { data } }
   }

   // ✅ Replace with:
   async function Page() {
     const res = await fetch('https://api.example.com/data', {
       cache: 'no-store' // Equivalent to getServerSideProps behavior
     })
     const data = await res.json()
     return <div>{data.title}</div>
   }
   ```

   **Migration Steps:**
   1. Move file from `pages/dashboard.tsx` → `app/dashboard/page.tsx`
   2. Remove getServerSideProps function
   3. Make component async and move fetch() into component body
   4. Add `cache: 'no-store'` to fetch() for dynamic behavior

---

### ⚠️ Warnings (1)

1. **File path uses middleware.ts**
   - Location: `middleware.ts` (root)
   - Pattern: middleware.ts filename
   - Status: ⚠️ WARNING - Next.js 16 renamed middleware to proxy
   - Issue: File should be named `proxy.ts` in Next.js 16+
   - Severity: MEDIUM (works but uses deprecated terminology)

   **Recommended Action:**
   Rename `middleware.ts` → `proxy.ts` and update imports accordingly.

---

### Summary

- **Total Patterns Checked:** 4
- **Compliant:** 2 ✅
- **Deprecated:** 1 ❌
- **Warnings:** 1 ⚠️
- **Overall Status:** ❌ FAILED (1 critical issue)

### Next Steps

1. Fix critical deprecated pattern (getServerSideProps)
2. Address warning (rename middleware.ts → proxy.ts)
3. Re-run verification after fixes
4. Proceed with implementation once all patterns compliant

---

**Context7 Documentation Used:**
- [Next.js 16 Data Fetching](https://nextjs.org/docs/app/building-your-application/data-fetching)
- [Next.js 16 generateMetadata](https://nextjs.org/docs/app/api-reference/functions/generate-metadata)
- [Next.js 16 generateStaticParams](https://nextjs.org/docs/app/api-reference/functions/generate-static-params)
- [Next.js 16 Routing Fundamentals](https://nextjs.org/docs/app/building-your-application/routing)
```

## Next.js 16 Pattern Reference

### Deprecated Patterns (❌ DO NOT USE)

| Deprecated API | Severity | Replacement | Notes |
|----------------|----------|-------------|-------|
| `getServerSideProps` | CRITICAL | async Server Component + `fetch(..., { cache: 'no-store' })` | pages/ directory only |
| `getStaticProps` | CRITICAL | async Server Component + `fetch(..., { cache: 'force-cache' })` or `next: { revalidate }` | pages/ directory only |
| `getStaticPaths` | CRITICAL | `generateStaticParams()` | App Router replacement |
| `getInitialProps` | CRITICAL | async Server Component + fetch() | Deprecated since Next.js 9 |
| `pages/` directory | CRITICAL | `app/` directory | Use App Router |
| `pages/_app.tsx` | CRITICAL | `app/layout.tsx` | Root layout |
| `pages/_document.tsx` | CRITICAL | `app/layout.tsx` with metadata | Root layout |
| `middleware.ts` | MEDIUM | `proxy.ts` | Next.js 16 renamed middleware |

### Current Patterns (✅ USE THESE)

| Pattern | API | Example | Cache Strategy |
|---------|-----|---------|----------------|
| **Static Generation** | `fetch()` with default cache | `await fetch(url)` | `cache: 'force-cache'` (default) |
| **Dynamic Rendering** | `fetch()` with no-store | `await fetch(url, { cache: 'no-store' })` | No caching |
| **ISR (Incremental Static Regeneration)** | `fetch()` with revalidate | `await fetch(url, { next: { revalidate: 60 } })` | Revalidate every 60s |
| **Dynamic Routes** | `generateStaticParams()` | See example above | Pre-render dynamic paths |
| **Metadata** | `generateMetadata()` | See example above | Dynamic SEO metadata |
| **Client Components** | `'use client'` directive | Add at top of file | For interactivity |
| **Route Handlers** | `app/api/*/route.ts` | `export async function GET(request)` | API endpoints |
| **Layouts** | `layout.tsx` | Shared UI across routes | Persistent across navigation |
| **Loading States** | `loading.tsx` | Automatic loading UI | Suspense boundary |
| **Error Handling** | `error.tsx` | Error boundary | Catches errors in segment |
| **404 Handling** | `not-found.tsx` | Custom 404 page | Per-route or global |
| **Request Proxying** | `proxy.ts` (root) | `export function middleware(request)` | Node.js runtime only |

## Constraints

- **MUST** query Context7 MCP before validating patterns (no internal knowledge)
- **MUST** flag all deprecated APIs (getServerSideProps, getStaticProps, getStaticPaths, getInitialProps)
- **MUST** detect pages/ directory usage and recommend app/ migration
- **MUST** recommend proxy.ts instead of middleware.ts for Next.js 16+
- **DO NOT** approve code with CRITICAL violations
- **DO NOT** rely on outdated Next.js documentation

## Reusability

**Domain-Agnostic:** Works for any Next.js 16 application

**Applicable To:**
- Next.js 16 web applications (any domain)
- Next.js migrations (pages/ → app/)
- Code reviews and pre-implementation validation
- Architectural decision validation

**Framework-Specific:** Next.js 16 only (not compatible with Next.js 13-15 patterns)

**Evolution:**
- Phase 1: Manual pattern validation with Context7 queries
- Phase 2: Automated validation on file save
- Phase 3: IDE integration for real-time validation
- Phase 4: AI-driven pattern migration (auto-fix deprecated code)

## Integration Points

**Triggered By:**
- Next.js Frontend Architect before implementing features
- Code review workflows
- Pre-commit hooks (future)
- Migration planning (pages/ → app/)

**Requires:**
- Context7 MCP tool (for latest Next.js documentation)
- Access to code files or snippets
- Next.js version detection (package.json)

**Outputs To:**
- Validation report (markdown)
- Pattern compliance status (✅/❌/⚠️)
- Replacement code recommendations
- Migration guidance documents

**Blocks:**
- Implementation if CRITICAL violations detected
- Code merge if deprecated patterns found
- Deployment if app/ directory conventions violated
