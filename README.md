# Misli
A collection of projects with emphasis on controlling and organizing the digital resources available to the individual.

On the software side - the `misli` python module holds code common for writing cross platform apps in Python that can use different GUI frameworks (mainly Qt or arbitrary web frontends (via Brython and Cordova)). The aim is not to make a new GUI framework, but to abstract away and experiment with some technologies and architecture patterns.

# Pamet
An app for organizing thoughts and notes

## Current state
A rewrite, using the technologies outlined in the Misli module, is ongoing. Currently the app is in pre-alpha (if even that). The purpuse of this stage is to get some feedback on the overall architecture and the code so far. Feature wise there's only note resizing, moving and editing ATM. The immediate goal is to reach feature parity with misli v3 and then add new functionality.

### Usage
- Double click to create a new note
- Click to select
- Long-press to initiate move
- Ctrl or shift to select multiple notes
- Ctrl+Shift to drag-select multiple notes
- Drag the lower right corner of a note to resize it
- Buttons 1,2,3,4 change the note color. 5 removes the background
* Selected notes get moved together and resized to the same size
* No manual saving is required

To reiterate - a LOT of the functionality is missing, so the demo as of now serves just to showcase the technical aspects of the project. Also the tests aren't updated (and there are other loose ends too).

## Installation
Currently only the setuptools install from source is possible (there are plans for proper packaging). Requires Python 3.8 or higher.

1. Get the code with `git clone https://github.com/v-ko/misli.git`

2. Install the python packages:
    * Enter the `misli` folder and run `python setup.py develop` in the console
    * Enter the `pamet` folder and do the same

Now you should be able to run `pamet` and `pamet-debug` from the console. They both start the app, but the latter prints verbose logging (and could be a bit slower).
*On Windows you might need to take note of the reported install path and add it to your PATH environment variable
Currently the setup is not tested on Windows, so if there's a problem - do post an issue on github, I'll try to be prompt in helping out.

### Uninstall
Again in the `misli` and `pamet` folders run: `python setup.py develop --uninstall`

### Legacy version
The project was to this point explicitly for personal use and was itself called Misli. I wrote the initial version around 2011 in C++ (with Qt for the GUI). There were several iterations afterwards. The codebase currently resides in the `misli3-cpp` folder (the last released version was 3). I started the rewrite in order to make the project more easily maintainable and extensible.

#### Installation
You can build the app with QtCreator, using the project file in `misli3-cpp/misli_desktop`. This version is tested on Linux only.

#### Features
---------------------
- Map-like navigation
- Changing note size, position and color
- Multiple note files (called "pages" in the new version)
- Note file hyperlinking (via "link notes")
- Real-time detection of file changes (useful if you're using some type of file synchronization)
- Adding images
- Displaying text files on the file system as notes
- Text search
- Connectiong notes visually with bendable arrows
- Links to web resources
- Exporting note files to HTML
- System command notes (double-clicking them runs e.g. a bash script)

among other.

#### Screenshots (from v2, I'm not a graphical designer as you might notice)
![screenshot1](https://a.fsdn.com/con/app/proj/misli/screenshots/Screenshot%20from%202014-09-05%2014%3A40%3A19.png/max/max/1)
![screenshot2](https://a.fsdn.com/con/app/proj/misli/screenshots/Screenshot%20from%202014-09-05%2014%3A30%3A01.png/max/max/1)

# Misli dev overview
## General app development choices
### Tech stack choices
#### Programming languages
- Python is the main language of choice for several reasons
    - Elegant syntax - it's readable and succint
    - Has a rich standard library and bindings for almost everything
    - Is widely used and novice-friendly
- Wherever optimized algorythm implementations are needed C++ would be the choice, but given the nature of the software that's not likely to happen much
- Given that the web is a target platform JS/HTML/CSS are inevitable to some extent

#### Devices and OS/platform targets
The ambition is to deploy (at least some of the apps) everywhere: to PC (Linux, MacOS, Windows), mobile devices (Android, iOS, PostmarketOS) and the web.

#### Frameworks and libraries
The preffered stack currently is:
- FastAPI or Flask for the REST API (Python)
- Qt for Python for the desktop apps
- Web/Mobile - most likely Cordova plus React and Brython (python interpreter for the browser). It's a bit exotic, but Cordova can deploy any web frontend and Brython seems stable and active enough as a project. The main motivation is to avoid duplicating the action/usecase function implemenetations as much as possible (and only reimplement the Views).


### Discussion of the cross-platform development stack
The rationale for this not-so-obvious stack is in part a compromise - that's the only setup where most of the functionality (incl. GUI usecases) can be written in Python and used across all platforms. Also Electron-like deployments for the desktop are sub-optimal (in functionality, not so much in overhead), compared to Qt, and I plan for the desktop apps to be well optimized and feature rich, while the web and mobile versions would be more light weight.

It's a vast jungle of technologies out there, especially for web development. Since the projects here are to a great extent experimental and can enjoy only limited development resources - it's important to reuse code as much as possible. That means some performance and usability compromises for the time being. I.e. it would be great to have native iOS and Android apps, web app in e.g. React/JS and a desktop app in Qt/C++, that all work flawlessly, but that would take x10 times the development expertise and resources. Or I might be mistaken and the debugging and instability hurdles will prove a worse enemy than code duplication.

#### Technologies taken into account and the reasons for not choosing them (as of now)
- Flutter - it makes great promises for single codebase cross-platform apps, but it's still a relatively new technology and non-mobile platforms are in alpha and beta. Also adding Dart as an additional language to the project would have its cost (last reviewed Feb 2021)
- React Native - a good, widely-used SDK, but it's targeted mostly at mobile platforms (with some recent deployment options for Windows/MacOS) and the standard component library cannot be used for web apps.
 - Expo - a framework on top of React Native that boasts fast development and an extensive API exposing native functionality. One drawback seems to be that an expo project is too heavily intertwined with the framework tools and modules, while the company can still possibly make major changes. It's still a possible replacement for Cordova/React though
 - React-native-web - it seems Expo actually uses react-native-web under the hood (since the r-n-w docs suggest using expo instead of a manual install)
- A bunch of other libraries and frameworks were reviewed but lacked maturity, platform support, etc.

## Architecture of a Misli based app (including Pamet)
The main principles I strive to follow are inspired by Clean Architecture by Robert Martin. There are both a lot of fans and critics of the book and I don't regard it as some bible of software architecture. In it though there are many patterns and principles layed out with the logic behind them and tradeoffs related to them. I've also gathered ideas from various lectures and GUI framework related documentation and posts.

### GUI acrhitecture
After much consideration of the existing alternatives I took a liking to the Flux idea of building a GUI and decided to go with a refined/simplified version of it. And the implementation turned out to be very close to the [Model-View-Presenter](https://en.wikipedia.org/wiki/Model%E2%80%93view%E2%80%93presenter) pattern.

The main considerations were:
- Keeping the platform/framework specific code as separated as possible from the actions/usecases
- Having the ability to arrange components in a hierarchy (like the DOM in web pages or the Qt QObject parent-child relationships tree). And to update their properties efficiently
- Having reproducibilty of the user actions and corresponding app state
- Avoiding complex  GUI logic nesting, where a view update can trigger another and make debugging a pain.

The architecture has these mechanisms:
- Flux-like dataflow - Views accept user input and call Actions, they update the View-Models, and the misli.gui module aggregates those updates and pushes them to the Views.


The GUI is composed by components in a hierarchy. Each of them consists of a View, a View-Model and possibly actions/usecases.

**ViewStates** are dataclasses that define the properties of the corresponding View. They can be changed only through the `misli_gui.update_state(view_model)` method. The latter queues an update to the View on the main loop. That means several ViewState updates called by a user action will be merged and dispatched as a single view-update event.

**Views** receive user input and display a part of the GUI. The visual representation of the View should rely mostly on the ViewState (though having some local state is possible). The View class has 2 virtual functions: to handle ViewState changes and to handle children changes (added/removed/updated). Upon user input the View should call actions.

**Actions** are functions, which define the GUI behavior in response to user interactions. They are defined with a decorator, which enables record/replay of action calls and produces better logging. All of the ViewState changes should happen in actions. They are anologous to an action + reducer in redux. They are executed synchronously on the main loop (and can be nested) but the changes they make to the ViewStates are cached and sent to the Views (to update the GUI) as a separate task on the main loop (to avoid rendering overhead in some cases).

Some examples for minimal apps using this architecture will come, but for now take a look at the codebase of Pamet.

I'd be happy to discuss and receive any comments here on Github as issues or at pditchev in GMail.



## Vision and plans for Pamet and other projects
The main motivation for my work on Pamet was to add more functionality to the app and be able to share the accomulated over the last 10 years notes and workflows with more people.

The project spiraled into an learning experience, since I wanted for it to be properly planned for the next 10 years and possible user base and feature accomulation (though I don't expect much from the former).
 I had a great and tragic adventure in the jungle of GUI technologies. I also wandered into reading about some aspects of software architecture, that I had not explored. There's probably a lot more to learn, and correct, hence the prompt for feedback on the architecture and overall codebase.

There's no commercial plans for the app, given that note taking is very personal (thus users would be hard to please), while the market is flooded with note taking apps. I did not find any app, though, which has an interface such as I imagined it. I do believe that many developers and power users can benifit the interface and functionality I'm aiming for. Even if that turns out to not be true - it would be a good basis for personal tools or at least a learning experience for me and anyone that might want to get involved.

As for the other related project ideas - I'll hopefully have written up proper descriptions for them till the end of 2021 (or maybe even have shared them via Pamet ;)
