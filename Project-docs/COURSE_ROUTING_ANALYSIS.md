# Course Routing Analysis

## 1. Overview
This document analyzes how Course URLs and routing are resolved across the frontend and backend architectures in the TELITE LMS repository, specifically tracing `useParams()` usage and backend lookup mechanisms.

## 2. Frontend Routing Resolution
A comprehensive search of the frontend codebase (`telite-frontend`) reveals that **course slugs are NOT used for URL routing**.
Instead, the architecture relies exclusively on the surrogate database key (`course_id`).

### Evidence (`telite-frontend/src/routes/org_router.jsx`):
Course authoring routes are defined using the `course_id`:
```jsx
<Route
  path="builder/:course_id"
  element={
    <ProtectedRoute session={session} allowRoles={["category_admin"]}>
      <CourseBuilderPage session={session} onLogout={onLogout} />
    </ProtectedRoute>
  }
/>
```

### Trace of `useParams()`:
- `CourseBuilderPage.jsx`: Extracts `course_id` (`const { course_id } = useParams();`).
- `LessonBlockEditor.jsx`: Extracts `slug` (`const { slug } = useParams();`), but tracing the route hierarchy (`/categories/:slug/builder/:course_id`) confirms this `slug` refers to `category_slug`, not the course slug.
- `LearnerPage.jsx`: The learner view does not use URL parameters to resolve courses. Instead, it maintains local state (`const [activeCourseId, setActiveCourseId] = useState(null)`) and renders the `LearnerPlayer` modal overlay dynamically using `course_id`.

## 3. Backend API Resolution
Backend endpoints match the frontend's reliance on `course_id`. A search across `telite-backend/app/api/routes` confirms that courses are resolved by their `course_id` in API paths.

### Evidence:
- Authoring endpoints: `@authoring_router.post("/courses/{course_id}/versions")`
- Management endpoints: `@management_router.patch("/categories/{category_slug}/courses/{course_id}")`

There are no endpoints mapping directly to `courses/:course_slug`.

## 4. Impact of Duplicate Slugs on Routing
**Question:** Would duplicate slugs across organizations or categories break existing routing?
**Answer:** No. Because neither the frontend routing nor the backend API path resolution relies on the course slug, having duplicate course slugs would have **zero impact** on existing routing or URL resolution. The system routes exclusively on `course_id`. 
*(Note: Duplicate slugs would break database inserts due to global unique constraints, but routing itself is completely insulated from this).*

## 5. Contradiction with Previous Reports
The previously generated `COURSE_IDENTITY_AUDIT.md` contains a significant inaccuracy. It states:
> *"Routing & API Canonical Identity: `slug`. Most external systems and frontend clients address the course via its `slug`."*

This is **false**. Verified repository evidence shows that frontend clients and backend APIs address courses via `course_id`. The course `slug` is essentially an unused artifact in the context of routing.
