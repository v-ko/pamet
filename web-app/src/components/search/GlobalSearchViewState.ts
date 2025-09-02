import { makeObservable, observable } from "mobx";

export class GlobalSearchViewState {
    query: string = '';
    focusCounter: number = 0;

    constructor(initialQuery: string = '') {
        this.query = initialQuery;
        makeObservable(this, {
            query: observable,
            focusCounter: observable,
        });
    }

    incrementFocusCounter() {
        this.focusCounter++;
    }
}
