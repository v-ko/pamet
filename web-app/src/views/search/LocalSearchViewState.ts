import { makeObservable, observable } from "mobx";

export class LocalSearchViewState {
    query: string = '';

    constructor(initialQuery: string = '') {
        this.query = initialQuery;

        makeObservable(this, {
            query: observable,
        });
    }
}
