import { InMemoryStore } from 'sivkit/storage/domain-store/InMemoryStore';
import { Change } from 'sivkit/model/Change';
import { Delta } from 'sivkit/model/Delta';
import { UserSettings } from '@/model/config/UserSettings';
import { DesktopStorageState, ProjectStorageState } from '@/model/config/ServiceState';
import { LocalStorageConfigSync } from './LocalStorageConfigSync';

test('reload restores user config without restoring runtime service status', async () => {
    const settings = new UserSettings({ id: UserSettings.SINGLETON_ID, parent_id: '', userName: 'Alice' });
    const states = [
        new DesktopStorageState({ id: DesktopStorageState.SINGLETON_ID, parent_id: '', closing: true, config_errors: {} }),
        new ProjectStorageState({ id: ProjectStorageState.idForProject('p'), parent_id: '', project_id: 'p', phase: 'open', filesystem: null, backup: null, history_error: null }),
    ];
    localStorage.clear();
    const store = new InMemoryStore();
    const sync = new LocalStorageConfigSync();
    const reloaded = new InMemoryStore();
    const reloadSync = new LocalStorageConfigSync();
    sync.setStore(store);
    reloadSync.setStore(reloaded);
    try {
        for (const entity of [settings, ...states]) store.insertOne(entity);
        await sync.pushDelta(Delta.fromChanges([settings, ...states].map(entity => Change.create(entity))));
        for (const state of states) expect(localStorage.getItem(`pamet-config:${state.id}`)).toBeNull();
        await reloadSync.initialize();
        expect(reloaded.findOne({ id: settings.id })?.data()).toEqual(settings.data());
        for (const state of states) expect(reloaded.findOne({ id: state.id })).toBeUndefined();
    } finally {
        sync.dispose();
        reloadSync.dispose();
        localStorage.clear();
    }
});
