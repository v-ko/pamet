import { Point2D } from "fusion/primitives/Point2D";

export enum NavigationDevice {
    MOUSE = "mouse",
    TOUCHPAD = "touchpad",
}

const LAST_EQUAL_SCROLLS_TO_ASSUME_MOUSE = 3;

export class NavigationDeviceAutoSwitcher {
    /**
     * A class to infer the navigation mode (touchpad or mouse) from the scroll
     * events. If the scroll event a horizontal component -
     * then we're using a touchpad. If the scrolling is y-only and uniform - then
     * we're using a mouse.
     */

    _currentDevice: NavigationDevice = NavigationDevice.MOUSE;
    _lastScrollEvents: Point2D[] = []; // The last 10 scroll events (deltaX, deltaY)

    get device(): NavigationDevice {
        return this._currentDevice;
    }

    setDevice(device: NavigationDevice) {
        if (this._currentDevice === device) {
            return;
        }
        console.log('Setting device to', device)
        this._currentDevice = device;
    }


    registerScrollEvent(delta: Point2D) {
        this._lastScrollEvents.push(delta);
        if (this._lastScrollEvents.length > 10) {
            this._lastScrollEvents.shift();
        }

        // Infer the navigation device

        // If there's a horizontal component - switch to touchpad
        if (delta.x !== 0) {
            this.setDevice(NavigationDevice.TOUCHPAD)
            return;
        }

        // If there are 3 vertical scroll events at equal (and typical) interval
        // assume mouse usage
        if (this._lastScrollEvents.length >= LAST_EQUAL_SCROLLS_TO_ASSUME_MOUSE) {
            const last3 = this._lastScrollEvents.slice(-LAST_EQUAL_SCROLLS_TO_ASSUME_MOUSE);
            const last3y = last3.map((e) => Math.abs(e.y));
            const interval = Math.min(...last3y);
            const isUniform = last3y.every((e) => (e % interval === 0) && (e % 1 === 0) && (e > 50));

            if (isUniform) {
                this.setDevice(NavigationDevice.MOUSE)
            }
        }
    }

    registerRightMouseDrag(delta: Point2D) {
        // Switch to mouse mode
        this.setDevice(NavigationDevice.MOUSE)
    }

}
