import { command } from "./fusion/libs/Command";


class PametCommands {
    @command('Create new note')
    createNewNote() {
        console.log('createNewNote command executed')

    }
}

export const commands = new PametCommands();
