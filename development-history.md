
# Pamet development history
## Tech stack choices
This was one of the more daunting tasks for this project, because of the fact that it's a jungle of GUI technologies out there. Also because I set out with high expectations and goals. Mainly:
- Deploy to the main platforms (desktop, web, mobile)
- Preferably use Python - since it's what I work with (and find elegant), but for some technical reasons too
- Preferably write in just one language - keep things DRY, given that I was going to work alone on the project at least initially

I researched a bunch of alternatives - Flutter, React/React Native, Expo, and whatever else I could find. But there was no silver bullet to be found.

### The initial wonky plan
So after a lot of digging I decided to go with Python+Qt for the desktop app and to build my own state manager in order to abstract the controller/actions away and be able to swap out GUI frameworks. In that sense the plan was to build the web app with Brython (a python interpreter that can run in a web page) and reuse the actions, as well as the state classes and the view base classes (and just reimplement the view widgets).

Also - get that - I'll deploy the web app as a mobile app using Cordova. So python executed in a browser, wrapped in Cordova on mobile - that would be a great debugging experience no doubt

## GUI acrhitecture considerations
After much consideration of the existing alternatives I took a liking to the Flux/Redux idea of isolating the view states and decided to go with a modified version of it. And the implementation turned out to be very close to the [Model-View-Presenter](https://en.wikipedia.org/wiki/Model%E2%80%93view%E2%80%93presenter) pattern.

The main considerations were:
- Keeping the platform/framework specific code as separated as possible from the actions(/presenter/controller)
- Having the ability to arrange components in a hierarchy (like the DOM in web pages or the Qt QObject parent-child relationships tree). And to update their properties efficiently
- Having reproducibilty of the user actions and corresponding app state
- Avoiding complex  GUI logic nesting, where a view update can trigger another and make debugging a pain.

## Learning, mistakes and deviations from the plan
Firstly - it turned out that building scalable GUI apps is quite the engineering challenge, which I'd underestimated until now. It's easy to imagine them, but not so much to build them in a robust, scalable, flexible, future-proof manner (given it's an innovative product, and not just some input forms).

So I had to read up on design patterns, GUI architecture, I took a liking to Clean architecture along the way. So I thought I had a pretty good idea what I wanted to build.

The implementation went along quite well - maybe too well, because at some point I realized that I'd overengineered it. I was pretty close to finishing up the infrastructure part (or so I thought) - I had a state manager, a view manager, an abstraction for platform functionality, pubsub for state and entity changes. Even command/shortcut/context managers in order to abstract that functionality away and not reimplement it when I get to implementing the web/mobile abomination.

Turns out though it sucks. I went to visit my grandparents, and I wanted to install a Raspberry Pi running a simple gallery app for them, connected to the tv. The gallery app would be minimalistic and me and some relatives would upload stuff via OwnCloud.

Queue an existential crisis - I tried to use my infrastructure to build the gallery app. And it was a miserable experience. I had overreached and almost went to make a GUI framework, which, frankly, sucked. So I implemented the app in pure Qt and realized I had to revise my plans seriously.

So after some laborous stripping of functionality and postponing the initial release by an ungodly amount of time - I got to reach a point where I was quite ok with adding features with the reduced infrastructure (the [Fusion](https://github.com/v-ko/fusion) module).

As for the Brython/Cordova plan - I might experiment with that, but it's no longer the main plan. I've heard mixed opininons from people that tried to use them + I've gotten more wary of large dependencies. So it might take more dev effort, but I'd rather write native minimal web/mobile apps for the time being. The dream of deploying the same codebase everywhere lives on though. May I live long enough to see it happen.

