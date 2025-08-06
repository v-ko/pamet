# Dev guidlines for the project
*** This is for AI assistants, but I guess it'll do for humans too if nothing else is present lol ***

## UI feature implementation

### Styling
Look at variables.css and e.g. the NoteEditView.css to get an idea of the programming style for css. Crude for now.

### Architecture
It's an architecture inspired by the FLUX pattern, and the standard MVC.
There's a domain store called the Frontend domain store (FDS), which the UI operates with (persistance is handled additionaly). Changes in the FDS trigger updates of the MobX view model - the UI component's view states. The UI views are implemented in React with MobX integration, so any changes to the state trigger a re-render. Views can call actions (decorated functions). In actions the mobX state can be altered, as well as the FDS (only there!). The changes are visualized to the user. And the cycle is completed.

