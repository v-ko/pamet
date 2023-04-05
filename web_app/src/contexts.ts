import { createContext } from 'react';

type CurrentPageContextData = {
    pageId: string,
    changePage: (pageId: string) => void
}

export const SelectionContext = createContext<Array<string>>([])
export const CurrentPageContext = createContext<CurrentPageContextData> ({
    pageId: "",
    changePage: (pageId: string) => {}
})

