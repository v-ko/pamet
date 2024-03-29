from fusion.util import Color

SELECTION_OVERLAY_COLOR = Color(1, 1, 0, 0.5)
ALIGNMENT_LINE_LENGTH = 120
LONG_PRESS_TIMEOUT = 0.3

MAX_RENDER_TIME = 0.017  # (s) ~60 fps

MOVE_SPEED = 1

DEFAULT_EYE_HEIGHT = 40

MIN_HEIGHT_SCALE = 0.2
MAX_HEIGHT_SCALE = 200

NO_SCALE_LINE_SPACING = 20

ALIGNMENT_GRID_UNIT = 10
AGU = ALIGNMENT_GRID_UNIT

NOTE_MARGIN = AGU / 2
DEFAULT_NOTE_WIDTH = 32 * AGU
DEFAULT_NOTE_HEIGHT = 16 * AGU
MIN_NOTE_WIDTH = 3 * AGU
MIN_NOTE_HEIGHT = 3 * AGU
MAX_NOTE_WIDTH = 192 * AGU
MAX_NOTE_HEIGHT = 192 * AGU

PREFERRED_TEXT_NOTE_ASPECT_RATIO = 5

MAX_AUTOSIZE_WIDTH = 1280  # 16:9
MAX_AUTOSIZE_HEIGHT = 405

DEFAULT_BG_COLOR = (0, 0, 1, 0.1)
DEFAULT_COLOR = (0, 0, 1, 1)

GREEN_FG_COLOR = (0, 0.64, 0.235, 1)

R_PALETTE = [0, 0.25, 0.5, 0.75, 1]
G_PALETTE = [0, 0.25, 0.5, 0.75, 1]
B_PALETTE = [0, 0.25, 0.5, 0.75, 1]
BG_ALPHA_PALETTE = [0, 0.055, 0.072, 0.1]

RESIZE_CIRCLE_RADIUS = 2 * AGU

ARROW_SELECTION_RADIUS = 10
ARROW_EDGE_RAIDUS = 25
DEFAULT_ARROW_THICKNESS = 1.5
ARROW_SELECTION_THICKNESS_DELTA = 3.5
CONTROL_POINT_RADIUS = 15
POTENTIAL_EDGE_RADIUS = CONTROL_POINT_RADIUS * 0.7

MAX_NAVIGATION_HISTORY = 10000

TOUR_PAGE_CONTENT = """# This is a tour page

It's a markdown file that accompanies the pamet page.
You can edit it by clicking the "Edit" button in the top right corner.

## Main feature of the tour - parallel navigation
When reading a tour page - when you scroll past a link to a pamet page - you'll get an instant preview.
Note that links split the page into segments, which get rendered separately.

### Example:
Scroll past [this link](pamet:/p/{page_id}/#eye_at=40/0/0) to view the center of the page.

.

.

.

.

.

.

.

And past [this one](pamet:/p/{page_id}/#eye_at=50/50/0) to view another position.
.

.

.

.

.

.

..

.

.

.

.

.

..

.

.

.

.

.

.
"""
