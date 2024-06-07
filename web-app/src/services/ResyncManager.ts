import { Change } from "pyfusion/Change";
import { Store } from "pyfusion/storage/BaseRepository";

export class FrontendStoreResyncService {
    
    private _store: Store;
    private _expectedChangesets: Change[][] = [];

    constructor(store: Store) {
        this._store = store;
    }

    pushExpectedChangeset(changeset: Change[]) {
        this._expectedChangesets.push(changeset);
    }
    receiveChangeset(changeset: Change[]) {
        // Expect the changeset to be equal to the first in the _expectedChangesets
        // If not -
        // raise exception for now
    }
}
