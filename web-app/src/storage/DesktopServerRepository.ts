import { BaseAsyncRepository } from "fusion/storage/BaseRepository";
import { CommitGraph } from "fusion/storage/CommitGraph";
import { Commit } from "fusion/storage/Commit";
import { Delta } from "fusion/storage/Delta";
import { ApiClient } from "./ApiClient";
import { getLogger } from "fusion/logging";
import { Change } from "fusion/Change";
import { AsyncInMemoryRepository } from "fusion/storage/AsyncInMemoryRepo";

const log = getLogger('DesktopServerRepository');

export class DesktopServerRepository extends BaseAsyncRepository {
    apiClient: ApiClient;
    _inMemRepo = new AsyncInMemoryRepository();

    constructor(apiClient: ApiClient) {
        super();
        this.apiClient = apiClient;
    }

    async init(branchName: string): Promise<void> {
        await this._inMemRepo.init(branchName);

        try {
            // Get all pages
            const pages = await this.apiClient.pages();

            // Create one commit for all the objects at once
            let changes: Change[] = []
            for (const page of pages) {
                const children = await this.apiClient.children(page.id);

                // Add page
                changes.push(Change.create(page));

                // Add notes
                for (const note of children.notes) {
                    changes.push(Change.create(note));
                }

                // Add arrows
                for (const arrow of children.arrows) {
                    changes.push(Change.create(arrow));
                }
            }

            const delta = Delta.fromChanges(changes);
            await this._inMemRepo.commit(delta, "Initial state from desktop server");

        } catch (error) {
            log.error('Failed to initialize from desktop server:', error);
            throw error;
        }
    }

    async getCommits(ids: string[]): Promise<Commit[]> {
        return this._inMemRepo.getCommits(ids);
    }

    async commit(deltaData: Delta, message: string): Promise<Commit> {
        return this._inMemRepo.commit(deltaData, message);
    }

    async reset(filter: { relativeToHead: number }): Promise<void> {
        return this._inMemRepo.reset(filter);
    }

    async _checkAndApplyUpdate(remoteGraph: CommitGraph, newCommits: Commit[]): Promise<void> {
        // No-op for read-only repo
        return this._inMemRepo._checkAndApplyUpdate(remoteGraph, newCommits)
    }

    async createBranch(branchName: string): Promise<void> {
        // No-op for read-only repo
        return this._inMemRepo.createBranch(branchName)
    }

    async eraseStorage(): Promise<void> {
        // No-op for read-only repo
        return this._inMemRepo.eraseStorage()
    }

    async getCommitGraph(): Promise<CommitGraph> {
        return this._inMemRepo.getCommitGraph()
    }
}
