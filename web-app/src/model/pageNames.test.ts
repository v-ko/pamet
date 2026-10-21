/** @jest-environment node */
import type { Page } from '@/model/Page';
import { isPagePathTaken, normalizePageName, pagePath } from '@/model/pageNames';

test('normalizePageName trims, normalizes and refuses non-portable names', () => {
  expect(normalizePageName('  Cafe\u0301 ')).toEqual({ name: 'Café', error: null });
  expect(normalizePageName('a/b').error).toMatch(/can't contain/);
  expect(normalizePageName('con').error).toMatch(/reserved/);
  expect(normalizePageName('   ').error).toBe('Enter a name.');
  expect(normalizePageName('x'.repeat(250)).error).toMatch(/too long/);
});

test('isPagePathTaken compares paths case-insensitively', () => {
  const pages = [{ id: 'a', path: 'Notes/Home.canvas.html' }] as Page[];
  expect(isPagePathTaken(pages, pagePath('notes', 'HOME'))).toBe(true);
  expect(isPagePathTaken(pages, pagePath('notes', 'HOME'), 'a')).toBe(false);
  expect(isPagePathTaken(pages, pagePath('', 'Home'))).toBe(false);
});
