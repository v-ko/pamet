import { getLogger } from "fusion/logging";
import { DeviceData } from "../../model/config/Device";
import { ProjectData } from "../../model/config/Project";
import { UserData } from "../../model/config/User";
import { BaseConfigAdapter } from "./BaseConfigAdapter";

const log = getLogger('PametConfigService');


export class PametConfigService {
    /**
     * A wrapper to access and modify user settings, device settings,
     * project metadata, and possibly other light config items that will be
     * stored in the local storage. An update handler can be set to be called
     * when the config is updated.
     */
    private _adapter: BaseConfigAdapter;

    constructor(adapter: BaseConfigAdapter) {
        this._adapter = adapter;
    }

    setUpdateHandler(handler: () => void) {
        this._adapter.setUpdateHandler(handler);
    }

    clear() {
        this._adapter.clear();
    }

    get userData() : UserData | undefined {
        let userData = this._adapter.get('user');
        if (userData) {
            return userData as UserData;
        } else {
            return undefined;
        }
    }
    set userData(userData: UserData) {
        this._adapter.set('user', userData);
    }

    get deviceData() : DeviceData | undefined {
        let deviceData = this._adapter.get('device');
        if (deviceData) {
            return deviceData as DeviceData;
        } else {
            return undefined;
        }
    }
    set deviceData(deviceData: DeviceData) {
        this._adapter.set('device', deviceData);
    }

    addProject(project: ProjectData){
        let userData = this.userData;
        if (!userData) {
            throw new Error("User data not found");
        }

        userData.projects.push(project);
        this.userData = userData;
    }
    removeProject(projectId: string) {
        let userData = this.userData;
        if (!userData) {
            throw new Error("User data not found");
        }

        let projects = userData.projects;
        let index = projects.findIndex(p => p.id === projectId);
        if (index === -1) {
            throw new Error(`Project with ID ${projectId} not found`);
        }
        projects.splice(index, 1);
        userData.projects = projects;
        this.userData = userData;
    }
    projectData(projectId: string): ProjectData | undefined {
        // For the current user
        let userData = this.userData;
        if (!userData) {
            throw new Error("User data not found");
        }
        let project = userData.projects.find(p => p.id === projectId);
        return project;
    }
    updateProjectData(projectData: ProjectData) {
        // For the current user
        let userData = this.userData;
        if (!userData) {
            throw new Error("User data not found");
        }
        let projects = userData.projects;
        let index = projects.findIndex(p => p.id === projectData.id);
        if (index === -1) {
            throw new Error(`Project with ID ${projectData.id} not found`);
        }

        log.info("Updating project in config", projectData);
        projects[index] = projectData;
        userData.projects = projects;
        this.userData = userData;
    }
}
