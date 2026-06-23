# Question Bank API Runtime Verification

## Question Banks - Create
### Role: platform_admin
- Status: 403
- Outcome: Denied (You do not have the required capability: manage_content)
### Role: super_admin
- Status: 200
- Outcome: Allowed (ID: 20)
### Role: category_admin
- Status: 403
- Outcome: Denied (You do not have the required capability: manage_content)
### Role: instructor
- Status: 403
- Outcome: Denied (You do not have the required capability: manage_content)
### Role: learner
- Status: 403
- Outcome: Denied (You do not have the required capability: manage_content)

## Tenant Isolation - Get Bank
Org 1 User -> Status 200
Org 2 User -> Status 404

## Questions - Create
### Role: platform_admin
- Status: 403
### Role: super_admin
- Status: 200
### Role: category_admin
- Status: 403
### Role: instructor
- Status: 403
### Role: learner
- Status: 403

## Questions - Update Draft
Update Draft -> Status 200

## Questions - Publish Question
Publish Question -> Status 200

## Questions - Attempt to Update without active draft
Update Active Published -> Status 400 (Invalid draft state)

## Questions - Create New Draft From Published
Create New Draft -> Status 200

## Questions - Archive Draft
Archive Draft -> Status 200

## Import Jobs - Create
### Role: platform_admin
- Status: 403
### Role: super_admin
- Status: 200
### Role: category_admin
- Status: 403
### Role: instructor
- Status: 403
### Role: learner
- Status: 403