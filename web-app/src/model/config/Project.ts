export interface ProjectData {
    id: string;
    title: string;
    owner?: string; // User id (optional, informative only)
    description: string;
    created: string;
    defaultPageId?: string;
}
