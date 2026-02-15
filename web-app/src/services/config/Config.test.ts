import { UserData } from "@/model/config/User";
import { PametKeyValueStorageService } from "@/services/config/Config";
import { DummyConfigAdapter } from "@/services/config/DummyAdapter";

// prep for mocking localStorage


describe('PametConfig', () => {
    let config: PametKeyValueStorageService;
    let adapter: DummyConfigAdapter;

    beforeEach(() => {
        adapter = new DummyConfigAdapter();
        config = new PametKeyValueStorageService(adapter);
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
        let userData: UserData = { id: '123', name: 'John Doe' }
        config.setUserData(userData);

        expect(config.getUserData()).toEqual(userData);
        expect(adapter.get('user')).toEqual(userData);
    });

    test('setUpdateHandler', () => {
        let handler = jest.fn();
        config.setUpdateHandler(handler);
        config.setDeviceData({ id: '123', name: 'WebApp' });

        // Expect the handler to fire
        expect(handler).toHaveBeenCalled();
    });

});
