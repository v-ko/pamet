import { Page } from "../../model/Page";
import { InMemoryRepository } from "./InMemoryRepository";


test("InMemoryRepository", () => {
    let repo = new InMemoryRepository();
    let entity = new Page({
        id: "123",
        created: '2021-01-01',
        modified: '2021-01-01',
        name: "Test Page",
        tour_segments: []
    })

    // Test insert
    let changeCreate = repo.insertOne(entity);
    expect(changeCreate).toBeDefined();

    let all_entities = [...repo.find()];
    expect(all_entities.length).toBe(1);

    // Test update
    entity.name = "456";
    let changeUpdate = repo.updateOne(entity);
    expect(changeUpdate).toBeDefined();
    expect([...repo.find()].length).toBe(1);

    // Test delete
    let changeDelete = repo.removeOne(entity);
    expect(changeDelete).toBeDefined();
    expect([...repo.find()].length).toBe(0);
});
