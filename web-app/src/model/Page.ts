import { Entity, EntityData, entityType } from "fusion/libs/Entity"
import { timestamp } from 'fusion/util.js';

export interface TourSegment {
  link: string;
  html: string;
}

export interface PageData extends EntityData {
  name: string;
  created: string;
  modified: string;
  // tour_segments: TourSegment[];
}


@entityType('Page')
export class Page extends Entity<PageData> implements PageData {
  toString(): string {
    return `<Page id=${this.id} name=${this.name}>`;
  }

  get parentId(): string {
    return '';
  }

  url(): string {
    return `pamet:///p/${this.id}`;
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
  get name(): string {
    return this._data.name;
  }
  set name(newName: string) {
    this._data.name = newName;
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
