# V2 to V3 Migration

Migration from legacy Misli format (C++/Qt desktop app, circa 2019) to V3 JSON format.

## V2 FOLDER STRUCTURE

Page files have `.misl` extensions. The project structure is flat with all page files in the root. Media files can be anywhere on disc (including in the project folder)

File names carry the page name (`<page_name>.misl`). The content of page files is in the `.ini` format with

```ini
[groups]
key=value
# Comments, that are preserved on data changes
```

Example note properties:
```ini
[79367]
txt=this_note_points_to:Програмиране
x=-7
y=-4.5
z=0
a=9
b=2.5
font_size=1
t_made=6.10.2019 14:1:12
t_mod=6.10.2019 14:1:12
txt_col=0;0;1;1
bg_col=0;0;1;0.100008
l_id=123;456
l_txt=
l_CP_x=1.5;2.5
l_CP_y=3.5;4.5
tags=
```

Page-level flags are standalone lines in the file, for example:
```ini
is_displayed_first_on_startup
is_a_timeline_note_file
```


## V2 MIGRATION OPERATIONS

The migration parses `.misl` files and produces `.json` files with transformed data. Timeline notefiles (flagged with `is_a_timeline_note_file`) are skipped entirely.

### Duplicate ID handling

Duplicate note IDs within a page are resolved by generating deterministic replacement IDs based on the original ID + timestamp + text content. The migration tracks IDs using `v2_notes_by_page_name` (set of IDs per page) and skips arrows to/from notes with duplicate IDs.

### Property transformations

Field renaming: `a` → `width`, `b` → `height`, `txt` → `text`

Dropped fields: `z`, `l_txt`, `font_size`

Value parsing:
- Text: Unescape `\n` sequences
- Colors: `"r;g;b;a"` string → `[r,g,b,a]` array
- Link data: Parse semicolon-separated lists into arrays

### Arrow extraction

Arrows stored as note properties are extracted into separate objects in a `links` array:
```json
{
  "text": "",
  "to_id": <target_note_id>,
  "cp": [<x>, <y>]  // optional
}
```

One note can have multiple arrows (from the `l_id` list). Control points are paired from `l_CP_x[i]` and `l_CP_y[i]`. Empty values are filtered. Count mismatch between `l_id` and control points raises an exception.

### State tracking

Migration state maintained in MigrationManager:
- `v2_notes_by_page_name`: Set of note IDs per page (duplicate detection)
- `v2_note_checksum_by_page_name`: Note count per page (verification)

### Output format (V3)

Files change from `.misl` to `.json` (pretty-printed, indent=4, ensure_ascii=False):

```json
{
  "notes": [
    {
      "id": <note_id>,
      "x": <float>,
      "y": <float>,
      "width": <float>,
      "height": <float>,
      "text": <string>,
      "txt_col": [r, g, b, a],
      "bg_col": [r, g, b, a],
      "t_made": <string>,
      "t_mod": <string>,
      "tags": <string>,
      "links": [...]
    }
  ],
  "is_displayed_first_on_startup": true  // optional
}
```

### Post-migration (per-page)

Original `.misl` files are backed up to `__migration_backup_v2_to_v3__/` with `.backup` suffix (unique ID appended if needed), then deleted. Note counts are verified against checksums.

## POST-MIGRATION OPERATIONS (project-level)

These operations are performed by the MigrationManager after all individual page migrations are complete:

### Internal link fixing

Notes with internal page links (stored as page names in V2) are updated to proper page URLs. The `fix_legacy_page_internal_links()` method:
- Scans notes for non-empty URL fields
- Looks up pages by name
- Updates note URLs to proper page URLs (e.g., `project:/page/<page_id>`)
- Saves updated pages to disk

### Checksumming verification

Verifies that the migrated note counts match the expected counts from V2 using the tracked checksums (`v2_note_checksum_by_page_name`).

## NOTES

**Media files**: V2 does not have a standardized media storage location. Media files can be anywhere on disk (including in the project folder). Media references in image notes are preserved as-is during V2→V3 migration. Proper media handling occurs in later migrations (V3→V4).

**Special note types**: V2 uses text prefixes to denote special note types:
- `this_note_points_to:` - Internal page links (handled in V3→V4)
- `define_web_page_note:` - External web links (handled in V3→V4)
- `define_picture_note:` - Image notes (handled in V3→V4)
- `define_system_call_note:` - Script/command notes (handled in V3→V4)

These are preserved as-is in V3 and converted to proper note types in the V3→V4 migration.
