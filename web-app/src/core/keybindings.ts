import { commands } from "@/core/commands";

export const DEFAULT_KEYBINDINGS = [
    // No modifier commands (assuming "when: noModifiers" is checked in contextConditionFulfilled):
    {
        key: 'n',
        command: commands.createNewNote.name,
        when: 'canvasFocus'
    },
    {
        key: 'e',
        command: commands.editSelectedNote.name,
        when: 'canvasFocus'
    },
    {
        key: 'l',
        command: commands.createArrow.name,
        when: 'canvasFocus'
    },
    {
        key: 'a',
        command: commands.autoSizeSelectedNotes.name,
        when: 'canvasFocus'
    },
    {
        key: 'escape',
        command: commands.cancelPageAction.name,
        when: 'canvasFocus'
    },
    {
        key: 'h',
        command: commands.showHelp.name,
        when: 'canvasFocus'
    },
    {
        key: 'delete',
        command: commands.deleteSelectedElements.name,
        when: 'canvasFocus'
    },
    {
        key: '1',
        command: commands.colorSelectedElementsPrimary.name,
        when: 'canvasFocus'
    },
    {
        key: '2',
        command: commands.colorSelectedElementsSuccess.name,
        when: 'canvasFocus'
    },
    {
        key: '3',
        command: commands.colorSelectedElementsError.name,
        when: 'canvasFocus'
    },
    {
        key: '4',
        command: commands.colorSelectedElementsSurfaceDim.name,
        when: 'canvasFocus'
    },
    {
        key: '5',
        command: commands.setNoteBackgroundToTransparent.name,
        when: 'canvasFocus'
    },
    {
        key: 'p',
        command: commands.createNewPage.name,
        when: 'canvasFocus'
    },

    {
        key: 'ctrl+=',
        command: commands.pageZoomIn.name,
        when: 'canvasFocus'
    },
    {
        key: 'ctrl+-',
        command: commands.pageZoomOut.name,
        when: 'canvasFocus'
    },
    {
        key: 'ctrl+0',
        command: commands.pageZoomReset.name,
        when: 'canvasFocus'
    },
    {
        key: 'ctrl+a',
        command: commands.selectAll.name,
        when: 'canvasFocus'
    },
    // Copy
    {
        key: 'ctrl+c',
        command: commands.copySelectedElements.name,
        when: 'canvasFocus'
    },
    {
        key: 'cmd+c',
        command: commands.copySelectedElements.name,
        when: 'canvasFocus'
    },
    // Cut
    {
        key: 'ctrl+x',
        command: commands.cutSelectedElements.name,
        when: 'canvasFocus'
    },
    {
        key: 'cmd+x',
        command: commands.cutSelectedElements.name,
        when: 'canvasFocus'
    },
    // Paste (internal clipboard)
    {
        key: 'ctrl+v',
        command: commands.paste.name,
        when: 'canvasFocus'
    },
    {
        key: 'cmd+v',
        command: commands.paste.name,
        when: 'canvasFocus'
    },
    {
        key: 'ctrl+e',
        command: commands.openPageProperties.name,
        when: 'canvasFocus'
    },
    {
        key: 'ctrl+shift+y',  // tmp, could not find a sane shortcut
        command: commands.createNewPage.name,
        when: 'canvasFocus'
    },
    {
        key: 'ctrl+shift+u',  // tmp, could not find a sane shortcut
        command: commands.storeStateToClipboard.name,
        when: 'canvasFocus'
    },
    {
        key: 'ctrl+shift+v',
        command: commands.pasteSpecial.name,
        when: 'canvasFocus'
    },
    {
        key: 'ctrl+p',
        command: commands.openPagePalette.name,
        when: ''
    },
    {
        key: 'ctrl+shift+p',
        command: commands.openCommandPalette.name,
        when: ''
    },
    {
        key: 'ctrl+alt+p',
        command: commands.openCommandPaletteWithProjectSwitch.name,
        when: ''
    },
    // Undo / Redo
    {
        key: 'ctrl+z',
        command: commands.undo.name,
        when: 'canvasFocus'
    },
    {
        key: 'ctrl+shift+z',
        command: commands.redo.name,
        when: 'canvasFocus'
    },
    {
        key: 'ctrl+y',
        command: commands.redo.name,
        when: 'canvasFocus'
    },
    // macOS-friendly variants
    {
        key: 'cmd+z',
        command: commands.undo.name,
        when: 'canvasFocus'
    },
    {
        key: 'cmd+shift+z',
        command: commands.redo.name,
        when: 'canvasFocus'
    },
    {
        key: 'backspace',
        command: commands.toggleLastPage.name,
        when: 'canvasFocus'
    }
]
