import { IDBPDatabase, OpenDBCallbacks, openDB, StoreNames } from "idb";


export class DebugConnectionTracker {
    // Keep a Set of DB references, or store extra info if you like
    static openConnections: Set<IDBPDatabase> = new Set();

    static async openDBWithTracking<T>(
        name: string,
        version?: number,
        callbacks?: OpenDBCallbacks<T>
    ) {
        const db = await openDB<T>(name, version, callbacks);

        // Track the open connection
        DebugConnectionTracker.openConnections.add(db as any);
        console.log('[DebugConnectionTracker] Opened', name, 'version:', db.version);
        console.log('[DebugConnectionTracker] Currently open DB count:', DebugConnectionTracker.openConnections.size);

        // If the DB is closed for any reason, remove it from the set
        db.addEventListener('close', () => {
            DebugConnectionTracker.openConnections.delete(db as any);
            console.log('[DebugConnectionTracker] Closed', name, 'Remaining count:', DebugConnectionTracker.openConnections.size);
        });

        return db;
    }

    static logAllConnections() {
        console.log('[DebugConnectionTracker] All open DBs:', DebugConnectionTracker.openConnections.size);
        for (const conn of DebugConnectionTracker.openConnections) {
            console.log('   =>', conn.name, conn.version, conn);
        }
    }
}
export function wrapDbWithTransactionDebug<T>(db: IDBPDatabase<T>): IDBPDatabase<T> {
    const originalTransaction = db.transaction.bind(db);

    // Replace the transaction method with a wrapper
    // that logs creation and completion
    (db as any).transaction = function (stores: string | string[], mode?: IDBTransactionMode) {
        console.log('[TxDebug] Starting transaction:', stores, mode);

        const tx = originalTransaction(stores as StoreNames<T>, mode);

        // Log completion
        tx.done.then(() => {
            console.log('[TxDebug] Finished transaction:', stores, mode);
        }).catch((err: any) => {
            console.error('[TxDebug] Transaction failed:', stores, mode, err);
        });

        return tx;
    };

    return db;
}
