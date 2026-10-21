import { canonicalKey, checkPortableName } from 'sivkit/util/portablePath';
import { CANVAS_EXT } from '@/app/constants';
import type { Page } from '@/model/Page';

const REASON_MESSAGES: Record<string, string> = {
  empty: 'Enter a name.',
  part_length: 'This name is too long.',
  char: 'A name can\'t contain / \\ < > : " | ? or *.',
  control: 'This name contains an invisible or control character.',
  reserved: 'This name is reserved on Windows.',
};

export interface NormalizedPageName {
  name: string;
  error: string | null;
}

/** The typed name trimmed and NFC-normalized, with the reason it can't be a
 * page file name on all systems (or null). */
export function normalizePageName(raw: string): NormalizedPageName {
  const name = raw.trim().normalize('NFC');
  const reason = name ? checkPortableName(name + CANVAS_EXT) : 'empty';
  const error = reason ? REASON_MESSAGES[reason] ?? `This name can't be a file name (${reason}).` : null;
  return { name, error };
}

/** The path of the page `name` in `folder` ('' for the project root). */
export function pagePath(folder: string, name: string): string {
  return (folder ? folder + '/' : '') + name + CANVAS_EXT;
}

/** True if a page other than `exceptPageId` has `path` as a case-insensitive
 * file system would see it. */
export function isPagePathTaken(pages: Iterable<Page>, path: string, exceptPageId?: string): boolean {
  const key = canonicalKey(path);
  for (const page of pages) {
    if (page.id !== exceptPageId && canonicalKey(page.path) === key) return true;
  }
  return false;
}
