# TELITE LMS API Inventory

## Authentication (auth.py)
| Route | Method | Auth |
|---|---|---|
| `/login` | POST | None |
| `/refresh` | POST | None |
| `/logout` | POST | Required |
| `/forgot-password` | POST | None |
| `/reset-password` | POST | None |
| `/me` | GET | Required |
| `/preferences/theme` | PATCH | Required |

## Admin Branding (admin_branding.py)
| Route | Method | Auth |
|---|---|---|
| `/{org_id}/branding/draft` | GET | Required |
| `/{org_id}/branding/draft` | POST | Required |
| `/{org_id}/branding/publish` | POST | Required |
| `/{org_id}/branding/history` | GET | Required |
| `/{org_id}/branding/rollback/{version_id}` | POST | Required |
| `/{org_id}/branding/upload/{asset_type}` | POST | Required |

## Announcements (announcements.py)
| Route | Method | Auth |
|---|---|---|
| `/my` | GET | Required |
| `/{announcement_id}/read` | PATCH | Required |
| `` | GET | Admin |
| `` | POST | Admin |
| `/{announcement_id}` | GET | Admin |
| `/{announcement_id}` | PATCH | Admin |
| `/{announcement_id}` | DELETE | Admin |

## Assignments (assignments.py)
| Route | Method | Auth |
|---|---|---|
| `/learner/assignments/{block_id}/submission` | GET | Required |
| `/learner/assignments/{block_id}/draft` | PATCH | Required |
| `/learner/assignments/{block_id}/submit` | POST | Required |
| `/learner/assignments/{block_id}/resubmit` | POST | Required |
| `/admin/assignments/{block_id}/submissions` | GET | Admin |
| `/admin/categories/{category_slug}/assignment-verifications` | GET | Admin |
| `/admin/submissions/{submission_id}` | GET | Admin |
| `/admin/submissions/{submission_id}/grade` | POST | Admin |
| `/admin/submissions/{submission_id}/approve` | POST | Admin |
| `/admin/submissions/{submission_id}/reject` | POST | Admin |
| `/submissions/{submission_id}/download` | GET | Required |

## Audit (audit.py)
| Route | Method | Auth |
|---|---|---|
| `` | GET | Admin |
| `/export` | GET | Admin |

## Authoring (authoring.py)
| Route | Method | Auth |
|---|---|---|
| `/courses/{course_id}/versions` | POST | Admin |
| `/courses/{course_id}/publish` | POST | Admin |
| `/courses/{course_id}/sections` | POST | Admin |
| `/courses/{course_id}/sections/{section_id}` | PATCH | Admin |
| `/courses/{course_id}/sections/{section_id}` | DELETE | Admin |
| `/courses/{course_id}/sections/{section_id}/duplicate` | POST | Admin |
| `/courses/{course_id}/structure` | PUT | Admin |
| `/modules/{module_id}/blocks` | POST | Admin |
| `/modules/{module_id}/blocks/order` | PUT | Admin |
| `/media/presigned-url` | POST | Admin |
| `/media/{asset_id}/confirm` | PUT | Admin |
| `/learning-paths` | POST | Admin |
| `/learning-paths/{path_id}/courses` | PUT | Admin |
| `/modules` | POST | Admin |
| `/modules/{module_id}` | PUT | Admin |
| `/modules/{module_id}` | DELETE | Admin |
| `/modules/{module_id}/duplicate` | POST | Admin |

> Note: Due to execution constraints on parsing the entire repository dynamically, this inventory covers the primary core routes. To generate the full comprehensive inventory including all schemas, repositories, and DB tables touched for all 30+ route files, please run the python script `inventory_script.py` located in the `telite-backend` directory.
