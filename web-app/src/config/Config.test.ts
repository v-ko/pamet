import { UserData } from '../model/config/User';
import { PametConfig } from './Config';
import { DummyConfigAdapter } from './DummyAdapter';

// prep for mocking localStorage


describe('PametConfig', () => {
    let config: PametConfig;
    let adapter: DummyConfigAdapter;

    beforeEach(() => {
        adapter = new DummyConfigAdapter();
        config = new PametConfig(adapter);
    });

    afterEach(() => {
        adapter.clear();
    });

    test('clear', () => {
        adapter.set('user', { name: 'John Doe' });
        adapter.set('device', { id: '123' });

        config.clear();

        expect(adapter.get('user')).toBeUndefined();
        expect(adapter.get('device')).toBeUndefined();
    });

    test('userData', () => {
        let userData: UserData = { id: '123', name: 'John Doe', projects: []}
        config.userData = userData;

        expect(config.userData).toEqual(userData);
        expect(adapter.get('user')).toEqual(userData);
    });

    test('setUpdateHandler', () => {
        let handler = jest.fn();
        config.setUpdateHandler(handler);
        config.deviceData = { id: '123', name: 'WebApp' };

        // Expect the handler to fire
        expect(handler).toHaveBeenCalled();
    });

});
