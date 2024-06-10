/**
 * Project data model
 *
 * Projects in Pamet
 */

export interface ProjectData {
    id: string;
    name: string;
    owner: string; // User id
    description: string;
    created: number;
    currentBranch: string;
}
