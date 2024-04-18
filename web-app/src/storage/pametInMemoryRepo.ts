import { InMemoryRepository } from "pyfusion/storage/InMemoryRepository";
import { PametRepository } from "./base";

class PametInMemoryRepo extends PametRepository {
    constructor() {
        super(new InMemoryRepository());
    }
}
