# Tallyfy API Reference - ACTUAL Implementation

## ⚠️ CRITICAL: Based on api-v2 Production Codebase

This reference is based on direct analysis of the Tallyfy api-v2 implementation,
NOT documentation. Use these exact values for successful integration.

## Field Types (from BaseCapture.php)

```php
public static $field_types = [
    'text',          // Short text (max 255 chars)
    'textarea',      // Long text (max 6000 chars)
    'radio',         // Radio buttons
    'dropdown',      // Single select dropdown
    'multiselect',   // Multiple select
    'date',          // Date picker
    'email',         // Email with validation
    'file',          // File upload
    'table',         // Table/grid
    'assignees_form',// User/guest assignment
];
```

## Database Schema

### Templates (core.checklists)
- `id`: VARCHAR(32) - Hash string ID
- `organization_id`: VARCHAR(32) - Tenant ID
- `title`: VARCHAR(250) - Template name
- `timeline_id`: VARCHAR(32) - Version tracking
- `version`: INTEGER - Version number

### Processes (core.runs)
- `id`: VARCHAR(32) - Hash string ID
- `checklist_id`: VARCHAR(32) - Template reference
- `name`: TEXT - Process instance name
- `status`: TEXT - Process state

### Form Fields (core.captures)
- `id`: VARCHAR(32) - Hash string ID
- `field_type`: TEXT - From $field_types array
- `class_id`: VARCHAR(32) - Step or checklist ID
- `options`: TEXT - JSON for dropdowns
- `field_validation`: TEXT - Laravel rules

## API Endpoints

### Templates
```
GET    /api/organizations/{org}/checklists
POST   /api/organizations/{org}/checklists
GET    /api/organizations/{org}/checklists/{id}
PUT    /api/organizations/{org}/checklists/{id}
DELETE /api/organizations/{org}/checklists/{id}
```

### Processes
```
GET    /api/organizations/{org}/runs
POST   /api/organizations/{org}/runs
GET    /api/organizations/{org}/runs/{id}
PUT    /api/organizations/{org}/runs/{id}
```

## Request Payloads

### Create Template
```json
{
  "title": "Template Name",
  "summary": "Description",
  "type": "template",
  "owner_id": 123,
  "prerun": [
    {
      "label": "Field Label",
      "field_type": "text",
      "required": true,
      "guidance": "Help text",
      "field_validation": "numeric|min:0|max:100"
    }
  ]
}
```

### Launch Process
```json
{
  "checklist_id": "abc123...",
  "name": "Process Name",
  "owner_id": 123,
  "prerun_data": {
    "field_id": "value"
  }
}
```

## Critical Implementation Notes

1. **IDs are 32-character strings**, not integers (except users/guests)
2. **Organization ID required** in all API paths
3. **Prerun fields** are captures with checklist class_id
4. **No "number" field type** - use text with numeric validation
5. **Field validation** uses Laravel rules, not custom type system
6. **Multi-tenancy** enforced at API route level
7. **Versioning** via timeline_id and version fields
8. **No X-Tallyfy-Client header** required

## Common Mistakes to Avoid

❌ Using 'short_text' → ✅ Use 'text'
❌ Using 'long_text' → ✅ Use 'textarea'
❌ Using 'radio_buttons' → ✅ Use 'radio'
❌ Using 'checklist' → ✅ Use 'multiselect'
❌ Using 'file_upload' → ✅ Use 'file'
❌ Using integer IDs → ✅ Use 32-char strings
❌ Missing org_id in path → ✅ Include /organizations/{org_id}/
❌ Using 'prerun' array → ✅ Use 'prerun_data' object
