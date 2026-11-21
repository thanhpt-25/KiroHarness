---
inclusion: auto
name: api-design
description: Load when designing or changing HTTP or RPC API endpoints, request/response schemas, or API versioning.
---

# API Design

- API style: {{API_STYLE}}.
- Name resources with plural nouns and use standard HTTP methods and status codes.
- Validate every request body and query parameter at the boundary and return a
  clear error that names the invalid field.
- Never break an existing client: add fields instead of renaming or removing
  them, and introduce a new version for breaking changes.
- Document each endpoint's request, response, and error shapes next to the code.
- Paginate list endpoints and set a maximum page size.
