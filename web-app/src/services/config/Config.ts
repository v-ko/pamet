import { ProjectReference } from "@/model/Project";
import { UserData } from "@/model/User";
import { BaseConfigAdapter, SettingsFieldValue } from "@/services/config/BaseConfigAdapter";

export class KeyValueStorage {
    protected _adapter: BaseConfigAdapter;

    constructor(adapter: BaseConfigAdapter) {
        this._adapter = adapter;
    }

    private _assertKey(key: string): void {
        if (!key.trim()) {
            throw new Error("Key is required");
        }
    }

    setUpdateHandler(handler: () => void): void {
        this._adapter.setUpdateHandler(handler);
    }

    get(key: string): SettingsFieldValue | undefined {
        this._assertKey(key);
        return this._adapter.get(key);
    }

    set(key: string, value: SettingsFieldValue | undefined): void {
        this._assertKey(key);
        this._adapter.set(key, value);
    }

    remove(key: string): void {
        this._assertKey(key);
        this._adapter.set(key, undefined);
    }
}

export class PametSettingsService extends KeyValueStorage {
    static readonly USER_SETTINGS_KEY = "userSettings";

    getUserData(): UserData | undefined {
        const userData = this.get(PametSettingsService.USER_SETTINGS_KEY);
        if (userData) {
            return userData as UserData;
        }
        return undefined;
    }

    setUserData(userData: UserData): void {
        this.set(PametSettingsService.USER_SETTINGS_KEY, userData);
    }

    getProjects(): ProjectReference[] {
        const userData = this.getUserData();
        if (!userData?.projects) {
            return [];
        }
        return userData.projects
    }

    setProjects(projects: ProjectReference[]): void {
        this.setUserData({
            ...(this.getUserData() ?? {}),
            projects,
        });
    }

    upsertProject(projectData: ProjectReference): void {
        const projects = this.getProjects();
        const index = projects.findIndex((project) => project.id === projectData.id);
        if (index === -1) {
            this.setProjects([...projects, projectData]);
            return;
        }
        const nextProjects = [...projects];
        nextProjects[index] = projectData;
        this.setProjects(nextProjects);
    }

    removeProject(projectId: string): void {
        const projects = this.getProjects();
        this.setProjects(projects.filter((project) => project.id !== projectId));
    }

    clear(): void {
        this.remove(PametSettingsService.USER_SETTINGS_KEY);
    }

    data(): object {
        return {
            [PametSettingsService.USER_SETTINGS_KEY]: this.getUserData(),
        };
    }
}

export class MiscPropertiesService extends KeyValueStorage {
    static readonly RECENT_PROJECTS_KEY = "recentProjects";
    static readonly DEVICE_ID_KEY = "deviceId";

    getRecentProjects(): ProjectReference[] {
        const projects = this.get(MiscPropertiesService.RECENT_PROJECTS_KEY);
        if (Array.isArray(projects)) {
            return projects.map((project) => ({
                id: project.id,
                title: project.title ?? project.id,
                uri: project.uri ?? '',
            })) as ProjectReference[];
        }
        return [];
    }

    getDeviceId(): string | undefined {
        const deviceId = this.get(MiscPropertiesService.DEVICE_ID_KEY);
        if (typeof deviceId === "string" && deviceId.trim()) {
            return deviceId;
        }
        return undefined;
    }

    setDeviceId(deviceId: string): void {
        this.set(MiscPropertiesService.DEVICE_ID_KEY, deviceId);
    }

    removeDeviceId(): void {
        this.remove(MiscPropertiesService.DEVICE_ID_KEY);
    }

    setRecentProjects(projects: ProjectReference[]): void {
        this.set(MiscPropertiesService.RECENT_PROJECTS_KEY, projects);
    }

    addRecentProject(project: ProjectReference): void {
        const projects = this.getRecentProjects();
        this.setRecentProjects([...projects, project]);
    }

    setMostRecentProject(project: ProjectReference): void {
        const projects = this.getRecentProjects().filter(
            (candidate) => candidate.id !== project.id,
        );
        this.setRecentProjects([project, ...projects]);
    }

    removeRecentProject(projectId: string): void {
        const projects = this.getRecentProjects();
        const nextProjects = projects.filter((project) => project.id !== projectId);
        if (nextProjects.length === projects.length) {
            throw new Error(`Recent project with ID ${projectId} not found`);
        }
        this.setRecentProjects(nextProjects);
    }

    recentProject(projectId: string): ProjectReference | undefined {
        return this.getRecentProjects().find((project) => project.id === projectId);
    }

    updateRecentProject(projectData: ProjectReference): void {
        const projects = this.getRecentProjects();
        const index = projects.findIndex((project) => project.id === projectData.id);
        if (index === -1) {
            throw new Error(`Recent project with ID ${projectData.id} not found`);
        }
        const nextProjects = [...projects];
        nextProjects[index] = projectData;
        this.setRecentProjects(nextProjects);
    }

    clear(): void {
        this.remove(MiscPropertiesService.RECENT_PROJECTS_KEY);
        this.remove(MiscPropertiesService.DEVICE_ID_KEY);
    }

    data(): object {
        return {
            [MiscPropertiesService.RECENT_PROJECTS_KEY]: this.getRecentProjects(),
            [MiscPropertiesService.DEVICE_ID_KEY]: this.getDeviceId(),
        };
    }
}
