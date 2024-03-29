import { render, fireEvent, screen } from '@testing-library/react';

// Mock the pamet.util.calculateTextLayout function
// since it uses the Context2D API which is not available in Jest
jest.mock('../../util', () => ({
    ...jest.requireActual('../../util'),
    calculateTextLayout: () => {
        return {
            lines: [
                'First line',
                'Second line'
            ],
            alignment: 'center',
            is_elided: false,
        };
    },
}));


// eslint-disable-next-line import/first
import { NoteComponentBase } from './Note';
// eslint-disable-next-line import/first
import { NoteViewState } from './NoteViewState';
// eslint-disable-next-line import/first
import { Note } from '../../model/Note';

describe('NoteContainer', () => {
    it('calls handleClick on click', () => {
        const mockHandleClick = jest.fn();

        const noteViewState = new NoteViewState(new Note({
            id: '11111-22222',
            geometry: [0, 0, 0, 0],
            style: {
                color: [0, 0, 0, 0],
                background_color: [0, 0, 0, 0],
            },
            content: { 'text': 'Your text here' },
            created: '2021-01-01',
            modified: '2021-01-01',
            metadata: {},
            tags: [],
            page_id: '11111',
            own_id: '22222',
        }));

        render(
            <NoteComponentBase noteViewState={noteViewState} />
        );
        let element = screen.getByText('First line', { exact: false })
        fireEvent.click(element);

        expect(mockHandleClick).toHaveBeenCalled();
    });
});
