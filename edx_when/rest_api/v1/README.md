### 📘 `GET /api/edx_when/v1/user-dates/`
### 📘 `GET /api/edx_when/v1/user-dates/{course_id}`

### Description
Retrieves user-specific dates for a specific course or all enrolled courses. in Open edX. Dates may include due dates, release dates, etc. Supports optional filtering.

---

### 🔐 Authentication
- Required: ✅ Yes
- Methods: 
  - `SessionAuthentication`
  - `JwtAuthentication`

User must be authenticated and have access to the course.

---

### 📥 Path Parameters

| Name       | Type   | Required | Description                     |
|------------|--------|----------|---------------------------------|
| course_id  | string | ❌ No    | Course ID in URL-encoded format |

---

### 🧾 Query Parameters (optional)

| Name        | Type   | Description                                                             |
|-------------|--------|-------------------------------------------------------------------------|
| block_types | string | Comma-separated list of block types (e.g., `problem,html`)              |
| block_keys  | string | Comma-separated list of block keys (usage IDs or block identifiers)     |
| date_types  | string | Comma-separated list of date types (e.g., `start,due`)               |

---

### ✅ Response (200 OK)

```json
{
  "block-v1:edX+DemoX+2023+type@problem+block@123abc": "2025-07-01T12:00:00Z",
  "block-v1:edX+DemoX+2023+type@video+block@456def": "2025-07-03T09:30:00Z"
}
```

- A dictionary where keys are block identifiers and values are ISO 8601 date strings.

---

### 🔒 Response Codes

| Code | Meaning                          |
|------|----------------------------------|
| 200  | Success                          |
| 401  | Unauthorized (not logged in)     |
| 403  | Forbidden (no access to course)  |

---

### 💡 Usage Example

#### Requests
```http
GET /api/edx_when/v1/user-dates/
```

```http
GET /api/edx_when/v1/user-dates/course-v1:edX+DemoX+2023
```

#### With Filters
```http
GET /api/edx_when/v1/user-dates/?block_types=problem,video&date_types=due
```

```http
GET /api/edx_when/v1/user-dates/course-v1:edX+DemoX+2023?block_types=problem,video&date_types=due
```

#### Curl Example
```bash
curl -X GET "https://your-domain.org/api/edx_when/v1/user-dates/?block_types=problem&date_types=due" \
  -H "Authorization: Bearer <your_jwt_token>"
```

```bash
curl -X GET "https://your-domain.org/api/edx_when/v1/user-dates/course-v1:edX+DemoX+2023?block_types=problem&date_types=due" \
  -H "Authorization: Bearer <your_jwt_token>"
```

---
