export interface MediaItemData {
    id: string;  // Unique for the project
    prefix: string;  // For FS storage and organization (e.g. path in the proeject)
    hash: string;  // Unique for the content (since the media providers may be less reliable?)
}
