import { makeObservable, observable } from "mobx";

export class LoadingDialogState {
    showAfterUnixTime: number | null = null; // Null to show immediately, or a Unix timestamp to show after that time
    title: string = '';
    taskDescription: string = '';
    taskProgress: number = -1; // -1 for spinner, 0-100 for progress bar

    constructor(title: string, taskDescription: string = '', taskProgress: number = -1, showAfterUnixTime: number | null = null) {
        this.title = title;
        this.taskDescription = taskDescription;
        this.taskProgress = taskProgress;
        this.showAfterUnixTime = showAfterUnixTime;
        
        makeObservable(this, {
            title: observable,
            taskDescription: observable,
            taskProgress: observable,
            showAfterUnixTime: observable,
        });
    }
}
