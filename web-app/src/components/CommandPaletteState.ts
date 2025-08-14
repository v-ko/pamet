import { makeObservable, observable } from "mobx";

// States
export class CommandPaletteState {
    initialInput: string = '';

    constructor(initialInput: string) {
        this.initialInput = initialInput;

        makeObservable(this, {
            initialInput: observable,
        });
    }
}

export class PageAndCommandPaletteState extends CommandPaletteState {
}

export class ProjectPaletteState extends CommandPaletteState {
}
