# PulseBoard Product Requirements

## Authentication

- Users must sign in with email and password.
- Users must reset their password using their registered email.
- Sessions shall expire after 24 hours of inactivity.

## Roles and access

- Administrators must manage user roles.
- Members must only edit projects to which they belong.

## Projects and tasks

- Managers must create projects with a name and description.
- Managers must assign tasks to project members.
- Members should update task status to TODO, IN_PROGRESS, BLOCKED, or DONE.
- Every task must retain a reference to its originating requirement.

## Notifications and API

- The system must notify an assignee when a task is assigned.
- The API shall reject unauthenticated requests with HTTP 401.
- The task API must return validation errors as structured JSON.
