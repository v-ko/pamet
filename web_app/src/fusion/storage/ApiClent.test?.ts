export {}
// import { ApiClient } from './ApiClient';

// describe('ApiClient', () => {
//     let client: ApiClient;
//     let host = 'http://api.example.com';

//     beforeEach(() => {
//         client = new ApiClient(host);
//     });

//     it('should get pages with filter', async () => {
//         const mockPages = [
//             { id: 1, title: 'Page 1' },
//             { id: 2, title: 'Page 2' }
//         ];

//         jest.spyOn(client, 'fetchData').mockResolvedValueOnce(mockPages);

//         const filter = { title: 'Page' };
//         const pages = await client.pages(filter);

//         expect(pages).toEqual(mockPages);
//     });

//     it('should get children of a page', async () => {

//         const mockChildren = {
//             notes: [{ id: 1, content: 'Note 1' }],
//             arrows: [{ id: 2, source: 1, target: 2 }]
//         };

//         jest.spyOn(client, 'fetchData').mockResolvedValueOnce(mockChildren);

//         const children = await client.children('1');

//         expect(children).toEqual(mockChildren);
//     });
// });
