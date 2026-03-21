import { ProjectReference } from "@/model/Project";

export interface UserData {
    id?: string;
    name?: string;
    projects?: ProjectReference[];
}
