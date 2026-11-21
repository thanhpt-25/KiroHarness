# Requirements Document

## Introduction

This example spec describes a small URL shortener. It shows the expected
format of a Kiro requirements document: an introduction, a glossary, and
numbered requirements with user stories and EARS acceptance criteria. Replace
it with your own feature or delete the `example-feature` directory.

## Glossary

- **Shortener_Service**: The HTTP service that creates and resolves short links.
- **Short_Link**: A 7-character code that maps to one target URL.
- **Link_Store**: The database table that stores each Short_Link and its target URL.

## Requirements

### Requirement 1: Create Short Links

**User Story:** As a marketer, I want to turn a long URL into a short link, so that I can share it in places with character limits.

#### Acceptance Criteria

1. WHEN a client submits a valid http or https URL, THE Shortener_Service SHALL store a new Short_Link in the Link_Store and return it with status 201.
2. IF a client submits a URL that is not a valid http or https URL, THEN THE Shortener_Service SHALL return status 400 with a message naming the invalid field.
3. THE Shortener_Service SHALL generate each Short_Link as 7 characters from the letters a to z, A to Z, and the digits 0 to 9.

### Requirement 2: Resolve Short Links

**User Story:** As a reader, I want a short link to take me to the original page, so that I can read what was shared.

#### Acceptance Criteria

1. WHEN a client requests an existing Short_Link, THE Shortener_Service SHALL redirect to the target URL with status 301.
2. IF a client requests a Short_Link that is not in the Link_Store, THEN THE Shortener_Service SHALL return status 404.
3. WHILE the Link_Store is unavailable, THE Shortener_Service SHALL return status 503 for every resolve request.
