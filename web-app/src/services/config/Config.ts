import { getLogger } from "fusion/logging";
import { buildRestApiAuthHeaders, RestApiAuthConfig } from "fusion/storage/rest-api/Auth";
import { DeviceData } from "@/model/config/Device";
import { ProjectData } from "@/model/config/Project";
import { UserData } from "@/model/config/User";
import { BaseConfigAdapter } from "@/services/config/BaseConfigAdapter";

const log = getLogger('PametConfigService');
const LOCAL_PROJECTS_KEY = "localProjects";

export abstract class BasePametKeyValueService {
    abstract setUpdateHandler(handler: () => void): void;
    abstract data(): object;
    abstract clear(): void;
    abstract getUserData(): UserData | undefined;
    abstract setUserData(userData: UserData): void;
    abstract getDeviceData(): DeviceData | undefined;
    abstract setDeviceData(deviceData: DeviceData): void;
    abstract getLocalProjects(): ProjectData[];
    abstract setLocalProjects(projects: ProjectData[]): void;

    addProject(project: ProjectData) {
        const projects = this.getLocalProjects();
        this.setLocalProjects([...projects, project]);
    }

    removeProject(projectId: string) {
        const projects = this.getLocalProjects();
        const index = projects.findIndex((p) => p.id === projectId);
        if (index === -1) {
            throw new Error(`Project with ID ${projectId} not found`);
        }
        projects.splice(index, 1);
        this.setLocalProjects(projects);
    }

    projectData(projectId: string): ProjectData | undefined {
        const project = this.getLocalProjects().find((p) => p.id === projectId);
        return project;
    }

    updateProjectData(projectData: ProjectData) {
        const projects = this.getLocalProjects();
        const index = projects.findIndex((p) => p.id === projectData.id);
        if (index === -1) {
            throw new Error(`Project with ID ${projectData.id} not found`);
        }
        log.info("Updating project in config", projectData);
        projects[index] = projectData;
        this.setLocalProjects(projects);
    }
}


export class PametKeyValueStorageService extends BasePametKeyValueService {
    /**
     * A wrapper to access and modify user settings, device settings,
     * project metadata, and other light config items stored in localStorage.
     */
    private _adapter: BaseConfigAdapter;

    constructor(adapter: BaseConfigAdapter) {
        super();
        this._adapter = adapter;
    }

    setUpdateHandler(handler: () => void) {
        this._adapter.setUpdateHandler(handler);
    }

    data(): object {
        return this._adapter.data();
    }

    clear() {
        this._adapter.clear();
    }

    getUserData(): UserData | undefined {
        const userData = this._adapter.get('user');
        if (userData) {
            return userData as UserData;
        }
        return undefined;
    }

    setUserData(userData: UserData) {
        this._adapter.set('user', userData);
    }

    getDeviceData(): DeviceData | undefined {
        const deviceData = this._adapter.get('device');
        if (deviceData) {
            return deviceData as DeviceData;
        }
        return undefined;
    }

    setDeviceData(deviceData: DeviceData) {
        this._adapter.set('device', deviceData);
    }

    getLocalProjects(): ProjectData[] {
        const projects = this._adapter.get(LOCAL_PROJECTS_KEY);
        if (Array.isArray(projects)) {
            return projects as ProjectData[];
        }
        return [];
    }

    setLocalProjects(projects: ProjectData[]) {
        this._adapter.set(LOCAL_PROJECTS_KEY, projects);
    }
}

export interface DesktopPametConfigServiceOptions {
    adapter: BaseConfigAdapter;
    baseUrl: string;
    auth: RestApiAuthConfig;
}

export class DesktopPametConfigService extends BasePametKeyValueService {
    private _adapter: BaseConfigAdapter;
    private _baseUrl: string;
    private _auth: RestApiAuthConfig;
    private _localProjects: ProjectData[] = [];

    constructor(options: DesktopPametConfigServiceOptions) {
        super();
        this._adapter = options.adapter;
        this._baseUrl = options.baseUrl;
        this._auth = options.auth;
    }

    async refreshLocalProjectsFromDesktop(): Promise<void> {
        const url = new URL('/desktop/local-projects', this._baseUrl).toString();
        const response = await fetch(url, {
            method: "GET",
            headers: buildRestApiAuthHeaders(this._auth),
        });

        if (!response.ok) {
            throw new Error(
                `Failed to fetch desktop local projects: ${response.status} ${response.statusText}`,
            );
        }

        const data = await response.json() as ProjectData[];
        this._localProjects = [...data];
    }

    setUpdateHandler(handler: () => void) {
        this._adapter.setUpdateHandler(handler);
    }

    data(): object {
        return {
            ...this._adapter.data(),
            [LOCAL_PROJECTS_KEY]: this._localProjects,
        };
    }

    clear() {
        log.warning("DesktopPametConfigService.clear() is local-only and not synced to desktop backend.");
        this._adapter.clear();
    }

    getUserData(): UserData | undefined {
        const userData = this._adapter.get('user');
        if (userData) {
            return userData as UserData;
        }
        return undefined;
    }

    setUserData(userData: UserData) {
        log.warning("DesktopPametConfigService.setUserData() is local-only and not synced to desktop backend.");
        this._adapter.set('user', userData);
    }

    getDeviceData(): DeviceData | undefined {
        const deviceData = this._adapter.get('device');
        if (deviceData) {
            return deviceData as DeviceData;
        }
        return undefined;
    }

    setDeviceData(deviceData: DeviceData) {
        log.warning("DesktopPametConfigService.setDeviceData() is local-only and not synced to desktop backend.");
        this._adapter.set('device', deviceData);
    }

    getLocalProjects(): ProjectData[] {
        return this._localProjects;
    }

    setLocalProjects(projects: ProjectData[]) {
        void projects;
        log.warning("DesktopPametConfigService.setLocalProjects() is not implemented for backend sync.");
        throw new Error("DesktopPametConfigService.setLocalProjects is not implemented");
    }

    addProject(project: ProjectData) {
        void project;
        log.warning("DesktopPametConfigService.addProject() is not implemented for backend sync.");
        throw new Error("DesktopPametConfigService.addProject is not implemented");
    }

    removeProject(projectId: string) {
        void projectId;
        log.warning("DesktopPametConfigService.removeProject() is not implemented for backend sync.");
        throw new Error("DesktopPametConfigService.removeProject is not implemented");
    }

    updateProjectData(projectData: ProjectData) {
        void projectData;
        log.warning("DesktopPametConfigService.updateProjectData() is not implemented for backend sync.");
        throw new Error("DesktopPametConfigService.updateProjectData is not implemented");
    }
}
