import { ProjectData } from "@/model/config/Project";

export interface UserData {
    id: string;
    name: string;
    projects: ProjectData[];
}
