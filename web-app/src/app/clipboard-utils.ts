import { getLogger } from "fusion/logging";
import { Note } from "@/model/Note";
import { PageViewState } from "@/views/page/PageViewState";

let log = getLogger('clipboard-utils');

function escapeHtml(text: string): string {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function isImageOnlyNote(note: Note): boolean {
    return !!note.content.image?.path
        && !note.text.trim()
        && !note.content.url
        && !note.content.page_ref;
}

export function selectedNotesToPlainText(selectedNotes: Note[]): string {
    let parts: string[] = [];
    for (const note of selectedNotes) {
        let lines: string[] = [];
        const text = note.text.trim();
        const url = (note.content.url ?? '').trim();
        if (text) lines.push(text);
        if (url) lines.push(url);
        if (lines.length > 0) {
            parts.push(lines.join('\n'));
        }
    }
    return parts.join('\n\n');
}

export function selectedNotesToHtml(selectedNotes: Note[]): string {
    let blocks: string[] = [];
    for (const note of selectedNotes) {
        const text = note.text.trim();
        const url = (note.content.url ?? '').trim();
        if (url && text) {
            const escapedText = escapeHtml(text).replace(/\n/g, '<br>');
            blocks.push(`<div><a href="${escapeHtml(url)}">${escapedText}</a></div>`);
        } else if (url) {
            blocks.push(`<div><a href="${escapeHtml(url)}">${escapeHtml(url)}</a></div>`);
        } else if (text) {
            blocks.push(`<div>${escapeHtml(text).replace(/\n/g, '<br>')}</div>`);
        }
    }
    return blocks.join('');
}

async function writeImageNoteToClipboard(note: Note, pageVS: PageViewState): Promise<boolean> {
    const path = note.content.image?.path;
    const imageUrl = path ? pageVS.fileUrlsByPath.get(path) : undefined;
    if (!imageUrl || !navigator.clipboard.write) {
        return false;
    }

    // Reuse the already-loaded <img> element from the DOM (avoids CORS issues with fetch)
    const img = document.querySelector(`img[src="${imageUrl}"]`) as HTMLImageElement | null;
    if (!img || !img.naturalWidth) {
        return false;
    }

    const canvas = new OffscreenCanvas(img.naturalWidth, img.naturalHeight);
    const ctx = canvas.getContext('2d');
    if (!ctx) {
        throw new Error('Could not create canvas context for clipboard image');
    }
    ctx.drawImage(img, 0, 0);
    const pngBlob = await canvas.convertToBlob({ type: 'image/png' });

    await navigator.clipboard.write([
        new ClipboardItem({ 'image/png': pngBlob }),
    ]);
    return true;
}

export function writeSelectedNotesToOsClipboard(selectedNotes: Note[], pageVS: PageViewState) {
    if (selectedNotes.length === 1 && isImageOnlyNote(selectedNotes[0])) {
        writeImageNoteToClipboard(selectedNotes[0], pageVS).catch((error) => {
            log.error('Failed to copy image note to OS clipboard:', error);
        });
        return;
    }

    const text = selectedNotesToPlainText(selectedNotes);
    if (!text) {
        return;
    }

    const html = selectedNotesToHtml(selectedNotes);
    if (navigator.clipboard.write && html) {
        navigator.clipboard.write([
            new ClipboardItem({
                'text/plain': new Blob([text], { type: 'text/plain' }),
                'text/html': new Blob([html], { type: 'text/html' }),
            }),
        ]).catch((error) => {
            log.error('Failed to copy rich content to OS clipboard:', error);
            navigator.clipboard.writeText(text).catch((fallbackError) => {
                log.error('Failed to copy text to OS clipboard:', fallbackError);
            });
        });
    } else {
        navigator.clipboard.writeText(text).catch((error) => {
            log.error('Failed to copy text to OS clipboard:', error);
        });
    }
}
