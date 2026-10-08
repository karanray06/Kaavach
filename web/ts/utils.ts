/**
 * utils.ts — Shared utility functions for Kavach frontend.
 */

export function escapeHtml(str: string): string {
  const div: HTMLDivElement = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}
