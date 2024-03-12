import { PageChild, PageChildData } from "../../model/PageChild";

export abstract class PageChildViewState {
    abstract pageChild(): PageChild<PageChildData>;

}
