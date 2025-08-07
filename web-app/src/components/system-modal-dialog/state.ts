import { makeObservable, observable } from "mobx";

export abstract class SystemModalDialogState {
    showAfterUnixTime?: number; // Null to show immediately, or a Unix timestamp to show after that time
}

export class MediaProcessingDialogState extends SystemModalDialogState {
    title: string = '';
    taskDescription: string = '';
    taskProgress: number = -1; // -1 for spinner, 0-100 for progress bar

    constructor() {
        super();
        makeObservable(this, {
            title: observable,
            taskDescription: observable,
            taskProgress: observable,
            showAfterUnixTime: observable,
        });
    }
}
