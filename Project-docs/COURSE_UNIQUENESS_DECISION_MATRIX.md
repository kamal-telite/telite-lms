# Course Uniqueness Decision Matrix

| Option | Domain Driven Design (DDD) | Multi-Tenant Compatibility | Routing Impact | Scalability & Future-Proofing | Maintainability (Category Moves) | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Global Slug (`slug`)** | **Poor.** Ignores tenant boundaries. | **Fail.** Tenants collide on generic names. | **Good.** Shortest possible URLs. | **Poor.** Will break in marketplace scaling. | **Good.** Category moves don't affect slug. | **REJECTED** |
| **Category-Scoped (`org_id + category_slug + slug`)** | **Poor.** Category is a mutable relationship, not identity. | **Pass.** Fixes cross-tenant collisions. | **Neutral.** URLs require category in path. | **Fair.** Restrictive for global catalogs. | **Fail.** Moving categories breaks identity/URLs. | **REJECTED** |
| **Tenant-Scoped (`org_id + slug`)** | **Excellent.** Org is the true root aggregate. | **Pass.** Perfect tenant isolation. | **Good.** Compatible with current `/courses/{id}` routing. | **Excellent.** Supports AI/Marketplace scopes perfectly. | **Good.** Courses can change categories freely. | **APPROVED** |

### Summary
The matrix objectively proves that **Tenant-Scoped (`org_id + slug`)** is the only valid choice. It satisfies strict multi-tenant isolation (fixing RC-003) while ensuring long-term maintainability, as courses can be freely updated or moved between categories without breaking their fundamental identity constraint.
