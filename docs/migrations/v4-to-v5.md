# V4 to V5 Migration

Migration from V4 format (`.pam4.json`) to the current canvas format (`.canvas.html`) with type unification, color role conversion, composite ID flattening, arrow schema restructuring, and image metadata migration.

This migration is **automatically performed** by the `MigrationManager.do_all_migrations()` method (unlike V2→V3 and V3→V4 which require manual invocation due to ambiguous file extensions).

## V4 FOLDER STRUCTURE

Page files have `.pam4.json` extensions. The project structure is flat with all page files in the root directory.

Filenames encode the page name and ID: `<slugified_page_name>-<page_id>.pam4.json`

Example V4 page file:
```json
{
    "id": "bed53cfd",
    "name": "Demo page",
    "created": "2022-09-17T15:47:38+03:00",
    "modified": "2022-09-17T15:47:44+03:00",
    "type_name": "Page",
    "notes": [
        {
            "id": ["bed53cfd", "073e6bbb"],
            "geometry": [30, 500, 320, 50],
            "style": {
                "color": [0, 0.64, 0.235, 1],
                "background_color": [0, 1, 0, 0.1]
            },
            "content": { "text": "New note" },
            "metadata": {},
            "created": "2022-09-17T15:48:20+03:00",
            "modified": "2022-09-17T15:48:20+03:00",
            "tags": [],
            "type_name": "TextNote"
        }
    ],
    "arrows": [
        {
            "id": ["bed53cfd", "b9b29675"],
            "tail_coords": null,
            "tail_note_id": "256bbc5e",
            "tail_anchor": "MID_RIGHT",
            "mid_point_coords": [],
            "head_coords": null,
            "head_note_id": "fb299d0b",
            "head_anchor": "MID_LEFT",
            "color": [0, 0, 1, 1],
            "line_type": null,
            "line_thickness": 1.5,
            "line_function_name": "bezier_cubic",
            "head_shape": null,
            "tail_shape": null,
            "type_name": "Arrow"
        }
    ]
}
```

### V4 note types

V4 has multiple concrete note types distinguished by `type_name`:
- `TextNote` – plain text notes
- `ImageNote` – image-only notes (content has `local_image_url`, metadata has `image_size`/`image_md5`)
- `CardNote` – card notes with both text and image (content has `text`, `image_url`, `local_image_url`)
- `ScriptNote` – notes with script paths (content has `script_path`, `text`)
- `OtherPageListNote` – auto-generated project index header

### V4 color format

Colors are stored as RGBA arrays with **normalized float channels** (0.0–1.0):
```json
"style": {
    "color": [0, 0, 1, 1],
    "background_color": [0, 0, 1, 0.1]
}
```

Arrow colors are stored at the element root level (not inside `style`):
```json
"color": [0, 0, 1, 1]
```

### V4 ID format

Element IDs are **composite arrays** of `[page_id, own_id]`:
```json
"id": ["bed53cfd", "073e6bbb"]
```

Arrow endpoint references (`tail_note_id`, `head_note_id`) are **own IDs only** (without page prefix):
```json
"tail_note_id": "256bbc5e"
```

### V4 image content

Two URL fields exist in `content`:
- `local_image_url` – the primary image reference, either:
  - An internal pamet URL: `"pamet:/p/__pasted_images__/media/[03a3230e].jpg"`
  - An absolute filesystem path: `"/home/p10/test_images/image.jpg"`
- `image_url` – redundant copy of the same URL (present on some notes, not all)

Image dimensions live in `metadata`:
```json
"metadata": {
    "image_size": [1920, 1177],
    "image_md5": "cff27e6a4e9659173c43ee138685c9ce"
}
```

## V4 MIGRATION OPERATIONS

### 1. Composite ID flattening

V4 composite `[page_id, own_id]` arrays are converted to flat string IDs:
```python
# V4: "id": ["bed53cfd", "073e6bbb"]
# V5: "id": "bed53cfd-073e6bbb", "parent_id": "bed53cfd"
```

A new `parent_id` field is added, set to the page_id extracted from the composite ID. This aligns with the Entity base class which uses `parent_id` for hierarchy.

### 2. Color role conversion

RGBA float arrays are converted to **named color roles** using closest-color Euclidean distance matching:

| Role | RGBA (normalized) | Description |
|------|-------------------|-------------|
| `primary` | `[0.0, 0.0, 1.0, 0.1]` | Default note background |
| `onPrimary` | `[0.0, 0.0, 1.0, 1.0]` | Default text color |
| `error` | `[1.0, 0.0, 0.0, 0.1]` | Error background |
| `onError` | `[1.0, 0.0, 0.0, 1.0]` | Error text |
| `success` | `[0.0, 1.0, 0.0, 0.1]` | Success background |
| `onSuccess` | `[0.0, 0.64, 0.235, 1.0]` | Success text |
| `surfaceDim` | `[0.0, 0.0, 0.0, 0.1]` | Dim surface |
| `onSurface` | `[0.0, 0.0, 0.0, 1.0]` | Surface text |
| `transparent` | `[0.0, 0.0, 0.0, 0.0]` | Fully transparent |

For notes:
```python
# V4: style.color → V5: style.color_role
# V4: style.background_color → V5: style.background_color_role
```

Missing colors default to `onPrimary` (text) and `primary` (background).

Legacy raw RGBA arrays are removed from `style` after role assignment.

For arrows: the root-level `color` field is converted to `style.color_role` using the same `legacy_normalized_rgba_to_role()` mapping (Euclidean distance in normalized RGBA space). Both the TypeScript and Python implementations use the same algorithm and hardcoded palette.

### 3. Note type unification

All legacy note types are unified to `CardNote`:
```python
# V4 type_name: "TextNote" | "ImageNote" | "ScriptNote" | "CardNote"
# V5 type_name: "CardNote"
```

The `OtherPageListNote` type is also converted to `CardNote` with special handling:
```python
# V5:
element.type_name = "CardNote"
element.metadata.is_project_index_header = True
element.content.text = "Project links index (double-click to generate missing links, for e.g. new pages)"
element.style.color_role = "onSurface"
element.style.background_color_role = "surfaceDim"
```

### 4. Image metadata migration

Image content is restructured from scattered fields into a unified `content.image` object:

```python
# V4:
#   content.local_image_url = "pamet:/p/__pasted_images__/media/[03a3230e].jpg"
#   content.image_url = "/home/p10/test_images/image.jpg"  (redundant, removed)
#   metadata.image_size = [1920, 1177]
#   metadata.image_md5 = "cff27e6a..."

# V5:
#   content.image = { "url": <converted_url>, "width": 1920, "height": 1177 }
```

URL conversion rules:
- **Internal pamet URLs**: `"pamet:/p/..."` → `"project:/p/..."`
- **Filesystem paths**: `"/home/p10/image.jpg"` → `"project:/desktop/fs/home/p10/image.jpg"`

Legacy fields removed: `content.local_image_url`, `content.image_url`, `metadata.image_size`, `metadata.image_md5`

Missing `image_size` defaults to `[0, 0]` with a warning logged.

During conversion, notes with `content.image` are immediately processed:
- Local files (resolved from the V4 URL scheme) under the old internal store (`.pamet/media/`) or outside the repo are **copied into `<repo>/images/`**. Images already living in user-facing folders under the repo root stay in place.
- The note's `content.image` is replaced with an inline reference: `content.image: { path, width, height, hash }` — the SHA-256 content hash (truncated) and real dimensions (via Pillow, with V4 metadata fallback).
- Multiple notes referencing the same source file share the same inline reference (dedup by source path).
- External (http/https) URLs are left as-is.
- Missing files produce an error annotation in `content.text`.

### 5. Internal link URL rewrite

Internal page links in `content.url` are converted to structured `page_ref` objects:
```python
# V4: content.url = "pamet:/p/<page_id>"
# V5: content.page_ref = { "id": "<page_id>", "path": "<page_name>.canvas.html" }
#      content.text = "<target page name>"   (or "(deleted <page_id>)" if missing)
```

The `content.url` field is removed. `content.text` is set to the target page's name (matching the TS `CardNote.createInternalLinkNote()` behaviour). If the target page is not found during migration, the text is set to `"(deleted <page_id>)"` (matching the TS `linkUpdatesForPageDelete()` convention).

### 6. Arrow schema restructuring

The flat V4 arrow format is restructured into nested endpoint objects:

```python
# V4:
{
    "tail_coords": null,
    "tail_note_id": "256bbc5e",
    "tail_anchor": "MID_RIGHT",
    "mid_point_coords": [[-150, -380]],
    "head_coords": null,
    "head_note_id": "fb299d0b",
    "head_anchor": "MID_LEFT",
    "color": [0, 0, 1, 1],
    "line_type": null,
    "line_thickness": 1.5,
    "line_function_name": "bezier_cubic",
    "head_shape": null,
    "tail_shape": null
}

# V5:
{
    "tail": {
        "position": null,
        "note_anchor_id": "bed53cfd-256bbc5e",
        "note_anchor_type": "mid_right"
    },
    "head": {
        "position": null,
        "note_anchor_id": "bed53cfd-fb299d0b",
        "note_anchor_type": "mid_left"
    },
    "mid_points": [[-150, -380]],
    "style": {
        "color_role": "onPrimary",
        "line_type": "solid",
        "thickness": 1.5,
        "line_function": "bezier_cubic",
        "head_shape": "arrow",
        "tail_shape": "arrow"
    }
}
```

Key transformations:
- **Endpoint note IDs** are prefixed with `page_id-` to match the flattened note ID format
- **Anchor types** are lowercased: `"MID_RIGHT"` → `"mid_right"`
- **Midpoints** are renamed: `mid_point_coords` → `mid_points`
- **Style properties** are consolidated into a `style` object with defaults for null values:
  - `line_type`: null → `"solid"`
  - `head_shape`/`tail_shape`: null → `"arrow"`
  - `line_function_name` → `line_function`
  - `line_thickness` → `thickness`
- **Arrow `color`** (root-level RGBA) → `style.color_role` via role mapping

Legacy flat arrow fields are removed after restructuring.

### 7. Miscellaneous cleanup

- `tags` field is removed from notes (was always `[]` in practice)
- Empty `content`, `metadata`, and `style` objects are ensured to exist on all elements
- `ScriptNote` content is preserved as-is in `content` (the `script_path` field remains)

## FILE PATH CHANGES

V4 and current canvas format both use flat file storage in the repository root directory:
```
repo_root/
  slug-page_id.pam4.json  →  <page_name>.canvas.html
```

The filename becomes name-based (with the page ID appended on collision). The `.canvas.html` file is an HTML document with the schema version in a `<meta>` tag and the JSON payload in a `<script>` tag.

### Post-migration (per-page)

Original `.pam4.json` files are backed up to `__migration_backup_v4_to_v5__/` with `.backup` suffix (unique ID appended if name collides), then deleted.

## POST-MIGRATION OPERATIONS (project-level)

Performed inside `migrate_v4_to_v5()` after all page files are converted:

### Repo properties migration

`migrate_repo_properties_file()` renames `.pamet/settings.json` → `.pamet/properties.json` and renames the `home_page` key to `home_page_id`.

### Backup layout migration

`migrate_backups_layout()` fixes legacy backup folder issues:
- Flattens nested `.pamet/backups/backups/` → `.pamet/backups/` (caused by a previous bug)
- Moves timestamp files (`last_backup_timestamp.txt`, `last_prune_timestamp.txt`) from `.pamet/` into `.pamet/backups/`
- Fixes doubled `+` in backup filenames (e.g. `++0200` → `+0200`) caused by incorrect timezone formatting

## OUTPUT FORMAT (Canvas)

Canvas files are valid HTML documents with the JSON payload in a `<script type="application/json" id="pamet-data">` tag and the schema version in a `<meta>` tag. The reader also accepts legacy plain-JSON files for backward compatibility.

JSON payload structure:

```json
{
  "id": "bed53cfd",
  "schema_version": 5,
  "name": "Demo page",
  "created": "2022-09-17T15:47:38+03:00",
  "modified": "2022-09-17T15:47:44+03:00",
  "type_name": "Page",
  "notes": [
    {
      "id": "bed53cfd-073e6bbb",
      "parent_id": "bed53cfd",
      "type_name": "CardNote",
      "geometry": [30, 500, 320, 50],
      "style": {
        "color_role": "onSuccess",
        "background_color_role": "success"
      },
      "content": {
        "text": "New note"
      },
      "metadata": {},
      "created": "2022-09-17T15:48:20+03:00",
      "modified": "2022-09-17T15:48:20+03:00"
    }
  ],
  "arrows": [
    {
      "id": "bed53cfd-b9b29675",
      "parent_id": "bed53cfd",
      "type_name": "Arrow",
      "tail": {
        "position": null,
        "note_anchor_id": "bed53cfd-256bbc5e",
        "note_anchor_type": "mid_right"
      },
      "head": {
        "position": null,
        "note_anchor_id": "bed53cfd-fb299d0b",
        "note_anchor_type": "mid_left"
      },
      "mid_points": [],
      "style": {
        "color_role": "onPrimary",
        "line_type": "solid",
        "thickness": 1.5,
        "line_function": "bezier_cubic",
        "head_shape": "arrow",
        "tail_shape": "arrow"
      }
    }
  ]
}
```

Image notes in V5 (after image migration):
```json
{
  "id": "bed53cfd-404c0810",
  "parent_id": "bed53cfd",
  "type_name": "CardNote",
  "geometry": [590, -580, 320, 120],
  "style": {
    "color_role": "onPrimary",
    "background_color_role": "primary"
  },
  "content": {
    "image": {
      "path": "images/[03a3230e].jpg",
      "width": 415,
      "height": 157,
      "hash": "<sha256-truncated>"
    }
  },
  "metadata": {},
  "created": "2023-01-21T19:43:40+02:00",
  "modified": "2023-01-21T19:43:40+02:00"
}
```

Image references are fully inline in the note's `content.image` — there are no separate `ImageItem`/`FileItem` entities.

## KNOWN ISSUES / IN-PROGRESS ITEMS

- **Color roles** – the Euclidean-distance mapping between legacy RGBA and roles is deterministic but lossy. Edge-case colors may map to unexpected roles.
- **Non-local image URLs** – external (http/https) image URLs are preserved as-is in `content.image`.
- **ScriptNote content preservation** – the `script_path` and `run_in_terminal` fields are carried through as-is inside `content`; no special V5 schema exists for scripts yet.

## NOTES

**Automatic migration**: Unlike V2→V3 and V3→V4 (which must be run manually due to ambiguous file extensions), V4→Canvas migration runs automatically on project open because `.pam4.json` files are unambiguous.

**Color mapping determinism**: The implementation uses Euclidean distance in RGBA space to find the closest role. The mapping is deterministic but lossy — any RGBA value not in the predefined set maps to its nearest neighbor.

**Page structure preserved**: Unlike V3→V4 which introduced page IDs and UUIDs, V4→V5 preserves existing page IDs and the `notes`/`arrows` split (though V5 also supports a `children` array combining both).

**Timestamps**: V4 timestamps are ISO 8601 strings (e.g., `"2022-09-17T15:47:38+03:00"`) and are preserved as-is in V5 (no format conversion, unlike V2→V3→V4 where timestamp format changed).
