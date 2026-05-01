import { Entity, EntityData, entityType } from "fusion/model/Entity"
import { timestamp } from 'fusion/util/base';
import { PametRoute } from "@/services/routing/PametRoute";
import { CANVAS_EXT } from "@/app/constants";

/** Extract the page name from a path by stripping the canvas extension. */
export function canvasPageNameFromPath(path: string): string {
  const lastSlash = path.lastIndexOf('/');
  const filename = lastSlash !== -1 ? path.substring(lastSlash + 1) : path;
  if (!filename.endsWith(CANVAS_EXT)) {
    throw new Error(`Page path '${path}' does not end with '${CANVAS_EXT}'`);
  }
  return filename.substring(0, filename.length - CANVAS_EXT.length);
}

export interface TourSegment {
  link: string;
  html: string;
}

export interface PageData extends EntityData {
  path: string;
  created: string;
  modified: string;
  // tour_segments: TourSegment[];
}


@entityType('Page')
export class Page extends Entity<PageData> {
  toString(): string {
    return `<Page id=${this.id} path=${this.path}>`;
  }

  get parentId(): string {
    return '';
  }

  projectScopedURI(): string {
    let route = new PametRoute({
      pageId: this.id,
    })
    return route.toProjectScopedURI()
  }

  get datetimeCreated(): Date {
    return new Date(this.created);
  }

  set datetimeCreated(newDt: Date) {
    this.created = timestamp(newDt);
  }

  get datetimeModified(): Date {
    return new Date(this.modified);
  }

  set datetimeModified(newDt: Date) {
    this.modified = timestamp(newDt);
  }

  //  Data access properties
  get path(): string {
    return this._data.path;
  }
  set path(newPath: string) {
    this._data.path = newPath;
  }
  /** Derived: filename stem without extension */
  get name(): string {
    if (!this.path) return '';
    return canvasPageNameFromPath(this.path);
  }
  /** Derived: parent directory (empty string for root) */
  get folder(): string {
    if (!this.path) return '';
    const lastSlash = this.path.lastIndexOf('/');
    return lastSlash !== -1 ? this.path.substring(0, lastSlash) : '';
  }
  get created(): string {
    return this._data.created;
  }
  set created(newDt: string) {
    this._data.created = newDt;
  }
  get modified(): string {
    return this._data.modified;
  }
  set modified(newDt: string) {
    this._data.modified = newDt;
  }
  // get tour_segments(): TourSegment[] {
  //   return this._data.tour_segments;
  // }
}
