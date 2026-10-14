# V3 to V4 Migration

Migration from V3 JSON format to V4 format with proper note typing, coordinate scaling, and arrow improvements.

## V3 FOLDER STRUCTURE

Page files have `.json` extensions. The project structure is flat with all page files in the root directory (no subdirectories).

File names carry the page name (`<page_name>.json`). Pages do not have IDs yet - they are identified by filename only.

Example V3 page file (mostly same as V2 but in json)
```json
{
  "is_displayed_first_on_startup": true,
  "notes": [
    {
      "id": 1,
      "x": 1.0,
      "y": -2.5,
      "width": 11.0,
      "height": 3.0,
      "text": "this_note_points_to:notes",
      "txt_col": [0, 0, 1, 1],
      "bg_col": [0, 0, 1, 0.1],
      "font_size": 1,
      "t_made": "10.4.2019 14:2:2",
      "t_mod": "10.4.2019 14:2:2",
      "tags": [],
      "links": [
        {
          "text": "",
          "to_id": 2,
          "cp": [12.25, -7.25]
        }
      ]
    }
  ]
}
```

### Text prefixes for special note types

V3 uses text prefixes to denote different note types:
- `this_note_points_to:<page_name>` - Internal page link
- `define_web_page_note:` - External web link (followed by `url=` and `name=` lines)
- `define_picture_note:<image_url>` - Image note
- `define_system_call_note:<script_path> <args>` - Script/command note

## V3 MIGRATION OPERATIONS

The migration parses `.json` files and produces `.pam4.json` files with transformed data and proper note types. Files remain in the repository root directory.

### Coordinate system scaling

All spatial properties are multiplied by `ONE_V3_COORD_UNIT_TO_V4 = 20` and snapped to grid:
- `x`, `y`, `width`, `height`
- Arrow control points (`cp`)

Overflow protection ensures coordinates stay within valid range (-2147483647 to 2147483647). Any coordinates outside this range are set to 1.

### Page ID generation

Pages get proper UUIDs generated from filename stem using `get_new_id(page_name)`.

Page timestamps (`datetime_created` and `datetime_modified`) are inferred from the earliest note creation time minus 10 seconds.

### Note ID transformation

V3 simple integer IDs are transformed to V4 composite IDs:
```python
note['id'] = (page_id, str(old_note_id))
```

Duplicate note IDs within a page are resolved using `new_id_for_legacy_note()` which generates deterministic IDs based on note_id + timestamp + content. Notes with duplicate IDs are tracked and arrows to/from them are removed.

### Property renaming and restructuring

Field renaming:
```python
note['color'] = note.pop('txt_col')
note['background_color'] = note.pop('bg_col')
```

Geometry consolidation:
```python
note['geometry'] = [
    note.pop('x'),
    note.pop('y'),
    note.pop('width'),
    note.pop('height')
]
```

Timestamp conversion:
```python
note['created'] = timestamp(datetime.strptime(t_made, TIME_FORMAT))
note['modified'] = timestamp(datetime.strptime(t_mod, TIME_FORMAT))
```

Timestamps are parsed from V3 format (`"10.4.2019 14:2:2"`) with local timezone applied, then converted to UTC timestamps.

Dropped fields: `font_size`

### Note type specialization

V3's text-prefix-based typing is converted to V4's proper class-based typing:

**Internal links** (TextNote with URL):
```python
# V3: text="this_note_points_to:PageName"
# V4:
note['type_name'] = 'TextNote'
note.url = 'PageName'  # Converted to proper URL in post-migration
```

**External links** (TextNote with URL):
```python
# V3: text="define_web_page_note:\nurl=https://...\nname=Link Text"
# V4:
note['type_name'] = 'TextNote'
note.url = 'https://...'
note.text = 'Link Text'
```

**Image notes**:
```python
# V3: text="define_picture_note:/path/to/image.png"
# V4:
note['type_name'] = 'ImageNote'
note.image_url = '/path/to/image.png'
note.local_image_url = '/path/to/image.png'
```

**Script notes**:
```python
# V3: text="define_system_call_note:/path/to/script arg1 arg2"
# V4:
note['type_name'] = 'ScriptNote'
note.script_path = '/path/to/script'
note.command_args = 'arg1 arg2'
note.text = 'define_system_call_note:/path/to/script arg1 arg2'
```

**Regular text notes**:
```python
# V3: text="Regular text"
# V4:
note['type_name'] = 'TextNote'
note.text = 'Regular text'
```

### Note size validation

Note dimensions are clamped to valid ranges:
- Width: `MIN_NOTE_WIDTH` to `MAX_NOTE_WIDTH`
- Height: `MIN_NOTE_HEIGHT` to `MAX_NOTE_HEIGHT`

Invalid sizes are logged and corrected automatically.

### Arrow extraction and enhancement

V3 arrows embedded in notes are extracted to V4 standalone arrow objects:

```python
# V3 (within note):
"links": [{"text": "", "to_id": 2, "cp": [12.25, -7.25]}]

# V4 (separate object):
{
  "id": (page_id, arrow_id),
  "page_id": page_id,
  "tail_note_id": source_note_id,
  "head_note_id": target_note_id,
  "tail_anchor_type": "MID_RIGHT",
  "head_anchor_type": "MID_LEFT",
  "midpoints": [[245.0, -145.0]]  # Scaled control point
}
```

Control points are scaled by `ONE_V3_COORD_UNIT_TO_V4` (20×).

Arrow anchor types are automatically inferred based on note positions:
- **Vertical alignment**: If notes are above/below each other, use `TOP_MID`/`BOTTOM_MID` anchors
- **Horizontal positioning**: If notes are left/right of each other, use `MID_LEFT`/`MID_RIGHT` anchors

Arrow IDs are deterministic based on `[tail_note_id, head_note_id]`. Duplicate arrows between the same two notes are removed.

Arrows to/from notes with duplicate IDs are removed entirely.

### State tracking

Migration state maintained per-page:
- `v3_note_checksum_by_page_name`: Note count per page (verification)

### File path changes

V3 and V4 both use flat file storage in the repository root directory. The difference is in file naming:

V3 filenames:
```
repo_root/
  page1.json
  page2.json
```

V4 filenames:
```
repo_root/
  page_name-<page_id>.pam4.json
  another_page-<page_id>.pam4.json
```

Filenames use slugified page names: `slugify(page.name, separator="_", max_length=100) + "-" + page.id + ".pam4.json"`

**Note**: The `/p/` path segment is part of the internal URL schema (e.g., `project:/page/<page_id>`), but files are NOT stored in a `p/` subdirectory on disk.

### Post-migration (per-page)

Original `.json` files are backed up to `__migration_backup_v3_to_v4__/` with `.backup` suffix (unique ID appended if needed), then deleted.

## POST-MIGRATION OPERATIONS (project-level)

These operations are performed after all individual page migrations are complete:

### Internal link fixing

Notes with internal page links have their `url` fields updated from page names to proper V4 page URLs:

- Reads all migrated V4 pages to build a `page_name → page_id` map
- Scans each page's notes for `url` fields containing page names (not full URLs)
- Converts page names to proper V4 page URLs: `"PageName"` → `"project:/page/<page_id>"`
- Writes back modified pages with proper JSON formatting

Only plain page names are converted. URLs starting with `http://`, `https://`, `project:/`, or `file://` are left unchanged.

## OUTPUT FORMAT (V4)

V4 pages have structured format with typed notes (pretty-printed, indent=4, ensure_ascii=False):

```json
{
  "id": "<page_uuid>",
  "name": "page_name",
  "datetime_created": 1234567890.123,
  "datetime_modified": 1234567890.123,
  "notes": [
    {
      "id": ["<page_id>", "note_id"],
      "type_name": "TextNote",
      "geometry": [x, y, width, height],
      "color": [r, g, b, a],
      "background_color": [r, g, b, a],
      "created": 1234567890.123,
      "modified": 1234567890.123,
      "text": "...",
      "url": "project:/page/<page_id>",
      "tags": []
    }
  ],
  "arrows": [
    {
      "id": ["<page_id>", "<arrow_id>"],
      "page_id": "<page_id>",
      "tail_note_id": "note_id",
      "head_note_id": "note_id",
      "tail_anchor_type": "MID_RIGHT",
      "head_anchor_type": "MID_LEFT",
      "midpoints": [[x, y]]
    }
  ]
}
```

Notes are typed objects loaded via `load_from_dict()` with proper class serialization.

## NOTES

**Media file handling**: Image URLs are preserved as-is. Actual media file organization happens in later migrations.

**Timezone handling**: Timestamps parsed with local timezone applied, then converted to UTC.

**ID determinism**: All generated IDs (notes, arrows, pages) are deterministic based on content/relationships, ensuring reproducible migrations.

**Error handling**: Missing timestamps trigger warnings but don't fail migration (current time used as fallback).
