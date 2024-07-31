# Pamet
An infinite canvas for organizing information with text/images/links. Written using Qt for Python.

⚠ **Still in alpha** ⚠ - you'll probably encounter GUI bugs, but the data storage/saving is stable. Development is transitioning to web technologies for the front end currently. You can check out the progress [here](https://github.com/users/v-ko/projects/1)

## Installation

### Via desktop version via pip
Requires Python `>3.10`. If it's not available for your package manager(/app store) - you can use [pyenv](https://github.com/pyenv/pyenv).

`pip install pamet` , start with `pamet`

### From source
Will update the instructions soon. The app is transitioning to web technologies. The legacy desktop vesrsion is under minimal maintenence mode and will not be developed further.

## Usage
- Ctrl+shift+P for the command palette
- Double click to create a new note
- L to craete an arrow
- Click to select
- Long-press and drag to move selected notes/arrows
- Ctrl or shift to select multiple notes
- Ctrl+Shift to drag-select multiple notes
- Drag the lower right corner of a note to resize it
- Buttons 1,2,3,4 change the note color. 5 removes the background
* Selected notes get moved together and resized to the same size
* No manual saving is required
- Copy/paste/cut work as you'd expect
- Paste special with ctrl+shift+V (imports links and multiple notes) - will be improved

![screenshot](https://misli.org/static/presentation/pamet_demo_page_screenshot.png)

https://github.com/v-ko/pamet/assets/3106360/c1d0f848-4e98-4c20-8d5e-5c7764e9c9d4

## Development install
Clone the repo with `--recurse-submodules`, since the [Fusion](https://github.com/v-ko/fusion) library is integrated as a git submodule at dev time.

## Testing
There are unit tests for some of the functionality and testing for the actions(=controller) which are not precise but are quite useful for visual verification (+are [easy to generate](tests/actions/new_test_HOW_TO.md)).

![screenshot](http://misli.org/static/presentation/pamet_test_suite_demo.gif)

## Development state and future
Check some notes on the [development so far](development-history.md)

Currently the code documentation isn't updated, and typing annotations have to be completed in places.

Next goals in terms of features:
- Server for page sharing
- A minimal web app for viewing pages
- A minimal android app for viewing and limited input
