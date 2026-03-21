import { UserData } from "@/model/User";
import { MiscPropertiesService, PametSettingsService } from "@/services/config/Config";
import { DummyConfigAdapter } from "@/services/config/DummyAdapter";


describe('Config', () => {
    let adapter: DummyConfigAdapter;

    beforeEach(() => {
        adapter = new DummyConfigAdapter();
    });

    afterEach(() => {
        adapter.clear();
    });

    test('settings use only userSettings key', () => {
        const config = new PametSettingsService(adapter);
        const userData: UserData = { id: '123', name: 'John Doe' };

        config.setUserData(userData);

        expect(adapter.get('userSettings')).toEqual(userData);
    });

    test('settings clear removes only settings keys', () => {
        const settings = new PametSettingsService(adapter);
        const misc = new MiscPropertiesService(adapter);

        settings.setUserData({ id: '123' });
        misc.setRecentProjects([{ id: 'p1', title: 'Project 1', uri: 'indexeddb:///p1' }]);
        misc.setDeviceId('device-1');

        settings.clear();

        expect(adapter.get('userSettings')).toBeUndefined();
        expect(adapter.get('recentProjects')).toEqual([{ id: 'p1', title: 'Project 1', uri: 'indexeddb:///p1' }]);
        expect(adapter.get('deviceId')).toBe('device-1');
    });

    test('setUpdateHandler fires on local updates', () => {
        const config = new PametSettingsService(adapter);
        const handler = jest.fn();

        config.setUpdateHandler(handler);
        config.setUserData({ id: '123' });

        expect(handler).toHaveBeenCalled();
    });

    test('tracked projects live under userSettings', () => {
        const config = new PametSettingsService(adapter);

        config.setUserData({ id: '123', name: 'John Doe' });
        config.upsertProject({ id: 'p1', title: 'Project 1', uri: 'indexeddb:///p1' });

        expect(config.getProjects()).toEqual([{ id: 'p1', title: 'Project 1', uri: 'indexeddb:///p1' }]);
        expect(adapter.get('userSettings')).toEqual({
            id: '123',
            name: 'John Doe',
            projects: [{ id: 'p1', title: 'Project 1', uri: 'indexeddb:///p1' }],
        });
    });


    test('device id lives in misc properties', () => {
        const misc = new MiscPropertiesService(adapter);

        misc.setDeviceId('device-1');

        expect(misc.getDeviceId()).toBe('device-1');
        expect(adapter.get('deviceId')).toBe('device-1');
    });
});
