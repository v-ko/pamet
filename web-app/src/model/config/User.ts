import { ProjectData } from "./Project";

export interface UserData {
    id: string;
    name: string;
    projects: ProjectData[];
}
